import json

import pytest

from stock_risk_mcp.cli import main
from tests.test_kiwoom_mock_credential_boundary_models import (
    kiwoom_mock_credential_boundary_fixture_payload,
)


def write(path, payload):
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def run(capsys, args):
    main(args)
    return json.loads(capsys.readouterr().out)


def test_kiwoom_mock_credential_boundary_cli_commands_return_boundary_only_json_outputs(tmp_path, capsys):
    fixture_file = write(
        tmp_path / "kiwoom_mock_credential_boundary_fixture.json",
        kiwoom_mock_credential_boundary_fixture_payload(),
    )
    check_file = tmp_path / "kiwoom_mock_credential_boundary_check.json"
    domain_file = tmp_path / "kiwoom_mock_credential_domain_policy.json"
    opt_in_file = tmp_path / "kiwoom_mock_credential_opt_in.json"
    safety_file = tmp_path / "kiwoom_mock_credential_safety.json"
    gap_file = tmp_path / "kiwoom_mock_credential_gap.json"

    check_result = run(
        capsys,
        ["kiwoom-mock-credential-boundary-check", "--fixture-file", str(fixture_file), "--output-file", str(check_file)],
    )
    domain_result = run(
        capsys,
        ["kiwoom-mock-credential-domain-policy-report", "--fixture-file", str(fixture_file), "--output-file", str(domain_file)],
    )
    opt_in_result = run(
        capsys,
        ["kiwoom-mock-credential-opt-in-report", "--fixture-file", str(fixture_file), "--output-file", str(opt_in_file)],
    )
    safety_result = run(
        capsys,
        ["kiwoom-mock-credential-safety-report", "--fixture-file", str(fixture_file), "--output-file", str(safety_file)],
    )
    gap_result = run(
        capsys,
        ["kiwoom-mock-credential-gap-report", "--fixture-file", str(fixture_file), "--output-file", str(gap_file)],
    )

    assert check_result["status"] == "COMPLETED"
    assert domain_result["status"] == "COMPLETED"
    assert opt_in_result["status"] == "COMPLETED"
    assert safety_result["status"] == "COMPLETED"
    assert gap_result["status"] == "COMPLETED"

    check_json = json.loads(check_file.read_text(encoding="utf-8"))
    domain_json = json.loads(domain_file.read_text(encoding="utf-8"))
    opt_in_json = json.loads(opt_in_file.read_text(encoding="utf-8"))
    safety_json = json.loads(safety_file.read_text(encoding="utf-8"))
    gap_json = json.loads(gap_file.read_text(encoding="utf-8"))

    assert check_json["mock_only"] is True
    assert check_json["credential_boundary_only"] is True
    assert domain_json["mock_only"] is True
    assert domain_json["non_executable"] is True
    assert opt_in_json["mock_only"] is True
    assert opt_in_json["disabled_by_default"] is True
    assert safety_json["mock_only"] is True
    assert safety_json["no_environment_read"] is True
    assert safety_json["no_credential_file_read"] is True
    assert gap_json["mock_only"] is True
    assert gap_json["gap_status"] == "NO_GAPS"


@pytest.mark.parametrize(
    "command",
    [
        "kiwoom-mock-credential-boundary-check",
        "kiwoom-mock-credential-domain-policy-report",
        "kiwoom-mock-credential-opt-in-report",
        "kiwoom-mock-credential-safety-report",
        "kiwoom-mock-credential-gap-report",
    ],
)
def test_kiwoom_mock_credential_boundary_cli_missing_fixture_is_json_safe(command, tmp_path, capsys):
    result = run(capsys, [command, "--fixture-file", str(tmp_path / "missing.json")])
    assert result["status"] == "FAILED"
    assert result["errors"]


def test_kiwoom_mock_credential_boundary_cli_output_has_required_safety_flags(tmp_path, capsys):
    fixture_file = write(
        tmp_path / "kiwoom_mock_credential_boundary_fixture.json",
        kiwoom_mock_credential_boundary_fixture_payload(),
    )

    result = run(capsys, ["kiwoom-mock-credential-safety-report", "--fixture-file", str(fixture_file)])

    assert result["mock_only"] is True
    assert result["credential_boundary_only"] is True
    assert result["disabled_by_default"] is True
    assert result["explicit_opt_in_required"] is True
    assert result["local_file_only"] is True
    assert result["offline_only"] is True
    assert result["non_executable"] is True
    assert result["no_credentials_loaded"] is True
    assert result["no_environment_read"] is True
    assert result["no_credential_file_read"] is True
    assert result["no_token_issued"] is True
    assert result["no_token_revoked"] is True
    assert result["no_api_call"] is True
    assert result["no_mockapi_call"] is True
    assert result["no_websocket_connection"] is True
    assert result["no_network_call"] is True
    assert result["no_real_order"] is True
    assert result["no_live_trading"] is True
    assert result["no_live_prod"] is True
    assert result["no_account_mutation"] is True
    assert result["no_production_domain_execution"] is True
    assert result["no_cloud_llm"] is True
    assert result["no_local_llm_runtime"] is True


def test_kiwoom_mock_credential_boundary_cli_output_has_no_unsafe_metadata(tmp_path, capsys):
    fixture_file = write(
        tmp_path / "kiwoom_mock_credential_boundary_fixture.json",
        kiwoom_mock_credential_boundary_fixture_payload(),
    )

    result = run(capsys, ["kiwoom-mock-credential-boundary-check", "--fixture-file", str(fixture_file)])
    dumped = json.dumps(result).lower()

    assert "\"appkey\":" not in dumped
    assert "\"secret_key_value\":" not in dumped
    assert "\"access_token\":" not in dumped
    assert "\"authorization\":" not in dumped
    assert "\"account_number\":" not in dumped
    assert "\"environment_read\":" not in dumped
    assert "\"credential_file_read\":" not in dumped
    assert "\"api_call\":" not in dumped
    assert "\"mockapi_call\":" not in dumped
    assert "\"network_call\":" not in dumped
    assert "\"websocket\":" not in dumped
    assert "\"real_order\":" not in dumped
    assert "\"live_trading\":" not in dumped
    assert "\"account_mutation\":" not in dumped
    assert "\"parquet\":" not in dumped
