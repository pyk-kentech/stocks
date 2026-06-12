from __future__ import annotations

from stock_risk_mcp.basket import BasketCandidate
from stock_risk_mcp.setup import SetupGrade, TradeDecision


def score_candidate(candidate: BasketCandidate) -> BasketCandidate:
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
