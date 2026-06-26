from __future__ import annotations

from collections import defaultdict

from stock_risk_mcp.feature_store_models import (
    FeatureStoreDatasetProfile,
    FeatureStoreFeatureRow,
    FeatureStoreLabelSpec,
    FeatureStorePipelineInput,
    FeatureStoreSplitMode,
    FeatureStoreSplitRole,
    FeatureStoreTrainingRow,
    FeatureStoreWalkForwardPlan,
    FeatureStoreWalkForwardSplit,
)


def _horizon_count(spec: FeatureStoreLabelSpec) -> int:
    digits = "".join(ch for ch in spec.label_horizon if ch.isdigit())
    return int(digits) if digits else 1


def build_feature_store_walk_forward_plan(
    pipeline_input: FeatureStorePipelineInput,
    feature_rows: list[FeatureStoreFeatureRow],
) -> FeatureStoreWalkForwardPlan:
    if pipeline_input.dataset_profile == FeatureStoreDatasetProfile.FULL_INTRADAY_PROFILE:
        raise ValueError("FULL_INTRADAY_PROFILE must remain blocked in tests and default flows")
    sorted_rows = sorted(feature_rows, key=lambda row: (row.feature_asof, row.instrument_id, row.row_id))
    max_horizon = max((_horizon_count(spec) for spec in pipeline_input.label_specs), default=1)
    count = len(sorted_rows)
    train_end = int(count * 0.7)
    validation_end = int(count * 0.85)
    purge = max_horizon
    embargo = max_horizon

    def _subset(start: int, end: int) -> list[FeatureStoreFeatureRow]:
        return sorted_rows[max(start, 0):max(end, 0)]

    train_rows = _subset(0, max(train_end - purge, 0))
    validation_rows = _subset(train_end + embargo, max(validation_end - purge, train_end + embargo))
    test_rows = _subset(validation_end + embargo, count)

    splits = [
        FeatureStoreWalkForwardSplit(
            split_id=f"{pipeline_input.dataset_id}-TRAIN-SPLIT",
            split_mode=pipeline_input.split_mode,
            split_role=FeatureStoreSplitRole.TRAIN,
            start_at=train_rows[0].feature_asof if train_rows else None,
            end_at=train_rows[-1].feature_asof if train_rows else None,
            row_ids=[row.row_id for row in train_rows],
            purge_window_count=purge,
            embargo_window_count=embargo,
        ),
        FeatureStoreWalkForwardSplit(
            split_id=f"{pipeline_input.dataset_id}-VALIDATION-SPLIT",
            split_mode=pipeline_input.split_mode,
            split_role=FeatureStoreSplitRole.VALIDATION,
            start_at=validation_rows[0].feature_asof if validation_rows else None,
            end_at=validation_rows[-1].feature_asof if validation_rows else None,
            row_ids=[row.row_id for row in validation_rows],
            purge_window_count=purge,
            embargo_window_count=embargo,
        ),
        FeatureStoreWalkForwardSplit(
            split_id=f"{pipeline_input.dataset_id}-TEST-SPLIT",
            split_mode=pipeline_input.split_mode,
            split_role=FeatureStoreSplitRole.TEST,
            start_at=test_rows[0].feature_asof if test_rows else None,
            end_at=test_rows[-1].feature_asof if test_rows else None,
            row_ids=[row.row_id for row in test_rows],
            purge_window_count=purge,
            embargo_window_count=embargo,
        ),
    ]
    return FeatureStoreWalkForwardPlan(
        plan_id=f"{pipeline_input.dataset_id}-WALK-FORWARD-PLAN",
        dataset_id=pipeline_input.dataset_id,
        dataset_profile=pipeline_input.dataset_profile,
        split_mode=pipeline_input.split_mode,
        splits=splits,
        max_label_horizon=f"{max_horizon}D",
    )


def assign_split_roles(
    feature_rows: list[FeatureStoreFeatureRow],
    walk_forward_plan: FeatureStoreWalkForwardPlan,
) -> dict[str, tuple[str, FeatureStoreSplitRole]]:
    assignments: dict[str, tuple[str, FeatureStoreSplitRole]] = {}
    for split in walk_forward_plan.splits:
        for row_id in split.row_ids:
            assignments[row_id] = (split.split_id, split.split_role)
    return assignments
