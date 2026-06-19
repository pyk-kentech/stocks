from __future__ import annotations

from collections import Counter
from datetime import date

from stock_risk_mcp.historical_dataset_validation_guard import (
    validate_historical_dataset_validation_feature_outcome_boundary,
    validate_historical_dataset_validation_metadata_safety,
    validate_historical_dataset_validation_split_integrity,
)
from stock_risk_mcp.historical_dataset_validation_models import (
    HistoricalDatasetCoverageReport,
    HistoricalDatasetLabelDistributionReport,
    HistoricalDatasetLeakageAuditReport,
    HistoricalDatasetSplitManifest,
    HistoricalDatasetSplitRecordRef,
    HistoricalDatasetValidationGapCategory,
    HistoricalDatasetValidationGapEntry,
    HistoricalDatasetValidationGapReport,
    HistoricalDatasetValidationInput,
    HistoricalDatasetValidationReport,
    HistoricalDatasetValidationSafetyReport,
)
from stock_risk_mcp.strategy_track_models import StrategyTrack


def build_historical_dataset_validation(
    validation_input: HistoricalDatasetValidationInput,
) -> HistoricalDatasetValidationInput:
    gap_entries: list[HistoricalDatasetValidationGapEntry] = []
    warnings: list[str] = []
    valid_records = []
    clean_records = []

    records = list(validation_input.dataset_records)
    if not records:
        gap_entries.append(
            _gap_entry(
                "missing-dataset-record",
                HistoricalDatasetValidationGapCategory.VALIDATION_MISSING_DATASET_RECORD,
                "BLOCKING",
                "missing dataset record",
            )
        )

    for record in records:
        valid_records.append(record)
        _collect_validation_gaps(record, gap_entries)
        _collect_leakage_gaps(record, gap_entries)
        if _record_is_leakage_clean(record):
            clean_records.append(record)

    for audit in validation_input.audit_records:
        try:
            validate_historical_dataset_validation_metadata_safety(
                {
                    "operator_context": audit.operator_context,
                    "source_path": audit.source_path,
                },
                context="historical dataset validation",
            )
        except ValueError as exc:
            gap_entries.append(_unsafe_gap(str(exc)))

    if validation_input.split_manifest.record_refs:
        try:
            validate_historical_dataset_validation_split_integrity(
                validation_input.split_manifest.model_dump(mode="json"),
                context="historical dataset validation",
            )
        except ValueError as exc:
            gap_entries.append(_split_gap(str(exc)))

    validation_report = _build_validation_report(validation_input, records, gap_entries, warnings)
    leakage_audit_report = _build_leakage_audit_report(validation_input, records, clean_records, gap_entries, warnings)
    split_manifest = _build_split_manifest(validation_input, records, gap_entries)
    coverage_report = _build_coverage_report(validation_input, records)
    label_distribution_report = _build_label_distribution_report(validation_input, records, split_manifest)
    gap_report = _build_gap_report(validation_input, gap_entries)
    safety_report = HistoricalDatasetValidationSafetyReport.model_validate(
        validation_input.validation_safety_report.model_dump(mode="json")
    )

    return validation_input.model_copy(
        update={
            "validation_report": validation_report,
            "leakage_audit_report": leakage_audit_report,
            "split_manifest": split_manifest,
            "coverage_report": coverage_report,
            "label_distribution_report": label_distribution_report,
            "validation_gap_report": gap_report,
            "validation_safety_report": safety_report,
        }
    )


def _collect_validation_gaps(record, gap_entries: list[HistoricalDatasetValidationGapEntry]) -> None:
    if record is None:
        gap_entries.append(
            _gap_entry(
                "missing-input",
                HistoricalDatasetValidationGapCategory.VALIDATION_MISSING_INPUT,
                "BLOCKING",
                "missing validation input record",
            )
        )
        return
    if not getattr(record, "feature_block", None):
        gap_entries.append(
            _gap_entry(
                f"missing-feature-{getattr(record, 'record_id', 'UNKNOWN')}",
                HistoricalDatasetValidationGapCategory.VALIDATION_MISSING_FEATURE_BLOCK,
                "BLOCKING",
                f"missing feature block for record {getattr(record, 'record_id', 'UNKNOWN')}",
            )
        )
    if not getattr(record, "outcome_block", None):
        gap_entries.append(
            _gap_entry(
                f"missing-outcome-{getattr(record, 'record_id', 'UNKNOWN')}",
                HistoricalDatasetValidationGapCategory.VALIDATION_MISSING_OUTCOME_BLOCK,
                "BLOCKING",
                f"missing outcome block for record {getattr(record, 'record_id', 'UNKNOWN')}",
            )
        )
    if not getattr(record, "source_manifest_ids", []):
        gap_entries.append(
            _gap_entry(
                f"missing-lineage-{record.record_id}",
                HistoricalDatasetValidationGapCategory.VALIDATION_MISSING_LINEAGE,
                "REPORT_ONLY",
                f"missing lineage for record {record.record_id}",
            )
        )
    if not getattr(record, "replay_window_id", None):
        gap_entries.append(
            _gap_entry(
                f"missing-replay-window-id-{record.record_id}",
                HistoricalDatasetValidationGapCategory.VALIDATION_MISSING_REPLAY_WINDOW_ID,
                "BLOCKING",
                f"missing replay window id for record {record.record_id}",
            )
        )
    if not getattr(record, "source_manifest_ids", []):
        gap_entries.append(
            _gap_entry(
                f"missing-source-manifest-{record.record_id}",
                HistoricalDatasetValidationGapCategory.VALIDATION_MISSING_SOURCE_MANIFEST_ID,
                "BLOCKING",
                f"missing source manifest id for record {record.record_id}",
            )
        )
    if getattr(record, "strategy_track", None) != StrategyTrack.DOMESTIC_KR:
        gap_entries.append(
            _gap_entry(
                f"unsupported-track-{record.record_id}",
                HistoricalDatasetValidationGapCategory.VALIDATION_UNSUPPORTED_TRACK,
                "BLOCKING",
                f"unsupported strategy track for record {record.record_id}",
            )
        )
    if getattr(record, "market", None) != "KRX":
        gap_entries.append(
            _gap_entry(
                f"unsupported-market-{record.record_id}",
                HistoricalDatasetValidationGapCategory.VALIDATION_UNSUPPORTED_MARKET,
                "BLOCKING",
                f"unsupported market for record {record.record_id}",
            )
        )


def _collect_leakage_gaps(record, gap_entries: list[HistoricalDatasetValidationGapEntry]) -> None:
    feature_block = getattr(record, "feature_block", None)
    if feature_block is None:
        return
    try:
        validate_historical_dataset_validation_feature_outcome_boundary(
            {"feature_block": feature_block},
            context="historical dataset validation",
        )
    except ValueError as exc:
        gap_entries.append(_leakage_gap(record.record_id, str(exc)))


def _record_is_leakage_clean(record) -> bool:
    feature_block = getattr(record, "feature_block", None)
    if feature_block is None:
        return False
    try:
        validate_historical_dataset_validation_feature_outcome_boundary(
            {"feature_block": feature_block},
            context="historical dataset validation",
        )
        return True
    except ValueError:
        return False


def _build_validation_report(validation_input, records, gap_entries, warnings):
    blocking_gap_count = sum(1 for gap in gap_entries if gap.severity == "BLOCKING")
    valid_record_count = sum(
        1
        for record in records
        if getattr(record, "feature_block", None)
        and getattr(record, "outcome_block", None)
        and getattr(record, "source_manifest_ids", [])
        and getattr(record, "replay_window_id", None)
    )
    return HistoricalDatasetValidationReport.model_validate(
        {
            "validation_report_id": validation_input.validation_report.validation_report_id,
            "validation_input_id": validation_input.validation_input_id,
            "record_count": len(records),
            "valid_record_count": valid_record_count,
            "missing_lineage_count": sum(1 for record in records if not getattr(record, "source_manifest_ids", [])),
            "missing_feature_count": sum(1 for record in records if not getattr(record, "feature_block", None)),
            "missing_outcome_count": sum(1 for record in records if not getattr(record, "outcome_block", None)),
            "blocked_count": blocking_gap_count,
            "warning_count": len(warnings),
            "warnings": warnings,
            "training_ready_approved": False,
            "source_manifest_ids": validation_input.dataset_export_manifest.source_manifest_ids,
            "source_audit_record_ids": validation_input.dataset_export_manifest.source_audit_record_ids,
            "provider_provenance_ids": validation_input.dataset_export_manifest.provider_provenance_ids,
        }
    )


def _build_leakage_audit_report(validation_input, records, clean_records, gap_entries, warnings):
    category_counts = Counter(gap.gap_category for gap in gap_entries)
    leakage_gaps = [
        gap
        for gap in gap_entries
        if gap.gap_category
        in {
            HistoricalDatasetValidationGapCategory.VALIDATION_FEATURE_OUTCOME_LEAKAGE_DETECTED,
            HistoricalDatasetValidationGapCategory.VALIDATION_OUTCOME_LABEL_IN_FEATURES_DETECTED,
            HistoricalDatasetValidationGapCategory.VALIDATION_FORWARD_RETURN_IN_FEATURES_DETECTED,
            HistoricalDatasetValidationGapCategory.VALIDATION_MFE_MAE_IN_FEATURES_DETECTED,
            HistoricalDatasetValidationGapCategory.VALIDATION_POST_ANCHOR_ACTUAL_IN_FEATURES_DETECTED,
            HistoricalDatasetValidationGapCategory.VALIDATION_SCANNER_INPUT_MUTATION_DETECTED,
        }
    ]
    affected_ids = []
    for gap in leakage_gaps:
        suffix = gap.gap_id.rsplit("-", 1)[-1]
        if suffix and suffix not in {"FEATURE", "OUTCOME"}:
            affected_ids.append(suffix)
    return HistoricalDatasetLeakageAuditReport.model_validate(
        {
            "leakage_audit_report_id": validation_input.leakage_audit_report.leakage_audit_report_id,
            "validation_input_id": validation_input.validation_input_id,
            "audited_record_count": len(records),
            "clean_record_count": len(clean_records),
            "blocked_record_count": len(records) - len(clean_records),
            "warning_count": len(warnings),
            "warnings": warnings,
            "outcome_label_in_features_count": category_counts[HistoricalDatasetValidationGapCategory.VALIDATION_OUTCOME_LABEL_IN_FEATURES_DETECTED],
            "forward_return_in_features_count": category_counts[HistoricalDatasetValidationGapCategory.VALIDATION_FORWARD_RETURN_IN_FEATURES_DETECTED],
            "max_excursion_in_features_count": category_counts[HistoricalDatasetValidationGapCategory.VALIDATION_MFE_MAE_IN_FEATURES_DETECTED],
            "post_anchor_actual_value_in_features_count": category_counts[HistoricalDatasetValidationGapCategory.VALIDATION_POST_ANCHOR_ACTUAL_IN_FEATURES_DETECTED],
            "scanner_input_mutation_risk_count": category_counts[HistoricalDatasetValidationGapCategory.VALIDATION_SCANNER_INPUT_MUTATION_DETECTED],
            "feature_outcome_leakage_absent": not leakage_gaps,
            "affected_record_ids": affected_ids,
            "source_manifest_ids": validation_input.dataset_export_manifest.source_manifest_ids,
            "source_audit_record_ids": validation_input.dataset_export_manifest.source_audit_record_ids,
            "provider_provenance_ids": validation_input.dataset_export_manifest.provider_provenance_ids,
        }
    )


def _build_split_manifest(validation_input, records, gap_entries):
    sorted_records = sorted(records, key=lambda record: (record.replay_session_date, record.record_id))
    if len(sorted_records) < 3:
        gap_entries.append(
            _gap_entry(
                "split-not-chronological-too-few",
                HistoricalDatasetValidationGapCategory.VALIDATION_SPLIT_NOT_CHRONOLOGICAL,
                "BLOCKING",
                "too few records for chronological train/validation/test split",
            )
        )
        return HistoricalDatasetSplitManifest.model_validate(
            {
                "split_manifest_id": validation_input.split_manifest.split_manifest_id,
                "validation_input_id": validation_input.validation_input_id,
                "split_config_id": validation_input.split_config.split_config_id,
                "split_policy": "CHRONOLOGICAL",
                "chronological": True,
                "random_shuffle_used": False,
                "train_record_count": 0,
                "validation_record_count": 0,
                "test_record_count": 0,
                "train_symbol_count": 0,
                "validation_symbol_count": 0,
                "test_symbol_count": 0,
                "train_record_refs": [],
                "validation_record_refs": [],
                "test_record_refs": [],
                "record_refs": [],
                "source_manifest_ids": validation_input.dataset_export_manifest.source_manifest_ids,
                "source_audit_record_ids": validation_input.dataset_export_manifest.source_audit_record_ids,
                "provider_provenance_ids": validation_input.dataset_export_manifest.provider_provenance_ids,
            }
        )
    train_count = max(1, int(len(sorted_records) * validation_input.split_config.train_ratio))
    validation_count = max(1, int(len(sorted_records) * validation_input.split_config.validation_ratio))
    if train_count + validation_count >= len(sorted_records):
        train_count = len(sorted_records) - 2
        validation_count = 1
    test_count = len(sorted_records) - train_count - validation_count
    if train_count < 1 or validation_count < 1 or test_count < 1:
        gap_entries.append(
            _gap_entry(
                "split-not-chronological-invalid-counts",
                HistoricalDatasetValidationGapCategory.VALIDATION_SPLIT_NOT_CHRONOLOGICAL,
                "BLOCKING",
                "chronological split produced invalid partition counts",
            )
        )
        return HistoricalDatasetSplitManifest.model_validate(
            {
                "split_manifest_id": validation_input.split_manifest.split_manifest_id,
                "validation_input_id": validation_input.validation_input_id,
                "split_config_id": validation_input.split_config.split_config_id,
                "split_policy": "CHRONOLOGICAL",
                "chronological": True,
                "random_shuffle_used": False,
                "train_record_count": 0,
                "validation_record_count": 0,
                "test_record_count": 0,
                "train_symbol_count": 0,
                "validation_symbol_count": 0,
                "test_symbol_count": 0,
                "train_record_refs": [],
                "validation_record_refs": [],
                "test_record_refs": [],
                "record_refs": [],
                "source_manifest_ids": validation_input.dataset_export_manifest.source_manifest_ids,
                "source_audit_record_ids": validation_input.dataset_export_manifest.source_audit_record_ids,
                "provider_provenance_ids": validation_input.dataset_export_manifest.provider_provenance_ids,
            }
        )
    train_records = sorted_records[:train_count]
    validation_records = sorted_records[train_count:train_count + validation_count]
    test_records = sorted_records[train_count + validation_count:]
    if len({record.record_id for record in sorted_records}) != len(sorted_records):
        gap_entries.append(
            _gap_entry(
                "split-record-duplicated",
                HistoricalDatasetValidationGapCategory.VALIDATION_SPLIT_RECORD_DUPLICATED,
                "BLOCKING",
                "duplicated split record detected",
            )
        )
    train_refs = [_record_ref(record, "TRAIN", index + 1) for index, record in enumerate(train_records)]
    validation_refs = [_record_ref(record, "VALIDATION", index + 1) for index, record in enumerate(validation_records)]
    test_refs = [_record_ref(record, "TEST", index + 1) for index, record in enumerate(test_records)]
    all_refs = [*train_refs, *validation_refs, *test_refs]
    try:
        validate_historical_dataset_validation_split_integrity(
            {
                "allow_random_shuffle": False,
                "record_refs": [ref.model_dump(mode="json") for ref in all_refs],
            },
            context="historical dataset validation",
        )
    except ValueError as exc:
        gap_entries.append(_split_gap(str(exc)))
    return HistoricalDatasetSplitManifest.model_validate(
        {
            "split_manifest_id": validation_input.split_manifest.split_manifest_id,
            "validation_input_id": validation_input.validation_input_id,
            "split_config_id": validation_input.split_config.split_config_id,
            "split_policy": "CHRONOLOGICAL",
            "chronological": True,
            "random_shuffle_used": False,
            "train_record_count": len(train_refs),
            "validation_record_count": len(validation_refs),
            "test_record_count": len(test_refs),
            "train_symbol_count": len({record.symbol for record in train_records}),
            "validation_symbol_count": len({record.symbol for record in validation_records}),
            "test_symbol_count": len({record.symbol for record in test_records}),
            "train_date_range_start": train_records[0].replay_session_date,
            "train_date_range_end": train_records[-1].replay_session_date,
            "validation_date_range_start": validation_records[0].replay_session_date,
            "validation_date_range_end": validation_records[-1].replay_session_date,
            "test_date_range_start": test_records[0].replay_session_date,
            "test_date_range_end": test_records[-1].replay_session_date,
            "train_label_distribution": _label_counts(train_records),
            "validation_label_distribution": _label_counts(validation_records),
            "test_label_distribution": _label_counts(test_records),
            "train_record_refs": [ref.model_dump(mode="json") for ref in train_refs],
            "validation_record_refs": [ref.model_dump(mode="json") for ref in validation_refs],
            "test_record_refs": [ref.model_dump(mode="json") for ref in test_refs],
            "record_refs": [ref.model_dump(mode="json") for ref in all_refs],
            "source_manifest_ids": validation_input.dataset_export_manifest.source_manifest_ids,
            "source_audit_record_ids": validation_input.dataset_export_manifest.source_audit_record_ids,
            "provider_provenance_ids": validation_input.dataset_export_manifest.provider_provenance_ids,
        }
    )


def _build_coverage_report(validation_input, records):
    symbols = [record.symbol for record in records]
    markets = [record.market for record in records]
    tracks = [record.strategy_track.value if hasattr(record.strategy_track, "value") else str(record.strategy_track) for record in records]
    return HistoricalDatasetCoverageReport.model_validate(
        {
            "coverage_report_id": validation_input.coverage_report.coverage_report_id,
            "validation_input_id": validation_input.validation_input_id,
            "record_count": len(records),
            "symbol_count": len(set(symbols)),
            "market_count": len(set(markets)),
            "strategy_track_count": len(set(tracks)),
            "earliest_replay_anchor_date": min((record.replay_session_date for record in records), default=None),
            "latest_replay_anchor_date": max((record.replay_session_date for record in records), default=None),
            "symbols": sorted(set(symbols)),
            "markets": sorted(set(markets)),
            "strategy_tracks": sorted(set(tracks)),
            "records_by_symbol": dict(Counter(symbols)),
            "records_by_market": dict(Counter(markets)),
            "records_by_strategy_track": dict(Counter(tracks)),
            "missing_feature_count": sum(1 for record in records if not getattr(record, "feature_block", None)),
            "missing_outcome_count": sum(1 for record in records if not getattr(record, "outcome_block", None)),
            "missing_lineage_count": sum(1 for record in records if not getattr(record, "source_manifest_ids", [])),
            "source_manifest_ids": validation_input.dataset_export_manifest.source_manifest_ids,
            "source_audit_record_ids": validation_input.dataset_export_manifest.source_audit_record_ids,
            "provider_provenance_ids": validation_input.dataset_export_manifest.provider_provenance_ids,
        }
    )


def _build_label_distribution_report(validation_input, records, split_manifest):
    label_counts = _label_counts(records)
    return HistoricalDatasetLabelDistributionReport.model_validate(
        {
            "label_distribution_report_id": validation_input.label_distribution_report.label_distribution_report_id,
            "validation_input_id": validation_input.validation_input_id,
            "record_count": len(records),
            "label_counts": label_counts,
            "label_percentages": _percentages(label_counts, len(records)),
            "split_label_counts": {
                "TRAIN": split_manifest.train_label_distribution,
                "VALIDATION": split_manifest.validation_label_distribution,
                "TEST": split_manifest.test_label_distribution,
            },
            "split_label_percentages": {
                "TRAIN": _percentages(split_manifest.train_label_distribution, split_manifest.train_record_count),
                "VALIDATION": _percentages(split_manifest.validation_label_distribution, split_manifest.validation_record_count),
                "TEST": _percentages(split_manifest.test_label_distribution, split_manifest.test_record_count),
            },
            "source_manifest_ids": validation_input.dataset_export_manifest.source_manifest_ids,
            "source_audit_record_ids": validation_input.dataset_export_manifest.source_audit_record_ids,
            "provider_provenance_ids": validation_input.dataset_export_manifest.provider_provenance_ids,
        }
    )


def _build_gap_report(validation_input, gap_entries):
    blocking_gap_count = sum(1 for gap in gap_entries if gap.severity == "BLOCKING")
    report_only_gap_count = sum(1 for gap in gap_entries if gap.severity != "BLOCKING")
    gap_status = "NO_GAPS"
    if blocking_gap_count:
        gap_status = "BLOCKING_GAPS"
    elif report_only_gap_count:
        gap_status = "REPORT_ONLY_GAPS"
    return HistoricalDatasetValidationGapReport.model_validate(
        {
            "gap_report_id": validation_input.validation_gap_report.gap_report_id,
            "validation_input_id": validation_input.validation_input_id,
            "gap_status": gap_status,
            "gap_categories": [gap.gap_category for gap in gap_entries if gap.gap_category is not None],
            "blocking_gap_count": blocking_gap_count,
            "report_only_gap_count": report_only_gap_count,
            "gaps": [gap.model_dump(mode="json") for gap in gap_entries],
            "source_manifest_ids": validation_input.dataset_export_manifest.source_manifest_ids,
            "source_audit_record_ids": validation_input.dataset_export_manifest.source_audit_record_ids,
            "provider_provenance_ids": validation_input.dataset_export_manifest.provider_provenance_ids,
        }
    )


def _record_ref(record, partition: str, index: int) -> HistoricalDatasetSplitRecordRef:
    return HistoricalDatasetSplitRecordRef.model_validate(
        {
            "record_ref_id": f"{partition}-RECORD-REF-{index}",
            "dataset_record_id": record.record_id,
            "split_partition": partition,
            "replay_anchor_date": record.replay_session_date,
            "symbol": record.symbol,
            "market": record.market,
        }
    )


def _gap_entry(gap_id: str, category: HistoricalDatasetValidationGapCategory, severity: str, message: str):
    return HistoricalDatasetValidationGapEntry.model_validate(
        {
            "gap_id": gap_id,
            "gap_category": category.value,
            "severity": severity,
            "message": message,
        }
    )


def _label_counts(records) -> dict[str, int]:
    counts = Counter()
    for record in records:
        outcome_block = getattr(record, "outcome_block", None)
        label = getattr(outcome_block, "outcome_label", None) if outcome_block is not None else None
        if label:
            counts[label] += 1
    return dict(counts)


def _percentages(counts: dict[str, int], total: int) -> dict[str, float]:
    if total <= 0:
        return {}
    return {label: count / total for label, count in counts.items()}


def _leakage_gap(record_id: str, message: str):
    lowered = message.lower()
    category = HistoricalDatasetValidationGapCategory.VALIDATION_FEATURE_OUTCOME_LEAKAGE_DETECTED
    if "outcome label" in lowered:
        category = HistoricalDatasetValidationGapCategory.VALIDATION_OUTCOME_LABEL_IN_FEATURES_DETECTED
    elif "forward return" in lowered:
        category = HistoricalDatasetValidationGapCategory.VALIDATION_FORWARD_RETURN_IN_FEATURES_DETECTED
    elif "max favorable" in lowered or "max adverse" in lowered:
        category = HistoricalDatasetValidationGapCategory.VALIDATION_MFE_MAE_IN_FEATURES_DETECTED
    elif "post-anchor" in lowered:
        category = HistoricalDatasetValidationGapCategory.VALIDATION_POST_ANCHOR_ACTUAL_IN_FEATURES_DETECTED
    elif "scanner input" in lowered:
        category = HistoricalDatasetValidationGapCategory.VALIDATION_SCANNER_INPUT_MUTATION_DETECTED
    return _gap_entry(f"leakage-{record_id}", category, "BLOCKING", message)


def _unsafe_gap(message: str):
    lowered = message.lower()
    category = HistoricalDatasetValidationGapCategory.VALIDATION_FEATURE_OUTCOME_LEAKAGE_DETECTED
    mapping = {
        "order": HistoricalDatasetValidationGapCategory.VALIDATION_ORDER_FIELD_DETECTED,
        "buy_sell": HistoricalDatasetValidationGapCategory.VALIDATION_BUY_SELL_WORDING_DETECTED,
        "remote": HistoricalDatasetValidationGapCategory.VALIDATION_REMOTE_SOURCE_NOT_ALLOWED,
        "api": HistoricalDatasetValidationGapCategory.VALIDATION_API_SOURCE_NOT_ALLOWED,
        "network": HistoricalDatasetValidationGapCategory.VALIDATION_NETWORK_SOURCE_NOT_ALLOWED,
        "provider": HistoricalDatasetValidationGapCategory.VALIDATION_PROVIDER_SOURCE_NOT_ALLOWED,
        "llm": HistoricalDatasetValidationGapCategory.VALIDATION_LLM_METADATA_NOT_ALLOWED,
        "gemini": HistoricalDatasetValidationGapCategory.VALIDATION_LLM_METADATA_NOT_ALLOWED,
        "training": HistoricalDatasetValidationGapCategory.VALIDATION_ML_TRAINING_TRIGGER_NOT_ALLOWED,
        "crawler": HistoricalDatasetValidationGapCategory.VALIDATION_CRAWLER_TRIGGER_NOT_ALLOWED,
        "live_prod": HistoricalDatasetValidationGapCategory.VALIDATION_LIVE_PROD_NOT_ALLOWED,
        "parquet": HistoricalDatasetValidationGapCategory.VALIDATION_PARQUET_NOT_ALLOWED,
    }
    for key, mapped in mapping.items():
        if key in lowered:
            category = mapped
            break
    return _gap_entry(f"unsafe-{category.value}", category, "BLOCKING", message)


def _split_gap(message: str):
    lowered = message.lower()
    category = HistoricalDatasetValidationGapCategory.VALIDATION_SPLIT_NOT_CHRONOLOGICAL
    if "duplicated" in lowered:
        category = HistoricalDatasetValidationGapCategory.VALIDATION_SPLIT_RECORD_DUPLICATED
    elif "overlap" in lowered:
        category = HistoricalDatasetValidationGapCategory.VALIDATION_SPLIT_PARTITION_OVERLAP
    return _gap_entry(f"split-{category.value}", category, "BLOCKING", message)
