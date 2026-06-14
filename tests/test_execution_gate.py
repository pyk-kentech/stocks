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


def test_execution_gate_approves_safe_sandbox_only_with_explicit_opt_in() -> None:
    intent = _intent()
    approved = RiskGateDecision(order_intent_id=intent.order_intent_id, approved=True, decision="APPROVED")

    assert not evaluate_execution_gate(intent, approved, ExecutionMode.SANDBOX, False).approved
    assert evaluate_execution_gate(
        intent, approved, ExecutionMode.SANDBOX, False, enable_sandbox_order=True
    ).approved


def test_execution_gate_sandbox_blocks_market_missing_stop_and_live() -> None:
    approved_intent = _intent()
    approved = RiskGateDecision(order_intent_id=approved_intent.order_intent_id, approved=True, decision="APPROVED")
    market = _intent(order_type="MARKET", limit_price=None, metadata_json={"reference_price": 100})
    no_stop = _intent(stop_loss_price=None)

    assert not evaluate_execution_gate(
        market, approved.model_copy(update={"order_intent_id": market.order_intent_id}),
        ExecutionMode.SANDBOX, False, enable_sandbox_order=True,
    ).approved
    assert not evaluate_execution_gate(
        no_stop, approved.model_copy(update={"order_intent_id": no_stop.order_intent_id}),
        ExecutionMode.SANDBOX, False, enable_sandbox_order=True,
    ).approved
    live = evaluate_execution_gate(approved_intent, approved, ExecutionMode.LIVE_DISABLED, False, enable_sandbox_order=True)
    assert "LIVE_EXECUTION_DISABLED_IN_V2_16" in live.reasons_json
    assert "LIVE_EXECUTION_DISABLED_IN_V2_16" in evaluate_execution_gate(
        approved_intent, approved, ExecutionMode.LIVE, False, enable_sandbox_order=True
    ).reasons_json


def test_execution_gate_blocks_expired_and_duplicate() -> None:
    expired = _intent(expires_at=datetime.now() - timedelta(seconds=1))
    approved = RiskGateDecision(order_intent_id=expired.order_intent_id, approved=True, decision="APPROVED")
    assert not evaluate_execution_gate(expired, approved, ExecutionMode.PAPER, False).approved
    assert not evaluate_execution_gate(expired, approved, ExecutionMode.PAPER, True).approved


def test_execution_gate_blocks_risk_decision_for_another_intent() -> None:
    intent = _intent()
    other = RiskGateDecision(order_intent_id="other", approved=True, decision="APPROVED")
    assert not evaluate_execution_gate(intent, other, ExecutionMode.PAPER, False).approved
