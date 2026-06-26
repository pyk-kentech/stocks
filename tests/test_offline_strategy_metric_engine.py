from stock_risk_mcp.offline_strategy_metric_engine import build_offline_strategy_metric_summary
from tests.test_offline_strategy_backtest_engine import test_offline_strategy_backtest_engine_uses_next_bar_fill  # noqa: F401
from stock_risk_mcp.offline_strategy_models import OfflineStrategyBacktestResult


def test_offline_strategy_metric_engine_computes_summary() -> None:
    backtest = OfflineStrategyBacktestResult.model_validate(
        {
            "result_id": "result-1",
            "candidate_id": "candidate-1",
            "readiness_status": "BACKTEST_READY",
            "trade_count": 0,
            "cumulative_return": 0.0,
            "max_drawdown": 0.0,
            "trades": [],
        }
    )
    summary = build_offline_strategy_metric_summary("offline-strategy-test", backtest)
    assert summary.trade_count == 0
    assert summary.report_only is True
