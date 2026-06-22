import json

import pytest

from stock_risk_mcp.cli import main
from tests.test_kiwoom_mock_api_transport_draft_engine import (
    kiwoom_mock_api_transport_engine_fixture_payload,
)


def write(path, payload):
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def run(capsys, args):
    main(args)
    return json.loads(capsys.readouterr().out)


def test_kiwoom_mock_api_transport_cli_commands_return_non_executable_json_outputs(tmp_path, capsys):
    fixture_file = write(
        tmp_path / "kiwoom_mock_api_transport_fixture.json",
        kiwoom_mock_api_transport_engine_fixture_payload(),
    )
    request_file = tmp_path / "kiwoom_mock_api_transport_request.json"
    policy_file = tmp_path / "kiwoom_mock_api_transport_policy.json"
    retry_file = tmp_path / "kiwoom_mock_api_transport_retry.json"
    error_file = tmp_path / "kiwoom_mock_api_transport_error.json"
    safety_file = tmp_path / "kiwoom_mock_api_transport_safety.json"
    gap_file = tmp_path / "kiwoom_mock_api_transport_gap.json"

    request_result = run(
        capsys,
        [
            "kiwoom-mock-api-transport-request-envelope-draft",
            "--fixture-file",
            str(fixture_file),
            "--output-file",
            str(request_file),
        ],
    )
    policy_result = run(
        capsys,
        [
            "kiwoom-mock-api-transport-policy-report",
            "--fixture-file",
            str(fixture_file),
            "--output-file",
            str(policy_file),
        ],
    )
    retry_result = run(
        capsys,
        [
            "kiwoom-mock-api-retry-timeout-report",
            "--fixture-file",
            str(fixture_file),
            "--output-file",
            str(retry_file),
        ],
    )
    error_result = run(
        capsys,
        [
            "kiwoom-mock-api-error-response-draft-report",
            "--fixture-file",
            str(fixture_file),
            "--output-file",
            str(error_file),
        ],
    )
    safety_result = run(
        capsys,
        [
            "kiwoom-mock-api-transport-safety-report",
            "--fixture-file",
            str(fixture_file),
            "--output-file",
            str(safety_file),
        ],
    )
    gap_result = run(
        capsys,
        [
            "kiwoom-mock-api-transport-gap-report",
            "--fixture-file",
            str(fixture_file),
            "--output-file",
            str(gap_file),
        ],
    )

    assert request_result["status"] == "COMPLETED"
    assert policy_result["status"] == "COMPLETED"
    assert retry_result["status"] == "COMPLETED"
    assert error_result["status"] == "COMPLETED"
    assert safety_result["status"] == "COMPLETED"
    assert gap_result["status"] == "COMPLETED"

    request_json = json.loads(request_file.read_text(encoding="utf-8"))
    policy_json = json.loads(policy_file.read_text(encoding="utf-8"))
    retry_json = json.loads(retry_file.read_text(encoding="utf-8"))
    error_json = json.loads(error_file.read_text(encoding="utf-8"))
    safety_json = json.loads(safety_file.read_text(encoding="utf-8"))
    gap_json = json.loads(gap_file.read_text(encoding="utf-8"))

    assert request_json["mock_only"] is True
    assert request_json["request_envelope_only"] is True
    assert request_json["non_executable"] is True
    assert request_json["authorization_header_generation_available"] is False
    assert request_json["http_client_available"] is False
    assert request_json["http_session_available"] is False
    assert request_json["network_execution_enabled"] is False

    assert policy_json["mock_only"] is True
    assert policy_json["allowed_mock_rest_domain"] == "https://mockapi.kiwoom.com"

    assert retry_json["mock_only"] is True
    assert retry_json["timeout_execution_enabled"] is False
    assert retry_json["retry_loop_enabled"] is False

    assert error_json["mock_only"] is True
    assert error_json["captures_live_response"] is False

    assert safety_json["mock_only"] is True
    assert "HTTP_CLIENT_CREATION_BLOCKED" in safety_json["blocked_capabilities"]

    assert gap_json["mock_only"] is True
    assert "KIWOOM_MOCK_API_TRANSPORT_MISSING_EXECUTABLE_TRANSPORT" in gap_json["gap_categories"]


def test_request_envelope_draft_cli_returns_non_executable_request_output(tmp_path, capsys):
    fixture_file = write(tmp_path / "fixture.json", kiwoom_mock_api_transport_engine_fixture_payload())
    result = run(capsys, ["kiwoom-mock-api-transport-request-envelope-draft", "--fixture-file", str(fixture_file)])
    assert result["network_execution_enabled"] is False
    assert result["authorization_header_generation_available"] is False
    assert result["http_client_available"] is False


def test_transport_policy_report_cli_returns_mock_domain_only_policy(tmp_path, capsys):
    fixture_file = write(tmp_path / "fixture.json", kiwoom_mock_api_transport_engine_fixture_payload())
    result = run(capsys, ["kiwoom-mock-api-transport-policy-report", "--fixture-file", str(fixture_file)])
    assert result["allowed_mock_rest_domain"] == "https://mockapi.kiwoom.com"
    assert result["krx_only"] is True


def test_retry_timeout_report_cli_is_representation_only(tmp_path, capsys):
    fixture_file = write(tmp_path / "fixture.json", kiwoom_mock_api_transport_engine_fixture_payload())
    result = run(capsys, ["kiwoom-mock-api-retry-timeout-report", "--fixture-file", str(fixture_file)])
    assert result["timeout_execution_enabled"] is False
    assert result["retry_loop_enabled"] is False
    assert result["sleep_backoff_enabled"] is False


def test_error_response_draft_report_cli_returns_local_non_executable_output(tmp_path, capsys):
    fixture_file = write(tmp_path / "fixture.json", kiwoom_mock_api_transport_engine_fixture_payload())
    result = run(capsys, ["kiwoom-mock-api-error-response-draft-report", "--fixture-file", str(fixture_file)])
    assert result["captures_live_response"] is False
    assert result["wraps_transport_exception"] is False


def test_safety_report_cli_includes_blocked_http_api_mockapi_websocket_network_live_prod_capabilities(
    tmp_path, capsys
):
    fixture_file = write(tmp_path / "fixture.json", kiwoom_mock_api_transport_engine_fixture_payload())
    result = run(capsys, ["kiwoom-mock-api-transport-safety-report", "--fixture-file", str(fixture_file)])
    blocked = set(result["blocked_capabilities"])
    assert {
        "AUTHORIZATION_HEADER_GENERATION_BLOCKED",
        "TOKEN_LOADING_BLOCKED",
        "HTTP_CLIENT_CREATION_BLOCKED",
        "HTTP_SESSION_CREATION_BLOCKED",
        "MOCKAPI_CALL_BLOCKED",
        "NETWORK_EXECUTION_BLOCKED",
        "LIVE_PROD_BLOCKED",
    }.issubset(blocked)


def test_gap_report_cli_includes_unresolved_transport_client_session_mockapi_gaps(tmp_path, capsys):
    fixture_file = write(tmp_path / "fixture.json", kiwoom_mock_api_transport_engine_fixture_payload())
    result = run(capsys, ["kiwoom-mock-api-transport-gap-report", "--fixture-file", str(fixture_file)])
    categories = set(result["gap_categories"])
    assert {
        "KIWOOM_MOCK_API_TRANSPORT_MISSING_EXECUTABLE_TRANSPORT",
        "KIWOOM_MOCK_API_HTTP_CLIENT_NOT_ALLOWED",
        "KIWOOM_MOCK_API_HTTP_SESSION_NOT_ALLOWED",
        "KIWOOM_MOCK_API_MOCKAPI_CALL_NOT_ALLOWED",
    }.issubset(categories)


def test_cli_rejects_production_domain_markers(tmp_path, capsys):
    payload = kiwoom_mock_api_transport_engine_fixture_payload()
    payload["endpoint_evidence_ref"]["documented_mock_domain"] = "https://api.kiwoom.com"
    fixture_file = write(tmp_path / "fixture.json", payload)
    result = run(capsys, ["kiwoom-mock-api-transport-request-envelope-draft", "--fixture-file", str(fixture_file)])
    assert result["status"] == "FAILED"
    assert "production domain" in result["errors"][0].lower()


def test_cli_rejects_raw_secret_token_account_auth_markers(tmp_path, capsys):
    payload = kiwoom_mock_api_transport_engine_fixture_payload()
    payload["request_envelope_draft"]["body_draft"]["field_value_previews"]["stk_cd"] = "Bearer abc"
    fixture_file = write(tmp_path / "fixture.json", payload)
    result = run(capsys, ["kiwoom-mock-api-transport-safety-report", "--fixture-file", str(fixture_file)])
    assert result["status"] == "FAILED"
    assert "authorization" in result["errors"][0].lower()


@pytest.mark.parametrize("path_value", ["https://mockapi.kiwoom.com/fixture.json", "fixture.parquet"])
def test_cli_rejects_remote_parquet_non_local_fixture_paths(path_value, capsys):
    result = run(capsys, ["kiwoom-mock-api-transport-gap-report", "--fixture-file", path_value])
    assert result["status"] == "FAILED"
    assert result["errors"]


def test_cli_does_not_require_or_read_environment_variables(tmp_path, capsys):
    fixture_file = write(tmp_path / "fixture.json", kiwoom_mock_api_transport_engine_fixture_payload())
    result = run(capsys, ["kiwoom-mock-api-transport-safety-report", "--fixture-file", str(fixture_file)])
    assert result["no_environment_read"] is True
    assert result["no_credentials_loaded"] is True


def test_cli_does_not_read_credential_files_or_load_tokens(tmp_path, capsys):
    fixture_file = write(tmp_path / "fixture.json", kiwoom_mock_api_transport_engine_fixture_payload())
    result = run(capsys, ["kiwoom-mock-api-transport-gap-report", "--fixture-file", str(fixture_file)])
    assert result["no_credential_file_read"] is True
    assert result["no_token_loaded"] is True
    assert result["no_token_used"] is True
    assert result["no_token_refreshed"] is True


def test_cli_does_not_create_http_client_session_transport_or_network_behavior(tmp_path, capsys):
    fixture_file = write(tmp_path / "fixture.json", kiwoom_mock_api_transport_engine_fixture_payload())
    result = run(capsys, ["kiwoom-mock-api-transport-safety-report", "--fixture-file", str(fixture_file)])
    assert result["no_http_client_created"] is True
    assert result["no_http_session_created"] is True
    assert result["no_api_call"] is True
    assert result["no_mockapi_call"] is True
    assert result["no_websocket_connection"] is True
    assert result["no_network_call"] is True
