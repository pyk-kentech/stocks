from stock_risk_mcp.broker_models import (
    BrokerCapability,
    BrokerConnectionStatus,
    BrokerId,
    BrokerOrderStatus,
)
from stock_risk_mcp.kiwoom_mock_execution_adapter import KiwoomMockExecutionAdapter
from stock_risk_mcp.order_intent import OrderType
from stock_risk_mcp.realtime_market_data import MarketRegion
from tests.test_broker_models import _request


def _kiwoom_request(**updates):
    values = {"broker_id": BrokerId.KIWOOM, "region": MarketRegion.KR, "ticker": "005930"}
    values.update(updates)
    return _request(**values)


def test_kiwoom_mock_adapter_health_and_capabilities() -> None:
    adapter = KiwoomMockExecutionAdapter()
    assert adapter.health_check().status == BrokerConnectionStatus.CONNECTED
    assert adapter.capabilities() == [BrokerCapability.ORDER_SUBMIT, BrokerCapability.ORDER_CANCEL]


def test_kiwoom_mock_adapter_fills_limit_stop_limit_and_explicit_price() -> None:
    adapter = KiwoomMockExecutionAdapter()
    assert adapter.submit_order(_kiwoom_request()).filled_price == 100
    assert adapter.submit_order(_kiwoom_request(order_type=OrderType.STOP_LIMIT)).filled_price == 100
    assert adapter.submit_order(_kiwoom_request(metadata_json={"mock_fill_price": 101})).filled_price == 101


def test_kiwoom_mock_adapter_rejects_market_without_price_and_non_kr() -> None:
    adapter = KiwoomMockExecutionAdapter()
    assert adapter.submit_order(
        _kiwoom_request(order_type=OrderType.MARKET, limit_price=None)
    ).status == BrokerOrderStatus.REJECTED
    assert adapter.submit_order(_kiwoom_request(region=MarketRegion.US)).status == BrokerOrderStatus.REJECTED
    assert adapter.submit_order(_kiwoom_request(quantity=-1)).status == BrokerOrderStatus.REJECTED
    assert adapter.submit_order(_kiwoom_request(limit_price=-1)).status == BrokerOrderStatus.REJECTED
    assert adapter.submit_order(_kiwoom_request(ticker="")).status == BrokerOrderStatus.REJECTED


def test_kiwoom_mock_adapter_normalizes_local_transport_error() -> None:
    receipt = KiwoomMockExecutionAdapter().submit_order(
        _kiwoom_request(metadata_json={"simulate_error": True})
    )
    assert receipt.status == BrokerOrderStatus.REJECTED
    assert "simulated local transport error" in receipt.message


def test_kiwoom_mock_adapter_cancel_and_status_are_deterministic() -> None:
    adapter = KiwoomMockExecutionAdapter()
    receipt = adapter.submit_order(_kiwoom_request())
    assert adapter.order_status(receipt.broker_order_id).status == BrokerOrderStatus.FILLED
    assert adapter.cancel_order(receipt.broker_order_id).status == BrokerOrderStatus.CANCELLED
    assert adapter.order_status(receipt.broker_order_id).status == BrokerOrderStatus.CANCELLED
