import pytest

from stock_risk_mcp.kiwoom_rest_readonly_chart_engine import (
    build_kiwoom_rest_daily_chart_request,
    build_kiwoom_rest_minute_chart_request,
    build_kiwoom_rest_readonly_chart_adapter,
)
from stock_risk_mcp.kiwoom_rest_readonly_chart_models import (
    KiwoomRestChartApiId,
    KiwoomRestChartConfig,
    KiwoomRestChartReadiness,
)
from tests.test_kiwoom_rest_readonly_chart_models import kiwoom_rest_readonly_chart_payload


def _config(**overrides):
    payload = kiwoom_rest_readonly_chart_payload()
    payload.update(overrides)
    return KiwoomRestChartConfig.model_validate(payload)


def test_ka10081_daily_chart_request_is_built_with_correct_shape():
    request = build_kiwoom_rest_daily_chart_request(_config(api_id="KA10081"))
    assert request.path == "/api/dostk/chart"
    assert request.request_headers["api-id"] == "ka10081"
    assert request.request_headers["authorization"] == "Bearer <TOKEN_REF_ONLY>"
    assert request.request_body == {"stk_cd": "005930", "base_dt": "20260202", "upd_stkpc_tp": "1"}


def test_ka10080_minute_chart_request_is_built_with_correct_shape():
    request = build_kiwoom_rest_minute_chart_request(
        _config(
            api_id="KA10080",
            tic_scope="1",
            mocked_response_payload={
                "stk_cd": "005930",
                "stk_min_pole_chart_qry": [],
                "return_code": 0,
                "return_msg": "정상적으로 처리되었습니다",
            },
        )
    )
    assert request.request_headers["api-id"] == "ka10080"
    assert request.request_body["tic_scope"] == "1"


def test_mocked_daily_response_parses_into_canonical_ohlcv_records():
    result = build_kiwoom_rest_readonly_chart_adapter(_config())
    record = result.canonical_ohlcv_report.records[0]
    assert record.provider_api_id == "KA10081"
    assert record.close == -78800.0
    assert record.available_at is not None


def test_mocked_minute_response_parses_into_canonical_ohlcv_records():
    result = build_kiwoom_rest_readonly_chart_adapter(
        _config(
            api_id="KA10080",
            tic_scope="1",
            mocked_response_payload={
                "stk_cd": "005930",
                "stk_min_pole_chart_qry": [
                    {
                        "cur_prc": "+70700",
                        "trde_qty": "123",
                        "cntr_tm": "20260202100100",
                        "open_pric": "+70600",
                        "high_pric": "+70800",
                        "low_pric": "+70500",
                    }
                ],
                "return_code": 0,
                "return_msg": "정상적으로 처리되었습니다",
                "cont_yn": "Y",
                "next_key": "PAGE2",
            },
        )
    )
    record = result.canonical_ohlcv_report.records[0]
    assert record.provider_api_id == "KA10080"
    assert record.timeframe == "1M"
    assert result.continuation_report.has_more is True


def test_signed_numeric_strings_are_normalized_safely():
    result = build_kiwoom_rest_readonly_chart_adapter(_config())
    record = result.canonical_ohlcv_report.records[0]
    assert record.open == -78850.0
    assert record.high == -78900.0


def test_return_code_nonzero_creates_data_gap():
    result = build_kiwoom_rest_readonly_chart_adapter(
        _config(mocked_response_payload={"stk_cd": "005930", "return_code": 100, "return_msg": "에러", "stk_day_pole_chart_qry": []})
    )
    assert result.summary_report.readiness == KiwoomRestChartReadiness.DATA_GAP


def test_malformed_response_creates_schema_gap():
    result = build_kiwoom_rest_readonly_chart_adapter(_config(mocked_response_payload={"stk_cd": "005930"}))
    assert result.summary_report.readiness == KiwoomRestChartReadiness.SCHEMA_GAP


def test_real_network_transport_attempt_is_blocked():
    result = build_kiwoom_rest_readonly_chart_adapter(_config(mocked_response_payload=None))
    assert result.summary_report.readiness == KiwoomRestChartReadiness.BLOCKED


def test_missing_available_at_creates_data_gap():
    result = build_kiwoom_rest_readonly_chart_adapter(_config(available_at=None))
    assert result.summary_report.readiness == KiwoomRestChartReadiness.DATA_GAP


def test_no_executable_order_output_is_produced_and_audit_is_redacted():
    result = build_kiwoom_rest_readonly_chart_adapter(_config())
    dumped = result.model_dump_json()
    assert "order_id" not in dumped.lower()
    assert result.audit_records[0].redaction_applied is True
