import json

import pytest

from stock_risk_mcp.kiwoom_mock_api_transport_draft_fixture import (
    load_kiwoom_mock_api_transport_draft_fixture,
)
from stock_risk_mcp.kiwoom_mock_api_transport_draft_guard import (
    validate_kiwoom_mock_api_transport_draft_metadata_safety,
)
from stock_risk_mcp.kiwoom_mock_api_transport_draft_models import (
    KiwoomMockApiBodyDraft,
    KiwoomMockApiEndpointEvidenceRef,
    KiwoomMockApiErrorResponseDraft,
    KiwoomMockApiHeaderDraft,
    KiwoomMockApiPathParamDraft,
    KiwoomMockApiQueryParamDraft,
    KiwoomMockApiRequestEnvelopeDraft,
    KiwoomMockApiRetryTimeoutPolicy,
    KiwoomMockApiTransportAuditRecord,
    KiwoomMockApiTransportDraftConfig,
    KiwoomMockApiTransportGapCategory,
    KiwoomMockApiTransportGapReport,
    KiwoomMockApiTransportPolicy,
    KiwoomMockApiTransportSafetyReport,
)


def kiwoom_mock_api_transport_draft_fixture_payload():
    return {
        "schema_version": "v6.6-kiwoom-mock-api-transport-draft-boundary",
        "fixture_format": "json",
        "config_id": "kiwoom-mock-api-transport-draft-config-1",
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
            "gap_categories": [
                "KIWOOM_MOCK_API_TRANSPORT_MISSING_EXECUTABLE_TRANSPORT",
                "KIWOOM_MOCK_API_AUTHORIZATION_HEADER_GENERATION_NOT_ALLOWED",
                "KIWOOM_MOCK_API_TOKEN_LOAD_NOT_ALLOWED",
            ],
            "blocking_gap_count": 3,
            "report_only_gap_count": 0,
            "gaps": [
                "HTTP client creation remains blocked.",
                "Authorization header generation remains blocked.",
                "Token loading remains blocked.",
            ],
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


def test_default_config_is_disabled_draft_only_mock_only_offline_only_non_executable():
    config = KiwoomMockApiTransportDraftConfig.model_validate(
        kiwoom_mock_api_transport_draft_fixture_payload()
    )
    assert config.disabled_by_default is True
    assert config.mock_only is True
    assert config.kiwoom_mock_api_transport_draft_only is True
    assert config.offline_only is True
    assert config.non_executable is True


def test_required_safety_flags_are_true():
    config = KiwoomMockApiTransportDraftConfig.model_validate(
        kiwoom_mock_api_transport_draft_fixture_payload()
    )
    assert config.transport_boundary_only is True
    assert config.request_envelope_only is True
    assert config.credential_ref_only is True
    assert config.token_ref_only is True
    assert config.no_http_client_created is True
    assert config.no_http_session_created is True
    assert config.no_token_used is True


def test_endpoint_evidence_ref_is_mock_only_and_non_executable():
    config = KiwoomMockApiTransportDraftConfig.model_validate(
        kiwoom_mock_api_transport_draft_fixture_payload()
    )
    endpoint = config.endpoint_evidence_ref
    assert isinstance(endpoint, KiwoomMockApiEndpointEvidenceRef)
    assert endpoint.evidence_only is True
    assert endpoint.executable is False
    assert endpoint.documented_mock_domain == "https://mockapi.kiwoom.com"


def test_production_domain_execution_is_blocked():
    payload = kiwoom_mock_api_transport_draft_fixture_payload()
    payload["endpoint_evidence_ref"]["documented_mock_domain"] = "https://api.kiwoom.com"
    with pytest.raises(ValueError, match="production domain"):
        KiwoomMockApiTransportDraftConfig.model_validate(payload)


@pytest.mark.parametrize(
    ("data", "pattern"),
    [
        ({"authorization": "Bearer abc"}, "authorization"),
        ({"access_token": "abc"}, "token"),
        ({"secretkey": "raw-secret"}, "secret"),
        ({"account_number": "1234567890"}, "account"),
        ({"http_client": "requests.Session()"}, "http client"),
        ({"websocket_connection": "wss://mockapi.kiwoom.com:10000"}, "websocket"),
    ],
)
def test_raw_secret_token_account_auth_transport_markers_are_rejected(data, pattern):
    with pytest.raises(ValueError, match=pattern):
        validate_kiwoom_mock_api_transport_draft_metadata_safety(data, context="test")


def test_authorization_header_generation_is_not_available():
    config = KiwoomMockApiTransportDraftConfig.model_validate(
        kiwoom_mock_api_transport_draft_fixture_payload()
    )
    draft = config.request_envelope_draft
    assert draft.authorization_header_generation_available is False
    assert "AUTHORIZATION_HEADER_GENERATION_BLOCKED" in config.safety_report.blocked_capabilities


def test_request_envelope_draft_is_non_executable_and_ref_only():
    config = KiwoomMockApiTransportDraftConfig.model_validate(
        kiwoom_mock_api_transport_draft_fixture_payload()
    )
    draft = config.request_envelope_draft
    assert isinstance(draft, KiwoomMockApiRequestEnvelopeDraft)
    assert draft.http_client_available is False
    assert draft.http_session_available is False
    assert draft.network_execution_enabled is False
    assert draft.token_ref_id == "KIWOOM_MOCK_TOKEN_REF"


def test_header_body_query_path_drafts_remain_report_only_and_redacted():
    config = KiwoomMockApiTransportDraftConfig.model_validate(
        kiwoom_mock_api_transport_draft_fixture_payload()
    )
    assert isinstance(config.request_envelope_draft.headers[0], KiwoomMockApiHeaderDraft)
    assert isinstance(config.request_envelope_draft.body_draft, KiwoomMockApiBodyDraft)
    assert isinstance(config.request_envelope_draft.query_params[0], KiwoomMockApiQueryParamDraft)
    assert isinstance(config.request_envelope_draft.path_params[0], KiwoomMockApiPathParamDraft)
    assert config.request_envelope_draft.body_draft.serializable_report_only is True
    assert config.request_envelope_draft.headers[1].redaction_applied is True


def test_retry_timeout_policy_is_representation_only():
    config = KiwoomMockApiTransportDraftConfig.model_validate(
        kiwoom_mock_api_transport_draft_fixture_payload()
    )
    policy = config.retry_timeout_policy
    assert isinstance(policy, KiwoomMockApiRetryTimeoutPolicy)
    assert policy.timeout_execution_enabled is False
    assert policy.retry_loop_enabled is False
    assert policy.sleep_backoff_enabled is False


def test_error_response_draft_is_local_only_and_non_live():
    config = KiwoomMockApiTransportDraftConfig.model_validate(
        kiwoom_mock_api_transport_draft_fixture_payload()
    )
    error_draft = config.error_response_draft
    assert isinstance(error_draft, KiwoomMockApiErrorResponseDraft)
    assert error_draft.captures_live_response is False
    assert error_draft.wraps_transport_exception is False


def test_safety_report_exposes_blocked_capabilities():
    report = KiwoomMockApiTransportDraftConfig.model_validate(
        kiwoom_mock_api_transport_draft_fixture_payload()
    ).safety_report
    assert isinstance(report, KiwoomMockApiTransportSafetyReport)
    assert "HTTP_CLIENT_CREATION_BLOCKED" in report.blocked_capabilities


def test_gap_report_exposes_unresolved_transport_gaps():
    report = KiwoomMockApiTransportDraftConfig.model_validate(
        kiwoom_mock_api_transport_draft_fixture_payload()
    ).gap_report
    assert isinstance(report, KiwoomMockApiTransportGapReport)
    assert report.blocking_gap_count == 3
    assert (
        KiwoomMockApiTransportGapCategory.KIWOOM_MOCK_API_AUTHORIZATION_HEADER_GENERATION_NOT_ALLOWED
        in report.gap_categories
    )


def test_audit_record_is_redacted_and_non_secret_bearing():
    record = KiwoomMockApiTransportDraftConfig.model_validate(
        kiwoom_mock_api_transport_draft_fixture_payload()
    ).audit_records[0]
    assert isinstance(record, KiwoomMockApiTransportAuditRecord)
    assert record.redaction_applied is True
    assert record.contains_secret_material is False


def test_local_fixture_loader_reads_only_local_draft_fixture_data(tmp_path):
    fixture_path = tmp_path / "kiwoom_mock_api_transport_draft_fixture.json"
    fixture_path.write_text(
        json.dumps(kiwoom_mock_api_transport_draft_fixture_payload()),
        encoding="utf-8",
    )
    loaded = load_kiwoom_mock_api_transport_draft_fixture(fixture_path)
    assert loaded.config_id == "KIWOOM-MOCK-API-TRANSPORT-DRAFT-CONFIG-1"


def test_fixture_loader_does_not_read_remote_paths_or_parquet(tmp_path):
    with pytest.raises(ValueError, match="local file path"):
        load_kiwoom_mock_api_transport_draft_fixture("https://mockapi.kiwoom.com/transport.json")
    with pytest.raises(ValueError, match="parquet remains unsupported"):
        load_kiwoom_mock_api_transport_draft_fixture(tmp_path / "transport.parquet")

