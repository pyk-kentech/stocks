import json

import pytest

from stock_risk_mcp.kiwoom_mock_api_preflight_gate_fixture import (
    load_kiwoom_mock_api_preflight_gate_fixture,
)
from stock_risk_mcp.kiwoom_mock_api_preflight_gate_guard import (
    validate_kiwoom_mock_api_preflight_gate_metadata_safety,
)
from stock_risk_mcp.kiwoom_mock_api_preflight_gate_models import (
    KiwoomMockApiExecutionReadiness,
    KiwoomMockApiPreflightAuditRecord,
    KiwoomMockApiPreflightDependencyRef,
    KiwoomMockApiPreflightGateConfig,
    KiwoomMockApiPreflightGapCategory,
    KiwoomMockApiPreflightGapReport,
    KiwoomMockApiPreflightReadinessReport,
    KiwoomMockApiPreflightRequestCategory,
    KiwoomMockApiPreflightSafetyReport,
)


def kiwoom_mock_api_preflight_gate_fixture_payload(
    *,
    documented_category: str = "QUOTE",
    documented_path: str = "/api/dostk/mrkcond",
    documented_mock_domain: str = "https://mockapi.kiwoom.com",
) -> dict:
    return {
        "schema_version": "v6.7-kiwoom-mock-api-preflight-gate",
        "fixture_format": "json",
        "config_id": "kiwoom-mock-api-preflight-gate-1",
        "credential_boundary_ref": {
            "ref_id": "kiwoom-mock-credential-boundary-ref-1",
            "ref_kind": "KIWOOM_MOCK_CREDENTIAL_BOUNDARY",
            "local_path": "docs/superpowers/plans/2026-06-18-kiwoom-mock-credential-environment-boundary-design.md",
        },
        "oauth_draft_boundary_ref": {
            "ref_id": "kiwoom-mock-oauth-draft-ref-1",
            "ref_kind": "KIWOOM_MOCK_OAUTH_DRAFT_BOUNDARY",
            "local_path": "docs/superpowers/plans/2026-06-18-kiwoom-mock-oauth-token-draft-boundary-design.md",
        },
        "transport_draft_ref": {
            "ref_id": "kiwoom-mock-transport-draft-ref-1",
            "ref_kind": "KIWOOM_MOCK_API_TRANSPORT_DRAFT_BOUNDARY",
            "local_path": "docs/superpowers/plans/2026-06-18-kiwoom-mock-api-transport-request-envelope-boundary-design.md",
        },
        "transport_draft_config": {
            "schema_version": "v6.6-kiwoom-mock-api-transport-draft-boundary",
            "fixture_format": "json",
            "config_id": "kiwoom-mock-api-transport-draft-config-1",
            "endpoint_evidence_ref": {
                "endpoint_ref_id": "kiwoom-mock-endpoint-1",
                "source_evidence_document_id": "KIWOOM-REST-EVIDENCE-PACK",
                "documented_api_id": "KT00017",
                "documented_category": documented_category,
                "documented_method": "POST",
                "documented_path": documented_path,
                "documented_mock_domain": documented_mock_domain,
                "documented_production_domain": "https://api.kiwoom.com",
                "documented_mock_support": True,
                "documented_krx_only_note": "KRX only",
                "evidence_only": True,
                "executable": False,
                "production_domain_blocked": True,
            },
            "request_envelope_draft": {
                "draft_id": "kiwoom-mock-api-request-envelope-1",
                "endpoint_ref_id": "KIWOOM-MOCK-ENDPOINT-1",
                "documented_method": "POST",
                "mock_domain_reference": "MOCK_DOMAIN_REF",
                "request_path": documented_path,
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
                "query_params": [],
                "path_params": [],
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
        },
    }


def test_default_gate_is_disabled_and_non_executable():
    config = KiwoomMockApiPreflightGateConfig.model_validate(
        kiwoom_mock_api_preflight_gate_fixture_payload()
    )
    assert config.disabled_by_default is True
    assert config.preflight_gate_only is True
    assert config.non_executable is True
    assert config.offline_only is True


def test_required_safety_flags_are_true():
    config = KiwoomMockApiPreflightGateConfig.model_validate(
        kiwoom_mock_api_preflight_gate_fixture_payload()
    )
    assert config.mock_only is True
    assert config.local_file_only is True
    assert config.no_http_client_created is True
    assert config.no_network_call is True
    assert config.no_authorization_header_generated is True


def test_dependency_refs_construct_as_local_reference_only():
    config = KiwoomMockApiPreflightGateConfig.model_validate(
        kiwoom_mock_api_preflight_gate_fixture_payload()
    )
    assert isinstance(config.credential_boundary_ref, KiwoomMockApiPreflightDependencyRef)
    assert config.credential_boundary_ref.local_path.endswith("kiwoom-mock-credential-environment-boundary-design.md")


@pytest.mark.parametrize(
    ("data", "pattern"),
    [
        ({"authorization": "Bearer abc"}, "authorization"),
        ({"access_token": "abc"}, "token"),
        ({"secretkey": "raw-secret"}, "secret"),
        ({"account_number": "123456"}, "account"),
        ({"http_client": "requests.Session()"}, "http client"),
    ],
)
def test_raw_secret_token_account_auth_markers_are_rejected(data, pattern):
    with pytest.raises(ValueError, match=pattern):
        validate_kiwoom_mock_api_preflight_gate_metadata_safety(data, context="test")


def test_readiness_safety_gap_and_audit_models_construct():
    readiness = KiwoomMockApiPreflightReadinessReport(
        readiness_report_id="preflight-readiness-1",
        request_category=KiwoomMockApiPreflightRequestCategory.QUOTE,
        readiness_decision=KiwoomMockApiExecutionReadiness.DRAFT_READY,
        rationale="quote endpoint remains future-execution candidate only",
        blocked_capabilities=[],
    )
    safety = KiwoomMockApiPreflightSafetyReport(
        safety_report_id="preflight-safety-1",
        blocked_capabilities=["HTTP_CLIENT_CREATION_BLOCKED"],
        findings=[],
    )
    gap = KiwoomMockApiPreflightGapReport(
        gap_report_id="preflight-gap-1",
        gap_status="UNRESOLVED_IMPLEMENTATION_GAPS",
        gap_categories=[KiwoomMockApiPreflightGapCategory.PREFLIGHT_HTTP_CLIENT_NOT_ALLOWED],
        blocking_gap_count=1,
        report_only_gap_count=0,
        gaps=["http client remains blocked"],
    )
    audit = KiwoomMockApiPreflightAuditRecord(
        audit_record_id="preflight-audit-1",
        created_at="2026-06-23T00:00:00+09:00",
        source_path="fixtures/kiwoom/preflight_gate_fixture.json",
        redaction_applied=True,
        contains_secret_material=False,
        evidence_refs=["KIWOOM-REST-EVIDENCE-PACK"],
    )
    assert readiness.readiness_decision == KiwoomMockApiExecutionReadiness.DRAFT_READY
    assert "HTTP_CLIENT_CREATION_BLOCKED" in safety.blocked_capabilities
    assert gap.blocking_gap_count == 1
    assert audit.redaction_applied is True


def test_local_fixture_loader_success(tmp_path):
    fixture_path = tmp_path / "kiwoom_mock_api_preflight_gate_fixture.json"
    fixture_path.write_text(
        json.dumps(kiwoom_mock_api_preflight_gate_fixture_payload()),
        encoding="utf-8",
    )
    loaded = load_kiwoom_mock_api_preflight_gate_fixture(fixture_path)
    assert loaded.config_id == "KIWOOM-MOCK-API-PREFLIGHT-GATE-1"


def test_local_fixture_loader_rejects_remote_parquet_non_json(tmp_path):
    with pytest.raises(ValueError, match="local file path"):
        load_kiwoom_mock_api_preflight_gate_fixture("https://mockapi.kiwoom.com/preflight.json")
    with pytest.raises(ValueError, match="parquet remains unsupported"):
        load_kiwoom_mock_api_preflight_gate_fixture(tmp_path / "preflight.parquet")
    with pytest.raises(ValueError, match="explicit local JSON"):
        load_kiwoom_mock_api_preflight_gate_fixture(tmp_path / "preflight.txt")
