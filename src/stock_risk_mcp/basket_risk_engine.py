from __future__ import annotations

from stock_risk_mcp.trade_plan_models import BasketRiskDecision, BasketRiskState


def review_basket_risk(state: BasketRiskState, plan_risk_amount: float) -> BasketRiskDecision:
    next_total = state.running_basket_risk_amount + plan_risk_amount
    if next_total > state.max_basket_risk_amount:
        return BasketRiskDecision(
            accepted=False,
            block_reason="BASKET_RISK_CAP_EXCEEDED",
            updated_state=state,
        )
    return BasketRiskDecision(
        accepted=True,
        updated_state=BasketRiskState(
            running_basket_risk_amount=next_total,
            max_basket_risk_amount=state.max_basket_risk_amount,
        ),
    )
