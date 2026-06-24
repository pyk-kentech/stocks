import pytest

from stock_risk_mcp.kiwoom_rest_readonly_rank_engine import (
    build_kiwoom_rest_readonly_rank_adapter,
    build_kiwoom_rest_realtime_inquiry_rank_request,
    build_kiwoom_rest_today_volume_rank_request,
    build_kiwoom_rest_trading_value_rank_request,
    build_kiwoom_rest_volume_surge_rank_request,
)
from stock_risk_mcp.kiwoom_rest_readonly_rank_models import (
    KiwoomRestRankConfig,
    KiwoomRestRankReadiness,
)
from tests.test_kiwoom_rest_readonly_rank_models import kiwoom_rest_readonly_rank_payload


def _config(**overrides):
    payload = kiwoom_rest_readonly_rank_payload()
    payload.update(overrides)
    return KiwoomRestRankConfig.model_validate(payload)


def test_ka00198_request_is_built_with_correct_shape():
    request = build_kiwoom_rest_realtime_inquiry_rank_request(
        _config(
            api_id="KA00198",
            qry_tp="1",
            mocked_response_payload={
                "return_code": 0,
                "return_msg": "정상적으로 처리되었습니다",
                "item_inq_rank": [],
            },
        )
    )
    assert request.path == "/api/dostk/stkinfo"
    assert request.request_headers["api-id"] == "ka00198"
    assert request.request_headers["authorization"] == "Bearer <TOKEN_REF_ONLY>"
    assert request.request_body == {"qry_tp": "1"}


def test_ka10023_request_is_built_with_correct_shape():
    request = build_kiwoom_rest_volume_surge_rank_request(_config())
    assert request.path == "/api/dostk/rkinfo"
    assert request.request_headers["api-id"] == "ka10023"
    assert request.request_body["tm"] == "5"


def test_ka10030_request_is_built_with_correct_shape():
    request = build_kiwoom_rest_today_volume_rank_request(
        _config(
            api_id="KA10030",
            sort_tp="1",
            mang_stk_incls="1",
            crd_tp="0",
            mocked_response_payload={
                "return_code": 0,
                "return_msg": "정상적으로 처리되었습니다",
                "trde_qty_upper": [],
            },
        )
    )
    assert request.request_headers["api-id"] == "ka10030"
    assert request.request_body["mang_stk_incls"] == "1"


def test_ka10032_request_is_built_with_correct_shape():
    request = build_kiwoom_rest_trading_value_rank_request(
        _config(
            api_id="KA10032",
            mang_stk_incls="0",
            mocked_response_payload={
                "return_code": 0,
                "return_msg": "정상적으로 처리되었습니다",
                "trde_prica_upper": [],
            },
        )
    )
    assert request.request_headers["api-id"] == "ka10032"
    assert request.request_body == {"mrkt_tp": "000", "mang_stk_incls": "0", "stex_tp": "3"}


def test_mocked_ka00198_response_parses_into_canonical_rank_signals():
    result = build_kiwoom_rest_readonly_rank_adapter(
        _config(
            api_id="KA00198",
            qry_tp="1",
            mocked_response_payload={
                "return_code": 0,
                "return_msg": "정상적으로 처리되었습니다",
                "item_inq_rank": [
                    {
                        "stk_cd": "005930",
                        "stk_nm": "삼성전자",
                        "bigd_rank": "1",
                        "rank_chg": "-2",
                        "rank_chg_sign": "2",
                        "past_curr_prc": "+78800",
                        "base_comp_chgr": "+2.50",
                        "pred_pre": "+1500",
                        "dt": "20260625",
                        "tm": "153000",
                    }
                ],
            },
        )
    )
    record = result.canonical_rank_report.signals[0]
    assert record.provider_api_id == "KA00198"
    assert record.rank == 1
    assert record.available_at is not None


def test_mocked_ka10023_response_parses_into_canonical_outlier_signals():
    result = build_kiwoom_rest_readonly_rank_adapter(_config())
    record = result.canonical_outlier_report.signals[0]
    assert record.provider_api_id == "KA10023"
    assert record.outlier_category.value == "VOLUME_SURGE"


def test_mocked_ka10030_response_parses_into_canonical_volume_rank_signals():
    result = build_kiwoom_rest_readonly_rank_adapter(
        _config(
            api_id="KA10030",
            mang_stk_incls="1",
            crd_tp="0",
            mocked_response_payload={
                "return_code": 0,
                "return_msg": "정상적으로 처리되었습니다",
                "trde_qty_upper": [
                    {
                        "stk_cd": "035420",
                        "stk_nm": "NAVER",
                        "now_rank": "3",
                        "pred_rank": "5",
                        "cur_prc": "+200000",
                        "pred_pre": "+5000",
                        "flu_rt": "+2.56",
                        "trde_qty": "987654",
                        "trde_prica": "21000000000",
                        "dt": "20260625",
                        "tm": "153000",
                    }
                ],
            },
        )
    )
    assert result.canonical_outlier_report.signals[0].outlier_category.value == "VOLUME_RANK"


def test_mocked_ka10032_response_parses_into_canonical_trading_value_rank_signals():
    result = build_kiwoom_rest_readonly_rank_adapter(
        _config(
            api_id="KA10032",
            mang_stk_incls="0",
            mocked_response_payload={
                "return_code": 0,
                "return_msg": "정상적으로 처리되었습니다",
                "trde_prica_upper": [
                    {
                        "stk_cd": "000660",
                        "stk_nm": "SK하이닉스",
                        "now_rank": "2",
                        "pred_rank": "3",
                        "cur_prc": "+240000",
                        "pred_pre": "+4000",
                        "flu_rt": "+1.69",
                        "trde_qty": "111111",
                        "trde_prica": "33300000000",
                        "dt": "20260625",
                        "tm": "153000",
                    }
                ],
            },
        )
    )
    assert result.canonical_outlier_report.signals[0].outlier_category.value == "TRADING_VALUE_RANK"


def test_signed_numeric_strings_are_normalized_safely():
    result = build_kiwoom_rest_readonly_rank_adapter(_config())
    record = result.canonical_outlier_report.signals[0]
    assert record.price == 78800.0
    assert record.price_change == 3900.0


def test_missing_relative_volume_creates_gap_note_not_crash():
    result = build_kiwoom_rest_readonly_rank_adapter(_config())
    assert result.canonical_outlier_report.signals[0].gap_reason == "RELATIVE_VOLUME_UNAVAILABLE"


def test_return_code_nonzero_creates_data_gap():
    result = build_kiwoom_rest_readonly_rank_adapter(
        _config(mocked_response_payload={"return_code": 100, "return_msg": "에러", "vol_surge_rank": []})
    )
    assert result.summary_report.readiness == KiwoomRestRankReadiness.DATA_GAP


def test_malformed_response_creates_schema_gap():
    result = build_kiwoom_rest_readonly_rank_adapter(_config(mocked_response_payload={"return_code": 0}))
    assert result.summary_report.readiness == KiwoomRestRankReadiness.SCHEMA_GAP


def test_continuation_is_represented():
    result = build_kiwoom_rest_readonly_rank_adapter(
        _config(mocked_response_payload={**kiwoom_rest_readonly_rank_payload()["mocked_response_payload"], "cont_yn": "Y", "next_key": "PAGE2"})
    )
    assert result.continuation_report.has_more is True


def test_future_supported_apis_are_reported_but_not_request_ready():
    result = build_kiwoom_rest_readonly_rank_adapter(_config(api_id="KA10019"))
    assert result.summary_report.readiness == KiwoomRestRankReadiness.SCHEMA_GAP
    assert "KA10019" in result.v7_integration_report.future_supported_api_ids
    assert "KA10019" not in result.v7_integration_report.request_builder_ready_api_ids


def test_real_network_transport_attempt_is_blocked():
    result = build_kiwoom_rest_readonly_rank_adapter(_config(mocked_response_payload=None))
    assert result.summary_report.readiness == KiwoomRestRankReadiness.BLOCKED


def test_missing_available_at_creates_data_gap():
    result = build_kiwoom_rest_readonly_rank_adapter(_config(available_at=None))
    assert result.summary_report.readiness == KiwoomRestRankReadiness.DATA_GAP


def test_v7_integration_report_sees_outlier_and_rank_readiness():
    result = build_kiwoom_rest_readonly_rank_adapter(_config())
    assert result.v7_integration_report.v712_breadth_routing_ready is True
    assert result.v7_integration_report.v710_price_liquidity_hints_ready is True


def test_no_executable_order_output_is_produced_and_audit_is_redacted():
    result = build_kiwoom_rest_readonly_rank_adapter(_config())
    dumped = result.model_dump_json()
    assert "order_id" not in dumped.lower()
    assert result.audit_records[0].redaction_applied is True
