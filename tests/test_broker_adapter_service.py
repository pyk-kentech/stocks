from stock_risk_mcp.broker_adapter_service import BrokerAdapterService
from stock_risk_mcp.broker_models import BrokerEnvironment, BrokerId, BrokerOrderStatus
from stock_risk_mcp.mock_broker_adapter import MockBrokerAdapter
from stock_risk_mcp.order_intent import ExecutionMode
from stock_risk_mcp.order_intent_service import OrderIntentService
from stock_risk_mcp.order_risk_gate import RiskGateConfig
from stock_risk_mcp.repository import RiskRepository
from tests.test_order_risk_gate import _intent


def test_broker_adapter_service_submits_approved_intent_and_persists(tmp_path) -> None:
    repository, intent = _approved(tmp_path)
    result = BrokerAdapterService(repository).submit_mock_order(intent.order_intent_id)

    assert result["receipt"].status == BrokerOrderStatus.FILLED
    assert repository.list_broker_order_requests(order_intent_id=intent.order_intent_id)
    assert repository.list_broker_order_receipts(order_intent_id=intent.order_intent_id)


def test_broker_adapter_service_rejects_unapproved_and_non_mock_routes(tmp_path) -> None:
    repository = RiskRepository(tmp_path / "risk.sqlite3")
    intent = OrderIntentService(repository).create(_intent())
    service = BrokerAdapterService(repository)

    assert service.submit_mock_order(intent.order_intent_id)["receipt"].status == BrokerOrderStatus.REJECTED
    assert service.submit_mock_order(intent.order_intent_id, broker_id=BrokerId.KIWOOM)["receipt"].status == BrokerOrderStatus.REJECTED
    assert service.submit_mock_order(
        intent.order_intent_id, environment=BrokerEnvironment.PAPER
    )["receipt"].status == BrokerOrderStatus.REJECTED


def test_duplicate_broker_submission_saves_request_and_rejected_receipt_without_second_fill(tmp_path) -> None:
    repository, intent = _approved(tmp_path)
    adapter = CountingMockBroker()
    service = BrokerAdapterService(repository, adapter)

    first = service.submit_mock_order(intent.order_intent_id)
    second = service.submit_mock_order(intent.order_intent_id)

    assert first["receipt"].status == BrokerOrderStatus.FILLED
    assert second["receipt"].status == BrokerOrderStatus.REJECTED
    assert "duplicate broker submission" in second["receipt"].message
    assert len(repository.list_broker_order_requests(order_intent_id=intent.order_intent_id)) == 2
    assert len(repository.list_broker_order_receipts(order_intent_id=intent.order_intent_id)) == 2
    assert adapter.submit_count == 1


class CountingMockBroker(MockBrokerAdapter):
    def __init__(self):
        self.submit_count = 0

    def submit_order(self, request):
        self.submit_count += 1
        return super().submit_order(request)


def _approved(tmp_path):
    repository = RiskRepository(tmp_path / "risk.sqlite3")
    intent_service = OrderIntentService(repository)
    intent = intent_service.create(_intent())
    intent_service.evaluate(intent.order_intent_id, RiskGateConfig(), ExecutionMode.PAPER)
    return repository, repository.get_order_intent(intent.order_intent_id)
