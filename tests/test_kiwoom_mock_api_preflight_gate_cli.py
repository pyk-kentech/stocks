import json

import pytest

from stock_risk_mcp.cli import main
from tests.test_kiwoom_mock_api_preflight_gate_models import (
    kiwoom_mock_api_preflight_gate_fixture_payload,
)


def write(path, payload):
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def run(capsys, args):
    main(args)
    return json.loads(capsys.readouterr().out)


def test_cli_commands_output_expected_reports(tmp_path, capsys):
    fixture_file = write(tmp_path / "preflight.json", kiwoom_mock_api_preflight_gate_fixture_payload())
    check_file = tmp_path / "preflight-check.json"
    readiness_file = tmp_path / "preflight-readiness.json"
    safety_file = tmp_path / "preflight-safety.json"
    gap_file = tmp_path / "preflight-gap.json"
    audit_file = tmp_path / "preflight-audit.json"

    check_result = run(
        capsys,
        ["kiwoom-mock-api-preflight-check", "--fixture-file", str(fixture_file), "--output-file", str(check_file)],
    )
    readiness_result = run(
        capsys,
        [
            "kiwoom-mock-api-preflight-readiness-report",
            "--fixture-file",
            str(fixture_file),
            "--output-file",
            str(readiness_file),
        ],
    )
    safety_result = run(
        capsys,
        ["kiwoom-mock-api-preflight-safety-report", "--fixture-file", str(fixture_file), "--output-file", str(safety_file)],
    )
    gap_result = run(
        capsys,
        ["kiwoom-mock-api-preflight-gap-report", "--fixture-file", str(fixture_file), "--output-file", str(gap_file)],
    )
    audit_result = run(
        capsys,
        ["kiwoom-mock-api-preflight-audit-report", "--fixture-file", str(fixture_file), "--output-file", str(audit_file)],
    )

    assert check_result["status"] == "COMPLETED"
    assert readiness_result["status"] == "COMPLETED"
    assert safety_result["status"] == "COMPLETED"
    assert gap_result["status"] == "COMPLETED"
    assert audit_result["status"] == "COMPLETED"

    check_json = json.loads(check_file.read_text(encoding="utf-8"))
    readiness_json = json.loads(readiness_file.read_text(encoding="utf-8"))
    safety_json = json.loads(safety_file.read_text(encoding="utf-8"))
    gap_json = json.loads(gap_file.read_text(encoding="utf-8"))
    audit_json = json.loads(audit_file.read_text(encoding="utf-8"))

    assert check_json["preflight_gate_only"] is True
    assert check_json["non_executable"] is True
    assert readiness_json["readiness_decision"] == "DRAFT_READY"
    assert safety_json["mock_only"] is True
    assert "HTTP_CLIENT_CREATION_BLOCKED" in safety_json["blocked_capabilities"]
    assert "PREFLIGHT_EXECUTION_NOT_IMPLEMENTED" in gap_json["gap_categories"]
    assert audit_json["redaction_applied"] is True


def test_remote_parquet_non_local_fixture_paths_are_rejected(capsys):
    for path_value in ("https://mockapi.kiwoom.com/preflight.json", "preflight.parquet"):
        result = run(capsys, ["kiwoom-mock-api-preflight-gap-report", "--fixture-file", path_value])
        assert result["status"] == "FAILED"
        assert result["errors"]


def test_cli_rejects_production_domain_markers(tmp_path, capsys):
    payload = kiwoom_mock_api_preflight_gate_fixture_payload(
        documented_mock_domain="https://api.kiwoom.com"
    )
    fixture_file = write(tmp_path / "fixture.json", payload)
    result = run(capsys, ["kiwoom-mock-api-preflight-check", "--fixture-file", str(fixture_file)])
    assert result["status"] == "FAILED"
    assert "production domain" in result["errors"][0].lower()


def test_cli_rejects_raw_secret_token_account_auth_markers(tmp_path, capsys):
    payload = kiwoom_mock_api_preflight_gate_fixture_payload()
    payload["transport_draft_config"]["request_envelope_draft"]["body_draft"]["field_value_previews"]["stk_cd"] = "Bearer abc"
    fixture_file = write(tmp_path / "fixture.json", payload)
    result = run(capsys, ["kiwoom-mock-api-preflight-safety-report", "--fixture-file", str(fixture_file)])
    assert result["status"] == "FAILED"
    assert "authorization" in result["errors"][0].lower()


def test_cli_has_no_env_credential_token_network_behavior(tmp_path, capsys):
    fixture_file = write(tmp_path / "preflight.json", kiwoom_mock_api_preflight_gate_fixture_payload())
    result = run(capsys, ["kiwoom-mock-api-preflight-check", "--fixture-file", str(fixture_file)])
    assert result["no_environment_read"] is True
    assert result["no_credential_file_read"] is True
    assert result["no_credentials_loaded"] is True
    assert result["no_token_loaded"] is True
    assert result["no_http_client_created"] is True
    assert result["no_http_session_created"] is True
    assert result["no_network_call"] is True
