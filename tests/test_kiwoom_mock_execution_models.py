from stock_risk_mcp.broker_models import BrokerOrderStatus
from stock_risk_mcp.kiwoom_mock_execution_models import (
    KiwoomMockOrderReceipt,
    KiwoomMockOrderRequest,
    KiwoomMockOrderStatus,
)
from stock_risk_mcp.order_intent import OrderSide, OrderType
from stock_risk_mcp.realtime_market_data import MarketRegion


def test_kiwoom_mock_models_validate_and_serialize() -> None:
    request = _request()
    receipt = KiwoomMockOrderReceipt(
        kiwoom_mock_order_request_id=request.kiwoom_mock_order_request_id,
        broker_order_receipt_id="broker_receipt_1", order_intent_id="intent_1",
        accepted=True, status=KiwoomMockOrderStatus.FILLED, filled_quantity=1,
        filled_price=100, filled_notional=100, mock_order_id="kiwoom_mock_order_1",
        message="filled",
    )

    assert request.ticker == "005930"
    assert request.kiwoom_mock_order_request_id.startswith("kiwoom_mock_request_")
    assert receipt.model_dump(mode="json")["status"] == BrokerOrderStatus.FILLED.value


def _request(**updates):
    values = dict(
        broker_order_request_id="broker_request_1", order_intent_id="intent_1",
        ticker=" 005930 ", region=MarketRegion.KR, side=OrderSide.BUY,
        order_type=OrderType.LIMIT, quantity=1, limit_price=100,
    )
    values.update(updates)
    return KiwoomMockOrderRequest(**values)
