import json

import pytest

from stock_risk_mcp.cli import main
from tests.test_kiwoom_mock_adapter_models import kiwoom_mock_adapter_fixture_payload


def write(path, payload):
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def run(capsys, args):
    main(args)
    return json.loads(capsys.readouterr().out)


def test_kiwoom_mock_adapter_cli_commands_return_draft_only_json_outputs(tmp_path, capsys):
    fixture_file = write(tmp_path / "kiwoom_mock_adapter_fixture.json", kiwoom_mock_adapter_fixture_payload())
    build_file = tmp_path / "kiwoom_mock_adapter_build.json"
    request_file = tmp_path / "kiwoom_mock_adapter_request.json"
    response_file = tmp_path / "kiwoom_mock_adapter_response.json"
    safety_file = tmp_path / "kiwoom_mock_adapter_safety.json"
    gap_file = tmp_path / "kiwoom_mock_adapter_gap.json"

    build_result = run(
        capsys,
        ["kiwoom-mock-adapter-draft-build", "--fixture-file", str(fixture_file), "--output-file", str(build_file)],
    )
    request_result = run(
        capsys,
        ["kiwoom-mock-adapter-request-draft-report", "--fixture-file", str(fixture_file), "--output-file", str(request_file)],
    )
    response_result = run(
        capsys,
        ["kiwoom-mock-adapter-response-draft-report", "--fixture-file", str(fixture_file), "--output-file", str(response_file)],
    )
    safety_result = run(
        capsys,
        ["kiwoom-mock-adapter-safety-report", "--fixture-file", str(fixture_file), "--output-file", str(safety_file)],
    )
    gap_result = run(
        capsys,
        ["kiwoom-mock-adapter-gap-report", "--fixture-file", str(fixture_file), "--output-file", str(gap_file)],
    )

    assert build_result["status"] == "COMPLETED"
    assert request_result["status"] == "COMPLETED"
    assert response_result["status"] == "COMPLETED"
    assert safety_result["status"] == "COMPLETED"
    assert gap_result["status"] == "COMPLETED"

    build_json = json.loads(build_file.read_text(encoding="utf-8"))
    request_json = json.loads(request_file.read_text(encoding="utf-8"))
    response_json = json.loads(response_file.read_text(encoding="utf-8"))
    safety_json = json.loads(safety_file.read_text(encoding="utf-8"))
    gap_json = json.loads(gap_file.read_text(encoding="utf-8"))

    assert build_json["kiwoom_mock_only"] is True
    assert build_json["draft_only"] is True
    assert build_json["paper_only"] is True
    assert request_json["kiwoom_mock_only"] is True
    assert request_json["non_executable"] is True
    assert response_json["kiwoom_mock_only"] is True
    assert response_json["offline_only"] is True
    assert safety_json["kiwoom_mock_only"] is True
    assert safety_json["no_credentials_loaded"] is True
    assert safety_json["no_api_call"] is True
    assert gap_json["kiwoom_mock_only"] is True
    assert "KIWOOM_MOCK_DRAFT_GENERATED" in gap_json["gap_categories"]


@pytest.mark.parametrize(
    "command",
    [
        "kiwoom-mock-adapter-draft-build",
        "kiwoom-mock-adapter-request-draft-report",
        "kiwoom-mock-adapter-response-draft-report",
        "kiwoom-mock-adapter-safety-report",
        "kiwoom-mock-adapter-gap-report",
    ],
)
def test_kiwoom_mock_adapter_cli_missing_fixture_is_json_safe(command, tmp_path, capsys):
    result = run(capsys, [command, "--fixture-file", str(tmp_path / "missing.json")])
    assert result["status"] == "FAILED"
    assert result["errors"]


def test_kiwoom_mock_adapter_cli_output_has_required_safety_flags(tmp_path, capsys):
    fixture_file = write(tmp_path / "kiwoom_mock_adapter_fixture.json", kiwoom_mock_adapter_fixture_payload())

    result = run(capsys, ["kiwoom-mock-adapter-safety-report", "--fixture-file", str(fixture_file)])

    assert result["kiwoom_mock_only"] is True
    assert result["draft_only"] is True
    assert result["paper_only"] is True
    assert result["disabled_by_default"] is True
    assert result["explicit_opt_in_required"] is True
    assert result["non_executable"] is True
    assert result["local_file_only"] is True
    assert result["offline_only"] is True
    assert result["evidence_backed"] is True
    assert result["no_credentials_loaded"] is True
    assert result["no_oauth_token_request"] is True
    assert result["no_api_call"] is True
    assert result["no_mockapi_call"] is True
    assert result["no_network_call"] is True
    assert result["no_websocket_connection"] is True
    assert result["no_real_order"] is True
    assert result["no_real_account_mutation"] is True
    assert result["no_live_trading"] is True
    assert result["no_live_prod"] is True
    assert result["no_broker_api_call"] is True
    assert result["no_order_api_call"] is True
    assert result["no_account_api_call"] is True
    assert result["no_provider_api_call"] is True
    assert result["no_cloud_llm"] is True
    assert result["no_local_llm_runtime"] is True


def test_kiwoom_mock_adapter_cli_output_has_no_unsafe_metadata(tmp_path, capsys):
    fixture_file = write(tmp_path / "kiwoom_mock_adapter_fixture.json", kiwoom_mock_adapter_fixture_payload())

    result = run(capsys, ["kiwoom-mock-adapter-draft-build", "--fixture-file", str(fixture_file)])
    dumped = json.dumps(result).lower()

    assert "\"credential\":" not in dumped
    assert "\"token\":" not in dumped
    assert "\"authorization_header\":" not in dumped
    assert "\"api_call\":" not in dumped
    assert "\"mockapi_call\":" not in dumped
    assert "\"network_transport\":" not in dumped
    assert "\"websocket\":" not in dumped
    assert "\"real_order_intent\":" not in dumped
    assert "\"real_account_mutation\":" not in dumped
    assert "\"live_trading\":" not in dumped
    assert "\"live_prod\":" not in dumped
    assert "\"parquet\":" not in dumped
