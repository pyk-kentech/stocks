from __future__ import annotations

import copy

import pytest

from stock_risk_mcp.historical_replay_bridge_engine import (
    build_historical_replay_event_stream,
    build_historical_scanner_replay_input,
    build_historical_replay_windows,
    validate_historical_replay_event_stream,
)
from stock_risk_mcp.historical_replay_bridge_fixture import HistoricalReplayBridgeFixture
from stock_risk_mcp.historical_replay_bridge_guard import (
    validate_historical_replay_bridge_fixture_safety,
    validate_historical_replay_metadata_safety,
)


def market_profile_payload() -> dict:
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


def historical_market_snapshot_payload() -> dict:
    return {
        "schema_version": "5.1-historical-market-data-snapshot",
        "snapshot_id": "historical-domestic-kr-1",
        "created_at": "2026-06-18T09:00:00+09:00",
        "ingestion_config": {
            "config_id": "historical-config-1",
            "strategy_track": "DOMESTIC_KR",
            "market_profile": market_profile_payload(),
            "source_type": "local_csv",
            "strict_validation_mode": True,
            "allow_report_only_downgrade": False,
            "currency_mismatch_policy": "FAIL_CLOSED",
            "duplicate_record_policy": "FAIL_CLOSED",
            "missing_session_policy": "FAIL_CLOSED",
            "stale_batch_policy": "FAIL_CLOSED",
            "unsupported_track_policy": "FAIL_CLOSED",
            "unsafe_source_policy": "FAIL_CLOSED",
        },
        "source_descriptor": {
            "source_descriptor_id": "source-desc-1",
            "source_type": "local_csv",
            "local_file_path": "fixtures/historical/domestic_kr_ohlcv.csv",
            "declared_format": "CSV",
            "declared_content_type": "text/csv",
            "strategy_track": "DOMESTIC_KR",
            "market_profile_id": "KRX",
            "source_id": "KRX_MANUAL_EXPORT",
            "source_vendor_name": "KRX Manual Export",
            "source_reliability_tier": "OFFICIAL",
            "path_safety_class": "LOCAL_RELATIVE",
            "timezone": "Asia/Seoul",
            "currency": "KRW",
            "source_symbol_namespace": "KRX",
            "contains_adjusted_prices": False,
            "contains_unadjusted_prices": True,
            "contains_turnover": False,
            "contains_trade_value": False,
            "report_only": False,
        },
        "provider_provenance": {
            "provenance_id": "provenance-1",
            "source_family": "KRX_MANUAL_EXPORT",
            "source_name": "KRX Manual Export",
            "source_tier": "OFFICIAL",
            "acquisition_mode": "LOCAL_FILE",
            "original_export_context": "MANUAL_DOWNLOAD",
            "local_export_timestamp": "2026-06-18T08:59:00+09:00",
            "manual_or_automated_origin": "MANUAL",
            "requires_reconciliation": False,
            "official_source_reference": "KRX_EXPORT_PORTAL",
            "notes": "Local offline fixture",
        },
        "adjustment_policy": {
            "policy_id": "adjustment-policy-1",
            "price_adjustment_mode": "UNADJUSTED",
            "split_adjustment_expected": False,
            "dividend_adjustment_expected": False,
            "corporate_action_backfill_expected": False,
            "adjusted_close_required": False,
            "mixed_adjustment_state_allowed": False,
            "report_only_if_uncertain": True,
        },
        "records": [
            {
                "symbol": "005930",
                "market": "KRX",
                "timestamp": "2026-06-18T09:00:00+09:00",
                "timezone": "Asia/Seoul",
                "open": 70000,
                "high": 71000,
                "low": 69900,
                "close": 70500,
                "volume": 1000,
                "currency": "KRW",
                "source_id": "KRX_MANUAL_EXPORT",
                "ingestion_batch_id": "batch-1",
            }
        ],
        "validation_report": {
            "validation_report_id": "validation-1",
            "ingestion_batch_id": "batch-1",
            "strategy_track": "DOMESTIC_KR",
            "market_profile_id": "KRX",
            "validation_status": "VALID",
            "error_count": 0,
            "warning_count": 0,
            "validation_issues": [],
        },
        "gap_report": {
            "gap_report_id": "gap-1",
            "ingestion_batch_id": "batch-1",
            "gap_status": "NO_GAPS",
            "gap_categories": [],
            "blocking_gap_count": 0,
            "report_only_gap_count": 0,
            "gaps": [],
        },
        "quality_report": {
            "quality_report_id": "quality-1",
            "ingestion_batch_id": "batch-1",
            "record_count": 1,
            "symbol_count": 1,
            "market_count": 1,
            "date_range_start": "2026-06-18T09:00:00+09:00",
            "date_range_end": "2026-06-18T09:00:00+09:00",
            "timezone_distribution": {"Asia/Seoul": 1},
            "currency_distribution": {"KRW": 1},
            "missing_value_count": 0,
            "duplicate_count": 0,
            "invalid_ohlc_count": 0,
            "invalid_volume_count": 0,
            "out_of_order_count": 0,
            "missing_session_count": 0,
            "stale_batch_marker": False,
            "adjustment_policy_summary": {"price_adjustment_mode": "UNADJUSTED"},
            "quality_bucket": "READY",
        },
        "manifest": {
            "manifest_id": "manifest-1",
            "ingestion_batch_id": "batch-1",
            "source_descriptor_id": "source-desc-1",
            "source_file_path": "fixtures/historical/domestic_kr_ohlcv.csv",
            "source_file_hash": "sha256:fixture",
            "source_provenance": {
                "provenance_id": "provenance-1",
                "source_family": "KRX_MANUAL_EXPORT",
                "source_name": "KRX Manual Export",
                "source_tier": "OFFICIAL",
                "acquisition_mode": "LOCAL_FILE",
                "original_export_context": "MANUAL_DOWNLOAD",
                "local_export_timestamp": "2026-06-18T08:59:00+09:00",
                "manual_or_automated_origin": "MANUAL",
                "requires_reconciliation": False,
                "official_source_reference": "KRX_EXPORT_PORTAL",
                "notes": "Local offline fixture",
            },
            "strategy_track": "DOMESTIC_KR",
            "market_profile_id": "KRX",
            "symbol_count": 1,
            "record_count": 1,
            "date_range_start": "2026-06-18T09:00:00+09:00",
            "date_range_end": "2026-06-18T09:00:00+09:00",
            "timezone": "Asia/Seoul",
            "currency": "KRW",
            "adjustment_policy": {
                "policy_id": "adjustment-policy-1",
                "price_adjustment_mode": "UNADJUSTED",
                "split_adjustment_expected": False,
                "dividend_adjustment_expected": False,
                "corporate_action_backfill_expected": False,
                "adjusted_close_required": False,
                "mixed_adjustment_state_allowed": False,
                "report_only_if_uncertain": True,
            },
            "validation_report_id": "validation-1",
            "quality_report_id": "quality-1",
            "gap_report_id": "gap-1",
            "audit_record_ids": ["audit-1"],
        },
        "audit_records": [
            {
                "audit_record_id": "audit-1",
                "ingestion_batch_id": "batch-1",
                "source_descriptor_id": "source-desc-1",
                "created_at": "2026-06-18T09:01:00+09:00",
                "operator_context": "TEST",
                "local_file_path": "fixtures/historical/domestic_kr_ohlcv.csv",
                "local_file_hash": "sha256:fixture",
                "parser_version": "fixture-only",
                "validation_report_id": "validation-1",
                "quality_report_id": "quality-1",
                "gap_report_id": "gap-1",
            }
        ],
    }


def historical_calendar_snapshot_payload() -> dict:
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
            }
        ],
        "corporate_events": [
            {
                "symbol": "005930",
                "market": "KRX",
                "event_date": "2026-06-18",
                "event_type": "EARNINGS_BEFORE_OPEN",
                "earnings_before_open_flag": True,
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
    }


def bridge_fixture_payload() -> dict:
    return {
        "schema_version": "5.2-historical-replay-bridge-fixture",
        "fixture_id": "bridge-fixture-1",
        "created_at": "2026-06-18T10:00:00+09:00",
        "bridge_config": {
            "config_id": "bridge-config-1",
            "strategy_track": "DOMESTIC_KR",
        },
        "historical_market_data_snapshot": historical_market_snapshot_payload(),
        "historical_calendar_event_snapshot": historical_calendar_snapshot_payload(),
        "scanner_replay_hints": [],
    }


def build_fixture(payload: dict | None = None) -> HistoricalReplayBridgeFixture:
    return HistoricalReplayBridgeFixture.model_validate(payload or bridge_fixture_payload())


def _set_market_records(payload: dict, records: list[dict]) -> None:
    payload["historical_market_data_snapshot"]["records"] = records
    payload["historical_market_data_snapshot"]["quality_report"]["record_count"] = len(records)
    payload["historical_market_data_snapshot"]["quality_report"]["symbol_count"] = len({record["symbol"] for record in records})
    payload["historical_market_data_snapshot"]["quality_report"]["date_range_start"] = records[0]["timestamp"]
    payload["historical_market_data_snapshot"]["quality_report"]["date_range_end"] = records[-1]["timestamp"]
    payload["historical_market_data_snapshot"]["manifest"]["record_count"] = len(records)
    payload["historical_market_data_snapshot"]["manifest"]["symbol_count"] = len({record["symbol"] for record in records})
    payload["historical_market_data_snapshot"]["manifest"]["date_range_start"] = records[0]["timestamp"]
    payload["historical_market_data_snapshot"]["manifest"]["date_range_end"] = records[-1]["timestamp"]


def _set_calendar_sessions(payload: dict, session_records: list[dict]) -> None:
    payload["historical_calendar_event_snapshot"]["session_records"] = session_records
    payload["historical_calendar_event_snapshot"]["manifest"]["session_record_count"] = len(session_records)
    payload["historical_calendar_event_snapshot"]["manifest"]["date_range_start"] = f"{session_records[0]['date']}T00:00:00+09:00"
    payload["historical_calendar_event_snapshot"]["manifest"]["date_range_end"] = f"{session_records[-1]['date']}T23:59:59+09:00"


def _set_market_events(payload: dict, market_events: list[dict]) -> None:
    payload["historical_calendar_event_snapshot"]["market_events"] = market_events
    payload["historical_calendar_event_snapshot"]["manifest"]["market_event_count"] = len(market_events)


def _set_corporate_events(payload: dict, corporate_events: list[dict]) -> None:
    payload["historical_calendar_event_snapshot"]["corporate_events"] = corporate_events
    payload["historical_calendar_event_snapshot"]["manifest"]["corporate_event_count"] = len(corporate_events)


def multi_session_bridge_payload() -> dict:
    payload = bridge_fixture_payload()
    _set_market_records(
        payload,
        [
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
        ],
    )
    _set_calendar_sessions(
        payload,
        [
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
        ],
    )
    payload["historical_calendar_event_snapshot"]["market_events"] = []
    payload["historical_calendar_event_snapshot"]["manifest"]["market_event_count"] = 0
    payload["historical_calendar_event_snapshot"]["corporate_events"] = []
    payload["historical_calendar_event_snapshot"]["manifest"]["corporate_event_count"] = 0
    return payload


def scanner_replay_ready_outputs():
    payload = multi_session_bridge_payload()
    _set_market_events(
        payload,
        [
            {
                "event_id": "market-event-1",
                "market": "KRX",
                "event_date": "2026-06-22",
                "event_time": "2026-06-22T08:30:00+09:00",
                "timezone": "Asia/Seoul",
                "event_type": "CPI_RELEASE",
                "event_scope": "MARKET_WIDE",
                "affected_symbols": [],
                "affected_market": "KRX",
                "source_id": "LOCAL_MACRO_EVENTS",
                "event_batch_id": "calendar-batch-1",
            },
            {
                "event_id": "market-event-2",
                "market": "KRX",
                "event_date": "2026-06-24",
                "event_time": "2026-06-24T08:30:00+09:00",
                "timezone": "Asia/Seoul",
                "event_type": "PPI_RELEASE",
                "event_scope": "MARKET_WIDE",
                "affected_symbols": [],
                "affected_market": "KRX",
                "source_id": "LOCAL_MACRO_EVENTS",
                "event_batch_id": "calendar-batch-1",
            },
        ],
    )
    _set_corporate_events(
        payload,
        [
            {
                "symbol": "005930",
                "market": "KRX",
                "event_date": "2026-06-24",
                "event_type": "EARNINGS_BEFORE_OPEN",
                "earnings_before_open_flag": True,
                "source_id": "LOCAL_CORPORATE_EVENTS",
            }
        ],
    )
    fixture = build_fixture(payload)
    stream = build_historical_replay_event_stream(fixture)
    window_bundle = build_historical_replay_windows(stream, fixture, session_window_sizes=(1, 3))
    return stream, window_bundle


def test_build_historical_replay_event_stream_is_deterministic_and_preserves_lineage():
    fixture = build_fixture()

    first_stream = build_historical_replay_event_stream(fixture)
    second_stream = build_historical_replay_event_stream(fixture)

    assert first_stream.model_dump(mode="json") == second_stream.model_dump(mode="json")
    assert first_stream.bridge_input_id == "BRIDGE-FIXTURE-1"
    assert first_stream.historical_market_snapshot_id == "HISTORICAL-DOMESTIC-KR-1"
    assert first_stream.historical_calendar_snapshot_id == "CALENDAR-DOMESTIC-KR-1"
    assert first_stream.source_manifest_ids == ["MANIFEST-1", "CALENDAR-MANIFEST-1"]
    assert first_stream.source_audit_record_ids == ["AUDIT-1"]
    assert first_stream.provider_provenance_ids == ["PROVENANCE-1"]
    assert first_stream.source_type == "LOCAL_CSV"
    assert first_stream.source_file_path == "fixtures/historical/domestic_kr_ohlcv.csv"
    assert first_stream.source_currency == "KRW"
    assert first_stream.source_timezone == "Asia/Seoul"
    assert [event.replay_event_id for event in first_stream.events] == [
        "BRIDGE-FIXTURE-1-20260618T090000+0900-005930-KRX-KRX_MANUAL_EXPORT-BATCH-1-000001"
    ]
    assert [event.symbol for event in first_stream.events] == ["005930"]
    assert first_stream.events[0].source_record_id == "005930-KRX-20260618T090000+0900-KRX_MANUAL_EXPORT-BATCH-1"
    assert first_stream.events[0].source_source_id == "KRX_MANUAL_EXPORT"
    assert first_stream.events[0].currency == "KRW"
    assert first_stream.events[0].timezone == "Asia/Seoul"
    assert first_stream.read_only is True
    assert first_stream.non_executable is True
    assert first_stream.local_file_only is True
    assert first_stream.no_network is True
    assert first_stream.no_provider_api is True
    assert first_stream.no_order is True
    assert first_stream.no_llm_runtime is True
    assert first_stream.no_ml_training is True
    assert first_stream.events[0].read_only is True
    assert first_stream.events[0].non_executable is True
    assert first_stream.events[0].local_file_only is True
    assert first_stream.events[0].no_network is True
    assert first_stream.events[0].no_provider_api is True
    assert first_stream.events[0].no_order is True
    assert first_stream.events[0].no_llm_runtime is True
    assert first_stream.events[0].no_ml_training is True


def test_build_historical_replay_event_stream_sorts_existing_rows_and_preserves_timezone_awareness():
    payload = bridge_fixture_payload()
    records = payload["historical_market_data_snapshot"]["records"]
    records.append(
        {
            "symbol": "000660",
            "market": "KRX",
            "timestamp": "2026-06-17T09:00:00+09:00",
            "timezone": "Asia/Seoul",
            "open": 120000,
            "high": 121000,
            "low": 119500,
            "close": 120500,
            "volume": 2500,
            "currency": "KRW",
            "source_id": "KRX_MANUAL_EXPORT",
            "ingestion_batch_id": "batch-1",
        }
    )
    payload["historical_market_data_snapshot"]["quality_report"]["record_count"] = 2
    payload["historical_market_data_snapshot"]["quality_report"]["symbol_count"] = 2
    payload["historical_market_data_snapshot"]["quality_report"]["date_range_start"] = "2026-06-17T09:00:00+09:00"
    payload["historical_market_data_snapshot"]["manifest"]["record_count"] = 2
    payload["historical_market_data_snapshot"]["manifest"]["symbol_count"] = 2
    payload["historical_market_data_snapshot"]["manifest"]["date_range_start"] = "2026-06-17T09:00:00+09:00"

    fixture = build_fixture(payload)

    stream = build_historical_replay_event_stream(fixture)

    assert [event.symbol for event in stream.events] == ["000660", "005930"]
    assert [event.session_date.isoformat() for event in stream.events] == ["2026-06-17", "2026-06-18"]
    assert [
        event.replay_event_id for event in stream.events
    ] == [
        "BRIDGE-FIXTURE-1-20260617T090000+0900-000660-KRX-KRX_MANUAL_EXPORT-BATCH-1-000001",
        "BRIDGE-FIXTURE-1-20260618T090000+0900-005930-KRX-KRX_MANUAL_EXPORT-BATCH-1-000002",
    ]
    assert all(event.replay_timestamp.tzinfo is not None for event in stream.events)
    assert all(event.replay_timestamp.utcoffset() is not None for event in stream.events)


def test_build_historical_scanner_replay_input_generates_report_only_bundle_and_preserves_lineage():
    stream, window_bundle = scanner_replay_ready_outputs()

    scanner_input, scanner_report, gap_report = build_historical_scanner_replay_input(stream, window_bundle)

    assert scanner_input is not None
    assert scanner_input.report_only is True
    assert scanner_input.read_only is True
    assert scanner_input.non_executable is True
    assert scanner_input.local_file_only is True
    assert scanner_input.no_network is True
    assert scanner_input.no_provider_api is True
    assert scanner_input.no_order is True
    assert scanner_input.no_llm_runtime is True
    assert scanner_input.no_ml_training is True
    assert scanner_input.replay_event_stream_id == stream.stream_id
    assert scanner_input.source_window_bundle_id == window_bundle.window_bundle_id
    assert scanner_input.scanner_window_ids == [window.window_id for window in window_bundle.windows]
    assert scanner_input.historical_market_snapshot_id == stream.historical_market_snapshot_id
    assert scanner_input.historical_calendar_snapshot_id == stream.historical_calendar_snapshot_id
    assert scanner_input.source_manifest_ids == stream.source_manifest_ids
    assert scanner_input.source_audit_record_ids == stream.source_audit_record_ids
    assert scanner_input.provider_provenance_ids == stream.provider_provenance_ids
    assert scanner_input.event_source_ids == ["LOCAL_CORPORATE_EVENTS", "LOCAL_MACRO_EVENTS"]

    assert scanner_input.replay_context.replay_event_stream_id == stream.stream_id
    assert scanner_input.replay_context.source_window_bundle_id == window_bundle.window_bundle_id
    assert scanner_input.replay_context.scanner_window_ids == [window.window_id for window in window_bundle.windows]
    assert scanner_input.replay_context.symbol == "005930"
    assert scanner_input.replay_context.market == "KRX"
    assert scanner_input.replay_context.early_close is True
    assert scanner_input.replay_context.holiday_session_gap is True
    assert scanner_input.replay_context.attached_market_event_count == 2
    assert scanner_input.replay_context.attached_corporate_event_count == 1
    assert scanner_input.replay_context.attached_event_context_summary == "MARKET_EVENTS=2|CORPORATE_EVENTS=1"
    assert scanner_input.replay_context.event_source_ids == ["LOCAL_CORPORATE_EVENTS", "LOCAL_MACRO_EVENTS"]
    assert scanner_input.replay_context.lineage_complete is True

    assert len(scanner_input.candidate_seeds) == len(window_bundle.windows)
    assert all(seed.report_only is True for seed in scanner_input.candidate_seeds)
    assert all(seed.non_executable is True for seed in scanner_input.candidate_seeds)
    assert all(seed.no_order is True for seed in scanner_input.candidate_seeds)
    assert all(seed.is_order_candidate is False for seed in scanner_input.candidate_seeds)
    assert all(seed.replay_event_stream_id == stream.stream_id for seed in scanner_input.candidate_seeds)
    assert all(seed.source_window_id in scanner_input.scanner_window_ids for seed in scanner_input.candidate_seeds)
    assert all(seed.scanner_context_id == scanner_input.replay_context.context_id for seed in scanner_input.candidate_seeds)
    assert {"local_macro_events", "local_corporate_events"} == {
        source_id.lower()
        for seed in scanner_input.candidate_seeds
        for source_id in seed.event_source_ids
    }
    seed_dump = scanner_input.model_dump_json().lower()
    for blocked_word in ("buy", "sell", "entry", "exit", "order intent", "execution hint"):
        assert blocked_word not in seed_dump

    assert scanner_report.report_only is True
    assert scanner_report.candidate_seed_count == len(scanner_input.candidate_seeds)
    assert scanner_report.scanner_window_count == len(scanner_input.scanner_window_ids)

    assert gap_report.report_only is True
    assert "SCANNER_REPLAY_INPUT_GENERATED" in gap_report.gap_categories
    assert "SCANNER_REPLAY_REPORT_ONLY" in gap_report.gap_categories
    assert gap_report.blocking_gap_count == 0


@pytest.mark.parametrize(
    ("stream_mutator", "bundle_mutator", "expected_category", "expects_input"),
    [
        (lambda stream: None, lambda bundle: bundle, "SCANNER_REPLAY_MISSING_EVENT_STREAM", False),
        (
            lambda stream: stream,
            lambda bundle: bundle.model_copy(update={"windows": []}),
            "SCANNER_REPLAY_MISSING_WINDOW",
            False,
        ),
        (
            lambda stream: stream.model_copy(update={"source_manifest_ids": []}),
            lambda bundle: bundle,
            "SCANNER_REPLAY_SOURCE_LINEAGE_MISSING",
            True,
        ),
        (
            lambda stream: stream.model_copy(update={"strategy_track": "FOREIGN_US"}),
            lambda bundle: bundle,
            "SCANNER_REPLAY_UNSUPPORTED_TRACK",
            False,
        ),
        (
            lambda stream: stream.model_copy(update={"market_profile_id": "NASDAQ"}),
            lambda bundle: bundle,
            "SCANNER_REPLAY_UNSUPPORTED_MARKET",
            False,
        ),
        (
            lambda stream: stream.model_copy(update={"no_network": False}),
            lambda bundle: bundle,
            "SCANNER_REPLAY_SAFETY_MARKER_MISSING",
            False,
        ),
    ],
)
def test_build_historical_scanner_replay_input_reports_missing_and_unsupported_gaps(
    stream_mutator,
    bundle_mutator,
    expected_category,
    expects_input,
):
    stream, window_bundle = scanner_replay_ready_outputs()

    scanner_input, scanner_report, gap_report = build_historical_scanner_replay_input(
        stream_mutator(stream),
        bundle_mutator(window_bundle),
    )

    assert expected_category in gap_report.gap_categories
    assert scanner_report.report_only is True
    if expects_input:
        assert scanner_input is not None
    else:
        assert scanner_input is None
        assert gap_report.blocking_gap_count >= 1


@pytest.mark.parametrize(
    ("stream_mutator", "bundle_mutator", "expected_category"),
    [
        (
            lambda stream: stream.model_copy(update={"source_notes": "order candidate handoff"}),
            lambda bundle: bundle,
            "SCANNER_REPLAY_ORDER_FIELD_DETECTED",
        ),
        (
            lambda stream: stream.model_copy(update={"source_notes": "execution path handoff"}),
            lambda bundle: bundle,
            "SCANNER_REPLAY_EXECUTION_FIELD_DETECTED",
        ),
        (
            lambda stream: stream.model_copy(update={"source_notes": "buy setup only"}),
            lambda bundle: bundle,
            "SCANNER_REPLAY_BUY_SELL_WORDING_DETECTED",
        ),
        (
            lambda stream: stream.model_copy(update={"source_file_path": "https://example.com/replay.csv"}),
            lambda bundle: bundle,
            "SCANNER_REPLAY_REMOTE_SOURCE_NOT_ALLOWED",
        ),
        (
            lambda stream: stream.model_copy(update={"source_type": "provider_api"}),
            lambda bundle: bundle,
            "SCANNER_REPLAY_API_SOURCE_NOT_ALLOWED",
        ),
        (
            lambda stream: stream.model_copy(update={"source_notes": "network socket relay"}),
            lambda bundle: bundle,
            "SCANNER_REPLAY_NETWORK_SOURCE_NOT_ALLOWED",
        ),
        (
            lambda stream: stream.model_copy(update={"source_notes": "provider metadata relay"}),
            lambda bundle: bundle,
            "SCANNER_REPLAY_PROVIDER_SOURCE_NOT_ALLOWED",
        ),
        (
            lambda stream: stream.model_copy(update={"source_notes": "gemini llm runtime"}),
            lambda bundle: bundle,
            "SCANNER_REPLAY_LLM_METADATA_NOT_ALLOWED",
        ),
        (
            lambda stream: stream.model_copy(update={"source_notes": "ml training trigger"}),
            lambda bundle: bundle,
            "SCANNER_REPLAY_ML_TRAINING_TRIGGER_NOT_ALLOWED",
        ),
        (
            lambda stream: stream.model_copy(update={"source_notes": "crawler trigger"}),
            lambda bundle: bundle,
            "SCANNER_REPLAY_CRAWLER_TRIGGER_NOT_ALLOWED",
        ),
        (
            lambda stream: stream.model_copy(update={"source_notes": "live prod bridge"}),
            lambda bundle: bundle,
            "SCANNER_REPLAY_LIVE_PROD_NOT_ALLOWED",
        ),
        (
            lambda stream: stream.model_copy(update={"source_file_path": "fixtures/historical/replay.parquet"}),
            lambda bundle: bundle,
            "SCANNER_REPLAY_PARQUET_NOT_ALLOWED",
        ),
        (
            lambda stream: stream,
            lambda bundle: bundle.model_copy(
                update={
                    "windows": [
                        bundle.windows[0].model_copy(
                            update={"warnings": ["sell setup wording detected"]}
                        )
                    ]
                    + bundle.windows[1:]
                }
            ),
            "SCANNER_REPLAY_BUY_SELL_WORDING_DETECTED",
        ),
    ],
)
def test_build_historical_scanner_replay_input_rejects_unsafe_metadata(
    stream_mutator,
    bundle_mutator,
    expected_category,
):
    stream, window_bundle = scanner_replay_ready_outputs()

    scanner_input, _scanner_report, gap_report = build_historical_scanner_replay_input(
        stream_mutator(stream),
        bundle_mutator(window_bundle),
    )

    assert scanner_input is None
    assert expected_category in gap_report.gap_categories
    assert gap_report.blocking_gap_count >= 1


@pytest.mark.parametrize(
    ("mutator", "message"),
    [
        (
            lambda payload: payload["historical_market_data_snapshot"]["provider_provenance"].__setitem__(
                "notes", "https://example.com/domestic_kr_ohlcv.csv"
            ),
            "remote",
        ),
        (
            lambda payload: payload["historical_market_data_snapshot"]["provider_provenance"].__setitem__(
                "notes", "remote export"
            ),
            "remote",
        ),
        (
            lambda payload: payload["historical_market_data_snapshot"]["provider_provenance"].__setitem__(
                "notes", "local parquet export"
            ),
            "parquet",
        ),
        (
            lambda payload: payload["historical_market_data_snapshot"]["provider_provenance"].__setitem__(
                "notes", "broker order account live prod"
            ),
            "broker",
        ),
        (
            lambda payload: payload["historical_market_data_snapshot"]["provider_provenance"].__setitem__(
                "notes", "execution engine network handoff"
            ),
            "execution",
        ),
        (
            lambda payload: payload["historical_market_data_snapshot"]["provider_provenance"].__setitem__(
                "notes", "kiwoom ls provider path"
            ),
            "kiwoom",
        ),
        (
            lambda payload: payload["historical_market_data_snapshot"]["provider_provenance"].__setitem__(
                "notes", "cloud model runtime llm"
            ),
            "cloud",
        ),
        (
            lambda payload: payload["historical_market_data_snapshot"]["provider_provenance"].__setitem__(
                "notes", "ml training trigger"
            ),
            "training",
        ),
    ],
)
def test_validate_historical_replay_bridge_fixture_safety_rejects_unsafe_metadata(mutator, message):
    payload = bridge_fixture_payload()
    mutator(payload)
    fixture = build_fixture(payload)

    with pytest.raises(ValueError, match=message):
        validate_historical_replay_bridge_fixture_safety(fixture)


@pytest.mark.parametrize(
    ("blocked_key", "message"),
    [
        ("remote_export_flag", "remote"),
        ("order_intent", "order"),
        ("execution_path", "execution"),
        ("broker_account_id", "broker"),
        ("provider_api_url", "provider"),
        ("network_socket", "network"),
        ("live_mode", "live"),
        ("prod_flag", "prod"),
        ("kiwoom_path", "kiwoom"),
        ("ls_source", "ls"),
        ("gemini_prompt", "gemini"),
        ("cloud_model_runtime", "cloud"),
        ("ml_training_job", "training"),
        ("crawler_trigger", "crawler"),
        ("parquet_path", "parquet"),
    ],
)
def test_validate_historical_replay_metadata_safety_rejects_unsafe_field_names(blocked_key, message):
    payload = {"safe_section": {blocked_key: "local-only-placeholder"}}

    with pytest.raises(ValueError, match=message):
        validate_historical_replay_metadata_safety(payload, context="historical replay bridge fixture")


def test_build_historical_replay_event_stream_rejects_unsafe_fixture_metadata():
    payload = bridge_fixture_payload()
    payload["historical_market_data_snapshot"]["provider_provenance"]["notes"] = "Gemini crawler handoff"
    fixture = build_fixture(copy.deepcopy(payload))

    with pytest.raises(ValueError, match="crawler"):
        build_historical_replay_event_stream(fixture)


@pytest.mark.parametrize(
    ("mutator", "message"),
    [
        (
            lambda stream: stream.model_copy(update={"historical_market_snapshot_id": ""}),
            "missing market snapshot",
        ),
        (
            lambda stream: stream.model_copy(update={"source_manifest_ids": ["", "CALENDAR-MANIFEST-1"]}),
            "missing source manifest",
        ),
        (
            lambda stream: stream.model_copy(update={"strategy_track": "OVERSEAS_US"}),
            "unsupported strategy track",
        ),
        (
            lambda stream: stream.model_copy(update={"market_profile_id": "NASDAQ"}),
            "unsupported market",
        ),
        (
            lambda stream: stream.model_copy(
                update={"events": [stream.events[0].model_copy(update={"currency": "USD"})]}
            ),
            "currency mismatch",
        ),
        (
            lambda stream: stream.model_copy(
                update={"events": [stream.events[0].model_copy(update={"timezone": "UTC"})]}
            ),
            "timezone mismatch",
        ),
        (
            lambda stream: stream.model_copy(update={"source_file_path": "https://example.com/data.csv"}),
            "remote",
        ),
        (
            lambda stream: stream.model_copy(update={"source_type": "provider_api"}),
            "provider",
        ),
        (
            lambda stream: stream.model_copy(update={"source_file_path": "network://socket"}),
            "network",
        ),
        (
            lambda stream: stream.model_copy(update={"source_notes": "execution order handoff"}),
            "execution",
        ),
        (
            lambda stream: stream.model_copy(update={"source_notes": "cloud llm runtime"}),
            "cloud",
        ),
    ],
)
def test_validate_historical_replay_event_stream_fails_closed_for_stream_level_metadata(mutator, message):
    stream = build_historical_replay_event_stream(build_fixture())
    invalid_stream = mutator(stream)

    with pytest.raises(ValueError, match=message):
        validate_historical_replay_event_stream(invalid_stream)


@pytest.mark.parametrize(
    ("mutator", "message"),
    [
        (lambda fixture: fixture.model_copy(update={"historical_market_data_snapshot": None}), "missing market snapshot"),
        (
            lambda fixture: fixture.model_copy(
                update={"bridge_config": fixture.bridge_config.model_copy(update={"strategy_track": None})}
            ),
            "missing strategy track",
        ),
        (
            lambda fixture: fixture.model_copy(
                update={
                    "historical_market_data_snapshot": fixture.historical_market_data_snapshot.model_copy(
                        update={
                            "source_descriptor": fixture.historical_market_data_snapshot.source_descriptor.model_copy(
                                update={"market_profile_id": ""}
                            )
                        }
                    )
                }
            ),
            "missing market profile",
        ),
        (
            lambda fixture: fixture.model_copy(
                update={"bridge_config": fixture.bridge_config.model_copy(update={"strategy_track": "FOREIGN_US"})}
            ),
            "unsupported strategy track",
        ),
        (
            lambda fixture: fixture.model_copy(
                update={
                    "historical_market_data_snapshot": fixture.historical_market_data_snapshot.model_copy(
                        update={
                            "source_descriptor": fixture.historical_market_data_snapshot.source_descriptor.model_copy(
                                update={"market_profile_id": "NASDAQ"}
                            )
                        }
                    )
                }
            ),
            "unsupported market",
        ),
        (
            lambda fixture: fixture.model_copy(
                update={
                    "historical_market_data_snapshot": fixture.historical_market_data_snapshot.model_copy(
                        update={
                            "records": [
                                fixture.historical_market_data_snapshot.records[0].model_copy(update={"currency": "USD"})
                            ]
                        }
                    )
                }
            ),
            "currency mismatch",
        ),
        (
            lambda fixture: fixture.model_copy(
                update={
                    "historical_market_data_snapshot": fixture.historical_market_data_snapshot.model_copy(
                        update={
                            "records": [
                                fixture.historical_market_data_snapshot.records[0].model_copy(update={"timezone": "UTC"})
                            ]
                        }
                    )
                }
            ),
            "timezone mismatch",
        ),
        (
            lambda fixture: fixture.model_copy(
                update={
                    "historical_market_data_snapshot": fixture.historical_market_data_snapshot.model_copy(
                        update={"manifest": fixture.historical_market_data_snapshot.manifest.model_copy(update={"manifest_id": ""})}
                    )
                }
            ),
            "missing source manifest",
        ),
    ],
)
def test_build_historical_replay_event_stream_fails_closed_for_invalid_conversion_inputs(mutator, message):
    fixture = build_fixture()
    invalid_fixture = mutator(fixture)

    with pytest.raises(ValueError, match=message):
        build_historical_replay_event_stream(invalid_fixture)


def test_build_historical_replay_event_stream_fails_closed_for_duplicate_replay_events():
    payload = bridge_fixture_payload()
    duplicate_record = copy.deepcopy(payload["historical_market_data_snapshot"]["records"][0])
    payload["historical_market_data_snapshot"]["records"].append(duplicate_record)
    payload["historical_market_data_snapshot"]["quality_report"]["record_count"] = 2
    payload["historical_market_data_snapshot"]["manifest"]["record_count"] = 2
    fixture = build_fixture(payload)

    with pytest.raises(ValueError, match="duplicate replay event"):
        build_historical_replay_event_stream(fixture)


def test_validate_historical_replay_event_stream_fails_closed_for_out_of_order_replay_events():
    payload = bridge_fixture_payload()
    payload["historical_market_data_snapshot"]["records"].append(
        {
            "symbol": "000660",
            "market": "KRX",
            "timestamp": "2026-06-17T09:00:00+09:00",
            "timezone": "Asia/Seoul",
            "open": 120000,
            "high": 121000,
            "low": 119500,
            "close": 120500,
            "volume": 2500,
            "currency": "KRW",
            "source_id": "KRX_MANUAL_EXPORT",
            "ingestion_batch_id": "batch-1",
        }
    )
    payload["historical_market_data_snapshot"]["quality_report"]["record_count"] = 2
    payload["historical_market_data_snapshot"]["quality_report"]["symbol_count"] = 2
    payload["historical_market_data_snapshot"]["quality_report"]["date_range_start"] = "2026-06-17T09:00:00+09:00"
    payload["historical_market_data_snapshot"]["manifest"]["record_count"] = 2
    payload["historical_market_data_snapshot"]["manifest"]["symbol_count"] = 2
    payload["historical_market_data_snapshot"]["manifest"]["date_range_start"] = "2026-06-17T09:00:00+09:00"
    fixture = build_fixture(payload)
    stream = build_historical_replay_event_stream(fixture)
    invalid_stream = stream.model_copy(update={"events": [stream.events[1], stream.events[0]]})

    with pytest.raises(ValueError, match="out-of-order replay event"):
        validate_historical_replay_event_stream(invalid_stream)


def test_validate_historical_replay_event_stream_fails_closed_for_duplicate_source_record_ids():
    payload = bridge_fixture_payload()
    payload["historical_market_data_snapshot"]["records"].append(
        {
            "symbol": "000660",
            "market": "KRX",
            "timestamp": "2026-06-17T09:00:00+09:00",
            "timezone": "Asia/Seoul",
            "open": 120000,
            "high": 121000,
            "low": 119500,
            "close": 120500,
            "volume": 2500,
            "currency": "KRW",
            "source_id": "KRX_MANUAL_EXPORT",
            "ingestion_batch_id": "batch-1",
        }
    )
    payload["historical_market_data_snapshot"]["quality_report"]["record_count"] = 2
    payload["historical_market_data_snapshot"]["quality_report"]["symbol_count"] = 2
    payload["historical_market_data_snapshot"]["quality_report"]["date_range_start"] = "2026-06-17T09:00:00+09:00"
    payload["historical_market_data_snapshot"]["manifest"]["record_count"] = 2
    payload["historical_market_data_snapshot"]["manifest"]["symbol_count"] = 2
    payload["historical_market_data_snapshot"]["manifest"]["date_range_start"] = "2026-06-17T09:00:00+09:00"
    stream = build_historical_replay_event_stream(build_fixture(payload))
    duplicate_stream = stream.model_copy(
        update={
            "events": [
                stream.events[0],
                stream.events[1].model_copy(update={"source_record_id": stream.events[0].source_record_id}),
            ]
        }
    )

    with pytest.raises(ValueError, match="duplicate replay event"):
        validate_historical_replay_event_stream(duplicate_stream)


def test_build_historical_replay_windows_uses_trading_sessions_and_preserves_lineage_and_safety():
    payload = multi_session_bridge_payload()
    fixture = build_fixture(payload)
    stream = build_historical_replay_event_stream(fixture)

    bundle = build_historical_replay_windows(stream, fixture, session_window_sizes=(1, 3))

    assert bundle.degraded_report_only is False
    assert bundle.requested_window_sizes == [1, 3]
    assert bundle.replay_event_stream_id == stream.stream_id
    assert bundle.historical_market_snapshot_id == stream.historical_market_snapshot_id
    assert bundle.historical_calendar_snapshot_id == "CALENDAR-DOMESTIC-KR-1"
    assert bundle.source_manifest_ids == ["MANIFEST-1", "CALENDAR-MANIFEST-1"]
    assert bundle.source_audit_record_ids == ["AUDIT-1"]
    assert bundle.provider_provenance_ids == ["PROVENANCE-1"]
    assert bundle.read_only is True
    assert bundle.non_executable is True
    assert bundle.local_file_only is True
    assert bundle.no_network is True
    assert bundle.no_provider_api is True
    assert bundle.no_order is True
    assert bundle.no_llm_runtime is True
    assert bundle.no_ml_training is True

    assert [(window.session_date.isoformat(), window.window_size_sessions) for window in bundle.windows] == [
        ("2026-06-19", 1),
        ("2026-06-22", 1),
        ("2026-06-24", 1),
        ("2026-06-24", 3),
    ]
    assert bundle.windows[0].event_ids == [
        "BRIDGE-FIXTURE-1-20260619T090000+0900-005930-KRX-KRX_MANUAL_EXPORT-BATCH-1-000001"
    ]
    assert [day.isoformat() for day in bundle.windows[1].window_session_dates] == ["2026-06-22"]
    assert bundle.windows[1].early_close is True
    assert [gap.value for gap in bundle.windows[1].gap_categories] == ["REPLAY_EARLY_CLOSE_SESSION_FLAGGED"]
    assert [day.isoformat() for day in bundle.windows[2].window_session_dates] == ["2026-06-24"]
    assert [day.isoformat() for day in bundle.windows[3].window_session_dates] == [
        "2026-06-19",
        "2026-06-22",
        "2026-06-24",
    ]
    assert bundle.windows[3].event_ids == [
        "BRIDGE-FIXTURE-1-20260619T090000+0900-005930-KRX-KRX_MANUAL_EXPORT-BATCH-1-000001",
        "BRIDGE-FIXTURE-1-20260622T090000+0900-005930-KRX-KRX_MANUAL_EXPORT-BATCH-1-000002",
        "BRIDGE-FIXTURE-1-20260624T090000+0900-005930-KRX-KRX_MANUAL_EXPORT-BATCH-1-000003",
    ]
    assert bundle.windows[3].replay_event_stream_id == stream.stream_id
    assert bundle.windows[3].source_manifest_ids == ["MANIFEST-1", "CALENDAR-MANIFEST-1"]
    assert bundle.windows[3].provider_provenance_ids == ["PROVENANCE-1"]
    assert bundle.windows[3].read_only is True
    assert bundle.windows[3].local_file_only is True
    assert bundle.windows[3].no_network is True
    assert bundle.windows[3].no_provider_api is True
    assert bundle.windows[3].no_order is True
    assert bundle.windows[3].no_llm_runtime is True
    assert bundle.windows[3].no_ml_training is True

    gap_categories = {gap.gap_category.value for gap in bundle.gap_report.gaps}
    assert "REPLAY_HOLIDAY_SESSION_RECOGNIZED" in gap_categories
    assert "REPLAY_EARLY_CLOSE_SESSION_FLAGGED" in gap_categories
    assert "REPLAY_MISSING_TRADING_SESSION" not in gap_categories
    assert bundle.gap_report.blocking_gap_count == 0
    assert bundle.gap_report.report_only_gap_count == 2


def test_build_historical_replay_windows_fails_closed_without_calendar_by_default():
    payload = multi_session_bridge_payload()
    payload["historical_calendar_event_snapshot"] = None
    fixture = build_fixture(payload)
    stream = build_historical_replay_event_stream(fixture)

    with pytest.raises(ValueError, match="missing trading calendar"):
        build_historical_replay_windows(stream, fixture, session_window_sizes=(1, 3))


def test_build_historical_replay_windows_supports_explicit_report_only_degraded_mode_for_missing_calendar():
    payload = multi_session_bridge_payload()
    payload["bridge_config"]["allow_report_only_degraded_calendar"] = True
    payload["historical_calendar_event_snapshot"] = None
    fixture = build_fixture(payload)
    stream = build_historical_replay_event_stream(fixture)

    bundle = build_historical_replay_windows(stream, fixture, session_window_sizes=(1, 3))

    assert bundle.degraded_report_only is True
    assert bundle.windows == []
    assert [gap.gap_category.value for gap in bundle.gap_report.gaps] == [
        "REPLAY_MISSING_TRADING_CALENDAR",
        "REPLAY_WINDOW_DEGRADED_REPORT_ONLY",
    ]


def test_build_historical_replay_windows_fails_closed_for_missing_expected_trading_session_inside_calendar_span():
    payload = multi_session_bridge_payload()
    _set_calendar_sessions(
        payload,
        [
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
                "date": "2026-06-23",
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
        ],
    )
    fixture = build_fixture(payload)
    stream = build_historical_replay_event_stream(fixture)

    with pytest.raises(
        ValueError,
        match=r"blocking replay window gaps detected: missing trading session for open calendar day 2026-06-23",
    ):
        build_historical_replay_windows(stream, fixture, session_window_sizes=(3,))


def test_build_historical_replay_windows_fails_closed_for_leading_and_trailing_missing_trading_sessions():
    payload = multi_session_bridge_payload()
    _set_calendar_sessions(
        payload,
        [
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
            },
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
            {
                "market": "KRX",
                "date": "2026-06-25",
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
        ],
    )
    fixture = build_fixture(payload)
    stream = build_historical_replay_event_stream(fixture)

    with pytest.raises(
        ValueError,
        match=(
            r"blocking replay window gaps detected: "
            r"missing trading session for open calendar day 2026-06-18, "
            r"missing trading session for open calendar day 2026-06-25"
        ),
    ):
        build_historical_replay_windows(stream, fixture, session_window_sizes=(1, 3))


def test_build_historical_replay_windows_fails_closed_for_event_on_holiday_or_non_trading_session_date():
    payload = multi_session_bridge_payload()
    _set_market_records(
        payload,
        [
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
                "timestamp": "2026-06-23T09:00:00+09:00",
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
        ],
    )
    fixture = build_fixture(payload)
    stream = build_historical_replay_event_stream(fixture)

    with pytest.raises(
        ValueError,
        match=r"blocking replay window gaps detected: event falls on non-trading calendar session 2026-06-23",
    ):
        build_historical_replay_windows(stream, fixture, session_window_sizes=(1, 3))


def test_build_historical_replay_windows_fails_closed_for_event_date_absent_from_session_records():
    payload = multi_session_bridge_payload()
    _set_market_records(
        payload,
        [
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
                "timestamp": "2026-06-20T09:00:00+09:00",
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
        ],
    )
    fixture = build_fixture(payload)
    stream = build_historical_replay_event_stream(fixture)

    with pytest.raises(
        ValueError,
        match=r"blocking replay window gaps detected: event session date 2026-06-20 is absent from trading calendar",
    ):
        build_historical_replay_windows(stream, fixture, session_window_sizes=(1, 3))


@pytest.mark.parametrize(
    ("fixture_mutator", "message"),
    [
        (
            lambda fixture: fixture.model_copy(
                update={
                    "historical_calendar_event_snapshot": fixture.historical_calendar_event_snapshot.model_copy(
                        update={"manifest": fixture.historical_calendar_event_snapshot.manifest.model_copy(update={"timezone": "UTC"})}
                    )
                }
            ),
            "calendar timezone mismatch",
        ),
        (
            lambda fixture: fixture.model_copy(
                update={
                    "historical_calendar_event_snapshot": fixture.historical_calendar_event_snapshot.model_copy(
                        update={
                            "session_records": [
                                fixture.historical_calendar_event_snapshot.session_records[0].model_copy(update={"market": "NASDAQ"}),
                                *fixture.historical_calendar_event_snapshot.session_records[1:],
                            ]
                        }
                    )
                }
            ),
            "market profile mismatch",
        ),
    ],
)
def test_build_historical_replay_windows_fails_closed_for_calendar_alignment_mismatches(fixture_mutator, message):
    fixture = build_fixture(multi_session_bridge_payload())
    stream = build_historical_replay_event_stream(fixture)
    invalid_fixture = fixture_mutator(fixture)

    with pytest.raises(ValueError, match=message):
        build_historical_replay_windows(stream, invalid_fixture, session_window_sizes=(1, 3))


def test_build_historical_replay_windows_reports_out_of_order_calendar_sessions_but_returns_sorted_windows():
    payload = multi_session_bridge_payload()
    payload["historical_calendar_event_snapshot"]["session_records"] = [
        payload["historical_calendar_event_snapshot"]["session_records"][1],
        payload["historical_calendar_event_snapshot"]["session_records"][0],
        payload["historical_calendar_event_snapshot"]["session_records"][3],
        payload["historical_calendar_event_snapshot"]["session_records"][2],
    ]
    fixture = build_fixture(payload)
    stream = build_historical_replay_event_stream(fixture)

    bundle = build_historical_replay_windows(stream, fixture, session_window_sizes=(1,))

    assert [window.session_date.isoformat() for window in bundle.windows] == ["2026-06-19", "2026-06-22", "2026-06-24"]
    assert [gap.gap_category.value for gap in bundle.gap_report.gaps] == [
        "REPLAY_WINDOW_OUT_OF_ORDER",
        "REPLAY_EARLY_CLOSE_SESSION_FLAGGED",
        "REPLAY_HOLIDAY_SESSION_RECOGNIZED",
    ]


def test_build_historical_replay_windows_attaches_report_only_event_context_and_preserves_lineage():
    payload = multi_session_bridge_payload()
    _set_market_events(
        payload,
        [
            {
                "event_id": "macro-1",
                "market": "KRX",
                "event_date": "2026-06-19",
                "event_time": "2026-06-19T08:30:00+09:00",
                "timezone": "Asia/Seoul",
                "event_type": "CPI_RELEASE",
                "event_scope": "MARKET_WIDE",
                "affected_symbols": [],
                "affected_market": "KRX",
                "source_id": "LOCAL_MACRO_EVENTS",
                "event_batch_id": "calendar-batch-1",
            },
            {
                "event_id": "derivatives-1",
                "market": "KRX",
                "event_date": "2026-06-24",
                "event_time": "2026-06-24T15:30:00+09:00",
                "timezone": "Asia/Seoul",
                "event_type": "OPTIONS_EXPIRATION",
                "event_scope": "MARKET_WIDE",
                "affected_symbols": [],
                "affected_market": "KRX",
                "source_id": "LOCAL_DERIVATIVES_EVENTS",
                "event_batch_id": "calendar-batch-1",
            },
        ],
    )
    _set_corporate_events(
        payload,
        [
            {
                "symbol": "005930",
                "market": "KRX",
                "event_date": "2026-06-19",
                "event_type": "EARNINGS_BEFORE_OPEN",
                "earnings_before_open_flag": True,
                "source_id": "LOCAL_CORPORATE_EVENTS",
            },
            {
                "symbol": "005930",
                "market": "KRX",
                "event_date": "2026-06-22",
                "event_type": "EARNINGS_AFTER_CLOSE",
                "earnings_after_close_flag": True,
                "source_id": "LOCAL_CORPORATE_EVENTS",
            },
            {
                "symbol": "005930",
                "market": "KRX",
                "event_date": "2026-06-24",
                "event_type": "DIVIDEND_EX_DATE",
                "dividend_ex_date_flag": True,
                "source_id": "LOCAL_CORPORATE_EVENTS",
            },
            {
                "symbol": "005930",
                "market": "KRX",
                "event_date": "2026-06-24",
                "event_type": "SPLIT_EFFECTIVE_DATE",
                "split_effective_date_flag": True,
                "source_id": "LOCAL_CORPORATE_EVENTS",
            },
            {
                "symbol": "005930",
                "market": "KRX",
                "event_date": "2026-06-24",
                "event_type": "CORPORATE_ACTION",
                "corporate_action_adjustment_flag": True,
                "source_id": "LOCAL_CORPORATE_EVENTS",
            },
        ],
    )
    fixture = build_fixture(payload)
    stream = build_historical_replay_event_stream(fixture)

    bundle = build_historical_replay_windows(stream, fixture, session_window_sizes=(1, 3))

    first_window = bundle.windows[0]
    assert [context.event_type for context in first_window.market_event_contexts] == ["CPI_RELEASE"]
    assert [context.event_type for context in first_window.corporate_event_contexts] == ["EARNINGS_BEFORE_OPEN"]
    assert first_window.market_event_contexts[0].historical_calendar_snapshot_id == "CALENDAR-DOMESTIC-KR-1"
    assert first_window.market_event_contexts[0].historical_market_snapshot_id == "HISTORICAL-DOMESTIC-KR-1"
    assert first_window.market_event_contexts[0].replay_event_stream_id == stream.stream_id
    assert first_window.market_event_contexts[0].replay_window_id == first_window.window_id
    assert first_window.market_event_contexts[0].source_manifest_ids == ["MANIFEST-1", "CALENDAR-MANIFEST-1"]
    assert first_window.market_event_contexts[0].event_source_id == "LOCAL_MACRO_EVENTS"
    assert first_window.market_event_contexts[0].event_batch_id == "CALENDAR-BATCH-1"
    assert first_window.market_event_contexts[0].known_time_complete is False
    assert first_window.market_event_contexts[0].report_only is True
    assert first_window.market_event_contexts[0].read_only is True
    assert first_window.market_event_contexts[0].non_executable is True
    assert first_window.market_event_contexts[0].local_file_only is True
    assert first_window.market_event_contexts[0].no_network is True
    assert first_window.market_event_contexts[0].no_provider_api is True
    assert first_window.market_event_contexts[0].no_order is True
    assert first_window.market_event_contexts[0].no_llm_runtime is True
    assert first_window.market_event_contexts[0].no_ml_training is True

    second_window = bundle.windows[1]
    assert [context.event_type for context in second_window.market_event_contexts] == []
    assert second_window.corporate_event_contexts == []

    last_window = bundle.windows[-1]
    assert [context.event_type for context in last_window.market_event_contexts] == [
        "CPI_RELEASE",
        "OPTIONS_EXPIRATION",
    ]
    assert [context.event_type for context in last_window.corporate_event_contexts] == [
        "EARNINGS_BEFORE_OPEN",
        "EARNINGS_AFTER_CLOSE",
        "DIVIDEND_EX_DATE",
        "SPLIT_EFFECTIVE_DATE",
        "CORPORATE_ACTION",
    ]
    assert bundle.event_context_report.attached_market_event_count == 2
    assert bundle.event_context_report.attached_corporate_event_count == 5
    assert bundle.event_context_report.event_source_ids == [
        "LOCAL_CORPORATE_EVENTS",
        "LOCAL_DERIVATIVES_EVENTS",
        "LOCAL_MACRO_EVENTS",
    ]
    assert bundle.event_context_report.event_batch_ids == ["CALENDAR-BATCH-1"]
    assert bundle.event_context_report.read_only is True
    assert bundle.event_context_report.non_executable is True
    assert bundle.event_context_report.local_file_only is True
    assert bundle.event_context_report.no_network is True
    assert bundle.event_context_report.no_provider_api is True
    assert bundle.event_context_report.no_order is True
    assert bundle.event_context_report.no_llm_runtime is True
    assert bundle.event_context_report.no_ml_training is True
    gap_categories = {gap.gap_category.value for gap in bundle.gap_report.gaps}
    assert "REPLAY_EVENT_KNOWN_TIME_INCOMPLETE" in gap_categories


def test_build_historical_replay_windows_reports_missing_market_known_time_without_silent_attachment():
    payload = multi_session_bridge_payload()
    _set_market_events(
        payload,
        [
            {
                "event_id": "macro-1",
                "market": "KRX",
                "event_date": "2026-06-24",
                "event_time": None,
                "timezone": "Asia/Seoul",
                "event_type": "CPI_RELEASE",
                "event_scope": "MARKET_WIDE",
                "affected_symbols": [],
                "affected_market": "KRX",
                "source_id": "LOCAL_MACRO_EVENTS",
                "event_batch_id": "calendar-batch-1",
            }
        ],
    )
    _set_corporate_events(payload, [])
    fixture = build_fixture(payload)
    stream = build_historical_replay_event_stream(fixture)

    bundle = build_historical_replay_windows(stream, fixture, session_window_sizes=(1,))

    target_window = next(window for window in bundle.windows if window.session_date.isoformat() == "2026-06-24")
    assert [context.event_type for context in target_window.market_event_contexts] == ["CPI_RELEASE"]
    assert target_window.market_event_contexts[0].known_time_complete is False
    assert target_window.market_event_contexts[0].known_at is None
    gap_messages = [gap.message for gap in bundle.gap_report.gaps]
    assert "known_at metadata is incomplete for market event MACRO-1" in gap_messages


def test_build_historical_replay_windows_attaches_market_events_only_to_matching_window_market_and_symbol():
    payload = multi_session_bridge_payload()
    _set_market_records(
        payload,
            [
                payload["historical_market_data_snapshot"]["records"][0],
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
                    "symbol": "000660",
                    "market": "KRX",
                    "timestamp": "2026-06-22T09:00:00+09:00",
                    "timezone": "Asia/Seoul",
                    "open": 120000,
                "high": 121000,
                "low": 119500,
                "close": 120500,
                "volume": 2500,
                "currency": "KRW",
                "source_id": "KRX_MANUAL_EXPORT",
                "ingestion_batch_id": "batch-1",
            },
            payload["historical_market_data_snapshot"]["records"][2],
        ],
    )
    _set_market_events(
        payload,
        [
            {
                "event_id": "macro-1",
                "market": "KRX",
                "event_date": "2026-06-22",
                "event_time": "2026-06-22T08:30:00+09:00",
                "timezone": "Asia/Seoul",
                "event_type": "FOMC_DECISION",
                "event_scope": "MARKET_WIDE",
                "affected_symbols": [],
                "affected_market": "KRX",
                "source_id": "LOCAL_MACRO_EVENTS",
                "event_batch_id": "calendar-batch-1",
            }
        ],
    )
    _set_corporate_events(
        payload,
            [
                {
                    "symbol": "005930",
                    "market": "KRX",
                    "event_date": "2026-06-22",
                    "event_type": "EARNINGS_AFTER_CLOSE",
                    "earnings_after_close_flag": True,
                    "source_id": "LOCAL_CORPORATE_EVENTS",
                },
                {
                    "symbol": "035420",
                    "market": "KRX",
                    "event_date": "2026-06-22",
                    "event_type": "EARNINGS_AFTER_CLOSE",
                    "earnings_after_close_flag": True,
                    "source_id": "LOCAL_CORPORATE_EVENTS",
                }
            ],
        )
    fixture = build_fixture(payload)
    stream = build_historical_replay_event_stream(fixture)

    bundle = build_historical_replay_windows(stream, fixture, session_window_sizes=(1,))

    target_window = next(window for window in bundle.windows if window.session_date.isoformat() == "2026-06-22")
    assert [context.event_type for context in target_window.market_event_contexts] == ["FOMC_DECISION"]
    assert target_window.corporate_event_contexts == []

    next_session_window = next(window for window in bundle.windows if window.session_date.isoformat() == "2026-06-24")
    assert [context.symbol for context in next_session_window.corporate_event_contexts] == ["005930"]


def test_build_historical_replay_windows_enforces_symbol_scoped_market_event_attachment():
    payload = multi_session_bridge_payload()
    _set_market_records(
        payload,
        [
            payload["historical_market_data_snapshot"]["records"][0],
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
                "symbol": "000660",
                "market": "KRX",
                "timestamp": "2026-06-22T09:00:00+09:00",
                "timezone": "Asia/Seoul",
                "open": 120000,
                "high": 121000,
                "low": 119500,
                "close": 120500,
                "volume": 2500,
                "currency": "KRW",
                "source_id": "KRX_MANUAL_EXPORT",
                "ingestion_batch_id": "batch-1",
            },
            {
                "symbol": "000660",
                "market": "KRX",
                "timestamp": "2026-06-24T09:00:00+09:00",
                "timezone": "Asia/Seoul",
                "open": 121000,
                "high": 122000,
                "low": 120500,
                "close": 121500,
                "volume": 2600,
                "currency": "KRW",
                "source_id": "KRX_MANUAL_EXPORT",
                "ingestion_batch_id": "batch-1",
            },
        ],
    )
    _set_market_events(
        payload,
        [
            {
                "event_id": "macro-symbol-1",
                "market": "KRX",
                "event_date": "2026-06-22",
                "event_time": "2026-06-22T08:30:00+09:00",
                "timezone": "Asia/Seoul",
                "event_type": "FOMC_DECISION",
                "event_scope": "SYMBOL_SCOPED",
                "affected_symbols": ["005930"],
                "affected_market": "KRX",
                "source_id": "LOCAL_MACRO_EVENTS",
                "event_batch_id": "calendar-batch-1",
            }
        ],
    )
    _set_corporate_events(payload, [])
    fixture = build_fixture(payload)
    stream = build_historical_replay_event_stream(fixture)

    bundle = build_historical_replay_windows(stream, fixture, session_window_sizes=(1, 3))

    mixed_symbol_window = next(window for window in bundle.windows if window.session_date.isoformat() == "2026-06-22")
    assert [context.event_type for context in mixed_symbol_window.market_event_contexts] == ["FOMC_DECISION"]
    assert [context.symbol for context in mixed_symbol_window.market_event_contexts] == ["005930"]

    non_matching_window = next(
        window
        for window in bundle.windows
        if window.session_date.isoformat() == "2026-06-24" and window.window_size_sessions == 1
    )
    assert non_matching_window.market_event_contexts == []


@pytest.mark.parametrize(
    ("market_events", "corporate_events", "expected_gap"),
    [
        (
            [
                {
                    "event_id": "unsupported-1",
                    "market": "KRX",
                    "event_date": "2026-06-19",
                    "event_time": "2026-06-19T08:30:00+09:00",
                    "timezone": "Asia/Seoul",
                    "event_type": "MARKET_HOLIDAY",
                    "event_scope": "MARKET_WIDE",
                    "affected_symbols": [],
                    "affected_market": "KRX",
                    "source_id": "LOCAL_MACRO_EVENTS",
                    "event_batch_id": "calendar-batch-1",
                }
            ],
            [],
            "REPLAY_UNSUPPORTED_EVENT_CONTEXT",
        ),
        (
            [
                {
                    "event_id": "macro-1",
                    "market": "KRX",
                    "event_date": "2026-06-19",
                    "event_time": "2026-06-19T08:30:00+09:00",
                    "timezone": "UTC",
                    "event_type": "CPI_RELEASE",
                    "event_scope": "MARKET_WIDE",
                    "affected_symbols": [],
                    "affected_market": "KRX",
                    "source_id": "LOCAL_MACRO_EVENTS",
                    "event_batch_id": "calendar-batch-1",
                }
            ],
            [],
            "REPLAY_CALENDAR_TIMEZONE_MISMATCH",
        ),
        (
            [
                {
                    "event_id": "macro-1",
                    "market": "NASDAQ",
                    "event_date": "2026-06-19",
                    "event_time": "2026-06-19T08:30:00+09:00",
                    "timezone": "Asia/Seoul",
                    "event_type": "CPI_RELEASE",
                    "event_scope": "MARKET_WIDE",
                    "affected_symbols": [],
                    "affected_market": "NASDAQ",
                    "source_id": "LOCAL_MACRO_EVENTS",
                    "event_batch_id": "calendar-batch-1",
                }
            ],
            [],
            "REPLAY_MARKET_PROFILE_MISMATCH",
        ),
    ],
)
def test_build_historical_replay_windows_reports_event_context_gaps(market_events, corporate_events, expected_gap):
    payload = multi_session_bridge_payload()
    _set_market_events(payload, market_events)
    _set_corporate_events(payload, corporate_events)
    fixture = build_fixture(payload)
    stream = build_historical_replay_event_stream(fixture)

    bundle = build_historical_replay_windows(stream, fixture, session_window_sizes=(1,))

    gap_categories = {gap.gap_category.value for gap in bundle.gap_report.gaps}
    assert expected_gap in gap_categories
    assert all(window.market_event_contexts == [] for window in bundle.windows)
    assert all(window.corporate_event_contexts == [] for window in bundle.windows)


def test_build_historical_replay_windows_fails_closed_for_duplicate_market_event_ids():
    payload = multi_session_bridge_payload()
    duplicate_event = {
        "event_id": "macro-1",
        "market": "KRX",
        "event_date": "2026-06-19",
        "event_time": "2026-06-19T08:30:00+09:00",
        "timezone": "Asia/Seoul",
        "event_type": "CPI_RELEASE",
        "event_scope": "MARKET_WIDE",
        "affected_symbols": [],
        "affected_market": "KRX",
        "source_id": "LOCAL_MACRO_EVENTS",
        "event_batch_id": "calendar-batch-1",
    }
    _set_market_events(payload, [duplicate_event, copy.deepcopy(duplicate_event)])
    fixture = build_fixture(payload)
    stream = build_historical_replay_event_stream(fixture)

    with pytest.raises(ValueError, match="duplicate replay event context"):
        build_historical_replay_windows(stream, fixture, session_window_sizes=(1,))


def test_build_historical_replay_windows_fails_closed_for_out_of_order_market_event_records():
    payload = multi_session_bridge_payload()
    _set_market_events(
        payload,
        [
            {
                "event_id": "macro-2",
                "market": "KRX",
                "event_date": "2026-06-24",
                "event_time": "2026-06-24T08:30:00+09:00",
                "timezone": "Asia/Seoul",
                "event_type": "PPI_RELEASE",
                "event_scope": "MARKET_WIDE",
                "affected_symbols": [],
                "affected_market": "KRX",
                "source_id": "LOCAL_MACRO_EVENTS",
                "event_batch_id": "calendar-batch-1",
            },
            {
                "event_id": "macro-1",
                "market": "KRX",
                "event_date": "2026-06-19",
                "event_time": "2026-06-19T08:30:00+09:00",
                "timezone": "Asia/Seoul",
                "event_type": "CPI_RELEASE",
                "event_scope": "MARKET_WIDE",
                "affected_symbols": [],
                "affected_market": "KRX",
                "source_id": "LOCAL_MACRO_EVENTS",
                "event_batch_id": "calendar-batch-1",
            },
        ],
    )
    fixture = build_fixture(payload)
    stream = build_historical_replay_event_stream(fixture)

    with pytest.raises(ValueError, match="out-of-order replay event context"):
        build_historical_replay_windows(stream, fixture, session_window_sizes=(1,))


def test_build_historical_replay_windows_blocks_future_actual_value_leakage_and_rejects_unsafe_event_keys():
    payload = multi_session_bridge_payload()
    payload["historical_calendar_event_snapshot"]["market_events"] = [
        {
            "event_id": "macro-1",
            "market": "KRX",
            "event_date": "2026-06-19",
            "event_time": "2026-06-19T08:30:00+09:00",
            "timezone": "Asia/Seoul",
            "event_type": "CPI_RELEASE",
            "event_scope": "MARKET_WIDE",
            "affected_symbols": [],
            "affected_market": "KRX",
            "source_id": "LOCAL_MACRO_EVENTS",
            "event_batch_id": "calendar-batch-1",
            "actual_value": "3.1",
        }
    ]
    payload["historical_calendar_event_snapshot"]["manifest"]["market_event_count"] = 1

    with pytest.raises(ValueError, match="actual_value"):
        build_fixture(payload)
