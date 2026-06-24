import json

import pytest

from stock_risk_mcp.kiwoom_rest_readonly_chart_fixture import load_kiwoom_rest_readonly_chart_fixture
from stock_risk_mcp.kiwoom_rest_readonly_chart_guard import validate_kiwoom_rest_chart_metadata_safety
from stock_risk_mcp.kiwoom_rest_readonly_chart_models import (
    KiwoomRestChartApiId,
    KiwoomRestChartConfig,
    KiwoomRestChartMode,
    KiwoomRestChartReadiness,
)


def kiwoom_rest_readonly_chart_payload(**overrides):
    payload = {
        "config_id": "kiwoom-rest-chart-1",
        "api_id": "KA10081",
        "provider_symbol": "005930",
        "canonical_instrument_key": "005930_KRX",
        "base_dt": "20260202",
        "upd_stkpc_tp": "1",
        "available_at": "2026-02-02T15:35:00+09:00",
        "source_ref": "fixtures/kiwoom/readonly_chart_fixture.json",
        "mocked_response_payload": {
            "stk_cd": "005930",
            "stk_day_pole_chart_qry": [
                {
                    "cur_prc": "-78800",
                    "trde_qty": "7913",
                    "cntr_tm": "20260202153000",
                    "open_pric": "-78850",
                    "high_pric": "-78900",
                    "low_pric": "-78800",
                    "acc_trde_qty": "14947571",
                    "pred_pre": "-600",
                    "pred_pre_sig": "5",
                }
            ],
            "return_code": 0,
            "return_msg": "정상적으로 처리되었습니다",
            "cont_yn": "N",
            "next_key": "",
        },
        "safety_report": {
            "safety_report_id": "kiwoom-rest-chart-safety-1",
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
                "audit_record_id": "kiwoom-rest-chart-audit-1",
                "created_at": "2026-02-02T15:36:00+09:00",
                "source_path": "fixtures/kiwoom/readonly_chart_fixture.json",
                "operator_context": "offline kiwoom readonly chart review",
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
    loaded = KiwoomRestChartConfig.model_validate(kiwoom_rest_readonly_chart_payload())
    assert loaded.mode == KiwoomRestChartMode.MOCKED_TRANSPORT_ONLY
    assert loaded.report_only is True
    assert loaded.no_network is True


def test_guard_rejects_raw_token_secret_account_markers():
    with pytest.raises(ValueError):
        validate_kiwoom_rest_chart_metadata_safety({"authorization": "Bearer raw-token"}, context="kiwoom chart")
    with pytest.raises(ValueError):
        validate_kiwoom_rest_chart_metadata_safety({"account_no": "123-45"}, context="kiwoom chart")


def test_fixture_loader_reads_local_json_only(tmp_path):
    fixture_path = tmp_path / "kiwoom_readonly_chart.json"
    fixture_path.write_text(json.dumps(kiwoom_rest_readonly_chart_payload()), encoding="utf-8")
    loaded = load_kiwoom_rest_readonly_chart_fixture(fixture_path)
    assert isinstance(loaded, KiwoomRestChartConfig)
    assert loaded.local_file_only is True


def test_fixture_loader_rejects_remote_or_parquet(tmp_path):
    with pytest.raises(ValueError, match="local file path"):
        load_kiwoom_rest_readonly_chart_fixture("https://example.com/chart.json")
    with pytest.raises(ValueError, match="parquet remains unsupported"):
        load_kiwoom_rest_readonly_chart_fixture(tmp_path / "chart.parquet")


def test_api_and_readiness_enums_surface_expected_values():
    assert KiwoomRestChartApiId.KA10080.value == "KA10080"
    assert KiwoomRestChartReadiness.READONLY_ADAPTER_READY.value == "READONLY_ADAPTER_READY"
