import pytest

from stock_risk_mcp.kiwoom_rest_readonly_quote_engine import (
    build_kiwoom_rest_basic_info_request,
    build_kiwoom_rest_execution_info_request,
    build_kiwoom_rest_quote_orderbook_request,
    build_kiwoom_rest_readonly_quote_adapter,
)
from stock_risk_mcp.kiwoom_rest_readonly_quote_models import (
    KiwoomRestQuoteConfig,
    KiwoomRestQuoteReadiness,
)
from tests.test_kiwoom_rest_readonly_quote_models import kiwoom_rest_readonly_quote_payload


def _config(**overrides):
    payload = kiwoom_rest_readonly_quote_payload()
    payload.update(overrides)
    return KiwoomRestQuoteConfig.model_validate(payload)


def test_ka10004_request_is_built_with_correct_shape():
    request = build_kiwoom_rest_quote_orderbook_request(_config())
    assert request.path == "/api/dostk/mrkcond"
    assert request.request_headers["api-id"] == "ka10004"
    assert request.request_headers["authorization"] == "Bearer <TOKEN_REF_ONLY>"
    assert request.request_body == {"stk_cd": "005930"}


def test_ka10003_request_is_built_with_correct_shape():
    request = build_kiwoom_rest_execution_info_request(
        _config(
            api_id="KA10003",
            mocked_response_payload={
                "stk_cd": "005930",
                "return_code": 0,
                "return_msg": "정상적으로 처리되었습니다",
                "cntr_infr": [],
            },
        )
    )
    assert request.path == "/api/dostk/stkinfo"
    assert request.request_headers["api-id"] == "ka10003"
    assert request.request_body == {"stk_cd": "005930"}


def test_ka10001_basic_info_request_is_built_safely():
    request = build_kiwoom_rest_basic_info_request(
        _config(
            api_id="KA10001",
            mocked_response_payload={
                "stk_cd": "005930",
                "return_code": 0,
                "return_msg": "정상적으로 처리되었습니다",
            },
        )
    )
    assert request.request_headers["api-id"] == "ka10001"
    assert request.request_body == {"stk_cd": "005930"}


def test_mocked_ka10004_response_parses_into_canonical_quote_orderbook_records():
    result = build_kiwoom_rest_readonly_quote_adapter(_config())
    quote = result.canonical_quote_report.records[0]
    orderbook = result.canonical_orderbook_report.records[0]
    assert quote.provider_api_id == "KA10004"
    assert quote.bid_price == 78800.0
    assert quote.ask_price == 78810.0
    assert orderbook.depth_summary_quantity == 4400.0


def test_mocked_ka10003_response_parses_into_execution_liquidity_records():
    result = build_kiwoom_rest_readonly_quote_adapter(
        _config(
            api_id="KA10003",
            mocked_response_payload={
                "stk_cd": "005930",
                "stk_nm": "삼성전자",
                "return_code": 0,
                "return_msg": "정상적으로 처리되었습니다",
                "cntr_infr": [
                    {
                        "tm": "153000",
                        "cur_prc": "+78800",
                        "pred_pre": "+3900",
                        "pre_rt": "+5.21",
                        "pri_sel_bid_unit": "+78810",
                        "pri_buy_bid_unit": "+78800",
                        "cntr_trde_qty": "250",
                        "sign": "2",
                    }
                ],
            },
        )
    )
    quote = result.canonical_quote_report.records[0]
    hint = result.liquidity_hint_report.records[0]
    assert quote.last_price == 78800.0
    assert quote.last_trade_quantity == 250.0
    assert hint.price_liquidity_ready is True


def test_mocked_ka10001_response_parses_available_metadata_without_inventing_missing_fields():
    result = build_kiwoom_rest_readonly_quote_adapter(
        _config(
            api_id="KA10001",
            mocked_response_payload={
                "stk_cd": "005930",
                "stk_nm": "삼성전자",
                "setl_mm": "12",
                "fav": "100",
                "flo_stk": "5969782550",
                "return_code": 0,
                "return_msg": "정상적으로 처리되었습니다",
            },
        )
    )
    info = result.basic_info_report.records[0]
    assert info.stock_name == "삼성전자"
    assert info.face_value == 100.0
    assert info.market_cap is None


def test_signed_numeric_strings_are_normalized_safely():
    result = build_kiwoom_rest_readonly_quote_adapter(_config())
    quote = result.canonical_quote_report.records[0]
    assert quote.bid_price == 78800.0
    assert quote.ask_price == 78810.0


def test_blank_malformed_numeric_creates_schema_gap_not_crash():
    result = build_kiwoom_rest_readonly_quote_adapter(_config(mocked_response_payload={**kiwoom_rest_readonly_quote_payload()["mocked_response_payload"], "ask_price_1": "abc"}))
    assert result.summary_report.readiness == KiwoomRestQuoteReadiness.SCHEMA_GAP


def test_spread_and_mid_price_are_computed_when_bid_ask_exist():
    result = build_kiwoom_rest_readonly_quote_adapter(_config())
    quote = result.canonical_quote_report.records[0]
    assert quote.spread == 10.0
    assert quote.mid_price == 78805.0


def test_liquidity_hint_is_produced_when_orderbook_evidence_exists():
    result = build_kiwoom_rest_readonly_quote_adapter(_config())
    hint = result.liquidity_hint_report.records[0]
    assert hint.outlier_routing_ready is True


def test_missing_bid_ask_creates_gap_note_not_crash():
    result = build_kiwoom_rest_readonly_quote_adapter(
        _config(
            mocked_response_payload={
                "stk_cd": "005930",
                "return_code": 0,
                "return_msg": "정상적으로 처리되었습니다",
                "bid_req_base_tm": "153000",
            }
        )
    )
    assert result.canonical_quote_report.records[0].gap_reason == "BID_ASK_UNAVAILABLE"


def test_return_code_nonzero_creates_data_gap():
    result = build_kiwoom_rest_readonly_quote_adapter(
        _config(mocked_response_payload={"stk_cd": "005930", "return_code": 100, "return_msg": "에러"})
    )
    assert result.summary_report.readiness == KiwoomRestQuoteReadiness.DATA_GAP


def test_malformed_response_creates_schema_gap():
    result = build_kiwoom_rest_readonly_quote_adapter(_config(mocked_response_payload={"stk_cd": "005930"}))
    assert result.summary_report.readiness == KiwoomRestQuoteReadiness.SCHEMA_GAP


def test_continuation_is_represented():
    result = build_kiwoom_rest_readonly_quote_adapter(
        _config(mocked_response_payload={**kiwoom_rest_readonly_quote_payload()["mocked_response_payload"], "cont_yn": "Y", "next_key": "PAGE2"})
    )
    assert result.continuation_report.has_more is True


def test_real_network_transport_attempt_is_blocked():
    result = build_kiwoom_rest_readonly_quote_adapter(_config(mocked_response_payload=None))
    assert result.summary_report.readiness == KiwoomRestQuoteReadiness.BLOCKED


def test_missing_available_at_creates_data_gap():
    result = build_kiwoom_rest_readonly_quote_adapter(_config(available_at=None))
    assert result.summary_report.readiness == KiwoomRestQuoteReadiness.DATA_GAP


def test_v7_integration_report_sees_quote_liquidity_readiness():
    result = build_kiwoom_rest_readonly_quote_adapter(_config())
    assert result.v7_integration_report.v710_price_liquidity_ready is True
    assert result.v7_integration_report.v712_liquidity_outlier_ready is True


def test_no_executable_order_output_is_produced_and_audit_is_redacted():
    result = build_kiwoom_rest_readonly_quote_adapter(_config())
    dumped = result.model_dump_json()
    assert "order_id" not in dumped.lower()
    assert result.audit_records[0].redaction_applied is True
