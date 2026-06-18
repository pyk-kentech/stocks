import json

from stock_risk_mcp.cli import main


def write(path, payload):
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def run(capsys, args):
    main(args)
    return json.loads(capsys.readouterr().out)


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


def historical_data_fixture_payload(csv_file):
    return {
        "schema_version": "5.1-historical-data-ingestion-fixture",
        "fixture_id": "hist-fixture-1",
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
            "local_file_path": str(csv_file),
            "declared_format": "CSV",
            "declared_content_type": "text/csv",
            "strategy_track": "DOMESTIC_KR",
            "market_profile_id": "KRX",
            "source_id": "KRX_MANUAL_EXPORT",
            "source_vendor_name": "KRX Manual Export",
            "source_reliability_tier": "OFFICIAL",
            "path_safety_class": "LOCAL_TMP",
            "timezone": "Asia/Seoul",
            "currency": "KRW",
            "source_symbol_namespace": "KRX",
            "contains_adjusted_prices": False,
            "contains_unadjusted_prices": True,
            "contains_turnover": True,
            "contains_trade_value": True,
        },
        "provider_provenance": {
            "provenance_id": "provenance-1",
            "source_family": "KRX_MANUAL_EXPORT",
            "source_name": "KRX Manual Export",
            "source_tier": "OFFICIAL",
            "acquisition_mode": "LOCAL_FILE",
            "requires_reconciliation": False,
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
        "ingestion_batch_id": "batch-1",
        "audit_record_ids": ["audit-1"],
    }


def historical_calendar_fixture_payload(session_file, market_event_file, corporate_event_file):
    return {
        "schema_version": "5.1-historical-calendar-ingestion-fixture",
        "fixture_id": "calendar-fixture-1",
        "created_at": "2026-06-18T09:00:00+09:00",
        "calendar_config": {
            "calendar_config_id": "calendar-config-1",
            "strategy_track": "DOMESTIC_KR",
            "market_profile": market_profile_payload(),
            "source_type": "local_jsonl",
            "session_validation_mode": "STRICT",
            "unexpected_closure_policy": "FAIL_CLOSED",
            "early_close_policy": "FAIL_CLOSED",
            "event_type_policy": "STRICT",
            "timezone_mismatch_policy": "REPORT_ONLY",
        },
        "session_file_path": str(session_file),
        "market_event_file_path": str(market_event_file),
        "corporate_event_file_path": str(corporate_event_file),
        "calendar_batch_id": "calendar-batch-1",
        "source_descriptor_ids": ["SESSIONS_JSONL", "MARKET_EVENTS_JSONL", "CORPORATE_EVENTS_JSONL"],
    }


def test_historical_ingestion_cli_commands_return_json_safe_outputs(tmp_path, capsys):
    csv_file = tmp_path / "ohlcv.csv"
    csv_file.write_text(
        "symbol,timestamp,open,high,low,close,volume\n"
        "005930,2026-06-18T09:00:00+09:00,70000,71000,69900,70500,1000\n",
        encoding="utf-8",
    )
    historical_data_fixture = write(
        tmp_path / "historical_data_fixture.json",
        historical_data_fixture_payload(csv_file),
    )
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
    historical_calendar_fixture = write(
        tmp_path / "historical_calendar_fixture.json",
        historical_calendar_fixture_payload(session_file, market_event_file, corporate_event_file),
    )
    validation_file = tmp_path / "historical_data_validation.json"
    quality_file = tmp_path / "historical_data_quality.json"
    gap_file = tmp_path / "historical_data_gap.json"
    manifest_file = tmp_path / "historical_data_manifest.json"
    calendar_validation_file = tmp_path / "historical_calendar_validation.json"
    calendar_gap_file = tmp_path / "historical_calendar_gap.json"

    data_config = run(capsys, ["historical-data-config-validate", "--fixture-file", str(historical_data_fixture)])
    data_validate = run(capsys, ["historical-data-validate", "--fixture-file", str(historical_data_fixture), "--output-file", str(validation_file)])
    data_quality = run(capsys, ["historical-data-quality-report", "--fixture-file", str(historical_data_fixture), "--output-file", str(quality_file)])
    data_gap = run(capsys, ["historical-data-gap-report", "--fixture-file", str(historical_data_fixture), "--output-file", str(gap_file)])
    data_manifest = run(capsys, ["historical-data-manifest-build", "--fixture-file", str(historical_data_fixture), "--output-file", str(manifest_file)])
    calendar_config = run(capsys, ["historical-calendar-config-validate", "--fixture-file", str(historical_calendar_fixture)])
    calendar_validate = run(capsys, ["historical-calendar-validate", "--fixture-file", str(historical_calendar_fixture), "--output-file", str(calendar_validation_file)])
    calendar_gap = run(capsys, ["historical-calendar-gap-report", "--fixture-file", str(historical_calendar_fixture), "--output-file", str(calendar_gap_file)])

    assert data_config["status"] == "COMPLETED"
    assert data_validate["status"] == "COMPLETED"
    assert data_quality["status"] == "COMPLETED"
    assert data_gap["status"] == "COMPLETED"
    assert data_manifest["status"] == "COMPLETED"
    assert calendar_config["status"] == "COMPLETED"
    assert calendar_validate["status"] == "COMPLETED"
    assert calendar_gap["status"] == "COMPLETED"


def test_historical_ingestion_cli_invalid_fixture_is_json_safe(tmp_path, capsys):
    result = run(capsys, ["historical-data-config-validate", "--fixture-file", str(tmp_path / "missing.json")])
    assert result["status"] == "FAILED"
    assert result["errors"]
