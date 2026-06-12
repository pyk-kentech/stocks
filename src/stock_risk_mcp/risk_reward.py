from __future__ import annotations

from stock_risk_mcp.setup import RiskRewardResult


def calculate_risk_reward(entry_price: float, stop_price: float, target_price: float) -> RiskRewardResult:
    risk_per_share = abs(entry_price - stop_price)
    if risk_per_share <= 0:
        raise ValueError("risk_per_share must be greater than zero")
    reward_per_share = abs(target_price - entry_price)
    return RiskRewardResult(
        entry_price=entry_price,
        stop_price=stop_price,
        target_price=target_price,
        risk_per_share=risk_per_share,
        reward_per_share=reward_per_share,
        risk_reward_ratio=reward_per_share / risk_per_share,
    )
