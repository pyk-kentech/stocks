from __future__ import annotations

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
from stock_risk_mcp.kiwoom_mock_execution_transport import FakeKiwoomExecutionTransport
from stock_risk_mcp.order_intent import OrderType
from stock_risk_mcp.realtime_market_data import MarketRegion


class KiwoomMockExecutionAdapter:
    broker_id = BrokerId.KIWOOM
    environment = BrokerEnvironment.LOCAL_MOCK

    def __init__(self, transport: FakeKiwoomExecutionTransport | None = None) -> None:
        self.transport = transport or FakeKiwoomExecutionTransport()

    def capabilities(self) -> list[BrokerCapability]:
        return [BrokerCapability.ORDER_SUBMIT, BrokerCapability.ORDER_CANCEL]

    def health_check(self) -> BrokerAdapterHealth:
        return BrokerAdapterHealth(
            broker_id=self.broker_id, environment=self.environment,
            status=BrokerConnectionStatus.CONNECTED, capabilities=self.capabilities(),
            message="Kiwoom-shaped deterministic local mock execution available",
        )

    def submit_order(self, request: BrokerOrderRequest) -> BrokerOrderReceipt:
        reason = self._validation_error(request)
        if reason:
            return self._receipt(request, {"status": "REJECTED", "accepted": False, "message": reason})
        price = self._fill_price(request)
        quantity = request.quantity or (request.notional / price if request.notional and price else None)
        result = self.transport.post("/kiwoom-mock/order/submit", {
            "broker_order_request_id": request.broker_order_request_id,
            "quantity": quantity, "fill_price": price,
            "simulate_error": request.metadata_json.get("simulate_error", False),
        })
        return self._receipt(request, result)

    def cancel_order(self, broker_order_id: str) -> BrokerOrderReceipt:
        result = self.transport.post("/kiwoom-mock/order/cancel", {"mock_order_id": broker_order_id})
        return self._standalone_receipt(broker_order_id, result)

    def order_status(self, broker_order_id: str) -> BrokerOrderReceipt:
        result = self.transport.post("/kiwoom-mock/order/status", {"mock_order_id": broker_order_id})
        return self._standalone_receipt(broker_order_id, result)

    def _validation_error(self, request: BrokerOrderRequest) -> str | None:
        if request.broker_id != self.broker_id or request.environment != self.environment:
            return "Kiwoom local mock routing mismatch"
        if request.region != MarketRegion.KR:
            return "v2.12 supports KR region only"
        if not request.ticker:
            return "ticker required"
        price = self._fill_price(request)
        if price is None:
            return "positive mock_fill_price required for MARKET order" if request.order_type == OrderType.MARKET else "positive limit_price required"
        quantity = request.quantity or (request.notional / price if request.notional and request.notional > 0 else None)
        if quantity is None or quantity <= 0:
            return "positive quantity required"
        return None

    @staticmethod
    def _fill_price(request: BrokerOrderRequest) -> float | None:
        value = request.metadata_json.get("mock_fill_price", request.limit_price)
        try:
            price = float(value)
            return price if price > 0 else None
        except (TypeError, ValueError):
            return None

    def _receipt(self, request: BrokerOrderRequest, result: dict) -> BrokerOrderReceipt:
        return BrokerOrderReceipt(
            broker_order_request_id=request.broker_order_request_id, order_intent_id=request.order_intent_id,
            broker_id=self.broker_id, environment=self.environment,
            status=BrokerOrderStatus(result["status"]), accepted=bool(result["accepted"]),
            filled_quantity=result.get("filled_quantity"), filled_price=result.get("filled_price"),
            filled_notional=result.get("filled_notional"), broker_order_id=result.get("mock_order_id"),
            message=result["message"], metadata_json={"network_access": False, "stop_trigger_simulated": False},
        )

    def _standalone_receipt(self, broker_order_id: str, result: dict) -> BrokerOrderReceipt:
        return BrokerOrderReceipt(
            broker_order_request_id="kiwoom_mock_local_operation", order_intent_id="kiwoom_mock_local_operation",
            broker_id=self.broker_id, environment=self.environment,
            status=BrokerOrderStatus(result["status"]), accepted=bool(result["accepted"]),
            broker_order_id=broker_order_id, message=result["message"], metadata_json={"network_access": False},
        )
