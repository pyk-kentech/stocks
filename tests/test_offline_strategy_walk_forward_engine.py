from stock_risk_mcp.offline_strategy_models import OfflineStrategyPipelineInput
from stock_risk_mcp.offline_strategy_walk_forward_engine import build_offline_strategy_walk_forward_result
from tests.test_offline_strategy_models import offline_strategy_rows_payload


def test_offline_strategy_walk_forward_engine_builds_anchored_splits() -> None:
    fixture = OfflineStrategyPipelineInput.model_validate(
        {"pipeline_id": "offline-strategy-test", "dataset_id": "offline-strategy-test", "ohlcv_rows": offline_strategy_rows_payload()}
    )
    result = build_offline_strategy_walk_forward_result(fixture, fixture.ohlcv_rows)
    assert len(result.splits) == 3
    assert result.readiness_status.value == "WALK_FORWARD_ANCHORED_READY"
