from stock_risk_mcp.broker_models import BrokerCapability, BrokerConnectionStatus, BrokerOrderStatus
from stock_risk_mcp.mock_broker_adapter import MockBrokerAdapter
from stock_risk_mcp.order_intent import OrderType
from tests.test_broker_models import _request


def test_mock_broker_health_and_capabilities_are_local_only() -> None:
    adapter = MockBrokerAdapter()
    health = adapter.health_check()

    assert health.status == BrokerConnectionStatus.CONNECTED
    assert BrokerCapability.ORDER_SUBMIT in adapter.capabilities()
    assert BrokerCapability.ORDER_CANCEL in adapter.capabilities()
    assert BrokerCapability.MARKET_DATA not in adapter.capabilities()
    assert BrokerCapability.ACCOUNT_READ not in adapter.capabilities()


def test_mock_broker_deterministic_limit_and_stop_limit_fills() -> None:
    adapter = MockBrokerAdapter()
    limit = adapter.submit_order(_request())
    stop_limit = adapter.submit_order(_request(order_type=OrderType.STOP_LIMIT))

    assert limit.status == stop_limit.status == BrokerOrderStatus.FILLED
    assert limit.filled_price == stop_limit.filled_price == 100


def test_mock_broker_market_requires_explicit_mock_fill_price() -> None:
    adapter = MockBrokerAdapter()
    rejected = adapter.submit_order(_request(order_type=OrderType.MARKET, limit_price=None))
    filled = adapter.submit_order(_request(
        order_type=OrderType.MARKET, limit_price=None, metadata_json={"mock_fill_price": 101}
    ))

    assert rejected.status == BrokerOrderStatus.REJECTED
    assert "mock_fill_price" in rejected.message
    assert filled.status == BrokerOrderStatus.FILLED
    assert filled.filled_price == 101
