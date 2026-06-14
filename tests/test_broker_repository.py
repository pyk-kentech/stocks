from stock_risk_mcp.broker_models import BrokerId
from stock_risk_mcp.mock_broker_adapter import MockBrokerAdapter
from stock_risk_mcp.repository import RiskRepository
from tests.test_broker_models import _request


def test_broker_repository_round_trip_and_success_detection(tmp_path) -> None:
    repository = RiskRepository(tmp_path / "risk.sqlite3")
    request = _request()
    receipt = MockBrokerAdapter().submit_order(request)
    health = MockBrokerAdapter().health_check()
    repository.save_broker_order_request(request)
    repository.save_broker_order_receipt(receipt)
    repository.save_broker_adapter_health_check(health)

    assert repository.get_broker_order_request(request.broker_order_request_id) == request
    assert repository.list_broker_order_requests(broker_id=BrokerId.MOCK, order_intent_id="intent_1")
    assert repository.get_broker_order_receipt(receipt.broker_order_receipt_id) == receipt
    assert repository.get_latest_broker_receipt(request.broker_order_request_id) == receipt
    assert repository.list_broker_order_receipts(order_intent_id="intent_1")
    assert repository.has_successful_broker_receipt("intent_1")
    assert repository.list_broker_adapter_health_checks()[0] == health
