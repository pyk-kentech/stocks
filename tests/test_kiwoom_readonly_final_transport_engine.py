import json

from stock_risk_mcp.kiwoom_readonly_final_transport_engine import build_kiwoom_readonly_final_transport
from stock_risk_mcp.kiwoom_readonly_final_transport_models import KiwoomReadonlyFinalRequest, KiwoomReadonlyFinalStatus
from tests.test_kiwoom_rest_readonly_chart_models import kiwoom_rest_readonly_chart_payload
from tests.test_kiwoom_rest_readonly_flow_models import kiwoom_rest_readonly_flow_payload
from tests.test_kiwoom_rest_readonly_quote_models import kiwoom_rest_readonly_quote_payload
from tests.test_kiwoom_rest_readonly_rank_models import kiwoom_rest_readonly_rank_payload
from tests.test_kiwoom_rest_readonly_sector_models import kiwoom_rest_readonly_sector_payload


def _request(api_id: str, mocked_response_payload=None, **overrides):
    payload = {
        "request_id": f"final-{api_id}",
        "mode": "MOCKED_TRANSPORT_ONLY",
        "api_id": api_id,
        "domain": "KIWOOM_MOCK_KRX",
        "body_json": {"stk_cd": "005930", "base_dt": "20260625", "upd_stkpc_tp": "1"},
        "provider_symbol": "005930",
        "canonical_instrument_key": "005930_KRX",
        "available_at": "2026-06-25T15:35:00+09:00",
        "mocked_response_payload": mocked_response_payload or {"return_code": 0, "return_msg": "정상"},
    }
    payload.update(overrides)
    return KiwoomReadonlyFinalRequest.model_validate(payload)


def test_default_transport_preview_is_blocked_or_preview_only():
    result = build_kiwoom_readonly_final_transport(
        _request("KA10081", mode="DRY_RUN_PREVIEW_ONLY", mocked_response_payload=None)
    )
    assert result.summary_report.status == KiwoomReadonlyFinalStatus.PREVIEW_READY
    assert result.response_report is None

    blocked = build_kiwoom_readonly_final_transport(
        _request("KA10081", mode="BLOCKED_BY_DEFAULT", mocked_response_payload=None)
    )
    assert blocked.summary_report.status == KiwoomReadonlyFinalStatus.BLOCKED_DEFAULT


def test_unallowlisted_account_order_and_unknown_apis_are_blocked():
    assert build_kiwoom_readonly_final_transport(_request("KA00001")).summary_report.status == KiwoomReadonlyFinalStatus.BLOCKED_ACCOUNT_API
    assert build_kiwoom_readonly_final_transport(_request("KT10000")).summary_report.status == KiwoomReadonlyFinalStatus.BLOCKED_ORDER_API
    assert build_kiwoom_readonly_final_transport(_request("ZZ99999")).summary_report.status == KiwoomReadonlyFinalStatus.BLOCKED_API_NOT_ALLOWLISTED


def test_missing_opt_in_and_pytest_real_network_are_blocked(monkeypatch):
    request = _request(
        "KA10081",
        mode="REAL_READONLY_SINGLE_CALL_SMOKE",
        mocked_response_payload=None,
        token_provider={"provider_kind": "ENV_EXPLICIT", "env_var_name": "KIWOOM_ACCESS_TOKEN"},
    )
    blocked = build_kiwoom_readonly_final_transport(request)
    assert blocked.summary_report.status == KiwoomReadonlyFinalStatus.BLOCKED_NETWORK_IN_TEST

    monkeypatch.delenv("PYTEST_CURRENT_TEST", raising=False)
    missing_opt_in = build_kiwoom_readonly_final_transport(request)
    assert missing_opt_in.summary_report.status == KiwoomReadonlyFinalStatus.BLOCKED_MISSING_OPT_IN


def test_raw_token_and_authorization_user_input_are_blocked():
    token_body = build_kiwoom_readonly_final_transport(
        _request("KA10081", body_json={"authorization": "Bearer real-token"})
    )
    assert token_body.summary_report.status == KiwoomReadonlyFinalStatus.BLOCKED_TOKEN_POLICY

    secret_body = build_kiwoom_readonly_final_transport(
        _request("KA10081", body_json={"appkey": "secret-key"})
    )
    assert secret_body.summary_report.status == KiwoomReadonlyFinalStatus.BLOCKED_TOKEN_POLICY


def test_mocked_transport_routes_supported_responses_through_existing_parsers():
    chart = build_kiwoom_readonly_final_transport(
        _request("KA10081", mocked_response_payload=kiwoom_rest_readonly_chart_payload()["mocked_response_payload"])
    )
    quote = build_kiwoom_readonly_final_transport(
        _request("KA10004", mocked_response_payload=kiwoom_rest_readonly_quote_payload()["mocked_response_payload"])
    )
    rank = build_kiwoom_readonly_final_transport(
        _request("KA10023", mocked_response_payload=kiwoom_rest_readonly_rank_payload()["mocked_response_payload"])
    )
    flow = build_kiwoom_readonly_final_transport(
        _request("KA10059", mocked_response_payload=kiwoom_rest_readonly_flow_payload()["mocked_response_payload"])
    )
    sector = build_kiwoom_readonly_final_transport(
        _request("KA90001", mocked_response_payload=kiwoom_rest_readonly_sector_payload()["mocked_response_payload"], provider_symbol=None, canonical_instrument_key=None)
    )

    assert chart.parser_routing_report.import_result.canonical_output_report.canonical_ohlcv_records
    assert quote.parser_routing_report.import_result.canonical_output_report.canonical_quote_records
    assert rank.parser_routing_report.import_result.canonical_output_report.canonical_outlier_signals
    assert flow.parser_routing_report.import_result.canonical_output_report.canonical_investor_flow_signals
    assert sector.parser_routing_report.import_result.canonical_output_report.canonical_theme_leadership_signals


def test_schema_gap_api_returns_schema_gap_not_crash():
    result = build_kiwoom_readonly_final_transport(_request("KA90003"))
    assert result.parser_routing_report.import_result.summary_report.readiness.value == "READONLY_SCHEMA_GAP"


def test_capture_is_disabled_by_default_and_safe_capture_writes_redacted_json(tmp_path):
    default_result = build_kiwoom_readonly_final_transport(
        _request("KA10081", mocked_response_payload=kiwoom_rest_readonly_chart_payload()["mocked_response_payload"])
    )
    assert default_result.capture_report.status.value == "CAPTURE_DISABLED"

    capture_result = build_kiwoom_readonly_final_transport(
        _request(
            "KA10081",
            mocked_response_payload=kiwoom_rest_readonly_chart_payload()["mocked_response_payload"],
            capture_policy={"enabled": True, "capture_dir": str(tmp_path)},
        )
    )
    assert capture_result.capture_report.status.value == "CAPTURE_WRITTEN"
    captured_file = capture_result.capture_report.captured_files[0]
    payload = json.loads(open(captured_file.file_path, encoding="utf-8").read())
    assert "authorization" not in json.dumps(payload).lower()
    assert capture_result.parser_routing_report.imported_file_path == captured_file.file_path


def test_snapshot_validation_uses_v86_and_partial_inputs_do_not_crash():
    result = build_kiwoom_readonly_final_transport(
        _request(
            "KA10081",
            mocked_response_payload=kiwoom_rest_readonly_chart_payload()["mocked_response_payload"],
            validate_snapshot=True,
        )
    )
    assert result.snapshot_validation_report is not None
    assert result.snapshot_validation_report.report_only is True
    assert result.snapshot_validation_report.status in {
        KiwoomReadonlyFinalStatus.DATA_GAP,
        KiwoomReadonlyFinalStatus.SNAPSHOT_VALIDATED,
    }


def test_final_readiness_report_marks_v8_complete_and_future_scopes_out_of_scope():
    result = build_kiwoom_readonly_final_transport(
        _request("KA10081", mocked_response_payload=kiwoom_rest_readonly_chart_payload()["mocked_response_payload"])
    )
    notes = " ".join(result.readiness_report.scope_notes).lower()
    assert result.readiness_report.v8_complete is True
    assert "v9 next scope is external macro/regime data pipeline" in notes
    assert "v10 next scope is feature store/cache pipeline" in notes
    assert "v11 next scope is real-data paper trading" in notes
    assert "v12 next scope is account-read and reconciliation" in notes
    assert "v13 next scope is controlled execution and live order controls" in notes
