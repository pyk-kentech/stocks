import json

import pytest

from stock_risk_mcp.historical_outcome_fixture import load_historical_outcome_fixture
from stock_risk_mcp.historical_outcome_guard import (
    validate_historical_outcome_metadata_safety,
    validate_historical_outcome_pre_outcome_boundary,
    validate_historical_outcome_source_type,
)
from stock_risk_mcp.historical_outcome_models import (
    HistoricalOutcomeGapCategory,
    HistoricalOutcomeLabel,
    HistoricalOutcomeObservationConfig,
    HistoricalOutcomeObservationInput,
    HistoricalOutcomeSafetyReport,
)
from tests.test_historical_replay_bridge_models import (
    _minimal_event_stream_payload,
    historical_calendar_snapshot_payload,
    historical_market_snapshot_payload,
)


def _window_bundle_payload():
    return {
        "window_bundle_id": "window-bundle-1",
        "replay_event_stream_id": "stream-1",
        "bridge_input_id": "bridge-input-1",
        "strategy_track": "DOMESTIC_KR",
        "market_profile_id": "KRX",
        "requested_window_sizes": [1, 3],
        "historical_market_snapshot_id": "historical-domestic-kr-1",
        "historical_calendar_snapshot_id": "calendar-domestic-kr-1",
        "source_manifest_ids": ["manifest-1", "calendar-manifest-1"],
        "source_audit_record_ids": ["audit-1"],
        "provider_provenance_ids": ["provenance-1"],
        "windows": [
            {
                "window_id": "window-1",
                "replay_event_stream_id": "stream-1",
                "bridge_input_id": "bridge-input-1",
                "strategy_track": "DOMESTIC_KR",
                "market_profile_id": "KRX",
                "session_date": "2026-06-18",
                "window_size_sessions": 1,
                "window_session_dates": ["2026-06-18"],
                "event_ids": ["event-1"],
                "historical_market_snapshot_id": "historical-domestic-kr-1",
                "historical_calendar_snapshot_id": "calendar-domestic-kr-1",
                "source_manifest_ids": ["manifest-1", "calendar-manifest-1"],
                "source_audit_record_ids": ["audit-1"],
                "provider_provenance_ids": ["provenance-1"],
            }
        ],
        "event_context_report": {
            "attachment_report_id": "attachment-report-1",
            "replay_event_stream_id": "stream-1",
            "bridge_input_id": "bridge-input-1",
            "historical_market_snapshot_id": "historical-domestic-kr-1",
            "historical_calendar_snapshot_id": "calendar-domestic-kr-1",
            "source_manifest_ids": ["manifest-1", "calendar-manifest-1"],
            "source_audit_record_ids": ["audit-1"],
            "provider_provenance_ids": ["provenance-1"],
            "attached_market_event_count": 0,
            "attached_corporate_event_count": 0,
            "event_source_ids": [],
            "event_batch_ids": [],
        },
        "gap_report": {
            "gap_report_id": "bridge-gap-report-1",
            "bridge_input_id": "bridge-input-1",
            "historical_market_snapshot_id": "historical-domestic-kr-1",
            "historical_calendar_snapshot_id": "calendar-domestic-kr-1",
            "source_manifest_ids": ["manifest-1", "calendar-manifest-1"],
            "source_audit_record_ids": ["audit-1"],
            "provider_provenance_ids": ["provenance-1"],
            "gap_categories": [],
            "blocking_gap_count": 0,
            "report_only_gap_count": 0,
            "gaps": [],
        },
    }


def _scanner_replay_input_payload():
    return {
        "replay_input_id": "replay-input-1",
        "strategy_track": "DOMESTIC_KR",
        "replay_context": {
            "context_id": "context-1",
            "strategy_track": "DOMESTIC_KR",
            "market_profile_id": "KRX",
            "historical_market_snapshot_id": "historical-domestic-kr-1",
            "historical_calendar_snapshot_id": "calendar-domestic-kr-1",
            "replay_event_stream_id": "stream-1",
            "source_window_bundle_id": "window-bundle-1",
            "scanner_window_ids": ["window-1"],
            "source_manifest_ids": ["manifest-1", "calendar-manifest-1"],
            "source_audit_record_ids": ["audit-1"],
            "provider_provenance_ids": ["provenance-1"],
        },
        "replay_event_stream_id": "stream-1",
        "source_window_bundle_id": "window-bundle-1",
        "historical_market_snapshot_id": "historical-domestic-kr-1",
        "historical_calendar_snapshot_id": "calendar-domestic-kr-1",
        "scanner_window_ids": ["window-1"],
        "event_source_ids": [],
        "source_manifest_ids": ["manifest-1", "calendar-manifest-1"],
        "source_audit_record_ids": ["audit-1"],
        "provider_provenance_ids": ["provenance-1"],
        "candidate_seeds": [
            {
                "seed_id": "seed-1",
                "symbol": "005930",
                "market": "KRX",
                "session_date": "2026-06-18",
                "reason_code": "CALENDAR_ALIGNED",
                "source_event_id": "event-1",
                "replay_event_stream_id": "stream-1",
                "source_window_id": "window-1",
                "scanner_context_id": "context-1",
                "source_manifest_ids": ["manifest-1", "calendar-manifest-1"],
                "source_audit_record_ids": ["audit-1"],
                "provider_provenance_ids": ["provenance-1"],
            }
        ],
    }


def historical_outcome_fixture_payload():
    return {
        "schema_version": "5.3-historical-outcome-observation-input",
        "observation_input_id": " observation-input-1 ",
        "observation_config": {
            "config_id": " historical-outcome-config-1 ",
            "strategy_track": "DOMESTIC_KR",
            "forward_window_sizes": [3, 1, 3],
            "favorable_return_threshold_pct": 0.03,
            "adverse_return_threshold_pct": 0.02,
            "volatile_mfe_threshold_pct": 0.05,
            "volatile_mae_threshold_pct": 0.04,
        },
        "replay_event_stream": _minimal_event_stream_payload(),
        "replay_window_bundle": _window_bundle_payload(),
        "scanner_replay_input": _scanner_replay_input_payload(),
        "historical_market_data_snapshot": historical_market_snapshot_payload(),
        "historical_calendar_event_snapshot": historical_calendar_snapshot_payload(),
        "observation_windows": [
            {
                "window_id": " outcome-window-1 ",
                "replay_window_id": "window-1",
                "symbol": "005930",
                "market": "KRX",
                "window_size_sessions": 3,
                "reference_timestamp": "2026-06-18T09:00:00+09:00",
                "observation_start_timestamp": "2026-06-18T09:01:00+09:00",
                "observation_end_timestamp": "2026-06-20T15:30:00+09:00",
                "window_session_dates": ["2026-06-18", "2026-06-19", "2026-06-20"],
                "historical_market_snapshot_id": "historical-domestic-kr-1",
                "historical_calendar_snapshot_id": "calendar-domestic-kr-1",
                "source_manifest_ids": ["manifest-1", "calendar-manifest-1"],
                "source_audit_record_ids": ["audit-1"],
                "provider_provenance_ids": ["provenance-1"],
            }
        ],
        "observation_records": [
            {
                "observation_record_id": "record-1",
                "window_id": "outcome-window-1",
                "symbol": "005930",
                "market": "KRX",
                "observation_timestamp": "2026-06-18T15:30:00+09:00",
                "close_price": 70500.0,
                "volume": 1000.0,
                "return_from_reference_pct": 0.01,
                "source_manifest_ids": ["manifest-1", "calendar-manifest-1"],
                "source_audit_record_ids": ["audit-1"],
                "provider_provenance_ids": ["provenance-1"],
            }
        ],
        "metric_sets": [
            {
                "metric_set_id": "metric-set-1",
                "window_id": "outcome-window-1",
                "observation_record_ids": ["record-1"],
                "reference_price": 69800.0,
                "anchor_close_price": 69800.0,
                "final_price": 70500.0,
                "forward_close_price": 70500.0,
                "forward_return_pct": 0.01,
                "max_favorable_excursion_pct": 0.02,
                "max_adverse_excursion_pct": -0.01,
                "final_return_pct": 0.01,
                "high_water_mark": 70500.0,
                "low_water_mark": 70500.0,
                "observed_volume_total": 1000.0,
                "observed_volume_average": 1000.0,
                "sessions_observed": 1,
                "missing_session_count": 0,
                "early_close_count": 0,
                "has_market_event_context": False,
                "has_corporate_event_context": False,
                "observed_point_count": 1,
            }
        ],
        "label_report": {
            "label_report_id": "label-report-1",
            "observation_input_id": "observation-input-1",
            "labels": [
                {
                    "label_id": "label-1",
                    "window_id": "outcome-window-1",
                    "metric_set_id": "metric-set-1",
                    "label_type": "OUTCOME_REPORT_ONLY",
                    "reason_code": "OFFLINE_OBSERVATION_ONLY",
                    "symbol": "005930",
                    "market": "KRX",
                    "final_return_pct": 0.01,
                }
            ],
            "warning_count": 0,
            "warnings": [],
            "source_manifest_ids": ["manifest-1", "calendar-manifest-1"],
            "source_audit_record_ids": ["audit-1"],
            "provider_provenance_ids": ["provenance-1"],
        },
        "gap_report": {
            "gap_report_id": "gap-report-1",
            "observation_input_id": "observation-input-1",
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
            "safety_report_id": "safety-report-1",
        },
        "audit_records": [
            {
                "audit_record_id": "audit-record-1",
                "observation_input_id": "observation-input-1",
                "created_at": "2026-06-18T16:00:00+09:00",
                "operator_context": "TEST",
                "source_path": "fixtures/historical/historical_outcome_fixture.json",
                "label_report_id": "label-report-1",
                "gap_report_id": "gap-report-1",
                "safety_report_id": "safety-report-1",
            }
        ],
    }


def test_historical_outcome_models_accept_fixture_only_inputs(tmp_path):
    fixture_file = tmp_path / "historical_outcome_fixture.json"
    fixture_file.write_text("{}", encoding="utf-8")

    with pytest.raises(ValueError, match="invalid historical outcome fixture at"):
        load_historical_outcome_fixture(fixture_file)

    fixture_file.write_text(json.dumps(historical_outcome_fixture_payload()), encoding="utf-8")
    observation_input = load_historical_outcome_fixture(fixture_file)

    assert isinstance(observation_input, HistoricalOutcomeObservationInput)
    assert HistoricalOutcomeLabel.model_fields["label_type"].annotation is not None
    assert HistoricalOutcomeObservationConfig.model_fields["read_only"].default is True
    assert HistoricalOutcomeSafetyReport.model_fields["no_order"].default is True
    assert observation_input.observation_input_id == "OBSERVATION-INPUT-1"
    assert observation_input.observation_config.forward_window_sizes == [1, 3]
    assert observation_input.label_report.labels[0].label_type.value == "OUTCOME_REPORT_ONLY"


def test_historical_outcome_models_reject_unsafe_runtime_flags():
    payload = historical_outcome_fixture_payload()
    payload["observation_config"]["no_order"] = False

    with pytest.raises(ValueError, match="no_order"):
        HistoricalOutcomeObservationInput.model_validate(payload)


def test_historical_outcome_models_require_timezone_aware_observation_timestamps():
    payload = historical_outcome_fixture_payload()
    payload["observation_windows"][0]["observation_end_timestamp"] = "2026-06-20T15:30:00"

    with pytest.raises(ValueError, match="timestamp must include timezone"):
        HistoricalOutcomeObservationInput.model_validate(payload)


def test_historical_outcome_fixture_requires_explicit_local_json_and_includes_source_path(tmp_path):
    fixture_file = tmp_path / "historical_outcome_fixture.txt"
    fixture_file.write_text(json.dumps(historical_outcome_fixture_payload()), encoding="utf-8")

    with pytest.raises(ValueError, match=str(fixture_file)):
        load_historical_outcome_fixture(fixture_file)


@pytest.mark.parametrize(
    ("payload", "message"),
    [
        ({"remote_url": "https://example.com/file.csv"}, "remote"),
        ({"provider_api": "broker"}, "provider"),
        ({"network_socket": "tcp://feed"}, "network"),
        ({"order_intent": "BUY"}, "order"),
        ({"execution_path": "paper execute"}, "execution"),
        ({"label_summary": "buy now"}, "buy_sell"),
        ({"mode": "live prod"}, "live_prod"),
        ({"broker_path": "broker"}, "broker"),
        ({"account_ref": "account"}, "account"),
        ({"kiwoom_source": "kiwoom"}, "kiwoom"),
        ({"ls_source": "ls"}, "ls"),
        ({"gemini_prompt": "analyze"}, "gemini"),
        ({"llm_summary": "llm"}, "llm"),
        ({"runtime_backend": "local model runtime"}, "cloud_model"),
        ({"ml_training_job": "fit"}, "training"),
        ({"crawler_trigger": "run"}, "crawler"),
        ({"parquet_path": "fixture.parquet"}, "parquet"),
        ({"runtime_signal": "OUTCOME_FAVORABLE"}, "runtime_signal"),
    ],
)
def test_historical_outcome_guard_rejects_unsafe_metadata(payload, message):
    with pytest.raises(ValueError, match=message):
        validate_historical_outcome_metadata_safety(payload, context="historical outcome")


@pytest.mark.parametrize("source_type", ["remote_url", "provider_api", "local_parquet"])
def test_historical_outcome_guard_rejects_non_local_source_types(source_type):
    with pytest.raises(ValueError, match="non-local source type"):
        validate_historical_outcome_source_type(source_type, context="historical outcome")


def test_historical_outcome_guard_rejects_outcome_label_attached_to_pre_outcome_scanner_input():
    payload = {
        "scanner_replay_input": {
            "candidate_seeds": [{"seed_id": "seed-1"}],
            "outcome_label": "OUTCOME_FAVORABLE",
        }
    }

    with pytest.raises(ValueError, match="pre-outcome scanner input"):
        validate_historical_outcome_pre_outcome_boundary(payload, context="historical outcome")


def test_historical_outcome_gap_taxonomy_exposes_required_v53_categories():
    assert HistoricalOutcomeGapCategory.OUTCOME_OBSERVATION_GENERATED.value == "OUTCOME_OBSERVATION_GENERATED"
    assert HistoricalOutcomeGapCategory.OUTCOME_REPORT_ONLY.value == "OUTCOME_REPORT_ONLY"
    assert HistoricalOutcomeGapCategory.OUTCOME_LEAKAGE_RISK_DETECTED.value == "OUTCOME_LEAKAGE_RISK_DETECTED"
    assert HistoricalOutcomeGapCategory.OUTCOME_PARQUET_NOT_ALLOWED.value == "OUTCOME_PARQUET_NOT_ALLOWED"
