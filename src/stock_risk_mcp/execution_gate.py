from __future__ import annotations

from datetime import datetime

from stock_risk_mcp.order_intent import (
    ExecutionGateDecision,
    ExecutionMode,
    OrderIntent,
    RiskGateDecision,
    OrderSide,
    OrderType,
)


def evaluate_execution_gate(
    intent: OrderIntent,
    risk_decision: RiskGateDecision | None,
    execution_mode: ExecutionMode,
    has_paper_execution: bool,
    enable_sandbox_order: bool = False,
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
    if execution_mode == ExecutionMode.SANDBOX:
        if not enable_sandbox_order:
            reasons.append("sandbox order is not explicitly enabled")
        if intent.order_type != OrderType.LIMIT:
            reasons.append("sandbox supports LIMIT orders only")
        if intent.side == OrderSide.BUY and intent.stop_loss_price is None:
            reasons.append("sandbox BUY stop-loss required")
        metadata = intent.metadata_json
        if metadata.get("margin") is True:
            reasons.append("sandbox margin disabled")
        if metadata.get("short") is True:
            reasons.append("sandbox short selling disabled")
        if str(metadata.get("instrument_type", "")).upper() in {"OPTION", "OPTIONS", "FUTURE", "FUTURES"}:
            reasons.append("sandbox derivatives disabled")
        try:
            if float(metadata.get("leverage", 1)) > 1:
                reasons.append("sandbox leverage disabled")
        except (TypeError, ValueError):
            reasons.append("sandbox invalid leverage")
    elif execution_mode in {ExecutionMode.LIVE, ExecutionMode.LIVE_DISABLED}:
        reasons.append("LIVE_EXECUTION_DISABLED_IN_V2_16")
    elif execution_mode != ExecutionMode.PAPER:
        reasons.append(f"{execution_mode.value.lower()} is disabled")
    return ExecutionGateDecision(
        order_intent_id=intent.order_intent_id,
        approved=not reasons,
        execution_mode=execution_mode,
        decision="APPROVED" if not reasons else "BLOCKED",
        reasons_json=reasons,
    )
