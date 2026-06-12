from __future__ import annotations

from datetime import date, datetime
from enum import StrEnum
from uuid import uuid4

from pydantic import Field

from stock_risk_mcp.basket import BasketAllocation
from stock_risk_mcp.models import BacktestOutcome, StrictModel
from stock_risk_mcp.setup import SetupDirection, SetupGrade


class PaperTradeStatus(StrEnum):
    OPEN = "OPEN"
    CLOSED = "CLOSED"
    CANCELLED = "CANCELLED"
    NO_DATA = "NO_DATA"


class ExitReason(StrEnum):
    STOP_LOSS = "STOP_LOSS"
    TAKE_PROFIT = "TAKE_PROFIT"
    TIME_EXIT = "TIME_EXIT"
    NO_DATA = "NO_DATA"
    INVALID_PLAN = "INVALID_PLAN"


class PaperTrade(StrictModel):
    trade_id: str
    basket_id: str
    ticker: str
    direction: SetupDirection
    setup_grade: SetupGrade
    entry_price: float
    stop_price: float
    target_price: float | None = None
    position_size: float
    allocated_loss_amount: float
    notional_value: float
    entry_date: date
    exit_date: date | None = None
    exit_price: float | None = None
    exit_reason: ExitReason | None = None
    realized_pnl: float | None = None
    realized_return_pct: float | None = None
    status: PaperTradeStatus
    created_at: datetime


class BasketBacktestResult(StrictModel):
    basket_id: str
    horizon_days: int = Field(..., ge=1)
    entry_date: date
    exit_date: date | None = None
    total_notional_value: float
    total_allocated_loss: float
    realized_pnl: float
    realized_return_pct: float
    max_drawdown: float | None = None
    max_gain: float | None = None
    win_count: int
    loss_count: int
    flat_count: int
    no_data_count: int
    closed_trade_count: int
    outcome: BacktestOutcome
    created_at: datetime


class BasketPerformanceSummary(StrictModel):
    total_baskets: int
    avg_return_pct: float | None = None
    median_return_pct: float | None = None
    win_rate: float | None = None
    avg_realized_pnl: float | None = None
    profit_factor: float | None = None
    avg_max_drawdown: float | None = None
    by_setup_grade: dict
    by_exit_reason: dict


def create_paper_trade(basket_id: str, allocation: BasketAllocation, entry_date: date) -> PaperTrade:
    return PaperTrade(
        trade_id=uuid4().hex,
        basket_id=basket_id,
        ticker=allocation.ticker,
        direction=SetupDirection.LONG,
        setup_grade=allocation.setup_grade,
        entry_price=allocation.entry_price,
        stop_price=allocation.stop_price,
        target_price=allocation.target_price,
        position_size=allocation.position_size,
        allocated_loss_amount=allocation.allocated_loss_amount,
        notional_value=allocation.allocated_notional_value,
        entry_date=entry_date,
        status=PaperTradeStatus.OPEN,
        created_at=datetime.now(),
    )


def close_paper_trade(trade: PaperTrade, exit_date: date, exit_price: float, reason: ExitReason) -> PaperTrade:
    realized_pnl = (exit_price - trade.entry_price) * trade.position_size
    realized_return_pct = realized_pnl / trade.notional_value * 100 if trade.notional_value else 0.0
    return trade.model_copy(
        update={
            "exit_date": exit_date,
            "exit_price": exit_price,
            "exit_reason": reason,
            "realized_pnl": realized_pnl,
            "realized_return_pct": realized_return_pct,
            "status": PaperTradeStatus.CLOSED,
        }
    )


def no_data_paper_trade(trade: PaperTrade) -> PaperTrade:
    return trade.model_copy(
        update={
            "exit_reason": ExitReason.NO_DATA,
            "status": PaperTradeStatus.NO_DATA,
        }
    )
