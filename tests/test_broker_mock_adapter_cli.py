import json

import pytest

from stock_risk_mcp.cli import main
from tests.test_broker_mock_adapter_models import broker_mock_adapter_fixture_payload


def write(path, payload):
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def run(capsys, args):
    main(args)
    return json.loads(capsys.readouterr().out)


def test_broker_mock_adapter_cli_commands_return_mock_only_json_outputs(tmp_path, capsys):
    fixture_file = write(tmp_path / "broker_mock_adapter_fixture.json", broker_mock_adapter_fixture_payload())
    run_file = tmp_path / "broker_mock_adapter_boundary.json"
    capability_file = tmp_path / "broker_mock_adapter_capability.json"
    order_file = tmp_path / "broker_mock_adapter_order_boundary.json"
    safety_file = tmp_path / "broker_mock_adapter_safety.json"
    gap_file = tmp_path / "broker_mock_adapter_gap.json"

    run_result = run(
        capsys,
        ["broker-mock-adapter-boundary-run", "--fixture-file", str(fixture_file), "--output-file", str(run_file)],
    )
    capability_result = run(
        capsys,
        ["broker-mock-adapter-capability-report", "--fixture-file", str(fixture_file), "--output-file", str(capability_file)],
    )
    order_result = run(
        capsys,
        ["broker-mock-adapter-order-boundary-report", "--fixture-file", str(fixture_file), "--output-file", str(order_file)],
    )
    safety_result = run(
        capsys,
        ["broker-mock-adapter-safety-report", "--fixture-file", str(fixture_file), "--output-file", str(safety_file)],
    )
    gap_result = run(
        capsys,
        ["broker-mock-adapter-gap-report", "--fixture-file", str(fixture_file), "--output-file", str(gap_file)],
    )

    assert run_result["status"] == "COMPLETED"
    assert capability_result["status"] == "COMPLETED"
    assert order_result["status"] == "COMPLETED"
    assert safety_result["status"] == "COMPLETED"
    assert gap_result["status"] == "COMPLETED"

    run_json = json.loads(run_file.read_text(encoding="utf-8"))
    capability_json = json.loads(capability_file.read_text(encoding="utf-8"))
    order_json = json.loads(order_file.read_text(encoding="utf-8"))
    safety_json = json.loads(safety_file.read_text(encoding="utf-8"))
    gap_json = json.loads(gap_file.read_text(encoding="utf-8"))

    assert run_json["mock_only"] is True
    assert run_json["paper_only"] is True
    assert run_json["disabled_by_default"] is True
    assert capability_json["mock_only"] is True
    assert capability_json["offline_only"] is True
    assert order_json["mock_only"] is True
    assert order_json["non_executable_by_default"] is True
    assert safety_json["mock_only"] is True
    assert safety_json["no_credentials_loaded"] is True
    assert safety_json["no_network_call"] is True
    assert gap_json["mock_only"] is True
    assert "BROKER_MOCK_BOUNDARY_GENERATED" in gap_json["gap_categories"]


@pytest.mark.parametrize(
    "command",
    [
        "broker-mock-adapter-boundary-run",
        "broker-mock-adapter-capability-report",
        "broker-mock-adapter-order-boundary-report",
        "broker-mock-adapter-safety-report",
        "broker-mock-adapter-gap-report",
    ],
)
def test_broker_mock_adapter_cli_missing_fixture_is_json_safe(command, tmp_path, capsys):
    result = run(capsys, [command, "--fixture-file", str(tmp_path / "missing.json")])
    assert result["status"] == "FAILED"
    assert result["errors"]


def test_broker_mock_adapter_cli_output_has_required_safety_flags(tmp_path, capsys):
    fixture_file = write(tmp_path / "broker_mock_adapter_fixture.json", broker_mock_adapter_fixture_payload())

    result = run(capsys, ["broker-mock-adapter-safety-report", "--fixture-file", str(fixture_file)])

    assert result["mock_only"] is True
    assert result["paper_only"] is True
    assert result["disabled_by_default"] is True
    assert result["explicit_opt_in_required"] is True
    assert result["non_executable_by_default"] is True
    assert result["local_file_only"] is True
    assert result["offline_only"] is True
    assert result["no_real_order"] is True
    assert result["no_real_account_mutation"] is True
    assert result["no_live_trading"] is True
    assert result["no_live_prod"] is True
    assert result["no_production_broker"] is True
    assert result["no_credentials_loaded"] is True
    assert result["no_network_call"] is True
    assert result["no_kiwoom_api_call"] is True
    assert result["no_ls_api_call"] is True
    assert result["no_broker_api_call"] is True
    assert result["no_order_api_call"] is True
    assert result["no_account_api_call"] is True
    assert result["no_provider_api_call"] is True
    assert result["no_cloud_llm"] is True
    assert result["no_local_llm_runtime"] is True


def test_broker_mock_adapter_cli_output_has_no_real_order_or_api_metadata(tmp_path, capsys):
    fixture_file = write(tmp_path / "broker_mock_adapter_fixture.json", broker_mock_adapter_fixture_payload())

    result = run(capsys, ["broker-mock-adapter-order-boundary-report", "--fixture-file", str(fixture_file)])
    dumped = json.dumps(result).lower()

    assert "\"real_order_intent\":" not in dumped
    assert "\"real_account_mutation\":" not in dumped
    assert "\"credential\":" not in dumped
    assert "\"token\":" not in dumped
    assert "\"api_endpoint\":" not in dumped
    assert "\"websocket\":" not in dumped
    assert "\"live_trading\":" not in dumped
    assert "\"live_prod\":" not in dumped
    assert "\"parquet\":" not in dumped
