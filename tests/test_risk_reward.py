from __future__ import annotations

import pytest

from stock_risk_mcp.risk_reward import calculate_risk_reward


def test_risk_reward_ratio_is_calculated() -> None:
    result = calculate_risk_reward(entry_price=10, stop_price=9, target_price=14)

    assert result.risk_per_share == 1
    assert result.reward_per_share == 4
    assert result.risk_reward_ratio == 4


def test_risk_reward_rejects_zero_risk() -> None:
    with pytest.raises(ValueError, match="risk_per_share"):
        calculate_risk_reward(entry_price=10, stop_price=10, target_price=14)
