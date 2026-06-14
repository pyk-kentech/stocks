from __future__ import annotations

from uuid import uuid4

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
from stock_risk_mcp.order_intent import OrderType


class MockBrokerAdapter:
    broker_id = BrokerId.MOCK
    environment = BrokerEnvironment.LOCAL_MOCK

    def capabilities(self) -> list[BrokerCapability]:
        return [BrokerCapability.ORDER_SUBMIT, BrokerCapability.ORDER_CANCEL]

    def health_check(self) -> BrokerAdapterHealth:
        return BrokerAdapterHealth(
            broker_id=self.broker_id,
            environment=self.environment,
            status=BrokerConnectionStatus.CONNECTED,
            capabilities=self.capabilities(),
            message="deterministic local mock broker connected",
        )

    def submit_order(self, request: BrokerOrderRequest) -> BrokerOrderReceipt:
        if request.broker_id != self.broker_id or request.environment != self.environment:
            return self._reject(request, "mock broker routing mismatch")
        quantity = request.quantity
        if quantity is None and request.notional is not None:
            price = self._fill_price(request)
            quantity = request.notional / price if price else None
        if quantity is None or quantity <= 0:
            return self._reject(request, "positive quantity required")
        price = self._fill_price(request)
        if price is None:
            return self._reject(request, "positive mock_fill_price required for MARKET order")
        return BrokerOrderReceipt(
            broker_order_request_id=request.broker_order_request_id,
            order_intent_id=request.order_intent_id,
            broker_id=self.broker_id,
            environment=self.environment,
            status=BrokerOrderStatus.FILLED,
            accepted=True,
            filled_quantity=quantity,
            filled_price=price,
            filled_notional=quantity * price,
            broker_order_id=f"mock_order_{uuid4().hex}",
            message="deterministic local mock fill",
            metadata_json={"network_access": False, "stop_trigger_simulated": False},
        )

    def cancel_order(self, broker_order_id: str) -> BrokerOrderReceipt:
        return BrokerOrderReceipt(
            broker_order_request_id="local_cancel",
            order_intent_id="local_cancel",
            broker_id=self.broker_id,
            environment=self.environment,
            status=BrokerOrderStatus.CANCELLED,
            accepted=True,
            broker_order_id=broker_order_id,
            message="deterministic local mock cancellation",
            metadata_json={"network_access": False},
        )

    @staticmethod
    def _fill_price(request: BrokerOrderRequest) -> float | None:
        if request.order_type == OrderType.MARKET:
            value = request.metadata_json.get("mock_fill_price")
        else:
            value = request.limit_price
        try:
            price = float(value)
            return price if price > 0 else None
        except (TypeError, ValueError):
            return None

    def _reject(self, request: BrokerOrderRequest, message: str) -> BrokerOrderReceipt:
        return BrokerOrderReceipt(
            broker_order_request_id=request.broker_order_request_id,
            order_intent_id=request.order_intent_id,
            broker_id=self.broker_id,
            environment=self.environment,
            status=BrokerOrderStatus.REJECTED,
            accepted=False,
            message=message,
            metadata_json={"network_access": False},
        )
