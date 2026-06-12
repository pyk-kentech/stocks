from __future__ import annotations

from stock_risk_mcp.basket import BasketAllocation, BasketCandidate, BasketPolicy


def allocate_candidates(candidates: list[BasketCandidate], policy: BasketPolicy) -> list[BasketAllocation]:
    selected = sorted(candidates, key=lambda item: item.score, reverse=True)[: policy.max_candidates]
    total_units = sum(policy.setup_risk_units.get(candidate.setup_grade, 0) for candidate in selected)
    if total_units <= 0:
        return []
    max_basket_loss = policy.account_equity * policy.max_basket_loss_pct / 100
    max_basket_notional = policy.account_equity * policy.max_basket_notional_pct / 100
    single_loss_limit = policy.account_equity * policy.max_single_candidate_loss_pct / 100
    single_notional_limit = policy.account_equity * policy.max_single_position_pct / 100
    remaining_notional = min(max_basket_notional, policy.cash_available)
    allocations: list[BasketAllocation] = []

    for candidate in selected:
        if candidate.entry_price is None or candidate.stop_price is None:
            continue
        risk_per_share = abs(candidate.entry_price - candidate.stop_price)
        if risk_per_share <= 0:
            continue
        unit = policy.setup_risk_units.get(candidate.setup_grade, 0)
        allocated_loss = max_basket_loss * unit / total_units
        allocated_loss = min(allocated_loss, single_loss_limit)
        if candidate.max_loss_amount is not None:
            allocated_loss = min(allocated_loss, candidate.max_loss_amount)
        position_size = allocated_loss / risk_per_share
        notional = position_size * candidate.entry_price
        allowed_notional = min(single_notional_limit, remaining_notional)
        if notional > allowed_notional:
            position_size = allowed_notional / candidate.entry_price if candidate.entry_price else 0
            notional = position_size * candidate.entry_price
            allocated_loss = position_size * risk_per_share
        if position_size <= 0:
            continue
        allocations.append(
            BasketAllocation(
                ticker=candidate.ticker,
                setup_grade=candidate.setup_grade,
                allocated_loss_amount=allocated_loss,
                allocated_notional_value=notional,
                position_size=position_size,
                entry_price=candidate.entry_price,
                stop_price=candidate.stop_price,
                target_price=candidate.target_price,
                risk_reward_ratio=candidate.risk_reward_ratio,
                allocation_reason=f"{candidate.setup_grade.value} setup risk-unit allocation",
            )
        )
        remaining_notional -= notional
    return allocations
