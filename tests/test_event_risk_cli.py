import json

from stock_risk_mcp.cli import main
from tests.test_event_risk_models import event_risk_payload


def write(path, payload):
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def run(capsys, args):
    main(args)
    return json.loads(capsys.readouterr().out)


def test_event_risk_cli_commands_output_expected_reports(tmp_path, capsys):
    fixture = write(tmp_path / "event_risk_fixture.json", event_risk_payload())
    check = run(capsys, ["event-risk-check", "--fixture-file", str(fixture)])
    snapshot = run(capsys, ["economic-calendar-snapshot-report", "--fixture-file", str(fixture)])
    window = run(capsys, ["event-window-report", "--fixture-file", str(fixture)])
    restriction = run(capsys, ["event-restriction-report", "--fixture-file", str(fixture)])
    adjustment = run(capsys, ["position-sizing-event-adjustment-report", "--fixture-file", str(fixture)])
    readiness = run(capsys, ["event-calendar-provider-readiness-report", "--fixture-file", str(fixture)])
    leakage = run(capsys, ["event-risk-leakage-report", "--fixture-file", str(fixture)])
    gap = run(capsys, ["event-risk-gap-report", "--fixture-file", str(fixture)])

    assert check["decision"] in {"ALLOW", "REDUCE_SIZE", "BLOCK_NEW_ENTRY", "REDUCE_ONLY", "WATCH_ONLY", "EVENT_ACTIVE", "COOLDOWN", "DATA_GAP", "BLOCKED", "REJECTED"}
    for report in (snapshot, window, restriction, adjustment, readiness, leakage, gap):
        assert report["report_only"] is True


def test_event_risk_cli_missing_fixture_is_json_safe(tmp_path, capsys):
    result = run(capsys, ["event-risk-check", "--fixture-file", str(tmp_path / "missing.json")])
    assert result["status"] == "FAILED"
    assert result["errors"]


def test_event_risk_cli_rejects_remote_or_parquet_paths(capsys):
    remote = run(capsys, ["economic-calendar-snapshot-report", "--fixture-file", "https://example.com/event_risk.json"])
    parquet = run(capsys, ["economic-calendar-snapshot-report", "--fixture-file", "event_risk.parquet"])
    assert remote["status"] == "FAILED"
    assert parquet["status"] == "FAILED"
