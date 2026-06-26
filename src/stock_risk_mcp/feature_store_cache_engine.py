from __future__ import annotations

from collections import Counter

from stock_risk_mcp.feature_store_guard import validate_feature_store_metadata_safety
from stock_risk_mcp.feature_store_models import (
    FeatureStoreCacheManifest,
    FeatureStoreCompletenessReport,
    FeatureStoreFeatureColumn,
    FeatureStoreFeatureRow,
    FeatureStoreFeatureSchema,
    FeatureStoreFreshnessReport,
    FeatureStoreGapEntry,
    FeatureStoreGapReport,
    FeatureStoreLineageRecord,
    FeatureStorePipelineInput,
    FeatureStoreReadinessStatus,
    FeatureStoreSourceRef,
)


def _gap(dataset_id: str, suffix: str, category: str, severity: str, message: str) -> FeatureStoreGapEntry:
    return FeatureStoreGapEntry(
        gap_id=f"{dataset_id}-{suffix}",
        gap_category=category,
        severity=severity,
        message=message,
    )


def build_feature_store_cache(
    pipeline_input: FeatureStorePipelineInput,
) -> tuple[list[FeatureStoreFeatureRow], FeatureStoreFeatureSchema, FeatureStoreCacheManifest, FeatureStoreCompletenessReport, FeatureStoreFreshnessReport, FeatureStoreGapReport]:
    for audit in pipeline_input.audit_records:
        validate_feature_store_metadata_safety(
            {"source_path": audit.source_path, "operator_context": audit.operator_context},
            context="feature store audit",
        )

    feature_rows: list[FeatureStoreFeatureRow] = []
    columns: dict[tuple[str, str], FeatureStoreFeatureColumn] = {}
    present_source_kinds = set()
    stale_row_ids: list[str] = []
    gaps: list[FeatureStoreGapEntry] = []

    for source in pipeline_input.source_feature_inputs:
        present_source_kinds.add(source.source_kind.value)
        if source.available_at > source.feature_asof:
            gaps.append(
                _gap(
                    pipeline_input.dataset_id,
                    f"{source.source_row_id}-AVAILABLE-AT",
                    "BLOCKED_LEAKAGE",
                    "BLOCKING",
                    "feature source available_at exceeds feature_asof",
                )
            )
            continue
        source_ref = FeatureStoreSourceRef.model_validate(source.source_ref.model_dump(mode="json"))
        lineage = FeatureStoreLineageRecord(
            lineage_id=f"{source.source_row_id}-LINEAGE",
            source_ref=source_ref,
            stage="CANONICAL_INPUT",
            source_available_at=source.available_at,
            feature_names=list(source.feature_values.keys()),
        )
        feature_rows.append(
            FeatureStoreFeatureRow(
                dataset_id=pipeline_input.dataset_id,
                row_id=source.source_row_id,
                instrument_id=source.instrument_id,
                market=source.market,
                currency=source.currency,
                feature_asof=source.feature_asof,
                available_at=source.available_at,
                snapshot_at=source.snapshot_at or source.feature_asof,
                feature_namespace=source.feature_namespace,
                feature_values=source.feature_values,
                feature_availability_map={name: source.available_at.isoformat() for name in source.feature_values},
                source_refs=[source_ref],
                lineage_records=[lineage],
                source_kind=source.source_kind,
            )
        )
        if (source.feature_asof - source.available_at).total_seconds() > 86400 * 10:
            stale_row_ids.append(source.source_row_id)
        for name, value in source.feature_values.items():
            dtype = type(value).__name__.upper() if value is not None else "NULL"
            columns[(source.feature_namespace.value, name)] = FeatureStoreFeatureColumn(
                column_name=name,
                namespace=source.feature_namespace,
                dtype=dtype,
                nullable=value is None,
                leakage_sensitive=False,
            )

    required_source_kinds = sorted({item.source_kind.value for item in pipeline_input.source_feature_inputs})
    missing_source_kinds = []
    if not feature_rows:
        missing_source_kinds = required_source_kinds
        gaps.append(_gap(pipeline_input.dataset_id, "NO-FEATURE-ROWS", "DATA_GAP", "BLOCKING", "no feature rows built"))

    readiness = FeatureStoreReadinessStatus.FEATURE_ROWS_READY if feature_rows and not gaps else FeatureStoreReadinessStatus.DATA_GAP
    schema = FeatureStoreFeatureSchema(
        schema_id=f"{pipeline_input.dataset_id}-FEATURE-SCHEMA",
        dataset_profile=pipeline_input.dataset_profile,
        columns=sorted(columns.values(), key=lambda item: (item.namespace.value, item.column_name)),
    )
    cache_manifest = FeatureStoreCacheManifest(
        manifest_id=f"{pipeline_input.dataset_id}-CACHE-MANIFEST",
        dataset_id=pipeline_input.dataset_id,
        dataset_profile=pipeline_input.dataset_profile,
        cache_root=pipeline_input.store_root,
        partition_spec=pipeline_input.partition_spec,
        cached_row_count=len(feature_rows),
        root_policy="SAFE_LOCAL_ROOT_ONLY",
    )
    completeness_report = FeatureStoreCompletenessReport(
        report_id=f"{pipeline_input.dataset_id}-COMPLETENESS-REPORT",
        required_source_kinds=required_source_kinds,
        present_source_kinds=sorted(present_source_kinds),
        missing_source_kinds=missing_source_kinds,
    )
    latest_asof = max((row.feature_asof for row in feature_rows), default=None)
    freshness_report = FeatureStoreFreshnessReport(
        report_id=f"{pipeline_input.dataset_id}-FRESHNESS-REPORT",
        stale_row_ids=stale_row_ids,
        latest_feature_asof=latest_asof,
    )
    gaps.append(_gap(pipeline_input.dataset_id, "CACHE-REPORT", "REPORT_GENERATED", "REPORT_ONLY", "feature store cache report generated"))
    gap_report = FeatureStoreGapReport(
        report_id=f"{pipeline_input.dataset_id}-CACHE-GAP-REPORT",
        dataset_id=pipeline_input.dataset_id,
        readiness_status=readiness,
        gap_entries=gaps,
    )
    return feature_rows, schema, cache_manifest, completeness_report, freshness_report, gap_report
