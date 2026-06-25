import pytest

from stock_risk_mcp.kiwoom_rest_readonly_sector_engine import (
    build_kiwoom_rest_etf_daily_trend_request,
    build_kiwoom_rest_readonly_sector_adapter,
    build_kiwoom_rest_theme_component_request,
    build_kiwoom_rest_theme_group_request,
)
from stock_risk_mcp.kiwoom_rest_readonly_sector_models import (
    KiwoomRestSectorConfig,
    KiwoomRestSectorReadiness,
)
from tests.test_kiwoom_rest_readonly_sector_models import kiwoom_rest_readonly_sector_payload


def _config(**overrides):
    payload = kiwoom_rest_readonly_sector_payload()
    payload.update(overrides)
    return KiwoomRestSectorConfig.model_validate(payload)


def test_ka90001_request_is_built_with_correct_shape():
    request = build_kiwoom_rest_theme_group_request(_config())
    assert request.path == "/api/dostk/thme"
    assert request.request_headers["api-id"] == "ka90001"
    assert request.request_headers["authorization"] == "Bearer <TOKEN_REF_ONLY>"
    assert request.request_body == {"qry_tp": "0", "stk_cd": "", "date_tp": "10", "thema_nm": "", "flu_pl_amt_tp": "1", "stex_tp": "1"}


def test_ka90002_request_is_built_with_correct_shape():
    request = build_kiwoom_rest_theme_component_request(
        _config(
            api_id="KA90002",
            theme_group_code="553",
            mocked_response_payload={"return_code": 0, "return_msg": "정상적으로 처리되었습니다"},
        )
    )
    assert request.path == "/api/dostk/thme"
    assert request.request_headers["api-id"] == "ka90002"
    assert request.request_body == {"date_tp": "10", "thema_grp_cd": "553", "stex_tp": "1"}


def test_ka40003_request_is_built_with_correct_shape():
    request = build_kiwoom_rest_etf_daily_trend_request(
        _config(
            api_id="KA40003",
            provider_symbol="069500",
            mocked_response_payload={"return_code": 0, "return_msg": "정상적으로 처리되었습니다", "etfdaly_trnsn": []},
        )
    )
    assert request.path == "/api/dostk/etf"
    assert request.request_headers["api-id"] == "ka40003"
    assert request.request_body == {"stk_cd": "069500"}


def test_mocked_ka90001_response_parses_into_canonical_theme_leadership_signals():
    result = build_kiwoom_rest_readonly_sector_adapter(_config())
    signal = result.canonical_theme_leadership_report.signals[0]
    assert signal.theme_group_code == "553"
    assert signal.theme_name == "2차전지"
    assert signal.participation_hint == 0.75


def test_mocked_ka90002_response_parses_available_theme_membership_fields_gap_aware():
    result = build_kiwoom_rest_readonly_sector_adapter(
        _config(
            api_id="KA90002",
            theme_group_code="553",
            mocked_response_payload={
                "return_code": 0,
                "return_msg": "정상적으로 처리되었습니다",
                "thema_nm": "2차전지",
                "flu_rt": "+3.25",
                "dt_prft_rt": "+5.10",
            },
        )
    )
    signal = result.canonical_theme_membership_report.signals[0]
    assert signal.theme_group_code == "553"
    assert signal.membership_evidence_flag is False
    assert signal.gap_reason == "THEME_COMPONENT_FIELDS_PARTIAL"


def test_mocked_ka40003_response_parses_into_canonical_etf_trend_signals():
    result = build_kiwoom_rest_readonly_sector_adapter(
        _config(
            api_id="KA40003",
            provider_symbol="069500",
            mocked_response_payload={
                "return_code": 0,
                "return_msg": "정상적으로 처리되었습니다",
                "etfdaly_trnsn": [
                    {"cntr_dt": "20260625", "cur_prc": "+157.80", "pred_pre": "+1.25", "pre_rt": "+0.80"}
                ],
            },
        )
    )
    signal = result.canonical_etf_trend_report.signals[0]
    assert signal.etf_stock_code == "069500"
    assert signal.trend_direction == "UP"


def test_sector_api_capability_matrix_includes_expected_ids():
    result = build_kiwoom_rest_readonly_sector_adapter(_config())
    api_ids = {entry.api_id.value for entry in result.sector_etf_capability_matrix_report.entries}
    assert {"KA20001", "KA20002", "KA20003", "KA20004", "KA20005", "KA20006", "KA20007", "KA20008", "KA20009", "KA20019"} <= api_ids


def test_etf_api_capability_matrix_includes_expected_ids():
    result = build_kiwoom_rest_readonly_sector_adapter(_config())
    api_ids = {entry.api_id.value for entry in result.sector_etf_capability_matrix_report.entries}
    assert {"KA40001", "KA40002", "KA40003", "KA40004", "KA40006", "KA40007", "KA40008", "KA40009", "KA40010"} <= api_ids


def test_apis_without_exact_schema_are_not_request_builder_ready():
    result = build_kiwoom_rest_readonly_sector_adapter(_config())
    matrix = {entry.api_id.value: entry for entry in result.sector_etf_capability_matrix_report.entries}
    assert matrix["KA20001"].request_builder_ready is False
    assert matrix["KA20001"].readiness == KiwoomRestSectorReadiness.FUTURE_SUPPORTED
    assert matrix["KA40004"].request_builder_ready is False
    assert matrix["KA40004"].readiness == KiwoomRestSectorReadiness.FUTURE_SUPPORTED


def test_signed_numeric_strings_are_normalized_safely():
    result = build_kiwoom_rest_readonly_sector_adapter(_config())
    signal = result.canonical_theme_leadership_report.signals[0]
    assert signal.theme_change_rate == 3.25
    assert signal.period_return == 5.10


def test_blank_malformed_numeric_creates_schema_gap_not_crash():
    result = build_kiwoom_rest_readonly_sector_adapter(
        _config(mocked_response_payload={"return_code": 0, "return_msg": "정상적으로 처리되었습니다", "thema_grp": [{"thema_grp_cd": "553", "thema_nm": "2차전지", "flu_rt": "abc"}]})
    )
    assert result.summary_report.readiness == KiwoomRestSectorReadiness.SCHEMA_GAP


def test_return_code_nonzero_creates_data_gap():
    result = build_kiwoom_rest_readonly_sector_adapter(_config(mocked_response_payload={"return_code": 100, "return_msg": "에러"}))
    assert result.summary_report.readiness == KiwoomRestSectorReadiness.DATA_GAP


def test_malformed_response_creates_schema_gap():
    result = build_kiwoom_rest_readonly_sector_adapter(_config(mocked_response_payload={"return_code": 0}))
    assert result.summary_report.readiness == KiwoomRestSectorReadiness.SCHEMA_GAP


def test_continuation_is_represented():
    result = build_kiwoom_rest_readonly_sector_adapter(
        _config(mocked_response_payload={**kiwoom_rest_readonly_sector_payload()["mocked_response_payload"], "cont_yn": "Y", "next_key": "PAGE2"})
    )
    assert result.continuation_report.has_more is True


def test_real_network_transport_attempt_is_blocked():
    result = build_kiwoom_rest_readonly_sector_adapter(_config(mocked_response_payload=None))
    assert result.summary_report.readiness == KiwoomRestSectorReadiness.BLOCKED


def test_missing_available_at_creates_data_gap():
    result = build_kiwoom_rest_readonly_sector_adapter(_config(available_at=None))
    assert result.summary_report.readiness == KiwoomRestSectorReadiness.DATA_GAP


def test_v7_integration_report_sees_sector_theme_etf_readiness():
    result = build_kiwoom_rest_readonly_sector_adapter(_config())
    assert result.v7_integration_report.v712_leadership_membership_etf_ready is True


def test_no_executable_order_output_is_produced_and_audit_is_redacted():
    result = build_kiwoom_rest_readonly_sector_adapter(_config())
    dumped = result.model_dump_json()
    assert "order_id" not in dumped.lower()
    assert result.audit_records[0].redaction_applied is True
