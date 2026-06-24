import json

import pytest

from stock_risk_mcp.kiwoom_rest_readonly_rank_fixture import load_kiwoom_rest_readonly_rank_fixture
from stock_risk_mcp.kiwoom_rest_readonly_rank_guard import validate_kiwoom_rest_rank_metadata_safety
from stock_risk_mcp.kiwoom_rest_readonly_rank_models import (
    KiwoomRestRankApiId,
    KiwoomRestRankConfig,
    KiwoomRestRankMode,
    KiwoomRestRankReadiness,
)


def kiwoom_rest_readonly_rank_payload(**overrides):
    payload = {
        "config_id": "kiwoom-rest-rank-1",
        "api_id": "KA10023",
        "available_at": "2026-06-25T15:35:00+09:00",
        "source_ref": "fixtures/kiwoom/readonly_rank_fixture.json",
        "mrkt_tp": "000",
        "sort_tp": "1",
        "tm_tp": "1",
        "trde_qty_tp": "10",
        "tm": "5",
        "stk_cnd": "3",
        "pric_tp": "0",
        "stex_tp": "3",
        "mocked_response_payload": {
            "return_code": 0,
            "return_msg": "정상적으로 처리되었습니다",
            "vol_surge_rank": [
                {
                    "stk_cd": "005930",
                    "stk_nm": "삼성전자",
                    "now_rank": "1",
                    "pred_rank": "2",
                    "flu_rt": "+5.25",
                    "cur_prc": "+78800",
                    "pred_pre": "+3900",
                    "trde_qty": "1234567",
                    "trde_prica": "45678900000",
                    "dt": "20260625",
                    "tm": "153000",
                }
            ],
            "cont_yn": "N",
            "next_key": "",
        },
        "safety_report": {
            "safety_report_id": "kiwoom-rest-rank-safety-1",
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
                "audit_record_id": "kiwoom-rest-rank-audit-1",
                "created_at": "2026-06-25T15:36:00+09:00",
                "source_path": "fixtures/kiwoom/readonly_rank_fixture.json",
                "operator_context": "offline kiwoom readonly rank review",
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
    loaded = KiwoomRestRankConfig.model_validate(kiwoom_rest_readonly_rank_payload())
    assert loaded.mode == KiwoomRestRankMode.MOCKED_TRANSPORT_ONLY
    assert loaded.report_only is True
    assert loaded.no_network is True


def test_guard_rejects_raw_token_secret_account_markers():
    with pytest.raises(ValueError):
        validate_kiwoom_rest_rank_metadata_safety({"authorization": "Bearer raw-token"}, context="kiwoom rank")
    with pytest.raises(ValueError):
        validate_kiwoom_rest_rank_metadata_safety({"account_no": "123-45"}, context="kiwoom rank")


def test_fixture_loader_reads_local_json_only(tmp_path):
    fixture_path = tmp_path / "kiwoom_readonly_rank.json"
    fixture_path.write_text(json.dumps(kiwoom_rest_readonly_rank_payload()), encoding="utf-8")
    loaded = load_kiwoom_rest_readonly_rank_fixture(fixture_path)
    assert isinstance(loaded, KiwoomRestRankConfig)
    assert loaded.local_file_only is True


def test_fixture_loader_rejects_remote_or_parquet(tmp_path):
    with pytest.raises(ValueError, match="local file path"):
        load_kiwoom_rest_readonly_rank_fixture("https://example.com/rank.json")
    with pytest.raises(ValueError, match="parquet remains unsupported"):
        load_kiwoom_rest_readonly_rank_fixture(tmp_path / "rank.parquet")


def test_api_and_readiness_enums_surface_expected_values():
    assert KiwoomRestRankApiId.KA00198.value == "KA00198"
    assert KiwoomRestRankApiId.KA10098.value == "KA10098"
    assert KiwoomRestRankReadiness.READONLY_ADAPTER_READY.value == "READONLY_ADAPTER_READY"
