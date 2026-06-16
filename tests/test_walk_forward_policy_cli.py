import json

from stock_risk_mcp.cli import main
from tests.test_walk_forward_policy_fixture import fixture_payload, write


def run(capsys, args):
    main(args)
    return json.loads(capsys.readouterr().out)


def test_policy_replay_run_and_show_commands(tmp_path, capsys):
    fixture_file = write(tmp_path, "policy_replay_fixture.json", fixture_payload())
    output_file = tmp_path / "policy_replay_report.json"
    summary = run(capsys, ["policy-replay-run", "--fixture-file", str(fixture_file), "--output-file", str(output_file)])
    shown = run(capsys, ["policy-replay-show", "--output-file", str(output_file)])
    assert summary["status"] == "COMPLETED"
    assert shown["metadata_json"]["advisory_only"] is True
    assert shown["metadata_json"]["production_policy_changed"] is False


def test_policy_replay_invalid_fixture_is_json_safe(tmp_path, capsys):
    result = run(capsys, ["policy-replay-run", "--fixture-file", str(tmp_path / "missing.json")])
    assert result["status"] == "FAILED"
    assert result["errors"]
