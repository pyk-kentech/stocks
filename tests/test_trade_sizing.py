from __future__ import annotations

import pytest

from stock_risk_mcp.setup import SetupGrade, TradeSizingPolicy
from stock_risk_mcp.trade_sizing import calculate_trade_size


def test_position_size_uses_max_loss_and_setup_multiplier() -> None:
    policy = TradeSizingPolicy(account_equity=10_000, cash_available=10_000, max_position_pct=100)

    result = calculate_trade_size(entry_price=10, risk_per_share=1, setup_grade=SetupGrade.A, policy=policy)
    b_result = calculate_trade_size(entry_price=10, risk_per_share=1, setup_grade=SetupGrade.B, policy=policy)

    assert result.max_loss_amount == pytest.approx(25)
    assert result.position_size == pytest.approx(25)
    assert b_result.max_loss_amount == pytest.approx(12.5)


def test_position_size_respects_cash_and_max_position_limits() -> None:
    cash_limited = calculate_trade_size(
        entry_price=10,
        risk_per_share=0.1,
        setup_grade=SetupGrade.A,
        policy=TradeSizingPolicy(account_equity=100_000, cash_available=500, max_position_pct=100),
    )
    position_limited = calculate_trade_size(
        entry_price=10,
        risk_per_share=0.1,
        setup_grade=SetupGrade.A,
        policy=TradeSizingPolicy(account_equity=10_000, cash_available=10_000, max_position_pct=5),
    )

    assert cash_limited.notional_value == pytest.approx(500)
    assert position_limited.notional_value == pytest.approx(500)
