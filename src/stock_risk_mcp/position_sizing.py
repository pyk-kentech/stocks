from __future__ import annotations

from stock_risk_mcp.models import PortfolioState, RiskPolicy


def score_to_order_pct(score: int, policy: RiskPolicy) -> float:
    if score < 60:
        return 0.0
    if score < 75:
        return 0.5
    if score < 85:
        return 1.0
    return policy.max_order_pct


def calculate_position_size(
    score: int,
    policy: RiskPolicy,
    portfolio: PortfolioState,
    blocked: bool = False,
) -> tuple[float, float]:
    remaining_position_pct = max(0.0, policy.max_single_position_pct - portfolio.current_position_pct)
    max_position_pct = min(policy.max_single_position_pct, portfolio.current_position_pct + remaining_position_pct)

    if blocked:
        return 0.0, round(max_position_pct, 4)

    order_pct = min(score_to_order_pct(score, policy), remaining_position_pct)
    order_usd = portfolio.total_equity_usd * (order_pct / 100)
    order_usd = min(order_usd, portfolio.cash_usd)
    return round(order_usd, 2), round(max_position_pct, 4)
