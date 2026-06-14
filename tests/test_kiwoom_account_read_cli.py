import json

from stock_risk_mcp.cli import main


def _run(capsys, args):
    main(args)
    return json.loads(capsys.readouterr().out)


def test_account_read_health_plan_run_reports_show_and_preview_cli(tmp_path, capsys):
    db = tmp_path / "risk.sqlite3"
    health = _run(capsys, ["kiwoom-account-read-health", "--db", str(db)])
    plan = _run(capsys, ["kiwoom-account-read-plan", "--db", str(db), "--endpoint-id", "kt00018"])
    dry = _run(capsys, [
        "kiwoom-account-read-run", "--db", str(db), "--endpoint-id", "kt00018",
        "--enable-real-network", "--enable-account-read", "--credential-source", "ENV",
        "--allow-auth-token-request", "--confirm-account", "--account-fingerprint", "mock",
        "--i-understand-this-can-read-account-data", "--kill-switch-inactive", "--dry-run",
    ])
    reports = _run(capsys, ["kiwoom-account-read-reports", "--db", str(db)])
    shown = _run(capsys, ["kiwoom-account-read-show", "--db", str(db), "--run-id", dry["run_id"]])
    preview = _run(capsys, [
        "kiwoom-account-read-reconcile-preview", "--db", str(db), "--run-id", dry["run_id"],
        "--kill-switch-inactive",
    ])
    text = json.dumps([health, plan, dry, reports, shown, preview]).lower()

    assert health["status"] == "DISABLED"
    assert plan["would_run"] is False
    assert dry["status"] == "DRY_RUN"
    assert reports["reports"]
    assert preview["orders_submitted"] is False
    for forbidden in ("account_number", "appkey", "secretkey", "authorization", "raw_response"):
        assert forbidden not in text
