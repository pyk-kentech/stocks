import json

from stock_risk_mcp.cli import main
from tests.test_domestic_realtime_fixture import write
from tests.test_domestic_replay_fixture import domestic_replay_fixture_payload


def run(capsys, args):
    main(args)
    return json.loads(capsys.readouterr().out)


def test_domestic_replay_cli_commands_return_json_safe_outputs(tmp_path, capsys):
    fixture_file = write(
        tmp_path,
        "domestic_replay_fixture.json",
        domestic_replay_fixture_payload(),
    )
    run_file = tmp_path / "replay_report.json"
    metrics_file = tmp_path / "replay_metrics.json"
    readiness_file = tmp_path / "replay_readiness.json"
    validated = run(capsys, ["domestic-replay-config-validate", "--fixture-file", str(fixture_file)])
    replayed = run(capsys, ["domestic-replay-run", "--fixture-file", str(fixture_file), "--output-file", str(run_file)])
    metrics = run(capsys, ["domestic-replay-metrics-report", "--fixture-file", str(fixture_file), "--output-file", str(metrics_file)])
    readiness = run(capsys, ["domestic-replay-promotion-readiness", "--fixture-file", str(fixture_file), "--output-file", str(readiness_file)])
    assert validated["status"] == "COMPLETED"
    assert replayed["status"] == "COMPLETED"
    assert metrics["status"] == "COMPLETED"
    assert readiness["status"] == "COMPLETED"


def test_domestic_replay_cli_invalid_fixture_is_json_safe(tmp_path, capsys):
    result = run(capsys, ["domestic-replay-config-validate", "--fixture-file", str(tmp_path / "missing.json")])
    assert result["status"] == "FAILED"
    assert result["errors"]
