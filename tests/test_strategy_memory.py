from __future__ import annotations

from datetime import date, datetime

from stock_risk_mcp.basket import BasketAllocation
from stock_risk_mcp.models import BacktestOutcome
from stock_risk_mcp.paper_trading import (
    BasketBacktestResult,
    ExitReason,
    close_paper_trade,
    create_paper_trade,
)
from stock_risk_mcp.setup import SetupGrade
from stock_risk_mcp.repository import RiskRepository
from stock_risk_mcp.strategy_memory import create_memories_from_paper_trades, create_memory_from_basket_result


def test_creates_strategy_memory_from_basket_result() -> None:
    memory = create_memory_from_basket_result(_result())

    assert memory.basket_id == "basket-1"
    assert memory.decision == "BASKET_BACKTEST"
    assert memory.outcome == "WIN"
    assert memory.features_json["horizon_days"] == 10


def test_creates_strategy_memories_from_paper_trades_without_inventing_features() -> None:
    trade = close_paper_trade(
        create_paper_trade("basket-1", _allocation(), date(2026, 1, 1)),
        date(2026, 1, 2),
        12,
        ExitReason.TAKE_PROFIT,
    )

    memory = create_memories_from_paper_trades([trade])[0]

    assert memory.ticker == "SAFE"
    assert memory.decision == "CLOSED"
    assert memory.features_json["setup_grade"] == "A"
    assert memory.features_json["exit_reason"] == "TAKE_PROFIT"
    assert memory.features_json["risk_reward_ratio"] is None
    assert memory.features_json["policy_id"] is None


def test_repository_saves_and_lists_strategy_memories(tmp_path) -> None:
    repository = RiskRepository(tmp_path / "risk.sqlite3")
    memory = create_memory_from_basket_result(_result())

    assert repository.save_strategy_memory(memory) == 1
    assert repository.list_strategy_memories() == [memory]


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


def _result() -> BasketBacktestResult:
    return BasketBacktestResult(
        basket_id="basket-1",
        horizon_days=10,
        entry_date=date(2026, 1, 1),
        exit_date=date(2026, 1, 2),
        total_notional_value=100,
        total_allocated_loss=10,
        realized_pnl=20,
        realized_return_pct=20,
        max_drawdown=-5,
        max_gain=20,
        win_count=1,
        loss_count=0,
        flat_count=0,
        no_data_count=0,
        closed_trade_count=1,
        outcome=BacktestOutcome.WIN,
        created_at=datetime(2026, 1, 2),
    )
