from __future__ import annotations

from datetime import datetime

from stock_risk_mcp.basket import BasketCandidate, BasketMode, BasketPlan, BasketPolicy, new_basket_id
from stock_risk_mcp.basket_allocator import allocate_candidates
from stock_risk_mcp.basket_risk import summarize_basket_risk
from stock_risk_mcp.basket_scoring import score_candidate
from stock_risk_mcp.setup import SetupGrade, TradeDecision
from stock_risk_mcp.strategy_policy import StrategyPolicy


def build_basket(
    candidates: list[BasketCandidate],
    policy: BasketPolicy,
    strategy_policy: StrategyPolicy | None = None,
) -> BasketPlan:
    if strategy_policy is None:
        scored = [score_candidate(candidate) for candidate in candidates]
    else:
        scored = [
            candidate
            if candidate.decision in {TradeDecision.BLOCK, TradeDecision.NO_TRADE}
            else score_candidate(candidate, strategy_policy)
            for candidate in candidates
        ]
    eligible: list[BasketCandidate] = []
    blocked: list[BasketCandidate] = []
    blocked_reasons: list[str] = []

    for candidate in scored:
        reason = _blocked_reason(candidate, policy)
        if reason:
            blocked.append(_with_block_reason(candidate, reason))
            blocked_reasons.append(reason)
        else:
            eligible.append(candidate)

    eligible, concentration_blocked, concentration_reasons = _apply_concentration(eligible, policy)
    blocked.extend(concentration_blocked)
    blocked_reasons.extend(concentration_reasons)
    eligible = sorted(eligible, key=lambda item: item.score, reverse=True)[: policy.max_candidates]
    allocations = allocate_candidates(eligible, policy)
    warnings = [warning for candidate in eligible for warning in candidate.warnings]
    risk_summary = summarize_basket_risk(eligible, allocations, policy, blocked_reasons, warnings)
    decision = _decision(risk_summary, policy)
    return BasketPlan(
        basket_id=new_basket_id(),
        basket_name=policy.basket_name,
        mode=BasketMode.PAPER_TRADING,
        policy=policy,
        candidates=scored,
        allocations=allocations,
        blocked=blocked,
        risk_summary=risk_summary,
        decision=decision,
        beginner_summary=_summary(decision),
        created_at=datetime.now(),
        policy_id=strategy_policy.policy_id if strategy_policy else None,
        policy_version=strategy_policy.version if strategy_policy else None,
        basket_scoring_mode="POLICY_WEIGHTED" if strategy_policy else "FIXED_RULES",
    )


def _blocked_reason(candidate: BasketCandidate, policy: BasketPolicy) -> str | None:
    if candidate.decision in {TradeDecision.BLOCK, TradeDecision.NO_TRADE}:
        return f"{candidate.ticker}: decision is {candidate.decision.value}"
    if candidate.decision == TradeDecision.REVIEW and not policy.allow_review_candidates:
        return f"{candidate.ticker}: REVIEW candidates are disabled"
    if candidate.setup_grade == SetupGrade.C and not policy.allow_c_setup:
        return f"{candidate.ticker}: C setup is disabled"
    if candidate.setup_grade == SetupGrade.NO_TRADE:
        return f"{candidate.ticker}: NO_TRADE setup"
    if candidate.risk_reward_ratio is None:
        return f"{candidate.ticker}: missing risk/reward ratio"
    if candidate.position_size is None or candidate.position_size <= 0:
        return f"{candidate.ticker}: invalid position size"
    if candidate.entry_price is None or candidate.stop_price is None:
        return f"{candidate.ticker}: missing entry or stop price"
    return None


def _apply_concentration(
    candidates: list[BasketCandidate], policy: BasketPolicy
) -> tuple[list[BasketCandidate], list[BasketCandidate], list[str]]:
    eligible = list(candidates)
    blocked: list[BasketCandidate] = []
    reasons: list[str] = []
    while True:
        offender = _lowest_concentration_offender(eligible, policy)
        if offender is None:
            return eligible, blocked, reasons
        eligible.remove(offender)
        reason = f"{offender.ticker}: sector/theme concentration limit"
        blocked.append(_with_block_reason(offender, reason))
        reasons.append(reason)


def _lowest_concentration_offender(candidates: list[BasketCandidate], policy: BasketPolicy) -> BasketCandidate | None:
    for field, limit in (("sector", policy.max_same_sector_count), ("theme", policy.max_same_theme_count)):
        groups: dict[str, list[BasketCandidate]] = {}
        for candidate in candidates:
            groups.setdefault(getattr(candidate, field) or "UNKNOWN", []).append(candidate)
        over_limit = [item for group in groups.values() if len(group) > limit for item in group]
        if over_limit:
            return min(over_limit, key=lambda item: item.score)
    return None


def _with_block_reason(candidate: BasketCandidate, reason: str) -> BasketCandidate:
    return candidate.model_copy(update={"reasons": [*candidate.reasons, reason]})


def _decision(risk_summary, policy: BasketPolicy) -> TradeDecision:
    if risk_summary.candidate_count < policy.min_candidates:
        return TradeDecision.NO_TRADE
    if not risk_summary.risk_ok:
        return TradeDecision.BLOCK
    if risk_summary.warnings:
        return TradeDecision.REVIEW
    return TradeDecision.PROPOSE


def _summary(decision: TradeDecision) -> str:
    if decision == TradeDecision.PROPOSE:
        return "바스켓 후보가 충분하고 전체 최대 손실 한도 안에서 포지션 크기가 계산되었습니다. 실제 주문 전 개별 Risk Engine 확인이 필요합니다."
    if decision == TradeDecision.REVIEW:
        return "바스켓 구성은 가능하지만 일부 경고가 있어 사용자 확인이 필요합니다."
    if decision == TradeDecision.NO_TRADE:
        return "조건을 만족하는 후보 수가 부족해 오늘은 바스켓 진입을 쉬는 것이 안전합니다."
    return "전체 손실 한도 또는 노출 한도를 초과하여 바스켓 진입을 차단합니다."
