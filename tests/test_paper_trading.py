from __future__ import annotations

import csv
import json
from datetime import date, datetime, timedelta

import pytest

from stock_risk_mcp.basket import BasketAllocation, BasketMode, BasketPlan, BasketPolicy, BasketRiskSummary
from stock_risk_mcp.cli import main
from stock_risk_mcp.models import BacktestOutcome, PriceBar
from stock_risk_mcp.paper_trading import ExitReason, PaperTradeStatus, create_paper_trade, close_paper_trade
from stock_risk_mcp.paper_trading import BasketBacktestResult
from stock_risk_mcp.repository import RiskRepository
from stock_risk_mcp.setup import SetupDirection, SetupGrade, TradeDecision


def test_allocation_converts_to_paper_trade_and_calculates_pnl() -> None:
    trade = create_paper_trade("basket-1", _allocation(), date(2026, 1, 1))

    assert trade.direction == SetupDirection.LONG
    assert trade.status == PaperTradeStatus.OPEN
    assert trade.entry_price == 10

    closed = close_paper_trade(trade, date(2026, 1, 5), 12, ExitReason.TAKE_PROFIT)

    assert closed.status == PaperTradeStatus.CLOSED
    assert closed.realized_pnl == pytest.approx(20)
    assert closed.realized_return_pct == pytest.approx(20)


def test_repository_saves_paper_trades_results_and_performance(tmp_path) -> None:
    repository = RiskRepository(tmp_path / "risk.sqlite3")
    trade = close_paper_trade(create_paper_trade("basket-1", _allocation(), date(2026, 1, 1)), date(2026, 1, 2), 12, ExitReason.TAKE_PROFIT)
    result = _result("basket-1", 20, 20)

    trade_id = repository.save_paper_trade(trade)
    result_id = repository.save_basket_backtest_result(result)

    assert trade_id == 1
    assert result_id == 1
    assert repository.list_paper_trades("basket-1") == [trade]
    assert repository.get_basket_backtest_result("basket-1") == result
    assert repository.get_basket_backtest_result("missing") is None
    assert repository.list_basket_backtest_results() == [result]
    assert repository.basket_performance_summary().total_baskets == 1


def test_paper_trading_cli_db_file_list_and_performance(tmp_path, capsys) -> None:
    db_path = tmp_path / "risk.sqlite3"
    price_file = tmp_path / "prices.csv"
    repository = RiskRepository(db_path)
    plan = _plan()
    repository.save_basket_plan(plan)
    bars = [_bar(date(2026, 1, 2), 9.5, 12.5, 12)]
    repository.save_price_bars(bars)
    _write_price_csv(price_file, bars)

    main(["paper-trade-basket", "--db", str(db_path), "--basket-id", plan.basket_id, "--horizon-days", "10"])
    db_output = json.loads(capsys.readouterr().out)
    main(
        [
            "paper-trade-basket-from-file",
            "--db",
            str(db_path),
            "--basket-id",
            plan.basket_id,
            "--price-history-file",
            str(price_file),
            "--horizon-days",
            "10",
        ]
    )
    file_output = json.loads(capsys.readouterr().out)
    main(["paper-trades", "--db", str(db_path), "--basket-id", plan.basket_id])
    trades_output = json.loads(capsys.readouterr().out)
    main(["basket-performance", "--db", str(db_path)])
    performance_output = json.loads(capsys.readouterr().out)

    assert db_output["outcome"] == "WIN"
    assert file_output["outcome"] == "WIN"
    assert trades_output["trades"]
    assert performance_output["total_baskets"] >= 1


def _allocation() -> BasketAllocation:
    return BasketAllocation(
        ticker="SAFE",
        setup_grade=SetupGrade.A,
        allocated_loss_amount=10,
        allocated_notional_value=100,
        position_size=10,
        entry_price=10,
        stop_price=9,
        target_price=12,
        risk_reward_ratio=2,
        allocation_reason="fixture",
    )


def _plan() -> BasketPlan:
    allocation = _allocation()
    return BasketPlan(
        basket_id="basket-1",
        basket_name="fixture",
        mode=BasketMode.PAPER_TRADING,
        policy=BasketPolicy(account_equity=10_000, cash_available=5_000, min_candidates=1),
        candidates=[],
        allocations=[allocation],
        blocked=[],
        risk_summary=BasketRiskSummary(
            total_allocated_loss=10,
            max_allowed_loss=100,
            total_notional_value=100,
            max_allowed_notional=2500,
            candidate_count=1,
            sector_counts={},
            theme_counts={},
            blocked_reasons=[],
            warnings=[],
            risk_ok=True,
        ),
        decision=TradeDecision.PROPOSE,
        beginner_summary="fixture",
        created_at=datetime(2026, 1, 1),
    )


def _result(basket_id: str, pnl: float, return_pct: float) -> BasketBacktestResult:
    return BasketBacktestResult(
        basket_id=basket_id,
        horizon_days=10,
        entry_date=date(2026, 1, 1),
        exit_date=date(2026, 1, 2),
        total_notional_value=100,
        total_allocated_loss=10,
        realized_pnl=pnl,
        realized_return_pct=return_pct,
        max_drawdown=min(pnl, 0),
        max_gain=max(pnl, 0),
        win_count=1,
        loss_count=0,
        flat_count=0,
        no_data_count=0,
        closed_trade_count=1,
        outcome=BacktestOutcome.WIN,
        created_at=datetime(2026, 1, 2),
    )


def _bar(day: date, low: float, high: float, close: float) -> PriceBar:
    return PriceBar(ticker="SAFE", date=day, low=low, high=high, close=close)


def _write_price_csv(path, bars: list[PriceBar]) -> None:
    with path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=["ticker", "date", "open", "high", "low", "close", "volume"])
        writer.writeheader()
        for bar in bars:
            writer.writerow(bar.model_dump(mode="json"))
