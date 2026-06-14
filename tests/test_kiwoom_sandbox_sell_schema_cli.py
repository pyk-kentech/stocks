import json

from stock_risk_mcp.cli import main
from stock_risk_mcp.local_ledger_service import LocalLedgerService
from stock_risk_mcp.order_intent import ExecutionMode, OrderSide
from stock_risk_mcp.order_intent_service import OrderIntentService
from stock_risk_mcp.order_risk_gate import RiskGateConfig
from stock_risk_mcp.repository import RiskRepository
from stock_risk_mcp.realtime_market_data import MarketRegion
from stock_risk_mcp.sell_safety_gate import SellSafetyGate
from tests.test_order_risk_gate import _intent


def _run(capsys, args):
    main(args)
    return json.loads(capsys.readouterr().out)


def test_sell_schema_verify_reports_show_and_dry_run_cli_are_offline(tmp_path, capsys):
    db = tmp_path / "risk.sqlite3"
    repository = RiskRepository(db)
    service = OrderIntentService(repository)
    intent = service.create(_intent(
        ticker="005930", region=MarketRegion.KR, side=OrderSide.SELL,
        quantity=1, stop_loss_price=None,
    ))
    LocalLedgerService(repository).upsert_position("005930", MarketRegion.KR, 2)
    SellSafetyGate(repository).evaluate(intent)
    service.evaluate(intent.order_intent_id, RiskGateConfig(), ExecutionMode.SANDBOX, True)

    report = _run(capsys, ["kiwoom-sandbox-sell-schema-verify", "--db", str(db)])
    reports = _run(capsys, ["kiwoom-sandbox-sell-schema-reports", "--db", str(db)])
    shown = _run(capsys, [
        "kiwoom-sandbox-sell-schema-show", "--db", str(db), "--report-id", report["report_id"],
    ])
    dry_run = _run(capsys, [
        "kiwoom-sandbox-sell-dry-run", "--db", str(db), "--order-intent-id", intent.order_intent_id,
    ])
    payload = json.dumps([report, reports, shown, dry_run]).lower()

    assert report["status"] == "UNVERIFIED"
    assert reports["reports"]
    assert shown["report_id"] == report["report_id"]
    assert dry_run["status"] == "BLOCKED"
    assert "sell_sandbox_order_schema_not_verified" in payload
    assert all(item not in payload for item in ("account_number", "raw_balance", "raw_holdings", "bearer "))
