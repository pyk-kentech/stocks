from stock_risk_mcp.offline_strategy_dataset_compatibility_engine import build_offline_strategy_dataset_compatibility
from stock_risk_mcp.offline_strategy_models import OfflineStrategyPipelineInput
from tests.test_offline_strategy_models import offline_strategy_rows_payload


def test_offline_strategy_dataset_compatibility_ready_for_direct_rows() -> None:
    fixture = OfflineStrategyPipelineInput.model_validate(
        {"pipeline_id": "offline-strategy-test", "dataset_id": "offline-strategy-test", "ohlcv_rows": offline_strategy_rows_payload()}
    )
    report = build_offline_strategy_dataset_compatibility(fixture, fixture.ohlcv_rows)
    assert report.readiness_status.value == "DATASET_COMPATIBILITY_READY"
    assert report.row_count == 20
