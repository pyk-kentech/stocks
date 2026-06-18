import pytest

from stock_risk_mcp.historical_calendar_models import (
    CalendarSafetyBoundary,
    HistoricalCalendarEventSnapshot,
)


def market_profile_payload():
    return {
        "market_id": "KRX",
        "country": "KR",
        "base_currency": "KRW",
        "exchange_session_profile": "KRX_CASH",
        "trading_hours": "09:00-15:30",
        "settlement_cash_availability": "T+2",
        "fee_tax_profile_reference": "profiles/domestic_kr_fee_tax.json",
        "realtime_data_profile_reference": "profiles/domestic_kr_realtime.json",
        "provider_capability_reference": "profiles/domestic_kr_local_file_only.json",
    }


def historical_calendar_snapshot_payload():
    return {
        "schema_version": "5.1-historical-calendar-event-snapshot",
        "snapshot_id": "calendar-domestic-kr-1",
        "created_at": "2026-06-18T09:00:00+09:00",
        "calendar_config": {
            "calendar_config_id": "calendar-config-1",
            "strategy_track": "DOMESTIC_KR",
            "market_profile": market_profile_payload(),
            "source_type": "local_csv",
            "session_validation_mode": "STRICT",
            "unexpected_closure_policy": "FAIL_CLOSED",
            "early_close_policy": "FAIL_CLOSED",
            "event_type_policy": "STRICT",
            "timezone_mismatch_policy": "FAIL_CLOSED",
        },
        "session_records": [
            {
                "market": "KRX",
                "date": "2026-06-18",
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
            }
        ],
        "market_events": [
            {
                "event_id": "market-event-1",
                "market": "KRX",
                "event_date": "2026-06-18",
                "event_time": "2026-06-18T08:30:00+09:00",
                "timezone": "Asia/Seoul",
                "event_type": "CPI_RELEASE",
                "event_scope": "MARKET_WIDE",
                "affected_symbols": [],
                "affected_market": "KRX",
                "source_id": "LOCAL_MACRO_EVENTS",
                "event_batch_id": "calendar-batch-1",
                "report_only": False,
                "non_executable": True,
            }
        ],
        "corporate_events": [
            {
                "symbol": "005930",
                "market": "KRX",
                "event_date": "2026-06-18",
                "event_type": "EARNINGS_BEFORE_OPEN",
                "earnings_before_open_flag": True,
                "earnings_after_close_flag": False,
                "dividend_ex_date_flag": False,
                "split_effective_date_flag": False,
                "corporate_action_adjustment_flag": False,
                "source_id": "LOCAL_CORPORATE_EVENTS",
            }
        ],
        "manifest": {
            "calendar_manifest_id": "calendar-manifest-1",
            "calendar_batch_id": "calendar-batch-1",
            "source_descriptor_ids": ["calendar-source-1"],
            "strategy_track": "DOMESTIC_KR",
            "market_profile_id": "KRX",
            "session_record_count": 1,
            "market_event_count": 1,
            "corporate_event_count": 1,
            "date_range_start": "2026-06-18T00:00:00+09:00",
            "date_range_end": "2026-06-18T23:59:59+09:00",
            "timezone": "Asia/Seoul",
            "validation_report_id": "calendar-validation-1",
            "gap_report_id": "calendar-gap-1",
            "safety_boundary": {},
        },
        "validation_report": {
            "calendar_validation_report_id": "calendar-validation-1",
            "calendar_batch_id": "calendar-batch-1",
            "strategy_track": "DOMESTIC_KR",
            "market_profile_id": "KRX",
            "validation_status": "VALID",
            "error_count": 0,
            "warning_count": 0,
            "validation_issues": [],
        },
        "gap_report": {
            "calendar_gap_report_id": "calendar-gap-1",
            "calendar_batch_id": "calendar-batch-1",
            "gap_status": "NO_GAPS",
            "gap_categories": [],
            "blocking_gap_count": 0,
            "report_only_gap_count": 0,
            "gaps": [],
        },
        "safety_boundary": {},
    }


def test_historical_calendar_fixture_constructs_valid_domestic_kr_local_csv_snapshot():
    snapshot = HistoricalCalendarEventSnapshot.model_validate(historical_calendar_snapshot_payload())

    assert snapshot.calendar_config.strategy_track.value == "DOMESTIC_KR"
    assert snapshot.calendar_config.market_profile.base_currency == "KRW"
    assert snapshot.calendar_config.source_type.value == "local_csv"
    assert snapshot.session_records[0].session_type.value == "REGULAR_SESSION"
    assert snapshot.market_events[0].event_type.value == "CPI_RELEASE"


def test_historical_calendar_fixture_constructs_valid_domestic_kr_local_jsonl_snapshot():
    payload = historical_calendar_snapshot_payload()
    payload["calendar_config"]["source_type"] = "local_jsonl"

    snapshot = HistoricalCalendarEventSnapshot.model_validate(payload)

    assert snapshot.calendar_config.source_type.value == "local_jsonl"


def test_historical_calendar_fixture_enforces_exact_schema_version():
    payload = historical_calendar_snapshot_payload()
    payload["schema_version"] = "5.1-historical-calendar-fixture"

    with pytest.raises(ValueError, match="schema_version must be exactly 5.1-historical-calendar-event-snapshot"):
        HistoricalCalendarEventSnapshot.model_validate(payload)


def test_historical_calendar_fixture_requires_timezone_aware_timestamps():
    payload = historical_calendar_snapshot_payload()
    payload["created_at"] = "2026-06-18T09:00:00"

    with pytest.raises(ValueError, match="timestamp must include timezone"):
        HistoricalCalendarEventSnapshot.model_validate(payload)


def test_historical_calendar_safety_boundary_defaults_deny_network_provider_exchange_broker_account_and_runtime_paths():
    boundary = CalendarSafetyBoundary()

    assert boundary.network_access_allowed is False
    assert boundary.provider_api_allowed is False
    assert boundary.exchange_api_allowed is False
    assert boundary.broker_api_allowed is False
    assert boundary.kiwoom_api_allowed is False
    assert boundary.ls_api_allowed is False
    assert boundary.account_access_allowed is False
    assert boundary.credential_access_allowed is False
    assert boundary.token_access_allowed is False
    assert boundary.live_or_prod_allowed is False
    assert boundary.cloud_llm_allowed is False
    assert boundary.local_model_runtime_allowed is False


def test_historical_calendar_fixture_rejects_invalid_source_type_value():
    payload = historical_calendar_snapshot_payload()
    payload["calendar_config"]["source_type"] = "remote_url"

    with pytest.raises(ValueError, match="Input should be 'local_csv' or 'local_jsonl'"):
        HistoricalCalendarEventSnapshot.model_validate(payload)


def test_historical_calendar_fixture_requires_market_event_target_scope():
    payload = historical_calendar_snapshot_payload()
    payload["market_events"][0]["affected_market"] = "   "

    with pytest.raises(
        ValueError,
        match="market event record requires affected_symbols or affected_market",
    ):
        HistoricalCalendarEventSnapshot.model_validate(payload)
