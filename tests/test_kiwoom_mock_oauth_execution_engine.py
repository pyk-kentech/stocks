import os

import pytest

from stock_risk_mcp.kiwoom_mock_oauth_execution_engine import (
    execute_kiwoom_mock_oauth,
)
from stock_risk_mcp.kiwoom_mock_oauth_execution_models import (
    KiwoomMockOAuthExecutionConfig,
    KiwoomMockOAuthExecutionMode,
)
from tests.test_kiwoom_mock_oauth_execution_models import (
    kiwoom_mock_oauth_execution_fixture_payload,
)


def _config(**overrides):
    payload = kiwoom_mock_oauth_execution_fixture_payload()
    payload.update(overrides)
    return KiwoomMockOAuthExecutionConfig.model_validate(payload)


def test_missing_explicit_opt_in_fails_closed(monkeypatch):
    monkeypatch.setenv("KIWOOM_MOCK_APP_KEY", "app-key")
    monkeypatch.setenv("KIWOOM_MOCK_SECRET_KEY", "secret-key")
    with pytest.raises(ValueError, match="explicit opt-in"):
        execute_kiwoom_mock_oauth(
            _config(),
            execute=False,
            acknowledge_mock_oauth_execution=False,
            mock_domain=False,
            transport=lambda request: {"token_type": "bearer", "token": "abc", "expires_dt": "20260623010000"},
        )


def test_missing_credentials_fail_closed_with_redacted_error(monkeypatch):
    monkeypatch.delenv("KIWOOM_MOCK_APP_KEY", raising=False)
    monkeypatch.delenv("KIWOOM_MOCK_SECRET_KEY", raising=False)
    with pytest.raises(ValueError, match="missing mock credentials"):
        execute_kiwoom_mock_oauth(
            _config(),
            execute=True,
            acknowledge_mock_oauth_execution=True,
            mock_domain=True,
            transport=lambda request: {"token_type": "bearer", "token": "abc", "expires_dt": "20260623010000"},
        )


def test_token_request_uses_mocked_http_transport_only(monkeypatch):
    monkeypatch.setenv("KIWOOM_MOCK_APP_KEY", "app-key")
    monkeypatch.setenv("KIWOOM_MOCK_SECRET_KEY", "secret-key")
    calls = []

    def transport(request):
        calls.append(request)
        return {"token_type": "bearer", "token": "abc123", "expires_dt": "20260623010000"}

    result = execute_kiwoom_mock_oauth(
        _config(execution_mode="TOKEN_REQUEST"),
        execute=True,
        acknowledge_mock_oauth_execution=True,
        mock_domain=True,
        transport=transport,
    )
    assert len(calls) == 1
    assert result.token_result.execution_mode == KiwoomMockOAuthExecutionMode.TOKEN_REQUEST
    assert result.token_result.token_present is True
    assert result.token_result.access_token_redacted == "REDACTED"


def test_token_revoke_uses_mocked_http_transport_only(monkeypatch):
    monkeypatch.setenv("KIWOOM_MOCK_APP_KEY", "app-key")
    monkeypatch.setenv("KIWOOM_MOCK_SECRET_KEY", "secret-key")
    calls = []

    def transport(request):
        calls.append(request)
        return {"return_code": 0, "return_msg": "revoked"}

    result = execute_kiwoom_mock_oauth(
        _config(execution_mode="TOKEN_REVOKE"),
        execute=True,
        acknowledge_mock_oauth_execution=True,
        mock_domain=True,
        transport=transport,
    )
    assert len(calls) == 1
    assert result.token_result.execution_mode == KiwoomMockOAuthExecutionMode.TOKEN_REVOKE
    assert result.token_result.token_present is False


def test_no_raw_secret_or_token_output(monkeypatch):
    monkeypatch.setenv("KIWOOM_MOCK_APP_KEY", "app-key")
    monkeypatch.setenv("KIWOOM_MOCK_SECRET_KEY", "secret-key")
    result = execute_kiwoom_mock_oauth(
        _config(),
        execute=True,
        acknowledge_mock_oauth_execution=True,
        mock_domain=True,
        transport=lambda request: {"token_type": "bearer", "token": "raw-token-value", "expires_dt": "20260623010000"},
    )
    dumped = result.model_dump_json()
    assert "raw-token-value" not in dumped
    assert "secret-key" not in dumped
    assert "app-key" not in dumped


def test_token_is_not_persisted(monkeypatch, tmp_path):
    monkeypatch.setenv("KIWOOM_MOCK_APP_KEY", "app-key")
    monkeypatch.setenv("KIWOOM_MOCK_SECRET_KEY", "secret-key")
    before = {path.name for path in tmp_path.iterdir()}
    result = execute_kiwoom_mock_oauth(
        _config(),
        execute=True,
        acknowledge_mock_oauth_execution=True,
        mock_domain=True,
        transport=lambda request: {"token_type": "bearer", "token": "abc", "expires_dt": "20260623010000"},
    )
    after = {path.name for path in tmp_path.iterdir()}
    assert before == after
    assert result.token_result.persisted_to_disk is False


def test_engine_never_reads_production_credential_names(monkeypatch):
    monkeypatch.setenv("KIWOOM_APP_KEY", "prod-app-key")
    monkeypatch.setenv("KIWOOM_SECRET_KEY", "prod-secret-key")
    monkeypatch.setenv("KIWOOM_MOCK_APP_KEY", "mock-app-key")
    monkeypatch.setenv("KIWOOM_MOCK_SECRET_KEY", "mock-secret-key")
    result = execute_kiwoom_mock_oauth(
        _config(),
        execute=True,
        acknowledge_mock_oauth_execution=True,
        mock_domain=True,
        transport=lambda request: {"token_type": "bearer", "token": "abc", "expires_dt": "20260623010000"},
    )
    assert result.audit_records[0].redaction_applied is True
    dumped = result.model_dump_json()
    assert "prod-app-key" not in dumped
    assert "prod-secret-key" not in dumped
