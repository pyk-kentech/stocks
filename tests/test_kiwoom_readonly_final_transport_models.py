import json

import pytest

from stock_risk_mcp.kiwoom_readonly_final_transport_fixture import load_kiwoom_readonly_final_transport_fixture
from stock_risk_mcp.kiwoom_readonly_final_transport_guard import (
    validate_kiwoom_readonly_final_transport_metadata_safety,
)
from stock_risk_mcp.kiwoom_readonly_final_transport_models import (
    KiwoomReadonlyFinalDomain,
    KiwoomReadonlyFinalRequest,
    KiwoomReadonlyFinalStatus,
    KiwoomReadonlyFinalTokenProviderKind,
    KiwoomReadonlyFinalTransportMode,
)


def kiwoom_readonly_final_transport_payload(**overrides):
    payload = {
        "request_id": "kiwoom-readonly-final-1",
        "mode": "DRY_RUN_PREVIEW_ONLY",
        "api_id": "KA10081",
        "domain": "KIWOOM_MOCK_KRX",
        "body_json": {"stk_cd": "005930", "base_dt": "20260625", "upd_stkpc_tp": "1"},
        "provider_symbol": "005930",
        "canonical_instrument_key": "005930_KRX",
        "available_at": "2026-06-25T15:35:00+09:00",
        "validate_snapshot": False,
    }
    payload.update(overrides)
    return payload


def test_final_transport_request_defaults_to_local_offline_readonly():
    loaded = KiwoomReadonlyFinalRequest.model_validate(kiwoom_readonly_final_transport_payload())
    assert loaded.mode == KiwoomReadonlyFinalTransportMode.DRY_RUN_PREVIEW_ONLY
    assert loaded.domain == KiwoomReadonlyFinalDomain.KIWOOM_MOCK_KRX
    assert loaded.token_provider.provider_kind == KiwoomReadonlyFinalTokenProviderKind.DISABLED
    assert loaded.report_only is True
    assert loaded.no_network is True


def test_final_transport_fixture_loader_reads_local_json_only(tmp_path):
    fixture_path = tmp_path / "kiwoom_readonly_final_transport_fixture.json"
    fixture_path.write_text(json.dumps(kiwoom_readonly_final_transport_payload()), encoding="utf-8")
    loaded = load_kiwoom_readonly_final_transport_fixture(fixture_path)
    assert isinstance(loaded, KiwoomReadonlyFinalRequest)
    assert loaded.local_file_only is True


def test_final_transport_fixture_rejects_remote_or_parquet(tmp_path):
    with pytest.raises(ValueError, match="local file path"):
        load_kiwoom_readonly_final_transport_fixture("https://example.com/final.json")
    with pytest.raises(ValueError, match="parquet remains unsupported"):
        load_kiwoom_readonly_final_transport_fixture(tmp_path / "final.parquet")


def test_final_transport_guard_rejects_remote_or_blank_context():
    validate_kiwoom_readonly_final_transport_metadata_safety(
        {"source_path": "local_data/kiwoom_readonly_captures", "operator_context": "offline smoke"},
        context="kiwoom final",
    )
    with pytest.raises(ValueError, match="local-only"):
        validate_kiwoom_readonly_final_transport_metadata_safety(
            {"source_path": "https://example.com/final.json", "operator_context": "offline smoke"},
            context="kiwoom final",
        )
    with pytest.raises(ValueError, match="operator_context is required"):
        validate_kiwoom_readonly_final_transport_metadata_safety(
            {"source_path": "local_data/kiwoom_readonly_captures", "operator_context": ""},
            context="kiwoom final",
        )


def test_final_transport_enums_surface_expected_values():
    assert KiwoomReadonlyFinalTransportMode.REAL_READONLY_SINGLE_CALL_SMOKE.value == "REAL_READONLY_SINGLE_CALL_SMOKE"
    assert KiwoomReadonlyFinalDomain.KIWOOM_PROD_READONLY.value == "KIWOOM_PROD_READONLY"
    assert KiwoomReadonlyFinalTokenProviderKind.ENV_EXPLICIT.value == "ENV_EXPLICIT"
    assert KiwoomReadonlyFinalStatus.V8_FINAL_READY.value == "V8_FINAL_READY"
