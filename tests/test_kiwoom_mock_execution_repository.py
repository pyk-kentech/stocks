from stock_risk_mcp.kiwoom_mock_execution_models import KiwoomMockOrderReceipt, KiwoomMockOrderStatus
from stock_risk_mcp.repository import RiskRepository
from tests.test_kiwoom_mock_execution_models import _request


def test_kiwoom_mock_repository_round_trip(tmp_path) -> None:
    repository = RiskRepository(tmp_path / "risk.sqlite3")
    request = _request()
    receipt = KiwoomMockOrderReceipt(
        kiwoom_mock_order_request_id=request.kiwoom_mock_order_request_id,
        broker_order_receipt_id="broker_receipt_1", order_intent_id=request.order_intent_id,
        accepted=True, status=KiwoomMockOrderStatus.FILLED, mock_order_id="mock_1", message="filled",
    )
    repository.save_kiwoom_mock_order_request(request)
    repository.save_kiwoom_mock_order_receipt(receipt)

    assert repository.list_kiwoom_mock_order_requests(request.order_intent_id)[0] == request
    assert repository.list_kiwoom_mock_order_receipts(request.order_intent_id)[0] == receipt
    assert repository.get_latest_kiwoom_mock_receipt(request.order_intent_id) == receipt
