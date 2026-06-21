import copy

from stock_risk_mcp.historical_model_experiment_engine import build_historical_model_experiment_registry
from stock_risk_mcp.historical_model_experiment_models import HistoricalModelExperimentRegistryInput
from tests.test_historical_model_experiment_models import historical_model_experiment_fixture_payload


def build_input(payload=None):
    return HistoricalModelExperimentRegistryInput.model_validate(payload or historical_model_experiment_fixture_payload())


def _engine_payload():
    payload = historical_model_experiment_fixture_payload()
    payload["metrics_report"]["train_accuracy"] = 0.85
    payload["metrics_report"]["validation_accuracy"] = 0.60
    payload["metrics_report"]["test_accuracy"] = 0.55
    payload["metrics_report"]["train_balanced_accuracy"] = 0.82
    payload["metrics_report"]["validation_balanced_accuracy"] = 0.58
    payload["metrics_report"]["test_balanced_accuracy"] = 0.54
    payload["metrics_report"]["train_macro_f1"] = 0.80
    payload["metrics_report"]["validation_macro_f1"] = 0.57
    payload["metrics_report"]["test_macro_f1"] = 0.53
    payload["metrics_report"]["confusion_matrix_counts"] = {"TEST|OUTCOME_FAVORABLE|OUTCOME_FAVORABLE": 1}
    payload["metrics_report"]["per_label_support"] = {"OUTCOME_FAVORABLE": 3, "OUTCOME_ADVERSE": 3}
    payload["metrics_report"]["warnings"] = []
    payload["baseline_evaluation_report"]["accuracy"] = 0.40
    payload["training_run_report"]["report_only_prediction_count"] = 4
    payload["training_run_report"]["training_executed"] = True
    payload["evaluation_report"]["report_only_prediction_count"] = 4
    return payload


def test_build_historical_model_experiment_registry_success_path():
    result = build_historical_model_experiment_registry(build_input(_engine_payload()))

    assert result.registry_report.experiment_count == 1
    assert result.registry_report.blocked_experiment_count == 1
    assert result.comparison_report.validation_accuracy_delta == 0.60
    assert result.comparison_report.test_accuracy_delta == 0.55
    assert result.comparison_report.safety_blocked is True
    assert result.risk_review_report.overfit_risk is False
    assert result.promotion_block_report.production_use_allowed is False
    assert result.lineage_report.artifact_manifest_lineage_present is True


def test_build_historical_model_experiment_registry_reports_missing_training_run_report_gap():
    registry_input = build_input(_engine_payload()).model_copy(update={"training_run_report": None})

    result = build_historical_model_experiment_registry(registry_input)

    assert any(item["gap_category"] == "EXPERIMENT_MISSING_TRAINING_RUN_REPORT" for item in result.gap_report.gaps)


def test_build_historical_model_experiment_registry_reports_missing_metrics_report_gap():
    registry_input = build_input(_engine_payload()).model_copy(update={"metrics_report": None})

    result = build_historical_model_experiment_registry(registry_input)

    assert any(item["gap_category"] == "EXPERIMENT_MISSING_METRICS_REPORT" for item in result.gap_report.gaps)


def test_build_historical_model_experiment_registry_reports_missing_artifact_manifest_gap():
    registry_input = build_input(_engine_payload()).model_copy(update={"artifact_manifest": None})

    result = build_historical_model_experiment_registry(registry_input)

    assert any(item["gap_category"] == "EXPERIMENT_MISSING_ARTIFACT_MANIFEST" for item in result.gap_report.gaps)


def test_build_historical_model_experiment_registry_reports_missing_safety_report_gap():
    registry_input = build_input(_engine_payload()).model_copy(update={"training_safety_report": None})

    result = build_historical_model_experiment_registry(registry_input)

    assert any(item["gap_category"] == "EXPERIMENT_MISSING_SAFETY_REPORT" for item in result.gap_report.gaps)


def test_build_historical_model_experiment_registry_reports_missing_dataset_lineage_gap():
    registry_input = build_input(_engine_payload())
    experiment_record = copy.deepcopy(registry_input.experiment_records[0].model_dump(mode="json"))
    experiment_record["dataset_manifest_id"] = ""
    registry_input = registry_input.model_copy(update={"experiment_records": [experiment_record]})

    result = build_historical_model_experiment_registry(registry_input)

    assert any(item["gap_category"] == "EXPERIMENT_MISSING_DATASET_LINEAGE" for item in result.gap_report.gaps)


def test_build_historical_model_experiment_registry_reports_missing_split_lineage_gap():
    registry_input = build_input(_engine_payload()).model_copy(update={"split_manifest": None})

    result = build_historical_model_experiment_registry(registry_input)

    assert any(item["gap_category"] == "EXPERIMENT_MISSING_SPLIT_LINEAGE" for item in result.gap_report.gaps)


def test_build_historical_model_experiment_comparison_report_does_not_rank_for_live_use():
    result = build_historical_model_experiment_registry(build_input(_engine_payload()))

    dumped = result.comparison_report.model_dump(mode="json")
    assert "live_rank" not in str(dumped).lower()
    assert "buy" not in str(dumped).lower()


def test_build_historical_model_experiment_registry_reports_weak_baseline_improvement_warning():
    payload = _engine_payload()
    payload["baseline_evaluation_report"]["accuracy"] = 0.54
    payload["metrics_report"]["test_accuracy"] = 0.55

    result = build_historical_model_experiment_registry(build_input(payload))

    assert result.risk_review_report.weak_baseline_improvement is True
    assert any(item["gap_category"] == "EXPERIMENT_WEAK_BASELINE_IMPROVEMENT" for item in result.gap_report.gaps)


def test_build_historical_model_experiment_registry_reports_overfit_risk_warning():
    payload = _engine_payload()
    payload["metrics_report"]["train_accuracy"] = 0.95
    payload["metrics_report"]["test_accuracy"] = 0.30

    result = build_historical_model_experiment_registry(build_input(payload))

    assert result.risk_review_report.overfit_risk is True
    assert any(item["gap_category"] == "EXPERIMENT_OVERFIT_RISK_DETECTED" for item in result.gap_report.gaps)


def test_build_historical_model_experiment_registry_reports_low_label_support_warning():
    payload = _engine_payload()
    payload["metrics_report"]["per_label_support"] = {"OUTCOME_FAVORABLE": 1}

    result = build_historical_model_experiment_registry(build_input(payload))

    assert result.risk_review_report.low_label_support is True
    assert any(item["gap_category"] == "EXPERIMENT_LOW_LABEL_SUPPORT" for item in result.gap_report.gaps)


def test_build_historical_model_experiment_registry_reports_severe_label_imbalance_warning():
    payload = _engine_payload()
    payload["metrics_report"]["per_label_support"] = {"OUTCOME_FAVORABLE": 10, "OUTCOME_ADVERSE": 1}

    result = build_historical_model_experiment_registry(build_input(payload))

    assert result.risk_review_report.severe_label_imbalance is True
    assert any(item["gap_category"] == "EXPERIMENT_SEVERE_LABEL_IMBALANCE" for item in result.gap_report.gaps)


def test_build_historical_model_experiment_risk_review_success_path():
    result = build_historical_model_experiment_registry(build_input(_engine_payload()))

    assert result.risk_review_report.unsafe_artifact_metadata is False
    assert result.risk_review_report.missing_safety_flags is False


def test_build_historical_model_experiment_registry_blocks_unsafe_artifact_metadata():
    registry_input = build_input(_engine_payload())
    artifact = registry_input.artifact_manifest.model_dump(mode="json")
    artifact["deployment_path"] = "registry/unsafe"
    registry_input = registry_input.model_copy(update={"artifact_manifest": artifact})

    result = build_historical_model_experiment_registry(registry_input)

    assert result.risk_review_report.unsafe_artifact_metadata is True
    assert any(item["gap_category"] == "EXPERIMENT_UNSAFE_ARTIFACT_METADATA" for item in result.gap_report.gaps)


def test_build_historical_model_experiment_registry_flags_optional_sklearn_dependency_risk():
    payload = _engine_payload()
    payload["experiment_records"][0]["model_type"] = "LOGISTIC_REGRESSION_OPTIONAL_SKLEARN"
    payload["training_run_report"]["model_type"] = "LOGISTIC_REGRESSION_OPTIONAL_SKLEARN"
    payload["evaluation_report"]["model_type"] = "LOGISTIC_REGRESSION_OPTIONAL_SKLEARN"
    payload["metrics_report"]["model_type"] = "LOGISTIC_REGRESSION_OPTIONAL_SKLEARN"
    payload["artifact_manifest"]["model_type"] = "LOGISTIC_REGRESSION_OPTIONAL_SKLEARN"

    result = build_historical_model_experiment_registry(build_input(payload))

    assert result.risk_review_report.optional_sklearn_dependency_risk is True
    assert any(item["gap_category"] == "EXPERIMENT_OPTIONAL_SKLEARN_DEPENDENCY_RISK" for item in result.gap_report.gaps)


def test_build_historical_model_experiment_promotion_blocks_remain_false():
    result = build_historical_model_experiment_registry(build_input(_engine_payload()))

    assert result.promotion_block_report.production_use_allowed is False
    assert result.promotion_block_report.live_inference_allowed is False
    assert result.promotion_block_report.runtime_trading_signal_allowed is False
    assert result.promotion_block_report.order_candidate_allowed is False
    assert result.promotion_block_report.paper_trading_allowed is False
    assert result.promotion_block_report.deployment_allowed is False


def test_build_historical_model_experiment_lineage_report_success_path():
    result = build_historical_model_experiment_registry(build_input(_engine_payload()))

    assert result.lineage_report.leakage_audit_lineage_present is True
    assert result.lineage_report.validation_split_lineage_present is True
    assert result.lineage_report.artifact_manifest_lineage_present is True


def test_build_historical_model_experiment_registry_rejects_unsafe_marker():
    registry_input = build_input(_engine_payload())
    experiment_record = copy.deepcopy(registry_input.experiment_records[0].model_dump(mode="json"))
    experiment_record["model_metadata"]["runtime_signal"] = "unsafe"
    experiment_records = [experiment_record]
    registry_input = registry_input.model_copy(update={"experiment_records": experiment_records})

    result = build_historical_model_experiment_registry(registry_input)

    assert any(item["gap_category"] == "EXPERIMENT_RUNTIME_SIGNAL_DETECTED" for item in result.gap_report.gaps)


def test_build_historical_model_experiment_registry_rejects_parquet():
    registry_input = build_input(_engine_payload())
    artifact = registry_input.artifact_manifest.model_dump(mode="json")
    artifact["local_artifact_path"] = "artifacts/model.parquet"
    registry_input = registry_input.model_copy(update={"artifact_manifest": artifact})

    result = build_historical_model_experiment_registry(registry_input)

    assert any(item["gap_category"] == "EXPERIMENT_PARQUET_NOT_ALLOWED" for item in result.gap_report.gaps)
