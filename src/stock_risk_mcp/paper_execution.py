from __future__ import annotations

from stock_risk_mcp.order_intent import (
    ExecutionGateDecision,
    ExecutionMode,
    OrderIntent,
    OrderIntentStatus,
    PaperExecution,
)
from stock_risk_mcp.order_risk_gate import _derived_quantity, _entry_price


def create_paper_execution(
    intent: OrderIntent,
    execution_decision: ExecutionGateDecision,
    fill_price: float | None = None,
) -> PaperExecution:
    if intent.status != OrderIntentStatus.EXECUTION_APPROVED:
        raise ValueError("order intent is not execution approved")
    if not execution_decision.approved or execution_decision.execution_mode != ExecutionMode.PAPER:
        raise ValueError("approved PAPER execution gate decision required")
    if execution_decision.order_intent_id != intent.order_intent_id:
        raise ValueError("execution gate decision must belong to the same order intent")
    price = fill_price if fill_price is not None else intent.limit_price
    if price is None or price <= 0:
        raise ValueError("positive deterministic fill price required")
    quantity = _derived_quantity(intent, _entry_price(intent))
    if quantity is None or quantity <= 0:
        raise ValueError("positive quantity required")
    return PaperExecution(
        order_intent_id=intent.order_intent_id,
        ticker=intent.ticker,
        side=intent.side,
        quantity=quantity,
        requested_price=intent.limit_price,
        filled_price=price,
        filled_notional=quantity * price,
        metadata_json={"execution_mode": ExecutionMode.PAPER.value, "slippage": 0},
    )
