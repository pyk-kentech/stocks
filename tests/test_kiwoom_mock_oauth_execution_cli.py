import json

import stock_risk_mcp.cli as cli_mod

from stock_risk_mcp.cli import main
from stock_risk_mcp.kiwoom_mock_oauth_execution_engine import execute_kiwoom_mock_oauth
from stock_risk_mcp.kiwoom_mock_oauth_execution_fixture import load_kiwoom_mock_oauth_execution_fixture
from tests.test_kiwoom_mock_oauth_execution_models import (
    kiwoom_mock_oauth_execution_fixture_payload,
)


def write(path, payload):
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def run(capsys, args):
    main(args)
    return json.loads(capsys.readouterr().out)


def install_mock_execution(monkeypatch):
    def fake_run(fixture_file, *, execute, acknowledge_mock_oauth_execution, mock_domain):
        fixture = load_kiwoom_mock_oauth_execution_fixture(fixture_file)
        return execute_kiwoom_mock_oauth(
            fixture,
            execute=execute,
            acknowledge_mock_oauth_execution=acknowledge_mock_oauth_execution,
            mock_domain=mock_domain,
            transport=lambda request: (
                {"return_code": 0, "return_msg": "revoked"}
                if fixture.execution_mode.value == "TOKEN_REVOKE"
                else {"token_type": "bearer", "token": "raw-token", "expires_dt": "20260623010000"}
            ),
        )

    monkeypatch.setattr(cli_mod, "_run_kiwoom_mock_oauth_execution", fake_run)


def test_cli_commands_require_explicit_execution_acknowledgement(tmp_path, capsys, monkeypatch):
    monkeypatch.setenv("KIWOOM_MOCK_APP_KEY", "app-key")
    monkeypatch.setenv("KIWOOM_MOCK_SECRET_KEY", "secret-key")
    fixture_file = write(tmp_path / "oauth.json", kiwoom_mock_oauth_execution_fixture_payload())
    result = run(capsys, ["kiwoom-mock-oauth-token-request-execute", "--fixture-file", str(fixture_file)])
    assert result["status"] == "FAILED"
    assert "explicit opt-in" in result["errors"][0].lower()


def test_token_request_execute_cli_uses_redacted_output(tmp_path, capsys, monkeypatch):
    install_mock_execution(monkeypatch)
    monkeypatch.setenv("KIWOOM_MOCK_APP_KEY", "app-key")
    monkeypatch.setenv("KIWOOM_MOCK_SECRET_KEY", "secret-key")
    fixture_file = write(tmp_path / "oauth.json", kiwoom_mock_oauth_execution_fixture_payload())
    result = run(
        capsys,
        [
            "kiwoom-mock-oauth-token-request-execute",
            "--fixture-file",
            str(fixture_file),
            "--mock-domain",
            "--execute",
            "--acknowledge-mock-oauth-execution",
        ],
    )
    dumped = json.dumps(result)
    assert result["token_result"]["token_present"] is True
    assert "app-key" not in dumped
    assert "secret-key" not in dumped
    assert "raw-token" not in dumped


def test_token_revoke_execute_cli_uses_redacted_output(tmp_path, capsys, monkeypatch):
    install_mock_execution(monkeypatch)
    monkeypatch.setenv("KIWOOM_MOCK_APP_KEY", "app-key")
    monkeypatch.setenv("KIWOOM_MOCK_SECRET_KEY", "secret-key")
    payload = kiwoom_mock_oauth_execution_fixture_payload()
    payload["execution_mode"] = "TOKEN_REVOKE"
    fixture_file = write(tmp_path / "oauth_revoke.json", payload)
    result = run(
        capsys,
        [
            "kiwoom-mock-oauth-token-revoke-execute",
            "--fixture-file",
            str(fixture_file),
            "--mock-domain",
            "--execute",
            "--acknowledge-mock-oauth-execution",
        ],
    )
    assert result["token_result"]["execution_mode"] == "TOKEN_REVOKE"
    assert result["token_result"]["token_present"] is False


def test_cli_report_commands_output_redacted_json(tmp_path, capsys):
    fixture_file = write(tmp_path / "oauth.json", kiwoom_mock_oauth_execution_fixture_payload())
    safety = run(capsys, ["kiwoom-mock-oauth-execution-safety-report", "--fixture-file", str(fixture_file)])
    gap = run(capsys, ["kiwoom-mock-oauth-execution-gap-report", "--fixture-file", str(fixture_file)])
    audit = run(capsys, ["kiwoom-mock-oauth-execution-audit-report", "--fixture-file", str(fixture_file)])
    assert "PRODUCTION_DOMAIN_BLOCKED" in safety["blocked_capabilities"]
    assert "MOCK_QUOTE_API_STAGE_NOT_IMPLEMENTED" in gap["gap_categories"]
    assert audit["redaction_applied"] is True


def test_cli_blocks_production_domain(tmp_path, capsys):
    payload = kiwoom_mock_oauth_execution_fixture_payload()
    payload["mock_domain"] = "https://api.kiwoom.com"
    fixture_file = write(tmp_path / "oauth.json", payload)
    result = run(capsys, ["kiwoom-mock-oauth-execution-safety-report", "--fixture-file", str(fixture_file)])
    assert result["status"] == "FAILED"
    assert "production domain" in result["errors"][0].lower()


def test_cli_rejects_remote_or_parquet_fixture_paths(capsys):
    remote = run(capsys, ["kiwoom-mock-oauth-execution-gap-report", "--fixture-file", "https://mockapi.kiwoom.com/oauth.json"])
    parquet = run(capsys, ["kiwoom-mock-oauth-execution-gap-report", "--fixture-file", "oauth.parquet"])
    assert remote["status"] == "FAILED"
    assert parquet["status"] == "FAILED"
