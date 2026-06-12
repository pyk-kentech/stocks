from __future__ import annotations

from datetime import datetime
from uuid import uuid4

from stock_risk_mcp.models import StrictModel
from stock_risk_mcp.paper_trading import BasketBacktestResult, PaperTrade


class StrategyMemory(StrictModel):
    memory_id: str
    basket_id: str | None = None
    ticker: str | None = None
    setup_grade: str | None = None
    decision: str
    features_json: dict
    outcome: str | None = None
    realized_return_pct: float | None = None
    realized_pnl: float | None = None
    max_drawdown: float | None = None
    policy_id: str | None = None
    policy_version: str | None = None
    created_at: datetime


def create_memory_from_basket_result(result: BasketBacktestResult) -> StrategyMemory:
    return StrategyMemory(
        memory_id=uuid4().hex,
        basket_id=result.basket_id,
        decision="BASKET_BACKTEST",
        features_json={
            "horizon_days": result.horizon_days,
            "total_notional_value": result.total_notional_value,
            "total_allocated_loss": result.total_allocated_loss,
            "closed_trade_count": result.closed_trade_count,
            "decision": "BASKET_BACKTEST",
            "policy_id": result.policy_id,
            "policy_version": result.policy_version,
            "setup_scoring_mode": None,
            "basket_scoring_mode": result.basket_scoring_mode,
        },
        outcome=result.outcome.value,
        realized_return_pct=result.realized_return_pct,
        realized_pnl=result.realized_pnl,
        max_drawdown=result.max_drawdown,
        policy_id=result.policy_id,
        policy_version=result.policy_version,
        created_at=result.created_at,
    )


def create_memories_from_paper_trades(trades: list[PaperTrade]) -> list[StrategyMemory]:
    return [_memory_from_paper_trade(trade) for trade in trades]


def _memory_from_paper_trade(trade: PaperTrade) -> StrategyMemory:
    setup_grade = trade.setup_grade.value
    exit_reason = trade.exit_reason.value if trade.exit_reason else None
    return StrategyMemory(
        memory_id=uuid4().hex,
        basket_id=trade.basket_id,
        ticker=trade.ticker,
        setup_grade=setup_grade,
        decision=trade.status.value,
        features_json={
            "setup_grade": setup_grade,
            "exit_reason": exit_reason,
            "risk_reward_ratio": None,
            "allocated_loss_amount": trade.allocated_loss_amount,
            "notional_value": trade.notional_value,
            "decision": trade.status.value,
            "policy_id": trade.policy_id,
            "policy_version": trade.policy_version,
            "setup_scoring_mode": None,
            "basket_scoring_mode": trade.basket_scoring_mode,
        },
        outcome=exit_reason,
        realized_return_pct=trade.realized_return_pct,
        realized_pnl=trade.realized_pnl,
        policy_id=trade.policy_id,
        policy_version=trade.policy_version,
        created_at=trade.created_at,
    )
