from datetime import datetime

from stock_risk_mcp.broker_adapter import BrokerAdapter
from stock_risk_mcp.broker_models import (
    BrokerAdapterHealth,
    BrokerCapability,
    BrokerConnectionStatus,
    BrokerEnvironment,
    BrokerId,
    BrokerOrderReceipt,
    BrokerOrderRequest,
    BrokerOrderStatus,
)
from stock_risk_mcp.order_intent import OrderSide, OrderType
from stock_risk_mcp.realtime_market_data import MarketRegion


def test_broker_models_serialize_and_default_ids() -> None:
    request = _request()
    receipt = BrokerOrderReceipt(
        broker_order_request_id=request.broker_order_request_id,
        order_intent_id=request.order_intent_id, broker_id=BrokerId.MOCK,
        environment=BrokerEnvironment.LOCAL_MOCK, status=BrokerOrderStatus.FILLED,
        accepted=True, filled_quantity=1, filled_price=100, filled_notional=100,
        broker_order_id="mock_1", message="filled",
    )
    health = BrokerAdapterHealth(
        broker_id=BrokerId.MOCK, environment=BrokerEnvironment.LOCAL_MOCK,
        status=BrokerConnectionStatus.CONNECTED, capabilities=[BrokerCapability.ORDER_SUBMIT],
        message="local mock",
    )

    assert request.ticker == "AAPL"
    assert request.broker_order_request_id.startswith("broker_request_")
    assert receipt.broker_order_receipt_id.startswith("broker_receipt_")
    assert isinstance(health.checked_at, datetime)
    assert receipt.model_dump(mode="json")["status"] == "FILLED"


def test_broker_adapter_protocol_is_runtime_checkable() -> None:
    assert hasattr(BrokerAdapter, "submit_order")


def _request(**updates):
    values = dict(
        order_intent_id="intent_1", broker_id=BrokerId.MOCK,
        environment=BrokerEnvironment.LOCAL_MOCK, ticker=" aapl ", region=MarketRegion.US,
        side=OrderSide.BUY, order_type=OrderType.LIMIT, quantity=1, notional=None,
        limit_price=100, stop_loss_price=95, take_profit_price=115,
    )
    values.update(updates)
    return BrokerOrderRequest(**values)
