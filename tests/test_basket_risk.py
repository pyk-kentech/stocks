from __future__ import annotations

from stock_risk_mcp.basket import BasketPolicy
from stock_risk_mcp.basket_allocator import allocate_candidates
from stock_risk_mcp.basket_risk import summarize_basket_risk
from stock_risk_mcp.setup import SetupGrade, TradeDecision
from tests.test_basket_builder import candidate


def test_risk_summary_tracks_totals_and_unknown_concentration() -> None:
    policy = BasketPolicy(account_equity=10_000, cash_available=5_000)
    candidates = [
        candidate("AAA", SetupGrade.A, TradeDecision.PROPOSE),
        candidate("BBB", SetupGrade.B, TradeDecision.REVIEW),
    ]
    allocations = allocate_candidates(candidates, policy)

    summary = summarize_basket_risk(candidates, allocations, policy)

    assert summary.total_allocated_loss <= summary.max_allowed_loss
    assert summary.total_notional_value <= summary.max_allowed_notional
    assert summary.sector_counts == {"UNKNOWN": 2}
    assert summary.theme_counts == {"UNKNOWN": 2}
    assert summary.risk_ok is True
