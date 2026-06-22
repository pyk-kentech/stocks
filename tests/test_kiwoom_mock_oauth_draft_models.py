import json

import pytest

from stock_risk_mcp.kiwoom_mock_oauth_draft_fixture import load_kiwoom_mock_oauth_draft_fixture
from stock_risk_mcp.kiwoom_mock_oauth_draft_guard import (
    validate_kiwoom_mock_oauth_draft_metadata_safety,
)
from stock_risk_mcp.kiwoom_mock_oauth_draft_models import (
    KiwoomMockOAuthDraftConfig,
    KiwoomMockOAuthEndpointRef,
    KiwoomMockOAuthGapCategory,
    KiwoomMockOAuthGapReport,
    KiwoomMockOAuthSafetyReport,
    KiwoomMockTokenLifecyclePolicy,
    KiwoomMockTokenRequestDraft,
    KiwoomMockTokenResponseDraft,
    KiwoomMockTokenRevokeDraft,
    KiwoomMockOAuthAuditRecord,
)


def kiwoom_mock_oauth_draft_fixture_payload():
    return {
        "schema_version": "v6.5-kiwoom-mock-oauth-draft-boundary",
        "fixture_format": "json",
        "config_id": "kiwoom-mock-oauth-draft-config-1",
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
            "blocked_capabilities": [
                "TOKEN_ISSUE_EXECUTION_BLOCKED",
                "TOKEN_REVOKE_EXECUTION_BLOCKED",
                "TOKEN_REFRESH_BLOCKED",
                "TOKEN_STORAGE_BLOCKED",
                "AUTHORIZATION_HEADER_GENERATION_BLOCKED",
                "PRODUCTION_DOMAIN_EXECUTION_BLOCKED",
            ],
            "findings": [],
        },
        "gap_report": {
            "gap_report_id": "kiwoom-mock-oauth-gap-report-1",
            "gap_status": "UNRESOLVED_IMPLEMENTATION_GAPS",
            "gap_categories": [
                "KIWOOM_MOCK_OAUTH_MISSING_EXECUTABLE_TRANSPORT",
                "KIWOOM_MOCK_OAUTH_EXECUTION_MODE_NOT_ALLOWED",
            ],
            "blocking_gap_count": 2,
            "report_only_gap_count": 0,
            "gaps": [
                "Future opt-in mock execution is intentionally unimplemented.",
                "Credential loading remains intentionally blocked.",
            ],
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


def test_default_config_is_disabled_draft_only_mock_only_offline_only_non_executable():
    config = KiwoomMockOAuthDraftConfig.model_validate(kiwoom_mock_oauth_draft_fixture_payload())
    assert config.disabled_by_default is True
    assert config.mock_only is True
    assert config.oauth_draft_only is True
    assert config.offline_only is True
    assert config.non_executable is True


def test_required_safety_flags_are_true():
    config = KiwoomMockOAuthDraftConfig.model_validate(kiwoom_mock_oauth_draft_fixture_payload())
    assert config.explicit_opt_in_required is True
    assert config.local_file_only is True
    assert config.no_token_issued is True
    assert config.no_token_revoked is True
    assert config.no_env_read is True
    assert config.no_credentials_loaded is True


def test_mock_oauth_endpoint_refs_are_evidence_only():
    config = KiwoomMockOAuthDraftConfig.model_validate(kiwoom_mock_oauth_draft_fixture_payload())
    endpoint = config.endpoint_refs[0]
    assert isinstance(endpoint, KiwoomMockOAuthEndpointRef)
    assert endpoint.evidence_only is True
    assert endpoint.executable is False


def test_production_domain_execution_is_blocked():
    payload = kiwoom_mock_oauth_draft_fixture_payload()
    payload["endpoint_refs"][0]["domain"] = "https://api.kiwoom.com"
    with pytest.raises(ValueError, match="production domain"):
        KiwoomMockOAuthDraftConfig.model_validate(payload)


@pytest.mark.parametrize(
    ("data", "pattern"),
    [
        ({"authorization_header": "Bearer abc"}, "authorization"),
        ({"access_token": "abc"}, "token"),
        ({"secretkey": "raw-secret"}, "secret"),
        ({"account_number": "1234567890"}, "account"),
    ],
)
def test_raw_secret_token_account_auth_markers_are_rejected(data, pattern):
    with pytest.raises(ValueError, match=pattern):
        validate_kiwoom_mock_oauth_draft_metadata_safety(data, context="test")


def test_authorization_header_generation_is_not_available():
    config = KiwoomMockOAuthDraftConfig.model_validate(kiwoom_mock_oauth_draft_fixture_payload())
    assert config.token_request_draft.authorization_header_available is False
    assert "AUTHORIZATION_HEADER_GENERATION_BLOCKED" in config.safety_report.blocked_capabilities


def test_token_request_draft_is_non_executable_and_credential_ref_only():
    config = KiwoomMockOAuthDraftConfig.model_validate(kiwoom_mock_oauth_draft_fixture_payload())
    draft = config.token_request_draft
    assert isinstance(draft, KiwoomMockTokenRequestDraft)
    assert draft.credential_ref_only is True
    assert draft.request_execution_enabled is False


def test_token_response_draft_does_not_store_real_tokens():
    config = KiwoomMockOAuthDraftConfig.model_validate(kiwoom_mock_oauth_draft_fixture_payload())
    draft = config.token_response_draft
    assert isinstance(draft, KiwoomMockTokenResponseDraft)
    assert draft.stores_real_token is False
    assert draft.token_storage_enabled is False


def test_token_revoke_draft_is_non_executable():
    config = KiwoomMockOAuthDraftConfig.model_validate(kiwoom_mock_oauth_draft_fixture_payload())
    draft = config.token_revoke_draft
    assert isinstance(draft, KiwoomMockTokenRevokeDraft)
    assert draft.request_execution_enabled is False


def test_token_lifecycle_policy_represents_lifetime_without_refresh_or_storage_execution():
    config = KiwoomMockOAuthDraftConfig.model_validate(kiwoom_mock_oauth_draft_fixture_payload())
    policy = config.token_lifecycle_policy
    assert isinstance(policy, KiwoomMockTokenLifecyclePolicy)
    assert policy.documented_lifetime_field_name == "expires_dt"
    assert policy.refresh_execution_allowed is False
    assert policy.storage_execution_allowed is False


def test_safety_report_exposes_blocked_capabilities():
    report = KiwoomMockOAuthDraftConfig.model_validate(
        kiwoom_mock_oauth_draft_fixture_payload()
    ).safety_report
    assert isinstance(report, KiwoomMockOAuthSafetyReport)
    assert "TOKEN_ISSUE_EXECUTION_BLOCKED" in report.blocked_capabilities


def test_gap_report_exposes_unresolved_implementation_gaps():
    report = KiwoomMockOAuthDraftConfig.model_validate(
        kiwoom_mock_oauth_draft_fixture_payload()
    ).gap_report
    assert isinstance(report, KiwoomMockOAuthGapReport)
    assert report.blocking_gap_count == 2
    assert KiwoomMockOAuthGapCategory.KIWOOM_MOCK_OAUTH_EXECUTION_MODE_NOT_ALLOWED in report.gap_categories


def test_audit_record_is_redacted_and_non_secret_bearing():
    record = KiwoomMockOAuthDraftConfig.model_validate(
        kiwoom_mock_oauth_draft_fixture_payload()
    ).audit_records[0]
    assert isinstance(record, KiwoomMockOAuthAuditRecord)
    assert record.redaction_applied is True
    assert record.contains_secret_material is False


def test_local_fixture_loader_reads_only_local_draft_fixture_data(tmp_path):
    fixture_path = tmp_path / "kiwoom_mock_oauth_draft_fixture.json"
    fixture_path.write_text(json.dumps(kiwoom_mock_oauth_draft_fixture_payload()), encoding="utf-8")
    loaded = load_kiwoom_mock_oauth_draft_fixture(fixture_path)
    assert loaded.config_id == "KIWOOM-MOCK-OAUTH-DRAFT-CONFIG-1"


def test_fixture_loader_does_not_read_env_vars_or_credential_files(tmp_path):
    with pytest.raises(ValueError, match="local file path"):
        load_kiwoom_mock_oauth_draft_fixture("https://mockapi.kiwoom.com/oauth.json")
    with pytest.raises(ValueError, match="explicit local JSON"):
        load_kiwoom_mock_oauth_draft_fixture(tmp_path / "fixture.txt")

