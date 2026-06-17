import json

from stock_risk_mcp.cli import main
from tests.test_domestic_realtime_fixture import domestic_realtime_fixture_payload, write


def run(capsys, args):
    main(args)
    return json.loads(capsys.readouterr().out)


def test_domestic_realtime_cli_commands_return_json_safe_outputs(tmp_path, capsys):
    fixture_file = write(tmp_path, "domestic_realtime_fixture.json", domestic_realtime_fixture_payload())
    normalized_file = tmp_path / "normalized.json"
    quality_file = tmp_path / "quality.json"
    validated = run(capsys, ["domestic-realtime-profile-validate", "--fixture-file", str(fixture_file)])
    planned = run(capsys, ["domestic-realtime-plan-show", "--fixture-file", str(fixture_file)])
    normalized = run(capsys, ["domestic-realtime-event-normalize", "--fixture-file", str(fixture_file), "--output-file", str(normalized_file)])
    quality = run(capsys, ["domestic-realtime-quality-report", "--fixture-file", str(fixture_file), "--output-file", str(quality_file)])
    assert validated["status"] == "COMPLETED"
    assert planned["subscription_plan"]["plan_id"] == "krx-plan-1"
    assert normalized["status"] == "COMPLETED"
    assert quality["status"] == "COMPLETED"


def test_domestic_realtime_cli_invalid_fixture_is_json_safe(tmp_path, capsys):
    result = run(capsys, ["domestic-realtime-profile-validate", "--fixture-file", str(tmp_path / "missing.json")])
    assert result["status"] == "FAILED"
    assert result["errors"]
