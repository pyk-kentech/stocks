from __future__ import annotations

from stock_risk_mcp.basket import BasketCandidate
from stock_risk_mcp.setup import SetupGrade, TradeDecision
from stock_risk_mcp.strategy_policy import StrategyPolicy


def score_candidate(candidate: BasketCandidate, policy: StrategyPolicy | None = None) -> BasketCandidate:
    if policy is not None:
        return _score_candidate_with_policy(candidate, policy)
    score = {
        SetupGrade.A: 40,
        SetupGrade.B: 25,
        SetupGrade.C: 5,
        SetupGrade.NO_TRADE: -100,
    }[candidate.setup_grade]
    rr = candidate.risk_reward_ratio
    if rr is not None:
        if rr >= 4:
            score += 15
        elif rr >= 3:
            score += 10
        elif rr < 2.5:
            score -= 20
    if candidate.setup_score >= 80:
        score += 10
    elif candidate.setup_score >= 60:
        score += 5
    if candidate.decision == TradeDecision.PROPOSE:
        score += 10
    elif candidate.decision == TradeDecision.REVIEW:
        score += 3
    elif candidate.decision in {TradeDecision.BLOCK, TradeDecision.NO_TRADE}:
        score -= 100
    if candidate.max_loss_amount is None:
        score -= 20
    if candidate.position_size is None or candidate.position_size <= 0:
        score -= 30
    return candidate.model_copy(update={"score": score})


def _score_candidate_with_policy(candidate: BasketCandidate, policy: StrategyPolicy) -> BasketCandidate:
    setup_component = {
        SetupGrade.A: 100,
        SetupGrade.B: 70,
        SetupGrade.C: 30,
        SetupGrade.NO_TRADE: 0,
    }[candidate.setup_grade]
    rr = candidate.risk_reward_ratio
    if rr is None:
        rr_component = 0
    elif rr >= 4:
        rr_component = 100
    elif rr >= 3:
        rr_component = 80
    elif rr >= 2.5:
        rr_component = 60
    else:
        rr_component = 20
    decision_component = {
        TradeDecision.PROPOSE: 90,
        TradeDecision.REVIEW: 65,
        TradeDecision.BLOCK: 0,
        TradeDecision.NO_TRADE: 0,
    }[candidate.decision]
    setup_policy_weight = policy.weights.get("setup_grade_score", 0)
    rr_policy_weight = policy.weights.get("risk_reward_score", 0)
    policy_total = setup_policy_weight + rr_policy_weight
    if policy_total > 0:
        setup_weight = 0.60 * setup_policy_weight / policy_total
        rr_weight = 0.60 * rr_policy_weight / policy_total
    else:
        setup_weight = 0.35
        rr_weight = 0.25
    score = round(setup_component * setup_weight + rr_component * rr_weight + decision_component * 0.40)
    return candidate.model_copy(update={"score": score})
