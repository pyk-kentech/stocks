from stock_risk_mcp.order_intent import ExecutionGateDecision, ExecutionMode, OrderIntentStatus
from stock_risk_mcp.paper_execution import create_paper_execution
from tests.test_order_risk_gate import _intent


def test_paper_execution_uses_explicit_then_limit_fill() -> None:
    intent = _intent(status=OrderIntentStatus.EXECUTION_APPROVED)
    decision = ExecutionGateDecision(
        order_intent_id=intent.order_intent_id, approved=True,
        execution_mode=ExecutionMode.PAPER, decision="APPROVED",
    )
    explicit = create_paper_execution(intent, decision, fill_price=99)
    fallback = create_paper_execution(intent, decision)

    assert explicit.filled_price == 99
    assert fallback.filled_price == 100
    assert fallback.filled_notional == 100


def test_paper_execution_rejects_decision_for_another_intent() -> None:
    import pytest
    intent = _intent(status=OrderIntentStatus.EXECUTION_APPROVED)
    decision = ExecutionGateDecision(
        order_intent_id="other", approved=True,
        execution_mode=ExecutionMode.PAPER, decision="APPROVED",
    )
    with pytest.raises(ValueError, match="same order intent"):
        create_paper_execution(intent, decision)
