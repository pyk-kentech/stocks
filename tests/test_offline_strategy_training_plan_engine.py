from stock_risk_mcp.offline_strategy_models import OfflineStrategyPipelineInput
from stock_risk_mcp.offline_strategy_training_plan_engine import build_offline_strategy_training_plan
from tests.test_offline_strategy_models import offline_strategy_rows_payload


def test_offline_strategy_training_plan_engine_builds_plan() -> None:
    fixture = OfflineStrategyPipelineInput.model_validate(
        {"pipeline_id": "offline-strategy-test", "dataset_id": "offline-strategy-test", "ohlcv_rows": offline_strategy_rows_payload()}
    )
    plan = build_offline_strategy_training_plan(fixture, 4)
    assert plan.candidate_count == 4
    assert plan.plan_id.endswith("PLAN")
