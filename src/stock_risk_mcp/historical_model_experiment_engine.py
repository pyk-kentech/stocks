from __future__ import annotations

from stock_risk_mcp.historical_model_experiment_guard import (
    validate_historical_model_experiment_artifact_safety,
    validate_historical_model_experiment_comparison_safety,
    validate_historical_model_experiment_metadata_safety,
    validate_historical_model_experiment_promotion_block,
)
from stock_risk_mcp.historical_model_experiment_models import (
    HistoricalModelExperimentRegistryInput,
    HistoricalModelTrainingModelType,
)


def build_historical_model_experiment_registry(
    registry_input: HistoricalModelExperimentRegistryInput,
) -> HistoricalModelExperimentRegistryInput:
    gap_entries: list[dict[str, str]] = []

    for audit in registry_input.audit_records:
        try:
            validate_historical_model_experiment_metadata_safety(
                {
                    "operator_context": audit.operator_context,
                    "source_path": audit.source_path,
                },
                context="historical model experiment",
            )
        except ValueError as exc:
            gap_entries.append(_unsafe_gap(str(exc)))

    if registry_input.training_run_report is None:
        gap_entries.append(_gap("missing-training-run-report", "EXPERIMENT_MISSING_TRAINING_RUN_REPORT", "BLOCKING", "missing training run report"))
    if registry_input.evaluation_report is None:
        gap_entries.append(_gap("missing-evaluation-report", "EXPERIMENT_MISSING_EVALUATION_REPORT", "BLOCKING", "missing evaluation report"))
    if registry_input.metrics_report is None:
        gap_entries.append(_gap("missing-metrics-report", "EXPERIMENT_MISSING_METRICS_REPORT", "BLOCKING", "missing metrics report"))
    if registry_input.artifact_manifest is None:
        gap_entries.append(_gap("missing-artifact-manifest", "EXPERIMENT_MISSING_ARTIFACT_MANIFEST", "BLOCKING", "missing artifact manifest"))
    if registry_input.training_safety_report is None:
        gap_entries.append(_gap("missing-safety-report", "EXPERIMENT_MISSING_SAFETY_REPORT", "BLOCKING", "missing safety report"))

    for record in registry_input.experiment_records:
        try:
            validate_historical_model_experiment_metadata_safety(
                {"model_metadata": _record_value(record, "model_metadata") or {}},
                context="historical model experiment",
            )
        except ValueError as exc:
            gap_entries.append(_unsafe_gap(str(exc)))

    if registry_input.artifact_manifest is not None:
        try:
            validate_historical_model_experiment_artifact_safety(
                _dump(registry_input.artifact_manifest),
                context="historical model experiment",
            )
        except ValueError as exc:
            gap_entries.append(_gap("unsafe-artifact-metadata", "EXPERIMENT_UNSAFE_ARTIFACT_METADATA", "BLOCKING", "unsafe artifact metadata detected"))
            gap_entries.append(_unsafe_gap(str(exc)))

    try:
        validate_historical_model_experiment_promotion_block(
            registry_input.promotion_block_report.model_dump(mode="json"),
            context="historical model experiment",
        )
    except ValueError:
        gap_entries.append(_gap("promotion-block-broken", "EXPERIMENT_DEPLOYMENT_BLOCKED", "BLOCKING", "promotion block must remain blocked-by-default"))

    try:
        validate_historical_model_experiment_comparison_safety(
            {
                "compared_experiment_ids": registry_input.comparison_report.compared_experiment_ids,
                "compared_metric_names": registry_input.comparison_report.compared_metric_names,
            },
            context="historical model experiment",
        )
    except ValueError as exc:
        gap_entries.append(_unsafe_gap(str(exc)))

    if not registry_input.experiment_records:
        gap_entries.append(_gap("missing-input", "EXPERIMENT_MISSING_INPUT", "BLOCKING", "missing experiment input"))
    if any(not _record_value(record, "dataset_manifest_id") for record in registry_input.experiment_records):
        gap_entries.append(_gap("missing-dataset-lineage", "EXPERIMENT_MISSING_DATASET_LINEAGE", "BLOCKING", "missing dataset lineage"))
    if registry_input.split_manifest is None:
        gap_entries.append(_gap("missing-split-lineage", "EXPERIMENT_MISSING_SPLIT_LINEAGE", "BLOCKING", "missing split lineage"))
    if registry_input.leakage_audit_report is None:
        gap_entries.append(_gap("missing-leakage-audit-lineage", "EXPERIMENT_MISSING_LEAKAGE_AUDIT_LINEAGE", "REPORT_ONLY", "missing leakage audit lineage"))

    metrics_report = registry_input.metrics_report
    baseline_report = registry_input.baseline_evaluation_report

    overfit_risk = False
    low_label_support = False
    severe_label_imbalance = False
    train_test_metric_gap = False
    weak_baseline_improvement = False
    optional_sklearn_dependency_risk = False
    unsupported_model_type = False
    unsafe_artifact_metadata = any(
        gap["gap_category"]
        in {
            "EXPERIMENT_UNSAFE_ARTIFACT_METADATA",
            "EXPERIMENT_PRODUCTION_DEPLOYMENT_NOT_ALLOWED",
            "EXPERIMENT_LIVE_INFERENCE_NOT_ALLOWED",
            "EXPERIMENT_RUNTIME_SIGNAL_DETECTED",
            "EXPERIMENT_ORDER_CANDIDATE_DETECTED",
            "EXPERIMENT_ORDER_FIELD_DETECTED",
            "EXPERIMENT_BROKER_PATH_NOT_ALLOWED",
            "EXPERIMENT_ACCOUNT_METADATA_NOT_ALLOWED",
            "EXPERIMENT_CREDENTIALS_NOT_ALLOWED",
            "EXPERIMENT_REMOTE_SOURCE_NOT_ALLOWED",
            "EXPERIMENT_API_SOURCE_NOT_ALLOWED",
            "EXPERIMENT_NETWORK_SOURCE_NOT_ALLOWED",
            "EXPERIMENT_PROVIDER_SOURCE_NOT_ALLOWED",
            "EXPERIMENT_CLOUD_LLM_NOT_ALLOWED",
            "EXPERIMENT_LOCAL_LLM_RUNTIME_NOT_ALLOWED",
            "EXPERIMENT_CRAWLER_TRIGGER_NOT_ALLOWED",
            "EXPERIMENT_LIVE_PROD_NOT_ALLOWED",
            "EXPERIMENT_PARQUET_NOT_ALLOWED",
        }
        for gap in gap_entries
    )

    if metrics_report is not None:
        train_accuracy = metrics_report.train_accuracy
        test_accuracy = metrics_report.test_accuracy
        if train_accuracy is not None and test_accuracy is not None:
            gap = train_accuracy - test_accuracy
            if gap >= 0.5:
                overfit_risk = True
                train_test_metric_gap = True
                gap_entries.append(_gap("overfit-risk-detected", "EXPERIMENT_OVERFIT_RISK_DETECTED", "REPORT_ONLY", "overfit risk detected"))
                gap_entries.append(_gap("train-test-gap-detected", "EXPERIMENT_TRAIN_TEST_METRIC_GAP", "REPORT_ONLY", "train/test metric gap detected"))

        per_label_support = getattr(metrics_report, "per_label_support", {}) or {}
        if per_label_support and any(count <= 2 for count in per_label_support.values()):
            low_label_support = True
            gap_entries.append(_gap("low-label-support", "EXPERIMENT_LOW_LABEL_SUPPORT", "REPORT_ONLY", "low label support detected"))
        if per_label_support and len(per_label_support) > 1:
            max_count = max(per_label_support.values())
            min_count = min(per_label_support.values())
            if min_count > 0 and max_count / min_count >= 4:
                severe_label_imbalance = True
                gap_entries.append(_gap("severe-label-imbalance", "EXPERIMENT_SEVERE_LABEL_IMBALANCE", "REPORT_ONLY", "severe label imbalance detected"))

    if baseline_report is not None and metrics_report is not None:
        baseline_accuracy = baseline_report.accuracy
        test_accuracy = metrics_report.test_accuracy
        if baseline_accuracy is not None and test_accuracy is not None:
            improvement = test_accuracy - baseline_accuracy
            if improvement <= 0.05:
                weak_baseline_improvement = True
                gap_entries.append(_gap("weak-baseline-improvement", "EXPERIMENT_WEAK_BASELINE_IMPROVEMENT", "REPORT_ONLY", "weak baseline improvement detected"))

    for record in registry_input.experiment_records:
        model_type = _record_value(record, "model_type")
        if model_type in {
            HistoricalModelTrainingModelType.LOGISTIC_REGRESSION_OPTIONAL_SKLEARN,
            HistoricalModelTrainingModelType.DECISION_TREE_OPTIONAL_SKLEARN,
            HistoricalModelTrainingModelType.RANDOM_FOREST_OPTIONAL_SKLEARN,
            "LOGISTIC_REGRESSION_OPTIONAL_SKLEARN",
            "DECISION_TREE_OPTIONAL_SKLEARN",
            "RANDOM_FOREST_OPTIONAL_SKLEARN",
        }:
            optional_sklearn_dependency_risk = True
            gap_entries.append(_gap("optional-sklearn-risk", "EXPERIMENT_OPTIONAL_SKLEARN_DEPENDENCY_RISK", "REPORT_ONLY", "optional sklearn dependency risk"))

        if model_type not in {
            HistoricalModelTrainingModelType.DUMMY_MAJORITY,
            HistoricalModelTrainingModelType.DUMMY_PRIOR,
            HistoricalModelTrainingModelType.LOGISTIC_REGRESSION_OPTIONAL_SKLEARN,
            HistoricalModelTrainingModelType.DECISION_TREE_OPTIONAL_SKLEARN,
            HistoricalModelTrainingModelType.RANDOM_FOREST_OPTIONAL_SKLEARN,
            "DUMMY_MAJORITY",
            "DUMMY_PRIOR",
            "LOGISTIC_REGRESSION_OPTIONAL_SKLEARN",
            "DECISION_TREE_OPTIONAL_SKLEARN",
            "RANDOM_FOREST_OPTIONAL_SKLEARN",
        }:
            unsupported_model_type = True
            gap_entries.append(_gap("unsupported-model-type", "EXPERIMENT_UNSUPPORTED_MODEL_TYPE", "BLOCKING", "unsupported model type"))

    gap_entries.extend(
        [
            _gap("registry-report-generated", "EXPERIMENT_REGISTRY_REPORT_GENERATED", "REPORT_ONLY", "experiment registry report generated"),
            _gap("experiment-report-only", "EXPERIMENT_REPORT_ONLY", "REPORT_ONLY", "experiment governance remains report-only"),
            _gap("experiment-local-only", "EXPERIMENT_LOCAL_ONLY", "REPORT_ONLY", "experiment governance remains local-only"),
            _gap("experiment-offline-only", "EXPERIMENT_OFFLINE_ONLY", "REPORT_ONLY", "experiment governance remains offline-only"),
            _gap("promotion-block-generated", "EXPERIMENT_PROMOTION_BLOCK_GENERATED", "REPORT_ONLY", "promotion block report generated"),
            _gap("production-use-blocked", "EXPERIMENT_PRODUCTION_USE_BLOCKED", "REPORT_ONLY", "production use blocked"),
            _gap("live-inference-blocked", "EXPERIMENT_LIVE_INFERENCE_BLOCKED", "REPORT_ONLY", "live inference blocked"),
            _gap("runtime-signal-blocked", "EXPERIMENT_RUNTIME_SIGNAL_BLOCKED", "REPORT_ONLY", "runtime signal blocked"),
            _gap("order-candidate-blocked", "EXPERIMENT_ORDER_CANDIDATE_BLOCKED", "REPORT_ONLY", "order candidate blocked"),
            _gap("paper-trading-blocked", "EXPERIMENT_PAPER_TRADING_BLOCKED", "REPORT_ONLY", "paper trading blocked"),
            _gap("deployment-blocked", "EXPERIMENT_DEPLOYMENT_BLOCKED", "REPORT_ONLY", "deployment blocked"),
        ]
    )

    comparison_report = registry_input.comparison_report.model_copy(
        update={
            "compared_experiment_ids": [_record_value(record, "experiment_id") for record in registry_input.experiment_records],
            "compared_metric_names": [
                "VALIDATION_ACCURACY",
                "TEST_ACCURACY",
                "BALANCED_ACCURACY",
                "MACRO_F1",
                "CONFUSION_MATRIX_SUMMARY",
                "BASELINE_IMPROVEMENT",
                "OVERFIT_GAP",
                "LOW_SUPPORT_WARNINGS",
                "SAFETY_BLOCKED_STATUS",
            ],
            "validation_accuracy_delta": metrics_report.validation_accuracy if metrics_report is not None else None,
            "test_accuracy_delta": metrics_report.test_accuracy if metrics_report is not None else None,
            "balanced_accuracy_delta": getattr(metrics_report, "test_balanced_accuracy", None) if metrics_report is not None else None,
            "macro_f1_delta": getattr(metrics_report, "test_macro_f1", None) if metrics_report is not None else None,
            "baseline_improvement_delta": (
                (metrics_report.test_accuracy - baseline_report.accuracy)
                if metrics_report is not None and baseline_report is not None and metrics_report.test_accuracy is not None and baseline_report.accuracy is not None
                else None
            ),
            "safety_blocked": True,
        }
    )

    risk_review_report = registry_input.risk_review_report.model_copy(
        update={
            "overfit_risk": overfit_risk,
            "low_label_support": low_label_support,
            "severe_label_imbalance": severe_label_imbalance,
            "train_test_metric_gap": train_test_metric_gap,
            "weak_baseline_improvement": weak_baseline_improvement,
            "missing_leakage_audit_lineage": registry_input.leakage_audit_report is None,
            "missing_validation_split_lineage": registry_input.split_manifest is None,
            "unsafe_artifact_metadata": unsafe_artifact_metadata,
            "optional_sklearn_dependency_risk": optional_sklearn_dependency_risk,
            "unsupported_model_type": unsupported_model_type,
            "missing_safety_flags": False,
        }
    )

    lineage_report = registry_input.lineage_report.model_copy(
        update={
            "leakage_audit_lineage_present": registry_input.leakage_audit_report is not None,
            "validation_split_lineage_present": registry_input.split_manifest is not None,
            "artifact_manifest_lineage_present": registry_input.artifact_manifest is not None,
        }
    )

    registry_report = registry_input.registry_report.model_copy(
        update={
            "experiment_count": len(registry_input.experiment_records),
            "blocked_experiment_count": len(registry_input.experiment_records),
        }
    )

    gap_report = registry_input.gap_report.model_copy(
        update={
            "gap_status": "BLOCKING_GAPS" if any(item["severity"] == "BLOCKING" for item in gap_entries) else "NO_GAPS",
            "gap_categories": [item["gap_category"] for item in gap_entries],
            "blocking_gap_count": len([item for item in gap_entries if item["severity"] == "BLOCKING"]),
            "report_only_gap_count": len([item for item in gap_entries if item["severity"] != "BLOCKING"]),
            "gaps": gap_entries,
        }
    )

    return registry_input.model_copy(
        update={
            "registry_report": registry_report,
            "comparison_report": comparison_report,
            "risk_review_report": risk_review_report,
            "promotion_block_report": registry_input.promotion_block_report,
            "lineage_report": lineage_report,
            "gap_report": gap_report,
        }
    )


def _unsafe_gap(reason: str) -> dict[str, str]:
    lowered = reason.lower()
    mapping = (
        ("deployment", "EXPERIMENT_PRODUCTION_DEPLOYMENT_NOT_ALLOWED", "production deployment not allowed"),
        ("live_inference", "EXPERIMENT_LIVE_INFERENCE_NOT_ALLOWED", "live inference not allowed"),
        ("runtime_signal", "EXPERIMENT_RUNTIME_SIGNAL_DETECTED", "runtime signal detected"),
        ("order_candidate", "EXPERIMENT_ORDER_CANDIDATE_DETECTED", "order candidate detected"),
        ("order", "EXPERIMENT_ORDER_FIELD_DETECTED", "order field detected"),
        ("buy_sell", "EXPERIMENT_BUY_SELL_WORDING_DETECTED", "buy/sell wording detected"),
        ("broker", "EXPERIMENT_BROKER_PATH_NOT_ALLOWED", "broker path not allowed"),
        ("account", "EXPERIMENT_ACCOUNT_METADATA_NOT_ALLOWED", "account metadata not allowed"),
        ("credential", "EXPERIMENT_CREDENTIALS_NOT_ALLOWED", "credentials not allowed"),
        ("remote", "EXPERIMENT_REMOTE_SOURCE_NOT_ALLOWED", "remote source not allowed"),
        ("api", "EXPERIMENT_API_SOURCE_NOT_ALLOWED", "api source not allowed"),
        ("network", "EXPERIMENT_NETWORK_SOURCE_NOT_ALLOWED", "network source not allowed"),
        ("provider", "EXPERIMENT_PROVIDER_SOURCE_NOT_ALLOWED", "provider source not allowed"),
        ("cloud_llm", "EXPERIMENT_CLOUD_LLM_NOT_ALLOWED", "cloud llm not allowed"),
        ("local_llm", "EXPERIMENT_LOCAL_LLM_RUNTIME_NOT_ALLOWED", "local llm runtime not allowed"),
        ("crawler", "EXPERIMENT_CRAWLER_TRIGGER_NOT_ALLOWED", "crawler trigger not allowed"),
        ("live_prod", "EXPERIMENT_LIVE_PROD_NOT_ALLOWED", "live/prod not allowed"),
        ("parquet", "EXPERIMENT_PARQUET_NOT_ALLOWED", "parquet not allowed"),
        ("paper_trading", "EXPERIMENT_PAPER_TRADING_BLOCKED", "paper trading blocked"),
        ("live_ranking", "EXPERIMENT_LIVE_INFERENCE_NOT_ALLOWED", "live-use ranking not allowed"),
    )
    for needle, category, message in mapping:
        if needle in lowered:
            severity = "BLOCKING" if category not in {"EXPERIMENT_PAPER_TRADING_BLOCKED"} else "REPORT_ONLY"
            return _gap(f"unsafe-{needle}", category, severity, message)
    return _gap("unsafe-experiment-metadata", "EXPERIMENT_UNSAFE_ARTIFACT_METADATA", "BLOCKING", "unsafe experiment metadata detected")


def _gap(gap_id: str, category: str, severity: str, message: str) -> dict[str, str]:
    return {
        "gap_id": gap_id.upper(),
        "gap_category": category,
        "severity": severity,
        "message": message,
    }


def _dump(value):
    return value.model_dump(mode="json") if hasattr(value, "model_dump") else value


def _record_value(record, field_name: str):
    if hasattr(record, field_name):
        return getattr(record, field_name)
    if isinstance(record, dict):
        return record.get(field_name)
    return None
