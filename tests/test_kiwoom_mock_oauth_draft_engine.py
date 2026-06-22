import json

import pytest

from stock_risk_mcp.kiwoom_mock_oauth_draft_engine import run_kiwoom_mock_oauth_draft_boundary
from stock_risk_mcp.kiwoom_mock_oauth_draft_fixture import load_kiwoom_mock_oauth_draft_fixture
from stock_risk_mcp.kiwoom_mock_oauth_draft_models import (
    KiwoomMockOAuthDraftConfig,
    KiwoomMockOAuthGapCategory,
)


def kiwoom_mock_oauth_engine_fixture_payload():
    return {
        "schema_version": "v6.5-kiwoom-mock-oauth-draft-boundary",
        "fixture_format": "json",
        "config_id": "kiwoom-mock-oauth-draft-engine-config-1",
        "endpoint_refs": [
            {
                "endpoint_ref_id": "kiwoom-mock-token-issue-endpoint-1",
                "documented_purpose": "TOKEN_ISSUE",
                "method": "POST",
                "domain": "https://mockapi.kiwoom.com",
                "path": "/oauth2/token",
                "evidence_only": True,
                "executable": False,
                "production_domain_blocked": True,
                "krx_only": True,
            },
            {
                "endpoint_ref_id": "kiwoom-mock-token-revoke-endpoint-1",
                "documented_purpose": "TOKEN_REVOKE",
                "method": "POST",
                "domain": "https://mockapi.kiwoom.com",
                "path": "/oauth2/revoke",
                "evidence_only": True,
                "executable": False,
                "production_domain_blocked": True,
                "krx_only": True,
            },
        ],
        "token_request_draft": {
            "draft_id": "kiwoom-mock-token-request-draft-1",
            "endpoint_ref_id": "KIWOOM-MOCK-TOKEN-ISSUE-ENDPOINT-1",
            "credential_ref_ids": [
                "KIWOOM_MOCK_APP_KEY_REF",
                "KIWOOM_MOCK_SECRET_KEY_REF",
            ],
            "request_field_names": ["grant_type", "appkey", "secretkey"],
            "response_field_names": ["expires_dt", "token_type", "token"],
            "credential_ref_only": True,
            "authorization_header_available": False,
            "request_execution_enabled": False,
        },
        "token_response_draft": {
            "response_draft_id": "kiwoom-mock-token-response-draft-1",
            "documented_response_field_names": ["expires_dt", "token_type", "token"],
            "stores_real_token": False,
            "token_storage_enabled": False,
            "token_refresh_enabled": False,
        },
        "token_revoke_draft": {
            "draft_id": "kiwoom-mock-token-revoke-draft-1",
            "endpoint_ref_id": "KIWOOM-MOCK-TOKEN-REVOKE-ENDPOINT-1",
            "credential_ref_ids": [
                "KIWOOM_MOCK_APP_KEY_REF",
                "KIWOOM_MOCK_SECRET_KEY_REF",
            ],
            "token_reference_label": "MASKED_TOKEN_REF",
            "request_field_names": ["appkey", "secretkey", "token"],
            "credential_ref_only": True,
            "request_execution_enabled": False,
        },
        "token_lifecycle_policy": {
            "policy_id": "kiwoom-mock-token-lifecycle-policy-1",
            "issue_execution_allowed": False,
            "revoke_execution_allowed": False,
            "refresh_execution_allowed": False,
            "storage_execution_allowed": False,
            "documented_lifetime_field_name": "expires_dt",
            "token_value_retained": False,
        },
        "safety_report": {
            "safety_report_id": "kiwoom-mock-oauth-safety-report-1",
            "blocked_capabilities": ["TOKEN_ISSUE_EXECUTION_BLOCKED"],
            "findings": [],
        },
        "gap_report": {
            "gap_report_id": "kiwoom-mock-oauth-gap-report-1",
            "gap_status": "UNRESOLVED_IMPLEMENTATION_GAPS",
            "gap_categories": [],
            "blocking_gap_count": 0,
            "report_only_gap_count": 0,
            "gaps": [],
        },
        "audit_records": [
            {
                "audit_record_id": "kiwoom-mock-oauth-audit-record-1",
                "created_at": "2026-06-23T00:00:00+09:00",
                "source_path": "fixtures/kiwoom/kiwoom_mock_oauth_draft_fixture.json",
                "redaction_applied": True,
                "contains_secret_material": False,
                "evidence_refs": ["KIWOOM-REST-EVIDENCE-PACK", "KIWOOM-CAPABILITY-MATRIX"],
            }
        ],
    }


def _config():
    return KiwoomMockOAuthDraftConfig.model_validate(kiwoom_mock_oauth_engine_fixture_payload())


def test_engine_builds_token_request_draft_only_when_valid_and_explicitly_opted_in():
    result = run_kiwoom_mock_oauth_draft_boundary(
        _config(),
        explicit_opt_in_ack=True,
        credential_boundary_ref="docs/superpowers/plans/2026-06-18-kiwoom-mock-credential-environment-boundary-design.md",
    )
    assert result.token_request_draft.request_execution_enabled is False
    assert result.token_request_draft.credential_ref_only is True
    assert "explicit_opt_in_acknowledged=true" in result.safety_report.findings


def test_default_disabled_config_does_not_produce_an_executable_path():
    result = run_kiwoom_mock_oauth_draft_boundary(_config(), explicit_opt_in_ack=False)
    assert result.token_request_draft.request_execution_enabled is False
    assert KiwoomMockOAuthGapCategory.KIWOOM_MOCK_OAUTH_EXECUTION_MODE_NOT_ALLOWED in result.gap_report.gap_categories


def test_request_draft_remains_credential_ref_only_and_non_executable():
    result = run_kiwoom_mock_oauth_draft_boundary(_config(), explicit_opt_in_ack=True, credential_boundary_ref="boundary-ref")
    assert result.token_request_draft.credential_ref_only is True
    assert result.token_request_draft.authorization_header_available is False
    assert result.token_request_draft.request_execution_enabled is False


def test_response_draft_does_not_contain_or_persist_real_access_token():
    result = run_kiwoom_mock_oauth_draft_boundary(_config(), explicit_opt_in_ack=True, credential_boundary_ref="boundary-ref")
    assert result.token_response_draft.stores_real_token is False
    assert result.token_response_draft.token_storage_enabled is False


def test_revoke_draft_is_non_executable_and_does_not_revoke_anything():
    result = run_kiwoom_mock_oauth_draft_boundary(_config(), explicit_opt_in_ack=True, credential_boundary_ref="boundary-ref")
    assert result.token_revoke_draft.request_execution_enabled is False


def test_lifecycle_report_blocks_token_storage_and_token_refresh():
    result = run_kiwoom_mock_oauth_draft_boundary(_config(), explicit_opt_in_ack=True, credential_boundary_ref="boundary-ref")
    assert result.token_lifecycle_policy.storage_execution_allowed is False
    assert result.token_lifecycle_policy.refresh_execution_allowed is False


def test_credential_boundary_dependency_is_validated_as_reference_only():
    result = run_kiwoom_mock_oauth_draft_boundary(
        _config(),
        explicit_opt_in_ack=True,
        credential_boundary_ref="docs/superpowers/plans/2026-06-18-kiwoom-mock-credential-environment-boundary-design.md",
    )
    assert "credential_boundary_dependency=REFERENCE_ONLY" in result.safety_report.findings


def test_mock_endpoint_evidence_refs_are_accepted_only_as_documentation_references():
    result = run_kiwoom_mock_oauth_draft_boundary(_config(), explicit_opt_in_ack=True, credential_boundary_ref="boundary-ref")
    assert all(endpoint.evidence_only for endpoint in result.endpoint_refs)
    assert all(not endpoint.executable for endpoint in result.endpoint_refs)


def test_production_domain_execution_is_blocked():
    payload = kiwoom_mock_oauth_engine_fixture_payload()
    payload["endpoint_refs"][0]["domain"] = "https://api.kiwoom.com"
    with pytest.raises(ValueError, match="production domain"):
        KiwoomMockOAuthDraftConfig.model_validate(payload)


def test_raw_secret_token_account_auth_markers_are_rejected():
    payload = kiwoom_mock_oauth_engine_fixture_payload()
    payload["safety_report"]["findings"] = ["authorization_header=Bearer abc"]
    with pytest.raises(ValueError, match="authorization"):
        KiwoomMockOAuthDraftConfig.model_validate(payload)


def test_authorization_header_generation_is_unavailable_and_impossible():
    result = run_kiwoom_mock_oauth_draft_boundary(_config(), explicit_opt_in_ack=True, credential_boundary_ref="boundary-ref")
    assert result.token_request_draft.authorization_header_available is False
    assert "AUTHORIZATION_HEADER_GENERATION_BLOCKED" in result.safety_report.blocked_capabilities


def test_safety_report_includes_all_blocked_oauth_token_api_mockapi_network_live_capabilities():
    result = run_kiwoom_mock_oauth_draft_boundary(_config(), explicit_opt_in_ack=True, credential_boundary_ref="boundary-ref")
    blocked = set(result.safety_report.blocked_capabilities)
    assert {
        "TOKEN_ISSUE_EXECUTION_BLOCKED",
        "TOKEN_REVOKE_EXECUTION_BLOCKED",
        "TOKEN_REFRESH_BLOCKED",
        "TOKEN_STORAGE_BLOCKED",
        "AUTHORIZATION_HEADER_GENERATION_BLOCKED",
        "API_CALL_BLOCKED",
        "MOCKAPI_CALL_BLOCKED",
        "NETWORK_CALL_BLOCKED",
        "LIVE_PROD_BLOCKED",
        "CREDENTIAL_LOADING_BLOCKED",
    }.issubset(blocked)


def test_gap_report_includes_unresolved_oauth_execution_token_storage_refresh_credential_loading_and_mockapi_execution_gaps():
    result = run_kiwoom_mock_oauth_draft_boundary(_config(), explicit_opt_in_ack=True, credential_boundary_ref="boundary-ref")
    categories = set(result.gap_report.gap_categories)
    assert {
        KiwoomMockOAuthGapCategory.KIWOOM_MOCK_OAUTH_EXECUTION_MODE_NOT_ALLOWED,
        KiwoomMockOAuthGapCategory.KIWOOM_MOCK_OAUTH_MISSING_EXECUTABLE_TRANSPORT,
        KiwoomMockOAuthGapCategory.KIWOOM_MOCK_OAUTH_MOCKAPI_CALL_NOT_ALLOWED,
        KiwoomMockOAuthGapCategory.KIWOOM_MOCK_OAUTH_CREDENTIAL_FILE_REFERENCE_DETECTED,
    }.issubset(categories)


def test_audit_record_is_redacted_and_contains_no_raw_credential_token_material():
    result = run_kiwoom_mock_oauth_draft_boundary(_config(), explicit_opt_in_ack=True, credential_boundary_ref="boundary-ref")
    record = result.audit_records[0]
    assert record.redaction_applied is True
    assert record.contains_secret_material is False


def test_fixture_loaded_draft_data_can_be_passed_through_engine_without_env_var_read_or_credential_file_read(tmp_path):
    fixture_path = tmp_path / "kiwoom_mock_oauth_engine_fixture.json"
    fixture_path.write_text(json.dumps(kiwoom_mock_oauth_engine_fixture_payload()), encoding="utf-8")
    config = load_kiwoom_mock_oauth_draft_fixture(fixture_path)
    result = run_kiwoom_mock_oauth_draft_boundary(config, explicit_opt_in_ack=True, credential_boundary_ref="boundary-ref")
    assert result.no_env_read is True
    assert result.no_credentials_loaded is True

