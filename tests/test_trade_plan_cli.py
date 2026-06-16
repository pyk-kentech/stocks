import json

from stock_risk_mcp.cli import main
from tests.test_trade_plan_fixture import candidate_payload, write


def run(capsys, args):
    main(args)
    return json.loads(capsys.readouterr().out)


def test_trade_plan_run_and_show_commands(tmp_path, capsys):
    fixture_file = write(tmp_path, "trade_plan_fixture.json", candidate_payload())
    output_file = tmp_path / "trade_plan_report.json"

    summary = run(capsys, ["trade-plan-run", "--fixture-file", str(fixture_file), "--output-file", str(output_file)])
    shown = run(capsys, ["trade-plan-show", "--output-file", str(output_file)])

    assert summary["status"] == "COMPLETED"
    assert shown["metadata_json"]["advisory_only"] is True
    assert shown["metadata_json"]["order_intents_created"] is False


def test_trade_plan_invalid_fixture_is_json_safe(tmp_path, capsys):
    result = run(capsys, ["trade-plan-run", "--fixture-file", str(tmp_path / "missing.json")])
    assert result["status"] == "FAILED"
    assert result["errors"]
