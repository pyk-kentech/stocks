from __future__ import annotations

from stock_risk_mcp.offline_strategy_models import OfflineStrategyPipelineInput, OfflineStrategyReadinessStatus, OfflineStrategyTrainingLaunchPlan


def build_offline_strategy_training_plan(pipeline_input: OfflineStrategyPipelineInput, candidate_count: int) -> OfflineStrategyTrainingLaunchPlan:
    return OfflineStrategyTrainingLaunchPlan(
        plan_id=f"{pipeline_input.dataset_id}-OFFLINE-STRATEGY-TRAINING-PLAN",
        dataset_id=pipeline_input.dataset_id,
        readiness_status=OfflineStrategyReadinessStatus.TRAINING_PLAN_READY,
        candidate_count=candidate_count,
        primary_walk_forward_mode=pipeline_input.primary_walk_forward_mode,
        rolling_enabled=pipeline_input.rolling_enabled,
    )
