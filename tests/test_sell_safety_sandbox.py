from stock_risk_mcp.kiwoom_real_readonly_models import KiwoomCredentialSource
from stock_risk_mcp.kiwoom_sandbox_order_models import KiwoomSandboxOrderConfig
from stock_risk_mcp.kiwoom_sandbox_order_service import KiwoomSandboxOrderService
from stock_risk_mcp.kiwoom_sandbox_order_transport import FakeKiwoomSandboxOrderTransport
from stock_risk_mcp.local_ledger_service import LocalLedgerService
from stock_risk_mcp.order_intent import ExecutionMode, OrderSide
from stock_risk_mcp.order_intent_service import OrderIntentService
from stock_risk_mcp.order_risk_gate import RiskGateConfig
from stock_risk_mcp.repository import RiskRepository
from stock_risk_mcp.realtime_market_data import MarketRegion
from stock_risk_mcp.sell_safety_gate import SellSafetyGate
from tests.test_order_risk_gate import _intent


def test_verified_sell_safety_still_cannot_submit_without_verified_sell_schema(tmp_path):
    repository = RiskRepository(tmp_path / "risk.sqlite3")
    intent_service = OrderIntentService(repository)
    intent = intent_service.create(_intent(
        ticker="005930", region=MarketRegion.KR, side=OrderSide.SELL,
        quantity=1, stop_loss_price=None,
    ))
    LocalLedgerService(repository).upsert_position("005930", MarketRegion.KR, 2)
    SellSafetyGate(repository).evaluate(intent)
    evaluated = intent_service.evaluate(intent.order_intent_id, RiskGateConfig(), ExecutionMode.SANDBOX, True)
    transport = FakeKiwoomSandboxOrderTransport()
    sandbox = KiwoomSandboxOrderService(
        repository,
        credential_loader=lambda *args: (_ for _ in ()).throw(AssertionError("credentials must not be read")),
        transport_factory=lambda *args: transport,
    )
    config = KiwoomSandboxOrderConfig(
        enable_real_network=True, enable_sandbox_order=True,
        credential_source=KiwoomCredentialSource.ENV, allow_auth_token_request=True,
    )

    result = sandbox.submit(intent.order_intent_id, config)

    assert evaluated["execution_decision"].approved is True
    assert result["receipt"].status == "BLOCKED"
    assert result["receipt"].sanitized_error == "SELL_SANDBOX_ORDER_SCHEMA_NOT_VERIFIED"
    assert transport.calls == []
