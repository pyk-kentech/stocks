import json

from stock_risk_mcp.cli import main
from tests.test_walk_forward_validation_models import walk_forward_validation_payload


def write(path, payload):
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def run(capsys, args):
    main(args)
    return json.loads(capsys.readouterr().out)


def test_walk_forward_validation_cli_commands_output_expected_reports(tmp_path, capsys):
    fixture_file = write(tmp_path / "walk_forward_validation_fixture.json", walk_forward_validation_payload())
    check = run(capsys, ["walk-forward-validation-check", "--fixture-file", str(fixture_file)])
    split = run(capsys, ["walk-forward-split-report", "--fixture-file", str(fixture_file)])
    snooping = run(capsys, ["data-snooping-report", "--fixture-file", str(fixture_file)])
    lineage = run(capsys, ["experiment-lineage-report", "--fixture-file", str(fixture_file)])
    pressure = run(capsys, ["parameter-search-pressure-report", "--fixture-file", str(fixture_file)])
    contamination = run(capsys, ["final-test-contamination-report", "--fixture-file", str(fixture_file)])
    stability = run(capsys, ["strategy-stability-report", "--fixture-file", str(fixture_file)])
    promotion = run(capsys, ["validation-promotion-readiness-report", "--fixture-file", str(fixture_file)])
    assert check["decision"] in {"VALIDATION_READY", "PAPER_READY"}
    assert split["report_only"] is True
    assert snooping["report_only"] is True
    assert lineage["report_only"] is True
    assert pressure["report_only"] is True
    assert contamination["report_only"] is True
    assert stability["report_only"] is True
    assert promotion["report_only"] is True


def test_walk_forward_validation_cli_missing_fixture_is_json_safe(tmp_path, capsys):
    result = run(capsys, ["walk-forward-validation-check", "--fixture-file", str(tmp_path / "missing.json")])
    assert result["status"] == "FAILED"
    assert result["errors"]


def test_walk_forward_validation_cli_rejects_remote_or_parquet_paths(capsys):
    remote = run(capsys, ["walk-forward-split-report", "--fixture-file", "https://example.com/wf.json"])
    parquet = run(capsys, ["walk-forward-split-report", "--fixture-file", "wf.parquet"])
    assert remote["status"] == "FAILED"
    assert parquet["status"] == "FAILED"
