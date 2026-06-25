import json

import pytest

from stock_risk_mcp.kiwoom_rest_readonly_flow_fixture import load_kiwoom_rest_readonly_flow_fixture
from stock_risk_mcp.kiwoom_rest_readonly_flow_guard import validate_kiwoom_rest_flow_metadata_safety
from stock_risk_mcp.kiwoom_rest_readonly_flow_models import (
    KiwoomRestFlowApiId,
    KiwoomRestFlowConfig,
    KiwoomRestFlowMode,
    KiwoomRestFlowReadiness,
)


def kiwoom_rest_readonly_flow_payload(**overrides):
    payload = {
        "config_id": "kiwoom-rest-flow-1",
        "api_id": "KA10059",
        "provider_symbol": "005930",
        "request_date": "20260202",
        "amt_qty_tp": "1",
        "trde_tp": "0",
        "unit_tp": "1",
        "available_at": "2026-02-02T15:35:00+09:00",
        "source_ref": "fixtures/kiwoom/readonly_flow_fixture.json",
        "mocked_response_payload": {
            "return_code": 0,
            "return_msg": "정상적으로 처리되었습니다",
            "stk_invsr_orgn": [
                {
                    "dt": "20260202",
                    "stk_cd": "005930",
                    "stk_nm": "삼성전자",
                    "cur_prc": "+78800",
                    "pred_pre": "+3900",
                    "frgnr_net_amt": "+120000000",
                    "orgn_net_amt": "-50000000",
                    "retl_net_amt": "-70000000",
                    "frgnr_net_qty": "+1500",
                    "orgn_net_qty": "-700",
                    "retl_net_qty": "-800",
                }
            ],
            "cont_yn": "N",
            "next_key": "",
        },
        "safety_report": {
            "safety_report_id": "kiwoom-rest-flow-safety-1",
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
                "audit_record_id": "kiwoom-rest-flow-audit-1",
                "created_at": "2026-02-02T15:36:00+09:00",
                "source_path": "fixtures/kiwoom/readonly_flow_fixture.json",
                "operator_context": "offline kiwoom readonly flow review",
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
    loaded = KiwoomRestFlowConfig.model_validate(kiwoom_rest_readonly_flow_payload())
    assert loaded.mode == KiwoomRestFlowMode.MOCKED_TRANSPORT_ONLY
    assert loaded.report_only is True
    assert loaded.no_network is True


def test_guard_rejects_raw_token_secret_account_markers():
    with pytest.raises(ValueError):
        validate_kiwoom_rest_flow_metadata_safety({"authorization": "Bearer raw-token"}, context="kiwoom flow")
    with pytest.raises(ValueError):
        validate_kiwoom_rest_flow_metadata_safety({"account_no": "123-45"}, context="kiwoom flow")


def test_fixture_loader_reads_local_json_only(tmp_path):
    fixture_path = tmp_path / "kiwoom_readonly_flow.json"
    fixture_path.write_text(json.dumps(kiwoom_rest_readonly_flow_payload()), encoding="utf-8")
    loaded = load_kiwoom_rest_readonly_flow_fixture(fixture_path)
    assert isinstance(loaded, KiwoomRestFlowConfig)
    assert loaded.local_file_only is True


def test_fixture_loader_rejects_remote_or_parquet(tmp_path):
    with pytest.raises(ValueError, match="local file path"):
        load_kiwoom_rest_readonly_flow_fixture("https://example.com/flow.json")
    with pytest.raises(ValueError, match="parquet remains unsupported"):
        load_kiwoom_rest_readonly_flow_fixture(tmp_path / "flow.parquet")


def test_api_and_readiness_enums_surface_expected_values():
    assert KiwoomRestFlowApiId.KA10059.value == "KA10059"
    assert KiwoomRestFlowApiId.KA90013.value == "KA90013"
    assert KiwoomRestFlowReadiness.READONLY_ADAPTER_READY.value == "READONLY_ADAPTER_READY"
