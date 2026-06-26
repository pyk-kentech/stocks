from __future__ import annotations

from pathlib import Path

from stock_risk_mcp.feature_store_backend import (
    build_feature_store_backend_capability_report,
    materialize_feature_store_manifest,
)
from stock_risk_mcp.feature_store_cache_engine import build_feature_store_cache
from stock_risk_mcp.feature_store_dataset_engine import build_feature_store_dataset
from stock_risk_mcp.feature_store_models import (
    FeatureStorePipelineInput,
    FeatureStorePipelineResult,
    FeatureStoreV7IntegrationReport,
    FeatureStoreV8IntegrationReport,
    FeatureStoreV9IntegrationReport,
)
from stock_risk_mcp.feature_store_walk_forward_engine import assign_split_roles, build_feature_store_walk_forward_plan


def _has_kind(feature_rows, kind: str) -> bool:
    return any(row.source_kind.value == kind for row in feature_rows)


def build_feature_store_pipeline(
    pipeline_input: FeatureStorePipelineInput,
    *,
    repo_root: Path,
) -> FeatureStorePipelineResult:
    feature_rows, feature_schema, cache_manifest, completeness_report, freshness_report, cache_gap_report = build_feature_store_cache(
        pipeline_input
    )
    walk_forward_plan = build_feature_store_walk_forward_plan(pipeline_input, feature_rows)
    split_assignments = assign_split_roles(feature_rows, walk_forward_plan)
    (
        label_rows,
        training_rows,
        leakage_report,
        dataset_manifest,
        training_manifest,
        training_readiness_report,
        safety_report,
        dataset_gap_report,
    ) = build_feature_store_dataset(pipeline_input, feature_rows, walk_forward_plan, split_assignments)
    backend_capability_report = build_feature_store_backend_capability_report(pipeline_input, repo_root=repo_root)
    materialization_result = materialize_feature_store_manifest(
        pipeline_input,
        training_manifest,
        training_rows,
        repo_root=repo_root,
        capability_report=backend_capability_report,
    )
    training_manifest = training_manifest.model_copy(
        update={
            "backend_capability_summary": ", ".join(f"{row.backend.value}:{row.status.value}" for row in backend_capability_report.rows),
            "materialization_summary": f"{materialization_result.selected_backend.value}:{materialization_result.status.value}",
        }
    )
    v7_report = FeatureStoreV7IntegrationReport(
        report_id=f"{pipeline_input.dataset_id}-V7-INTEGRATION-REPORT",
        v71_point_in_time_universe_ready=_has_kind(feature_rows, "V7_POINT_IN_TIME_UNIVERSE_CONTEXT"),
        v72_walk_forward_guard_ready=_has_kind(feature_rows, "V7_WALK_FORWARD_GUARD_CONTEXT"),
        v73_training_promotion_ready=_has_kind(feature_rows, "V7_TRAINING_PROMOTION_CONTEXT"),
        v710_position_sizing_context_ready=_has_kind(feature_rows, "V7_POSITION_SIZING_CONTEXT"),
        v711_event_risk_feature_ready=_has_kind(feature_rows, "V7_EVENT_RISK_CONTEXT"),
        v712_outlier_leadership_feature_ready=_has_kind(feature_rows, "V7_OUTLIER_ROUTING_CONTEXT"),
    )
    v8_report = FeatureStoreV8IntegrationReport(
        report_id=f"{pipeline_input.dataset_id}-V8-INTEGRATION-REPORT",
        domestic_snapshot_feature_ready=_has_kind(feature_rows, "V8_DOMESTIC_STOCK_SNAPSHOT"),
        local_kiwoom_chart_label_source_ready=bool(
            any(kind in {"V8_CAPTURED_KIWOOM_CHART_HISTORY", "V8_MANUAL_IMPORTED_KIWOOM_CHART_HISTORY"} for kind in {bar.source_ref.source_kind.value for bar in pipeline_input.price_history_rows})
        ),
        v8_lineage_source_coverage_ready=any(
            row.source_kind.value.startswith("V8_") for row in feature_rows
        ),
    )
    v9_report = FeatureStoreV9IntegrationReport(
        report_id=f"{pipeline_input.dataset_id}-V9-INTEGRATION-REPORT",
        macro_snapshot_feature_ready=_has_kind(feature_rows, "V9_MACRO_REGIME_SNAPSHOT"),
        regime_classification_feature_ready=_has_kind(feature_rows, "V9_REGIME_CLASSIFICATION"),
        macro_event_window_feature_ready=_has_kind(feature_rows, "V9_MACRO_EVENT_WINDOW"),
        macro_provider_gap_propagated=any("provider_gap" in key.lower() for row in feature_rows for key in row.feature_values),
    )
    final_gap_report = dataset_gap_report.model_copy(
        update={"gap_entries": cache_gap_report.gap_entries + dataset_gap_report.gap_entries}
    )
    return FeatureStorePipelineResult(
        feature_schema=feature_schema,
        feature_rows=feature_rows,
        label_rows=label_rows,
        training_rows=training_rows,
        cache_manifest=cache_manifest,
        dataset_manifest=dataset_manifest,
        training_dataset_manifest=training_manifest,
        walk_forward_plan=walk_forward_plan,
        leakage_report=leakage_report,
        completeness_report=completeness_report,
        freshness_report=freshness_report,
        backend_capability_report=backend_capability_report,
        v7_integration_report=v7_report,
        v8_integration_report=v8_report,
        v9_integration_report=v9_report,
        materialization_result=materialization_result,
        training_readiness_report=training_readiness_report,
        safety_report=safety_report,
        gap_report=final_gap_report,
    )
