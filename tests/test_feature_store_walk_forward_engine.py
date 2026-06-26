from stock_risk_mcp.feature_store_cache_engine import build_feature_store_cache
from stock_risk_mcp.feature_store_models import FeatureStorePipelineInput
from stock_risk_mcp.feature_store_walk_forward_engine import assign_split_roles, build_feature_store_walk_forward_plan
from tests.test_feature_store_models import feature_store_payload


def test_feature_store_walk_forward_plan_uses_purge_and_embargo():
    pipeline_input = FeatureStorePipelineInput.model_validate(feature_store_payload())
    feature_rows, *_ = build_feature_store_cache(pipeline_input)
    plan = build_feature_store_walk_forward_plan(pipeline_input, feature_rows)
    assignments = assign_split_roles(feature_rows, plan)

    assert plan.splits
    assert all(split.purge_window_count == 1 for split in plan.splits)
    assert all(split.embargo_window_count == 1 for split in plan.splits)
    assert assignments
