import json

import pytest

from stock_risk_mcp.historical_model_experiment_fixture import load_historical_model_experiment_fixture
from stock_risk_mcp.historical_model_experiment_guard import (
    validate_historical_model_experiment_artifact_safety,
    validate_historical_model_experiment_comparison_safety,
    validate_historical_model_experiment_metadata_safety,
    validate_historical_model_experiment_promotion_block,
)
from stock_risk_mcp.historical_model_experiment_models import (
    HistoricalModelComparisonReport,
    HistoricalModelExperimentGapCategory,
    HistoricalModelExperimentLineageReport,
    HistoricalModelExperimentRecord,
    HistoricalModelExperimentRegistryConfig,
    HistoricalModelExperimentRegistryInput,
    HistoricalModelExperimentRegistryReport,
    HistoricalModelExperimentSafetyReport,
    HistoricalModelRiskReviewReport,
    HistoricalModelPromotionBlockReport,
)
from tests.test_historical_model_training_models import historical_model_training_fixture_payload


def historical_model_experiment_fixture_payload():
    training_payload = historical_model_training_fixture_payload()
    return {
        "schema_version": "5.8-historical-model-experiment-registry-input",
        "registry_input_id": "historical-model-experiment-registry-input-1",
        "registry_config": {
            "config_id": "historical-model-experiment-registry-config-1",
            "strategy_track": "DOMESTIC_KR",
        },
        "experiment_records": [
            {
                "experiment_id": "historical-model-experiment-1",
                "model_type": "DUMMY_MAJORITY",
                "dataset_manifest_id": "DATASET-EXPORT-MANIFEST-1",
                "split_manifest_id": "DATASET-SPLIT-MANIFEST-1",
                "feature_schema_version": "5.4-HISTORICAL-DATASET-FEATURE-BLOCK",
                "label_schema_version": "5.4-HISTORICAL-DATASET-OUTCOME-BLOCK",
                "metrics_report_id": "HISTORICAL-MODEL-METRICS-REPORT-1",
                "artifact_manifest_id": "HISTORICAL-MODEL-ARTIFACT-MANIFEST-1",
                "safety_report_id": "HISTORICAL-MODEL-SAFETY-REPORT-1",
                "training_timestamp": "2026-06-18T17:00:00+09:00",
                "model_metadata": {"sandbox_origin": "offline"},
                "source_manifest_ids": ["MANIFEST-1", "CALENDAR-MANIFEST-1"],
                "source_audit_record_ids": ["AUDIT-1"],
                "provider_provenance_ids": ["PROVENANCE-1"],
            }
        ],
        "training_run_report": training_payload["run_report"],
        "evaluation_report": training_payload["evaluation_report"],
        "metrics_report": training_payload["metrics_report"],
        "artifact_manifest": training_payload["artifact_manifest"],
        "training_safety_report": training_payload["safety_report"],
        "training_gap_report": training_payload["gap_report"],
        "baseline_evaluation_report": training_payload["baseline_evaluation_report"],
        "split_manifest": training_payload["split_manifest"],
        "leakage_audit_report": training_payload["leakage_audit_report"],
        "registry_report": {
            "registry_report_id": "historical-model-experiment-registry-report-1",
            "registry_input_id": "historical-model-experiment-registry-input-1",
            "experiment_count": 1,
            "blocked_experiment_count": 1,
            "source_manifest_ids": ["MANIFEST-1", "CALENDAR-MANIFEST-1"],
            "source_audit_record_ids": ["AUDIT-1"],
            "provider_provenance_ids": ["PROVENANCE-1"],
        },
        "comparison_report": {
            "comparison_report_id": "historical-model-comparison-report-1",
            "registry_input_id": "historical-model-experiment-registry-input-1",
            "compared_experiment_ids": ["HISTORICAL-MODEL-EXPERIMENT-1"],
            "compared_metric_names": ["VALIDATION_ACCURACY", "TEST_ACCURACY"],
            "validation_accuracy_delta": 0.0,
            "test_accuracy_delta": 0.0,
            "balanced_accuracy_delta": 0.0,
            "macro_f1_delta": 0.0,
            "baseline_improvement_delta": 0.0,
            "safety_blocked": True,
            "source_manifest_ids": ["MANIFEST-1", "CALENDAR-MANIFEST-1"],
            "source_audit_record_ids": ["AUDIT-1"],
            "provider_provenance_ids": ["PROVENANCE-1"],
        },
        "risk_review_report": {
            "risk_review_report_id": "historical-model-risk-review-report-1",
            "registry_input_id": "historical-model-experiment-registry-input-1",
            "overfit_risk": False,
            "low_label_support": False,
            "severe_label_imbalance": False,
            "train_test_metric_gap": False,
            "weak_baseline_improvement": False,
            "missing_leakage_audit_lineage": False,
            "missing_validation_split_lineage": False,
            "unsafe_artifact_metadata": False,
            "optional_sklearn_dependency_risk": False,
            "unsupported_model_type": False,
            "missing_safety_flags": False,
            "source_manifest_ids": ["MANIFEST-1", "CALENDAR-MANIFEST-1"],
            "source_audit_record_ids": ["AUDIT-1"],
            "provider_provenance_ids": ["PROVENANCE-1"],
        },
        "promotion_block_report": {
            "promotion_block_report_id": "historical-model-promotion-block-report-1",
            "registry_input_id": "historical-model-experiment-registry-input-1",
            "production_use_allowed": False,
            "live_inference_allowed": False,
            "runtime_trading_signal_allowed": False,
            "order_candidate_allowed": False,
            "paper_trading_allowed": False,
            "broker_path_allowed": False,
            "live_prod_allowed": False,
            "deployment_allowed": False,
            "source_manifest_ids": ["MANIFEST-1", "CALENDAR-MANIFEST-1"],
            "source_audit_record_ids": ["AUDIT-1"],
            "provider_provenance_ids": ["PROVENANCE-1"],
        },
        "lineage_report": {
            "lineage_report_id": "historical-model-lineage-report-1",
            "registry_input_id": "historical-model-experiment-registry-input-1",
            "leakage_audit_lineage_present": True,
            "validation_split_lineage_present": True,
            "artifact_manifest_lineage_present": True,
            "source_manifest_ids": ["MANIFEST-1", "CALENDAR-MANIFEST-1"],
            "source_audit_record_ids": ["AUDIT-1"],
            "provider_provenance_ids": ["PROVENANCE-1"],
        },
        "safety_report": {
            "safety_report_id": "historical-model-experiment-safety-report-1",
        },
        "gap_report": {
            "gap_report_id": "historical-model-experiment-gap-report-1",
            "registry_input_id": "historical-model-experiment-registry-input-1",
            "gap_status": "NO_GAPS",
            "gap_categories": [],
            "blocking_gap_count": 0,
            "report_only_gap_count": 0,
            "gaps": [],
            "source_manifest_ids": ["MANIFEST-1", "CALENDAR-MANIFEST-1"],
            "source_audit_record_ids": ["AUDIT-1"],
            "provider_provenance_ids": ["PROVENANCE-1"],
        },
        "audit_records": [
            {
                "audit_record_id": "historical-model-experiment-audit-record-1",
                "registry_input_id": "historical-model-experiment-registry-input-1",
                "created_at": "2026-06-18T18:00:00+09:00",
                "operator_context": "TEST",
                "source_path": "fixtures/historical/historical_model_experiment_fixture.json",
                "source_manifest_ids": ["MANIFEST-1", "CALENDAR-MANIFEST-1"],
                "source_audit_record_ids": ["AUDIT-1"],
                "provider_provenance_ids": ["PROVENANCE-1"],
            }
        ],
    }


def test_historical_model_experiment_models_accept_local_offline_fixture_only_inputs(tmp_path):
    fixture_file = tmp_path / "historical_model_experiment_fixture.json"
    fixture_file.write_text(json.dumps(historical_model_experiment_fixture_payload()), encoding="utf-8")

    registry_input = load_historical_model_experiment_fixture(fixture_file)

    assert isinstance(registry_input, HistoricalModelExperimentRegistryInput)
    assert isinstance(registry_input.registry_config, HistoricalModelExperimentRegistryConfig)
    assert registry_input.registry_config.no_live_inference is True
    assert registry_input.registry_config.no_deployment is True


def test_historical_model_experiment_models_require_safety_flags():
    payload = historical_model_experiment_fixture_payload()
    payload["registry_config"]["no_deployment"] = False

    with pytest.raises(ValueError, match="no_deployment"):
        HistoricalModelExperimentRegistryInput.model_validate(payload)


def test_historical_model_experiment_record_construction():
    registry_input = HistoricalModelExperimentRegistryInput.model_validate(historical_model_experiment_fixture_payload())

    record = registry_input.experiment_records[0]
    assert isinstance(record, HistoricalModelExperimentRecord)
    assert record.no_runtime_trading_signal is True
    assert record.no_order_candidate is True


def test_historical_model_experiment_registry_report_construction():
    registry_input = HistoricalModelExperimentRegistryInput.model_validate(historical_model_experiment_fixture_payload())

    report = registry_input.registry_report
    assert isinstance(report, HistoricalModelExperimentRegistryReport)
    assert report.experiment_count == 1


def test_historical_model_comparison_report_construction():
    registry_input = HistoricalModelExperimentRegistryInput.model_validate(historical_model_experiment_fixture_payload())

    report = registry_input.comparison_report
    assert isinstance(report, HistoricalModelComparisonReport)
    assert report.safety_blocked is True


def test_historical_model_risk_review_report_construction():
    registry_input = HistoricalModelExperimentRegistryInput.model_validate(historical_model_experiment_fixture_payload())

    report = registry_input.risk_review_report
    assert isinstance(report, HistoricalModelRiskReviewReport)
    assert report.optional_sklearn_dependency_risk is False


def test_historical_model_promotion_block_report_is_blocked_by_default():
    registry_input = HistoricalModelExperimentRegistryInput.model_validate(historical_model_experiment_fixture_payload())

    report = registry_input.promotion_block_report
    assert isinstance(report, HistoricalModelPromotionBlockReport)
    assert report.production_use_allowed is False
    assert report.live_inference_allowed is False
    assert report.runtime_trading_signal_allowed is False
    assert report.order_candidate_allowed is False
    assert report.paper_trading_allowed is False
    assert report.broker_path_allowed is False
    assert report.live_prod_allowed is False
    assert report.deployment_allowed is False


def test_historical_model_lineage_report_construction():
    registry_input = HistoricalModelExperimentRegistryInput.model_validate(historical_model_experiment_fixture_payload())

    report = registry_input.lineage_report
    assert isinstance(report, HistoricalModelExperimentLineageReport)
    assert report.validation_split_lineage_present is True


def test_historical_model_safety_report_construction():
    registry_input = HistoricalModelExperimentRegistryInput.model_validate(historical_model_experiment_fixture_payload())

    report = registry_input.safety_report
    assert isinstance(report, HistoricalModelExperimentSafetyReport)
    assert report.no_live_inference is True
    assert report.no_deployment is True


def test_historical_model_experiment_fixture_loader_wraps_source_path_in_error(tmp_path):
    fixture_file = tmp_path / "historical_model_experiment_fixture.txt"
    fixture_file.write_text("{}", encoding="utf-8")

    with pytest.raises(ValueError, match=str(fixture_file)):
        load_historical_model_experiment_fixture(fixture_file)


def test_historical_model_experiment_fixture_rejects_parquet():
    payload = historical_model_experiment_fixture_payload()
    payload["artifact_manifest"]["local_artifact_path"] = "artifacts/historical_model_1.parquet"

    with pytest.raises(ValueError, match="parquet"):
        HistoricalModelExperimentRegistryInput.model_validate(payload)


@pytest.mark.parametrize("field_name", ["deployment_path", "runtime_signal_field", "order_candidate_field", "live_mode"])
def test_historical_model_experiment_record_rejects_deployment_runtime_order_live_markers(field_name):
    payload = historical_model_experiment_fixture_payload()
    payload["experiment_records"][0]["model_metadata"][field_name] = "unsafe"

    with pytest.raises(ValueError, match="unsafe metadata"):
        HistoricalModelExperimentRegistryInput.model_validate(payload)


def test_historical_model_experiment_gap_categories_exist():
    expected = {
        "EXPERIMENT_REGISTRY_REPORT_GENERATED",
        "EXPERIMENT_REPORT_ONLY",
        "EXPERIMENT_LOCAL_ONLY",
        "EXPERIMENT_OFFLINE_ONLY",
        "EXPERIMENT_MISSING_INPUT",
        "EXPERIMENT_MISSING_TRAINING_RUN_REPORT",
        "EXPERIMENT_MISSING_EVALUATION_REPORT",
        "EXPERIMENT_MISSING_METRICS_REPORT",
        "EXPERIMENT_MISSING_ARTIFACT_MANIFEST",
        "EXPERIMENT_MISSING_SAFETY_REPORT",
        "EXPERIMENT_MISSING_DATASET_LINEAGE",
        "EXPERIMENT_MISSING_SPLIT_LINEAGE",
        "EXPERIMENT_MISSING_LEAKAGE_AUDIT_LINEAGE",
        "EXPERIMENT_UNSUPPORTED_MODEL_TYPE",
        "EXPERIMENT_OVERFIT_RISK_DETECTED",
        "EXPERIMENT_LOW_LABEL_SUPPORT",
        "EXPERIMENT_SEVERE_LABEL_IMBALANCE",
        "EXPERIMENT_TRAIN_TEST_METRIC_GAP",
        "EXPERIMENT_WEAK_BASELINE_IMPROVEMENT",
        "EXPERIMENT_OPTIONAL_SKLEARN_DEPENDENCY_RISK",
        "EXPERIMENT_UNSAFE_ARTIFACT_METADATA",
        "EXPERIMENT_MISSING_SAFETY_FLAGS",
        "EXPERIMENT_PROMOTION_BLOCK_GENERATED",
        "EXPERIMENT_PRODUCTION_USE_BLOCKED",
        "EXPERIMENT_LIVE_INFERENCE_BLOCKED",
        "EXPERIMENT_RUNTIME_SIGNAL_BLOCKED",
        "EXPERIMENT_ORDER_CANDIDATE_BLOCKED",
        "EXPERIMENT_PAPER_TRADING_BLOCKED",
        "EXPERIMENT_DEPLOYMENT_BLOCKED",
        "EXPERIMENT_PRODUCTION_DEPLOYMENT_NOT_ALLOWED",
        "EXPERIMENT_LIVE_INFERENCE_NOT_ALLOWED",
        "EXPERIMENT_RUNTIME_SIGNAL_DETECTED",
        "EXPERIMENT_ORDER_CANDIDATE_DETECTED",
        "EXPERIMENT_ORDER_FIELD_DETECTED",
        "EXPERIMENT_BUY_SELL_WORDING_DETECTED",
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
    assert expected == {item.value for item in HistoricalModelExperimentGapCategory}


@pytest.mark.parametrize(
    ("payload", "label"),
    [
        ({"deployment_target": "offline"}, "deployment"),
        ({"live_inference_mode": "disabled"}, "live_inference"),
        ({"runtime_signal": "GO"}, "runtime_signal"),
        ({"order_candidate": "X"}, "order_candidate"),
        ({"comment": "buy entry now"}, "buy_sell"),
        ({"broker_metadata": "none"}, "broker"),
        ({"account_metadata": "none"}, "account"),
        ({"order_metadata": "none"}, "order"),
        ({"credential_ref": "x"}, "credential"),
        ({"source_path": "https://example.com/file.json"}, "remote"),
        ({"api_source": "rest"}, "api"),
        ({"network_path": "tcp://host"}, "network"),
        ({"provider_hint": "vendor"}, "provider"),
        ({"cloud_llm": "gemini"}, "cloud_llm"),
        ({"local_llm_runtime": "ollama"}, "local_llm"),
        ({"crawler_trigger": "crawl"}, "crawler"),
        ({"mode": "live"}, "live_prod"),
        ({"artifact": "file.parquet"}, "parquet"),
    ],
)
def test_historical_model_experiment_guard_rejects_unsafe_metadata(payload, label):
    with pytest.raises(ValueError, match=label):
        validate_historical_model_experiment_metadata_safety(payload, context="historical model experiment")


def test_historical_model_experiment_artifact_safety_rejects_unsafe_artifact_manifest():
    with pytest.raises(ValueError, match="deployment"):
        validate_historical_model_experiment_artifact_safety(
            {"deployment_path": "registry/production"}, context="historical model experiment"
        )


def test_historical_model_experiment_guard_rejects_production_readiness_claim():
    with pytest.raises(ValueError, match="deployment"):
        validate_historical_model_experiment_metadata_safety(
            {"production_readiness": "deployment approved"}, context="historical model experiment"
        )


def test_historical_model_experiment_guard_rejects_deployment_path():
    with pytest.raises(ValueError, match="deployment"):
        validate_historical_model_experiment_metadata_safety(
            {"model_metadata": {"deployment_path": "/prod/model"}}, context="historical model experiment"
        )


def test_historical_model_experiment_promotion_block_remains_blocked_by_default():
    payload = historical_model_experiment_fixture_payload()["promotion_block_report"]
    validate_historical_model_experiment_promotion_block(payload, context="historical model experiment")

    payload["paper_trading_allowed"] = True
    with pytest.raises(ValueError, match="blocked-by-default"):
        validate_historical_model_experiment_promotion_block(payload, context="historical model experiment")


def test_historical_model_experiment_comparison_guard_rejects_live_use_ranking():
    with pytest.raises(ValueError, match="live_ranking"):
        validate_historical_model_experiment_comparison_safety(
            {"ranking_mode": "live_rank_for_prod_use"}, context="historical model experiment"
        )
