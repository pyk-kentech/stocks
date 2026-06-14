import json

from stock_risk_mcp.cli import main


def test_broker_cli_health_submit_lists_and_duplicate(tmp_path, capsys) -> None:
    db = tmp_path / "risk.sqlite3"
    intent_id = _approved_intent(db, capsys)
    main(["broker-adapter-health", "--db", str(db), "--broker", "mock", "--environment", "LOCAL_MOCK"])
    health = json.loads(capsys.readouterr().out)
    main(["broker-submit-mock-order", "--db", str(db), "--order-intent-id", intent_id])
    first = json.loads(capsys.readouterr().out)
    main(["broker-submit-mock-order", "--db", str(db), "--order-intent-id", intent_id])
    duplicate = json.loads(capsys.readouterr().out)
    main(["broker-order-requests-list", "--db", str(db), "--order-intent-id", intent_id])
    requests = json.loads(capsys.readouterr().out)
    main(["broker-order-receipts-list", "--db", str(db), "--order-intent-id", intent_id])
    receipts = json.loads(capsys.readouterr().out)

    assert health["status"] == "CONNECTED"
    assert first["receipt"]["status"] == "FILLED"
    assert duplicate["receipt"]["status"] == "REJECTED"
    assert "duplicate broker submission" in duplicate["receipt"]["message"]
    assert len(requests["broker_order_requests"]) == 2
    assert len(receipts["broker_order_receipts"]) == 2


def test_broker_cli_non_mock_is_json_safe_rejection(tmp_path, capsys) -> None:
    db = tmp_path / "risk.sqlite3"
    intent_id = _approved_intent(db, capsys)
    main([
        "broker-submit-mock-order", "--db", str(db), "--order-intent-id", intent_id,
        "--broker", "KIWOOM",
    ])
    result = json.loads(capsys.readouterr().out)
    assert result["receipt"]["status"] == "REJECTED"


def _approved_intent(db, capsys):
    main([
        "create-order-intent", "--db", str(db), "--ticker", "AAPL", "--region", "US",
        "--side", "BUY", "--order-type", "LIMIT", "--quantity", "1", "--limit-price", "100",
        "--stop-loss-price", "95", "--source-type", "manual", "--reason", "test",
    ])
    created = json.loads(capsys.readouterr().out)
    intent_id = created["order_intent"]["order_intent_id"]
    main(["evaluate-order-intents", "--db", str(db), "--order-intent-id", intent_id])
    capsys.readouterr()
    return intent_id
