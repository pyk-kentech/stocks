from datetime import datetime, timedelta

from stock_risk_mcp.broker_models import BrokerOrderStatus
from stock_risk_mcp.kiwoom_mock_execution_adapter import KiwoomMockExecutionAdapter
from stock_risk_mcp.kiwoom_mock_execution_service import KiwoomMockExecutionService
from stock_risk_mcp.order_intent import ExecutionMode
from stock_risk_mcp.order_intent_service import OrderIntentService
from stock_risk_mcp.order_risk_gate import RiskGateConfig, evaluate_risk_gate
from stock_risk_mcp.repository import RiskRepository
from stock_risk_mcp.realtime_market_data import MarketRegion
from tests.test_order_risk_gate import _intent


def test_kiwoom_mock_service_submits_approved_intent_and_persists_both_audits(tmp_path) -> None:
    repository, intent = _approved(tmp_path)
    result = KiwoomMockExecutionService(repository).submit_order(intent.order_intent_id)

    assert result["receipt"].status == BrokerOrderStatus.FILLED
    assert repository.list_broker_order_requests(order_intent_id=intent.order_intent_id)
    assert repository.list_kiwoom_mock_order_requests(intent.order_intent_id)
    assert repository.list_kiwoom_mock_order_receipts(intent.order_intent_id)


def test_kiwoom_mock_service_blocks_missing_approval_and_expired_intent(tmp_path) -> None:
    repository = RiskRepository(tmp_path / "risk.sqlite3")
    unapproved = OrderIntentService(repository).create(_intent(ticker="005930", region=MarketRegion.KR))
    expired = OrderIntentService(repository).create(_intent(
        ticker="000660", region=MarketRegion.KR, expires_at=datetime.now() - timedelta(seconds=1)
    ))
    service = KiwoomMockExecutionService(repository)

    assert service.submit_order(unapproved.order_intent_id)["receipt"].status == BrokerOrderStatus.REJECTED
    assert "expired" in service.submit_order(expired.order_intent_id)["receipt"].message


def test_kiwoom_mock_service_requires_execution_gate_after_risk_approval(tmp_path) -> None:
    repository = RiskRepository(tmp_path / "risk.sqlite3")
    intent = OrderIntentService(repository).create(_intent(ticker="005930", region=MarketRegion.KR))
    repository.save_risk_gate_decision(evaluate_risk_gate(intent, RiskGateConfig()))

    result = KiwoomMockExecutionService(repository).submit_order(intent.order_intent_id)
    assert "execution gate" in result["receipt"].message


def test_kiwoom_mock_service_market_requires_upstream_opt_in_and_mock_fill_price(tmp_path) -> None:
    repository = RiskRepository(tmp_path / "risk.sqlite3")
    service = OrderIntentService(repository)
    intent = service.create(_intent(
        ticker="005930", region=MarketRegion.KR, order_type="MARKET", limit_price=None,
        metadata_json={"reference_price": 100},
    ))
    service.evaluate(intent.order_intent_id, RiskGateConfig(allow_market_orders=True), ExecutionMode.PAPER)

    rejected = KiwoomMockExecutionService(repository).submit_order(intent.order_intent_id)
    filled = KiwoomMockExecutionService(repository).submit_order(intent.order_intent_id, mock_fill_price=101)

    assert rejected["receipt"].status == BrokerOrderStatus.REJECTED
    assert filled["receipt"].status == BrokerOrderStatus.FILLED


def test_kiwoom_mock_duplicate_persists_rejection_without_adapter_refill(tmp_path) -> None:
    repository, intent = _approved(tmp_path)
    adapter = CountingKiwoomAdapter()
    service = KiwoomMockExecutionService(repository, adapter)

    first = service.submit_order(intent.order_intent_id)
    second = service.submit_order(intent.order_intent_id)

    assert first["receipt"].status == BrokerOrderStatus.FILLED
    assert second["receipt"].status == BrokerOrderStatus.REJECTED
    assert "duplicate broker submission" in second["receipt"].message
    assert adapter.submit_count == 1
    assert len(repository.list_kiwoom_mock_order_requests(intent.order_intent_id)) == 2


def test_kiwoom_mock_cancel_and_status_are_persisted_against_original_intent(tmp_path) -> None:
    repository, intent = _approved(tmp_path)
    service = KiwoomMockExecutionService(repository)
    submitted = service.submit_order(intent.order_intent_id)
    mock_order_id = submitted["receipt"].broker_order_id

    cancelled = service.cancel_order(mock_order_id)
    status = service.order_status(mock_order_id)

    assert cancelled["receipt"].order_intent_id == intent.order_intent_id
    assert status["receipt"].order_intent_id == intent.order_intent_id
    assert len(repository.list_kiwoom_mock_order_receipts(intent.order_intent_id)) == 3


class CountingKiwoomAdapter(KiwoomMockExecutionAdapter):
    def __init__(self):
        super().__init__()
        self.submit_count = 0

    def submit_order(self, request):
        self.submit_count += 1
        return super().submit_order(request)


def _approved(tmp_path):
    repository = RiskRepository(tmp_path / "risk.sqlite3")
    service = OrderIntentService(repository)
    intent = service.create(_intent(ticker="005930", region=MarketRegion.KR))
    service.evaluate(intent.order_intent_id, RiskGateConfig(), ExecutionMode.PAPER)
    return repository, repository.get_order_intent(intent.order_intent_id)
