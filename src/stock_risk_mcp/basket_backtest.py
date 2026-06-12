from __future__ import annotations

from datetime import date, datetime

from stock_risk_mcp.basket import BasketPlan
from stock_risk_mcp.exits import simulate_long_exit
from stock_risk_mcp.models import BacktestOutcome, PriceBar
from stock_risk_mcp.paper_trading import (
    BasketBacktestResult,
    PaperTrade,
    PaperTradeStatus,
    close_paper_trade,
    create_paper_trade,
    no_data_paper_trade,
)


def run_basket_backtest(
    plan: BasketPlan,
    price_bars_by_ticker: dict[str, list[PriceBar]],
    entry_date: date,
    horizon_days: int,
) -> tuple[BasketBacktestResult, list[PaperTrade]]:
    trades: list[PaperTrade] = []
    for allocation in plan.allocations:
        trade = create_paper_trade(
            plan.basket_id,
            allocation,
            entry_date,
            plan.policy_id,
            plan.policy_version,
            plan.basket_scoring_mode,
        )
        exit_result = simulate_long_exit(
            trade.entry_price,
            trade.stop_price,
            trade.target_price,
            price_bars_by_ticker.get(trade.ticker, []),
            entry_date,
            horizon_days,
        )
        if exit_result.price is None or exit_result.date is None:
            trades.append(no_data_paper_trade(trade))
        else:
            trades.append(close_paper_trade(trade, exit_result.date, exit_result.price, exit_result.reason))

    closed = [trade for trade in trades if trade.status == PaperTradeStatus.CLOSED]
    realized_pnl = sum(trade.realized_pnl or 0 for trade in closed)
    total_notional = sum(trade.notional_value for trade in trades)
    total_allocated_loss = sum(trade.allocated_loss_amount for trade in trades)
    no_data_count = sum(trade.status == PaperTradeStatus.NO_DATA for trade in trades)
    outcome = _outcome(realized_pnl, len(trades), no_data_count)
    result = BasketBacktestResult(
        basket_id=plan.basket_id,
        horizon_days=horizon_days,
        entry_date=entry_date,
        exit_date=max((trade.exit_date for trade in closed if trade.exit_date is not None), default=None),
        total_notional_value=total_notional,
        total_allocated_loss=total_allocated_loss,
        realized_pnl=realized_pnl,
        realized_return_pct=realized_pnl / total_notional * 100 if total_notional else 0.0,
        max_drawdown=min((trade.realized_pnl or 0 for trade in closed), default=None),
        max_gain=max((trade.realized_pnl or 0 for trade in closed), default=None),
        win_count=sum((trade.realized_pnl or 0) > 0 for trade in closed),
        loss_count=sum((trade.realized_pnl or 0) < 0 for trade in closed),
        flat_count=sum((trade.realized_pnl or 0) == 0 for trade in closed),
        no_data_count=no_data_count,
        closed_trade_count=len(closed),
        outcome=outcome,
        created_at=datetime.now(),
        policy_id=plan.policy_id,
        policy_version=plan.policy_version,
        basket_scoring_mode=plan.basket_scoring_mode,
    )
    return result, trades


def _outcome(realized_pnl: float, trade_count: int, no_data_count: int) -> BacktestOutcome:
    if trade_count > 0 and no_data_count == trade_count:
        return BacktestOutcome.NO_DATA
    if realized_pnl > 0:
        return BacktestOutcome.WIN
    if realized_pnl < 0:
        return BacktestOutcome.LOSS
    return BacktestOutcome.FLAT
