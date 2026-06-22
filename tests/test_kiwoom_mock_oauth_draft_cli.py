import json

import pytest

from stock_risk_mcp.cli import main
from tests.test_kiwoom_mock_oauth_draft_engine import kiwoom_mock_oauth_engine_fixture_payload


def write(path, payload):
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def run(capsys, args):
    main(args)
    return json.loads(capsys.readouterr().out)


def test_kiwoom_mock_oauth_cli_commands_return_non_executable_json_outputs(tmp_path, capsys):
    fixture_file = write(tmp_path / "kiwoom_mock_oauth_fixture.json", kiwoom_mock_oauth_engine_fixture_payload())
    request_file = tmp_path / "kiwoom_mock_oauth_request.json"
    response_file = tmp_path / "kiwoom_mock_oauth_response.json"
    revoke_file = tmp_path / "kiwoom_mock_oauth_revoke.json"
    lifecycle_file = tmp_path / "kiwoom_mock_oauth_lifecycle.json"
    safety_file = tmp_path / "kiwoom_mock_oauth_safety.json"
    gap_file = tmp_path / "kiwoom_mock_oauth_gap.json"

    request_result = run(
        capsys,
        ["kiwoom-mock-oauth-token-request-draft", "--fixture-file", str(fixture_file), "--output-file", str(request_file)],
    )
    response_result = run(
        capsys,
        ["kiwoom-mock-oauth-token-response-draft-report", "--fixture-file", str(fixture_file), "--output-file", str(response_file)],
    )
    revoke_result = run(
        capsys,
        ["kiwoom-mock-oauth-token-revoke-draft", "--fixture-file", str(fixture_file), "--output-file", str(revoke_file)],
    )
    lifecycle_result = run(
        capsys,
        ["kiwoom-mock-oauth-token-lifecycle-report", "--fixture-file", str(fixture_file), "--output-file", str(lifecycle_file)],
    )
    safety_result = run(
        capsys,
        ["kiwoom-mock-oauth-safety-report", "--fixture-file", str(fixture_file), "--output-file", str(safety_file)],
    )
    gap_result = run(
        capsys,
        ["kiwoom-mock-oauth-gap-report", "--fixture-file", str(fixture_file), "--output-file", str(gap_file)],
    )

    assert request_result["status"] == "COMPLETED"
    assert response_result["status"] == "COMPLETED"
    assert revoke_result["status"] == "COMPLETED"
    assert lifecycle_result["status"] == "COMPLETED"
    assert safety_result["status"] == "COMPLETED"
    assert gap_result["status"] == "COMPLETED"

    request_json = json.loads(request_file.read_text(encoding="utf-8"))
    response_json = json.loads(response_file.read_text(encoding="utf-8"))
    revoke_json = json.loads(revoke_file.read_text(encoding="utf-8"))
    lifecycle_json = json.loads(lifecycle_file.read_text(encoding="utf-8"))
    safety_json = json.loads(safety_file.read_text(encoding="utf-8"))
    gap_json = json.loads(gap_file.read_text(encoding="utf-8"))

    assert request_json["mock_only"] is True
    assert request_json["oauth_draft_only"] is True
    assert request_json["non_executable"] is True
    assert request_json["credential_ref_only"] is True
    assert request_json["request_execution_enabled"] is False

    assert response_json["mock_only"] is True
    assert response_json["stores_real_token"] is False
    assert response_json["token_storage_enabled"] is False

    assert revoke_json["mock_only"] is True
    assert revoke_json["request_execution_enabled"] is False

    assert lifecycle_json["mock_only"] is True
    assert lifecycle_json["refresh_execution_allowed"] is False
    assert lifecycle_json["storage_execution_allowed"] is False

    assert safety_json["mock_only"] is True
    assert "API_CALL_BLOCKED" in safety_json["blocked_capabilities"]

    assert gap_json["mock_only"] is True
    assert "KIWOOM_MOCK_OAUTH_EXECUTION_MODE_NOT_ALLOWED" in gap_json["gap_categories"]


def test_token_request_draft_cli_returns_non_executable_request_draft_output(tmp_path, capsys):
    fixture_file = write(tmp_path / "fixture.json", kiwoom_mock_oauth_engine_fixture_payload())
    result = run(capsys, ["kiwoom-mock-oauth-token-request-draft", "--fixture-file", str(fixture_file)])
    assert result["request_execution_enabled"] is False
    assert result["authorization_header_available"] is False
    assert result["credential_ref_only"] is True


def test_token_response_draft_report_cli_returns_redacted_non_token_bearing_output(tmp_path, capsys):
    fixture_file = write(tmp_path / "fixture.json", kiwoom_mock_oauth_engine_fixture_payload())
    result = run(capsys, ["kiwoom-mock-oauth-token-response-draft-report", "--fixture-file", str(fixture_file)])
    dumped = json.dumps(result).lower()
    assert result["stores_real_token"] is False
    assert "\"access_token\":" not in dumped
    assert "\"authorization\":" not in dumped


def test_token_revoke_draft_cli_returns_non_executable_revoke_draft_output(tmp_path, capsys):
    fixture_file = write(tmp_path / "fixture.json", kiwoom_mock_oauth_engine_fixture_payload())
    result = run(capsys, ["kiwoom-mock-oauth-token-revoke-draft", "--fixture-file", str(fixture_file)])
    assert result["request_execution_enabled"] is False


def test_lifecycle_report_cli_shows_token_storage_and_refresh_blocked(tmp_path, capsys):
    fixture_file = write(tmp_path / "fixture.json", kiwoom_mock_oauth_engine_fixture_payload())
    result = run(capsys, ["kiwoom-mock-oauth-token-lifecycle-report", "--fixture-file", str(fixture_file)])
    assert result["storage_execution_allowed"] is False
    assert result["refresh_execution_allowed"] is False


def test_safety_report_cli_includes_blocked_oauth_token_api_mockapi_websocket_network_live_capabilities(tmp_path, capsys):
    fixture_file = write(tmp_path / "fixture.json", kiwoom_mock_oauth_engine_fixture_payload())
    result = run(capsys, ["kiwoom-mock-oauth-safety-report", "--fixture-file", str(fixture_file)])
    blocked = set(result["blocked_capabilities"])
    assert {
        "TOKEN_ISSUE_EXECUTION_BLOCKED",
        "TOKEN_REVOKE_EXECUTION_BLOCKED",
        "API_CALL_BLOCKED",
        "MOCKAPI_CALL_BLOCKED",
        "NETWORK_CALL_BLOCKED",
        "WEBSOCKET_BLOCKED",
        "LIVE_PROD_BLOCKED",
    }.issubset(blocked)


def test_gap_report_cli_includes_unresolved_oauth_execution_token_storage_refresh_credential_loading_and_mockapi_execution_gaps(tmp_path, capsys):
    fixture_file = write(tmp_path / "fixture.json", kiwoom_mock_oauth_engine_fixture_payload())
    result = run(capsys, ["kiwoom-mock-oauth-gap-report", "--fixture-file", str(fixture_file)])
    categories = set(result["gap_categories"])
    assert {
        "KIWOOM_MOCK_OAUTH_EXECUTION_MODE_NOT_ALLOWED",
        "KIWOOM_MOCK_OAUTH_MISSING_EXECUTABLE_TRANSPORT",
        "KIWOOM_MOCK_OAUTH_MOCKAPI_CALL_NOT_ALLOWED",
        "KIWOOM_MOCK_OAUTH_CREDENTIAL_FILE_REFERENCE_DETECTED",
    }.issubset(categories)


def test_cli_rejects_production_domain_markers(tmp_path, capsys):
    payload = kiwoom_mock_oauth_engine_fixture_payload()
    payload["endpoint_refs"][0]["domain"] = "https://api.kiwoom.com"
    fixture_file = write(tmp_path / "fixture.json", payload)
    result = run(capsys, ["kiwoom-mock-oauth-token-request-draft", "--fixture-file", str(fixture_file)])
    assert result["status"] == "FAILED"
    assert "production domain" in result["errors"][0].lower()


def test_cli_rejects_raw_secret_token_account_auth_markers(tmp_path, capsys):
    payload = kiwoom_mock_oauth_engine_fixture_payload()
    payload["safety_report"]["findings"] = ["authorization_header=Bearer abc"]
    fixture_file = write(tmp_path / "fixture.json", payload)
    result = run(capsys, ["kiwoom-mock-oauth-safety-report", "--fixture-file", str(fixture_file)])
    assert result["status"] == "FAILED"
    assert "authorization" in result["errors"][0].lower()


@pytest.mark.parametrize("path_value", ["https://mockapi.kiwoom.com/fixture.json", "fixture.parquet"])
def test_cli_rejects_remote_parquet_non_local_fixture_paths(path_value, capsys):
    result = run(capsys, ["kiwoom-mock-oauth-gap-report", "--fixture-file", path_value])
    assert result["status"] == "FAILED"
    assert result["errors"]


def test_cli_does_not_require_or_read_environment_variables(tmp_path, capsys):
    fixture_file = write(tmp_path / "fixture.json", kiwoom_mock_oauth_engine_fixture_payload())
    result = run(capsys, ["kiwoom-mock-oauth-safety-report", "--fixture-file", str(fixture_file)])
    assert result["no_env_read"] is True
    assert result["no_credentials_loaded"] is True


def test_cli_does_not_read_credential_files(tmp_path, capsys):
    fixture_file = write(tmp_path / "fixture.json", kiwoom_mock_oauth_engine_fixture_payload())
    result = run(capsys, ["kiwoom-mock-oauth-gap-report", "--fixture-file", str(fixture_file)])
    dumped = json.dumps(result).lower()
    assert "credential file read not allowed" not in dumped


def test_cli_does_not_perform_oauth_token_api_mockapi_websocket_network_calls(tmp_path, capsys):
    fixture_file = write(tmp_path / "fixture.json", kiwoom_mock_oauth_engine_fixture_payload())
    result = run(capsys, ["kiwoom-mock-oauth-safety-report", "--fixture-file", str(fixture_file)])
    assert result["no_token_issued"] is True
    assert result["no_token_revoked"] is True
    assert result["no_api_call"] is True
    assert result["no_mockapi_call"] is True
    assert result["no_websocket_connection"] is True
    assert result["no_network_call"] is True

