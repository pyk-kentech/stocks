from stock_risk_mcp.offline_strategy_guard import validate_offline_strategy_input_gate
from stock_risk_mcp.offline_strategy_models import OfflineStrategyPipelineInput
from tests.test_offline_strategy_models import offline_strategy_rows_payload


def test_offline_strategy_guard_accepts_chronological_direct_rows() -> None:
    fixture = OfflineStrategyPipelineInput.model_validate(
        {"pipeline_id": "offline-strategy-test", "dataset_id": "offline-strategy-test", "ohlcv_rows": offline_strategy_rows_payload()}
    )
    readiness, findings, gaps = validate_offline_strategy_input_gate(fixture)
    assert readiness.value == "DATASET_COMPATIBILITY_READY"
    assert findings == []
    assert gaps == []
