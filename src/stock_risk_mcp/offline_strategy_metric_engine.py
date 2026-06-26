from __future__ import annotations

from stock_risk_mcp.offline_strategy_models import OfflineStrategyBacktestResult, OfflineStrategyMetricSummary


def build_offline_strategy_metric_summary(dataset_id: str, backtest_result: OfflineStrategyBacktestResult) -> OfflineStrategyMetricSummary:
    trades = backtest_result.trades
    winners = [trade for trade in trades if trade.net_return > 0]
    losers = [trade for trade in trades if trade.net_return <= 0]
    gross_profit = sum(trade.net_return for trade in winners)
    gross_loss = abs(sum(trade.net_return for trade in losers))
    trade_count = len(trades)
    avg_trade = sum(trade.net_return for trade in trades) / trade_count if trade_count else 0.0
    expectancy = avg_trade
    profit_factor = gross_profit / gross_loss if gross_loss else (gross_profit if gross_profit else 0.0)
    win_rate = len(winners) / trade_count if trade_count else 0.0
    stop_hit_rate = 0.0
    return OfflineStrategyMetricSummary(
        report_id=f"{dataset_id}-{backtest_result.candidate_id}-METRIC-SUMMARY",
        candidate_id=backtest_result.candidate_id,
        trade_count=trade_count,
        out_of_sample_trade_count=trade_count,
        cumulative_return=backtest_result.cumulative_return,
        average_trade_return=avg_trade,
        expectancy=expectancy,
        profit_factor=profit_factor,
        win_rate=win_rate,
        max_drawdown=backtest_result.max_drawdown,
        stop_hit_rate=stop_hit_rate,
        exposure=float(trade_count),
        turnover=float(trade_count),
        warnings=backtest_result.warnings,
    )
