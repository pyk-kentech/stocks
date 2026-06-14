import json

from stock_risk_mcp.cli import main
from stock_risk_mcp.order_intent import ExecutionMode
from stock_risk_mcp.order_intent_service import OrderIntentService
from stock_risk_mcp.order_risk_gate import RiskGateConfig
from stock_risk_mcp.repository import RiskRepository
from stock_risk_mcp.realtime_market_data import MarketRegion
from tests.test_order_risk_gate import _intent


def _run(capsys, args):
    main(args)
    return json.loads(capsys.readouterr().out)


def test_sandbox_health_plan_and_dry_run_cli_are_offline(tmp_path, capsys):
    db = tmp_path / "risk.sqlite3"
    repository = RiskRepository(db)
    service = OrderIntentService(repository)
    intent = service.create(_intent(ticker="005930", region=MarketRegion.KR, quantity=1))
    service.evaluate(intent.order_intent_id, RiskGateConfig(), ExecutionMode.SANDBOX, enable_sandbox_order=True)

    health = _run(capsys, ["kiwoom-sandbox-order-health", "--db", str(db)])
    plan = _run(capsys, ["kiwoom-sandbox-order-plan", "--db", str(db), "--order-intent-id", intent.order_intent_id])
    dry = _run(capsys, [
        "kiwoom-sandbox-order-submit", "--db", str(db), "--order-intent-id", intent.order_intent_id,
        "--enable-real-network", "--enable-sandbox-order", "--credential-source", "ENV",
        "--allow-auth-token-request", "--dry-run",
    ])
    requests = _run(capsys, ["kiwoom-sandbox-order-requests", "--db", str(db)])
    receipts = _run(capsys, ["kiwoom-sandbox-order-receipts", "--db", str(db)])

    assert health["status"] == "DISABLED"
    assert plan["would_submit"] is True
    assert dry["receipt"]["status"] == "DRY_RUN"
    assert requests["requests"]
    assert receipts["receipts"]
    assert "account_number" not in json.dumps([health, plan, dry, requests, receipts]).lower()


def test_sandbox_submit_cli_defaults_blocked(tmp_path, capsys):
    db = tmp_path / "risk.sqlite3"
    intent = OrderIntentService(RiskRepository(db)).create(_intent(ticker="005930", region=MarketRegion.KR, quantity=1))
    result = _run(capsys, ["kiwoom-sandbox-order-submit", "--db", str(db), "--order-intent-id", intent.order_intent_id])
    assert result["receipt"]["status"] == "BLOCKED"
