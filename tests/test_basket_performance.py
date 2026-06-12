from __future__ import annotations

from datetime import date, datetime

from stock_risk_mcp.basket_performance import summarize_basket_performance
from stock_risk_mcp.models import BacktestOutcome
from stock_risk_mcp.paper_trading import BasketBacktestResult


def test_basket_performance_summary_calculates_returns_and_profit_factor() -> None:
    summary = summarize_basket_performance([_result("a", 10, 5), _result("b", -5, -2.5)])

    assert summary.total_baskets == 2
    assert summary.avg_return_pct == 1.25
    assert summary.median_return_pct == 1.25
    assert summary.win_rate == 0.5
    assert summary.avg_realized_pnl == 2.5
    assert summary.profit_factor == 2


def _result(basket_id: str, pnl: float, return_pct: float) -> BasketBacktestResult:
    return BasketBacktestResult(
        basket_id=basket_id,
        horizon_days=10,
        entry_date=date(2026, 1, 1),
        exit_date=date(2026, 1, 11),
        total_notional_value=200,
        total_allocated_loss=20,
        realized_pnl=pnl,
        realized_return_pct=return_pct,
        max_drawdown=min(pnl, 0),
        max_gain=max(pnl, 0),
        win_count=1 if pnl > 0 else 0,
        loss_count=1 if pnl < 0 else 0,
        flat_count=0,
        no_data_count=0,
        closed_trade_count=1,
        outcome=BacktestOutcome.WIN if pnl > 0 else BacktestOutcome.LOSS,
        created_at=datetime(2026, 1, 11),
    )
