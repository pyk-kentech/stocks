from __future__ import annotations

import math
from collections import Counter, defaultdict

from stock_risk_mcp.feature_store_models import (
    FeatureStoreDatasetManifest,
    FeatureStoreFeatureRow,
    FeatureStoreGapEntry,
    FeatureStoreGapReport,
    FeatureStoreLeakageReport,
    FeatureStoreLabelDerivationMethod,
    FeatureStoreLabelDirection,
    FeatureStoreLabelHorizonPolicy,
    FeatureStoreLabelRow,
    FeatureStoreLabelSpec,
    FeatureStorePipelineInput,
    FeatureStorePriceBar,
    FeatureStoreReadinessStatus,
    FeatureStoreSafetyReport,
    FeatureStoreSourceKind,
    FeatureStoreSplitRole,
    FeatureStoreTrainingDatasetManifest,
    FeatureStoreTrainingReadinessReport,
    FeatureStoreTrainingRow,
)


def _gap(dataset_id: str, suffix: str, category: str, severity: str, message: str) -> FeatureStoreGapEntry:
    return FeatureStoreGapEntry(
        gap_id=f"{dataset_id}-{suffix}",
        gap_category=category,
        severity=severity,
        message=message,
    )


def _horizon_sessions(spec: FeatureStoreLabelSpec) -> int:
    digits = "".join(ch for ch in spec.label_horizon if ch.isdigit())
    return int(digits) if digits else 1


def _bars_for_instrument(price_history_rows: list[FeatureStorePriceBar]) -> dict[str, list[FeatureStorePriceBar]]:
    grouped: dict[str, list[FeatureStorePriceBar]] = defaultdict(list)
    for bar in price_history_rows:
        grouped[bar.instrument_id].append(bar)
    for bars in grouped.values():
        bars.sort(key=lambda item: item.observed_at)
    return grouped


def _find_anchor_bar(feature_row: FeatureStoreFeatureRow, bars: list[FeatureStorePriceBar], spec: FeatureStoreLabelSpec):
    eligible = [bar for bar in bars if bar.available_at <= feature_row.feature_asof]
    if not eligible:
        return None, "ANCHOR_PRICE_UNAVAILABLE"
    return eligible[-1], None


def _derive_label(feature_row: FeatureStoreFeatureRow, bars: list[FeatureStorePriceBar], spec: FeatureStoreLabelSpec, dataset_id: str):
    if spec.label_horizon_policy == FeatureStoreLabelHorizonPolicy.UNKNOWN_HORIZON_POLICY:
        return None, "UNKNOWN_HORIZON_POLICY"
    if spec.derivation_method == FeatureStoreLabelDerivationMethod.LOCAL_PRICE_HISTORY_OUTLIER_CONTINUATION:
        if feature_row.feature_namespace.value not in {"domestic.outlier", "domestic.rank"} and not any("outlier" in key.lower() or "rank" in key.lower() for key in feature_row.feature_values):
            return None, "OUTLIER_CONTEXT_MISSING"

    anchor_bar, anchor_gap = _find_anchor_bar(feature_row, bars, spec)
    if anchor_gap:
        return None, anchor_gap
    future_bars = [bar for bar in bars if bar.observed_at > anchor_bar.observed_at]
    horizon = _horizon_sessions(spec)
    if len(future_bars) < horizon:
        return None, "LABEL_GAP"
    window_bars = future_bars[:horizon]
    anchor_price = anchor_bar.close_price
    end_bar = window_bars[-1]
    value = None
    unit = "PERCENT"
    quality_flags: list[str] = []
    if spec.derivation_method == FeatureStoreLabelDerivationMethod.LOCAL_PRICE_HISTORY_FORWARD_RETURN:
        value = (end_bar.close_price / anchor_price) - 1.0
    elif spec.derivation_method == FeatureStoreLabelDerivationMethod.LOCAL_PRICE_HISTORY_FORWARD_LOG_RETURN:
        value = math.log(end_bar.close_price / anchor_price)
        unit = "LOG_RETURN"
    elif spec.derivation_method == FeatureStoreLabelDerivationMethod.LOCAL_PRICE_HISTORY_MFE:
        highs = [bar.high_price for bar in window_bars if bar.high_price is not None]
        if highs:
            value = (max(highs) / anchor_price) - 1.0
        else:
            value = max((bar.close_price / anchor_price) - 1.0 for bar in window_bars)
            quality_flags.append("CLOSE_ONLY_EXCURSION")
    elif spec.derivation_method == FeatureStoreLabelDerivationMethod.LOCAL_PRICE_HISTORY_MAE:
        lows = [bar.low_price for bar in window_bars if bar.low_price is not None]
        if lows:
            value = (min(lows) / anchor_price) - 1.0
        else:
            value = min((bar.close_price / anchor_price) - 1.0 for bar in window_bars)
            quality_flags.append("CLOSE_ONLY_EXCURSION")
    elif spec.derivation_method == FeatureStoreLabelDerivationMethod.LOCAL_PRICE_HISTORY_VOL_ADJUSTED_RETURN:
        volatility = None
        for key, raw in feature_row.feature_values.items():
            if "volatility" in key.lower() and isinstance(raw, (int, float)) and raw:
                volatility = float(raw)
                break
        if volatility is None or volatility == 0:
            return None, "VOLATILITY_INPUT_GAP"
        value = ((end_bar.close_price / anchor_price) - 1.0) / volatility
        unit = "VOL_ADJ_RETURN"
    elif spec.derivation_method == FeatureStoreLabelDerivationMethod.LOCAL_PRICE_HISTORY_OUTLIER_CONTINUATION:
        value = (end_bar.close_price / anchor_price) - 1.0
        unit = "CONTINUATION_RETURN"
    else:
        return None, "UNSUPPORTED_DERIVATION"

    return FeatureStoreLabelRow(
        dataset_id=dataset_id,
        label_row_id=f"{feature_row.row_id}-{spec.label_name}-{spec.label_horizon}",
        row_id=feature_row.row_id,
        instrument_id=feature_row.instrument_id,
        label_name=spec.label_name,
        label_horizon=spec.label_horizon,
        label_horizon_policy=spec.label_horizon_policy,
        label_value=value,
        label_unit=unit,
        label_direction=spec.label_direction,
        label_window_start=window_bars[0].observed_at,
        label_window_end=end_bar.observed_at,
        label_observed_at=end_bar.observed_at,
        label_available_at=end_bar.available_at,
        label_input_source_kind=(
            feature_row.source_kind
            if feature_row.source_kind
            in {
                FeatureStoreSourceKind.V8_CAPTURED_KIWOOM_CHART_HISTORY,
                FeatureStoreSourceKind.V8_MANUAL_IMPORTED_KIWOOM_CHART_HISTORY,
                FeatureStoreSourceKind.LOCAL_PRICE_HISTORY_FIXTURE,
                FeatureStoreSourceKind.MANUAL_PRICE_HISTORY_FIXTURE,
            }
            else FeatureStoreSourceKind.LOCAL_PRICE_HISTORY_FIXTURE
        ),
        label_input_source_ref=anchor_bar.source_ref,
        derivation_method=spec.derivation_method,
        anchor_price=anchor_price,
        anchor_observed_at=anchor_bar.observed_at,
        anchor_available_at=anchor_bar.available_at,
        anchor_source_ref=anchor_bar.source_ref,
        anchor_price_policy=spec.anchor_price_policy,
        quality_flags=quality_flags,
    ), None


def build_feature_store_dataset(
    pipeline_input: FeatureStorePipelineInput,
    feature_rows: list[FeatureStoreFeatureRow],
    walk_forward_plan,
    split_assignments: dict[str, tuple[str, object]],
) -> tuple[list[FeatureStoreLabelRow], list[FeatureStoreTrainingRow], object, FeatureStoreDatasetManifest, FeatureStoreTrainingDatasetManifest, FeatureStoreTrainingReadinessReport, FeatureStoreSafetyReport, FeatureStoreGapReport]:
    price_bars = _bars_for_instrument(pipeline_input.price_history_rows)
    label_rows = list(pipeline_input.manual_label_rows)
    gap_entries: list[FeatureStoreGapEntry] = []
    blocked_rows: list[str] = []
    warning_rows: list[str] = []
    leakage_categories: list[str] = []

    for feature_row in feature_rows:
        if feature_row.available_at > feature_row.feature_asof:
            blocked_rows.append(feature_row.row_id)
            leakage_categories.append("FEATURE_AVAILABLE_AT_VIOLATION")
        for key in feature_row.feature_values:
            normalized = key.lower()
            if normalized in {"forward_return", "future_return", "mfe", "mae", "target", "label", "outcome"}:
                blocked_rows.append(feature_row.row_id)
                leakage_categories.append("LABEL_LIKE_FEATURE_NAME")
        for spec in pipeline_input.label_specs:
            if any(label.row_id == feature_row.row_id and label.label_name == spec.label_name and label.label_horizon == spec.label_horizon for label in label_rows):
                continue
            derived, reason = _derive_label(feature_row, price_bars.get(feature_row.instrument_id, []), spec, pipeline_input.dataset_id)
            if derived is not None:
                if derived.anchor_available_at and derived.anchor_available_at > feature_row.feature_asof:
                    blocked_rows.append(feature_row.row_id)
                    leakage_categories.append("ANCHOR_AVAILABLE_AT_VIOLATION")
                    continue
                if derived.anchor_observed_at and derived.label_window_start <= derived.anchor_observed_at:
                    blocked_rows.append(feature_row.row_id)
                    leakage_categories.append("LABEL_WINDOW_START_VIOLATION")
                    continue
                if derived.label_available_at <= feature_row.feature_asof:
                    blocked_rows.append(feature_row.row_id)
                    leakage_categories.append("LABEL_AVAILABLE_AT_VIOLATION")
                    continue
                label_rows.append(derived)
            else:
                gap_entries.append(_gap(pipeline_input.dataset_id, f"{feature_row.row_id}-{spec.label_name}-{spec.label_horizon}", "LABEL_GAP", "WARNING", reason or "label gap"))

    labels_by_row: dict[str, list[FeatureStoreLabelRow]] = defaultdict(list)
    for label in label_rows:
        labels_by_row[label.row_id].append(label)

    training_rows: list[FeatureStoreTrainingRow] = []
    row_count_by_split: Counter[str] = Counter()
    label_count_by_horizon: Counter[str] = Counter()
    blocked_row_id_set = set(blocked_rows)

    for feature_row in feature_rows:
        split_id, split_role = split_assignments.get(
            feature_row.row_id,
            (f"{pipeline_input.dataset_id}-EXCLUDED", FeatureStoreSplitRole.EXCLUDED),
        )
        attached_labels = labels_by_row.get(feature_row.row_id, [])
        label_values = {f"{label.label_name}_{label.label_horizon}": label.label_value for label in attached_labels}
        label_gap_reasons = []
        if not attached_labels and pipeline_input.label_specs:
            label_gap_reasons.append("LABEL_GAP")
        blocked = feature_row.row_id in blocked_row_id_set
        if blocked and split_role != FeatureStoreSplitRole.EXCLUDED:
            split_role = FeatureStoreSplitRole.EXCLUDED
        training_rows.append(
            FeatureStoreTrainingRow(
                dataset_id=pipeline_input.dataset_id,
                training_row_id=f"{feature_row.row_id}-TRAINING",
                row_id=feature_row.row_id,
                instrument_id=feature_row.instrument_id,
                split_id=split_id,
                split_role=split_role,
                label_row_ids=[label.label_row_id for label in attached_labels],
                label_values=label_values,
                labeled=bool(attached_labels),
                blocked_from_training=blocked,
                blocking_reasons=["BLOCKED_LEAKAGE"] if blocked else [],
                label_gap_reasons=label_gap_reasons,
            )
        )
        row_count_by_split[split_role.value] += 1
        for label in attached_labels:
            label_count_by_horizon[label.label_horizon] += 1

    labeled_count = sum(1 for row in training_rows if row.labeled and not row.blocked_from_training)
    unlabeled_count = sum(1 for row in training_rows if not row.labeled and not row.blocked_from_training)
    blocked_count = sum(1 for row in training_rows if row.blocked_from_training)
    if blocked_count:
        readiness = FeatureStoreReadinessStatus.BLOCKED_LEAKAGE
    elif labeled_count:
        readiness = FeatureStoreReadinessStatus.LABELED_DATASET_READY
    elif unlabeled_count:
        readiness = FeatureStoreReadinessStatus.UNLABELED_DATASET_READY
    else:
        readiness = FeatureStoreReadinessStatus.LABEL_GAP

    leakage_report = FeatureStoreLeakageReport(
        report_id=f"{pipeline_input.dataset_id}-LEAKAGE-REPORT",
        dataset_id=pipeline_input.dataset_id,
        readiness_status=readiness,
        blocked_row_ids=sorted(blocked_row_id_set),
        warning_row_ids=warning_rows,
        leakage_categories=sorted(set(leakage_categories)),
        findings=sorted(set(leakage_categories + [gap.gap_category for gap in gap_entries if gap.gap_category == "LABEL_GAP"])),
    )
    unique_source_refs = {
        source.source_id: source
        for row in feature_rows
        for source in row.source_refs
    }

    dataset_manifest = FeatureStoreDatasetManifest(
        dataset_id=pipeline_input.dataset_id,
        schema_version=pipeline_input.schema_version,
        created_at=max((row.feature_asof for row in feature_rows), default=None) or pipeline_input.audit_records[0].created_at,
        generator_version=pipeline_input.generator_version,
        dataset_profile=pipeline_input.dataset_profile,
        feature_schema_ref=f"{pipeline_input.dataset_id}-FEATURE-SCHEMA",
        row_count=len(feature_rows),
        source_refs=sorted(unique_source_refs.values(), key=lambda item: item.source_id),
        freshness_summary="STALE_ROWS_PRESENT" if any(row.row_id in blocked_rows for row in feature_rows) else "FEATURE_ROWS_FRESH_ENOUGH",
        completeness_summary="FEATURE_ROWS_PRESENT" if feature_rows else "FEATURE_ROWS_MISSING",
        readiness_status=FeatureStoreReadinessStatus.FEATURE_ROWS_READY if feature_rows else FeatureStoreReadinessStatus.DATA_GAP,
    )
    training_manifest = FeatureStoreTrainingDatasetManifest(
        dataset_id=pipeline_input.dataset_id,
        schema_version=pipeline_input.schema_version,
        created_at=dataset_manifest.created_at,
        generator_version=pipeline_input.generator_version,
        dataset_profile=pipeline_input.dataset_profile,
        feature_schema_ref=dataset_manifest.feature_schema_ref,
        row_count=len(feature_rows),
        source_refs=dataset_manifest.source_refs,
        freshness_summary=dataset_manifest.freshness_summary,
        completeness_summary=dataset_manifest.completeness_summary,
        readiness_status=readiness,
        training_row_count=len(training_rows),
        labeled_row_count=labeled_count,
        unlabeled_row_count=unlabeled_count,
        row_count_by_split=dict(row_count_by_split),
        label_count_by_horizon=dict(label_count_by_horizon),
        label_coverage_summary=f"Labeled rows: {labeled_count}; unlabeled rows: {unlabeled_count}",
        split_coverage_summary=f"Splits: {dict(row_count_by_split)}",
        lineage_summary=f"Source kinds: {sorted({row.source_kind.value for row in feature_rows})}",
        leakage_summary=f"Blocked rows: {blocked_count}; categories: {sorted(set(leakage_categories))}",
        survivorship_readiness_summary="RESEARCH_ONLY_IF_V71_CONTEXT_MISSING" if not any(row.source_kind.value == "V7_POINT_IN_TIME_UNIVERSE_CONTEXT" for row in feature_rows) else "V71_CONTEXT_PRESENT",
        backend_capability_summary="BACKEND_REPORT_REQUIRED",
        materialization_summary="MATERIALIZATION_PENDING",
    )
    training_readiness_report = FeatureStoreTrainingReadinessReport(
        report_id=f"{pipeline_input.dataset_id}-TRAINING-READINESS-REPORT",
        dataset_id=pipeline_input.dataset_id,
        readiness_status=readiness,
        findings=sorted(set([gap.gap_category for gap in gap_entries] + leakage_categories)) or [readiness.value],
    )
    safety_report = FeatureStoreSafetyReport(
        report_id=f"{pipeline_input.dataset_id}-SAFETY-REPORT",
        findings=[
            "REPORT_ONLY",
            "NO_PROVIDER_CALLS",
            "NO_ENV_READ",
            "NO_ACCOUNT_ORDER_PATH",
            "NO_MODEL_TRAINING",
            "NO_PAPER_TRADING",
        ],
    )
    gap_entries.append(_gap(pipeline_input.dataset_id, "DATASET-REPORT", "REPORT_GENERATED", "REPORT_ONLY", "feature store dataset report generated"))
    gap_report = FeatureStoreGapReport(
        report_id=f"{pipeline_input.dataset_id}-DATASET-GAP-REPORT",
        dataset_id=pipeline_input.dataset_id,
        readiness_status=readiness,
        gap_entries=gap_entries,
    )
    return label_rows, training_rows, leakage_report, dataset_manifest, training_manifest, training_readiness_report, safety_report, gap_report
