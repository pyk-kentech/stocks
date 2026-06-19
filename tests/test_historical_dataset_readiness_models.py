import json

import pytest

from stock_risk_mcp.historical_dataset_readiness_fixture import load_historical_dataset_readiness_fixture
from stock_risk_mcp.historical_dataset_readiness_guard import (
    validate_historical_dataset_readiness_baseline_claims,
    validate_historical_dataset_readiness_metadata_safety,
    validate_historical_dataset_readiness_split_integrity,
)
from stock_risk_mcp.historical_dataset_readiness_models import (
    HistoricalDatasetBaselineConfig,
    HistoricalDatasetBaselineEvaluationReport,
    HistoricalDatasetImbalanceReport,
    HistoricalDatasetReadinessConfig,
    HistoricalDatasetReadinessGapCategory,
    HistoricalDatasetReadinessInput,
    HistoricalDatasetReadinessReport,
    HistoricalDatasetReadinessSafetyReport,
    HistoricalDatasetSplitQualityReport,
)
from tests.test_historical_dataset_validation_models import historical_dataset_validation_fixture_payload


def historical_dataset_readiness_fixture_payload():
    validation_payload = historical_dataset_validation_fixture_payload()
    return {
        "schema_version": "5.6-historical-dataset-readiness-input",
        "readiness_input_id": "dataset-readiness-input-1",
        "readiness_config": {
            "config_id": "dataset-readiness-config-1",
            "strategy_track": "DOMESTIC_KR",
            "minimum_record_count": 1,
            "minimum_train_count": 1,
            "minimum_validation_count": 0,
            "minimum_test_count": 0,
            "minimum_label_coverage": 1,
        },
        "baseline_config": {
            "baseline_config_id": "dataset-baseline-config-1",
            "strategy_track": "DOMESTIC_KR",
            "enabled_baselines": [
                "MAJORITY_LABEL_BASELINE",
                "PER_SYMBOL_MAJORITY_LABEL_BASELINE",
                "PER_MARKET_MAJORITY_LABEL_BASELINE",
                "PER_TRACK_MAJORITY_LABEL_BASELINE",
                "PRIOR_DISTRIBUTION_BASELINE",
                "NO_SKILL_BASELINE",
            ],
            "deterministic_only": True,
            "non_learning_only": True,
        },
        "dataset_records": validation_payload["dataset_records"],
        "validation_report": validation_payload["validation_report"],
        "leakage_audit_report": validation_payload["leakage_audit_report"],
        "split_manifest": validation_payload["split_manifest"],
        "coverage_report": validation_payload["coverage_report"],
        "label_distribution_report": validation_payload["label_distribution_report"],
        "validation_gap_report": validation_payload["validation_gap_report"],
        "validation_safety_report": validation_payload["validation_safety_report"],
        "readiness_report": {
            "readiness_report_id": "dataset-readiness-report-1",
            "readiness_input_id": "dataset-readiness-input-1",
            "record_count": 1,
            "blocking_gate_count": 0,
            "warning_count": 0,
            "warnings": [],
            "trade_approval": False,
            "training_approval": False,
            "source_manifest_ids": ["manifest-1", "calendar-manifest-1"],
            "source_audit_record_ids": ["audit-1"],
            "provider_provenance_ids": ["provenance-1"],
        },
        "split_quality_report": {
            "split_quality_report_id": "dataset-split-quality-report-1",
            "readiness_input_id": "dataset-readiness-input-1",
            "chronological_split": True,
            "random_shuffle_used": False,
            "partition_overlap_detected": False,
            "duplicated_record_id_detected": False,
            "train_record_count": 1,
            "validation_record_count": 0,
            "test_record_count": 0,
            "train_date_range_start": "2026-06-18",
            "train_date_range_end": "2026-06-18",
            "validation_date_range_start": None,
            "validation_date_range_end": None,
            "test_date_range_start": None,
            "test_date_range_end": None,
            "source_manifest_ids": ["manifest-1", "calendar-manifest-1"],
            "source_audit_record_ids": ["audit-1"],
            "provider_provenance_ids": ["provenance-1"],
        },
        "imbalance_report": {
            "imbalance_report_id": "dataset-imbalance-report-1",
            "readiness_input_id": "dataset-readiness-input-1",
            "label_counts": {"OUTCOME_REPORT_ONLY": 1},
            "label_percentages": {"OUTCOME_REPORT_ONLY": 1.0},
            "split_label_counts": {"TRAIN": {"OUTCOME_REPORT_ONLY": 1}},
            "severe_imbalance_warning": False,
            "warning_count": 0,
            "warnings": [],
            "source_manifest_ids": ["manifest-1", "calendar-manifest-1"],
            "source_audit_record_ids": ["audit-1"],
            "provider_provenance_ids": ["provenance-1"],
        },
        "baseline_evaluation_report": {
            "baseline_evaluation_report_id": "dataset-baseline-evaluation-report-1",
            "readiness_input_id": "dataset-readiness-input-1",
            "baseline_names": [
                "MAJORITY_LABEL_BASELINE",
                "PER_SYMBOL_MAJORITY_LABEL_BASELINE",
                "PER_MARKET_MAJORITY_LABEL_BASELINE",
                "PER_TRACK_MAJORITY_LABEL_BASELINE",
                "PRIOR_DISTRIBUTION_BASELINE",
                "NO_SKILL_BASELINE",
            ],
            "deterministic_only": True,
            "non_learning_only": True,
            "accuracy": 1.0,
            "label_coverage": 1.0,
            "confusion_matrix_counts": {"OUTCOME_REPORT_ONLY->OUTCOME_REPORT_ONLY": 1},
            "split_metric_summary": {"TRAIN": {"accuracy": 1.0}},
            "trained_model_artifact_present": False,
            "model_weights_present": False,
            "runtime_trading_signal_present": False,
            "source_manifest_ids": ["manifest-1", "calendar-manifest-1"],
            "source_audit_record_ids": ["audit-1"],
            "provider_provenance_ids": ["provenance-1"],
        },
        "readiness_gap_report": {
            "gap_report_id": "dataset-readiness-gap-report-1",
            "readiness_input_id": "dataset-readiness-input-1",
            "gap_status": "NO_GAPS",
            "gap_categories": [],
            "blocking_gap_count": 0,
            "report_only_gap_count": 0,
            "gaps": [],
            "source_manifest_ids": ["manifest-1", "calendar-manifest-1"],
            "source_audit_record_ids": ["audit-1"],
            "provider_provenance_ids": ["provenance-1"],
        },
        "readiness_safety_report": {
            "safety_report_id": "dataset-readiness-safety-report-1",
        },
        "audit_records": [
            {
                "audit_record_id": "dataset-readiness-audit-record-1",
                "readiness_input_id": "dataset-readiness-input-1",
                "created_at": "2026-06-18T16:00:00+09:00",
                "operator_context": "TEST",
                "source_path": "fixtures/historical/historical_dataset_readiness_fixture.json",
                "source_manifest_ids": ["manifest-1", "calendar-manifest-1"],
                "source_audit_record_ids": ["audit-1"],
                "provider_provenance_ids": ["provenance-1"],
            }
        ],
    }


def test_historical_dataset_readiness_models_accept_local_fixture_only_inputs(tmp_path):
    fixture_file = tmp_path / "historical_dataset_readiness_fixture.json"
    fixture_file.write_text(json.dumps(historical_dataset_readiness_fixture_payload()), encoding="utf-8")

    readiness_input = load_historical_dataset_readiness_fixture(fixture_file)

    assert isinstance(readiness_input, HistoricalDatasetReadinessInput)
    assert isinstance(readiness_input.readiness_config, HistoricalDatasetReadinessConfig)
    assert isinstance(readiness_input.readiness_report, HistoricalDatasetReadinessReport)
    assert isinstance(readiness_input.split_quality_report, HistoricalDatasetSplitQualityReport)
    assert isinstance(readiness_input.imbalance_report, HistoricalDatasetImbalanceReport)
    assert isinstance(readiness_input.baseline_config, HistoricalDatasetBaselineConfig)
    assert isinstance(readiness_input.baseline_evaluation_report, HistoricalDatasetBaselineEvaluationReport)
    assert isinstance(readiness_input.readiness_safety_report, HistoricalDatasetReadinessSafetyReport)


def test_historical_dataset_readiness_models_require_safety_flags():
    payload = historical_dataset_readiness_fixture_payload()
    payload["readiness_config"]["no_learned_model_evaluation"] = False

    with pytest.raises(ValueError, match="no_learned_model_evaluation"):
        HistoricalDatasetReadinessInput.model_validate(payload)


def test_historical_dataset_readiness_input_consumes_validation_artifacts_only():
    readiness_input = HistoricalDatasetReadinessInput.model_validate(historical_dataset_readiness_fixture_payload())

    assert readiness_input.validation_report.validation_report_id == "DATASET-VALIDATION-REPORT-1"
    assert readiness_input.split_manifest.split_manifest_id == "DATASET-SPLIT-MANIFEST-1"
    assert readiness_input.coverage_report.coverage_report_id == "DATASET-COVERAGE-REPORT-1"


def test_historical_dataset_split_quality_report_construction():
    readiness_input = HistoricalDatasetReadinessInput.model_validate(historical_dataset_readiness_fixture_payload())

    report = readiness_input.split_quality_report
    assert report.chronological_split is True
    assert report.random_shuffle_used is False
    assert report.partition_overlap_detected is False
    assert report.duplicated_record_id_detected is False


def test_historical_dataset_imbalance_report_construction():
    readiness_input = HistoricalDatasetReadinessInput.model_validate(historical_dataset_readiness_fixture_payload())

    report = readiness_input.imbalance_report
    assert report.label_counts["OUTCOME_REPORT_ONLY"] == 1
    assert report.label_percentages["OUTCOME_REPORT_ONLY"] == 1.0
    assert report.severe_imbalance_warning is False


def test_historical_dataset_baseline_config_construction():
    readiness_input = HistoricalDatasetReadinessInput.model_validate(historical_dataset_readiness_fixture_payload())

    baseline_config = readiness_input.baseline_config
    assert isinstance(baseline_config, HistoricalDatasetBaselineConfig)
    assert baseline_config.deterministic_only is True
    assert baseline_config.non_learning_only is True


def test_historical_dataset_baseline_evaluation_report_is_non_learning():
    readiness_input = HistoricalDatasetReadinessInput.model_validate(historical_dataset_readiness_fixture_payload())

    report = readiness_input.baseline_evaluation_report
    assert report.deterministic_only is True
    assert report.non_learning_only is True
    assert report.runtime_trading_signal_present is False


def test_historical_dataset_baseline_evaluation_report_has_no_model_weights_or_training_artifacts():
    readiness_input = HistoricalDatasetReadinessInput.model_validate(historical_dataset_readiness_fixture_payload())

    report = readiness_input.baseline_evaluation_report
    assert report.trained_model_artifact_present is False
    assert report.model_weights_present is False


def test_historical_dataset_readiness_fixture_loader_wraps_source_path_in_error(tmp_path):
    fixture_file = tmp_path / "historical_dataset_readiness_fixture.txt"
    fixture_file.write_text(json.dumps(historical_dataset_readiness_fixture_payload()), encoding="utf-8")

    with pytest.raises(ValueError, match=str(fixture_file)):
        load_historical_dataset_readiness_fixture(fixture_file)


def test_historical_dataset_readiness_fixture_rejects_parquet_metadata(tmp_path):
    payload = historical_dataset_readiness_fixture_payload()
    payload["validation_report"]["source_manifest_ids"] = ["PARQUET"]
    fixture_file = tmp_path / "historical_dataset_readiness_fixture.json"
    fixture_file.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(ValueError, match="parquet"):
        load_historical_dataset_readiness_fixture(fixture_file)


def test_historical_dataset_readiness_gap_taxonomy_exposes_required_v56_categories():
    assert HistoricalDatasetReadinessGapCategory.READINESS_REPORT_GENERATED.value == "READINESS_REPORT_GENERATED"
    assert HistoricalDatasetReadinessGapCategory.READINESS_REPORT_ONLY.value == "READINESS_REPORT_ONLY"
    assert HistoricalDatasetReadinessGapCategory.READINESS_MISSING_INPUT.value == "READINESS_MISSING_INPUT"
    assert HistoricalDatasetReadinessGapCategory.READINESS_MISSING_VALIDATION_REPORT.value == "READINESS_MISSING_VALIDATION_REPORT"
    assert HistoricalDatasetReadinessGapCategory.READINESS_MISSING_LEAKAGE_AUDIT.value == "READINESS_MISSING_LEAKAGE_AUDIT"
    assert HistoricalDatasetReadinessGapCategory.READINESS_MISSING_SPLIT_MANIFEST.value == "READINESS_MISSING_SPLIT_MANIFEST"
    assert HistoricalDatasetReadinessGapCategory.READINESS_MISSING_COVERAGE_REPORT.value == "READINESS_MISSING_COVERAGE_REPORT"
    assert HistoricalDatasetReadinessGapCategory.READINESS_MISSING_LABEL_DISTRIBUTION.value == "READINESS_MISSING_LABEL_DISTRIBUTION"
    assert HistoricalDatasetReadinessGapCategory.READINESS_VALIDATION_NOT_CLEAN.value == "READINESS_VALIDATION_NOT_CLEAN"
    assert HistoricalDatasetReadinessGapCategory.READINESS_LEAKAGE_AUDIT_NOT_CLEAN.value == "READINESS_LEAKAGE_AUDIT_NOT_CLEAN"
    assert HistoricalDatasetReadinessGapCategory.READINESS_SPLIT_NOT_CHRONOLOGICAL.value == "READINESS_SPLIT_NOT_CHRONOLOGICAL"
    assert HistoricalDatasetReadinessGapCategory.READINESS_SPLIT_RANDOM_SHUFFLE_DETECTED.value == "READINESS_SPLIT_RANDOM_SHUFFLE_DETECTED"
    assert HistoricalDatasetReadinessGapCategory.READINESS_SPLIT_PARTITION_OVERLAP.value == "READINESS_SPLIT_PARTITION_OVERLAP"
    assert HistoricalDatasetReadinessGapCategory.READINESS_SPLIT_DUPLICATED_RECORD_ID.value == "READINESS_SPLIT_DUPLICATED_RECORD_ID"
    assert HistoricalDatasetReadinessGapCategory.READINESS_TRAIN_COUNT_TOO_SMALL.value == "READINESS_TRAIN_COUNT_TOO_SMALL"
    assert HistoricalDatasetReadinessGapCategory.READINESS_VALIDATION_COUNT_TOO_SMALL.value == "READINESS_VALIDATION_COUNT_TOO_SMALL"
    assert HistoricalDatasetReadinessGapCategory.READINESS_TEST_COUNT_TOO_SMALL.value == "READINESS_TEST_COUNT_TOO_SMALL"
    assert HistoricalDatasetReadinessGapCategory.READINESS_LABEL_COVERAGE_TOO_LOW.value == "READINESS_LABEL_COVERAGE_TOO_LOW"
    assert HistoricalDatasetReadinessGapCategory.READINESS_LABEL_IMBALANCE_WARNING.value == "READINESS_LABEL_IMBALANCE_WARNING"
    assert HistoricalDatasetReadinessGapCategory.READINESS_MISSINGNESS_WARNING.value == "READINESS_MISSINGNESS_WARNING"
    assert HistoricalDatasetReadinessGapCategory.READINESS_LINEAGE_INCOMPLETE.value == "READINESS_LINEAGE_INCOMPLETE"
    assert HistoricalDatasetReadinessGapCategory.READINESS_BASELINE_REPORT_GENERATED.value == "READINESS_BASELINE_REPORT_GENERATED"
    assert HistoricalDatasetReadinessGapCategory.READINESS_BASELINE_NON_LEARNING.value == "READINESS_BASELINE_NON_LEARNING"
    assert HistoricalDatasetReadinessGapCategory.READINESS_LEARNED_MODEL_DETECTED.value == "READINESS_LEARNED_MODEL_DETECTED"
    assert HistoricalDatasetReadinessGapCategory.READINESS_MODEL_WEIGHT_DETECTED.value == "READINESS_MODEL_WEIGHT_DETECTED"
    assert HistoricalDatasetReadinessGapCategory.READINESS_ML_TRAINING_TRIGGER_NOT_ALLOWED.value == "READINESS_ML_TRAINING_TRIGGER_NOT_ALLOWED"
    assert HistoricalDatasetReadinessGapCategory.READINESS_ML_READY_TENSOR_EXPORT_NOT_ALLOWED.value == "READINESS_ML_READY_TENSOR_EXPORT_NOT_ALLOWED"
    assert HistoricalDatasetReadinessGapCategory.READINESS_ORDER_FIELD_DETECTED.value == "READINESS_ORDER_FIELD_DETECTED"
    assert HistoricalDatasetReadinessGapCategory.READINESS_BUY_SELL_WORDING_DETECTED.value == "READINESS_BUY_SELL_WORDING_DETECTED"
    assert HistoricalDatasetReadinessGapCategory.READINESS_REMOTE_SOURCE_NOT_ALLOWED.value == "READINESS_REMOTE_SOURCE_NOT_ALLOWED"
    assert HistoricalDatasetReadinessGapCategory.READINESS_API_SOURCE_NOT_ALLOWED.value == "READINESS_API_SOURCE_NOT_ALLOWED"
    assert HistoricalDatasetReadinessGapCategory.READINESS_NETWORK_SOURCE_NOT_ALLOWED.value == "READINESS_NETWORK_SOURCE_NOT_ALLOWED"
    assert HistoricalDatasetReadinessGapCategory.READINESS_PROVIDER_SOURCE_NOT_ALLOWED.value == "READINESS_PROVIDER_SOURCE_NOT_ALLOWED"
    assert HistoricalDatasetReadinessGapCategory.READINESS_LLM_METADATA_NOT_ALLOWED.value == "READINESS_LLM_METADATA_NOT_ALLOWED"
    assert HistoricalDatasetReadinessGapCategory.READINESS_CRAWLER_TRIGGER_NOT_ALLOWED.value == "READINESS_CRAWLER_TRIGGER_NOT_ALLOWED"
    assert HistoricalDatasetReadinessGapCategory.READINESS_LIVE_PROD_NOT_ALLOWED.value == "READINESS_LIVE_PROD_NOT_ALLOWED"
    assert HistoricalDatasetReadinessGapCategory.READINESS_PARQUET_NOT_ALLOWED.value == "READINESS_PARQUET_NOT_ALLOWED"


@pytest.mark.parametrize(
    ("payload", "message"),
    [
        ({"learned_model_name": "xgboost"}, "learned"),
        ({"model_weights_path": "weights.bin"}, "weight"),
        ({"ml_training_job": "fit"}, "training"),
        ({"tensor_export_path": "tensor.npy"}, "tensor"),
        ({"runtime_trading_signal": "BUY"}, "trading signal"),
        ({"order_intent": "BUY"}, "order"),
        ({"execution_path": "execute"}, "execution"),
        ({"label_summary": "buy now"}, "buy_sell"),
        ({"mode": "live prod"}, "live_prod"),
        ({"broker_path": "broker"}, "broker"),
        ({"account_ref": "account"}, "account"),
        ({"kiwoom_source": "kiwoom"}, "kiwoom"),
        ({"ls_source": "ls"}, "ls"),
        ({"remote_url": "https://example.com/file.json"}, "remote"),
        ({"provider_api": "provider"}, "provider"),
        ({"network_socket": "tcp://feed"}, "network"),
        ({"gemini_prompt": "analyze"}, "gemini"),
        ({"llm_summary": "llm"}, "llm"),
        ({"cloud_model_runtime": "cloud model"}, "cloud_model"),
        ({"crawler_trigger": "run"}, "crawler"),
        ({"parquet_path": "fixture.parquet"}, "parquet"),
    ],
)
def test_historical_dataset_readiness_guard_rejects_unsafe_metadata(payload, message):
    with pytest.raises(ValueError, match=message):
        validate_historical_dataset_readiness_metadata_safety(payload, context="historical dataset readiness")


def test_historical_dataset_readiness_guard_rejects_random_shuffle_marker():
    with pytest.raises(ValueError, match="random shuffle"):
        validate_historical_dataset_readiness_split_integrity(
            {"random_shuffle_used": True},
            context="historical dataset readiness",
        )


def test_historical_dataset_readiness_guard_rejects_split_overlap_marker():
    with pytest.raises(ValueError, match="overlap"):
        validate_historical_dataset_readiness_split_integrity(
            {"partition_overlap_detected": True},
            context="historical dataset readiness",
        )


def test_historical_dataset_readiness_guard_rejects_duplicated_split_record_marker():
    with pytest.raises(ValueError, match="duplicated"):
        validate_historical_dataset_readiness_split_integrity(
            {"duplicated_record_id_detected": True},
            context="historical dataset readiness",
        )


@pytest.mark.parametrize(
    ("payload", "message"),
    [
        ({"deterministic_only": False}, "deterministic"),
        ({"non_learning_only": False}, "non-learning"),
        ({"trained_model_artifact_present": True}, "trained"),
        ({"model_weights_present": True}, "weight"),
        ({"training_claim": "fit"}, "training"),
        ({"learned_model_fit": "classifier.fit"}, "learning"),
    ],
)
def test_historical_dataset_readiness_guard_rejects_baseline_learning_training_claims(payload, message):
    with pytest.raises(ValueError, match=message):
        validate_historical_dataset_readiness_baseline_claims(payload, context="historical dataset readiness")
