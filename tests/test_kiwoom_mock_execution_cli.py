import json

from stock_risk_mcp.cli import main
from stock_risk_mcp.order_intent import ExecutionMode
from stock_risk_mcp.order_intent_service import OrderIntentService
from stock_risk_mcp.order_risk_gate import RiskGateConfig
from stock_risk_mcp.repository import RiskRepository
from stock_risk_mcp.realtime_market_data import MarketRegion
from tests.test_order_risk_gate import _intent


def test_kiwoom_mock_execution_cli_commands(tmp_path, capsys) -> None:
    db = tmp_path / "risk.sqlite3"
    repository = RiskRepository(db)
    service = OrderIntentService(repository)
    intent = service.create(_intent(ticker="005930", region=MarketRegion.KR))
    service.evaluate(intent.order_intent_id, RiskGateConfig(), ExecutionMode.PAPER)

    main(["kiwoom-mock-execution-health", "--db", str(db)])
    health = json.loads(capsys.readouterr().out)
    main(["kiwoom-mock-submit-order", "--db", str(db), "--order-intent-id", intent.order_intent_id])
    submitted = json.loads(capsys.readouterr().out)
    main(["kiwoom-mock-submit-order", "--db", str(db), "--order-intent-id", intent.order_intent_id])
    duplicate = json.loads(capsys.readouterr().out)
    main(["kiwoom-mock-cancel-order", "--db", str(db), "--mock-order-id", submitted["receipt"]["broker_order_id"]])
    cancelled = json.loads(capsys.readouterr().out)
    main(["kiwoom-mock-order-status", "--db", str(db), "--mock-order-id", submitted["receipt"]["broker_order_id"]])
    status = json.loads(capsys.readouterr().out)
    main(["kiwoom-mock-order-requests-list", "--db", str(db)])
    requests = json.loads(capsys.readouterr().out)
    main(["kiwoom-mock-order-receipts-list", "--db", str(db)])
    receipts = json.loads(capsys.readouterr().out)

    assert health["status"] == "CONNECTED"
    assert submitted["receipt"]["status"] == "FILLED"
    assert duplicate["receipt"]["status"] == "REJECTED"
    assert cancelled["receipt"]["status"] == "CANCELLED"
    assert status["receipt"]["status"] in {"UNKNOWN", "CANCELLED", "FILLED"}
    assert len(requests["kiwoom_mock_order_requests"]) == 2
    assert len(receipts["kiwoom_mock_order_receipts"]) == 4
    assert "authorization" not in str([health, submitted, duplicate, cancelled, status]).lower()
