from stock_risk_mcp.offline_strategy_models import (
    OfflineStrategyBacktestResult,
    OfflineStrategyCandidate,
    OfflineStrategyMetricSummary,
    OfflineStrategyPipelineInput,
)
from stock_risk_mcp.offline_strategy_promotion_gate import build_offline_strategy_promotion_decision
from tests.test_offline_strategy_models import offline_strategy_rows_payload


def test_offline_strategy_promotion_gate_rejects_tiny_sample() -> None:
    pipeline = OfflineStrategyPipelineInput.model_validate(
        {"pipeline_id": "offline-strategy-test", "dataset_id": "offline-strategy-test", "ohlcv_rows": offline_strategy_rows_payload()}
    )
    candidate = OfflineStrategyCandidate.model_validate(
        {
            "candidate_id": "candidate-1",
            "dataset_id": "offline-strategy-test",
            "template_id": "VOLUME_PULLBACK_LONG_V1",
            "family": "VOLUME_PULLBACK_LONG",
            "direction": "LONG_ONLY",
            "parameter_values": {},
        }
    )
    backtest = OfflineStrategyBacktestResult.model_validate(
        {"result_id": "result-1", "candidate_id": "candidate-1", "readiness_status": "BACKTEST_READY", "trade_count": 1, "cumulative_return": 0.1, "max_drawdown": 0.01, "trades": []}
    )
    metric = OfflineStrategyMetricSummary.model_validate(
        {"report_id": "metric-1", "candidate_id": "candidate-1", "trade_count": 1, "out_of_sample_trade_count": 1, "cumulative_return": 0.1, "average_trade_return": 0.1, "expectancy": 0.1, "profit_factor": 2.0, "win_rate": 1.0, "max_drawdown": 0.01}
    )
    decision = build_offline_strategy_promotion_decision(pipeline, candidate, backtest, metric)
    assert decision.status.value in {"REJECTED", "WATCHLIST_ONLY"}
