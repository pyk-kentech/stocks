import json

import pytest

from stock_risk_mcp.kiwoom_mock_credential_boundary_fixture import (
    load_kiwoom_mock_credential_boundary_fixture,
)
from stock_risk_mcp.kiwoom_mock_credential_boundary_guard import (
    validate_kiwoom_mock_credential_boundary_metadata_safety,
)
from stock_risk_mcp.kiwoom_mock_credential_boundary_models import (
    KiwoomMockCredentialAuditRecord,
    KiwoomMockCredentialBoundaryConfig,
    KiwoomMockCredentialGapCategory,
    KiwoomMockCredentialGapReport,
    KiwoomMockCredentialRef,
    KiwoomMockCredentialSafetyReport,
    KiwoomMockDomainPolicy,
    KiwoomMockEnvironment,
    KiwoomMockExecutionMode,
    KiwoomMockOptInGate,
    KiwoomMockTokenBoundary,
)


def kiwoom_mock_credential_boundary_fixture_payload():
    return {
        "schema_version": "v6.4-kiwoom-mock-credential-boundary",
        "fixture_format": "json",
        "config_id": "kiwoom-mock-credential-boundary-1",
        "environment": {
            "environment_id": "kiwoom-mock-environment-1",
            "mock_only_env_name": "KIWOOM_MOCK_ONLY",
            "dry_run_env_name": "KIWOOM_MOCK_DRY_RUN",
            "explicit_opt_in_env_name": "KIWOOM_MOCK_EXPLICIT_OPT_IN",
            "app_key_ref_env_name": "KIWOOM_MOCK_APP_KEY_REF",
            "secret_key_ref_env_name": "KIWOOM_MOCK_SECRET_KEY_REF",
            "account_ref_env_name": "KIWOOM_MOCK_ACCOUNT_REF",
            "reads_environment": False,
        },
        "credential_refs": [
            {
                "credential_ref_id": "kiwoom-app-key-ref-1",
                "source_type": "ENVIRONMENT_REFERENCE",
                "source_label": "mock app key reference",
                "reference_name": "KIWOOM_MOCK_APP_KEY_REF",
                "loaded": False,
                "secret_material_present": False,
                "reads_credential_file": False,
            },
            {
                "credential_ref_id": "kiwoom-secret-key-ref-1",
                "source_type": "ENVIRONMENT_REFERENCE",
                "source_label": "mock secret key reference",
                "reference_name": "KIWOOM_MOCK_SECRET_KEY_REF",
                "loaded": False,
                "secret_material_present": False,
                "reads_credential_file": False,
            },
            {
                "credential_ref_id": "kiwoom-account-ref-1",
                "source_type": "ENVIRONMENT_REFERENCE",
                "source_label": "mock account reference",
                "reference_name": "KIWOOM_MOCK_ACCOUNT_REF",
                "loaded": False,
                "secret_material_present": False,
                "reads_credential_file": False,
            },
        ],
        "token_boundary": {
            "token_boundary_id": "kiwoom-token-boundary-1",
            "documented_issue_endpoint_path": "/oauth2/token",
            "documented_revoke_endpoint_path": "/oauth2/revoke",
            "issue_allowed_now": False,
            "revoke_allowed_now": False,
            "execution_mode_requirement": "KIWOOM_MOCK_OPT_IN_EXECUTION_FUTURE",
            "token_issue_attempted": False,
            "token_revoke_attempted": False,
        },
        "domain_policy": {
            "domain_policy_id": "kiwoom-domain-policy-1",
            "allowed_mock_rest_domain": "https://mockapi.kiwoom.com",
            "forbidden_production_rest_domain": "https://api.kiwoom.com",
            "allowed_mock_websocket_domain": "wss://mockapi.kiwoom.com:10000",
            "forbidden_production_websocket_domain": "wss://api.kiwoom.com:10000",
            "krx_only": True,
            "production_domain_execution_allowed": False,
        },
        "opt_in_gate": {
            "opt_in_gate_id": "kiwoom-opt-in-gate-1",
            "gate_state": "BLOCKED_DEFAULT",
            "explicit_opt_in_present": False,
            "mock_execution_allowed_now": False,
            "dry_run_only": True,
        },
        "execution_mode": "KIWOOM_MOCK_DRY_RUN",
        "safety_report": {
            "safety_report_id": "kiwoom-credential-safety-report-1",
            "blocked": False,
            "findings": [],
        },
        "gap_report": {
            "gap_report_id": "kiwoom-credential-gap-report-1",
            "gap_status": "NO_GAPS",
            "gap_categories": [],
            "blocking_gap_count": 0,
            "report_only_gap_count": 0,
            "gaps": [],
        },
        "audit_records": [
            {
                "audit_record_id": "kiwoom-credential-audit-record-1",
                "created_at": "2026-06-22T21:00:00+09:00",
                "source_path": "fixtures/kiwoom/kiwoom_mock_credential_boundary_fixture.json",
                "source_manifest_ids": ["MANIFEST-1"],
            }
        ],
    }


def test_valid_config_construction():
    config = KiwoomMockCredentialBoundaryConfig.model_validate(kiwoom_mock_credential_boundary_fixture_payload())
    assert isinstance(config, KiwoomMockCredentialBoundaryConfig)
    assert config.execution_mode == KiwoomMockExecutionMode.KIWOOM_MOCK_DRY_RUN


def test_required_safety_flags():
    payload = kiwoom_mock_credential_boundary_fixture_payload()
    payload["no_network_call"] = False
    with pytest.raises(ValueError, match="no_network_call"):
        KiwoomMockCredentialBoundaryConfig.model_validate(payload)


def test_environment_policy_construction():
    config = KiwoomMockCredentialBoundaryConfig.model_validate(kiwoom_mock_credential_boundary_fixture_payload())
    assert isinstance(config.environment, KiwoomMockEnvironment)
    assert config.environment.mock_only_env_name == "KIWOOM_MOCK_ONLY"


def test_credential_ref_construction_with_symbolic_refs_only():
    config = KiwoomMockCredentialBoundaryConfig.model_validate(kiwoom_mock_credential_boundary_fixture_payload())
    assert isinstance(config.credential_refs[0], KiwoomMockCredentialRef)
    assert config.credential_refs[0].reference_name == "KIWOOM_MOCK_APP_KEY_REF"


@pytest.mark.parametrize(
    ("field_index", "value", "pattern"),
    [
        (0, "appkey-real-secret", "approved KIWOOM_MOCK"),
        (1, "secret_key_value", "approved KIWOOM_MOCK"),
        (0, "Bearer token", "approved KIWOOM_MOCK"),
        (2, "1234567890", "approved KIWOOM_MOCK"),
    ],
)
def test_credential_ref_rejects_raw_values(field_index, value, pattern):
    payload = kiwoom_mock_credential_boundary_fixture_payload()
    payload["credential_refs"][field_index]["reference_name"] = value
    with pytest.raises(ValueError, match=pattern):
        KiwoomMockCredentialBoundaryConfig.model_validate(payload)


def test_token_boundary_construction():
    config = KiwoomMockCredentialBoundaryConfig.model_validate(kiwoom_mock_credential_boundary_fixture_payload())
    assert isinstance(config.token_boundary, KiwoomMockTokenBoundary)
    assert config.token_boundary.issue_allowed_now is False


def test_token_boundary_does_not_issue_or_revoke_tokens():
    payload = kiwoom_mock_credential_boundary_fixture_payload()
    payload["token_boundary"]["token_issue_attempted"] = True
    with pytest.raises(ValueError, match="token issue"):
        KiwoomMockCredentialBoundaryConfig.model_validate(payload)


def test_domain_policy_construction():
    config = KiwoomMockCredentialBoundaryConfig.model_validate(kiwoom_mock_credential_boundary_fixture_payload())
    assert isinstance(config.domain_policy, KiwoomMockDomainPolicy)
    assert config.domain_policy.allowed_mock_rest_domain == "https://mockapi.kiwoom.com"


def test_production_domain_execution_blocked():
    payload = kiwoom_mock_credential_boundary_fixture_payload()
    payload["domain_policy"]["production_domain_execution_allowed"] = True
    with pytest.raises(ValueError, match="production domain execution"):
        KiwoomMockCredentialBoundaryConfig.model_validate(payload)


def test_mock_domain_policy_represented():
    config = KiwoomMockCredentialBoundaryConfig.model_validate(kiwoom_mock_credential_boundary_fixture_payload())
    assert config.domain_policy.forbidden_production_rest_domain == "https://api.kiwoom.com"
    assert config.domain_policy.krx_only is True


def test_opt_in_gate_disabled_by_default():
    config = KiwoomMockCredentialBoundaryConfig.model_validate(kiwoom_mock_credential_boundary_fixture_payload())
    assert isinstance(config.opt_in_gate, KiwoomMockOptInGate)
    assert config.opt_in_gate.gate_state == "BLOCKED_DEFAULT"


def test_explicit_opt_in_required():
    payload = kiwoom_mock_credential_boundary_fixture_payload()
    payload["opt_in_gate"]["explicit_opt_in_present"] = True
    with pytest.raises(ValueError, match="explicit opt-in"):
        KiwoomMockCredentialBoundaryConfig.model_validate(payload)


def test_execution_mode_remains_non_executable():
    config = KiwoomMockCredentialBoundaryConfig.model_validate(kiwoom_mock_credential_boundary_fixture_payload())
    assert config.non_executable is True
    assert config.execution_mode == KiwoomMockExecutionMode.KIWOOM_MOCK_DRY_RUN


def test_safety_report_construction():
    report = KiwoomMockCredentialBoundaryConfig.model_validate(
        kiwoom_mock_credential_boundary_fixture_payload()
    ).safety_report
    assert isinstance(report, KiwoomMockCredentialSafetyReport)


def test_gap_report_construction():
    report = KiwoomMockCredentialBoundaryConfig.model_validate(
        kiwoom_mock_credential_boundary_fixture_payload()
    ).gap_report
    assert isinstance(report, KiwoomMockCredentialGapReport)


def test_audit_record_construction():
    record = KiwoomMockCredentialBoundaryConfig.model_validate(
        kiwoom_mock_credential_boundary_fixture_payload()
    ).audit_records[0]
    assert isinstance(record, KiwoomMockCredentialAuditRecord)


def test_local_fixture_loader_success(tmp_path):
    fixture_path = tmp_path / "kiwoom_mock_credential_boundary_fixture.json"
    fixture_path.write_text(json.dumps(kiwoom_mock_credential_boundary_fixture_payload()), encoding="utf-8")
    loaded = load_kiwoom_mock_credential_boundary_fixture(fixture_path)
    assert loaded.config_id == "KIWOOM-MOCK-CREDENTIAL-BOUNDARY-1"


def test_local_fixture_loader_failure_includes_source_path(tmp_path):
    fixture_path = tmp_path / "broken.json"
    fixture_path.write_text("{", encoding="utf-8")
    with pytest.raises(ValueError, match=str(fixture_path)):
        load_kiwoom_mock_credential_boundary_fixture(fixture_path)


@pytest.mark.parametrize(
    ("data", "pattern"),
    [
        ({"environment_read": True}, "environment read"),
        ({"credential_file_read": True}, "credential file read"),
        ({"token_issue": True}, "token issue"),
        ({"token_revoke": True}, "token revoke"),
        ({"mockapi_call": True}, "mockapi call"),
        ({"api_call": True}, "api call"),
        ({"websocket_connection": True}, "websocket"),
        ({"network_call": True}, "network"),
        ({"real_order": True}, "real order"),
        ({"live_trading": True}, "live trading"),
        ({"account_mutation": True}, "account mutation"),
        ({"prod_mode": True}, "live/prod"),
        ({"cloud_llm": "gemini"}, "cloud llm"),
        ({"local_llm_runtime": "ollama"}, "local llm runtime"),
        ({"fixture_format": "parquet"}, "parquet"),
    ],
)
def test_guard_rejects_unsafe_markers(data, pattern):
    with pytest.raises(ValueError, match=pattern):
        validate_kiwoom_mock_credential_boundary_metadata_safety(data, context="test")


def test_gap_categories_exist():
    expected = {
        "KIWOOM_CREDENTIAL_BOUNDARY_GENERATED",
        "KIWOOM_CREDENTIAL_BOUNDARY_ONLY",
        "KIWOOM_CREDENTIAL_LOCAL_ONLY",
        "KIWOOM_CREDENTIAL_OFFLINE_ONLY",
        "KIWOOM_CREDENTIAL_DISABLED_BY_DEFAULT",
        "KIWOOM_CREDENTIAL_EXPLICIT_OPT_IN_REQUIRED",
        "KIWOOM_CREDENTIAL_MISSING_INPUT",
        "KIWOOM_CREDENTIAL_MISSING_ENVIRONMENT",
        "KIWOOM_CREDENTIAL_MISSING_DOMAIN_POLICY",
        "KIWOOM_CREDENTIAL_MISSING_OPT_IN_GATE",
        "KIWOOM_CREDENTIAL_MOCK_DOMAIN_REQUIRED",
        "KIWOOM_CREDENTIAL_PRODUCTION_DOMAIN_NOT_ALLOWED",
        "KIWOOM_CREDENTIAL_LIVE_PROD_NOT_ALLOWED",
        "KIWOOM_CREDENTIAL_CREDENTIAL_LOADING_NOT_ALLOWED",
        "KIWOOM_CREDENTIAL_ENVIRONMENT_READ_NOT_ALLOWED",
        "KIWOOM_CREDENTIAL_CREDENTIAL_FILE_READ_NOT_ALLOWED",
        "KIWOOM_CREDENTIAL_TOKEN_ISSUE_NOT_ALLOWED",
        "KIWOOM_CREDENTIAL_TOKEN_REVOKE_NOT_ALLOWED",
        "KIWOOM_CREDENTIAL_API_CALL_NOT_ALLOWED",
        "KIWOOM_CREDENTIAL_MOCKAPI_CALL_NOT_ALLOWED",
        "KIWOOM_CREDENTIAL_WEBSOCKET_NOT_ALLOWED",
        "KIWOOM_CREDENTIAL_NETWORK_CALL_NOT_ALLOWED",
        "KIWOOM_CREDENTIAL_REAL_ORDER_NOT_ALLOWED",
        "KIWOOM_CREDENTIAL_LIVE_TRADING_NOT_ALLOWED",
        "KIWOOM_CREDENTIAL_ACCOUNT_MUTATION_NOT_ALLOWED",
        "KIWOOM_CREDENTIAL_SECRET_VALUE_NOT_ALLOWED",
        "KIWOOM_CREDENTIAL_UNREDACTED_SECRET_NOT_ALLOWED",
        "KIWOOM_CREDENTIAL_CLOUD_LLM_NOT_ALLOWED",
        "KIWOOM_CREDENTIAL_LOCAL_LLM_RUNTIME_NOT_ALLOWED",
        "KIWOOM_CREDENTIAL_PARQUET_NOT_ALLOWED",
    }
    assert expected == {item.value for item in KiwoomMockCredentialGapCategory}


def test_parquet_rejected_in_fixture_metadata():
    payload = kiwoom_mock_credential_boundary_fixture_payload()
    payload["fixture_format"] = "parquet"
    with pytest.raises(ValueError, match="parquet remains unsupported"):
        KiwoomMockCredentialBoundaryConfig.model_validate(payload)
