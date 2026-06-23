import json

import pytest

from stock_risk_mcp.kiwoom_mock_oauth_execution_engine import (
    build_kiwoom_mock_oauth_execution_gap_report,
)
from stock_risk_mcp.kiwoom_mock_oauth_execution_fixture import (
    load_kiwoom_mock_oauth_execution_fixture,
)
from stock_risk_mcp.kiwoom_mock_oauth_execution_guard import (
    validate_kiwoom_mock_oauth_execution_metadata_safety,
)
from stock_risk_mcp.kiwoom_mock_oauth_execution_models import (
    KiwoomMockOAuthExecutionConfig,
    KiwoomMockOAuthExecutionGapReport,
    KiwoomMockOAuthExecutionMode,
    KiwoomMockOAuthExecutionSafetyReport,
    KiwoomMockOAuthTokenResult,
)


def kiwoom_mock_oauth_execution_fixture_payload() -> dict:
    return {
        "schema_version": "v6.8-kiwoom-mock-oauth-execution-adapter",
        "fixture_format": "json",
        "config_id": "kiwoom-mock-oauth-execution-config-1",
        "execution_mode": "TOKEN_REQUEST",
        "mock_domain": "https://mockapi.kiwoom.com",
        "allowed_env_var_names": ["KIWOOM_MOCK_APP_KEY", "KIWOOM_MOCK_SECRET_KEY"],
        "timeout_seconds": 5,
        "max_retry_count": 1,
        "retry_backoff_seconds": 0.0,
        "allow_env_read": True,
        "explicit_opt_in_required": True,
        "redact_output": True,
        "persist_token_to_disk": False,
        "allow_token_refresh": False,
        "credential_boundary_ref": "docs/superpowers/plans/2026-06-18-kiwoom-mock-credential-environment-boundary-design.md",
        "oauth_draft_boundary_ref": "docs/superpowers/plans/2026-06-18-kiwoom-mock-oauth-token-draft-boundary-design.md",
        "transport_boundary_ref": "docs/superpowers/plans/2026-06-18-kiwoom-mock-api-transport-request-envelope-boundary-design.md",
        "preflight_boundary_ref": "docs/superpowers/plans/2026-06-18-kiwoom-mock-api-execution-readiness-preflight-gate-design.md",
        "safety_report": {
            "safety_report_id": "kiwoom-mock-oauth-execution-safety-report-1",
            "blocked_capabilities": [
                "PRODUCTION_DOMAIN_BLOCKED",
                "ACCOUNT_PATH_BLOCKED",
                "ORDER_PATH_BLOCKED",
                "QUOTE_PATH_BLOCKED",
                "WEBSOCKET_BLOCKED",
                "LIVE_PROD_BLOCKED",
            ],
            "findings": [],
        },
        "gap_report": {
            "gap_report_id": "kiwoom-mock-oauth-execution-gap-report-1",
            "gap_status": "UNRESOLVED_FUTURE_STAGES",
            "gap_categories": [
                "MOCK_QUOTE_API_STAGE_NOT_IMPLEMENTED",
                "MOCK_ACCOUNT_API_STAGE_NOT_IMPLEMENTED",
                "MOCK_ORDER_API_STAGE_NOT_IMPLEMENTED",
            ],
            "blocking_gap_count": 3,
            "report_only_gap_count": 0,
            "gaps": [
                "quote stage deferred",
                "account stage deferred",
                "order stage deferred",
            ],
        },
        "audit_records": [
            {
                "audit_record_id": "kiwoom-mock-oauth-execution-audit-record-1",
                "created_at": "2026-06-23T00:00:00+09:00",
                "source_path": "fixtures/kiwoom/kiwoom_mock_oauth_execution_fixture.json",
                "redaction_applied": True,
                "contains_secret_material": False,
                "contains_token_material": False,
                "evidence_refs": ["KIWOOM-REST-EVIDENCE-PACK", "KIWOOM-CAPABILITY-MATRIX"],
            }
        ],
    }


def test_default_execution_is_disabled():
    config = KiwoomMockOAuthExecutionConfig.model_validate(
        kiwoom_mock_oauth_execution_fixture_payload()
    )
    assert config.disabled_by_default is True
    assert config.mock_only is True
    assert config.execution_capable is True
    assert config.non_executable_without_opt_in is True


def test_only_mock_credential_env_names_are_accepted():
    config = KiwoomMockOAuthExecutionConfig.model_validate(
        kiwoom_mock_oauth_execution_fixture_payload()
    )
    assert config.allowed_env_var_names == ["KIWOOM_MOCK_APP_KEY", "KIWOOM_MOCK_SECRET_KEY"]


def test_production_domain_is_blocked():
    payload = kiwoom_mock_oauth_execution_fixture_payload()
    payload["mock_domain"] = "https://api.kiwoom.com"
    with pytest.raises(ValueError, match="production domain"):
        KiwoomMockOAuthExecutionConfig.model_validate(payload)


@pytest.mark.parametrize(
    ("data", "pattern"),
    [
        ({"secretkey": "raw-secret"}, "secret"),
        ({"access_token": "raw-token"}, "token"),
        ({"authorization": "Bearer abc"}, "authorization"),
        ({"account_number": "123456"}, "account"),
    ],
)
def test_raw_secret_token_output_markers_are_rejected(data, pattern):
    with pytest.raises(ValueError, match=pattern):
        validate_kiwoom_mock_oauth_execution_metadata_safety(data, context="test")


def test_token_result_is_in_memory_only():
    result = KiwoomMockOAuthTokenResult(
        token_result_id="kiwoom-mock-oauth-token-result-1",
        execution_mode=KiwoomMockOAuthExecutionMode.TOKEN_REQUEST,
        token_type="bearer",
        expires_at="2026-06-23T01:00:00+09:00",
        access_token_redacted="REDACTED",
        token_present=True,
        in_memory_only=True,
        persisted_to_disk=False,
        raw_token_exposed=False,
    )
    dumped = result.model_dump(mode="json")
    assert dumped["token_present"] is True
    assert dumped["persisted_to_disk"] is False
    assert "raw_token" not in dumped


def test_safety_report_blocks_non_oauth_paths():
    report = KiwoomMockOAuthExecutionSafetyReport.model_validate(
        kiwoom_mock_oauth_execution_fixture_payload()["safety_report"]
    )
    assert "ACCOUNT_PATH_BLOCKED" in report.blocked_capabilities
    assert "ORDER_PATH_BLOCKED" in report.blocked_capabilities


def test_gap_report_lists_future_stages():
    report = build_kiwoom_mock_oauth_execution_gap_report(
        KiwoomMockOAuthExecutionConfig.model_validate(
            kiwoom_mock_oauth_execution_fixture_payload()
        )
    )
    assert isinstance(report, KiwoomMockOAuthExecutionGapReport)
    assert "MOCK_QUOTE_API_STAGE_NOT_IMPLEMENTED" in [item.value for item in report.gap_categories]


def test_fixture_loader_reads_local_json_only(tmp_path):
    fixture_path = tmp_path / "kiwoom_mock_oauth_execution_fixture.json"
    fixture_path.write_text(
        json.dumps(kiwoom_mock_oauth_execution_fixture_payload()),
        encoding="utf-8",
    )
    loaded = load_kiwoom_mock_oauth_execution_fixture(fixture_path)
    assert loaded.config_id == "KIWOOM-MOCK-OAUTH-EXECUTION-CONFIG-1"


def test_fixture_loader_rejects_remote_or_parquet(tmp_path):
    with pytest.raises(ValueError, match="local file path"):
        load_kiwoom_mock_oauth_execution_fixture("https://mockapi.kiwoom.com/oauth.json")
    with pytest.raises(ValueError, match="parquet remains unsupported"):
        load_kiwoom_mock_oauth_execution_fixture(tmp_path / "oauth.parquet")
