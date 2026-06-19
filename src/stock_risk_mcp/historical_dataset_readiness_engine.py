from __future__ import annotations

from collections import Counter, defaultdict

from stock_risk_mcp.historical_dataset_readiness_guard import (
    validate_historical_dataset_readiness_metadata_safety,
    validate_historical_dataset_readiness_split_integrity,
)
from stock_risk_mcp.historical_dataset_readiness_models import (
    HistoricalDatasetBaselineEvaluationReport,
    HistoricalDatasetImbalanceReport,
    HistoricalDatasetReadinessGapCategory,
    HistoricalDatasetReadinessGapEntry,
    HistoricalDatasetReadinessGapReport,
    HistoricalDatasetReadinessInput,
    HistoricalDatasetReadinessReport,
    HistoricalDatasetReadinessSafetyReport,
    HistoricalDatasetSplitQualityReport,
)


def build_historical_dataset_readiness(
    readiness_input: HistoricalDatasetReadinessInput,
) -> HistoricalDatasetReadinessInput:
    gap_entries: list[HistoricalDatasetReadinessGapEntry] = []
    warnings: list[str] = []
    records = list(readiness_input.dataset_records)
    records_by_id = {record.record_id: record for record in records}

    for audit in readiness_input.audit_records:
        try:
            validate_historical_dataset_readiness_metadata_safety(
                {
                    "operator_context": audit.operator_context,
                    "source_path": audit.source_path,
                },
                context="historical dataset readiness",
            )
        except ValueError as exc:
            gap_entries.append(_unsafe_gap(readiness_input, str(exc)))

    validation_report = readiness_input.validation_report
    if validation_report is None:
        gap_entries.append(
            _gap_entry(
                readiness_input,
                "missing-validation-report",
                HistoricalDatasetReadinessGapCategory.READINESS_MISSING_VALIDATION_REPORT,
                "BLOCKING",
                "missing validation report",
            )
        )
    elif validation_report.blocked_count > 0:
        gap_entries.append(
            _gap_entry(
                readiness_input,
                "validation-not-clean",
                HistoricalDatasetReadinessGapCategory.READINESS_VALIDATION_NOT_CLEAN,
                "BLOCKING",
                "validation report is not clean",
            )
        )

    leakage_audit = readiness_input.leakage_audit_report
    if leakage_audit is None:
        gap_entries.append(
            _gap_entry(
                readiness_input,
                "missing-leakage-audit",
                HistoricalDatasetReadinessGapCategory.READINESS_MISSING_LEAKAGE_AUDIT,
                "BLOCKING",
                "missing leakage audit report",
            )
        )
    elif (not leakage_audit.feature_outcome_leakage_absent) or leakage_audit.blocked_record_count > 0:
        gap_entries.append(
            _gap_entry(
                readiness_input,
                "leakage-audit-not-clean",
                HistoricalDatasetReadinessGapCategory.READINESS_LEAKAGE_AUDIT_NOT_CLEAN,
                "BLOCKING",
                "leakage audit report is not clean",
            )
        )

    split_manifest = readiness_input.split_manifest
    if split_manifest is None:
        gap_entries.append(
            _gap_entry(
                readiness_input,
                "missing-split-manifest",
                HistoricalDatasetReadinessGapCategory.READINESS_MISSING_SPLIT_MANIFEST,
                "BLOCKING",
                "missing split manifest",
            )
        )
        partitions = {"TRAIN": [], "VALIDATION": [], "TEST": []}
    else:
        partitions = {
            "TRAIN": list(split_manifest.train_record_refs),
            "VALIDATION": list(split_manifest.validation_record_refs),
            "TEST": list(split_manifest.test_record_refs),
        }
        if not split_manifest.chronological or split_manifest.split_policy != "CHRONOLOGICAL":
            gap_entries.append(
                _gap_entry(
                    readiness_input,
                    "split-not-chronological",
                    HistoricalDatasetReadinessGapCategory.READINESS_SPLIT_NOT_CHRONOLOGICAL,
                    "BLOCKING",
                    "split manifest is not chronological",
                )
            )
        try:
            validate_historical_dataset_readiness_split_integrity(
                split_manifest.model_dump(mode="json"),
                context="historical dataset readiness",
            )
        except ValueError as exc:
            gap_entries.append(_split_gap(readiness_input, str(exc)))
        _collect_split_partition_gaps(readiness_input, split_manifest, gap_entries)

    coverage_report = readiness_input.coverage_report
    if coverage_report is None:
        gap_entries.append(
            _gap_entry(
                readiness_input,
                "missing-coverage-report",
                HistoricalDatasetReadinessGapCategory.READINESS_MISSING_COVERAGE_REPORT,
                "BLOCKING",
                "missing coverage report",
            )
        )

    label_distribution_report = readiness_input.label_distribution_report
    if label_distribution_report is None:
        gap_entries.append(
            _gap_entry(
                readiness_input,
                "missing-label-distribution-report",
                HistoricalDatasetReadinessGapCategory.READINESS_MISSING_LABEL_DISTRIBUTION,
                "BLOCKING",
                "missing label distribution report",
            )
        )

    _collect_record_gaps(readiness_input, records, gap_entries, warnings)
    _collect_threshold_gaps(readiness_input, records, partitions, gap_entries)

    split_quality_report = _build_split_quality_report(readiness_input, records_by_id, partitions)
    imbalance_report = _build_imbalance_report(readiness_input, records, records_by_id, partitions, gap_entries, warnings)
    baseline_report = _build_baseline_evaluation_report(readiness_input, records_by_id, partitions, gap_entries)

    if not baseline_report.deterministic_only or not baseline_report.non_learning_only:
        gap_entries.append(
            _gap_entry(
                readiness_input,
                "baseline-learning-claim-rejected",
                HistoricalDatasetReadinessGapCategory.READINESS_LEARNED_MODEL_DETECTED,
                "BLOCKING",
                "baseline report must remain deterministic and non-learning",
            )
        )
    if baseline_report.trained_model_artifact_present:
        gap_entries.append(
            _gap_entry(
                readiness_input,
                "baseline-trained-artifact-detected",
                HistoricalDatasetReadinessGapCategory.READINESS_LEARNED_MODEL_DETECTED,
                "BLOCKING",
                "baseline report exposed learned model artifact",
            )
        )
    if baseline_report.model_weights_present:
        gap_entries.append(
            _gap_entry(
                readiness_input,
                "baseline-weight-detected",
                HistoricalDatasetReadinessGapCategory.READINESS_MODEL_WEIGHT_DETECTED,
                "BLOCKING",
                "baseline report exposed model weight marker",
            )
        )

    gap_entries.append(
        _gap_entry(
            readiness_input,
            "readiness-report-generated",
            HistoricalDatasetReadinessGapCategory.READINESS_REPORT_GENERATED,
            "REPORT_ONLY",
            "historical dataset readiness report generated",
        )
    )
    gap_entries.append(
        _gap_entry(
            readiness_input,
            "readiness-report-only",
            HistoricalDatasetReadinessGapCategory.READINESS_REPORT_ONLY,
            "REPORT_ONLY",
            "historical dataset readiness remains report-only and non-executable",
        )
    )
    gap_entries.append(
        _gap_entry(
            readiness_input,
            "baseline-report-generated",
            HistoricalDatasetReadinessGapCategory.READINESS_BASELINE_REPORT_GENERATED,
            "REPORT_ONLY",
            "deterministic baseline evaluation report generated",
        )
    )
    gap_entries.append(
        _gap_entry(
            readiness_input,
            "baseline-non-learning",
            HistoricalDatasetReadinessGapCategory.READINESS_BASELINE_NON_LEARNING,
            "REPORT_ONLY",
            "baseline evaluation remains deterministic and non-learning",
        )
    )

    readiness_report = _build_readiness_report(readiness_input, records, gap_entries, warnings)
    gap_report = _build_gap_report(readiness_input, gap_entries)
    safety_report = HistoricalDatasetReadinessSafetyReport.model_validate(
        readiness_input.readiness_safety_report.model_dump(mode="json")
    )

    return readiness_input.model_copy(
        update={
            "readiness_report": readiness_report,
            "split_quality_report": split_quality_report,
            "imbalance_report": imbalance_report,
            "baseline_evaluation_report": baseline_report,
            "readiness_gap_report": gap_report,
            "readiness_safety_report": safety_report,
        }
    )


def _collect_record_gaps(readiness_input, records, gap_entries, warnings) -> None:
    if not records:
        gap_entries.append(
            _gap_entry(
                readiness_input,
                "missing-input",
                HistoricalDatasetReadinessGapCategory.READINESS_MISSING_INPUT,
                "BLOCKING",
                "missing readiness input records",
            )
        )
        return

    for record in records:
        if not record.source_manifest_ids or not record.replay_window_id or not record.outcome_observation_id:
            gap_entries.append(
                _gap_entry(
                    readiness_input,
                    f"lineage-incomplete-{record.record_id}",
                    HistoricalDatasetReadinessGapCategory.READINESS_LINEAGE_INCOMPLETE,
                    "REPORT_ONLY",
                    f"incomplete lineage for record {record.record_id}",
                )
            )
        if record.outcome_block.outcome_label is None:
            warnings.append(f"missing outcome label for record {record.record_id}")
            gap_entries.append(
                _gap_entry(
                    readiness_input,
                    f"missingness-{record.record_id}",
                    HistoricalDatasetReadinessGapCategory.READINESS_MISSINGNESS_WARNING,
                    "REPORT_ONLY",
                    f"missing outcome label for record {record.record_id}",
                )
            )


def _collect_threshold_gaps(readiness_input, records, partitions, gap_entries) -> None:
    config = readiness_input.readiness_config
    if len(records) < config.minimum_record_count:
        gap_entries.append(
            _gap_entry(
                readiness_input,
                "record-count-too-small",
                HistoricalDatasetReadinessGapCategory.READINESS_TRAIN_COUNT_TOO_SMALL,
                "BLOCKING",
                "record count below readiness minimum",
            )
        )
    if len(partitions["TRAIN"]) < config.minimum_train_count:
        gap_entries.append(
            _gap_entry(
                readiness_input,
                "train-count-too-small",
                HistoricalDatasetReadinessGapCategory.READINESS_TRAIN_COUNT_TOO_SMALL,
                "BLOCKING",
                "train split count below readiness minimum",
            )
        )
    if len(partitions["VALIDATION"]) < config.minimum_validation_count:
        gap_entries.append(
            _gap_entry(
                readiness_input,
                "validation-count-too-small",
                HistoricalDatasetReadinessGapCategory.READINESS_VALIDATION_COUNT_TOO_SMALL,
                "BLOCKING",
                "validation split count below readiness minimum",
            )
        )
    if len(partitions["TEST"]) < config.minimum_test_count:
        gap_entries.append(
            _gap_entry(
                readiness_input,
                "test-count-too-small",
                HistoricalDatasetReadinessGapCategory.READINESS_TEST_COUNT_TOO_SMALL,
                "BLOCKING",
                "test split count below readiness minimum",
            )
        )


def _collect_split_partition_gaps(readiness_input, split_manifest, gap_entries) -> None:
    seen_partition: dict[str, str] = {}
    duplicate_seen: set[str] = set()
    prior_end = None
    for partition in ("TRAIN", "VALIDATION", "TEST"):
        refs = getattr(split_manifest, f"{partition.lower()}_record_refs")
        dates = [ref.replay_anchor_date for ref in refs]
        if dates and dates != sorted(dates):
            gap_entries.append(
                _gap_entry(
                    readiness_input,
                    f"split-not-chronological-{partition.lower()}",
                    HistoricalDatasetReadinessGapCategory.READINESS_SPLIT_NOT_CHRONOLOGICAL,
                    "BLOCKING",
                    f"{partition.lower()} split is not chronological",
                )
            )
        if prior_end is not None and dates and min(dates) < prior_end:
            gap_entries.append(
                _gap_entry(
                    readiness_input,
                    f"split-overlap-{partition.lower()}",
                    HistoricalDatasetReadinessGapCategory.READINESS_SPLIT_PARTITION_OVERLAP,
                    "BLOCKING",
                    f"{partition.lower()} split overlaps prior partition chronology",
                )
            )
        if dates:
            prior_end = max(dates)
        for ref in refs:
            prior_partition = seen_partition.get(ref.dataset_record_id)
            if prior_partition is not None and prior_partition != partition:
                gap_entries.append(
                    _gap_entry(
                        readiness_input,
                        f"split-partition-overlap-{ref.dataset_record_id}",
                        HistoricalDatasetReadinessGapCategory.READINESS_SPLIT_PARTITION_OVERLAP,
                        "BLOCKING",
                        f"record {ref.dataset_record_id} appears in multiple partitions",
                    )
                )
            seen_partition[ref.dataset_record_id] = partition
            if ref.dataset_record_id in duplicate_seen:
                continue
            partition_occurrences = sum(
                1 for candidate in split_manifest.record_refs if candidate.dataset_record_id == ref.dataset_record_id
            )
            if partition_occurrences > 1:
                gap_entries.append(
                    _gap_entry(
                        readiness_input,
                        f"duplicated-record-id-{ref.dataset_record_id}",
                        HistoricalDatasetReadinessGapCategory.READINESS_SPLIT_DUPLICATED_RECORD_ID,
                        "BLOCKING",
                        f"duplicated record id detected in split manifest for {ref.dataset_record_id}",
                    )
                )
                duplicate_seen.add(ref.dataset_record_id)


def _build_split_quality_report(readiness_input, records_by_id, partitions) -> HistoricalDatasetSplitQualityReport:
    split_manifest = readiness_input.split_manifest
    return HistoricalDatasetSplitQualityReport.model_validate(
        {
            "split_quality_report_id": readiness_input.split_quality_report.split_quality_report_id,
            "readiness_input_id": readiness_input.readiness_input_id,
            "chronological_split": bool(split_manifest and split_manifest.chronological and split_manifest.split_policy == "CHRONOLOGICAL"),
            "random_shuffle_used": bool(split_manifest and split_manifest.random_shuffle_used),
            "partition_overlap_detected": _partition_overlap_detected(partitions),
            "duplicated_record_id_detected": _duplicated_record_id_detected(partitions),
            "train_record_count": len(partitions["TRAIN"]),
            "validation_record_count": len(partitions["VALIDATION"]),
            "test_record_count": len(partitions["TEST"]),
            "train_symbol_count": _symbol_count(partitions["TRAIN"]),
            "validation_symbol_count": _symbol_count(partitions["VALIDATION"]),
            "test_symbol_count": _symbol_count(partitions["TEST"]),
            "train_date_range_start": _range_start(partitions["TRAIN"]),
            "train_date_range_end": _range_end(partitions["TRAIN"]),
            "validation_date_range_start": _range_start(partitions["VALIDATION"]),
            "validation_date_range_end": _range_end(partitions["VALIDATION"]),
            "test_date_range_start": _range_start(partitions["TEST"]),
            "test_date_range_end": _range_end(partitions["TEST"]),
            "train_label_distribution": _label_distribution(partitions["TRAIN"], records_by_id),
            "validation_label_distribution": _label_distribution(partitions["VALIDATION"], records_by_id),
            "test_label_distribution": _label_distribution(partitions["TEST"], records_by_id),
            "source_manifest_ids": _lineage_ids(readiness_input, "source_manifest_ids"),
            "source_audit_record_ids": _lineage_ids(readiness_input, "source_audit_record_ids"),
            "provider_provenance_ids": _lineage_ids(readiness_input, "provider_provenance_ids"),
        }
    )


def _build_imbalance_report(readiness_input, records, records_by_id, partitions, gap_entries, warnings) -> HistoricalDatasetImbalanceReport:
    label_counts = Counter()
    missing_label_count = 0
    for record in records:
        label = record.outcome_block.outcome_label
        if label is None:
            missing_label_count += 1
            continue
        label_counts[label] += 1
    label_percentages = _percentages(label_counts)

    split_label_counts = {
        partition: _label_distribution(refs, records_by_id) for partition, refs in partitions.items()
    }
    split_label_percentages = {
        partition: _percentages(Counter(counts)) for partition, counts in split_label_counts.items()
    }

    unique_label_count = len(label_counts)
    severe_imbalance = bool(label_percentages and max(label_percentages.values()) >= 0.8)
    low_label_coverage = unique_label_count < readiness_input.readiness_config.minimum_label_coverage
    missing_label_warning = missing_label_count > 0
    if severe_imbalance:
        warnings.append("severe label imbalance detected")
        gap_entries.append(
            _gap_entry(
                readiness_input,
                "label-imbalance-warning",
                HistoricalDatasetReadinessGapCategory.READINESS_LABEL_IMBALANCE_WARNING,
                "REPORT_ONLY",
                "severe label imbalance detected",
            )
        )
    if low_label_coverage:
        warnings.append("label coverage below readiness minimum")
        gap_entries.append(
            _gap_entry(
                readiness_input,
                "label-coverage-too-low",
                HistoricalDatasetReadinessGapCategory.READINESS_LABEL_COVERAGE_TOO_LOW,
                "BLOCKING",
                "label coverage below readiness minimum",
            )
        )
    if missing_label_warning:
        warnings.append("missing label values detected")

    return HistoricalDatasetImbalanceReport.model_validate(
        {
            "imbalance_report_id": readiness_input.imbalance_report.imbalance_report_id,
            "readiness_input_id": readiness_input.readiness_input_id,
            "label_counts": dict(label_counts),
            "label_percentages": label_percentages,
            "split_label_counts": split_label_counts,
            "split_label_percentages": split_label_percentages,
            "severe_imbalance_warning": severe_imbalance,
            "missing_label_warning": missing_label_warning,
            "low_label_coverage_warning": low_label_coverage,
            "warning_count": len(warnings),
            "warnings": warnings,
            "source_manifest_ids": _lineage_ids(readiness_input, "source_manifest_ids"),
            "source_audit_record_ids": _lineage_ids(readiness_input, "source_audit_record_ids"),
            "provider_provenance_ids": _lineage_ids(readiness_input, "provider_provenance_ids"),
        }
    )


def _build_baseline_evaluation_report(readiness_input, records_by_id, partitions, gap_entries) -> HistoricalDatasetBaselineEvaluationReport:
    train_records = [records_by_id[ref.dataset_record_id] for ref in partitions["TRAIN"] if ref.dataset_record_id in records_by_id]
    validation_records = [records_by_id[ref.dataset_record_id] for ref in partitions["VALIDATION"] if ref.dataset_record_id in records_by_id]
    test_records = [records_by_id[ref.dataset_record_id] for ref in partitions["TEST"] if ref.dataset_record_id in records_by_id]
    all_eval_records = validation_records + test_records or train_records

    train_labels = [record.outcome_block.outcome_label for record in train_records if record.outcome_block.outcome_label]
    global_majority = _majority_label(train_labels)
    predictions_by_baseline = {
        "MAJORITY_LABEL_BASELINE": lambda record: global_majority,
        "PER_SYMBOL_MAJORITY_LABEL_BASELINE": _per_key_majority_predictor(train_records, "symbol", global_majority),
        "PER_MARKET_MAJORITY_LABEL_BASELINE": _per_key_majority_predictor(train_records, "market", global_majority),
        "PER_TRACK_MAJORITY_LABEL_BASELINE": _per_key_majority_predictor(train_records, "strategy_track", global_majority),
        "PRIOR_DISTRIBUTION_BASELINE": lambda record: global_majority,
        "NO_SKILL_BASELINE": lambda record: global_majority,
    }

    split_metric_summary = {}
    confusion_matrix_counts = Counter()
    aggregate_accuracy = []
    aggregate_coverage = []
    for baseline_name in readiness_input.baseline_config.enabled_baselines:
        predictor = predictions_by_baseline[baseline_name]
        for partition_name, partition_records in (
            ("TRAIN", train_records),
            ("VALIDATION", validation_records),
            ("TEST", test_records),
        ):
            metrics = _score_partition(partition_records, predictor, confusion_matrix_counts if partition_name == "TEST" else None)
            split_metric_summary[f"{partition_name}:{baseline_name}"] = metrics
            if partition_name == "TEST" and metrics["accuracy"] is not None:
                aggregate_accuracy.append(metrics["accuracy"])
                aggregate_coverage.append(metrics["label_coverage"])

    baseline_report = HistoricalDatasetBaselineEvaluationReport.model_validate(
        {
            "baseline_evaluation_report_id": readiness_input.baseline_evaluation_report.baseline_evaluation_report_id,
            "readiness_input_id": readiness_input.readiness_input_id,
            "baseline_names": readiness_input.baseline_config.enabled_baselines,
            "deterministic_only": True,
            "non_learning_only": True,
            "accuracy": _mean_or_none(aggregate_accuracy),
            "label_coverage": _mean_or_none(aggregate_coverage),
            "confusion_matrix_counts": dict(confusion_matrix_counts),
            "split_metric_summary": split_metric_summary,
            "trained_model_artifact_present": False,
            "model_weights_present": False,
            "runtime_trading_signal_present": False,
            "source_manifest_ids": _lineage_ids(readiness_input, "source_manifest_ids"),
            "source_audit_record_ids": _lineage_ids(readiness_input, "source_audit_record_ids"),
            "provider_provenance_ids": _lineage_ids(readiness_input, "provider_provenance_ids"),
        }
    )

    if all_eval_records and global_majority is None:
        gap_entries.append(
            _gap_entry(
                readiness_input,
                "missing-labels-for-baseline",
                HistoricalDatasetReadinessGapCategory.READINESS_LABEL_COVERAGE_TOO_LOW,
                "BLOCKING",
                "baseline evaluation requires at least one observed training label",
            )
        )
    return baseline_report


def _build_readiness_report(readiness_input, records, gap_entries, warnings) -> HistoricalDatasetReadinessReport:
    return HistoricalDatasetReadinessReport.model_validate(
        {
            "readiness_report_id": readiness_input.readiness_report.readiness_report_id,
            "readiness_input_id": readiness_input.readiness_input_id,
            "record_count": len(records),
            "blocking_gate_count": sum(1 for gap in gap_entries if gap.severity == "BLOCKING"),
            "warning_count": len(warnings),
            "warnings": warnings,
            "trade_approval": False,
            "training_approval": False,
            "source_manifest_ids": _lineage_ids(readiness_input, "source_manifest_ids"),
            "source_audit_record_ids": _lineage_ids(readiness_input, "source_audit_record_ids"),
            "provider_provenance_ids": _lineage_ids(readiness_input, "provider_provenance_ids"),
        }
    )


def _build_gap_report(readiness_input, gap_entries) -> HistoricalDatasetReadinessGapReport:
    blocking_gap_count = sum(1 for gap in gap_entries if gap.severity == "BLOCKING")
    report_only_gap_count = sum(1 for gap in gap_entries if gap.severity != "BLOCKING")
    return HistoricalDatasetReadinessGapReport.model_validate(
        {
            "gap_report_id": readiness_input.readiness_gap_report.gap_report_id,
            "readiness_input_id": readiness_input.readiness_input_id,
            "gap_status": "BLOCKING_GAPS" if blocking_gap_count else "REPORT_ONLY",
            "gap_categories": [gap.gap_category.value for gap in gap_entries if gap.gap_category is not None],
            "blocking_gap_count": blocking_gap_count,
            "report_only_gap_count": report_only_gap_count,
            "gaps": [gap.model_dump(mode="json") for gap in gap_entries],
            "source_manifest_ids": _lineage_ids(readiness_input, "source_manifest_ids"),
            "source_audit_record_ids": _lineage_ids(readiness_input, "source_audit_record_ids"),
            "provider_provenance_ids": _lineage_ids(readiness_input, "provider_provenance_ids"),
        }
    )


def _gap_entry(readiness_input, gap_id, category, severity, message) -> HistoricalDatasetReadinessGapEntry:
    return HistoricalDatasetReadinessGapEntry.model_validate(
        {
            "gap_id": gap_id,
            "gap_category": category.value,
            "severity": severity,
            "message": message,
        }
    )


def _unsafe_gap(readiness_input, reason: str) -> HistoricalDatasetReadinessGapEntry:
    mapping = (
        ("buy_sell", HistoricalDatasetReadinessGapCategory.READINESS_BUY_SELL_WORDING_DETECTED, "unsafe buy/sell wording detected"),
        ("order", HistoricalDatasetReadinessGapCategory.READINESS_ORDER_FIELD_DETECTED, "unsafe order field detected"),
        ("execution", HistoricalDatasetReadinessGapCategory.READINESS_ORDER_FIELD_DETECTED, "unsafe execution field detected"),
        ("remote", HistoricalDatasetReadinessGapCategory.READINESS_REMOTE_SOURCE_NOT_ALLOWED, "remote source is not allowed"),
        ("api", HistoricalDatasetReadinessGapCategory.READINESS_API_SOURCE_NOT_ALLOWED, "api source is not allowed"),
        ("network", HistoricalDatasetReadinessGapCategory.READINESS_NETWORK_SOURCE_NOT_ALLOWED, "network source is not allowed"),
        ("provider", HistoricalDatasetReadinessGapCategory.READINESS_PROVIDER_SOURCE_NOT_ALLOWED, "provider source is not allowed"),
        ("kiwoom", HistoricalDatasetReadinessGapCategory.READINESS_PROVIDER_SOURCE_NOT_ALLOWED, "kiwoom source is not allowed"),
        ("ls", HistoricalDatasetReadinessGapCategory.READINESS_PROVIDER_SOURCE_NOT_ALLOWED, "ls source is not allowed"),
        ("gemini", HistoricalDatasetReadinessGapCategory.READINESS_LLM_METADATA_NOT_ALLOWED, "gemini metadata is not allowed"),
        ("llm", HistoricalDatasetReadinessGapCategory.READINESS_LLM_METADATA_NOT_ALLOWED, "llm metadata is not allowed"),
        ("cloud_model", HistoricalDatasetReadinessGapCategory.READINESS_LLM_METADATA_NOT_ALLOWED, "cloud model metadata is not allowed"),
        ("crawler", HistoricalDatasetReadinessGapCategory.READINESS_CRAWLER_TRIGGER_NOT_ALLOWED, "crawler trigger is not allowed"),
        ("parquet", HistoricalDatasetReadinessGapCategory.READINESS_PARQUET_NOT_ALLOWED, "parquet is not allowed"),
        ("training", HistoricalDatasetReadinessGapCategory.READINESS_ML_TRAINING_TRIGGER_NOT_ALLOWED, "ml training trigger is not allowed"),
        ("tensor", HistoricalDatasetReadinessGapCategory.READINESS_ML_READY_TENSOR_EXPORT_NOT_ALLOWED, "ml-ready tensor export is not allowed"),
        ("learned", HistoricalDatasetReadinessGapCategory.READINESS_LEARNED_MODEL_DETECTED, "learned model marker detected"),
        ("learning", HistoricalDatasetReadinessGapCategory.READINESS_LEARNED_MODEL_DETECTED, "learned model marker detected"),
        ("weight", HistoricalDatasetReadinessGapCategory.READINESS_MODEL_WEIGHT_DETECTED, "model weight marker detected"),
        ("live_prod", HistoricalDatasetReadinessGapCategory.READINESS_LIVE_PROD_NOT_ALLOWED, "live/prod marker detected"),
    )
    lowered = reason.lower()
    for needle, category, message in mapping:
        if needle in lowered:
            return _gap_entry(readiness_input, f"unsafe-{needle}", category, "BLOCKING", message)
    return _gap_entry(
        readiness_input,
        "unsafe-metadata",
        HistoricalDatasetReadinessGapCategory.READINESS_ORDER_FIELD_DETECTED,
        "BLOCKING",
        "unsafe readiness metadata detected",
    )


def _split_gap(readiness_input, reason: str) -> HistoricalDatasetReadinessGapEntry:
    lowered = reason.lower()
    if "random shuffle" in lowered:
        return _gap_entry(
            readiness_input,
            "random-shuffle-detected",
            HistoricalDatasetReadinessGapCategory.READINESS_SPLIT_RANDOM_SHUFFLE_DETECTED,
            "BLOCKING",
            "random shuffle detected in split manifest",
        )
    if "overlap" in lowered:
        return _gap_entry(
            readiness_input,
            "partition-overlap-detected",
            HistoricalDatasetReadinessGapCategory.READINESS_SPLIT_PARTITION_OVERLAP,
            "BLOCKING",
            "split partition overlap detected",
        )
    return _gap_entry(
        readiness_input,
        "duplicated-record-detected",
        HistoricalDatasetReadinessGapCategory.READINESS_SPLIT_DUPLICATED_RECORD_ID,
        "BLOCKING",
        "duplicated split record id detected",
    )


def _lineage_ids(readiness_input, field_name: str) -> list[str]:
    values = []
    for source in (
        readiness_input.validation_report,
        readiness_input.leakage_audit_report,
        readiness_input.split_manifest,
        readiness_input.coverage_report,
        readiness_input.label_distribution_report,
    ):
        if source is None:
            continue
        values.extend(getattr(source, field_name, []))
    return list(dict.fromkeys(values))


def _partition_overlap_detected(partitions) -> bool:
    seen = {}
    for partition, refs in partitions.items():
        for ref in refs:
            prior = seen.get(ref.dataset_record_id)
            if prior is not None and prior != partition:
                return True
            seen[ref.dataset_record_id] = partition
    return False


def _duplicated_record_id_detected(partitions) -> bool:
    record_ids = [ref.dataset_record_id for refs in partitions.values() for ref in refs]
    return len(record_ids) != len(set(record_ids))


def _symbol_count(refs) -> int:
    return len({ref.symbol for ref in refs})


def _range_start(refs):
    if not refs:
        return None
    return min(ref.replay_anchor_date for ref in refs).isoformat()


def _range_end(refs):
    if not refs:
        return None
    return max(ref.replay_anchor_date for ref in refs).isoformat()


def _label_distribution(refs, records_by_id) -> dict[str, int]:
    counts = Counter()
    for ref in refs:
        record = records_by_id.get(ref.dataset_record_id)
        if record is None or record.outcome_block.outcome_label is None:
            continue
        counts[record.outcome_block.outcome_label] += 1
    return dict(counts)


def _percentages(counts: Counter | dict[str, int]) -> dict[str, float]:
    total = sum(counts.values())
    if total == 0:
        return {}
    return {key: value / total for key, value in counts.items()}


def _majority_label(labels: list[str]) -> str | None:
    if not labels:
        return None
    counts = Counter(labels)
    return sorted(counts.items(), key=lambda item: (-item[1], item[0]))[0][0]


def _per_key_majority_predictor(records, attribute: str, fallback: str | None):
    by_key = defaultdict(list)
    for record in records:
        label = record.outcome_block.outcome_label
        if label is None:
            continue
        key = getattr(record, attribute)
        if hasattr(key, "value"):
            key = key.value
        by_key[key].append(label)
    majority_by_key = {key: _majority_label(labels) for key, labels in by_key.items()}

    def predictor(record):
        key = getattr(record, attribute)
        if hasattr(key, "value"):
            key = key.value
        return majority_by_key.get(key, fallback)

    return predictor


def _score_partition(records, predictor, confusion_counter=None) -> dict[str, float | None]:
    if not records:
        return {"accuracy": 0.0, "label_coverage": 0.0}
    actual_labels = [record.outcome_block.outcome_label for record in records]
    predictions = [predictor(record) for record in records]
    comparable = [(actual, predicted) for actual, predicted in zip(actual_labels, predictions) if actual and predicted]
    if confusion_counter is not None:
        for actual, predicted in comparable:
            confusion_counter[f"{predicted}->{actual}"] += 1
    if not comparable:
        return {"accuracy": 0.0, "label_coverage": 0.0}
    correct = sum(1 for actual, predicted in comparable if actual == predicted)
    return {
        "accuracy": correct / len(comparable),
        "label_coverage": len(comparable) / len(records),
    }


def _mean_or_none(values: list[float]) -> float | None:
    if not values:
        return None
    return sum(values) / len(values)
