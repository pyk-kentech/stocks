from stock_risk_mcp.offline_strategy_models import (
    OfflineStrategyBacktestResult,
    OfflineStrategyCandidate,
    OfflineStrategyExitReason,
    OfflineStrategyMetricSummary,
    OfflineStrategyPipelineInput,
    OfflineStrategySimulatedTrade,
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


def test_offline_strategy_promotion_gate_passed_decision_has_no_rejection_reason() -> None:
    pipeline = OfflineStrategyPipelineInput.model_validate(
        {"pipeline_id": "offline-strategy-test", "dataset_id": "offline-strategy-test", "ohlcv_rows": offline_strategy_rows_payload()}
    )
    candidate = OfflineStrategyCandidate.model_validate(
        {
            "candidate_id": "candidate-2",
            "dataset_id": "offline-strategy-test",
            "template_id": "VOLUME_PULLBACK_LONG_V1",
            "family": "VOLUME_PULLBACK_LONG",
            "direction": "LONG_ONLY",
            "parameter_values": {},
        }
    )
    backtest = OfflineStrategyBacktestResult.model_validate(
        {
            "result_id": "result-2",
            "candidate_id": "candidate-2",
            "readiness_status": "BACKTEST_READY",
            "trade_count": 5,
            "cumulative_return": 0.3,
            "max_drawdown": 0.05,
            "max_drawdown_raw": 0.05,
            "max_drawdown_unit": "FRACTION_OF_EQUITY",
            "trades": [
                OfflineStrategySimulatedTrade.model_validate(
                    {
                        "trade_id": "trade-1",
                        "candidate_id": "candidate-2",
                        "instrument_id": "005930",
                        "entry_at": "2026-06-10T15:30:00+09:00",
                        "exit_at": "2026-06-11T15:30:00+09:00",
                        "entry_price": 100.0,
                        "exit_price": 106.0,
                        "gross_return": 0.06,
                        "net_return": 0.055,
                        "exit_reason": OfflineStrategyExitReason.TIME_EXIT,
                        "split_role": "TEST",
                    }
                )
            ],
            "leakage_audit_status": "LEAKAGE_AUDIT_PASSED",
        }
    )
    metric = OfflineStrategyMetricSummary.model_validate(
        {
            "report_id": "metric-2",
            "candidate_id": "candidate-2",
            "trade_count": 5,
            "out_of_sample_trade_count": 5,
            "cumulative_return": 0.3,
            "average_trade_return": 0.06,
            "expectancy": 0.06,
            "profit_factor": 2.0,
            "win_rate": 0.6,
            "max_drawdown": 0.05,
            "max_drawdown_unit": "FRACTION_OF_EQUITY",
        }
    )
    decision = build_offline_strategy_promotion_decision(pipeline, candidate, backtest, metric, diagnostics={"leakage_audit_status": "LEAKAGE_AUDIT_PASSED"})
    assert decision.status.value == "PROMOTED_OFFLINE_CANDIDATE"
    assert decision.reasons == []
