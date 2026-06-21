import json

import pytest

from stock_risk_mcp.historical_model_training_fixture import load_historical_model_training_fixture
from stock_risk_mcp.historical_model_training_guard import (
    validate_historical_model_training_artifact_safety,
    validate_historical_model_training_feature_boundary,
    validate_historical_model_training_label_schema_safety,
    validate_historical_model_training_metadata_safety,
    validate_historical_model_training_model_type_safety,
    validate_historical_model_training_split_safety,
)
from stock_risk_mcp.historical_model_training_models import (
    HistoricalModelArtifactManifest,
    HistoricalModelTrainingConfig,
    HistoricalModelTrainingFeatureSchema,
    HistoricalModelTrainingGapCategory,
    HistoricalModelTrainingInput,
    HistoricalModelTrainingLabelSchema,
    HistoricalModelTrainingModelType,
    HistoricalModelTrainingRunConfig,
)
from tests.test_historical_dataset_readiness_models import historical_dataset_readiness_fixture_payload


def historical_model_training_fixture_payload():
    readiness_payload = historical_dataset_readiness_fixture_payload()
    return {
        "schema_version": "5.7-historical-model-training-input",
        "training_input_id": "historical-model-training-input-1",
        "training_config": {
            "config_id": "historical-model-training-config-1",
            "strategy_track": "DOMESTIC_KR",
            "sandbox_mode": "RESEARCH_ONLY",
        },
        "dataset_ref": {
            "dataset_ref_id": "historical-model-dataset-ref-1",
            "dataset_manifest_id": "DATASET-EXPORT-MANIFEST-1",
            "source_manifest_ids": ["MANIFEST-1", "CALENDAR-MANIFEST-1"],
            "source_audit_record_ids": ["AUDIT-1"],
            "provider_provenance_ids": ["PROVENANCE-1"],
        },
        "split_ref": {
            "split_ref_id": "historical-model-split-ref-1",
            "split_manifest_id": "DATASET-SPLIT-MANIFEST-1",
            "split_policy": "CHRONOLOGICAL",
            "chronological": True,
            "random_shuffle_used": False,
            "source_manifest_ids": ["MANIFEST-1", "CALENDAR-MANIFEST-1"],
            "source_audit_record_ids": ["AUDIT-1"],
            "provider_provenance_ids": ["PROVENANCE-1"],
        },
        "feature_schema": {
            "feature_schema_id": "historical-model-feature-schema-1",
            "feature_schema_version": "5.4-HISTORICAL-DATASET-FEATURE-BLOCK",
            "feature_fields": [
                "REPLAY_CONTEXT_ID",
                "SCANNER_REPLAY_INPUT_ID",
                "KNOWN_EVENT_CONTEXT_SUMMARY",
                "ATTACHED_MARKET_EVENT_COUNT",
                "ATTACHED_CORPORATE_EVENT_COUNT",
            ],
        },
        "label_schema": {
            "label_schema_id": "historical-model-label-schema-1",
            "label_schema_version": "5.4-HISTORICAL-DATASET-OUTCOME-BLOCK",
            "label_source": "OUTCOME_BLOCK_ONLY",
            "label_field": "OUTCOME_LABEL",
        },
        "run_config": {
            "run_config_id": "historical-model-run-config-1",
            "requested_model_type": "DUMMY_MAJORITY",
            "random_shuffle_enabled": False,
        },
        "dataset_records": readiness_payload["dataset_records"],
        "dataset_export_manifest": {
            "manifest_id": "DATASET-EXPORT-MANIFEST-1",
            "export_format": "JSON",
            "local_output_path": "fixtures/historical/historical_dataset_export.json",
            "record_count": 1,
            "symbol_count": 1,
            "market_count": 1,
            "date_range_start": "2026-06-18",
            "date_range_end": "2026-06-18",
            "feature_schema_version": "5.4-HISTORICAL-DATASET-FEATURE-BLOCK",
            "outcome_schema_version": "5.4-HISTORICAL-DATASET-OUTCOME-BLOCK",
            "quality_report_id": "DATASET-QUALITY-REPORT-1",
            "gap_report_id": "DATASET-GAP-REPORT-1",
            "safety_report_id": "DATASET-SAFETY-REPORT-1",
            "export_formats": ["JSON", "JSONL", "CSV"],
            "source_manifest_ids": ["MANIFEST-1", "CALENDAR-MANIFEST-1"],
            "source_audit_record_ids": ["AUDIT-1"],
            "provider_provenance_ids": ["PROVENANCE-1"],
        },
        "validation_report": readiness_payload["validation_report"],
        "leakage_audit_report": readiness_payload["leakage_audit_report"],
        "split_manifest": readiness_payload["split_manifest"],
        "coverage_report": readiness_payload["coverage_report"],
        "label_distribution_report": readiness_payload["label_distribution_report"],
        "readiness_report": readiness_payload["readiness_report"],
        "split_quality_report": readiness_payload["split_quality_report"],
        "imbalance_report": readiness_payload["imbalance_report"],
        "baseline_evaluation_report": readiness_payload["baseline_evaluation_report"],
        "plan_check_report": {
            "plan_check_report_id": "historical-model-plan-check-report-1",
            "training_input_id": "historical-model-training-input-1",
            "eligible_for_sandbox_training": False,
            "warning_count": 0,
            "warnings": [],
            "blocking_issue_count": 0,
            "source_manifest_ids": ["MANIFEST-1", "CALENDAR-MANIFEST-1"],
            "source_audit_record_ids": ["AUDIT-1"],
            "provider_provenance_ids": ["PROVENANCE-1"],
        },
        "run_report": {
            "run_report_id": "historical-model-run-report-1",
            "training_input_id": "historical-model-training-input-1",
            "model_type": "DUMMY_MAJORITY",
            "sandbox_mode": "RESEARCH_ONLY",
            "report_only_prediction_count": 0,
            "training_executed": False,
            "source_manifest_ids": ["MANIFEST-1", "CALENDAR-MANIFEST-1"],
            "source_audit_record_ids": ["AUDIT-1"],
            "provider_provenance_ids": ["PROVENANCE-1"],
        },
        "evaluation_report": {
            "evaluation_report_id": "historical-model-evaluation-report-1",
            "training_input_id": "historical-model-training-input-1",
            "model_type": "DUMMY_MAJORITY",
            "report_only_prediction_count": 0,
            "runtime_trading_signal_present": False,
            "order_candidate_present": False,
            "source_manifest_ids": ["MANIFEST-1", "CALENDAR-MANIFEST-1"],
            "source_audit_record_ids": ["AUDIT-1"],
            "provider_provenance_ids": ["PROVENANCE-1"],
        },
        "metrics_report": {
            "metrics_report_id": "historical-model-metrics-report-1",
            "training_input_id": "historical-model-training-input-1",
            "model_type": "DUMMY_MAJORITY",
            "train_accuracy": 0.0,
            "validation_accuracy": 0.0,
            "test_accuracy": 0.0,
            "source_manifest_ids": ["MANIFEST-1", "CALENDAR-MANIFEST-1"],
            "source_audit_record_ids": ["AUDIT-1"],
            "provider_provenance_ids": ["PROVENANCE-1"],
        },
        "artifact_manifest": {
            "artifact_manifest_id": "historical-model-artifact-manifest-1",
            "model_id": "historical-model-1",
            "model_type": "DUMMY_MAJORITY",
            "training_dataset_manifest_id": "DATASET-EXPORT-MANIFEST-1",
            "split_manifest_id": "DATASET-SPLIT-MANIFEST-1",
            "feature_schema_version": "5.4-HISTORICAL-DATASET-FEATURE-BLOCK",
            "label_schema_version": "5.4-HISTORICAL-DATASET-OUTCOME-BLOCK",
            "training_timestamp": "2026-06-18T17:00:00+09:00",
            "metrics_report_id": "historical-model-metrics-report-1",
            "local_artifact_path": "artifacts/historical_model_1.json",
        },
        "safety_report": {
            "safety_report_id": "historical-model-safety-report-1",
        },
        "gap_report": {
            "gap_report_id": "historical-model-gap-report-1",
            "training_input_id": "historical-model-training-input-1",
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
                "audit_record_id": "historical-model-audit-record-1",
                "training_input_id": "historical-model-training-input-1",
                "created_at": "2026-06-18T17:30:00+09:00",
                "operator_context": "TEST",
                "source_path": "fixtures/historical/historical_model_training_fixture.json",
                "source_manifest_ids": ["MANIFEST-1", "CALENDAR-MANIFEST-1"],
                "source_audit_record_ids": ["AUDIT-1"],
                "provider_provenance_ids": ["PROVENANCE-1"],
            }
        ],
    }


def test_historical_model_training_models_accept_local_offline_fixture_only_inputs(tmp_path):
    fixture_file = tmp_path / "historical_model_training_fixture.json"
    fixture_file.write_text(json.dumps(historical_model_training_fixture_payload()), encoding="utf-8")

    training_input = load_historical_model_training_fixture(fixture_file)

    assert isinstance(training_input, HistoricalModelTrainingInput)
    assert isinstance(training_input.training_config, HistoricalModelTrainingConfig)
    assert isinstance(training_input.feature_schema, HistoricalModelTrainingFeatureSchema)
    assert isinstance(training_input.label_schema, HistoricalModelTrainingLabelSchema)
    assert isinstance(training_input.run_config, HistoricalModelTrainingRunConfig)
    assert training_input.training_config.sandbox_mode == "RESEARCH_ONLY"


def test_historical_model_training_models_require_safety_flags():
    payload = historical_model_training_fixture_payload()
    payload["training_config"]["offline_only"] = False

    with pytest.raises(ValueError, match="offline_only"):
        HistoricalModelTrainingInput.model_validate(payload)


def test_historical_model_training_split_ref_requires_chronological_policy():
    payload = historical_model_training_fixture_payload()
    payload["split_ref"]["split_policy"] = "RANDOM"

    with pytest.raises(ValueError, match="chronological"):
        HistoricalModelTrainingInput.model_validate(payload)


def test_historical_model_training_run_config_disables_random_shuffle_by_default():
    training_input = HistoricalModelTrainingInput.model_validate(historical_model_training_fixture_payload())

    assert training_input.run_config.random_shuffle_enabled is False


def test_historical_model_training_allowed_model_type_enum():
    assert HistoricalModelTrainingModelType.DUMMY_MAJORITY.value == "DUMMY_MAJORITY"
    assert HistoricalModelTrainingModelType.DUMMY_PRIOR.value == "DUMMY_PRIOR"
    assert HistoricalModelTrainingModelType.LOGISTIC_REGRESSION_OPTIONAL_SKLEARN.value == "LOGISTIC_REGRESSION_OPTIONAL_SKLEARN"
    assert HistoricalModelTrainingModelType.DECISION_TREE_OPTIONAL_SKLEARN.value == "DECISION_TREE_OPTIONAL_SKLEARN"
    assert HistoricalModelTrainingModelType.RANDOM_FOREST_OPTIONAL_SKLEARN.value == "RANDOM_FOREST_OPTIONAL_SKLEARN"


def test_historical_model_training_artifact_manifest_is_local_report_only_and_non_executable():
    training_input = HistoricalModelTrainingInput.model_validate(historical_model_training_fixture_payload())

    artifact = training_input.artifact_manifest
    assert isinstance(artifact, HistoricalModelArtifactManifest)
    assert artifact.local_file_only is True
    assert artifact.report_only is True
    assert artifact.non_executable is True


@pytest.mark.parametrize("field_name", ["credential_ref", "broker_metadata", "account_id", "order_id", "live_mode"])
def test_historical_model_training_artifact_manifest_rejects_unsafe_metadata(field_name):
    payload = historical_model_training_fixture_payload()
    payload["artifact_manifest"][field_name] = "forbidden"

    with pytest.raises(ValueError, match="not allowed|forbidden|unsafe"):
        HistoricalModelTrainingInput.model_validate(payload)


@pytest.mark.parametrize(
    "field_name",
    [
        "OUTCOME_LABEL",
        "FORWARD_RETURN_PCT",
        "MAX_FAVORABLE_EXCURSION_PCT",
        "MAX_ADVERSE_EXCURSION_PCT",
        "ACTUAL_FORWARD_VALUE",
    ],
)
def test_historical_model_training_feature_schema_rejects_obvious_outcome_leakage_fields(field_name):
    payload = historical_model_training_fixture_payload()
    payload["feature_schema"]["feature_fields"].append(field_name)

    with pytest.raises(ValueError, match="feature schema"):
        HistoricalModelTrainingInput.model_validate(payload)


def test_historical_model_training_label_schema_references_outcome_side_labels_only():
    training_input = HistoricalModelTrainingInput.model_validate(historical_model_training_fixture_payload())

    assert training_input.label_schema.label_source == "OUTCOME_BLOCK_ONLY"
    assert training_input.label_schema.label_field == "OUTCOME_LABEL"


def test_historical_model_training_fixture_loader_wraps_source_path_in_error(tmp_path):
    fixture_file = tmp_path / "historical_model_training_fixture.txt"
    fixture_file.write_text(json.dumps(historical_model_training_fixture_payload()), encoding="utf-8")

    with pytest.raises(ValueError, match=str(fixture_file)):
        load_historical_model_training_fixture(fixture_file)


def test_historical_model_training_fixture_rejects_parquet_metadata(tmp_path):
    payload = historical_model_training_fixture_payload()
    payload["artifact_manifest"]["local_artifact_path"] = "artifacts/historical_model_1.parquet"
    fixture_file = tmp_path / "historical_model_training_fixture.json"
    fixture_file.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(ValueError, match="parquet"):
        load_historical_model_training_fixture(fixture_file)


def test_historical_model_training_gap_taxonomy_exposes_required_v57_categories():
    required = {
        "TRAINING_PLAN_CHECK_GENERATED",
        "TRAINING_REPORT_ONLY",
        "TRAINING_LOCAL_ONLY",
        "TRAINING_OFFLINE_ONLY",
        "TRAINING_MISSING_INPUT",
        "TRAINING_MISSING_DATASET_REF",
        "TRAINING_MISSING_SPLIT_REF",
        "TRAINING_MISSING_READINESS_REPORT",
        "TRAINING_MISSING_VALIDATION_REPORT",
        "TRAINING_MISSING_LEAKAGE_AUDIT",
        "TRAINING_READINESS_NOT_CLEAN",
        "TRAINING_VALIDATION_NOT_CLEAN",
        "TRAINING_LEAKAGE_AUDIT_NOT_CLEAN",
        "TRAINING_SPLIT_NOT_CHRONOLOGICAL",
        "TRAINING_RANDOM_SHUFFLE_DETECTED",
        "TRAINING_FEATURE_SCHEMA_MISSING",
        "TRAINING_LABEL_SCHEMA_MISSING",
        "TRAINING_FEATURE_LEAKAGE_DETECTED",
        "TRAINING_OUTCOME_LABEL_IN_FEATURES_DETECTED",
        "TRAINING_FORWARD_RETURN_IN_FEATURES_DETECTED",
        "TRAINING_POST_ANCHOR_ACTUAL_IN_FEATURES_DETECTED",
        "TRAINING_LABEL_NOT_OUTCOME_SIDE",
        "TRAINING_UNSUPPORTED_MODEL_TYPE",
        "TRAINING_SKLEARN_UNAVAILABLE",
        "TRAINING_MODEL_ARTIFACT_GENERATED",
        "TRAINING_ARTIFACT_REPORT_ONLY",
        "TRAINING_MODEL_WEIGHT_DETECTED_UNSAFE",
        "TRAINING_RUNTIME_SIGNAL_DETECTED",
        "TRAINING_ORDER_CANDIDATE_DETECTED",
        "TRAINING_ORDER_FIELD_DETECTED",
        "TRAINING_BUY_SELL_WORDING_DETECTED",
        "TRAINING_REMOTE_SOURCE_NOT_ALLOWED",
        "TRAINING_API_SOURCE_NOT_ALLOWED",
        "TRAINING_NETWORK_SOURCE_NOT_ALLOWED",
        "TRAINING_PROVIDER_SOURCE_NOT_ALLOWED",
        "TRAINING_CLOUD_LLM_NOT_ALLOWED",
        "TRAINING_LOCAL_LLM_RUNTIME_NOT_ALLOWED",
        "TRAINING_CRAWLER_TRIGGER_NOT_ALLOWED",
        "TRAINING_LIVE_PROD_NOT_ALLOWED",
        "TRAINING_BROKER_PATH_NOT_ALLOWED",
        "TRAINING_CREDENTIALS_NOT_ALLOWED",
        "TRAINING_PARQUET_NOT_ALLOWED",
    }
    assert {item.value for item in HistoricalModelTrainingGapCategory} >= required


@pytest.mark.parametrize(
    ("payload", "label"),
    [
        ({"source_path": "https://remote.example/fixture.json"}, "remote"),
        ({"provider_api": "api"}, "api"),
        ({"network_path": "tcp://sandbox"}, "network"),
        ({"provider_name": "provider-x"}, "provider"),
        ({"cloud_llm_backend": "gpt"}, "cloud_llm"),
        ({"local_llm_runtime": "ollama"}, "local_llm"),
        ({"crawler_trigger": "crawl"}, "crawler"),
        ({"mode": "LIVE"}, "live_prod"),
        ({"broker_path": "broker-adapter"}, "broker"),
        ({"account_id": "acct-1"}, "account"),
        ({"order_id": "order-1"}, "order"),
        ({"credential_token": "secret"}, "credential"),
        ({"summary": "buy now"}, "buy_sell"),
        ({"runtime_signal": "go"}, "runtime_signal"),
        ({"order_candidate": "candidate"}, "order_candidate"),
    ],
)
def test_historical_model_training_metadata_safety_rejects_unsafe_markers(payload, label):
    with pytest.raises(ValueError, match=label):
        validate_historical_model_training_metadata_safety(payload, context="historical model training")


def test_historical_model_training_split_safety_rejects_random_shuffle():
    with pytest.raises(ValueError, match="random shuffle"):
        validate_historical_model_training_split_safety({"random_shuffle_used": True}, context="historical model training")


def test_historical_model_training_split_safety_rejects_non_chronological_split():
    with pytest.raises(ValueError, match="chronological"):
        validate_historical_model_training_split_safety(
            {"split_policy": "RANDOM", "chronological": False},
            context="historical model training",
        )


@pytest.mark.parametrize(
    ("feature_fields", "label"),
    [
        (["OUTCOME_LABEL"], "outcome label"),
        (["FORWARD_RETURN_PCT"], "forward return"),
        (["ACTUAL_FORWARD_VALUE"], "post-anchor"),
    ],
)
def test_historical_model_training_feature_boundary_rejects_leakage_fields(feature_fields, label):
    with pytest.raises(ValueError, match=label):
        validate_historical_model_training_feature_boundary(
            {"feature_fields": feature_fields},
            context="historical model training",
        )


def test_historical_model_training_label_schema_safety_rejects_non_outcome_side_labels():
    with pytest.raises(ValueError, match="outcome-side"):
        validate_historical_model_training_label_schema_safety(
            {"label_source": "FEATURE_BLOCK", "label_field": "OUTCOME_LABEL"},
            context="historical model training",
        )


def test_historical_model_training_model_type_safety_rejects_unsupported_model_type():
    with pytest.raises(ValueError, match="unsupported"):
        validate_historical_model_training_model_type_safety(
            {"requested_model_type": "XGBOOST"},
            context="historical model training",
        )


def test_historical_model_training_model_type_safety_accepts_optional_sklearn_without_import():
    validate_historical_model_training_model_type_safety(
        {"requested_model_type": "LOGISTIC_REGRESSION_OPTIONAL_SKLEARN"},
        context="historical model training",
    )


def test_historical_model_training_artifact_safety_rejects_unsafe_artifact_manifest():
    with pytest.raises(ValueError, match="runtime deployment|broker|provider|order|live"):
        validate_historical_model_training_artifact_safety(
            {
                "local_artifact_path": "artifacts/model.json",
                "runtime_deployment": True,
                "broker_metadata": "broker",
            },
            context="historical model training",
        )
