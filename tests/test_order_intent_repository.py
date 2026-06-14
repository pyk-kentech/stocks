from stock_risk_mcp.execution_gate import evaluate_execution_gate
from stock_risk_mcp.order_intent import ExecutionMode, OrderIntentStatus
from stock_risk_mcp.order_risk_gate import RiskGateConfig, evaluate_risk_gate
from stock_risk_mcp.paper_execution import create_paper_execution
from stock_risk_mcp.repository import RiskRepository
from tests.test_order_risk_gate import _intent


def test_order_intent_repository_round_trip_and_audit(tmp_path) -> None:
    repository = RiskRepository(tmp_path / "risk.sqlite3")
    intent = _intent()
    repository.save_order_intent(intent)
    repository.update_order_intent_status(intent.order_intent_id, OrderIntentStatus.RISK_APPROVED)
    updated = repository.get_order_intent(intent.order_intent_id)
    risk = evaluate_risk_gate(updated, RiskGateConfig())
    repository.save_risk_gate_decision(risk)
    execution = evaluate_execution_gate(updated, risk, ExecutionMode.PAPER, False)
    repository.save_execution_gate_decision(execution)
    approved = updated.model_copy(update={"status": OrderIntentStatus.EXECUTION_APPROVED})
    paper = create_paper_execution(approved, execution)
    repository.save_paper_execution(paper)

    assert repository.get_order_intent(intent.order_intent_id).status == OrderIntentStatus.RISK_APPROVED
    assert repository.list_order_intents(ticker="AAPL")
    assert repository.get_latest_risk_gate_decision(intent.order_intent_id) == risk
    assert repository.get_risk_gate_decision(risk.risk_gate_decision_id) == risk
    assert repository.get_latest_execution_gate_decision(intent.order_intent_id) == execution
    assert repository.get_execution_gate_decision(execution.execution_gate_decision_id) == execution
    assert repository.get_paper_execution(paper.paper_execution_id) == paper
    assert repository.list_paper_executions(ticker="AAPL")
    assert repository.has_paper_execution(intent.order_intent_id)
