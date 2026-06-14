import json

from stock_risk_mcp.cli import main


def _run(capsys, args):
    main(args)
    return json.loads(capsys.readouterr().out)


def test_local_ledger_and_sell_safety_cli_are_offline(tmp_path, capsys):
    db = tmp_path / "risk.sqlite3"
    position = _run(capsys, [
        "local-ledger-position-upsert", "--db", str(db), "--symbol", "005930",
        "--region", "KR", "--quantity", "10", "--reserved-quantity", "2",
    ])
    positions = _run(capsys, ["local-ledger-positions", "--db", str(db)])
    snapshot = _run(capsys, ["local-ledger-snapshot", "--db", str(db)])
    transactions = _run(capsys, ["local-ledger-transactions", "--db", str(db)])
    decision = _run(capsys, [
        "sell-safety-check", "--db", str(db), "--symbol", "005930", "--region", "KR",
        "--quantity", "8",
    ])
    decisions = _run(capsys, ["sell-safety-decisions", "--db", str(db)])
    shown = _run(capsys, [
        "sell-safety-show", "--db", str(db), "--decision-id", decision["sell_safety_decision_id"],
    ])
    text = json.dumps([position, positions, snapshot, transactions, decision, decisions, shown]).lower()

    assert position["available_quantity"] == 8
    assert positions["positions"]
    assert snapshot["position_count"] == 1
    assert transactions["transactions"]
    assert decision["status"] == "APPROVED"
    assert shown["status"] == "APPROVED"
    for forbidden in ("account_number", "authorization", "secretkey", "raw_holdings"):
        assert forbidden not in text


def test_sell_safety_cli_blocks_without_ledger(tmp_path, capsys):
    result = _run(capsys, [
        "sell-safety-check", "--db", str(tmp_path / "risk.sqlite3"),
        "--symbol", "005930", "--region", "KR", "--quantity", "1",
    ])
    assert result["status"] == "BLOCKED"
    assert "LOCAL_LEDGER_UNAVAILABLE" in result["reasons_json"]
