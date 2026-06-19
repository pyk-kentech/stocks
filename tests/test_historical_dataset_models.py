import json

import pytest

from stock_risk_mcp.historical_dataset_guard import (
    validate_historical_dataset_feature_outcome_boundary,
    validate_historical_dataset_metadata_safety,
)
from stock_risk_mcp.historical_dataset_fixture import load_historical_dataset_fixture
from stock_risk_mcp.historical_dataset_models import (
    HistoricalDatasetAssemblyInput,
    HistoricalDatasetAssemblyConfig,
    HistoricalDatasetFeatureBlock,
    HistoricalDatasetGapCategory,
    HistoricalDatasetOutcomeBlock,
    HistoricalDatasetSafetyReport,
)
from tests.test_historical_outcome_models import historical_outcome_fixture_payload


def historical_dataset_fixture_payload():
    outcome_payload = historical_outcome_fixture_payload()
    return {
        "schema_version": "5.4-historical-dataset-assembly-input",
        "assembly_input_id": "dataset-assembly-input-1",
        "assembly_config": {
            "config_id": "dataset-assembly-config-1",
            "strategy_track": "DOMESTIC_KR",
            "export_formats": ["json", "jsonl", "csv"],
        },
        "historical_market_data_snapshot": outcome_payload["historical_market_data_snapshot"],
        "historical_calendar_event_snapshot": outcome_payload["historical_calendar_event_snapshot"],
        "replay_event_stream": outcome_payload["replay_event_stream"],
        "replay_window_bundle": outcome_payload["replay_window_bundle"],
        "scanner_replay_input": outcome_payload["scanner_replay_input"],
        "historical_outcome_observation_input": outcome_payload,
        "records": [
            {
                "record_id": "dataset-record-1",
                "strategy_track": "DOMESTIC_KR",
                "market_profile_id": "KRX",
                "symbol": "005930",
                "market": "KRX",
                "replay_session_date": "2026-06-18",
                "replay_event_ids": ["event-1"],
                "replay_window_id": "window-1",
                "scanner_replay_candidate_seed_id": "seed-1",
                "outcome_observation_id": "observation-input-1",
                "feature_block": {
                    "block_id": "feature-block-1",
                    "replay_context_id": "context-1",
                    "scanner_replay_input_id": "replay-input-1",
                    "known_event_context_summary": "known-at-replay",
                    "attached_market_event_count": 0,
                    "attached_corporate_event_count": 0,
                },
                "outcome_block": {
                    "block_id": "outcome-block-1",
                    "outcome_observed_after_anchor": True,
                    "outcome_label": "OUTCOME_REPORT_ONLY",
                    "forward_return_pct": 0.01,
                    "max_favorable_excursion_pct": 0.02,
                    "max_adverse_excursion_pct": -0.01,
                    "sessions_observed": 1,
                    "missing_session_count": 0,
                    "early_close_count": 0,
                },
                "source_manifest_ids": ["manifest-1", "calendar-manifest-1"],
                "source_audit_record_ids": ["audit-1"],
                "provider_provenance_ids": ["provenance-1"],
            }
        ],
        "export_manifest": {
            "manifest_id": "dataset-export-manifest-1",
            "record_count": 1,
            "export_formats": ["json", "jsonl", "csv"],
            "source_manifest_ids": ["manifest-1", "calendar-manifest-1"],
            "source_audit_record_ids": ["audit-1"],
            "provider_provenance_ids": ["provenance-1"],
        },
        "quality_report": {
            "quality_report_id": "dataset-quality-report-1",
            "record_count": 1,
            "valid_record_count": 1,
            "warning_count": 0,
            "warnings": [],
            "source_manifest_ids": ["manifest-1", "calendar-manifest-1"],
            "source_audit_record_ids": ["audit-1"],
            "provider_provenance_ids": ["provenance-1"],
        },
        "gap_report": {
            "gap_report_id": "dataset-gap-report-1",
            "gap_status": "NO_GAPS",
            "gap_categories": [],
            "blocking_gap_count": 0,
            "report_only_gap_count": 0,
            "gaps": [],
            "source_manifest_ids": ["manifest-1", "calendar-manifest-1"],
            "source_audit_record_ids": ["audit-1"],
            "provider_provenance_ids": ["provenance-1"],
        },
        "safety_report": {
            "safety_report_id": "dataset-safety-report-1",
        },
        "audit_records": [
            {
                "audit_record_id": "dataset-audit-record-1",
                "assembly_input_id": "dataset-assembly-input-1",
                "created_at": "2026-06-18T16:00:00+09:00",
                "operator_context": "TEST",
                "source_path": "fixtures/historical/historical_dataset_fixture.json",
                "source_manifest_ids": ["manifest-1", "calendar-manifest-1"],
                "source_audit_record_ids": ["audit-1"],
                "provider_provenance_ids": ["provenance-1"],
            }
        ],
    }


def test_historical_dataset_models_accept_local_fixture_only_inputs(tmp_path):
    fixture_file = tmp_path / "historical_dataset_fixture.json"
    fixture_file.write_text(json.dumps(historical_dataset_fixture_payload()), encoding="utf-8")

    dataset_input = load_historical_dataset_fixture(fixture_file)

    assert isinstance(dataset_input, HistoricalDatasetAssemblyInput)
    assert isinstance(dataset_input.assembly_config, HistoricalDatasetAssemblyConfig)
    assert isinstance(dataset_input.records[0].feature_block, HistoricalDatasetFeatureBlock)
    assert isinstance(dataset_input.records[0].outcome_block, HistoricalDatasetOutcomeBlock)
    assert HistoricalDatasetSafetyReport.model_fields["report_only"].default is True
    assert dataset_input.assembly_config.read_only is True
    assert dataset_input.records[0].report_only is True
    assert dataset_input.records[0].outcome_block.outcome_observed_after_anchor is True


def test_historical_dataset_feature_block_rejects_outcome_label():
    payload = historical_dataset_fixture_payload()
    payload["records"][0]["feature_block"]["outcome_label"] = "OUTCOME_FAVORABLE"

    with pytest.raises(ValueError, match="outcome label"):
        HistoricalDatasetAssemblyInput.model_validate(payload)


def test_historical_dataset_feature_block_rejects_forward_return():
    payload = historical_dataset_fixture_payload()
    payload["records"][0]["feature_block"]["forward_return_pct"] = 0.1

    with pytest.raises(ValueError, match="forward return"):
        HistoricalDatasetAssemblyInput.model_validate(payload)


def test_historical_dataset_feature_block_rejects_mfe_and_mae():
    payload = historical_dataset_fixture_payload()
    payload["records"][0]["feature_block"]["max_favorable_excursion_pct"] = 0.2

    with pytest.raises(ValueError, match="post-anchor actual values"):
        HistoricalDatasetAssemblyInput.model_validate(payload)

    payload = historical_dataset_fixture_payload()
    payload["records"][0]["feature_block"]["max_adverse_excursion_pct"] = -0.2

    with pytest.raises(ValueError, match="post-anchor actual values"):
        HistoricalDatasetAssemblyInput.model_validate(payload)


def test_historical_dataset_models_require_safety_flags():
    payload = historical_dataset_fixture_payload()
    payload["assembly_config"]["no_order"] = False

    with pytest.raises(ValueError, match="no_order"):
        HistoricalDatasetAssemblyInput.model_validate(payload)


def test_historical_dataset_fixture_loader_wraps_source_path_in_error(tmp_path):
    fixture_file = tmp_path / "historical_dataset_fixture.txt"
    fixture_file.write_text(json.dumps(historical_dataset_fixture_payload()), encoding="utf-8")

    with pytest.raises(ValueError, match=str(fixture_file)):
        load_historical_dataset_fixture(fixture_file)


def test_historical_dataset_fixture_rejects_parquet_metadata(tmp_path):
    payload = historical_dataset_fixture_payload()
    payload["export_manifest"]["export_formats"] = ["parquet"]
    fixture_file = tmp_path / "historical_dataset_fixture.json"
    fixture_file.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(ValueError, match="parquet"):
        load_historical_dataset_fixture(fixture_file)


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
        ({"runtime_backend": "local model runtime"}, "cloud_model"),
        ({"ml_training_job": "fit"}, "training"),
        ({"crawler_trigger": "run"}, "crawler"),
        ({"parquet_path": "fixture.parquet"}, "parquet"),
    ],
)
def test_historical_dataset_guard_rejects_unsafe_metadata(payload, message):
    with pytest.raises(ValueError, match=message):
        validate_historical_dataset_metadata_safety(payload, context="historical dataset")


def test_historical_dataset_guard_rejects_mutated_scanner_marker():
    payload = {"scanner_replay_input": {"outcome_label": "OUTCOME_FAVORABLE"}}

    with pytest.raises(ValueError, match="pre-outcome scanner input"):
        validate_historical_dataset_feature_outcome_boundary(payload, context="historical dataset")


def test_historical_dataset_gap_taxonomy_exposes_required_v54_categories():
    assert HistoricalDatasetGapCategory.DATASET_RECORD_GENERATED.value == "DATASET_RECORD_GENERATED"
    assert HistoricalDatasetGapCategory.DATASET_REPORT_ONLY.value == "DATASET_REPORT_ONLY"
    assert HistoricalDatasetGapCategory.DATASET_FEATURE_OUTCOME_LEAKAGE_DETECTED.value == "DATASET_FEATURE_OUTCOME_LEAKAGE_DETECTED"
    assert HistoricalDatasetGapCategory.DATASET_OUTCOME_LABEL_IN_FEATURES_DETECTED.value == "DATASET_OUTCOME_LABEL_IN_FEATURES_DETECTED"
    assert HistoricalDatasetGapCategory.DATASET_FORWARD_RETURN_IN_FEATURES_DETECTED.value == "DATASET_FORWARD_RETURN_IN_FEATURES_DETECTED"
    assert HistoricalDatasetGapCategory.DATASET_SCANNER_INPUT_MUTATION_DETECTED.value == "DATASET_SCANNER_INPUT_MUTATION_DETECTED"
    assert HistoricalDatasetGapCategory.DATASET_ORDER_FIELD_DETECTED.value == "DATASET_ORDER_FIELD_DETECTED"
    assert HistoricalDatasetGapCategory.DATASET_BUY_SELL_WORDING_DETECTED.value == "DATASET_BUY_SELL_WORDING_DETECTED"
    assert HistoricalDatasetGapCategory.DATASET_REMOTE_SOURCE_NOT_ALLOWED.value == "DATASET_REMOTE_SOURCE_NOT_ALLOWED"
    assert HistoricalDatasetGapCategory.DATASET_API_SOURCE_NOT_ALLOWED.value == "DATASET_API_SOURCE_NOT_ALLOWED"
    assert HistoricalDatasetGapCategory.DATASET_NETWORK_SOURCE_NOT_ALLOWED.value == "DATASET_NETWORK_SOURCE_NOT_ALLOWED"
    assert HistoricalDatasetGapCategory.DATASET_PROVIDER_SOURCE_NOT_ALLOWED.value == "DATASET_PROVIDER_SOURCE_NOT_ALLOWED"
    assert HistoricalDatasetGapCategory.DATASET_LLM_METADATA_NOT_ALLOWED.value == "DATASET_LLM_METADATA_NOT_ALLOWED"
    assert HistoricalDatasetGapCategory.DATASET_ML_TRAINING_TRIGGER_NOT_ALLOWED.value == "DATASET_ML_TRAINING_TRIGGER_NOT_ALLOWED"
    assert HistoricalDatasetGapCategory.DATASET_CRAWLER_TRIGGER_NOT_ALLOWED.value == "DATASET_CRAWLER_TRIGGER_NOT_ALLOWED"
    assert HistoricalDatasetGapCategory.DATASET_LIVE_PROD_NOT_ALLOWED.value == "DATASET_LIVE_PROD_NOT_ALLOWED"
    assert HistoricalDatasetGapCategory.DATASET_PARQUET_NOT_ALLOWED.value == "DATASET_PARQUET_NOT_ALLOWED"
