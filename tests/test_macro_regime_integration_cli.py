import json

from stock_risk_mcp.cli import run_command


def _fixture_payload():
    return {
        "pipeline_id": "macro-regime-cli",
        "anchor_at": "2026-06-26T09:10:00+09:00",
        "available_at": "2026-06-26T09:05:00+09:00",
        "provider_definitions": [
            {
                "provider": "LOCAL_FIXTURE",
                "capabilities": ["NQ_FUTURES", "ES_FUTURES"],
                "status": "MANUAL_ONLY",
                "credential_policy": "NOT_REQUIRED",
                "opt_in_required": False,
                "notes": "manual futures fixtures only",
            },
            {
                "provider": "FRED",
                "capabilities": ["VIX", "DOLLAR_STRENGTH", "US10Y", "USDKRW"],
                "status": "MOCKED_ONLY",
                "credential_policy": "KEY_REF_ONLY",
                "supports_real_http": True,
                "key_ref_required": True,
                "notes": "fred preview plus mocked parsing",
            },
            {
                "provider": "INVESTING_CALENDAR_MANUAL",
                "capabilities": ["MANUAL_EVENT_CALENDAR", "CPI_EVENT"],
                "status": "MANUAL_ONLY",
                "credential_policy": "MANUAL_IMPORT_ONLY",
                "opt_in_required": False,
                "notes": "manual macro calendar import",
            },
        ],
        "fred_series_requests": [
            {
                "request_id": "fred-vix",
                "series_id": "VIX",
                "fred_series_code": "VIXCLS",
                "observation_start": "2026-06-20",
                "observation_end": "2026-06-25",
                "api_key_ref": "FRED_KEY_REF",
            }
        ],
        "manual_series_points": [
            {
                "series_id": "NQ_CONTINUOUS",
                "asset_class": "FUTURES",
                "provider": "LOCAL_FIXTURE",
                "provider_symbol": "NQM2026",
                "observed_at": "2026-06-26T09:00:00+09:00",
                "available_at": "2026-06-26T09:02:00+09:00",
                "value": 20150.0,
                "pct_change_1d": 0.7,
                "unit": "INDEX",
                "source_ref": "fixtures/macro/nq.json",
            },
            {
                "series_id": "ES_CONTINUOUS",
                "asset_class": "FUTURES",
                "provider": "LOCAL_FIXTURE",
                "provider_symbol": "ESM2026",
                "observed_at": "2026-06-26T09:00:00+09:00",
                "available_at": "2026-06-26T09:02:00+09:00",
                "value": 5525.0,
                "pct_change_1d": 0.5,
                "unit": "INDEX",
                "source_ref": "fixtures/macro/es.json",
            },
        ],
        "manual_events": [],
        "mocked_provider_payloads": [
            {
                "payload_id": "fred-vix",
                "provider": "FRED",
                "series_id": "VIX",
                "source_ref": "fixtures/macro/fred_vix.json",
                "payload": {"observations": [{"date": "2026-06-25", "value": "15.20"}]},
            },
            {
                "payload_id": "fred-us10y",
                "provider": "FRED",
                "series_id": "US10Y",
                "source_ref": "fixtures/macro/fred_us10y.json",
                "payload": {"observations": [{"date": "2026-06-25", "value": "3.90"}]},
            },
            {
                "payload_id": "fred-usdkrw",
                "provider": "FRED",
                "series_id": "USDKRW",
                "source_ref": "fixtures/macro/fred_usdkrw.json",
                "payload": {"observations": [{"date": "2026-06-25", "value": "1360.00"}]},
            },
            {
                "payload_id": "fred-dollar",
                "provider": "FRED",
                "series_id": "DOLLAR_STRENGTH",
                "source_ref": "fixtures/macro/fred_dollar.json",
                "payload": {"observations": [{"date": "2026-06-25", "value": "121.50"}]},
            },
            {
                "payload_id": "macro-event",
                "provider": "INVESTING_CALENDAR_MANUAL",
                "source_ref": "fixtures/macro/events.json",
                "payload": {
                    "events": [
                        {
                            "event_id": "macro-cpi-1",
                            "event_type": "CPI",
                            "country": "US",
                            "title": "US CPI",
                            "event_time": "2026-06-26T13:30:00+00:00",
                            "timezone": "UTC",
                            "importance": "HIGH",
                            "affected_assets": ["NQ_CONTINUOUS", "ES_CONTINUOUS"],
                            "pre_event_block_window_minutes": 30,
                            "pre_event_reduce_window_minutes": 60,
                            "post_event_cooldown_minutes": 45,
                            "event_active_window_minutes": 15,
                            "available_at": "2026-06-20T00:00:00+00:00",
                        }
                    ]
                },
            },
        ],
        "audit_records": [
            {
                "audit_record_id": "macro-regime-audit-cli",
                "created_at": "2026-06-26T09:11:00+09:00",
                "source_path": "fixtures/macro/macro_regime_fixture.json",
                "operator_context": "offline macro regime cli test",
                "redaction_applied": True,
                "contains_secret_material": False,
                "contains_token_material": False,
                "contains_account_material": False,
            }
        ],
    }


def test_macro_regime_cli_reports_build_from_fixture(tmp_path):
    fixture_file = tmp_path / "macro_regime_fixture.json"
    fixture_file.write_text(json.dumps(_fixture_payload()), encoding="utf-8")

    parser = __import__("stock_risk_mcp.cli", fromlist=["build_command_parser"]).build_command_parser()
    args = parser.parse_args(["macro-regime-classification-report", "--fixture-file", str(fixture_file)])
    result = run_command(args)
    assert result["label"] == "MACRO_RISK_ON"

    args = parser.parse_args(["macro-regime-v7-integration-report", "--fixture-file", str(fixture_file)])
    result = run_command(args)
    assert result["market_regime_context"] == "RISK_ON_COMPATIBLE"

    args = parser.parse_args(["macro-regime-fred-request-preview", "--fixture-file", str(fixture_file)])
    result = run_command(args)
    assert result["provider"] == "FRED"
