import json

from stock_risk_mcp.cli import main
from tests.test_point_in_time_universe_models import point_in_time_universe_payload


def write(path, payload):
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def run(capsys, args):
    main(args)
    return json.loads(capsys.readouterr().out)


def test_point_in_time_universe_cli_commands_output_expected_reports(tmp_path, capsys):
    fixture_file = write(tmp_path / "point_in_time_universe_fixture.json", point_in_time_universe_payload())
    check = run(capsys, ["point-in-time-universe-check", "--fixture-file", str(fixture_file)])
    universe = run(capsys, ["point-in-time-universe-report", "--fixture-file", str(fixture_file)])
    survivorship = run(capsys, ["survivorship-bias-dataset-report", "--fixture-file", str(fixture_file)])
    lifecycle = run(capsys, ["security-lifecycle-coverage-report", "--fixture-file", str(fixture_file)])
    leakage = run(capsys, ["dataset-leakage-report", "--fixture-file", str(fixture_file)])
    promotion = run(capsys, ["dataset-promotion-readiness-report", "--fixture-file", str(fixture_file)])
    assert check["decision"] == "TRAINING_READY"
    assert universe["report_only"] is True
    assert survivorship["report_only"] is True
    assert lifecycle["report_only"] is True
    assert leakage["report_only"] is True
    assert promotion["report_only"] is True


def test_point_in_time_universe_cli_missing_fixture_is_json_safe(tmp_path, capsys):
    result = run(capsys, ["point-in-time-universe-check", "--fixture-file", str(tmp_path / "missing.json")])
    assert result["status"] == "FAILED"
    assert result["errors"]


def test_point_in_time_universe_cli_rejects_remote_or_parquet_paths(capsys):
    remote = run(capsys, ["dataset-leakage-report", "--fixture-file", "https://example.com/pit.json"])
    parquet = run(capsys, ["dataset-leakage-report", "--fixture-file", "pit.parquet"])
    assert remote["status"] == "FAILED"
    assert parquet["status"] == "FAILED"
