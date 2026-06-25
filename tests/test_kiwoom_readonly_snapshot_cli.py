import json

from stock_risk_mcp.cli import main
from tests.test_kiwoom_readonly_snapshot_models import kiwoom_readonly_snapshot_payload


def write(path, payload):
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def run(capsys, args):
    main(args)
    return json.loads(capsys.readouterr().out)


def test_snapshot_cli_commands_output_expected_reports(tmp_path, capsys):
    fixture_file = write(tmp_path / "kiwoom_readonly_snapshot_fixture.json", kiwoom_readonly_snapshot_payload())
    check = run(capsys, ["kiwoom-readonly-snapshot-composer-check", "--fixture-file", str(fixture_file)])
    coverage = run(capsys, ["kiwoom-readonly-snapshot-source-coverage-report", "--fixture-file", str(fixture_file)])
    freshness = run(capsys, ["kiwoom-readonly-snapshot-freshness-report", "--fixture-file", str(fixture_file)])
    completeness = run(capsys, ["kiwoom-readonly-snapshot-completeness-report", "--fixture-file", str(fixture_file)])
    conflict = run(capsys, ["kiwoom-readonly-snapshot-conflict-report", "--fixture-file", str(fixture_file)])
    snapshot = run(capsys, ["kiwoom-readonly-domestic-stock-snapshot-report", "--fixture-file", str(fixture_file)])
    v710 = run(capsys, ["kiwoom-readonly-snapshot-v7-10-integration-report", "--fixture-file", str(fixture_file)])
    v712 = run(capsys, ["kiwoom-readonly-snapshot-v7-12-integration-report", "--fixture-file", str(fixture_file)])
    v713 = run(capsys, ["kiwoom-readonly-snapshot-v7-13-integration-report", "--fixture-file", str(fixture_file)])
    safety = run(capsys, ["kiwoom-readonly-snapshot-safety-report", "--fixture-file", str(fixture_file)])
    gap = run(capsys, ["kiwoom-readonly-snapshot-gap-report", "--fixture-file", str(fixture_file)])

    assert check["readiness"] in {"SNAPSHOT_READY", "PARTIAL", "STALE", "CONFLICT", "DATA_GAP", "BLOCKED", "REJECTED"}
    for report in (coverage, freshness, completeness, conflict, snapshot, v710, v712, v713, safety, gap):
        assert report["report_only"] is True


def test_snapshot_cli_rejects_remote_or_parquet_or_missing(capsys, tmp_path):
    missing = run(capsys, ["kiwoom-readonly-snapshot-composer-check", "--fixture-file", str(tmp_path / "missing.json")])
    remote = run(capsys, ["kiwoom-readonly-snapshot-source-coverage-report", "--fixture-file", "https://example.com/snapshot.json"])
    parquet = run(capsys, ["kiwoom-readonly-snapshot-source-coverage-report", "--fixture-file", "snapshot.parquet"])
    assert missing["status"] == "FAILED"
    assert remote["status"] == "FAILED"
    assert parquet["status"] == "FAILED"
