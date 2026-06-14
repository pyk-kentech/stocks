from __future__ import annotations

from datetime import datetime

from stock_risk_mcp.order_intent import (
    ExecutionGateDecision,
    ExecutionMode,
    OrderIntent,
    RiskGateDecision,
)


def evaluate_execution_gate(
    intent: OrderIntent,
    risk_decision: RiskGateDecision | None,
    execution_mode: ExecutionMode,
    has_paper_execution: bool,
) -> ExecutionGateDecision:
    reasons: list[str] = []
    if risk_decision is None or not risk_decision.approved:
        reasons.append("approved risk gate decision required")
    elif risk_decision.order_intent_id != intent.order_intent_id:
        reasons.append("risk gate decision belongs to another order intent")
    if intent.expires_at is not None and intent.expires_at <= datetime.now():
        reasons.append("order intent expired")
    if has_paper_execution:
        reasons.append("paper execution already exists")
    if execution_mode != ExecutionMode.PAPER:
        reasons.append(f"{execution_mode.value.lower()} is disabled")
    return ExecutionGateDecision(
        order_intent_id=intent.order_intent_id,
        approved=not reasons,
        execution_mode=execution_mode,
        decision="APPROVED" if not reasons else "BLOCKED",
        reasons_json=reasons,
    )
