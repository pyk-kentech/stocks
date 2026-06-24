import json

from stock_risk_mcp.cli import main
from tests.test_controlled_mock_dry_run_models import controlled_mock_dry_run_payload


def write(path, payload):
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def run(capsys, args):
    main(args)
    return json.loads(capsys.readouterr().out)


def test_controlled_mock_dry_run_cli_commands_output_expected_reports(tmp_path, capsys):
    fixture_file = write(tmp_path / "controlled_mock_dry_run_fixture.json", controlled_mock_dry_run_payload())
    check = run(capsys, ["controlled-mock-dry-run-check", "--fixture-file", str(fixture_file)])
    preview = run(capsys, ["mock-order-intent-preview-report", "--fixture-file", str(fixture_file)])
    preflight = run(capsys, ["mock-preflight-rehearsal-report", "--fixture-file", str(fixture_file)])
    provider = run(capsys, ["mock-provider-readiness-rehearsal-report", "--fixture-file", str(fixture_file)])
    market = run(capsys, ["mock-market-regime-rehearsal-report", "--fixture-file", str(fixture_file)])
    sizing = run(capsys, ["mock-position-sizing-rehearsal-report", "--fixture-file", str(fixture_file)])
    event_risk = run(capsys, ["mock-event-risk-rehearsal-report", "--fixture-file", str(fixture_file)])
    breadth = run(capsys, ["mock-breadth-outlier-routing-rehearsal-report", "--fixture-file", str(fixture_file)])
    order_gate = run(capsys, ["mock-order-gate-rehearsal-report", "--fixture-file", str(fixture_file)])
    budget = run(capsys, ["mock-risk-budget-rehearsal-report", "--fixture-file", str(fixture_file)])
    kill_switch = run(capsys, ["mock-kill-switch-rehearsal-report", "--fixture-file", str(fixture_file)])
    rollback = run(capsys, ["mock-rollback-rehearsal-report", "--fixture-file", str(fixture_file)])
    audit = run(capsys, ["mock-audit-trail-rehearsal-report", "--fixture-file", str(fixture_file)])
    boundary = run(capsys, ["mock-dry-run-boundary-violation-report", "--fixture-file", str(fixture_file)])
    gap = run(capsys, ["mock-dry-run-gap-report", "--fixture-file", str(fixture_file)])

    assert check["decision"] in {"BLOCKED", "RESEARCH_ONLY", "DRY_RUN_REHEARSED", "MOCK_EXECUTION_REVIEW_READY", "WATCH_ONLY", "GAP", "REJECTED"}
    for report in (preview, preflight, provider, market, sizing, event_risk, breadth, order_gate, budget, kill_switch, rollback, audit, boundary, gap):
        assert report["report_only"] is True


def test_controlled_mock_dry_run_cli_missing_fixture_is_json_safe(tmp_path, capsys):
    result = run(capsys, ["controlled-mock-dry-run-check", "--fixture-file", str(tmp_path / "missing.json")])
    assert result["status"] == "FAILED"
    assert result["errors"]


def test_controlled_mock_dry_run_cli_rejects_remote_or_parquet_paths(capsys):
    remote = run(capsys, ["mock-order-intent-preview-report", "--fixture-file", "https://example.com/mock_dry_run.json"])
    parquet = run(capsys, ["mock-order-intent-preview-report", "--fixture-file", "mock_dry_run.parquet"])
    assert remote["status"] == "FAILED"
    assert parquet["status"] == "FAILED"
