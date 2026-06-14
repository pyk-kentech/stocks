from __future__ import annotations

from datetime import datetime

from stock_risk_mcp.broker_models import (
    BrokerEnvironment,
    BrokerId,
    BrokerOrderReceipt,
    BrokerOrderRequest,
    BrokerOrderStatus,
)
from stock_risk_mcp.kiwoom_mock_execution_adapter import KiwoomMockExecutionAdapter
from stock_risk_mcp.kiwoom_mock_execution_models import (
    KiwoomMockOrderReceipt,
    KiwoomMockOrderRequest,
    KiwoomMockOrderStatus,
)
from stock_risk_mcp.order_intent import ExecutionMode, OrderIntent, OrderIntentStatus
from stock_risk_mcp.repository import RiskRepository


class KiwoomMockExecutionService:
    def __init__(
        self, repository: RiskRepository, adapter: KiwoomMockExecutionAdapter | None = None
    ) -> None:
        self.repository = repository
        self.adapter = adapter or KiwoomMockExecutionAdapter()

    def health(self):
        health = self.adapter.health_check()
        self.repository.save_broker_adapter_health_check(health)
        return health

    def submit_order(self, order_intent_id: str, mock_fill_price: float | None = None) -> dict:
        intent = self.repository.get_order_intent(order_intent_id)
        request = self._build_request(intent, mock_fill_price)
        mock_request = self._build_mock_request(request)
        self.repository.save_broker_order_request(request)
        self.repository.save_kiwoom_mock_order_request(mock_request)
        reason = self._block_reason(intent)
        if reason is None and self.repository.has_successful_broker_receipt(order_intent_id):
            reason = "duplicate broker submission"
        receipt = self._rejected(request, reason) if reason else self.adapter.submit_order(request)
        mock_receipt = self._build_mock_receipt(mock_request, receipt)
        self.repository.save_broker_order_receipt(receipt)
        self.repository.save_kiwoom_mock_order_receipt(mock_receipt)
        return {"request": request, "receipt": receipt, "kiwoom_mock_request": mock_request, "kiwoom_mock_receipt": mock_receipt}

    def cancel_order(self, mock_order_id: str) -> dict:
        return self._local_operation(mock_order_id, self.adapter.cancel_order)

    def order_status(self, mock_order_id: str) -> dict:
        return self._local_operation(mock_order_id, self.adapter.order_status)

    def _local_operation(self, mock_order_id: str, operation) -> dict:
        prior = self.repository.get_kiwoom_mock_receipt_by_mock_order_id(mock_order_id)
        broker_prior = self.repository.get_broker_order_receipt(prior.broker_order_receipt_id)
        receipt = operation(mock_order_id).model_copy(update={
            "broker_order_request_id": broker_prior.broker_order_request_id,
            "order_intent_id": prior.order_intent_id,
        })
        mock_receipt = KiwoomMockOrderReceipt(
            kiwoom_mock_order_request_id=prior.kiwoom_mock_order_request_id,
            broker_order_receipt_id=receipt.broker_order_receipt_id, order_intent_id=prior.order_intent_id,
            accepted=receipt.accepted, status=KiwoomMockOrderStatus(receipt.status.value),
            mock_order_id=mock_order_id, message=receipt.message, metadata_json={"network_access": False},
        )
        self.repository.save_broker_order_receipt(receipt)
        self.repository.save_kiwoom_mock_order_receipt(mock_receipt)
        return {"receipt": receipt, "kiwoom_mock_receipt": mock_receipt}

    def _block_reason(self, intent: OrderIntent) -> str | None:
        if intent.expires_at is not None and intent.expires_at <= datetime.now():
            return "order intent expired"
        risk = self.repository.get_latest_risk_gate_decision(intent.order_intent_id)
        if risk is None or not risk.approved:
            return "approved risk gate decision required"
        execution = self.repository.get_latest_execution_gate_decision(intent.order_intent_id)
        if execution is None or not execution.approved:
            return "approved execution gate decision required"
        if execution.execution_mode != ExecutionMode.PAPER:
            return "approved PAPER execution gate decision required"
        if intent.status != OrderIntentStatus.EXECUTION_APPROVED:
            return "order intent is not execution approved"
        return None

    @staticmethod
    def _build_request(intent: OrderIntent, mock_fill_price: float | None) -> BrokerOrderRequest:
        metadata = dict(intent.metadata_json)
        if mock_fill_price is not None:
            metadata["mock_fill_price"] = mock_fill_price
        return BrokerOrderRequest(
            order_intent_id=intent.order_intent_id, broker_id=BrokerId.KIWOOM,
            environment=BrokerEnvironment.LOCAL_MOCK, ticker=intent.ticker, region=intent.region,
            side=intent.side, order_type=intent.order_type, quantity=intent.quantity,
            notional=intent.notional, limit_price=intent.limit_price, stop_loss_price=intent.stop_loss_price,
            take_profit_price=intent.take_profit_price, metadata_json=metadata,
        )

    @staticmethod
    def _build_mock_request(request: BrokerOrderRequest) -> KiwoomMockOrderRequest:
        return KiwoomMockOrderRequest(
            broker_order_request_id=request.broker_order_request_id, order_intent_id=request.order_intent_id,
            ticker=request.ticker, region=request.region, side=request.side, order_type=request.order_type,
            quantity=request.quantity, notional=request.notional, limit_price=request.limit_price,
            stop_loss_price=request.stop_loss_price, take_profit_price=request.take_profit_price,
            mock_fill_price=request.metadata_json.get("mock_fill_price"),
            metadata_json={"network_access": False},
        )

    @staticmethod
    def _build_mock_receipt(request: KiwoomMockOrderRequest, receipt: BrokerOrderReceipt) -> KiwoomMockOrderReceipt:
        return KiwoomMockOrderReceipt(
            kiwoom_mock_order_request_id=request.kiwoom_mock_order_request_id,
            broker_order_receipt_id=receipt.broker_order_receipt_id, order_intent_id=receipt.order_intent_id,
            accepted=receipt.accepted, status=KiwoomMockOrderStatus(receipt.status.value),
            filled_quantity=receipt.filled_quantity, filled_price=receipt.filled_price,
            filled_notional=receipt.filled_notional, mock_order_id=receipt.broker_order_id,
            message=receipt.message, metadata_json={"network_access": False},
        )

    @staticmethod
    def _rejected(request: BrokerOrderRequest, reason: str | None) -> BrokerOrderReceipt:
        return BrokerOrderReceipt(
            broker_order_request_id=request.broker_order_request_id, order_intent_id=request.order_intent_id,
            broker_id=BrokerId.KIWOOM, environment=BrokerEnvironment.LOCAL_MOCK,
            status=BrokerOrderStatus.REJECTED, accepted=False,
            message=reason or "Kiwoom mock submission rejected", metadata_json={"network_access": False},
        )
