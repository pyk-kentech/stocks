import json

import pytest

from stock_risk_mcp.kiwoom_mock_api_transport_draft_engine import (
    run_kiwoom_mock_api_transport_draft_boundary,
)
from stock_risk_mcp.kiwoom_mock_api_transport_draft_fixture import (
    load_kiwoom_mock_api_transport_draft_fixture,
)
from stock_risk_mcp.kiwoom_mock_api_transport_draft_models import (
    KiwoomMockApiTransportDraftConfig,
    KiwoomMockApiTransportGapCategory,
)


def kiwoom_mock_api_transport_engine_fixture_payload():
    return {
        "schema_version": "v6.6-kiwoom-mock-api-transport-draft-boundary",
        "fixture_format": "json",
        "config_id": "kiwoom-mock-api-transport-engine-config-1",
        "endpoint_evidence_ref": {
            "endpoint_ref_id": "kiwoom-mock-balance-endpoint-1",
            "source_evidence_document_id": "KIWOOM-REST-EVIDENCE-PACK",
            "documented_api_id": "kt00017",
            "documented_category": "ACCOUNT_QUERY",
            "documented_method": "POST",
            "documented_path": "/api/dostk/acnt",
            "documented_mock_domain": "https://mockapi.kiwoom.com",
            "documented_production_domain": "https://api.kiwoom.com",
            "documented_mock_support": True,
            "documented_krx_only_note": "KRX only",
            "evidence_only": True,
            "executable": False,
            "production_domain_blocked": True,
        },
        "request_envelope_draft": {
            "draft_id": "kiwoom-mock-api-request-envelope-1",
            "endpoint_ref_id": "KIWOOM-MOCK-BALANCE-ENDPOINT-1",
            "documented_method": "POST",
            "mock_domain_reference": "MOCK_DOMAIN_REF",
            "request_path": "/api/dostk/acnt",
            "credential_ref_ids": ["KIWOOM_MOCK_APP_KEY_REF", "KIWOOM_MOCK_SECRET_KEY_REF"],
            "token_ref_id": "KIWOOM_MOCK_TOKEN_REF",
            "headers": [
                {
                    "header_name": "content-type",
                    "required": True,
                    "value_source": "LITERAL_SAFE",
                    "value_preview": "application/json;charset=UTF-8",
                    "redaction_applied": False,
                },
                {
                    "header_name": "authorization",
                    "required": True,
                    "value_source": "TOKEN_REF_BLOCKED",
                    "value_preview": "TOKEN_REF_ONLY",
                    "redaction_applied": True,
                },
            ],
            "query_params": [
                {
                    "param_name": "qry_tp",
                    "value_source": "LITERAL_SAFE",
                    "value_preview": "0",
                    "redaction_applied": False,
                }
            ],
            "path_params": [
                {
                    "param_name": "market_code",
                    "value_source": "LITERAL_SAFE",
                    "value_preview": "KRX",
                    "redaction_applied": False,
                }
            ],
            "body_draft": {
                "field_names": ["appkey", "secretkey", "stk_cd"],
                "field_value_sources": {
                    "appkey": "CREDENTIAL_REF_ONLY",
                    "secretkey": "CREDENTIAL_REF_ONLY",
                    "stk_cd": "LITERAL_SAFE",
                },
                "field_value_previews": {
                    "appkey": "KIWOOM_MOCK_APP_KEY_REF",
                    "secretkey": "KIWOOM_MOCK_SECRET_KEY_REF",
                    "stk_cd": "005930",
                },
                "redaction_applied": True,
                "serializable_report_only": True,
            },
            "authorization_header_generation_available": False,
            "http_client_available": False,
            "http_session_available": False,
            "network_execution_enabled": False,
        },
        "transport_policy": {
            "policy_id": "kiwoom-mock-api-transport-policy-1",
            "allowed_mock_rest_domain": "https://mockapi.kiwoom.com",
            "forbidden_production_rest_domain": "https://api.kiwoom.com",
            "krx_only": True,
            "disabled_by_default": True,
            "explicit_opt_in_required": True,
        },
        "retry_timeout_policy": {
            "policy_id": "kiwoom-mock-api-retry-timeout-policy-1",
            "request_timeout_class": "DOCUMENTED_ONLY",
            "retry_policy_class": "DOCUMENTED_ONLY",
            "rate_limit_note_ref": "KIWOOM-RATE-LIMIT-NOTE-REF",
            "timeout_execution_enabled": False,
            "retry_loop_enabled": False,
            "sleep_backoff_enabled": False,
        },
        "error_response_draft": {
            "error_draft_id": "kiwoom-mock-api-error-response-draft-1",
            "documented_error_fields": ["return_code", "return_msg"],
            "captures_live_response": False,
            "wraps_transport_exception": False,
            "contains_credential_material": False,
        },
        "safety_report": {
            "safety_report_id": "kiwoom-mock-api-transport-safety-report-1",
            "blocked_capabilities": [
                "AUTHORIZATION_HEADER_GENERATION_BLOCKED",
                "TOKEN_LOADING_BLOCKED",
                "HTTP_CLIENT_CREATION_BLOCKED",
                "HTTP_SESSION_CREATION_BLOCKED",
                "NETWORK_EXECUTION_BLOCKED",
                "PRODUCTION_DOMAIN_EXECUTION_BLOCKED",
            ],
            "findings": [],
        },
        "gap_report": {
            "gap_report_id": "kiwoom-mock-api-transport-gap-report-1",
            "gap_status": "UNRESOLVED_IMPLEMENTATION_GAPS",
            "gap_categories": [],
            "blocking_gap_count": 0,
            "report_only_gap_count": 0,
            "gaps": [],
        },
        "audit_records": [
            {
                "audit_record_id": "kiwoom-mock-api-transport-audit-record-1",
                "created_at": "2026-06-23T00:00:00+09:00",
                "source_path": "fixtures/kiwoom/kiwoom_mock_api_transport_draft_fixture.json",
                "redaction_applied": True,
                "contains_secret_material": False,
                "evidence_refs": [
                    "KIWOOM-REST-EVIDENCE-PACK",
                    "KIWOOM-CAPABILITY-MATRIX",
                    "V6.5-OAUTH-DRAFT-BOUNDARY",
                ],
            }
        ],
    }


def _config():
    return KiwoomMockApiTransportDraftConfig.model_validate(
        kiwoom_mock_api_transport_engine_fixture_payload()
    )


def test_engine_builds_request_envelope_draft_only_from_valid_local_draft_config():
    result = run_kiwoom_mock_api_transport_draft_boundary(
        _config(),
        oauth_draft_boundary_ref="docs/superpowers/plans/2026-06-18-kiwoom-mock-oauth-token-draft-boundary-design.md",
    )
    assert result.request_envelope_draft.network_execution_enabled is False
    assert "draft_bundle_built=true" in result.safety_report.findings


def test_default_disabled_config_does_not_create_executable_transport_path():
    result = run_kiwoom_mock_api_transport_draft_boundary(_config())
    assert result.request_envelope_draft.http_client_available is False
    assert (
        KiwoomMockApiTransportGapCategory.KIWOOM_MOCK_API_TRANSPORT_MISSING_EXECUTABLE_TRANSPORT
        in result.gap_report.gap_categories
    )


def test_request_envelope_remains_draft_only_mock_only_offline_only_non_executable():
    result = run_kiwoom_mock_api_transport_draft_boundary(_config(), oauth_draft_boundary_ref="boundary-ref")
    assert result.request_envelope_draft.non_executable is True
    assert result.request_envelope_draft.mock_only is True
    assert result.request_envelope_draft.offline_only is True


def test_endpoint_evidence_refs_remain_documentation_refs_not_executable_urls():
    result = run_kiwoom_mock_api_transport_draft_boundary(_config(), oauth_draft_boundary_ref="boundary-ref")
    assert result.endpoint_evidence_ref.evidence_only is True
    assert result.endpoint_evidence_ref.executable is False


def test_http_method_refs_do_not_create_executable_http_requests():
    result = run_kiwoom_mock_api_transport_draft_boundary(_config(), oauth_draft_boundary_ref="boundary-ref")
    assert result.request_envelope_draft.documented_method == "POST"
    assert result.request_envelope_draft.network_execution_enabled is False


def test_header_draft_cannot_generate_authorization_header():
    result = run_kiwoom_mock_api_transport_draft_boundary(_config(), oauth_draft_boundary_ref="boundary-ref")
    assert result.request_envelope_draft.authorization_header_generation_available is False
    assert "AUTHORIZATION_HEADER_GENERATION_BLOCKED" in result.safety_report.blocked_capabilities


def test_body_query_path_drafts_reject_raw_secret_token_account_auth_markers():
    payload = kiwoom_mock_api_transport_engine_fixture_payload()
    payload["request_envelope_draft"]["body_draft"]["field_value_previews"]["stk_cd"] = "Bearer abc"
    with pytest.raises(ValueError, match="authorization"):
        KiwoomMockApiTransportDraftConfig.model_validate(payload)


def test_token_ref_only_and_credential_ref_only_policies_are_enforced():
    result = run_kiwoom_mock_api_transport_draft_boundary(_config(), oauth_draft_boundary_ref="boundary-ref")
    assert result.request_envelope_draft.token_ref_id == "KIWOOM_MOCK_TOKEN_REF"
    assert result.request_envelope_draft.credential_ref_ids == [
        "KIWOOM_MOCK_APP_KEY_REF",
        "KIWOOM_MOCK_SECRET_KEY_REF",
    ]


def test_mock_domain_only_policy_is_enforced():
    result = run_kiwoom_mock_api_transport_draft_boundary(_config(), oauth_draft_boundary_ref="boundary-ref")
    assert result.transport_policy.allowed_mock_rest_domain == "https://mockapi.kiwoom.com"


def test_production_domain_execution_is_blocked():
    payload = kiwoom_mock_api_transport_engine_fixture_payload()
    payload["endpoint_evidence_ref"]["documented_mock_domain"] = "https://api.kiwoom.com"
    with pytest.raises(ValueError, match="production domain"):
        KiwoomMockApiTransportDraftConfig.model_validate(payload)


def test_retry_timeout_rate_limit_policy_is_representation_only():
    result = run_kiwoom_mock_api_transport_draft_boundary(_config(), oauth_draft_boundary_ref="boundary-ref")
    assert result.retry_timeout_policy.timeout_execution_enabled is False
    assert result.retry_timeout_policy.retry_loop_enabled is False
    assert result.retry_timeout_policy.sleep_backoff_enabled is False


def test_error_response_draft_is_local_and_non_executable():
    result = run_kiwoom_mock_api_transport_draft_boundary(_config(), oauth_draft_boundary_ref="boundary-ref")
    assert result.error_response_draft.captures_live_response is False
    assert result.error_response_draft.wraps_transport_exception is False


def test_safety_report_includes_blocked_http_api_mockapi_websocket_network_live_prod_capabilities():
    result = run_kiwoom_mock_api_transport_draft_boundary(_config(), oauth_draft_boundary_ref="boundary-ref")
    blocked = set(result.safety_report.blocked_capabilities)
    assert {
        "AUTHORIZATION_HEADER_GENERATION_BLOCKED",
        "TOKEN_LOADING_BLOCKED",
        "HTTP_CLIENT_CREATION_BLOCKED",
        "HTTP_SESSION_CREATION_BLOCKED",
        "API_CALL_BLOCKED",
        "MOCKAPI_CALL_BLOCKED",
        "WEBSOCKET_BLOCKED",
        "NETWORK_EXECUTION_BLOCKED",
        "LIVE_PROD_BLOCKED",
        "REAL_ORDER_BLOCKED",
    }.issubset(blocked)


def test_gap_report_includes_unresolved_http_client_session_transport_mockapi_execution_gaps():
    result = run_kiwoom_mock_api_transport_draft_boundary(_config(), oauth_draft_boundary_ref="boundary-ref")
    categories = set(result.gap_report.gap_categories)
    assert {
        KiwoomMockApiTransportGapCategory.KIWOOM_MOCK_API_TRANSPORT_MISSING_EXECUTABLE_TRANSPORT,
        KiwoomMockApiTransportGapCategory.KIWOOM_MOCK_API_HTTP_CLIENT_NOT_ALLOWED,
        KiwoomMockApiTransportGapCategory.KIWOOM_MOCK_API_HTTP_SESSION_NOT_ALLOWED,
        KiwoomMockApiTransportGapCategory.KIWOOM_MOCK_API_MOCKAPI_CALL_NOT_ALLOWED,
    }.issubset(categories)


def test_audit_record_is_redacted_and_contains_no_raw_credential_token_account_material():
    result = run_kiwoom_mock_api_transport_draft_boundary(_config(), oauth_draft_boundary_ref="boundary-ref")
    record = result.audit_records[0]
    assert record.redaction_applied is True
    assert record.contains_secret_material is False


def test_fixture_loaded_draft_data_can_be_passed_through_engine_without_env_var_read_or_network_call(
    tmp_path,
):
    fixture_path = tmp_path / "kiwoom_mock_api_transport_engine_fixture.json"
    fixture_path.write_text(
        json.dumps(kiwoom_mock_api_transport_engine_fixture_payload()),
        encoding="utf-8",
    )
    config = load_kiwoom_mock_api_transport_draft_fixture(fixture_path)
    result = run_kiwoom_mock_api_transport_draft_boundary(
        config,
        oauth_draft_boundary_ref="docs/superpowers/plans/2026-06-18-kiwoom-mock-oauth-token-draft-boundary-design.md",
    )
    assert result.no_environment_read is True
    assert result.no_credentials_loaded is True
    assert result.no_network_call is True
