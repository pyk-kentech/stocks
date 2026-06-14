from __future__ import annotations

from stock_risk_mcp.broker_models import (
    BrokerAdapterHealth,
    BrokerConnectionStatus,
    BrokerEnvironment,
    BrokerId,
    BrokerOrderReceipt,
    BrokerOrderRequest,
    BrokerOrderStatus,
)
from stock_risk_mcp.mock_broker_adapter import MockBrokerAdapter
from stock_risk_mcp.order_intent import ExecutionMode, OrderIntent, OrderIntentStatus
from stock_risk_mcp.repository import RiskRepository


class BrokerAdapterService:
    def __init__(self, repository: RiskRepository, mock_adapter: MockBrokerAdapter | None = None) -> None:
        self.repository = repository
        self.mock_adapter = mock_adapter or MockBrokerAdapter()

    def health(
        self, broker_id: BrokerId = BrokerId.MOCK, environment: BrokerEnvironment = BrokerEnvironment.LOCAL_MOCK
    ) -> BrokerAdapterHealth:
        if broker_id == BrokerId.MOCK and environment == BrokerEnvironment.LOCAL_MOCK:
            health = self.mock_adapter.health_check()
        else:
            health = BrokerAdapterHealth(
                broker_id=broker_id, environment=environment,
                status=BrokerConnectionStatus.DISABLED, capabilities=[],
                message="v2.10 supports only MOCK broker in LOCAL_MOCK environment",
            )
        self.repository.save_broker_adapter_health_check(health)
        return health

    def submit_mock_order(
        self,
        order_intent_id: str,
        mock_fill_price: float | None = None,
        broker_id: BrokerId = BrokerId.MOCK,
        environment: BrokerEnvironment = BrokerEnvironment.LOCAL_MOCK,
    ) -> dict:
        intent = self.repository.get_order_intent(order_intent_id)
        request = self._build_request(intent, broker_id, environment, mock_fill_price)
        self.repository.save_broker_order_request(request)
        reason = self._submission_block_reason(intent, broker_id, environment)
        if reason is None and self.repository.has_successful_broker_receipt(order_intent_id):
            reason = "duplicate broker submission"
        receipt = self._rejected(request, reason) if reason else self.mock_adapter.submit_order(request)
        self.repository.save_broker_order_receipt(receipt)
        return {"request": request, "receipt": receipt}

    def _submission_block_reason(
        self, intent: OrderIntent, broker_id: BrokerId, environment: BrokerEnvironment
    ) -> str | None:
        if broker_id != BrokerId.MOCK:
            return "v2.10 rejects non-MOCK broker"
        if environment != BrokerEnvironment.LOCAL_MOCK:
            return "v2.10 rejects non-LOCAL_MOCK environment"
        if intent.status != OrderIntentStatus.EXECUTION_APPROVED:
            return "order intent is not execution approved"
        decision = self.repository.get_latest_execution_gate_decision(intent.order_intent_id)
        if decision is None or not decision.approved:
            return "approved execution gate decision required"
        if decision.order_intent_id != intent.order_intent_id:
            return "execution gate decision belongs to another order intent"
        if decision.execution_mode != ExecutionMode.PAPER:
            return "approved PAPER execution gate decision required"
        return None

    @staticmethod
    def _build_request(
        intent: OrderIntent,
        broker_id: BrokerId,
        environment: BrokerEnvironment,
        mock_fill_price: float | None,
    ) -> BrokerOrderRequest:
        metadata = dict(intent.metadata_json)
        if mock_fill_price is not None:
            metadata["mock_fill_price"] = mock_fill_price
        return BrokerOrderRequest(
            order_intent_id=intent.order_intent_id, broker_id=broker_id, environment=environment,
            ticker=intent.ticker, region=intent.region, side=intent.side, order_type=intent.order_type,
            quantity=intent.quantity, notional=intent.notional, limit_price=intent.limit_price,
            stop_loss_price=intent.stop_loss_price, take_profit_price=intent.take_profit_price,
            metadata_json=metadata,
        )

    @staticmethod
    def _rejected(request: BrokerOrderRequest, message: str | None) -> BrokerOrderReceipt:
        return BrokerOrderReceipt(
            broker_order_request_id=request.broker_order_request_id,
            order_intent_id=request.order_intent_id,
            broker_id=request.broker_id,
            environment=request.environment,
            status=BrokerOrderStatus.REJECTED,
            accepted=False,
            message=message or "broker submission rejected",
            metadata_json={"network_access": False},
        )
