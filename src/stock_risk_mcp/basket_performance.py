from __future__ import annotations

import statistics

from stock_risk_mcp.models import BacktestOutcome
from stock_risk_mcp.paper_trading import BasketBacktestResult, BasketPerformanceSummary, PaperTrade


def summarize_basket_performance(
    results: list[BasketBacktestResult],
    trades: list[PaperTrade] | None = None,
) -> BasketPerformanceSummary:
    if not results:
        return BasketPerformanceSummary(total_baskets=0, by_setup_grade={}, by_exit_reason={})
    returns = [result.realized_return_pct for result in results]
    pnls = [result.realized_pnl for result in results]
    gains = sum(value for value in pnls if value > 0)
    losses = abs(sum(value for value in pnls if value < 0))
    return BasketPerformanceSummary(
        total_baskets=len(results),
        avg_return_pct=statistics.fmean(returns),
        median_return_pct=statistics.median(returns),
        win_rate=sum(result.outcome == BacktestOutcome.WIN for result in results) / len(results),
        avg_realized_pnl=statistics.fmean(pnls),
        profit_factor=gains / losses if losses else None,
        avg_max_drawdown=statistics.fmean(
            result.max_drawdown for result in results if result.max_drawdown is not None
        )
        if any(result.max_drawdown is not None for result in results)
        else None,
        by_setup_grade=_count_by(trades or [], "setup_grade"),
        by_exit_reason=_count_by(trades or [], "exit_reason"),
    )


def _count_by(trades: list[PaperTrade], field: str) -> dict[str, int]:
    counts: dict[str, int] = {}
    for trade in trades:
        value = getattr(trade, field)
        key = value.value if value is not None else "NONE"
        counts[key] = counts.get(key, 0) + 1
    return counts
