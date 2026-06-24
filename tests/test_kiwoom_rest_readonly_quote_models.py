import json

import pytest

from stock_risk_mcp.kiwoom_rest_readonly_quote_fixture import load_kiwoom_rest_readonly_quote_fixture
from stock_risk_mcp.kiwoom_rest_readonly_quote_guard import validate_kiwoom_rest_quote_metadata_safety
from stock_risk_mcp.kiwoom_rest_readonly_quote_models import (
    KiwoomRestQuoteApiId,
    KiwoomRestQuoteConfig,
    KiwoomRestQuoteMode,
    KiwoomRestQuoteReadiness,
)


def kiwoom_rest_readonly_quote_payload(**overrides):
    payload = {
        "config_id": "kiwoom-rest-quote-1",
        "api_id": "KA10004",
        "provider_symbol": "005930",
        "available_at": "2026-06-25T15:35:00+09:00",
        "request_date": "20260625",
        "source_ref": "fixtures/kiwoom/readonly_quote_fixture.json",
        "mocked_response_payload": {
            "stk_cd": "005930",
            "stk_nm": "삼성전자",
            "return_code": 0,
            "return_msg": "정상적으로 처리되었습니다",
            "bid_req_base_tm": "153000",
            "ask_price_1": "+78810",
            "ask_qty_1": "1200",
            "bid_price_1": "+78800",
            "bid_qty_1": "1500",
            "ask_price_2": "+78820",
            "ask_qty_2": "900",
            "bid_price_2": "+78790",
            "bid_qty_2": "800",
            "cont_yn": "N",
            "next_key": "",
        },
        "safety_report": {
            "safety_report_id": "kiwoom-rest-quote-safety-1",
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
                "audit_record_id": "kiwoom-rest-quote-audit-1",
                "created_at": "2026-06-25T15:36:00+09:00",
                "source_path": "fixtures/kiwoom/readonly_quote_fixture.json",
                "operator_context": "offline kiwoom readonly quote review",
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
    loaded = KiwoomRestQuoteConfig.model_validate(kiwoom_rest_readonly_quote_payload())
    assert loaded.mode == KiwoomRestQuoteMode.MOCKED_TRANSPORT_ONLY
    assert loaded.report_only is True
    assert loaded.no_network is True


def test_guard_rejects_raw_token_secret_account_markers():
    with pytest.raises(ValueError):
        validate_kiwoom_rest_quote_metadata_safety({"authorization": "Bearer raw-token"}, context="kiwoom quote")
    with pytest.raises(ValueError):
        validate_kiwoom_rest_quote_metadata_safety({"account_no": "123-45"}, context="kiwoom quote")


def test_fixture_loader_reads_local_json_only(tmp_path):
    fixture_path = tmp_path / "kiwoom_readonly_quote.json"
    fixture_path.write_text(json.dumps(kiwoom_rest_readonly_quote_payload()), encoding="utf-8")
    loaded = load_kiwoom_rest_readonly_quote_fixture(fixture_path)
    assert isinstance(loaded, KiwoomRestQuoteConfig)
    assert loaded.local_file_only is True


def test_fixture_loader_rejects_remote_or_parquet(tmp_path):
    with pytest.raises(ValueError, match="local file path"):
        load_kiwoom_rest_readonly_quote_fixture("https://example.com/quote.json")
    with pytest.raises(ValueError, match="parquet remains unsupported"):
        load_kiwoom_rest_readonly_quote_fixture(tmp_path / "quote.parquet")


def test_api_and_readiness_enums_surface_expected_values():
    assert KiwoomRestQuoteApiId.KA10004.value == "KA10004"
    assert KiwoomRestQuoteApiId.KA10001.value == "KA10001"
    assert KiwoomRestQuoteReadiness.READONLY_ADAPTER_READY.value == "READONLY_ADAPTER_READY"
