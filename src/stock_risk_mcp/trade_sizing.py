from __future__ import annotations

from stock_risk_mcp.setup import SetupGrade, TradeSizeResult, TradeSizingPolicy


def calculate_trade_size(
    entry_price: float,
    risk_per_share: float,
    setup_grade: SetupGrade,
    policy: TradeSizingPolicy,
) -> TradeSizeResult:
    if risk_per_share <= 0 or entry_price <= 0:
        return TradeSizeResult(max_loss_amount=0, position_size=0, notional_value=0)
    multiplier = policy.setup_risk_multipliers.get(setup_grade, 0.0)
    max_loss_amount = policy.account_equity * policy.max_single_trade_loss_pct / 100 * multiplier
    position_size = max_loss_amount / risk_per_share
    notional_limit = min(policy.cash_available, policy.account_equity * policy.max_position_pct / 100)
    position_size = min(position_size, notional_limit / entry_price)
    return TradeSizeResult(
        max_loss_amount=max_loss_amount,
        position_size=position_size,
        notional_value=position_size * entry_price,
    )
