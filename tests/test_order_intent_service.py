from stock_risk_mcp.order_intent import ExecutionMode, OrderIntentStatus
from stock_risk_mcp.order_intent_service import OrderIntentService
from stock_risk_mcp.order_risk_gate import RiskGateConfig
from stock_risk_mcp.repository import RiskRepository
from tests.test_order_risk_gate import _intent


def test_order_intent_service_evaluates_and_paper_executes(tmp_path) -> None:
    repository = RiskRepository(tmp_path / "risk.sqlite3")
    service = OrderIntentService(repository)
    intent = service.create(_intent())

    result = service.evaluate(intent.order_intent_id, RiskGateConfig(), ExecutionMode.PAPER)
    execution = service.paper_execute(intent.order_intent_id)

    assert result["intent"].status == OrderIntentStatus.EXECUTION_APPROVED
    assert result["risk_decision"].approved
    assert result["execution_decision"].approved
    assert execution["intent"].status == OrderIntentStatus.PAPER_EXECUTED
    assert repository.has_paper_execution(intent.order_intent_id)


def test_order_intent_service_skips_execution_gate_when_risk_blocked(tmp_path) -> None:
    service = OrderIntentService(RiskRepository(tmp_path / "risk.sqlite3"))
    intent = service.create(_intent(stop_loss_price=None))

    result = service.evaluate(intent.order_intent_id, RiskGateConfig(), ExecutionMode.PAPER)

    assert result["intent"].status == OrderIntentStatus.RISK_BLOCKED
    assert result["execution_decision"] is None


def test_order_intent_service_blocks_and_audits_duplicate_paper_execution(tmp_path) -> None:
    repository = RiskRepository(tmp_path / "risk.sqlite3")
    service = OrderIntentService(repository)
    intent = service.create(_intent())
    service.evaluate(intent.order_intent_id, RiskGateConfig(), ExecutionMode.PAPER)
    service.paper_execute(intent.order_intent_id)

    results = service.paper_execute_many(intent.order_intent_id)

    assert results[0]["error"] == "paper execution already exists"
    assert repository.get_latest_execution_gate_decision(intent.order_intent_id).approved is False
