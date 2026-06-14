import json

from stock_risk_mcp.cli import main


def test_order_intent_cli_create_evaluate_execute_and_list(tmp_path, capsys) -> None:
    db = tmp_path / "risk.sqlite3"
    main([
        "create-order-intent", "--db", str(db), "--ticker", "AAPL", "--region", "US",
        "--side", "BUY", "--order-type", "LIMIT", "--quantity", "1", "--limit-price", "100",
        "--stop-loss-price", "95", "--source-type", "manual", "--reason", "test",
    ])
    created = json.loads(capsys.readouterr().out)
    intent_id = created["order_intent"]["order_intent_id"]
    main(["order-intents-list", "--db", str(db), "--ticker", "AAPL"])
    listed = json.loads(capsys.readouterr().out)
    main(["evaluate-order-intents", "--db", str(db), "--order-intent-id", intent_id])
    evaluated = json.loads(capsys.readouterr().out)
    main(["paper-execute-approved-intents", "--db", str(db), "--order-intent-id", intent_id])
    executed = json.loads(capsys.readouterr().out)
    main(["paper-executions-list", "--db", str(db), "--ticker", "AAPL"])
    papers = json.loads(capsys.readouterr().out)

    assert listed["order_intents"]
    assert evaluated["results"][0]["intent"]["status"] == "EXECUTION_APPROVED"
    assert executed["results"][0]["intent"]["status"] == "PAPER_EXECUTED"
    assert papers["paper_executions"]


def test_create_order_intent_validation_returns_json(tmp_path, capsys) -> None:
    main([
        "create-order-intent", "--db", str(tmp_path / "risk.sqlite3"), "--ticker", "AAPL",
        "--region", "US", "--side", "BUY", "--order-type", "LIMIT",
        "--source-type", "manual", "--reason", "test", "--confidence-score", "2",
    ])
    result = json.loads(capsys.readouterr().out)
    assert result["status"] == "FAILED"
    assert result["errors"]


def test_order_intent_cli_missing_selected_id_returns_json(tmp_path, capsys) -> None:
    main([
        "evaluate-order-intents", "--db", str(tmp_path / "risk.sqlite3"),
        "--order-intent-id", "missing",
    ])
    result = json.loads(capsys.readouterr().out)
    assert result["status"] == "FAILED"
    assert result["errors"]


def test_create_order_intent_invalid_side_returns_json(tmp_path, capsys) -> None:
    main([
        "create-order-intent", "--db", str(tmp_path / "risk.sqlite3"), "--ticker", "AAPL",
        "--region", "US", "--side", "INVALID", "--order-type", "LIMIT",
        "--source-type", "manual", "--reason", "test",
    ])
    result = json.loads(capsys.readouterr().out)
    assert result["status"] == "FAILED"
    assert result["errors"]
