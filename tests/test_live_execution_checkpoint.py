from stock_risk_mcp.execution_gate import evaluate_execution_gate
from stock_risk_mcp.order_intent import ExecutionMode, RiskGateDecision
from tests.test_order_risk_gate import _intent


def test_v217_checkpoint_keeps_live_execution_blocked() -> None:
    intent = _intent()
    approved = RiskGateDecision(
        order_intent_id=intent.order_intent_id,
        approved=True,
        decision="APPROVED",
    )

    decision = evaluate_execution_gate(
        intent,
        approved,
        ExecutionMode.LIVE,
        has_paper_execution=False,
        enable_sandbox_order=True,
    )

    assert not decision.approved
    assert decision.decision == "BLOCKED"
    assert "LIVE_EXECUTION_DISABLED_IN_V2_16" in decision.reasons_json
