import json

import pytest

from stock_risk_mcp.macro_regime_provider_fixture import load_macro_regime_fixture
from stock_risk_mcp.macro_regime_provider_guard import validate_macro_regime_metadata_safety
from stock_risk_mcp.macro_regime_provider_models import (
    MacroRegimePipelineInput,
    MacroRegimeProviderStatus,
    MacroRegimeSeriesId,
)


def macro_regime_payload(**overrides):
    payload = {
        "pipeline_id": "macro-regime-test",
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
            }
        ],
        "manual_events": [],
        "mocked_provider_payloads": [],
        "audit_records": [
            {
                "audit_record_id": "macro-regime-audit-1",
                "created_at": "2026-06-26T09:11:00+09:00",
                "source_path": "fixtures/macro/macro_regime_fixture.json",
                "operator_context": "offline macro regime review",
                "redaction_applied": True,
                "contains_secret_material": False,
                "contains_token_material": False,
                "contains_account_material": False,
            }
        ],
    }
    payload.update(overrides)
    return payload


def test_macro_regime_defaults_are_local_report_only():
    loaded = MacroRegimePipelineInput.model_validate(macro_regime_payload())
    assert loaded.report_only is True
    assert loaded.no_order is True
    assert loaded.no_env_read is True
    assert loaded.fred_series_requests[0].series_id == MacroRegimeSeriesId.VIX


def test_guard_rejects_secret_and_order_markers():
    with pytest.raises(ValueError):
        validate_macro_regime_metadata_safety({"authorization": "Bearer secret"}, context="macro regime")
    with pytest.raises(ValueError):
        validate_macro_regime_metadata_safety({"note": "place order now"}, context="macro regime")


def test_fixture_loader_reads_local_json_only(tmp_path):
    path = tmp_path / "macro_regime_fixture.json"
    path.write_text(json.dumps(macro_regime_payload()), encoding="utf-8")
    loaded = load_macro_regime_fixture(path)
    assert isinstance(loaded, MacroRegimePipelineInput)
    assert loaded.local_file_only is True


def test_fixture_loader_rejects_remote_or_parquet(tmp_path):
    with pytest.raises(ValueError, match="local file path"):
        load_macro_regime_fixture("https://example.com/macro.json")
    with pytest.raises(ValueError, match="parquet remains unsupported"):
        load_macro_regime_fixture(tmp_path / "macro.parquet")


def test_provider_status_surface_is_exposed():
    assert MacroRegimeProviderStatus.PROVIDER_SETUP_REQUIRED.value == "PROVIDER_SETUP_REQUIRED"
