import json

import pytest

from stock_risk_mcp.kiwoom_mock_api_preflight_gate_engine import (
    run_kiwoom_mock_api_preflight_gate,
)
from stock_risk_mcp.kiwoom_mock_api_preflight_gate_fixture import (
    load_kiwoom_mock_api_preflight_gate_fixture,
)
from stock_risk_mcp.kiwoom_mock_api_preflight_gate_models import (
    KiwoomMockApiExecutionReadiness,
    KiwoomMockApiPreflightGateConfig,
    KiwoomMockApiPreflightRequestCategory,
)
from tests.test_kiwoom_mock_api_preflight_gate_models import (
    kiwoom_mock_api_preflight_gate_fixture_payload,
)


def _config(**kwargs):
    return KiwoomMockApiPreflightGateConfig.model_validate(
        kiwoom_mock_api_preflight_gate_fixture_payload(**kwargs)
    )


def test_valid_mock_domain_read_only_quote_draft_can_become_draft_ready():
    result = run_kiwoom_mock_api_preflight_gate(_config())
    assert result.readiness_report.request_category == KiwoomMockApiPreflightRequestCategory.QUOTE
    assert result.readiness_report.readiness_decision == KiwoomMockApiExecutionReadiness.DRAFT_READY


def test_quote_draft_with_unresolved_future_execution_requirements_can_become_gap():
    result = run_kiwoom_mock_api_preflight_gate(
        _config(documented_category="QUOTE", documented_path="/api/dostk/mrkcond/detail")
    )
    assert result.readiness_report.request_category == KiwoomMockApiPreflightRequestCategory.QUOTE
    assert result.readiness_report.readiness_decision == KiwoomMockApiExecutionReadiness.GAP


def test_oauth_endpoint_remains_blocked():
    result = run_kiwoom_mock_api_preflight_gate(
        _config(documented_category="QUOTE", documented_path="/oauth2/token")
    )
    assert result.readiness_report.readiness_decision == KiwoomMockApiExecutionReadiness.BLOCKED
    assert result.readiness_report.request_category == KiwoomMockApiPreflightRequestCategory.OAUTH


def test_account_endpoint_remains_blocked():
    result = run_kiwoom_mock_api_preflight_gate(
        _config(documented_category="ACCOUNT", documented_path="/api/dostk/acnt")
    )
    assert result.readiness_report.readiness_decision == KiwoomMockApiExecutionReadiness.BLOCKED
    assert result.readiness_report.request_category == KiwoomMockApiPreflightRequestCategory.ACCOUNT


def test_order_endpoint_remains_blocked():
    result = run_kiwoom_mock_api_preflight_gate(
        _config(documented_category="ORDER", documented_path="/api/dostk/ordr")
    )
    assert result.readiness_report.readiness_decision == KiwoomMockApiExecutionReadiness.BLOCKED
    assert result.readiness_report.request_category == KiwoomMockApiPreflightRequestCategory.ORDER


def test_websocket_endpoint_remains_blocked():
    result = run_kiwoom_mock_api_preflight_gate(
        _config(documented_category="WEBSOCKET", documented_path="/api/websocket/quote")
    )
    assert result.readiness_report.readiness_decision == KiwoomMockApiExecutionReadiness.BLOCKED
    assert result.readiness_report.request_category == KiwoomMockApiPreflightRequestCategory.WEBSOCKET


def test_production_domain_rejected_or_blocked():
    with pytest.raises(ValueError, match="production domain"):
        _config(documented_mock_domain="https://api.kiwoom.com")


def test_unknown_endpoint_rejected():
    result = run_kiwoom_mock_api_preflight_gate(
        _config(documented_category="MISC", documented_path="/api/unknown")
    )
    assert result.readiness_report.readiness_decision == KiwoomMockApiExecutionReadiness.REJECTED
    assert result.readiness_report.request_category == KiwoomMockApiPreflightRequestCategory.UNKNOWN


def test_no_authorization_header_token_client_session_network_behavior():
    result = run_kiwoom_mock_api_preflight_gate(_config())
    assert result.no_authorization_header_generated is True
    assert result.no_token_loaded is True
    assert result.no_token_used is True
    assert result.no_token_refreshed is True
    assert result.no_http_client_created is True
    assert result.no_http_session_created is True
    assert result.no_network_call is True


def test_safety_report_includes_blocked_capabilities():
    result = run_kiwoom_mock_api_preflight_gate(_config())
    blocked = set(result.safety_report.blocked_capabilities)
    assert {
        "AUTHORIZATION_HEADER_GENERATION_BLOCKED",
        "TOKEN_LOADING_BLOCKED",
        "HTTP_CLIENT_CREATION_BLOCKED",
        "ACCOUNT_ENDPOINT_BLOCKED",
        "ORDER_ENDPOINT_BLOCKED",
    } & blocked or "AUTHORIZATION_HEADER_GENERATION_BLOCKED" in blocked


def test_gap_report_includes_unresolved_execution_client_session_token_account_order_gaps():
    result = run_kiwoom_mock_api_preflight_gate(_config())
    categories = {category.value for category in result.gap_report.gap_categories}
    assert {
        "PREFLIGHT_HTTP_CLIENT_NOT_ALLOWED",
        "PREFLIGHT_HTTP_SESSION_NOT_ALLOWED",
        "PREFLIGHT_TOKEN_LOADING_NOT_ALLOWED",
        "PREFLIGHT_EXECUTION_NOT_IMPLEMENTED",
    }.issubset(categories)


def test_audit_report_is_redacted():
    result = run_kiwoom_mock_api_preflight_gate(_config())
    assert result.audit_records[0].redaction_applied is True
    assert result.audit_records[0].contains_secret_material is False


def test_fixture_loaded_draft_data_can_be_passed_through_engine_without_env_credential_token_network_behavior(
    tmp_path,
):
    fixture_path = tmp_path / "kiwoom_mock_api_preflight_gate_fixture.json"
    fixture_path.write_text(
        json.dumps(kiwoom_mock_api_preflight_gate_fixture_payload()),
        encoding="utf-8",
    )
    config = load_kiwoom_mock_api_preflight_gate_fixture(fixture_path)
    result = run_kiwoom_mock_api_preflight_gate(config)
    assert result.no_environment_read is True
    assert result.no_credential_file_read is True
    assert result.no_credentials_loaded is True
    assert result.no_network_call is True
