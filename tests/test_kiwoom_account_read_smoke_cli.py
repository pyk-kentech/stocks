import json

from stock_risk_mcp.cli import main


def _run(capsys, args):
    main(args)
    return json.loads(capsys.readouterr().out)


def test_account_read_smoke_plan_run_reports_and_show_cli(tmp_path, capsys):
    db = tmp_path / "risk.sqlite3"
    plan = _run(capsys, ["kiwoom-account-read-smoke-plan"])
    dry = _run(capsys, [
        "kiwoom-account-read-smoke-run", "--db", str(db), "--endpoint-set", "minimal",
        "--enable-real-network", "--enable-account-read", "--credential-source", "ENV",
        "--allow-auth-token-request", "--confirm-account", "--account-fingerprint", "mock",
        "--i-understand-this-can-read-account-data", "--kill-switch-inactive", "--dry-run",
    ])
    reports = _run(capsys, ["kiwoom-account-read-smoke-reports", "--db", str(db)])
    shown = _run(capsys, [
        "kiwoom-account-read-smoke-show", "--db", str(db), "--smoke-run-id", dry["smoke_run_id"],
    ])
    text = json.dumps([plan, dry, reports, shown]).lower()

    assert plan["endpoint_sets"]["minimal"] == ["kt00001"]
    assert dry["status"] == "DRY_RUN"
    assert reports["smoke_reports"]
    assert shown["steps"][0]["endpoint_classification"] == "ACCOUNT_READ"
    for forbidden in ("account_number", "cash_balance", "authorization", "raw_response"):
        assert forbidden not in text


def test_reconcile_cli_uses_explicit_ledger_and_remains_order_free(tmp_path, capsys):
    db = tmp_path / "risk.sqlite3"
    ledger = tmp_path / "ledger.json"
    ledger.write_text(json.dumps({"symbols": [{"symbol": "005930"}]}), encoding="utf-8")
    dry = _run(capsys, [
        "kiwoom-account-read-run", "--db", str(db), "--endpoint-id", "kt00018",
        "--enable-real-network", "--enable-account-read", "--credential-source", "ENV",
        "--allow-auth-token-request", "--confirm-account", "--account-fingerprint", "mock",
        "--i-understand-this-can-read-account-data", "--kill-switch-inactive", "--dry-run",
    ])
    result = _run(capsys, [
        "kiwoom-account-read-reconcile-preview", "--db", str(db), "--run-id", dry["run_id"],
        "--kill-switch-inactive", "--local-ledger-file", str(ledger),
    ])
    assert result["reconciliation_status"] == "ACCOUNT_DATA_UNAVAILABLE"
    assert result["orders_submitted"] is False
    assert result["live_execution_enabled"] is False
