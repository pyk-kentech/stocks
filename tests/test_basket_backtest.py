from __future__ import annotations

from datetime import date, datetime, timedelta

from stock_risk_mcp.basket import BasketAllocation, BasketMode, BasketPlan, BasketPolicy, BasketRiskSummary
from stock_risk_mcp.basket_backtest import run_basket_backtest
from stock_risk_mcp.models import BacktestOutcome, PriceBar
from stock_risk_mcp.setup import SetupGrade, TradeDecision


def test_basket_backtest_aggregates_trade_results_and_outcomes() -> None:
    plan = _plan()
    entry_date = date(2026, 1, 1)
    bars = {
        "WIN": [_bar("WIN", entry_date + timedelta(days=1), 9.5, 12.5, 12)],
        "LOSS": [_bar("LOSS", entry_date + timedelta(days=1), 8.5, 10.5, 9)],
    }

    result, trades = run_basket_backtest(plan, bars, entry_date, horizon_days=10)

    assert result.realized_pnl == 30
    assert result.win_count == 1
    assert result.loss_count == 1
    assert result.closed_trade_count == 2
    assert result.outcome == BacktestOutcome.WIN
    assert {trade.ticker for trade in trades} == {"WIN", "LOSS"}


def test_basket_backtest_returns_no_data_when_all_trades_have_no_data() -> None:
    result, trades = run_basket_backtest(_plan(), {}, date(2026, 1, 1), horizon_days=10)

    assert result.outcome == BacktestOutcome.NO_DATA
    assert result.no_data_count == 2
    assert all(trade.status.value == "NO_DATA" for trade in trades)


def _plan() -> BasketPlan:
    allocations = [
        _allocation("WIN", 20),
        _allocation("LOSS", 10),
    ]
    return BasketPlan(
        basket_id="basket-1",
        basket_name="fixture",
        mode=BasketMode.PAPER_TRADING,
        policy=BasketPolicy(account_equity=10_000, cash_available=5_000, min_candidates=1),
        candidates=[],
        allocations=allocations,
        blocked=[],
        risk_summary=BasketRiskSummary(
            total_allocated_loss=30,
            max_allowed_loss=100,
            total_notional_value=300,
            max_allowed_notional=2500,
            candidate_count=2,
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


def _allocation(ticker: str, position_size: float) -> BasketAllocation:
    return BasketAllocation(
        ticker=ticker,
        setup_grade=SetupGrade.A,
        allocated_loss_amount=position_size,
        allocated_notional_value=position_size * 10,
        position_size=position_size,
        entry_price=10,
        stop_price=9,
        target_price=12,
        risk_reward_ratio=2,
        allocation_reason="fixture",
    )


def _bar(ticker: str, day: date, low: float, high: float, close: float) -> PriceBar:
    return PriceBar(ticker=ticker, date=day, low=low, high=high, close=close)
