import json

import pytest

from stock_risk_mcp.kiwoom_rest_readonly_sector_fixture import load_kiwoom_rest_readonly_sector_fixture
from stock_risk_mcp.kiwoom_rest_readonly_sector_guard import validate_kiwoom_rest_sector_metadata_safety
from stock_risk_mcp.kiwoom_rest_readonly_sector_models import (
    KiwoomRestSectorApiId,
    KiwoomRestSectorConfig,
    KiwoomRestSectorMode,
    KiwoomRestSectorReadiness,
)


def kiwoom_rest_readonly_sector_payload(**overrides):
    payload = {
        "config_id": "kiwoom-rest-sector-1",
        "api_id": "KA90001",
        "qry_tp": "0",
        "provider_symbol": "",
        "date_tp": "10",
        "theme_name": "",
        "flu_pl_amt_tp": "1",
        "stex_tp": "1",
        "available_at": "2026-06-25T15:35:00+09:00",
        "source_ref": "fixtures/kiwoom/readonly_sector_fixture.json",
        "mocked_response_payload": {
            "return_code": 0,
            "return_msg": "정상적으로 처리되었습니다",
            "thema_grp": [
                {
                    "thema_grp_cd": "553",
                    "thema_nm": "2차전지",
                    "stk_num": "12",
                    "flu_sig": "2",
                    "flu_rt": "+3.25",
                    "rising_stk_num": "9",
                    "fall_stk_num": "3",
                    "dt_prft_rt": "+5.10",
                    "main_stk": "LG에너지솔루션",
                }
            ],
            "cont_yn": "N",
            "next_key": "",
        },
        "safety_report": {
            "safety_report_id": "kiwoom-rest-sector-safety-1",
            "blocked_capabilities": [
                "ACCOUNT_API_BLOCKED",
                "ORDER_API_BLOCKED",
                "WEBSOCKET_BLOCKED",
                "NETWORK_BLOCKED",
                "TOKEN_LOADING_BLOCKED",
                "AUTH_HEADER_GENERATION_BLOCKED",
            ],
            "findings": [],
        },
        "audit_records": [
            {
                "audit_record_id": "kiwoom-rest-sector-audit-1",
                "created_at": "2026-06-25T15:36:00+09:00",
                "source_path": "fixtures/kiwoom/readonly_sector_fixture.json",
                "operator_context": "offline kiwoom readonly sector review",
                "redaction_applied": True,
                "contains_secret_material": False,
                "contains_token_material": False,
                "contains_account_material": False,
            }
        ],
    }
    payload.update(overrides)
    return payload


def test_default_adapter_is_mocked_transport_readonly_report_only():
    loaded = KiwoomRestSectorConfig.model_validate(kiwoom_rest_readonly_sector_payload())
    assert loaded.mode == KiwoomRestSectorMode.MOCKED_TRANSPORT_ONLY
    assert loaded.report_only is True
    assert loaded.no_network is True


def test_guard_rejects_raw_token_secret_account_markers():
    with pytest.raises(ValueError):
        validate_kiwoom_rest_sector_metadata_safety({"authorization": "Bearer raw-token"}, context="kiwoom sector")
    with pytest.raises(ValueError):
        validate_kiwoom_rest_sector_metadata_safety({"account_no": "123-45"}, context="kiwoom sector")


def test_fixture_loader_reads_local_json_only(tmp_path):
    fixture_path = tmp_path / "kiwoom_readonly_sector.json"
    fixture_path.write_text(json.dumps(kiwoom_rest_readonly_sector_payload()), encoding="utf-8")
    loaded = load_kiwoom_rest_readonly_sector_fixture(fixture_path)
    assert isinstance(loaded, KiwoomRestSectorConfig)
    assert loaded.local_file_only is True


def test_fixture_loader_rejects_remote_or_parquet(tmp_path):
    with pytest.raises(ValueError, match="local file path"):
        load_kiwoom_rest_readonly_sector_fixture("https://example.com/sector.json")
    with pytest.raises(ValueError, match="parquet remains unsupported"):
        load_kiwoom_rest_readonly_sector_fixture(tmp_path / "sector.parquet")


def test_api_and_readiness_enums_surface_expected_values():
    assert KiwoomRestSectorApiId.KA90001.value == "KA90001"
    assert KiwoomRestSectorApiId.KA40010.value == "KA40010"
    assert KiwoomRestSectorReadiness.READONLY_ADAPTER_READY.value == "READONLY_ADAPTER_READY"
