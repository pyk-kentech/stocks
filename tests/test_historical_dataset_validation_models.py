import json

import pytest

from stock_risk_mcp.historical_dataset_validation_fixture import load_historical_dataset_validation_fixture
from stock_risk_mcp.historical_dataset_validation_guard import (
    validate_historical_dataset_validation_feature_outcome_boundary,
    validate_historical_dataset_validation_metadata_safety,
    validate_historical_dataset_validation_split_integrity,
)
from stock_risk_mcp.historical_dataset_validation_models import (
    HistoricalDatasetCoverageReport,
    HistoricalDatasetLabelDistributionReport,
    HistoricalDatasetLeakageAuditReport,
    HistoricalDatasetSplitConfig,
    HistoricalDatasetSplitManifest,
    HistoricalDatasetSplitRecordRef,
    HistoricalDatasetValidationConfig,
    HistoricalDatasetValidationGapCategory,
    HistoricalDatasetValidationInput,
    HistoricalDatasetValidationReport,
    HistoricalDatasetValidationSafetyReport,
)
from tests.test_historical_dataset_models import historical_dataset_fixture_payload


def historical_dataset_validation_fixture_payload():
    dataset_payload = historical_dataset_fixture_payload()
    return {
        "schema_version": "5.5-historical-dataset-validation-input",
        "validation_input_id": "dataset-validation-input-1",
        "validation_config": {
            "config_id": "dataset-validation-config-1",
            "strategy_track": "DOMESTIC_KR",
            "require_chronological_split": True,
            "allow_random_shuffle": False,
            "default_train_ratio": 0.7,
            "default_validation_ratio": 0.15,
            "default_test_ratio": 0.15,
        },
        "split_config": {
            "split_config_id": "dataset-split-config-1",
            "strategy_track": "DOMESTIC_KR",
            "split_policy": "CHRONOLOGICAL",
            "allow_random_shuffle": False,
            "train_ratio": 0.7,
            "validation_ratio": 0.15,
            "test_ratio": 0.15,
        },
        "dataset_records": dataset_payload["records"],
        "dataset_export_manifest": dataset_payload["export_manifest"],
        "dataset_quality_report": dataset_payload["quality_report"],
        "dataset_gap_report": dataset_payload["gap_report"],
        "dataset_safety_report": dataset_payload["safety_report"],
        "validation_report": {
            "validation_report_id": "dataset-validation-report-1",
            "validation_input_id": "dataset-validation-input-1",
            "record_count": 1,
            "valid_record_count": 1,
            "missing_lineage_count": 0,
            "missing_feature_count": 0,
            "missing_outcome_count": 0,
            "blocked_count": 0,
            "warning_count": 0,
            "warnings": [],
            "training_ready_approved": False,
            "source_manifest_ids": ["manifest-1", "calendar-manifest-1"],
            "source_audit_record_ids": ["audit-1"],
            "provider_provenance_ids": ["provenance-1"],
        },
        "leakage_audit_report": {
            "leakage_audit_report_id": "dataset-leakage-audit-report-1",
            "validation_input_id": "dataset-validation-input-1",
            "audited_record_count": 1,
            "clean_record_count": 1,
            "blocked_record_count": 0,
            "warning_count": 0,
            "warnings": [],
            "outcome_label_in_features_count": 0,
            "forward_return_in_features_count": 0,
            "max_excursion_in_features_count": 0,
            "post_anchor_actual_value_in_features_count": 0,
            "scanner_input_mutation_risk_count": 0,
            "feature_outcome_leakage_absent": True,
            "affected_record_ids": [],
            "source_manifest_ids": ["manifest-1", "calendar-manifest-1"],
            "source_audit_record_ids": ["audit-1"],
            "provider_provenance_ids": ["provenance-1"],
        },
        "split_manifest": {
            "split_manifest_id": "dataset-split-manifest-1",
            "validation_input_id": "dataset-validation-input-1",
            "split_config_id": "dataset-split-config-1",
            "split_policy": "CHRONOLOGICAL",
            "chronological": True,
            "random_shuffle_used": False,
            "train_record_count": 1,
            "validation_record_count": 0,
            "test_record_count": 0,
            "train_symbol_count": 1,
            "validation_symbol_count": 0,
            "test_symbol_count": 0,
            "train_date_range_start": "2026-06-18",
            "train_date_range_end": "2026-06-18",
            "validation_date_range_start": None,
            "validation_date_range_end": None,
            "test_date_range_start": None,
            "test_date_range_end": None,
            "train_label_distribution": {"OUTCOME_REPORT_ONLY": 1},
            "validation_label_distribution": {},
            "test_label_distribution": {},
            "train_record_refs": [
                {
                    "record_ref_id": "dataset-split-record-ref-1",
                    "dataset_record_id": "DATASET-RECORD-1",
                    "split_partition": "TRAIN",
                    "replay_anchor_date": "2026-06-18",
                    "symbol": "005930",
                    "market": "KRX",
                }
            ],
            "validation_record_refs": [],
            "test_record_refs": [],
            "record_refs": [
                {
                    "record_ref_id": "dataset-split-record-ref-1",
                    "dataset_record_id": "DATASET-RECORD-1",
                    "split_partition": "TRAIN",
                    "replay_anchor_date": "2026-06-18",
                    "symbol": "005930",
                    "market": "KRX",
                }
            ],
            "source_manifest_ids": ["manifest-1", "calendar-manifest-1"],
            "source_audit_record_ids": ["audit-1"],
            "provider_provenance_ids": ["provenance-1"],
        },
        "coverage_report": {
            "coverage_report_id": "dataset-coverage-report-1",
            "validation_input_id": "dataset-validation-input-1",
            "record_count": 1,
            "symbol_count": 1,
            "market_count": 1,
            "strategy_track_count": 1,
            "earliest_replay_anchor_date": "2026-06-18",
            "latest_replay_anchor_date": "2026-06-18",
            "symbols": ["005930"],
            "markets": ["KRX"],
            "strategy_tracks": ["DOMESTIC_KR"],
            "records_by_symbol": {"005930": 1},
            "records_by_market": {"KRX": 1},
            "records_by_strategy_track": {"DOMESTIC_KR": 1},
            "missing_feature_count": 0,
            "missing_outcome_count": 0,
            "missing_lineage_count": 0,
            "source_manifest_ids": ["manifest-1", "calendar-manifest-1"],
            "source_audit_record_ids": ["audit-1"],
            "provider_provenance_ids": ["provenance-1"],
        },
        "label_distribution_report": {
            "label_distribution_report_id": "dataset-label-distribution-report-1",
            "validation_input_id": "dataset-validation-input-1",
            "record_count": 1,
            "label_counts": {"OUTCOME_REPORT_ONLY": 1},
            "label_percentages": {"OUTCOME_REPORT_ONLY": 1.0},
            "split_label_counts": {"TRAIN": {"OUTCOME_REPORT_ONLY": 1}},
            "split_label_percentages": {"TRAIN": {"OUTCOME_REPORT_ONLY": 1.0}},
            "source_manifest_ids": ["manifest-1", "calendar-manifest-1"],
            "source_audit_record_ids": ["audit-1"],
            "provider_provenance_ids": ["provenance-1"],
        },
        "validation_gap_report": {
            "gap_report_id": "dataset-validation-gap-report-1",
            "validation_input_id": "dataset-validation-input-1",
            "gap_status": "NO_GAPS",
            "gap_categories": [],
            "blocking_gap_count": 0,
            "report_only_gap_count": 0,
            "gaps": [],
            "source_manifest_ids": ["manifest-1", "calendar-manifest-1"],
            "source_audit_record_ids": ["audit-1"],
            "provider_provenance_ids": ["provenance-1"],
        },
        "validation_safety_report": {
            "safety_report_id": "dataset-validation-safety-report-1",
        },
        "audit_records": [
            {
                "audit_record_id": "dataset-validation-audit-record-1",
                "validation_input_id": "dataset-validation-input-1",
                "created_at": "2026-06-18T16:00:00+09:00",
                "operator_context": "TEST",
                "source_path": "fixtures/historical/historical_dataset_validation_fixture.json",
                "source_manifest_ids": ["manifest-1", "calendar-manifest-1"],
                "source_audit_record_ids": ["audit-1"],
                "provider_provenance_ids": ["provenance-1"],
            }
        ],
    }


def test_historical_dataset_validation_models_accept_local_fixture_only_inputs(tmp_path):
    fixture_file = tmp_path / "historical_dataset_validation_fixture.json"
    fixture_file.write_text(json.dumps(historical_dataset_validation_fixture_payload()), encoding="utf-8")

    validation_input = load_historical_dataset_validation_fixture(fixture_file)

    assert isinstance(validation_input, HistoricalDatasetValidationInput)
    assert isinstance(validation_input.validation_config, HistoricalDatasetValidationConfig)
    assert isinstance(validation_input.validation_report, HistoricalDatasetValidationReport)
    assert isinstance(validation_input.leakage_audit_report, HistoricalDatasetLeakageAuditReport)
    assert isinstance(validation_input.split_manifest, HistoricalDatasetSplitManifest)
    assert isinstance(validation_input.coverage_report, HistoricalDatasetCoverageReport)
    assert isinstance(validation_input.label_distribution_report, HistoricalDatasetLabelDistributionReport)
    assert isinstance(validation_input.validation_safety_report, HistoricalDatasetValidationSafetyReport)


def test_historical_dataset_validation_models_require_safety_flags():
    payload = historical_dataset_validation_fixture_payload()
    payload["validation_config"]["no_ml_training"] = False

    with pytest.raises(ValueError, match="no_ml_training"):
        HistoricalDatasetValidationInput.model_validate(payload)


def test_historical_dataset_leakage_audit_report_construction():
    validation_input = HistoricalDatasetValidationInput.model_validate(historical_dataset_validation_fixture_payload())

    report = validation_input.leakage_audit_report
    assert report.feature_outcome_leakage_absent is True
    assert report.outcome_label_in_features_count == 0
    assert report.forward_return_in_features_count == 0
    assert report.max_excursion_in_features_count == 0
    assert report.post_anchor_actual_value_in_features_count == 0
    assert report.scanner_input_mutation_risk_count == 0


def test_historical_dataset_split_config_construction():
    validation_input = HistoricalDatasetValidationInput.model_validate(historical_dataset_validation_fixture_payload())

    split_config = validation_input.split_config
    assert isinstance(split_config, HistoricalDatasetSplitConfig)
    assert split_config.split_policy == "CHRONOLOGICAL"
    assert split_config.allow_random_shuffle is False


def test_historical_dataset_split_manifest_is_chronological_and_report_only():
    validation_input = HistoricalDatasetValidationInput.model_validate(historical_dataset_validation_fixture_payload())

    manifest = validation_input.split_manifest
    assert manifest.chronological is True
    assert manifest.random_shuffle_used is False
    assert manifest.report_only is True


def test_historical_dataset_split_record_refs_are_report_only():
    validation_input = HistoricalDatasetValidationInput.model_validate(historical_dataset_validation_fixture_payload())

    record_ref = validation_input.split_manifest.record_refs[0]
    assert isinstance(record_ref, HistoricalDatasetSplitRecordRef)
    assert record_ref.report_only is True
    assert not hasattr(record_ref, "feature_block")
    assert not hasattr(record_ref, "outcome_block")


def test_historical_dataset_validation_fixture_loader_wraps_source_path_in_error(tmp_path):
    fixture_file = tmp_path / "historical_dataset_validation_fixture.txt"
    fixture_file.write_text(json.dumps(historical_dataset_validation_fixture_payload()), encoding="utf-8")

    with pytest.raises(ValueError, match=str(fixture_file)):
        load_historical_dataset_validation_fixture(fixture_file)


def test_historical_dataset_validation_fixture_rejects_parquet_metadata(tmp_path):
    payload = historical_dataset_validation_fixture_payload()
    payload["dataset_export_manifest"]["export_formats"] = ["parquet"]
    fixture_file = tmp_path / "historical_dataset_validation_fixture.json"
    fixture_file.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(ValueError, match="parquet"):
        load_historical_dataset_validation_fixture(fixture_file)


def test_historical_dataset_validation_gap_taxonomy_exposes_required_v55_categories():
    assert HistoricalDatasetValidationGapCategory.VALIDATION_REPORT_GENERATED.value == "VALIDATION_REPORT_GENERATED"
    assert HistoricalDatasetValidationGapCategory.VALIDATION_REPORT_ONLY.value == "VALIDATION_REPORT_ONLY"
    assert HistoricalDatasetValidationGapCategory.VALIDATION_MISSING_INPUT.value == "VALIDATION_MISSING_INPUT"
    assert HistoricalDatasetValidationGapCategory.VALIDATION_MISSING_DATASET_RECORD.value == "VALIDATION_MISSING_DATASET_RECORD"
    assert HistoricalDatasetValidationGapCategory.VALIDATION_MISSING_FEATURE_BLOCK.value == "VALIDATION_MISSING_FEATURE_BLOCK"
    assert HistoricalDatasetValidationGapCategory.VALIDATION_MISSING_OUTCOME_BLOCK.value == "VALIDATION_MISSING_OUTCOME_BLOCK"
    assert HistoricalDatasetValidationGapCategory.VALIDATION_MISSING_LINEAGE.value == "VALIDATION_MISSING_LINEAGE"
    assert HistoricalDatasetValidationGapCategory.VALIDATION_MISSING_REPLAY_WINDOW_ID.value == "VALIDATION_MISSING_REPLAY_WINDOW_ID"
    assert HistoricalDatasetValidationGapCategory.VALIDATION_MISSING_SOURCE_MANIFEST_ID.value == "VALIDATION_MISSING_SOURCE_MANIFEST_ID"
    assert HistoricalDatasetValidationGapCategory.VALIDATION_FEATURE_OUTCOME_LEAKAGE_DETECTED.value == "VALIDATION_FEATURE_OUTCOME_LEAKAGE_DETECTED"
    assert HistoricalDatasetValidationGapCategory.VALIDATION_OUTCOME_LABEL_IN_FEATURES_DETECTED.value == "VALIDATION_OUTCOME_LABEL_IN_FEATURES_DETECTED"
    assert HistoricalDatasetValidationGapCategory.VALIDATION_FORWARD_RETURN_IN_FEATURES_DETECTED.value == "VALIDATION_FORWARD_RETURN_IN_FEATURES_DETECTED"
    assert HistoricalDatasetValidationGapCategory.VALIDATION_MFE_MAE_IN_FEATURES_DETECTED.value == "VALIDATION_MFE_MAE_IN_FEATURES_DETECTED"
    assert HistoricalDatasetValidationGapCategory.VALIDATION_POST_ANCHOR_ACTUAL_IN_FEATURES_DETECTED.value == "VALIDATION_POST_ANCHOR_ACTUAL_IN_FEATURES_DETECTED"
    assert HistoricalDatasetValidationGapCategory.VALIDATION_SCANNER_INPUT_MUTATION_DETECTED.value == "VALIDATION_SCANNER_INPUT_MUTATION_DETECTED"
    assert HistoricalDatasetValidationGapCategory.VALIDATION_SPLIT_NOT_CHRONOLOGICAL.value == "VALIDATION_SPLIT_NOT_CHRONOLOGICAL"
    assert HistoricalDatasetValidationGapCategory.VALIDATION_SPLIT_RECORD_DUPLICATED.value == "VALIDATION_SPLIT_RECORD_DUPLICATED"
    assert HistoricalDatasetValidationGapCategory.VALIDATION_SPLIT_PARTITION_OVERLAP.value == "VALIDATION_SPLIT_PARTITION_OVERLAP"
    assert HistoricalDatasetValidationGapCategory.VALIDATION_UNSUPPORTED_MARKET.value == "VALIDATION_UNSUPPORTED_MARKET"
    assert HistoricalDatasetValidationGapCategory.VALIDATION_UNSUPPORTED_TRACK.value == "VALIDATION_UNSUPPORTED_TRACK"
    assert HistoricalDatasetValidationGapCategory.VALIDATION_ORDER_FIELD_DETECTED.value == "VALIDATION_ORDER_FIELD_DETECTED"
    assert HistoricalDatasetValidationGapCategory.VALIDATION_BUY_SELL_WORDING_DETECTED.value == "VALIDATION_BUY_SELL_WORDING_DETECTED"
    assert HistoricalDatasetValidationGapCategory.VALIDATION_REMOTE_SOURCE_NOT_ALLOWED.value == "VALIDATION_REMOTE_SOURCE_NOT_ALLOWED"
    assert HistoricalDatasetValidationGapCategory.VALIDATION_API_SOURCE_NOT_ALLOWED.value == "VALIDATION_API_SOURCE_NOT_ALLOWED"
    assert HistoricalDatasetValidationGapCategory.VALIDATION_NETWORK_SOURCE_NOT_ALLOWED.value == "VALIDATION_NETWORK_SOURCE_NOT_ALLOWED"
    assert HistoricalDatasetValidationGapCategory.VALIDATION_PROVIDER_SOURCE_NOT_ALLOWED.value == "VALIDATION_PROVIDER_SOURCE_NOT_ALLOWED"
    assert HistoricalDatasetValidationGapCategory.VALIDATION_LLM_METADATA_NOT_ALLOWED.value == "VALIDATION_LLM_METADATA_NOT_ALLOWED"
    assert HistoricalDatasetValidationGapCategory.VALIDATION_ML_TRAINING_TRIGGER_NOT_ALLOWED.value == "VALIDATION_ML_TRAINING_TRIGGER_NOT_ALLOWED"
    assert HistoricalDatasetValidationGapCategory.VALIDATION_CRAWLER_TRIGGER_NOT_ALLOWED.value == "VALIDATION_CRAWLER_TRIGGER_NOT_ALLOWED"
    assert HistoricalDatasetValidationGapCategory.VALIDATION_LIVE_PROD_NOT_ALLOWED.value == "VALIDATION_LIVE_PROD_NOT_ALLOWED"
    assert HistoricalDatasetValidationGapCategory.VALIDATION_PARQUET_NOT_ALLOWED.value == "VALIDATION_PARQUET_NOT_ALLOWED"


@pytest.mark.parametrize(
    ("payload", "message"),
    [
        ({"feature_block": {"outcome_label": "OUTCOME_FAVORABLE"}}, "outcome label"),
        ({"feature_block": {"forward_return_pct": 0.1}}, "forward return"),
        ({"feature_block": {"max_favorable_excursion_pct": 0.2}}, "max favorable"),
        ({"feature_block": {"max_adverse_excursion_pct": -0.2}}, "max adverse"),
        ({"feature_block": {"forward_close_price": 70000.0}}, "post-anchor"),
        ({"scanner_replay_input": {"outcome_label": "OUTCOME_FAVORABLE"}}, "scanner input"),
    ],
)
def test_historical_dataset_validation_guard_rejects_feature_outcome_boundary_violations(payload, message):
    with pytest.raises(ValueError, match=message):
        validate_historical_dataset_validation_feature_outcome_boundary(payload, context="historical dataset validation")


def test_historical_dataset_validation_guard_rejects_random_shuffle_marker():
    with pytest.raises(ValueError, match="random shuffle"):
        validate_historical_dataset_validation_split_integrity({"allow_random_shuffle": True}, context="historical dataset validation")


def test_historical_dataset_validation_guard_rejects_duplicate_split_record_refs():
    with pytest.raises(ValueError, match="duplicated"):
        validate_historical_dataset_validation_split_integrity(
            {
                "record_refs": [
                    {"dataset_record_id": "DATASET-RECORD-1", "split_partition": "TRAIN"},
                    {"dataset_record_id": "DATASET-RECORD-1", "split_partition": "TRAIN"},
                ]
            },
            context="historical dataset validation",
        )


def test_historical_dataset_validation_guard_rejects_split_partition_overlap():
    with pytest.raises(ValueError, match="overlap"):
        validate_historical_dataset_validation_split_integrity(
            {
                "partition_overlap": True,
            },
            context="historical dataset validation",
        )


@pytest.mark.parametrize(
    ("payload", "message"),
    [
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
        ({"runtime_backend": "cloud model"}, "cloud_model"),
        ({"ml_training_job": "fit"}, "training"),
        ({"crawler_trigger": "run"}, "crawler"),
        ({"parquet_path": "fixture.parquet"}, "parquet"),
    ],
)
def test_historical_dataset_validation_guard_rejects_unsafe_metadata(payload, message):
    with pytest.raises(ValueError, match=message):
        validate_historical_dataset_validation_metadata_safety(payload, context="historical dataset validation")
