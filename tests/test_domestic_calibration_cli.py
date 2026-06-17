import json

from stock_risk_mcp.cli import main
from tests.test_domestic_calibration_fixture import calibration_fixture_payload
from tests.test_domestic_realtime_fixture import write


def run(capsys, args):
    main(args)
    return json.loads(capsys.readouterr().out)


def test_domestic_calibration_cli_commands_return_json_safe_outputs(tmp_path, capsys):
    fixture_file = write(
        tmp_path,
        "domestic_calibration_fixture.json",
        calibration_fixture_payload(tmp_path),
    )
    run_file = tmp_path / "calibration_run.json"
    compare_file = tmp_path / "policy_compare.json"
    gate_file = tmp_path / "promotion_gate.json"
    validated = run(capsys, ["domestic-calibration-config-validate", "--fixture-file", str(fixture_file)])
    calibrated = run(capsys, ["domestic-calibration-run", "--fixture-file", str(fixture_file), "--output-file", str(run_file)])
    compared = run(capsys, ["domestic-policy-compare", "--fixture-file", str(fixture_file), "--output-file", str(compare_file)])
    gated = run(capsys, ["domestic-promotion-gate-report", "--fixture-file", str(fixture_file), "--output-file", str(gate_file)])
    assert validated["status"] == "COMPLETED"
    assert calibrated["status"] == "COMPLETED"
    assert compared["status"] == "COMPLETED"
    assert gated["status"] == "COMPLETED"


def test_domestic_calibration_cli_invalid_fixture_is_json_safe(tmp_path, capsys):
    result = run(capsys, ["domestic-calibration-config-validate", "--fixture-file", str(tmp_path / "missing.json")])
    assert result["status"] == "FAILED"
    assert result["errors"]
