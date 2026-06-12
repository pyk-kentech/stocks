from __future__ import annotations

from stock_risk_mcp.basket_scoring import score_candidate
from tests.test_basket_builder import candidate
from stock_risk_mcp.setup import SetupGrade, TradeDecision


def test_candidate_scoring_rewards_a_and_b_and_blocks_no_trade() -> None:
    a = score_candidate(candidate("A", SetupGrade.A, TradeDecision.PROPOSE, rr=4, setup_score=85))
    b = score_candidate(candidate("B", SetupGrade.B, TradeDecision.REVIEW, rr=3, setup_score=65))
    no_trade = score_candidate(candidate("X", SetupGrade.NO_TRADE, TradeDecision.NO_TRADE, rr=None))

    assert a.score > b.score
    assert b.score > 0
    assert no_trade.score < 0
