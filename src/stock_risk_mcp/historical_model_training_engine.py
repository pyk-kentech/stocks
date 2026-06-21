from __future__ import annotations

import importlib
from collections import Counter
from datetime import datetime, timezone
from math import isclose

from stock_risk_mcp.historical_model_training_guard import (
    validate_historical_model_training_artifact_safety,
    validate_historical_model_training_feature_boundary,
    validate_historical_model_training_label_schema_safety,
    validate_historical_model_training_metadata_safety,
    validate_historical_model_training_model_type_safety,
    validate_historical_model_training_split_safety,
)
from stock_risk_mcp.historical_model_training_models import (
    HistoricalModelTrainingInput,
    HistoricalModelTrainingModelType,
)


def build_historical_model_training_plan_check(
    training_input: HistoricalModelTrainingInput,
) -> HistoricalModelTrainingInput:
    gap_entries: list[dict[str, str]] = []
    warnings: list[str] = []

    for audit in training_input.audit_records:
        try:
            validate_historical_model_training_metadata_safety(
                {
                    "operator_context": audit.operator_context,
                    "source_path": audit.source_path,
                },
                context="historical model training",
            )
        except ValueError as exc:
            gap_entries.append(_unsafe_gap(str(exc)))

    try:
        validate_historical_model_training_artifact_safety(
            training_input.artifact_manifest.model_dump(mode="json"),
            context="historical model training",
        )
    except ValueError as exc:
        gap_entries.append(_artifact_gap(str(exc)))

    if training_input.readiness_report is None:
        gap_entries.append(_gap("missing-readiness-report", "TRAINING_MISSING_READINESS_REPORT", "BLOCKING", "missing readiness report"))
    elif training_input.readiness_report.blocking_gate_count > 0:
        gap_entries.append(_gap("readiness-not-clean", "TRAINING_READINESS_NOT_CLEAN", "BLOCKING", "readiness report is not clean"))

    if training_input.validation_report is None:
        gap_entries.append(_gap("missing-validation-report", "TRAINING_MISSING_VALIDATION_REPORT", "BLOCKING", "missing validation report"))
    elif training_input.validation_report.blocked_count > 0:
        gap_entries.append(_gap("validation-not-clean", "TRAINING_VALIDATION_NOT_CLEAN", "BLOCKING", "validation report is not clean"))

    if training_input.leakage_audit_report is None:
        gap_entries.append(_gap("missing-leakage-audit", "TRAINING_MISSING_LEAKAGE_AUDIT", "BLOCKING", "missing leakage audit report"))
    elif not training_input.leakage_audit_report.feature_outcome_leakage_absent:
        gap_entries.append(_gap("leakage-audit-not-clean", "TRAINING_LEAKAGE_AUDIT_NOT_CLEAN", "BLOCKING", "leakage audit report is not clean"))

    if training_input.split_manifest is None:
        gap_entries.append(_gap("missing-split-ref", "TRAINING_MISSING_SPLIT_REF", "BLOCKING", "missing split manifest"))
        split_partitions = {"TRAIN": [], "VALIDATION": [], "TEST": []}
    else:
        split_failed = False
        try:
            validate_historical_model_training_split_safety(
                training_input.split_manifest.model_dump(mode="json"),
                context="historical model training",
            )
        except ValueError as exc:
            reason = str(exc).lower()
            if "random shuffle" in reason:
                gap_entries.append(_gap("random-shuffle-detected", "TRAINING_RANDOM_SHUFFLE_DETECTED", "BLOCKING", "random shuffle detected"))
            else:
                gap_entries.append(_gap("split-not-chronological", "TRAINING_SPLIT_NOT_CHRONOLOGICAL", "BLOCKING", "split is not chronological"))
            split_failed = True
        gap_entries.extend(_split_partition_gaps(training_input))
        if split_failed:
            split_partitions = {"TRAIN": [], "VALIDATION": [], "TEST": []}
        else:
            split_partitions = prepare_historical_model_training_splits(training_input)

    try:
        validate_historical_model_training_feature_boundary(
            training_input.feature_schema.model_dump(mode="json"),
            context="historical model training",
        )
    except ValueError as exc:
        gap_entries.append(_feature_gap(str(exc)))

    try:
        validate_historical_model_training_label_schema_safety(
            training_input.label_schema.model_dump(mode="json"),
            context="historical model training",
        )
    except ValueError:
        gap_entries.append(_gap("label-not-outcome-side", "TRAINING_LABEL_NOT_OUTCOME_SIDE", "BLOCKING", "label schema is not outcome-side"))

    try:
        validate_historical_model_training_model_type_safety(
            training_input.run_config.model_dump(mode="json"),
            context="historical model training",
        )
    except ValueError:
        gap_entries.append(_gap("unsupported-model-type", "TRAINING_UNSUPPORTED_MODEL_TYPE", "BLOCKING", "unsupported model type"))

    if not split_partitions["TRAIN"] or not split_partitions["VALIDATION"] or not split_partitions["TEST"]:
        gap_entries.append(_gap("missing-split-partition", "TRAINING_MISSING_SPLIT_REF", "BLOCKING", "missing split partition"))

    report = training_input.plan_check_report.model_copy(
        update={
            "eligible_for_sandbox_training": len([gap for gap in gap_entries if gap["severity"] == "BLOCKING"]) == 0,
            "warning_count": len(warnings),
            "warnings": warnings,
            "blocking_issue_count": len([gap for gap in gap_entries if gap["severity"] == "BLOCKING"]),
        }
    )
    gap_report = training_input.gap_report.model_copy(
        update={
            "gap_status": "BLOCKING_GAPS" if any(gap["severity"] == "BLOCKING" for gap in gap_entries) else "NO_GAPS",
            "gap_categories": [gap["gap_category"] for gap in gap_entries],
            "blocking_gap_count": len([gap for gap in gap_entries if gap["severity"] == "BLOCKING"]),
            "report_only_gap_count": len([gap for gap in gap_entries if gap["severity"] != "BLOCKING"]),
            "gaps": gap_entries,
        }
    )
    return training_input.model_copy(update={"plan_check_report": report, "gap_report": gap_report})


def run_historical_model_training_sandbox(training_input: HistoricalModelTrainingInput) -> HistoricalModelTrainingInput:
    result = build_historical_model_training_plan_check(training_input)
    gap_entries = [dict(gap) for gap in result.gap_report.gaps]

    if result.plan_check_report is None:
        gap_entries.append(_gap("missing-plan-check", "TRAINING_MISSING_PLAN_CHECK", "BLOCKING", "missing training plan check"))
        return _blocked_training_result(result, gap_entries)

    if not result.plan_check_report.eligible_for_sandbox_training:
        gap_entries.append(_gap("plan-check-failed", "TRAINING_PLAN_CHECK_FAILED", "BLOCKING", "training plan check failed"))
        return _blocked_training_result(result, gap_entries)

    try:
        feature_rows = extract_historical_model_training_feature_rows(result)
    except ValueError as exc:
        gap_entries.append(_feature_or_unsafe_gap(str(exc)))
        return _blocked_training_result(result, gap_entries)

    if not feature_rows:
        gap_entries.append(_gap("missing-feature-matrix", "TRAINING_MISSING_FEATURE_MATRIX", "BLOCKING", "missing feature matrix"))
        return _blocked_training_result(result, gap_entries)

    try:
        labels = extract_historical_model_training_labels(result)
    except ValueError as exc:
        gap_entries.append(_feature_or_unsafe_gap(str(exc)))
        return _blocked_training_result(result, gap_entries)

    if not labels:
        gap_entries.append(_gap("missing-labels", "TRAINING_MISSING_LABELS", "BLOCKING", "missing labels"))
        return _blocked_training_result(result, gap_entries)

    try:
        split_records = prepare_historical_model_training_splits(result)
    except ValueError as exc:
        gap_entries.append(_unsafe_gap(str(exc)))
        return _blocked_training_result(result, gap_entries)

    partition_record_ids = {
        "TRAIN": [record.record_id for record in split_records["TRAIN"]],
        "VALIDATION": [record.record_id for record in split_records["VALIDATION"]],
        "TEST": [record.record_id for record in split_records["TEST"]],
    }
    for partition_name, category in (
        ("TRAIN", "TRAINING_MISSING_TRAIN_SPLIT"),
        ("VALIDATION", "TRAINING_MISSING_VALIDATION_SPLIT"),
        ("TEST", "TRAINING_MISSING_TEST_SPLIT"),
    ):
        if not partition_record_ids[partition_name]:
            gap_entries.append(_gap(f"missing-{partition_name.lower()}-split", category, "BLOCKING", f"missing {partition_name.lower()} split"))
    if any(gap["severity"] == "BLOCKING" for gap in gap_entries):
        return _blocked_training_result(result, gap_entries)

    rows_by_record_id = {row["record_id"]: row for row in feature_rows}
    for partition_name, record_ids in partition_record_ids.items():
        if not all(record_id in rows_by_record_id for record_id in record_ids):
            gap_entries.append(_gap(f"missing-feature-matrix-{partition_name.lower()}", "TRAINING_MISSING_FEATURE_MATRIX", "BLOCKING", f"missing feature matrix for {partition_name.lower()} split"))
        if not all(record_id in labels for record_id in record_ids):
            gap_entries.append(_gap(f"missing-labels-{partition_name.lower()}", "TRAINING_MISSING_LABELS", "BLOCKING", f"missing labels for {partition_name.lower()} split"))
    if any(gap["severity"] == "BLOCKING" for gap in gap_entries):
        return _blocked_training_result(result, gap_entries)

    model_type = result.run_config.requested_model_type
    train_ids = partition_record_ids["TRAIN"]
    validation_ids = partition_record_ids["VALIDATION"]
    test_ids = partition_record_ids["TEST"]

    train_labels = [labels[record_id] for record_id in train_ids]
    validation_labels = [labels[record_id] for record_id in validation_ids]
    test_labels = [labels[record_id] for record_id in test_ids]
    all_partition_labels = {
        "TRAIN": train_labels,
        "VALIDATION": validation_labels,
        "TEST": test_labels,
    }
    all_label_values = sorted(set(train_labels + validation_labels + test_labels))

    try:
        if model_type in {HistoricalModelTrainingModelType.DUMMY_MAJORITY, HistoricalModelTrainingModelType.DUMMY_PRIOR}:
            majority_label = _majority_label(train_labels)
            predictor = lambda record_ids: [majority_label for _ in record_ids]
        else:
            predictor = _build_optional_sklearn_predictor(result, rows_by_record_id, train_ids, train_labels)
    except ImportError:
        gap_entries.append(_gap("sklearn-unavailable", "TRAINING_SKLEARN_UNAVAILABLE", "BLOCKING", "sklearn unavailable"))
        return _blocked_training_result(result, gap_entries)
    except ValueError as exc:
        gap_entries.append(_unsafe_gap(str(exc)))
        return _blocked_training_result(result, gap_entries)

    predictions_by_partition = {
        "TRAIN": predictor(train_ids),
        "VALIDATION": predictor(validation_ids),
        "TEST": predictor(test_ids),
    }

    confusion_matrix_counts: dict[str, int] = {}
    for partition_name, actuals in all_partition_labels.items():
        for actual, predicted in zip(actuals, predictions_by_partition[partition_name], strict=True):
            key = f"{partition_name}|{actual}|{predicted}"
            confusion_matrix_counts[key] = confusion_matrix_counts.get(key, 0) + 1

    metrics_by_partition = {
        partition_name: _classification_metrics(actuals, predictions_by_partition[partition_name], all_label_values)
        for partition_name, actuals in all_partition_labels.items()
    }
    label_support = Counter(train_labels + validation_labels + test_labels)
    baseline_accuracy = result.baseline_evaluation_report.accuracy
    baseline_comparison = {}
    if baseline_accuracy is not None and metrics_by_partition["TEST"]["accuracy"] is not None:
        baseline_comparison["TEST_ACCURACY_DELTA_VS_BASELINE"] = metrics_by_partition["TEST"]["accuracy"] - baseline_accuracy
        baseline_comparison["BASELINE_REFERENCE_ACCURACY"] = baseline_accuracy

    warnings: list[str] = []
    train_accuracy = metrics_by_partition["TRAIN"]["accuracy"]
    test_accuracy = metrics_by_partition["TEST"]["accuracy"]
    if train_accuracy is not None and test_accuracy is not None and train_accuracy - test_accuracy >= 0.5 and not isclose(train_accuracy - test_accuracy, 0.5):
        warnings.append("OVERFIT_WARNING")
    elif train_accuracy is not None and test_accuracy is not None and train_accuracy - test_accuracy >= 0.5:
        warnings.append("OVERFIT_WARNING")
    if any(count <= 2 for count in label_support.values()):
        warnings.append("LOW_SUPPORT_LABEL_WARNING")

    metrics_report = result.metrics_report.model_copy(
        update={
            "model_type": model_type,
            "train_accuracy": metrics_by_partition["TRAIN"]["accuracy"],
            "validation_accuracy": metrics_by_partition["VALIDATION"]["accuracy"],
            "test_accuracy": metrics_by_partition["TEST"]["accuracy"],
            "train_balanced_accuracy": metrics_by_partition["TRAIN"]["balanced_accuracy"],
            "validation_balanced_accuracy": metrics_by_partition["VALIDATION"]["balanced_accuracy"],
            "test_balanced_accuracy": metrics_by_partition["TEST"]["balanced_accuracy"],
            "train_macro_precision": metrics_by_partition["TRAIN"]["macro_precision"],
            "validation_macro_precision": metrics_by_partition["VALIDATION"]["macro_precision"],
            "test_macro_precision": metrics_by_partition["TEST"]["macro_precision"],
            "train_macro_recall": metrics_by_partition["TRAIN"]["macro_recall"],
            "validation_macro_recall": metrics_by_partition["VALIDATION"]["macro_recall"],
            "test_macro_recall": metrics_by_partition["TEST"]["macro_recall"],
            "train_macro_f1": metrics_by_partition["TRAIN"]["macro_f1"],
            "validation_macro_f1": metrics_by_partition["VALIDATION"]["macro_f1"],
            "test_macro_f1": metrics_by_partition["TEST"]["macro_f1"],
            "confusion_matrix_counts": confusion_matrix_counts,
            "per_label_support": dict(label_support),
            "baseline_comparison": baseline_comparison,
            "warnings": warnings,
        }
    )

    timestamp = datetime.now(timezone.utc)
    artifact_manifest = result.artifact_manifest.model_copy(
        update={
            "model_type": model_type,
            "metrics_report_id": metrics_report.metrics_report_id,
            "training_timestamp": timestamp,
            "local_artifact_path": _artifact_path_for_model_type(model_type),
        }
    )
    try:
        validate_historical_model_training_artifact_safety(
            artifact_manifest.model_dump(mode="json"),
            context="historical model training",
        )
    except ValueError as exc:
        gap_entries.append(_artifact_gap(str(exc)))
        return _blocked_training_result(result, gap_entries)

    prediction_count = len(train_ids) + len(validation_ids) + len(test_ids)
    run_report = result.run_report.model_copy(
        update={
            "model_type": model_type,
            "report_only_prediction_count": prediction_count,
            "training_executed": True,
        }
    )
    evaluation_report = result.evaluation_report.model_copy(
        update={
            "model_type": model_type,
            "report_only_prediction_count": prediction_count,
            "runtime_trading_signal_present": False,
            "order_candidate_present": False,
        }
    )
    gap_entries.extend(
        [
            _gap("model-artifact-generated", "TRAINING_MODEL_ARTIFACT_GENERATED", "REPORT_ONLY", "model artifact manifest generated"),
            _gap("artifact-report-only", "TRAINING_ARTIFACT_REPORT_ONLY", "REPORT_ONLY", "artifact manifest remains report-only"),
        ]
    )
    gap_report = _update_gap_report(result, gap_entries)

    return result.model_copy(
        update={
            "run_report": run_report,
            "evaluation_report": evaluation_report,
            "metrics_report": metrics_report,
            "artifact_manifest": artifact_manifest,
            "gap_report": gap_report,
        }
    )


def extract_historical_model_training_feature_rows(training_input: HistoricalModelTrainingInput) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for record in training_input.dataset_records:
        raw_payload = record.feature_block.model_dump(mode="json") if hasattr(record.feature_block, "model_dump") else dict(record.feature_block)
        payload = {
            key: value
            for key, value in raw_payload.items()
            if key
            not in {
                "block_id",
                "read_only",
                "report_only",
                "non_executable",
                "local_file_only",
                "no_network",
                "no_provider_api",
                "no_order",
                "no_llm_runtime",
                "no_ml_training",
            }
        }
        validate_historical_model_training_feature_boundary(
            {"feature_fields": [key.upper() for key in payload.keys()]},
            context="historical model training",
        )
        validate_historical_model_training_metadata_safety(payload, context="historical model training")
        row = {"record_id": record.record_id}
        row.update(payload)
        rows.append(row)
    return rows


def extract_historical_model_training_labels(training_input: HistoricalModelTrainingInput) -> dict[str, str]:
    validate_historical_model_training_label_schema_safety(
        training_input.label_schema.model_dump(mode="json"),
        context="historical model training",
    )
    labels = {}
    for record in training_input.dataset_records:
        label = record.outcome_block.outcome_label
        if label is not None:
            labels[record.record_id] = label
    return labels


def prepare_historical_model_training_splits(training_input: HistoricalModelTrainingInput) -> dict[str, list]:
    split_manifest = training_input.split_manifest
    if split_manifest is None:
        return {"TRAIN": [], "VALIDATION": [], "TEST": []}
    validate_historical_model_training_split_safety(split_manifest.model_dump(mode="json"), context="historical model training")
    records_by_id = {record.record_id: record for record in training_input.dataset_records}
    return {
        "TRAIN": [records_by_id[ref.dataset_record_id] for ref in split_manifest.train_record_refs if ref.dataset_record_id in records_by_id],
        "VALIDATION": [records_by_id[ref.dataset_record_id] for ref in split_manifest.validation_record_refs if ref.dataset_record_id in records_by_id],
        "TEST": [records_by_id[ref.dataset_record_id] for ref in split_manifest.test_record_refs if ref.dataset_record_id in records_by_id],
    }


def _build_optional_sklearn_predictor(
    training_input: HistoricalModelTrainingInput,
    rows_by_record_id: dict[str, dict[str, object]],
    train_ids: list[str],
    train_labels: list[str],
):
    if not train_ids:
        raise ValueError("missing labels")
    feature_fields = [field.lower() for field in training_input.feature_schema.feature_fields]
    train_rows = [rows_by_record_id[record_id] for record_id in train_ids]
    categories_by_field = _fit_feature_categories(train_rows, feature_fields)
    x_train = [_encode_row(rows_by_record_id[record_id], feature_fields, categories_by_field) for record_id in train_ids]
    requested_model_type = training_input.run_config.requested_model_type
    if requested_model_type == HistoricalModelTrainingModelType.LOGISTIC_REGRESSION_OPTIONAL_SKLEARN:
        sklearn_module = importlib.import_module("sklearn.linear_model")
        model = sklearn_module.LogisticRegression(random_state=0, max_iter=200)
    elif requested_model_type == HistoricalModelTrainingModelType.DECISION_TREE_OPTIONAL_SKLEARN:
        sklearn_module = importlib.import_module("sklearn.tree")
        model = sklearn_module.DecisionTreeClassifier(random_state=0)
    elif requested_model_type == HistoricalModelTrainingModelType.RANDOM_FOREST_OPTIONAL_SKLEARN:
        sklearn_module = importlib.import_module("sklearn.ensemble")
        model = sklearn_module.RandomForestClassifier(random_state=0, n_estimators=10)
    else:
        raise ValueError("unsupported model type")
    model.fit(x_train, train_labels)

    def predictor(record_ids: list[str]) -> list[str]:
        rows = [_encode_row(rows_by_record_id[record_id], feature_fields, categories_by_field) for record_id in record_ids]
        return list(model.predict(rows))

    return predictor


def _fit_feature_categories(rows: list[dict[str, object]], feature_fields: list[str]) -> dict[str, list[str]]:
    categories_by_field: dict[str, list[str]] = {}
    for field in feature_fields:
        values = [row.get(field) for row in rows]
        if any(isinstance(value, str) for value in values):
            categories_by_field[field] = sorted({str(value) for value in values})
    return categories_by_field


def _encode_row(row: dict[str, object], feature_fields: list[str], categories_by_field: dict[str, list[str]]) -> list[float]:
    encoded: list[float] = []
    for field in feature_fields:
        value = row.get(field)
        if field in categories_by_field:
            choices = categories_by_field[field]
            encoded.extend(1.0 if str(value) == choice else 0.0 for choice in choices)
        elif isinstance(value, bool):
            encoded.append(1.0 if value else 0.0)
        elif isinstance(value, int | float):
            encoded.append(float(value))
        elif value is None:
            encoded.append(0.0)
        else:
            encoded.append(float(sum(ord(char) for char in str(value))))
    return encoded


def _classification_metrics(actuals: list[str], predictions: list[str], label_values: list[str]) -> dict[str, float | None]:
    if not actuals:
        return {
            "accuracy": None,
            "balanced_accuracy": None,
            "macro_precision": None,
            "macro_recall": None,
            "macro_f1": None,
        }
    correct = sum(1 for actual, predicted in zip(actuals, predictions, strict=True) if actual == predicted)
    accuracy = correct / len(actuals)

    precisions: list[float] = []
    recalls: list[float] = []
    f1_scores: list[float] = []
    for label in label_values:
        tp = sum(1 for actual, predicted in zip(actuals, predictions, strict=True) if actual == label and predicted == label)
        fp = sum(1 for actual, predicted in zip(actuals, predictions, strict=True) if actual != label and predicted == label)
        fn = sum(1 for actual, predicted in zip(actuals, predictions, strict=True) if actual == label and predicted != label)
        precision = tp / (tp + fp) if (tp + fp) else 0.0
        recall = tp / (tp + fn) if (tp + fn) else 0.0
        f1 = (2 * precision * recall / (precision + recall)) if (precision + recall) else 0.0
        precisions.append(precision)
        recalls.append(recall)
        f1_scores.append(f1)
    return {
        "accuracy": accuracy,
        "balanced_accuracy": sum(recalls) / len(recalls) if recalls else None,
        "macro_precision": sum(precisions) / len(precisions) if precisions else None,
        "macro_recall": sum(recalls) / len(recalls) if recalls else None,
        "macro_f1": sum(f1_scores) / len(f1_scores) if f1_scores else None,
    }


def _majority_label(labels: list[str]) -> str:
    counts = Counter(labels)
    highest_count = max(counts.values())
    return sorted(label for label, count in counts.items() if count == highest_count)[0]


def _artifact_path_for_model_type(model_type: HistoricalModelTrainingModelType) -> str:
    return f"artifacts/{model_type.value.lower()}.json"


def _blocked_training_result(training_input: HistoricalModelTrainingInput, gap_entries: list[dict[str, str]]) -> HistoricalModelTrainingInput:
    gap_report = _update_gap_report(training_input, gap_entries)
    run_report = training_input.run_report.model_copy(update={"training_executed": False, "report_only_prediction_count": 0})
    evaluation_report = training_input.evaluation_report.model_copy(
        update={"report_only_prediction_count": 0, "runtime_trading_signal_present": False, "order_candidate_present": False}
    )
    return training_input.model_copy(
        update={
            "run_report": run_report,
            "evaluation_report": evaluation_report,
            "gap_report": gap_report,
        }
    )


def _update_gap_report(training_input: HistoricalModelTrainingInput, gap_entries: list[dict[str, str]]):
    return training_input.gap_report.model_copy(
        update={
            "gap_status": "BLOCKING_GAPS" if any(gap["severity"] == "BLOCKING" for gap in gap_entries) else "NO_GAPS",
            "gap_categories": [gap["gap_category"] for gap in gap_entries],
            "blocking_gap_count": len([gap for gap in gap_entries if gap["severity"] == "BLOCKING"]),
            "report_only_gap_count": len([gap for gap in gap_entries if gap["severity"] != "BLOCKING"]),
            "gaps": gap_entries,
        }
    )


def _split_partition_gaps(training_input: HistoricalModelTrainingInput) -> list[dict[str, str]]:
    split_manifest = training_input.split_manifest
    if split_manifest is None:
        return []
    gaps: list[dict[str, str]] = []
    seen_partition = {}
    all_ids = []
    prior_end = None
    for partition_name, refs in (
        ("TRAIN", split_manifest.train_record_refs),
        ("VALIDATION", split_manifest.validation_record_refs),
        ("TEST", split_manifest.test_record_refs),
    ):
        dates = [ref.replay_anchor_date for ref in refs]
        if dates and dates != sorted(dates):
            gaps.append(_gap(f"{partition_name.lower()}-not-chronological", "TRAINING_SPLIT_NOT_CHRONOLOGICAL", "BLOCKING", f"{partition_name.lower()} split is not chronological"))
        if prior_end is not None and dates and min(dates) < prior_end:
            gaps.append(_gap(f"{partition_name.lower()}-overlap", "TRAINING_SPLIT_NOT_CHRONOLOGICAL", "BLOCKING", f"{partition_name.lower()} split overlaps prior partition"))
        if dates:
            prior_end = max(dates)
        for ref in refs:
            all_ids.append(ref.dataset_record_id)
            prior = seen_partition.get(ref.dataset_record_id)
            if prior is not None and prior != partition_name:
                gaps.append(_gap(f"{partition_name.lower()}-partition-overlap", "TRAINING_SPLIT_NOT_CHRONOLOGICAL", "BLOCKING", "split partition overlap detected"))
            seen_partition[ref.dataset_record_id] = partition_name
    if len(all_ids) != len(set(all_ids)):
        gaps.append(_gap("duplicated-record-id", "TRAINING_SPLIT_NOT_CHRONOLOGICAL", "BLOCKING", "duplicated dataset record id detected"))
    return gaps


def _feature_gap(reason: str) -> dict[str, str]:
    lowered = reason.lower()
    if "outcome label" in lowered:
        return _gap("outcome-label-in-features", "TRAINING_OUTCOME_LABEL_IN_FEATURES_DETECTED", "BLOCKING", "outcome label detected in features")
    if "forward return" in lowered:
        return _gap("forward-return-in-features", "TRAINING_FORWARD_RETURN_IN_FEATURES_DETECTED", "BLOCKING", "forward return detected in features")
    return _gap("post-anchor-actual-in-features", "TRAINING_POST_ANCHOR_ACTUAL_IN_FEATURES_DETECTED", "BLOCKING", "post-anchor actual value detected in features")


def _artifact_gap(reason: str) -> dict[str, str]:
    lowered = reason.lower()
    if "runtime deployment" in lowered:
        return _gap("runtime-signal-detected", "TRAINING_RUNTIME_SIGNAL_DETECTED", "BLOCKING", "runtime trading signal detected")
    if "parquet" in lowered:
        return _gap("unsafe-parquet", "TRAINING_PARQUET_NOT_ALLOWED", "BLOCKING", "parquet not allowed")
    if "credential" in lowered:
        return _gap("unsafe-credential", "TRAINING_CREDENTIALS_NOT_ALLOWED", "BLOCKING", "credentials not allowed")
    if "broker" in lowered:
        return _gap("unsafe-broker", "TRAINING_BROKER_PATH_NOT_ALLOWED", "BLOCKING", "broker path not allowed")
    if "account" in lowered:
        return _gap("unsafe-account", "TRAINING_BROKER_PATH_NOT_ALLOWED", "BLOCKING", "account path not allowed")
    if "order" in lowered:
        return _gap("unsafe-order", "TRAINING_ORDER_FIELD_DETECTED", "BLOCKING", "order field detected")
    if "provider" in lowered:
        return _gap("unsafe-provider", "TRAINING_PROVIDER_SOURCE_NOT_ALLOWED", "BLOCKING", "provider source not allowed")
    if "live" in lowered:
        return _gap("unsafe-live", "TRAINING_LIVE_PROD_NOT_ALLOWED", "BLOCKING", "live/prod not allowed")
    return _gap("unsafe-artifact", "TRAINING_MODEL_ARTIFACT_UNSAFE", "BLOCKING", "model artifact metadata unsafe")


def _feature_or_unsafe_gap(reason: str) -> dict[str, str]:
    lowered = reason.lower()
    if "outcome label" in lowered or "forward return" in lowered or "post-anchor" in lowered:
        return _feature_gap(reason)
    return _unsafe_gap(reason)


def _unsafe_gap(reason: str) -> dict[str, str]:
    lowered = reason.lower()
    mapping = (
        ("buy_sell", "TRAINING_BUY_SELL_WORDING_DETECTED", "buy/sell wording detected"),
        ("runtime_signal", "TRAINING_RUNTIME_SIGNAL_DETECTED", "runtime trading signal detected"),
        ("order_candidate", "TRAINING_ORDER_CANDIDATE_DETECTED", "order candidate detected"),
        ("order", "TRAINING_ORDER_FIELD_DETECTED", "order field detected"),
        ("remote", "TRAINING_REMOTE_SOURCE_NOT_ALLOWED", "remote source not allowed"),
        ("api", "TRAINING_API_SOURCE_NOT_ALLOWED", "api source not allowed"),
        ("network", "TRAINING_NETWORK_SOURCE_NOT_ALLOWED", "network source not allowed"),
        ("provider", "TRAINING_PROVIDER_SOURCE_NOT_ALLOWED", "provider source not allowed"),
        ("cloud_llm", "TRAINING_CLOUD_LLM_NOT_ALLOWED", "cloud llm not allowed"),
        ("local_llm", "TRAINING_LOCAL_LLM_RUNTIME_NOT_ALLOWED", "local llm runtime not allowed"),
        ("crawler", "TRAINING_CRAWLER_TRIGGER_NOT_ALLOWED", "crawler trigger not allowed"),
        ("live_prod", "TRAINING_LIVE_PROD_NOT_ALLOWED", "live/prod not allowed"),
        ("broker", "TRAINING_BROKER_PATH_NOT_ALLOWED", "broker path not allowed"),
        ("credential", "TRAINING_CREDENTIALS_NOT_ALLOWED", "credentials not allowed"),
        ("parquet", "TRAINING_PARQUET_NOT_ALLOWED", "parquet not allowed"),
    )
    for needle, category, message in mapping:
        if needle in lowered:
            return _gap(f"unsafe-{needle}", category, "BLOCKING", message)
    return _gap("unsafe-training-metadata", "TRAINING_REMOTE_SOURCE_NOT_ALLOWED", "BLOCKING", "unsafe training metadata detected")


def _gap(gap_id: str, category: str, severity: str, message: str) -> dict[str, str]:
    return {
        "gap_id": gap_id.upper(),
        "gap_category": category,
        "severity": severity,
        "message": message,
    }
