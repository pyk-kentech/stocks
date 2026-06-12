from __future__ import annotations

import pytest

from stock_risk_mcp.basket import BasketPolicy
from stock_risk_mcp.basket_allocator import allocate_candidates
from stock_risk_mcp.setup import SetupGrade, TradeDecision
from tests.test_basket_builder import candidate


def test_allocator_distributes_loss_by_risk_units_and_respects_limits() -> None:
    policy = BasketPolicy(
        account_equity=10_000,
        cash_available=5_000,
        max_basket_loss_pct=1,
        max_basket_notional_pct=25,
        max_single_candidate_loss_pct=0.5,
        max_single_position_pct=5,
    )
    candidates = [
        candidate("AAA", SetupGrade.A, TradeDecision.PROPOSE, max_loss=100),
        candidate("BBB", SetupGrade.B, TradeDecision.REVIEW, max_loss=100),
    ]

    allocations = allocate_candidates(candidates, policy)
    by_ticker = {allocation.ticker: allocation for allocation in allocations}

    assert by_ticker["AAA"].allocated_loss_amount == pytest.approx(50)
    assert by_ticker["BBB"].allocated_loss_amount == pytest.approx(100 * 0.5 / 1.5)
    assert all(allocation.allocated_notional_value <= 500 for allocation in allocations)
    assert sum(allocation.allocated_loss_amount for allocation in allocations) <= 100
    assert sum(allocation.allocated_notional_value for allocation in allocations) <= 2500
