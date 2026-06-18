import json

import pytest

from stock_risk_mcp.historical_calendar_models import HistoricalCalendarEventSnapshot
from stock_risk_mcp.historical_data_models import HistoricalMarketDataSnapshot


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


def historical_market_snapshot_payload():
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


def _minimal_event_stream_payload(**overrides):
    payload = {
        "stream_id": "stream-1",
        "bridge_input_id": "bridge-input-1",
        "strategy_track": "DOMESTIC_KR",
        "market_profile_id": "KRX",
        "source_type": "local_csv",
        "source_file_path": "fixtures/historical/domestic_kr_ohlcv.csv",
        "source_currency": "KRW",
        "source_timezone": "Asia/Seoul",
        "historical_market_snapshot_id": "historical-domestic-kr-1",
        "historical_calendar_snapshot_id": "calendar-domestic-kr-1",
        "source_manifest_ids": ["manifest-1"],
        "source_audit_record_ids": ["audit-1"],
        "provider_provenance_ids": ["provenance-1"],
        "events": [],
    }
    payload.update(overrides)
    return payload


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


def test_historical_replay_bridge_models_accept_local_snapshot_inputs(tmp_path):
    from stock_risk_mcp.historical_replay_bridge_fixture import load_historical_replay_bridge_fixture
    from stock_risk_mcp.historical_replay_bridge_models import (
        HistoricalReplayBridgeGapCategory,
        HistoricalReplayBridgeInput,
        HistoricalReplayBridgeSafetyReport,
    )

    fixture_file = tmp_path / "bridge_fixture.json"
    fixture_file.write_text("{}", encoding="utf-8")

    with pytest.raises(ValueError, match="invalid historical replay bridge fixture at"):
        load_historical_replay_bridge_fixture(fixture_file)

    market_snapshot = HistoricalMarketDataSnapshot.model_validate(historical_market_snapshot_payload())
    calendar_snapshot = HistoricalCalendarEventSnapshot.model_validate(historical_calendar_snapshot_payload())
    bridge_input = HistoricalReplayBridgeInput.model_validate(
        {
            "bridge_input_id": "bridge-input-1",
            "historical_market_data_snapshot": market_snapshot.model_dump(mode="json"),
            "historical_calendar_event_snapshot": calendar_snapshot.model_dump(mode="json"),
            "source_manifest_ids": ["manifest-1", "calendar-manifest-1"],
            "source_audit_record_ids": ["audit-1"],
            "provider_provenance_ids": ["provenance-1"],
        }
    )

    assert HistoricalReplayBridgeGapCategory.REPLAY_REMOTE_SOURCE_NOT_ALLOWED.value == "REPLAY_REMOTE_SOURCE_NOT_ALLOWED"
    assert HistoricalReplayBridgeSafetyReport.model_fields["read_only"].default is True
    assert HistoricalReplayBridgeInput.model_fields["historical_market_data_snapshot"].annotation is not None
    assert bridge_input.historical_market_data_snapshot.snapshot_id == "historical-domestic-kr-1"


def test_historical_replay_bridge_fixture_loader_accepts_local_snapshot_fixture(tmp_path):
    from stock_risk_mcp.historical_replay_bridge_fixture import load_historical_replay_bridge_fixture

    payload = {
        "schema_version": "5.2-historical-replay-bridge-fixture",
        "fixture_id": "bridge-fixture-1",
        "created_at": "2026-06-18T10:00:00+09:00",
        "bridge_config": {
            "config_id": "bridge-config-1",
            "strategy_track": "DOMESTIC_KR",
        },
        "historical_market_data_snapshot": historical_market_snapshot_payload(),
        "historical_calendar_event_snapshot": historical_calendar_snapshot_payload(),
        "scanner_replay_hints": [
            {
                "seed_id": "seed-1",
                "symbol": "005930",
                "market": "KRX",
                "session_date": "2026-06-18",
                "reason_code": "CALENDAR_ALIGNED",
                "source_event_id": "market-event-1",
            }
        ],
    }
    fixture_file = tmp_path / "bridge_fixture.json"
    fixture_file.write_text(json.dumps(payload), encoding="utf-8")

    fixture = load_historical_replay_bridge_fixture(fixture_file)

    assert fixture.bridge_config.read_only is True
    assert fixture.historical_market_data_snapshot.snapshot_id == "historical-domestic-kr-1"
    assert fixture.historical_calendar_event_snapshot.snapshot_id == "calendar-domestic-kr-1"
    assert fixture.scanner_replay_hints[0].symbol == "005930"


def test_task2_fixture_and_ids_enforce_consistent_id_hygiene(tmp_path):
    from stock_risk_mcp.historical_replay_bridge_fixture import load_historical_replay_bridge_fixture
    from stock_risk_mcp.historical_replay_bridge_models import (
        HistoricalReplayBridgeSafetyReport,
        HistoricalReplayEventStream,
        HistoricalReplayWindow,
    )
    from stock_risk_mcp.historical_scanner_replay_models import HistoricalScannerReplayInput, HistoricalScannerReplayContext

    payload = {
        "schema_version": "5.2-historical-replay-bridge-fixture",
        "fixture_id": "   ",
        "created_at": "2026-06-18T10:00:00+09:00",
        "bridge_config": {
            "config_id": "bridge-config-1",
            "strategy_track": "DOMESTIC_KR",
        },
        "historical_market_data_snapshot": historical_market_snapshot_payload(),
        "historical_calendar_event_snapshot": historical_calendar_snapshot_payload(),
        "scanner_replay_hints": [],
    }
    fixture_file = tmp_path / "bad_bridge_fixture.json"
    fixture_file.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(ValueError, match="fixture_id must not be blank"):
        load_historical_replay_bridge_fixture(fixture_file)

    event_stream = HistoricalReplayEventStream.model_validate(_minimal_event_stream_payload(bridge_input_id=" bridge-input-1 "))
    window = HistoricalReplayWindow.model_validate(
        {
            "window_id": "window-1",
            "bridge_input_id": "bridge-input-1",
            "strategy_track": "DOMESTIC_KR",
            "market_profile_id": "KRX",
            "session_date": "2026-06-18",
            "event_ids": ["event-1"],
            "historical_market_snapshot_id": "historical-domestic-kr-1",
            "historical_calendar_snapshot_id": "calendar-domestic-kr-1",
        }
    )
    context = HistoricalScannerReplayContext.model_validate(
        {
            "context_id": "context-1",
            "strategy_track": "DOMESTIC_KR",
            "market_profile_id": "KRX",
            "historical_market_snapshot_id": "historical-domestic-kr-1",
            "historical_calendar_snapshot_id": "calendar-domestic-kr-1",
            "source_manifest_ids": ["manifest-1"],
            "source_audit_record_ids": ["audit-1"],
            "provider_provenance_ids": ["provenance-1"],
        }
    )
    scanner_input = HistoricalScannerReplayInput.model_validate(
        {
            "replay_input_id": " replay-input-1 ",
            "strategy_track": "DOMESTIC_KR",
            "replay_context": context.model_dump(mode="json"),
            "historical_market_snapshot_id": "historical-domestic-kr-1",
            "historical_calendar_snapshot_id": "calendar-domestic-kr-1",
            "source_manifest_ids": ["manifest-1"],
            "source_audit_record_ids": ["audit-1"],
            "provider_provenance_ids": ["provenance-1"],
            "candidate_seeds": [],
            "scanner_window_ids": ["window-1"],
        }
    )

    assert event_stream.bridge_input_id == "BRIDGE-INPUT-1"
    assert window.bridge_input_id == "BRIDGE-INPUT-1"
    assert scanner_input.replay_input_id == "REPLAY-INPUT-1"
    assert HistoricalReplayBridgeSafetyReport.model_validate(
        {"safety_report_id": " custom-safety-report "}
    ).safety_report_id == "CUSTOM-SAFETY-REPORT"


def test_historical_replay_window_and_scanner_reports_preserve_lineage_calendar_refs_and_safety_flags():
    from stock_risk_mcp.historical_replay_bridge_models import (
        HistoricalReplayBridgeGapReport,
        HistoricalReplayEventStream,
        HistoricalReplayWindow,
    )
    from stock_risk_mcp.historical_scanner_replay_models import (
        HistoricalScannerReplayCandidateSeed,
        HistoricalScannerReplayInput,
        HistoricalScannerReplayContext,
        HistoricalScannerReplayGapReport,
        HistoricalScannerReplayReport,
    )

    event_stream = HistoricalReplayEventStream.model_validate(
        _minimal_event_stream_payload(
            source_manifest_ids=["manifest-1", "calendar-manifest-1"],
        )
    )
    window = HistoricalReplayWindow.model_validate(
        {
            "window_id": "window-1",
            "bridge_input_id": "bridge-input-1",
            "strategy_track": "DOMESTIC_KR",
            "market_profile_id": "KRX",
            "session_date": "2026-06-18",
            "event_ids": ["event-1"],
            "historical_market_snapshot_id": "historical-domestic-kr-1",
            "historical_calendar_snapshot_id": "calendar-domestic-kr-1",
            "source_manifest_ids": ["manifest-1", "calendar-manifest-1"],
            "source_audit_record_ids": ["audit-1"],
            "provider_provenance_ids": ["provenance-1"],
        }
    )
    bridge_gap_report = HistoricalReplayBridgeGapReport.model_validate(
        {
            "gap_report_id": "bridge-gap-1",
            "bridge_input_id": "bridge-input-1",
            "historical_market_snapshot_id": "historical-domestic-kr-1",
            "historical_calendar_snapshot_id": "calendar-domestic-kr-1",
            "source_manifest_ids": ["manifest-1", "calendar-manifest-1"],
            "source_audit_record_ids": ["audit-1"],
            "provider_provenance_ids": ["provenance-1"],
            "blocking_gap_count": 0,
            "report_only_gap_count": 0,
            "gaps": [
                {
                    "gap_id": "bridge-gap-entry-1",
                    "gap_category": "REPLAY_MISSING_TRADING_SESSION",
                    "severity": "REPORT_ONLY",
                    "message": "missing trading session marker",
                    "source_manifest_id": "manifest-1",
                    "source_audit_record_id": "audit-1",
                    "provider_provenance_id": "provenance-1",
                }
            ],
        }
    )
    scanner_seed = HistoricalScannerReplayCandidateSeed.model_validate(
        {
            "seed_id": "seed-1",
            "symbol": "005930",
            "market": "KRX",
            "session_date": "2026-06-18",
            "reason_code": "CALENDAR_ALIGNED",
            "source_event_id": "event-1",
            "source_manifest_ids": ["manifest-1", "calendar-manifest-1"],
            "source_audit_record_ids": ["audit-1"],
            "provider_provenance_ids": ["provenance-1"],
        }
    )
    scanner_context = HistoricalScannerReplayContext.model_validate(
        {
            "context_id": "context-1",
            "strategy_track": "DOMESTIC_KR",
            "market_profile_id": "KRX",
            "historical_market_snapshot_id": "historical-domestic-kr-1",
            "historical_calendar_snapshot_id": "calendar-domestic-kr-1",
            "source_manifest_ids": ["manifest-1", "calendar-manifest-1"],
            "source_audit_record_ids": ["audit-1"],
            "provider_provenance_ids": ["provenance-1"],
        }
    )
    scanner_input = HistoricalScannerReplayInput.model_validate(
        {
            "replay_input_id": "replay-input-1",
            "strategy_track": "DOMESTIC_KR",
            "replay_context": scanner_context.model_dump(mode="json"),
            "historical_market_snapshot_id": "historical-domestic-kr-1",
            "historical_calendar_snapshot_id": "calendar-domestic-kr-1",
            "source_manifest_ids": ["manifest-1", "calendar-manifest-1"],
            "source_audit_record_ids": ["audit-1"],
            "provider_provenance_ids": ["provenance-1"],
            "candidate_seeds": [scanner_seed.model_dump(mode="json")],
            "scanner_window_ids": ["window-1"],
        }
    )
    scanner_report = HistoricalScannerReplayReport.model_validate(
        {
            "report_id": "scanner-report-1",
            "replay_input_id": "replay-input-1",
            "strategy_track": "DOMESTIC_KR",
            "historical_calendar_snapshot_id": "calendar-domestic-kr-1",
            "source_manifest_ids": ["manifest-1", "calendar-manifest-1"],
            "source_audit_record_ids": ["audit-1"],
            "provider_provenance_ids": ["provenance-1"],
            "candidate_seed_count": 1,
            "scanner_window_count": 1,
        }
    )
    scanner_gap_report = HistoricalScannerReplayGapReport.model_validate(
        {
            "gap_report_id": "scanner-gap-1",
            "replay_input_id": "replay-input-1",
            "historical_calendar_snapshot_id": "calendar-domestic-kr-1",
            "source_manifest_ids": ["manifest-1", "calendar-manifest-1"],
            "source_audit_record_ids": ["audit-1"],
            "provider_provenance_ids": ["provenance-1"],
            "blocking_gap_count": 0,
            "report_only_gap_count": 0,
            "gaps": [
                {
                    "gap_id": "scanner-gap-entry-1",
                    "severity": "REPORT_ONLY",
                    "message": "calendar context missing",
                    "source_manifest_id": "manifest-1",
                    "source_audit_record_id": "audit-1",
                    "provider_provenance_id": "provenance-1",
                }
            ],
        }
    )

    assert event_stream.local_file_only is True
    assert event_stream.no_order is True
    assert event_stream.no_llm_runtime is True
    assert event_stream.provider_provenance_ids == ["PROVENANCE-1"]
    assert window.historical_calendar_snapshot_id == "CALENDAR-DOMESTIC-KR-1"
    assert window.source_manifest_ids == ["MANIFEST-1", "CALENDAR-MANIFEST-1"]
    assert window.local_file_only is True
    assert window.no_llm_runtime is True
    assert window.no_ml_training is True
    assert bridge_gap_report.historical_market_snapshot_id == "HISTORICAL-DOMESTIC-KR-1"
    assert bridge_gap_report.historical_calendar_snapshot_id == "CALENDAR-DOMESTIC-KR-1"
    assert bridge_gap_report.source_audit_record_ids == ["AUDIT-1"]
    assert bridge_gap_report.no_provider_api is True
    assert bridge_gap_report.gaps[0].source_manifest_id == "MANIFEST-1"
    assert scanner_seed.report_only is True
    assert scanner_seed.no_order is True
    assert scanner_seed.source_manifest_ids == ["MANIFEST-1", "CALENDAR-MANIFEST-1"]
    assert scanner_input.historical_calendar_snapshot_id == "CALENDAR-DOMESTIC-KR-1"
    assert scanner_input.source_audit_record_ids == ["AUDIT-1"]
    assert scanner_input.local_file_only is True
    assert scanner_input.no_ml_training is True
    assert scanner_report.historical_calendar_snapshot_id == "CALENDAR-DOMESTIC-KR-1"
    assert scanner_report.source_audit_record_ids == ["AUDIT-1"]
    assert scanner_report.no_provider_api is True
    assert scanner_gap_report.provider_provenance_ids == ["PROVENANCE-1"]
    assert scanner_gap_report.no_order is True
    assert scanner_gap_report.gaps[0].provider_provenance_id == "PROVENANCE-1"


def test_task2_models_fail_closed_when_safety_flags_are_disabled():
    from stock_risk_mcp.historical_replay_bridge_models import (
        HistoricalReplayBridgeGapReport,
        HistoricalReplayEventStream,
    )
    from stock_risk_mcp.historical_scanner_replay_models import (
        HistoricalScannerReplayCandidateSeed,
        HistoricalScannerReplayInput,
        HistoricalScannerReplayContext,
    )

    with pytest.raises(ValueError, match="historical replay event stream must remain no_network"):
        HistoricalReplayEventStream.model_validate(_minimal_event_stream_payload(no_network=False))

    with pytest.raises(ValueError, match="historical replay bridge gap report must remain no_provider_api"):
        HistoricalReplayBridgeGapReport.model_validate(
            {
                "gap_report_id": "bridge-gap-1",
                "bridge_input_id": "bridge-input-1",
                "historical_market_snapshot_id": "historical-domestic-kr-1",
                "historical_calendar_snapshot_id": "calendar-domestic-kr-1",
                "source_manifest_ids": ["manifest-1"],
                "source_audit_record_ids": ["audit-1"],
                "provider_provenance_ids": ["provenance-1"],
                "blocking_gap_count": 0,
                "report_only_gap_count": 0,
                "gaps": [],
                "no_provider_api": False,
            }
        )

    with pytest.raises(ValueError, match="historical scanner replay candidate seed must remain no_llm_runtime"):
        HistoricalScannerReplayCandidateSeed.model_validate(
            {
                "seed_id": "seed-1",
                "symbol": "005930",
                "market": "KRX",
                "session_date": "2026-06-18",
                "reason_code": "CALENDAR_ALIGNED",
                "source_event_id": "event-1",
                "source_manifest_ids": ["manifest-1"],
                "source_audit_record_ids": ["audit-1"],
                "provider_provenance_ids": ["provenance-1"],
                "no_llm_runtime": False,
            }
        )

    context = HistoricalScannerReplayContext.model_validate(
        {
            "context_id": "context-1",
            "strategy_track": "DOMESTIC_KR",
            "market_profile_id": "KRX",
            "historical_market_snapshot_id": "historical-domestic-kr-1",
            "historical_calendar_snapshot_id": "calendar-domestic-kr-1",
            "source_manifest_ids": ["manifest-1"],
            "source_audit_record_ids": ["audit-1"],
            "provider_provenance_ids": ["provenance-1"],
        }
    )
    seed = HistoricalScannerReplayCandidateSeed.model_validate(
        {
            "seed_id": "seed-1",
            "symbol": "005930",
            "market": "KRX",
            "session_date": "2026-06-18",
            "reason_code": "CALENDAR_ALIGNED",
            "source_event_id": "event-1",
            "source_manifest_ids": ["manifest-1"],
            "source_audit_record_ids": ["audit-1"],
            "provider_provenance_ids": ["provenance-1"],
        }
    )
    with pytest.raises(ValueError, match="historical scanner replay input must remain no_ml_training"):
        HistoricalScannerReplayInput.model_validate(
            {
                "replay_input_id": "replay-input-1",
                "strategy_track": "DOMESTIC_KR",
                "replay_context": context.model_dump(mode="json"),
                "historical_market_snapshot_id": "historical-domestic-kr-1",
                "historical_calendar_snapshot_id": "calendar-domestic-kr-1",
                "source_manifest_ids": ["manifest-1"],
                "source_audit_record_ids": ["audit-1"],
                "provider_provenance_ids": ["provenance-1"],
                "candidate_seeds": [seed.model_dump(mode="json")],
                "scanner_window_ids": ["window-1"],
                "no_ml_training": False,
            }
        )


def test_task2_models_reject_malformed_lineage_ids_and_context_contradictions():
    from stock_risk_mcp.historical_replay_bridge_models import HistoricalReplayBridgeGapReport, HistoricalReplayBridgeInput
    from stock_risk_mcp.historical_scanner_replay_models import (
        HistoricalScannerReplayCandidateSeed,
        HistoricalScannerReplayContext,
        HistoricalScannerReplayInput,
    )

    with pytest.raises(ValueError):
        HistoricalReplayBridgeGapReport.model_validate(
            {
                "gap_report_id": "bridge-gap-1",
                "bridge_input_id": "bridge-input-1",
                "historical_market_snapshot_id": "historical-domestic-kr-1",
                "historical_calendar_snapshot_id": "calendar-domestic-kr-1",
                "source_manifest_ids": ["   "],
                "source_audit_record_ids": ["audit-1"],
                "provider_provenance_ids": ["provenance-1"],
                "blocking_gap_count": 0,
                "report_only_gap_count": 0,
                "gaps": [],
            }
        )

    market_snapshot = HistoricalMarketDataSnapshot.model_validate(historical_market_snapshot_payload())
    bad_calendar_payload = historical_calendar_snapshot_payload()
    bad_calendar_payload["manifest"]["market_profile_id"] = "KOSDAQ"
    with pytest.raises(ValueError, match="manifest market_profile_id must match calendar_config market_profile"):
        HistoricalCalendarEventSnapshot.model_validate(bad_calendar_payload)

    good_calendar_snapshot = HistoricalCalendarEventSnapshot.model_validate(historical_calendar_snapshot_payload())
    contradiction_input = {
        "bridge_input_id": "bridge-input-1",
        "historical_market_data_snapshot": market_snapshot.model_dump(mode="json"),
        "historical_calendar_event_snapshot": good_calendar_snapshot.model_dump(mode="json"),
        "source_manifest_ids": ["manifest-1"],
        "source_audit_record_ids": ["audit-1"],
        "provider_provenance_ids": ["provenance-1"],
    }
    bridge_input = HistoricalReplayBridgeInput.model_validate(contradiction_input)
    assert bridge_input.historical_calendar_event_snapshot.snapshot_id == "calendar-domestic-kr-1"

    context = HistoricalScannerReplayContext.model_validate(
        {
            "context_id": "context-1",
            "strategy_track": "DOMESTIC_KR",
            "market_profile_id": "KRX",
            "historical_market_snapshot_id": "historical-domestic-kr-1",
            "historical_calendar_snapshot_id": "calendar-domestic-kr-1",
            "source_manifest_ids": ["manifest-1"],
            "source_audit_record_ids": ["audit-1"],
            "provider_provenance_ids": ["provenance-1"],
        }
    )
    seed = HistoricalScannerReplayCandidateSeed.model_validate(
        {
            "seed_id": "seed-1",
            "symbol": "005930",
            "market": "KRX",
            "session_date": "2026-06-18",
            "reason_code": "CALENDAR_ALIGNED",
            "source_event_id": "event-1",
            "source_manifest_ids": ["manifest-1"],
            "source_audit_record_ids": ["audit-1"],
            "provider_provenance_ids": ["provenance-1"],
        }
    )
    with pytest.raises(
        ValueError,
        match="historical scanner replay input historical_calendar_snapshot_id must match replay_context historical_calendar_snapshot_id",
    ):
        HistoricalScannerReplayInput.model_validate(
            {
                "replay_input_id": "replay-input-1",
                "strategy_track": "DOMESTIC_KR",
                "replay_context": context.model_dump(mode="json"),
                "historical_market_snapshot_id": "historical-domestic-kr-1",
                "historical_calendar_snapshot_id": "calendar-domestic-kr-2",
                "source_manifest_ids": ["manifest-1"],
                "source_audit_record_ids": ["audit-1"],
                "provider_provenance_ids": ["provenance-1"],
                "candidate_seeds": [seed.model_dump(mode="json")],
                "scanner_window_ids": ["window-1"],
            }
        )


def test_task2_models_reject_timezone_naive_datetime_where_relevant():
    from stock_risk_mcp.historical_replay_bridge_models import HistoricalReplayBridgeAuditRecord, HistoricalReplayEvent

    with pytest.raises(ValueError, match="timestamp must include timezone"):
        HistoricalReplayEvent.model_validate(
            {
                "replay_event_id": "event-1",
                "bridge_input_id": "bridge-input-1",
                "symbol": "005930",
                "market": "KRX",
                "session_date": "2026-06-18",
                "replay_timestamp": "2026-06-18T09:00:00",
                "source_manifest_ids": ["manifest-1"],
                "source_audit_record_ids": ["audit-1"],
                "provider_provenance_ids": ["provenance-1"],
                "historical_market_snapshot_id": "historical-domestic-kr-1",
                "historical_calendar_snapshot_id": "calendar-domestic-kr-1",
            }
        )

    with pytest.raises(ValueError, match="timestamp must include timezone"):
        HistoricalReplayBridgeAuditRecord.model_validate(
            {
                "audit_record_id": "bridge-audit-1",
                "bridge_input_id": "bridge-input-1",
                "created_at": "2026-06-18T10:00:00",
                "source_manifest_ids": ["manifest-1"],
                "source_audit_record_ids": ["audit-1"],
                "provider_provenance_ids": ["provenance-1"],
                "historical_market_snapshot_id": "historical-domestic-kr-1",
                "historical_calendar_snapshot_id": "calendar-domestic-kr-1",
            }
        )


def test_task2_models_reject_none_for_required_text_fields():
    from stock_risk_mcp.historical_replay_bridge_models import HistoricalReplayEventStream
    from stock_risk_mcp.historical_scanner_replay_models import HistoricalScannerReplayCandidateSeed

    with pytest.raises(ValueError, match="bridge_input_id must not be null"):
        HistoricalReplayEventStream.model_validate(
            {
                "stream_id": "stream-1",
                "bridge_input_id": None,
                "strategy_track": "DOMESTIC_KR",
                "market_profile_id": "KRX",
                "historical_market_snapshot_id": "historical-domestic-kr-1",
                "historical_calendar_snapshot_id": "calendar-domestic-kr-1",
                "source_manifest_ids": ["manifest-1"],
                "source_audit_record_ids": ["audit-1"],
                "provider_provenance_ids": ["provenance-1"],
                "events": [],
            }
        )

    with pytest.raises(ValueError, match="reason_code must not be null"):
        HistoricalScannerReplayCandidateSeed.model_validate(
            {
                "seed_id": "seed-1",
                "symbol": "005930",
                "market": "KRX",
                "session_date": "2026-06-18",
                "reason_code": None,
                "source_event_id": "event-1",
                "source_manifest_ids": ["manifest-1"],
                "source_audit_record_ids": ["audit-1"],
                "provider_provenance_ids": ["provenance-1"],
            }
        )


def test_task2_models_reject_scalar_string_for_lineage_list_fields():
    from stock_risk_mcp.historical_replay_bridge_models import HistoricalReplayBridgeGapReport
    from stock_risk_mcp.historical_scanner_replay_models import HistoricalScannerReplayInput, HistoricalScannerReplayContext

    with pytest.raises(ValueError, match="gap_lineage_ids must be a list"):
        HistoricalReplayBridgeGapReport.model_validate(
            {
                "gap_report_id": "bridge-gap-1",
                "bridge_input_id": "bridge-input-1",
                "historical_market_snapshot_id": "historical-domestic-kr-1",
                "historical_calendar_snapshot_id": "calendar-domestic-kr-1",
                "source_manifest_ids": "manifest-1",
                "source_audit_record_ids": ["audit-1"],
                "provider_provenance_ids": ["provenance-1"],
                "blocking_gap_count": 0,
                "report_only_gap_count": 0,
                "gaps": [],
            }
        )

    context = HistoricalScannerReplayContext.model_validate(
        {
            "context_id": "context-1",
            "strategy_track": "DOMESTIC_KR",
            "market_profile_id": "KRX",
            "historical_market_snapshot_id": "historical-domestic-kr-1",
            "historical_calendar_snapshot_id": "calendar-domestic-kr-1",
            "source_manifest_ids": ["manifest-1"],
            "source_audit_record_ids": ["audit-1"],
            "provider_provenance_ids": ["provenance-1"],
        }
    )
    with pytest.raises(ValueError, match="bundle_lineage_ids must be a list"):
        HistoricalScannerReplayInput.model_validate(
            {
                "replay_input_id": "replay-input-1",
                "strategy_track": "DOMESTIC_KR",
                "replay_context": context.model_dump(mode="json"),
                "historical_market_snapshot_id": "historical-domestic-kr-1",
                "historical_calendar_snapshot_id": "calendar-domestic-kr-1",
                "source_manifest_ids": "manifest-1",
                "source_audit_record_ids": ["audit-1"],
                "provider_provenance_ids": ["provenance-1"],
                "candidate_seeds": [],
                "scanner_window_ids": ["window-1"],
            }
        )


def test_task2_gap_entries_reject_null_message_fields():
    from stock_risk_mcp.historical_replay_bridge_models import HistoricalReplayBridgeGapReport
    from stock_risk_mcp.historical_scanner_replay_models import HistoricalScannerReplayGapReport

    with pytest.raises(ValueError, match="message must not be null"):
        HistoricalReplayBridgeGapReport.model_validate(
            {
                "gap_report_id": "bridge-gap-1",
                "bridge_input_id": "bridge-input-1",
                "historical_market_snapshot_id": "historical-domestic-kr-1",
                "historical_calendar_snapshot_id": "calendar-domestic-kr-1",
                "source_manifest_ids": ["manifest-1"],
                "source_audit_record_ids": ["audit-1"],
                "provider_provenance_ids": ["provenance-1"],
                "blocking_gap_count": 0,
                "report_only_gap_count": 0,
                "gaps": [
                    {
                        "gap_id": "bridge-gap-entry-1",
                        "gap_category": "REPLAY_MISSING_TRADING_SESSION",
                        "severity": "REPORT_ONLY",
                        "message": None,
                    }
                ],
            }
        )

    with pytest.raises(ValueError, match="message must not be null"):
        HistoricalScannerReplayGapReport.model_validate(
            {
                "gap_report_id": "scanner-gap-1",
                "replay_input_id": "replay-input-1",
                "historical_calendar_snapshot_id": "calendar-domestic-kr-1",
                "source_manifest_ids": ["manifest-1"],
                "source_audit_record_ids": ["audit-1"],
                "provider_provenance_ids": ["provenance-1"],
                "blocking_gap_count": 0,
                "report_only_gap_count": 0,
                "gaps": [
                    {
                        "gap_id": "scanner-gap-entry-1",
                        "severity": "REPORT_ONLY",
                        "message": None,
                    }
                ],
            }
        )
