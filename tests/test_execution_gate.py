from datetime import datetime, timedelta

from stock_risk_mcp.execution_gate import evaluate_execution_gate
from stock_risk_mcp.order_intent import ExecutionMode, RiskGateDecision
from tests.test_order_risk_gate import _intent


def test_execution_gate_requires_risk_approval_and_paper_mode() -> None:
    intent = _intent()
    approved = RiskGateDecision(order_intent_id=intent.order_intent_id, approved=True, decision="APPROVED")
    blocked = approved.model_copy(update={"approved": False})

    assert evaluate_execution_gate(intent, approved, ExecutionMode.PAPER, False).approved
    assert not evaluate_execution_gate(intent, blocked, ExecutionMode.PAPER, False).approved
    assert not evaluate_execution_gate(intent, approved, ExecutionMode.SANDBOX_DISABLED, False).approved
    assert not evaluate_execution_gate(intent, approved, ExecutionMode.LIVE_DISABLED, False).approved


def test_execution_gate_blocks_expired_and_duplicate() -> None:
    expired = _intent(expires_at=datetime.now() - timedelta(seconds=1))
    approved = RiskGateDecision(order_intent_id=expired.order_intent_id, approved=True, decision="APPROVED")
    assert not evaluate_execution_gate(expired, approved, ExecutionMode.PAPER, False).approved
    assert not evaluate_execution_gate(expired, approved, ExecutionMode.PAPER, True).approved


def test_execution_gate_blocks_risk_decision_for_another_intent() -> None:
    intent = _intent()
    other = RiskGateDecision(order_intent_id="other", approved=True, decision="APPROVED")
    assert not evaluate_execution_gate(intent, other, ExecutionMode.PAPER, False).approved
