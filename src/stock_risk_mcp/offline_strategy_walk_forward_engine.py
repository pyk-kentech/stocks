from __future__ import annotations

from stock_risk_mcp.offline_strategy_models import (
    OfflineStrategyPipelineInput,
    OfflineStrategyReadinessStatus,
    OfflineStrategyWalkForwardMode,
    OfflineStrategyWalkForwardResult,
    OfflineStrategyWalkForwardSplit,
)


def build_offline_strategy_walk_forward_result(pipeline_input: OfflineStrategyPipelineInput, rows) -> OfflineStrategyWalkForwardResult:
    sorted_rows = sorted(rows, key=lambda row: (row.observed_at, row.instrument_id, row.row_id))
    count = len(sorted_rows)
    train_end = max(int(count * 0.6), 1)
    validation_end = max(int(count * 0.8), train_end + 1)
    purge = 1
    embargo = 1

    def row_ids(start: int, end: int) -> list[str]:
        return [row.row_id for row in sorted_rows[start:end]]

    splits = [
        OfflineStrategyWalkForwardSplit(
            split_id=f"{pipeline_input.dataset_id}-TRAIN-SPLIT",
            split_role="TRAIN",
            walk_forward_mode=pipeline_input.primary_walk_forward_mode,
            start_at=sorted_rows[0].observed_at if sorted_rows else None,
            end_at=sorted_rows[max(train_end - purge - 1, 0)].observed_at if sorted_rows and train_end - purge > 0 else None,
            row_ids=row_ids(0, max(train_end - purge, 0)),
            purge_window_count=purge,
            embargo_window_count=embargo,
        ),
        OfflineStrategyWalkForwardSplit(
            split_id=f"{pipeline_input.dataset_id}-VALIDATION-SPLIT",
            split_role="VALIDATION",
            walk_forward_mode=pipeline_input.primary_walk_forward_mode,
            start_at=sorted_rows[min(train_end + embargo, count - 1)].observed_at if sorted_rows and train_end + embargo < count else None,
            end_at=sorted_rows[max(validation_end - purge - 1, 0)].observed_at if sorted_rows and validation_end - purge > 0 else None,
            row_ids=row_ids(min(train_end + embargo, count), max(validation_end - purge, min(train_end + embargo, count))),
            purge_window_count=purge,
            embargo_window_count=embargo,
        ),
        OfflineStrategyWalkForwardSplit(
            split_id=f"{pipeline_input.dataset_id}-TEST-SPLIT",
            split_role="TEST",
            walk_forward_mode=pipeline_input.primary_walk_forward_mode,
            start_at=sorted_rows[min(validation_end + embargo, count - 1)].observed_at if sorted_rows and validation_end + embargo < count else None,
            end_at=sorted_rows[-1].observed_at if sorted_rows else None,
            row_ids=row_ids(min(validation_end + embargo, count), count),
            purge_window_count=purge,
            embargo_window_count=embargo,
        ),
    ]
    readiness = (
        OfflineStrategyReadinessStatus.WALK_FORWARD_ROLLING_RESEARCH_ONLY
        if pipeline_input.primary_walk_forward_mode == OfflineStrategyWalkForwardMode.ROLLING_CHRONOLOGICAL_WALK_FORWARD
        else OfflineStrategyReadinessStatus.WALK_FORWARD_ANCHORED_READY
    )
    return OfflineStrategyWalkForwardResult(
        result_id=f"{pipeline_input.dataset_id}-WALK-FORWARD-RESULT",
        dataset_id=pipeline_input.dataset_id,
        primary_mode=pipeline_input.primary_walk_forward_mode,
        readiness_status=readiness,
        splits=splits,
        rolling_secondary_only=pipeline_input.primary_walk_forward_mode == OfflineStrategyWalkForwardMode.ROLLING_CHRONOLOGICAL_WALK_FORWARD,
    )
