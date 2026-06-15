from __future__ import annotations

from stock_risk_mcp.order_intent import OrderIntent, OrderSide, OrderType
from stock_risk_mcp.repository import RiskRepository
from stock_risk_mcp.strategy_core import (
    StrategyCandidateOrderType,
    StrategyDecision,
    StrategyDecisionStatus,
)


def create_order_intent_draft(repository: RiskRepository, decision: StrategyDecision) -> OrderIntent:
    if decision.status not in (StrategyDecisionStatus.CANDIDATE_BUY, StrategyDecisionStatus.CANDIDATE_SELL):
        raise ValueError("strategy decision does not allow an OrderIntent draft")
    candidate = repository.get_strategy_candidate(decision.candidate_id)
    snapshot = repository.get_strategy_feature_snapshot(decision.snapshot_id)
    if candidate.order_type == StrategyCandidateOrderType.MARKET:
        raise ValueError("MARKET strategy OrderIntent drafts are blocked")
    forbidden = ("margin", "short", "credit", "leverage", "options", "futures", "fractional")
    if any(bool(candidate.metadata_json.get(key)) for key in forbidden):
        raise ValueError("forbidden strategy exposure is blocked")
    intent = OrderIntent(
        ticker=snapshot.ticker, region=snapshot.region, side=OrderSide(candidate.side.value),
        order_type=OrderType(candidate.order_type.value), quantity=candidate.quantity,
        notional=candidate.notional, limit_price=candidate.limit_price,
        stop_loss_price=candidate.stop_loss_price, take_profit_price=candidate.take_profit_price,
        source_type="strategy_decision_draft", source_id=decision.decision_id,
        reason=candidate.rationale, confidence_score=decision.confidence_score,
        metadata_json={
            "strategy_run_id": decision.run_id, "strategy_candidate_id": candidate.candidate_id,
            "strategy_decision_id": decision.decision_id, "draft_only": True,
            "requires_risk_gate": True, "requires_execution_gate": True,
            "requires_sell_safety": decision.requires_sell_safety,
        },
    )
    repository.save_order_intent(intent)
    return intent
