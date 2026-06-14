import json

from stock_risk_mcp.cli import main


def _run(capsys, args):
    main(args)
    return json.loads(capsys.readouterr().out)


def test_smoke_plan_cli_is_offline(capsys):
    result = _run(capsys, ["kiwoom-real-readonly-smoke-plan"])
    assert result["status"] == "PLANNED"
    assert result["network_called"] is False
    assert result["credentials_read"] is False


def test_smoke_run_cli_defaults_blocked_and_dry_run_persists(tmp_path, capsys):
    db = tmp_path / "risk.sqlite3"
    blocked = _run(capsys, [
        "kiwoom-real-readonly-smoke-run", "--db", str(db), "--endpoint-set", "minimal",
    ])
    assert blocked["status"] == "BLOCKED"

    dry_run = _run(capsys, [
        "kiwoom-real-readonly-smoke-run", "--db", str(db), "--endpoint-set", "minimal",
        "--enable-real-network", "--environment", "MOCK",
        "--base-url", "https://mockapi.kiwoom.com",
        "--credential-source", "ENV", "--allow-auth-token-request", "--dry-run",
    ])
    assert dry_run["status"] == "DRY_RUN"
    assert dry_run["endpoint_ids"] == ["ka10001"]

    reports = _run(capsys, ["kiwoom-real-readonly-smoke-reports", "--db", str(db)])
    shown = _run(capsys, [
        "kiwoom-real-readonly-smoke-show", "--db", str(db), "--smoke-run-id", dry_run["smoke_run_id"],
    ])
    assert len(reports["smoke_reports"]) == 2
    assert shown["steps"][0]["request_status"] == "DRY_RUN"
