import copy

import pytest

from stock_risk_mcp.historical_outcome_engine import (
    build_historical_outcome_label_report,
    build_historical_outcome_windows,
)
from stock_risk_mcp.historical_outcome_models import HistoricalOutcomeObservationInput
from tests.test_historical_outcome_models import historical_outcome_fixture_payload


def build_input(payload=None):
    return HistoricalOutcomeObservationInput.model_validate(payload or historical_outcome_fixture_payload())


def _multi_session_payload():
    payload = historical_outcome_fixture_payload()
    payload["replay_window_bundle"]["windows"] = [
        {
            "window_id": "window-1",
            "replay_event_stream_id": "stream-1",
            "bridge_input_id": "bridge-input-1",
            "strategy_track": "DOMESTIC_KR",
            "market_profile_id": "KRX",
            "session_date": "2026-06-19",
            "window_size_sessions": 1,
            "window_session_dates": ["2026-06-19"],
            "event_ids": ["event-1"],
            "historical_market_snapshot_id": "historical-domestic-kr-1",
            "historical_calendar_snapshot_id": "calendar-domestic-kr-1",
            "source_manifest_ids": ["manifest-1", "calendar-manifest-1"],
            "source_audit_record_ids": ["audit-1"],
            "provider_provenance_ids": ["provenance-1"],
            "market_event_contexts": [
                {
                    "context_id": "market-context-1",
                    "replay_window_id": "window-1",
                    "replay_event_stream_id": "stream-1",
                    "bridge_input_id": "bridge-input-1",
                    "context_scope": "MARKET_WIDE",
                    "event_source_record_id": "macro-1",
                    "event_source_id": "LOCAL_MACRO_EVENTS",
                    "event_batch_id": "calendar-batch-1",
                    "event_type": "CPI_RELEASE",
                    "market": "KRX",
                    "symbol": None,
                    "event_date": "2026-06-19",
                    "event_time": "2026-06-19T08:30:00+09:00",
                    "known_at": None,
                    "known_time_complete": False,
                    "historical_market_snapshot_id": "historical-domestic-kr-1",
                    "historical_calendar_snapshot_id": "calendar-domestic-kr-1",
                    "source_manifest_ids": ["manifest-1", "calendar-manifest-1"],
                    "source_audit_record_ids": ["audit-1"],
                    "provider_provenance_ids": ["provenance-1"],
                }
            ],
            "corporate_event_contexts": [],
        }
    ]
    payload["replay_window_bundle"]["event_context_report"] = {
        "attachment_report_id": "attachment-report-1",
        "replay_event_stream_id": "stream-1",
        "bridge_input_id": "bridge-input-1",
        "historical_market_snapshot_id": "historical-domestic-kr-1",
        "historical_calendar_snapshot_id": "calendar-domestic-kr-1",
        "source_manifest_ids": ["manifest-1", "calendar-manifest-1"],
        "source_audit_record_ids": ["audit-1"],
        "provider_provenance_ids": ["provenance-1"],
        "attached_market_event_count": 1,
        "attached_corporate_event_count": 0,
        "event_source_ids": ["LOCAL_MACRO_EVENTS"],
        "event_batch_ids": ["CALENDAR-BATCH-1"],
    }
    payload["replay_event_stream"]["events"] = [
        {
            "replay_event_id": "event-1",
            "bridge_input_id": "bridge-input-1",
            "symbol": "005930",
            "market": "KRX",
            "session_date": "2026-06-19",
            "replay_timestamp": "2026-06-19T09:00:00+09:00",
            "source_record_id": "source-record-1",
            "source_source_id": "KRX_MANUAL_EXPORT",
            "currency": "KRW",
            "timezone": "Asia/Seoul",
            "source_manifest_ids": ["manifest-1", "calendar-manifest-1"],
            "source_audit_record_ids": ["audit-1"],
            "provider_provenance_ids": ["provenance-1"],
            "historical_market_snapshot_id": "historical-domestic-kr-1",
            "historical_calendar_snapshot_id": "calendar-domestic-kr-1",
        }
    ]
    payload["historical_market_data_snapshot"]["records"] = [
        {
            "symbol": "005930",
            "market": "KRX",
            "timestamp": "2026-06-19T09:00:00+09:00",
            "timezone": "Asia/Seoul",
            "open": 70000,
            "high": 71000,
            "low": 69900,
            "close": 70500,
            "volume": 1000,
            "currency": "KRW",
            "source_id": "KRX_MANUAL_EXPORT",
            "ingestion_batch_id": "batch-1",
        },
        {
            "symbol": "005930",
            "market": "KRX",
            "timestamp": "2026-06-22T09:00:00+09:00",
            "timezone": "Asia/Seoul",
            "open": 70600,
            "high": 71200,
            "low": 70400,
            "close": 71100,
            "volume": 1100,
            "currency": "KRW",
            "source_id": "KRX_MANUAL_EXPORT",
            "ingestion_batch_id": "batch-1",
        },
        {
            "symbol": "005930",
            "market": "KRX",
            "timestamp": "2026-06-24T09:00:00+09:00",
            "timezone": "Asia/Seoul",
            "open": 71100,
            "high": 71600,
            "low": 70900,
            "close": 71400,
            "volume": 1200,
            "currency": "KRW",
            "source_id": "KRX_MANUAL_EXPORT",
            "ingestion_batch_id": "batch-1",
        },
    ]
    payload["historical_market_data_snapshot"]["quality_report"]["record_count"] = 3
    payload["historical_market_data_snapshot"]["quality_report"]["date_range_start"] = "2026-06-19T09:00:00+09:00"
    payload["historical_market_data_snapshot"]["quality_report"]["date_range_end"] = "2026-06-24T09:00:00+09:00"
    payload["historical_market_data_snapshot"]["manifest"]["record_count"] = 3
    payload["historical_market_data_snapshot"]["manifest"]["date_range_start"] = "2026-06-19T09:00:00+09:00"
    payload["historical_market_data_snapshot"]["manifest"]["date_range_end"] = "2026-06-24T09:00:00+09:00"
    payload["historical_calendar_event_snapshot"]["session_records"] = [
        {
            "market": "KRX",
            "date": "2026-06-19",
            "timezone": "Asia/Seoul",
            "is_trading_day": True,
            "is_holiday": False,
            "is_early_close": False,
            "regular_open_time": "09:00:00",
            "regular_close_time": "15:30:00",
            "actual_open_time": "09:00:00",
            "actual_close_time": "15:30:00",
            "session_type": "REGULAR_SESSION",
            "source_id": "KRX_LOCAL_CALENDAR",
            "calendar_batch_id": "calendar-batch-1",
        },
        {
            "market": "KRX",
            "date": "2026-06-22",
            "timezone": "Asia/Seoul",
            "is_trading_day": True,
            "is_holiday": False,
            "is_early_close": True,
            "regular_open_time": "09:00:00",
            "regular_close_time": "15:30:00",
            "actual_open_time": "09:00:00",
            "actual_close_time": "12:00:00",
            "session_type": "EARLY_CLOSE",
            "source_id": "KRX_LOCAL_CALENDAR",
            "calendar_batch_id": "calendar-batch-1",
        },
        {
            "market": "KRX",
            "date": "2026-06-23",
            "timezone": "Asia/Seoul",
            "is_trading_day": False,
            "is_holiday": True,
            "is_early_close": False,
            "regular_open_time": "09:00:00",
            "regular_close_time": "15:30:00",
            "actual_open_time": None,
            "actual_close_time": None,
            "session_type": "MARKET_HOLIDAY",
            "source_id": "KRX_LOCAL_CALENDAR",
            "calendar_batch_id": "calendar-batch-1",
        },
        {
            "market": "KRX",
            "date": "2026-06-24",
            "timezone": "Asia/Seoul",
            "is_trading_day": True,
            "is_holiday": False,
            "is_early_close": False,
            "regular_open_time": "09:00:00",
            "regular_close_time": "15:30:00",
            "actual_open_time": "09:00:00",
            "actual_close_time": "15:30:00",
            "session_type": "REGULAR_SESSION",
            "source_id": "KRX_LOCAL_CALENDAR",
            "calendar_batch_id": "calendar-batch-1",
        },
    ]
    payload["historical_calendar_event_snapshot"]["manifest"]["session_record_count"] = 4
    payload["historical_calendar_event_snapshot"]["manifest"]["date_range_start"] = "2026-06-19T00:00:00+09:00"
    payload["historical_calendar_event_snapshot"]["manifest"]["date_range_end"] = "2026-06-24T23:59:59+09:00"
    payload["observation_windows"] = []
    payload["observation_records"] = []
    payload["metric_sets"] = []
    payload["label_report"]["labels"] = []
    return payload


def test_build_historical_outcome_windows_uses_trading_sessions_and_skips_holidays():
    result = build_historical_outcome_windows(build_input(_multi_session_payload()), forward_window_sizes=(1, 2))

    assert [window.window_size_sessions for window in result.observation_windows] == [1, 2]
    assert [day.isoformat() for day in result.observation_windows[0].window_session_dates] == ["2026-06-22"]
    assert [day.isoformat() for day in result.observation_windows[1].window_session_dates] == ["2026-06-22", "2026-06-24"]
    assert all("2026-06-23" not in [day.isoformat() for day in window.window_session_dates] for window in result.observation_windows)
    assert result.metric_sets[0].anchor_close_price == 70500.0
    assert result.metric_sets[0].forward_close_price == 71100.0
    assert result.metric_sets[1].forward_close_price == 71400.0
    assert result.metric_sets[1].sessions_observed == 2


def test_build_historical_outcome_windows_flags_early_close_and_preserves_event_context_flags():
    result = build_historical_outcome_windows(build_input(_multi_session_payload()), forward_window_sizes=(2,))

    metric_set = result.metric_sets[0]
    assert metric_set.early_close_count == 1
    assert metric_set.has_market_event_context is True
    assert metric_set.has_corporate_event_context is False
    assert any(gap.message.endswith("includes early-close sessions") for gap in result.gap_report.gaps)


def test_build_historical_outcome_windows_fails_closed_without_calendar_by_default():
    payload = _multi_session_payload()
    payload["historical_calendar_event_snapshot"] = None

    with pytest.raises(ValueError, match="missing trading calendar"):
        build_historical_outcome_windows(build_input(payload), forward_window_sizes=(1,))


def test_build_historical_outcome_windows_supports_explicit_report_only_degraded_mode_for_missing_calendar():
    payload = _multi_session_payload()
    payload["observation_config"]["allow_report_only_degraded_calendar"] = True
    payload["historical_calendar_event_snapshot"] = None
    payload["replay_event_stream"]["historical_calendar_snapshot_id"] = None
    payload["replay_window_bundle"]["historical_calendar_snapshot_id"] = None
    payload["scanner_replay_input"]["historical_calendar_snapshot_id"] = None
    payload["scanner_replay_input"]["replay_context"]["historical_calendar_snapshot_id"] = None

    result = build_historical_outcome_windows(build_input(payload), forward_window_sizes=(1,))

    assert result.observation_windows == []
    assert result.observation_records == []
    assert result.metric_sets == []
    assert [gap.gap_category.value for gap in result.gap_report.gaps] == [
        "OUTCOME_MISSING_TRADING_CALENDAR",
        "OUTCOME_REPORT_ONLY",
    ]


def test_build_historical_outcome_windows_produces_explicit_gap_for_missing_forward_price_and_does_not_mutate_scanner_input():
    payload = _multi_session_payload()
    payload["historical_market_data_snapshot"]["records"] = payload["historical_market_data_snapshot"]["records"][:2]
    payload["historical_market_data_snapshot"]["quality_report"]["record_count"] = 2
    payload["historical_market_data_snapshot"]["manifest"]["record_count"] = 2
    observation_input = build_input(payload)
    before = copy.deepcopy(observation_input.scanner_replay_input.model_dump(mode="json"))

    result = build_historical_outcome_windows(observation_input, forward_window_sizes=(2,))

    after = observation_input.scanner_replay_input.model_dump(mode="json")
    assert before == after
    assert result.observation_windows == []
    assert any(gap.gap_category.value == "OUTCOME_MISSING_FORWARD_PRICE" for gap in result.gap_report.gaps)


def test_build_historical_outcome_label_report_assigns_favorable_label_from_metrics():
    payload = historical_outcome_fixture_payload()
    payload["label_report"]["labels"] = []
    payload["observation_config"]["favorable_return_threshold_pct"] = 0.009
    payload["observation_config"]["adverse_return_threshold_pct"] = 0.02
    payload["observation_config"]["volatile_mfe_threshold_pct"] = 0.05
    payload["observation_config"]["volatile_mae_threshold_pct"] = 0.04

    result = build_historical_outcome_label_report(build_input(payload))

    assert [label.label_type.value for label in result.label_report.labels] == ["OUTCOME_FAVORABLE"]
    assert result.label_report.labels[0].reason_code == "FAVORABLE_RETURN_THRESHOLD_MET"
    assert result.label_report.labels[0].report_only is True


def test_build_historical_outcome_label_report_assigns_volatile_mixed_before_directional_labels():
    payload = historical_outcome_fixture_payload()
    payload["label_report"]["labels"] = []
    payload["observation_config"]["favorable_return_threshold_pct"] = 0.05
    payload["observation_config"]["adverse_return_threshold_pct"] = 0.05
    payload["observation_config"]["volatile_mfe_threshold_pct"] = 0.015
    payload["observation_config"]["volatile_mae_threshold_pct"] = 0.009

    result = build_historical_outcome_label_report(build_input(payload))

    assert [label.label_type.value for label in result.label_report.labels] == ["OUTCOME_VOLATILE_MIXED"]
    assert result.label_report.labels[0].reason_code == "VOLATILE_MIXED_THRESHOLD_MET"


def test_build_historical_outcome_label_report_fails_closed_when_threshold_config_is_missing():
    payload = historical_outcome_fixture_payload()
    payload["label_report"]["labels"] = []
    payload["observation_config"]["favorable_return_threshold_pct"] = None

    result = build_historical_outcome_label_report(build_input(payload))

    assert [label.label_type.value for label in result.label_report.labels] == ["OUTCOME_INCONCLUSIVE"]
    assert result.label_report.labels[0].reason_code == "THRESHOLD_CONFIG_MISSING"
    assert any(gap.gap_category.value == "OUTCOME_THRESHOLD_CONFIG_MISSING" for gap in result.gap_report.gaps)


def test_build_historical_outcome_label_report_marks_insufficient_forward_data_from_existing_gaps():
    payload = historical_outcome_fixture_payload()
    payload["label_report"]["labels"] = []
    payload["gap_report"]["gap_status"] = "REPORT_ONLY_GAPS"
    payload["gap_report"]["gap_categories"] = ["OUTCOME_INSUFFICIENT_FORWARD_DATA"]
    payload["gap_report"]["blocking_gap_count"] = 0
    payload["gap_report"]["report_only_gap_count"] = 1
    payload["gap_report"]["gaps"] = [
        {
            "gap_id": "gap-insufficient-forward-data-1",
            "gap_category": "OUTCOME_INSUFFICIENT_FORWARD_DATA",
            "severity": "REPORT_ONLY",
            "message": "insufficient forward data",
            "source_manifest_id": "manifest-1",
            "source_audit_record_id": "audit-1",
            "provider_provenance_id": "provenance-1",
        }
    ]

    result = build_historical_outcome_label_report(build_input(payload))

    assert [label.label_type.value for label in result.label_report.labels] == ["OUTCOME_INSUFFICIENT_FORWARD_DATA"]
    assert result.label_report.labels[0].reason_code == "INSUFFICIENT_FORWARD_DATA"


def test_build_historical_outcome_label_report_blocks_leakage_risk_from_scanner_input():
    payload = historical_outcome_fixture_payload()
    payload["label_report"]["labels"] = []
    payload["scanner_replay_input"]["candidate_seeds"][0]["source_window_id"] = "OUTCOME_FAVORABLE"

    result = build_historical_outcome_label_report(build_input(payload))

    assert [label.label_type.value for label in result.label_report.labels] == ["OUTCOME_BLOCKED_SAFETY"]
    assert result.label_report.labels[0].reason_code == "LEAKAGE_RISK_DETECTED"
    assert any(gap.gap_category.value == "OUTCOME_LEAKAGE_RISK_DETECTED" for gap in result.gap_report.gaps)


def test_build_historical_outcome_label_report_blocks_buy_sell_wording_in_observation_metadata():
    payload = historical_outcome_fixture_payload()
    payload["label_report"]["labels"] = []
    payload["audit_records"][0]["operator_context"] = "BUY"

    result = build_historical_outcome_label_report(build_input(payload))

    assert [label.label_type.value for label in result.label_report.labels] == ["OUTCOME_BLOCKED_SAFETY"]
    assert result.label_report.labels[0].reason_code == "BUY_SELL_WORDING_DETECTED"
    assert any(gap.gap_category.value == "OUTCOME_BUY_SELL_WORDING_DETECTED" for gap in result.gap_report.gaps)


@pytest.mark.parametrize(
    ("payload_mutator", "expected_gap"),
    [
        (lambda payload: payload["audit_records"][0].__setitem__("source_path", "https://example.com/outcome.json"), "OUTCOME_REMOTE_SOURCE_NOT_ALLOWED"),
        (lambda payload: payload["audit_records"][0].__setitem__("operator_context", "provider api"), "OUTCOME_PROVIDER_SOURCE_NOT_ALLOWED"),
        (lambda payload: payload["audit_records"][0].__setitem__("operator_context", "network socket"), "OUTCOME_NETWORK_SOURCE_NOT_ALLOWED"),
        (lambda payload: payload["audit_records"][0].__setitem__("operator_context", "gemini"), "OUTCOME_LLM_METADATA_NOT_ALLOWED"),
        (lambda payload: payload["audit_records"][0].__setitem__("operator_context", "ml training"), "OUTCOME_ML_TRAINING_TRIGGER_NOT_ALLOWED"),
        (lambda payload: payload["audit_records"][0].__setitem__("operator_context", "crawler"), "OUTCOME_CRAWLER_TRIGGER_NOT_ALLOWED"),
        (lambda payload: payload["audit_records"][0].__setitem__("operator_context", "live prod"), "OUTCOME_LIVE_PROD_NOT_ALLOWED"),
        (lambda payload: payload["audit_records"][0].__setitem__("source_path", "fixtures/historical/outcome.parquet"), "OUTCOME_PARQUET_NOT_ALLOWED"),
        (lambda payload: payload["audit_records"][0].__setitem__("operator_context", "order"), "OUTCOME_ORDER_FIELD_DETECTED"),
    ],
)
def test_build_historical_outcome_label_report_maps_safety_violations_to_explicit_gaps(payload_mutator, expected_gap):
    payload = historical_outcome_fixture_payload()
    payload["label_report"]["labels"] = []
    payload_mutator(payload)

    result = build_historical_outcome_label_report(build_input(payload))

    assert [label.label_type.value for label in result.label_report.labels] == ["OUTCOME_BLOCKED_SAFETY"]
    assert any(gap.gap_category.value == expected_gap for gap in result.gap_report.gaps)


def test_build_historical_outcome_label_report_adds_report_only_warning_for_missing_known_time_metadata():
    observed = build_historical_outcome_windows(build_input(_multi_session_payload()), forward_window_sizes=(1,))
    before = copy.deepcopy(observed.scanner_replay_input.model_dump(mode="json"))

    result = build_historical_outcome_label_report(observed)

    after = observed.scanner_replay_input.model_dump(mode="json")
    assert before == after
    assert result.label_report.warning_count == len(result.label_report.warnings)
    assert any("known-time metadata" in warning for warning in result.label_report.warnings)
    assert any("missing known-time metadata for attached event context" in gap.message for gap in result.gap_report.gaps)
    assert result.safety_report.read_only is True
    assert result.safety_report.no_order is True


def test_build_historical_outcome_label_report_does_not_attach_labels_back_to_scanner_replay_input():
    payload = historical_outcome_fixture_payload()
    payload["label_report"]["labels"] = []
    observation_input = build_input(payload)
    before = copy.deepcopy(observation_input.scanner_replay_input.model_dump(mode="json"))

    result = build_historical_outcome_label_report(observation_input)

    after = observation_input.scanner_replay_input.model_dump(mode="json")
    result_scanner_input = result.scanner_replay_input.model_dump(mode="json")
    assert before == after == result_scanner_input
    assert "outcome_label" not in str(result_scanner_input).lower()
    assert result.label_report.labels[0].outcome_observed_after_anchor is True
