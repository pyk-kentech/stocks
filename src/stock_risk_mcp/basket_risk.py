from __future__ import annotations

from collections import Counter

from stock_risk_mcp.basket import BasketAllocation, BasketCandidate, BasketPolicy, BasketRiskSummary


def summarize_basket_risk(
    candidates: list[BasketCandidate],
    allocations: list[BasketAllocation],
    policy: BasketPolicy,
    blocked_reasons: list[str] | None = None,
    warnings: list[str] | None = None,
) -> BasketRiskSummary:
    max_loss = policy.account_equity * policy.max_basket_loss_pct / 100
    max_notional = policy.account_equity * policy.max_basket_notional_pct / 100
    total_loss = sum(item.allocated_loss_amount for item in allocations)
    total_notional = sum(item.allocated_notional_value for item in allocations)
    allocated_tickers = {item.ticker for item in allocations}
    allocated_candidates = [candidate for candidate in candidates if candidate.ticker in allocated_tickers]
    return BasketRiskSummary(
        total_allocated_loss=total_loss,
        max_allowed_loss=max_loss,
        total_notional_value=total_notional,
        max_allowed_notional=max_notional,
        candidate_count=len(allocations),
        sector_counts=dict(Counter(candidate.sector or "UNKNOWN" for candidate in allocated_candidates)),
        theme_counts=dict(Counter(candidate.theme or "UNKNOWN" for candidate in allocated_candidates)),
        blocked_reasons=blocked_reasons or [],
        warnings=warnings or [],
        risk_ok=total_loss <= max_loss and total_notional <= max_notional,
    )
