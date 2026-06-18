import json

from stock_risk_mcp.historical_calendar_engine import (
    build_historical_calendar_gap_report,
    build_historical_calendar_manifest,
    build_historical_calendar_validation_report,
    parse_corporate_event_records,
    parse_market_event_records,
    parse_trading_session_records,
)
from stock_risk_mcp.historical_calendar_models import (
    CalendarGapStatus,
    TradingCalendarConfig,
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


def build_calendar_config(source_type: str = "local_jsonl"):
    return TradingCalendarConfig.model_validate(
        {
            "calendar_config_id": "calendar-config-1",
            "strategy_track": "DOMESTIC_KR",
            "market_profile": market_profile_payload(),
            "source_type": source_type,
            "session_validation_mode": "STRICT",
            "unexpected_closure_policy": "FAIL_CLOSED",
            "early_close_policy": "FAIL_CLOSED",
            "event_type_policy": "STRICT",
            "timezone_mismatch_policy": "REPORT_ONLY",
        }
    )


def test_historical_calendar_engine_parses_local_jsonl_and_builds_reports(tmp_path):
    session_file = tmp_path / "sessions.jsonl"
    session_file.write_text(
        json.dumps(
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
        )
        + "\n",
        encoding="utf-8",
    )
    market_event_file = tmp_path / "market_events.jsonl"
    market_event_file.write_text(
        json.dumps(
            {
                "event_id": "market-event-1",
                "market": "KRX",
                "event_date": "2026-06-18",
                "event_time": "2026-06-18T08:30:00+09:00",
                "timezone": "Asia/Seoul",
                "event_type": "CPI_RELEASE",
                "event_scope": "MARKET_WIDE",
                "affected_market": "KRX",
                "affected_symbols": [],
                "source_id": "LOCAL_MACRO_EVENTS",
                "event_batch_id": "calendar-batch-1",
            }
        )
        + "\n",
        encoding="utf-8",
    )
    corporate_event_file = tmp_path / "corporate_events.jsonl"
    corporate_event_file.write_text(
        json.dumps(
            {
                "symbol": "005930",
                "market": "KRX",
                "event_date": "2026-06-18",
                "event_type": "EARNINGS_BEFORE_OPEN",
                "earnings_before_open_flag": True,
                "source_id": "LOCAL_CORPORATE_EVENTS",
            }
        )
        + "\n",
        encoding="utf-8",
    )
    calendar_config = build_calendar_config()

    session_records, session_issues = parse_trading_session_records(
        local_file_path=str(session_file),
        source_type=calendar_config.source_type,
    )
    market_events, market_event_issues = parse_market_event_records(
        local_file_path=str(market_event_file),
        source_type=calendar_config.source_type,
    )
    corporate_events, corporate_event_issues = parse_corporate_event_records(
        local_file_path=str(corporate_event_file),
        source_type=calendar_config.source_type,
    )
    validation = build_historical_calendar_validation_report(
        calendar_config=calendar_config,
        session_records=session_records,
        market_events=market_events,
        corporate_events=corporate_events,
        parse_issues=[*session_issues, *market_event_issues, *corporate_event_issues],
        calendar_batch_id="calendar-batch-1",
    )
    gap = build_historical_calendar_gap_report(
        calendar_config=calendar_config,
        validation_report=validation,
        calendar_batch_id="calendar-batch-1",
    )
    manifest = build_historical_calendar_manifest(
        calendar_config=calendar_config,
        session_records=session_records,
        market_events=market_events,
        corporate_events=corporate_events,
        validation_report=validation,
        gap_report=gap,
        calendar_batch_id="calendar-batch-1",
        source_descriptor_ids=["SESSIONS_JSONL", "MARKET_EVENTS_JSONL", "CORPORATE_EVENTS_JSONL"],
    )

    assert session_issues == []
    assert market_event_issues == []
    assert corporate_event_issues == []
    assert validation.validation_status.value == "VALID"
    assert gap.gap_status == CalendarGapStatus.NO_GAPS
    assert manifest.session_record_count == 1
    assert manifest.market_event_count == 1
    assert manifest.corporate_event_count == 1


def test_historical_calendar_engine_downgrades_event_timezone_mismatch_to_report_only_gap(tmp_path):
    session_file = tmp_path / "sessions.jsonl"
    session_file.write_text(
        json.dumps(
            {
                "market": "KRX",
                "date": "2026-06-18",
                "timezone": "Asia/Seoul",
                "is_trading_day": True,
                "is_holiday": False,
                "is_early_close": False,
                "session_type": "REGULAR_SESSION",
                "source_id": "KRX_LOCAL_CALENDAR",
                "calendar_batch_id": "calendar-batch-2",
            }
        )
        + "\n",
        encoding="utf-8",
    )
    market_event_file = tmp_path / "market_events.jsonl"
    market_event_file.write_text(
        json.dumps(
            {
                "event_id": "market-event-2",
                "market": "KRX",
                "event_date": "2026-06-18",
                "event_time": "2026-06-18T08:30:00+00:00",
                "timezone": "UTC",
                "event_type": "CPI_RELEASE",
                "event_scope": "MARKET_WIDE",
                "affected_market": "KRX",
                "affected_symbols": [],
                "source_id": "LOCAL_MACRO_EVENTS",
                "event_batch_id": "calendar-batch-2",
            }
        )
        + "\n",
        encoding="utf-8",
    )
    calendar_config = build_calendar_config()

    session_records, session_issues = parse_trading_session_records(
        local_file_path=str(session_file),
        source_type=calendar_config.source_type,
    )
    market_events, market_event_issues = parse_market_event_records(
        local_file_path=str(market_event_file),
        source_type=calendar_config.source_type,
    )
    validation = build_historical_calendar_validation_report(
        calendar_config=calendar_config,
        session_records=session_records,
        market_events=market_events,
        corporate_events=[],
        parse_issues=[*session_issues, *market_event_issues],
        calendar_batch_id="calendar-batch-2",
    )
    gap = build_historical_calendar_gap_report(
        calendar_config=calendar_config,
        validation_report=validation,
        calendar_batch_id="calendar-batch-2",
    )

    assert validation.validation_status.value == "VALID_WITH_WARNINGS"
    assert validation.warning_count == 1
    assert gap.gap_status == CalendarGapStatus.REPORT_ONLY_GAPS
    assert [item.value for item in gap.gap_categories] == ["TIMEZONE_MISMATCH"]
