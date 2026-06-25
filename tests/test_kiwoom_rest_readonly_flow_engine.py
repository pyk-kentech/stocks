import pytest

from stock_risk_mcp.kiwoom_rest_readonly_flow_engine import (
    build_kiwoom_rest_investor_flow_request,
    build_kiwoom_rest_program_flow_request,
    build_kiwoom_rest_readonly_flow_adapter,
)
from stock_risk_mcp.kiwoom_rest_readonly_flow_models import KiwoomRestFlowConfig, KiwoomRestFlowReadiness
from tests.test_kiwoom_rest_readonly_flow_models import kiwoom_rest_readonly_flow_payload


def _config(**overrides):
    payload = kiwoom_rest_readonly_flow_payload()
    payload.update(overrides)
    return KiwoomRestFlowConfig.model_validate(payload)


def test_ka10059_request_is_built_with_correct_shape():
    request = build_kiwoom_rest_investor_flow_request(_config())
    assert request.path == "/api/dostk/stkinfo"
    assert request.request_headers["api-id"] == "ka10059"
    assert request.request_headers["authorization"] == "Bearer <TOKEN_REF_ONLY>"
    assert request.request_body == {"dt": "20260202", "stk_cd": "005930", "amt_qty_tp": "1", "trde_tp": "0", "unit_tp": "1"}


def test_ka90003_request_is_schema_gap_without_path_evidence():
    result = build_kiwoom_rest_readonly_flow_adapter(
        _config(
            api_id="KA90003",
            trde_upper_tp="1",
            mrkt_tp="P00101",
            stex_tp="1",
            mocked_response_payload={"return_code": 0, "return_msg": "정상적으로 처리되었습니다", "program_net_buy_top50": []},
        )
    )
    assert result.summary_report.readiness == KiwoomRestFlowReadiness.SCHEMA_GAP


def test_ka90003_request_is_built_when_path_evidence_is_present():
    request = build_kiwoom_rest_program_flow_request(
        _config(
            api_id="KA90003",
            path_hint="/api/dostk/program",
            trde_upper_tp="1",
            mrkt_tp="P00101",
            stex_tp="1",
            mocked_response_payload={"return_code": 0, "return_msg": "정상적으로 처리되었습니다", "program_net_buy_top50": []},
        )
    )
    assert request.path == "/api/dostk/program"
    assert request.request_headers["api-id"] == "ka90003"


def test_mocked_ka10059_response_parses_into_canonical_investor_flow_signals():
    result = build_kiwoom_rest_readonly_flow_adapter(_config())
    signals = result.canonical_investor_flow_report.signals
    assert {signal.flow_category.value for signal in signals} == {"FOREIGN", "INSTITUTION", "RETAIL"}
    assert signals[0].provider_api_id == "KA10059"


def test_mocked_ka90003_response_parses_into_canonical_program_flow_signals_if_builder_ready():
    result = build_kiwoom_rest_readonly_flow_adapter(
        _config(
            api_id="KA90003",
            path_hint="/api/dostk/program",
            trde_upper_tp="1",
            mrkt_tp="P00101",
            stex_tp="1",
            mocked_response_payload={
                "return_code": 0,
                "return_msg": "정상적으로 처리되었습니다",
                "program_net_buy_top50": [
                    {
                        "stk_cd": "005930",
                        "stk_nm": "삼성전자",
                        "acc_trde_qty": "12000",
                        "prm_sell_amt": "-30000000",
                        "prm_buy_amt": "+80000000",
                        "prm_netprps_amt": "+50000000",
                    }
                ],
            },
        )
    )
    assert result.canonical_program_flow_report.signals[0].program_net_amount == 50000000.0


def test_flow_short_program_capability_matrix_includes_expected_api_ids():
    result = build_kiwoom_rest_readonly_flow_adapter(_config())
    api_ids = {entry["api_id"] for entry in result.flow_capability_matrix_report.model_dump(mode="json")["entries"]}
    assert {"KA10008", "KA10014", "KA10058", "KA10059", "KA10060", "KA10061", "KA10063", "KA10064", "KA10065", "KA10066", "KA10068", "KA10069", "KA90003", "KA90004", "KA90005", "KA90007", "KA90008", "KA90009", "KA90010", "KA90012", "KA90013"} <= api_ids


def test_apis_without_exact_schema_are_not_request_builder_ready():
    result = build_kiwoom_rest_readonly_flow_adapter(_config())
    matrix = {entry.api_id.value: entry for entry in result.flow_capability_matrix_report.entries}
    assert matrix["KA10014"].request_builder_ready is False
    assert matrix["KA10014"].readiness == KiwoomRestFlowReadiness.FUTURE_SUPPORTED
    assert matrix["KA90003"].request_builder_ready is False
    assert matrix["KA90003"].readiness == KiwoomRestFlowReadiness.SCHEMA_GAP


def test_signed_numeric_strings_are_normalized_safely():
    result = build_kiwoom_rest_readonly_flow_adapter(_config())
    foreign_signal = next(signal for signal in result.canonical_investor_flow_report.signals if signal.flow_category.value == "FOREIGN")
    assert foreign_signal.net_buy_amount == 120000000.0
    assert foreign_signal.net_buy_quantity == 1500.0


def test_blank_malformed_numeric_creates_schema_gap_not_crash():
    result = build_kiwoom_rest_readonly_flow_adapter(
        _config(mocked_response_payload={"return_code": 0, "return_msg": "정상적으로 처리되었습니다", "stk_invsr_orgn": [{"dt": "20260202", "stk_cd": "005930", "frgnr_net_amt": "abc"}]})
    )
    assert result.summary_report.readiness == KiwoomRestFlowReadiness.SCHEMA_GAP


def test_return_code_nonzero_creates_data_gap():
    result = build_kiwoom_rest_readonly_flow_adapter(_config(mocked_response_payload={"return_code": 100, "return_msg": "에러"}))
    assert result.summary_report.readiness == KiwoomRestFlowReadiness.DATA_GAP


def test_malformed_response_creates_schema_gap():
    result = build_kiwoom_rest_readonly_flow_adapter(_config(mocked_response_payload={"return_code": 0}))
    assert result.summary_report.readiness == KiwoomRestFlowReadiness.SCHEMA_GAP


def test_continuation_is_represented():
    result = build_kiwoom_rest_readonly_flow_adapter(
        _config(mocked_response_payload={**kiwoom_rest_readonly_flow_payload()["mocked_response_payload"], "cont_yn": "Y", "next_key": "PAGE2"})
    )
    assert result.continuation_report.has_more is True


def test_real_network_transport_attempt_is_blocked():
    result = build_kiwoom_rest_readonly_flow_adapter(_config(mocked_response_payload=None))
    assert result.summary_report.readiness == KiwoomRestFlowReadiness.BLOCKED


def test_missing_available_at_creates_data_gap():
    result = build_kiwoom_rest_readonly_flow_adapter(_config(available_at=None))
    assert result.summary_report.readiness == KiwoomRestFlowReadiness.DATA_GAP


def test_v7_integration_report_sees_flow_program_readiness():
    result = build_kiwoom_rest_readonly_flow_adapter(_config())
    assert result.v7_integration_report.v712_flow_program_ready is True
    assert result.v7_integration_report.v710_risk_liquidity_hints_ready is True


def test_no_executable_order_output_is_produced_and_audit_is_redacted():
    result = build_kiwoom_rest_readonly_flow_adapter(_config())
    dumped = result.model_dump_json()
    assert "order_id" not in dumped.lower()
    assert result.audit_records[0].redaction_applied is True
