from __future__ import annotations

from stock_risk_mcp.basket import BasketCandidate, BasketPolicy
from stock_risk_mcp.basket_scoring import score_candidate
from stock_risk_mcp.setup import SetupGrade, TradeDecision
from stock_risk_mcp.strategy_policy import apply_strategy_policy_to_basket_policy, create_default_strategy_policy


def test_policy_none_preserves_fixed_basket_candidate_score() -> None:
    candidate = _candidate(SetupGrade.A, 4, TradeDecision.PROPOSE)

    assert score_candidate(candidate, None) == score_candidate(candidate)
    assert score_candidate(candidate).score == 75


def test_policy_weighted_basket_score_uses_fixed_decision_and_normalized_setup_rr_weights() -> None:
    policy = create_default_strategy_policy().model_copy(
        update={"weights": {**create_default_strategy_policy().weights, "setup_grade_score": 0.20, "risk_reward_score": 0.10}}
    )

    propose = score_candidate(_candidate(SetupGrade.A, 4, TradeDecision.PROPOSE), policy)
    review = score_candidate(_candidate(SetupGrade.A, 4, TradeDecision.REVIEW), policy)

    # setup=100 * .40, rr=100 * .20, decision(PROPOSE)=90 * .40
    assert propose.score == 96
    # The decision component changes only the PROPOSE/REVIEW priority.
    assert review.score == 86


def test_strategy_policy_maps_only_allowed_basket_soft_fields() -> None:
    base = BasketPolicy(account_equity=10_000, cash_available=5_000, max_single_position_pct=4)
    strategy = create_default_strategy_policy().model_copy(
        update={
            "basket_rules": {**create_default_strategy_policy().basket_rules, "max_candidates": 7},
            "risk_overrides": {**create_default_strategy_policy().risk_overrides, "A_risk_unit": 1.5},
        }
    )

    mapped = apply_strategy_policy_to_basket_policy(base, strategy)

    assert mapped.max_candidates == 7
    assert mapped.setup_risk_units[SetupGrade.A] == 1.5
    assert mapped.max_single_position_pct == 4
    assert mapped.account_equity == 10_000


def _candidate(grade: SetupGrade, rr: float, decision: TradeDecision) -> BasketCandidate:
    return BasketCandidate(
        ticker="SAFE",
        setup_grade=grade,
        setup_score=85,
        decision=decision,
        entry_price=10,
        stop_price=9,
        target_price=14,
        risk_reward_ratio=rr,
        max_loss_amount=25,
        position_size=25,
        notional_value=250,
        score=0,
        reasons=[],
        warnings=[],
    )
