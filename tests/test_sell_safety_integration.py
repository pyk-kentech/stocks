from stock_risk_mcp.local_ledger_service import LocalLedgerService
from stock_risk_mcp.order_intent import ExecutionMode, OrderSide
from stock_risk_mcp.order_intent_service import OrderIntentService
from stock_risk_mcp.order_risk_gate import RiskGateConfig
from stock_risk_mcp.repository import RiskRepository
from stock_risk_mcp.realtime_market_data import MarketRegion
from stock_risk_mcp.sell_safety_gate import SellSafetyGate
from tests.test_order_risk_gate import _intent


def test_order_intent_service_uses_saved_sell_safety_for_sandbox_gate(tmp_path):
    repository = RiskRepository(tmp_path / "risk.sqlite3")
    service = OrderIntentService(repository)
    intent = service.create(_intent(
        ticker="005930", region=MarketRegion.KR, side=OrderSide.SELL,
        quantity=1, stop_loss_price=None,
    ))
    LocalLedgerService(repository).upsert_position("005930", MarketRegion.KR, 2)

    blocked = service.evaluate(intent.order_intent_id, RiskGateConfig(), ExecutionMode.SANDBOX, True)
    assert blocked["risk_decision"].approved is False

    SellSafetyGate(repository).evaluate(intent)
    approved = service.evaluate(intent.order_intent_id, RiskGateConfig(), ExecutionMode.SANDBOX, True)
    assert approved["risk_decision"].approved is True
    assert approved["execution_decision"].approved is True
