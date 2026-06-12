from __future__ import annotations

from stock_risk_mcp.basket import BasketCandidate, BasketPolicy
from stock_risk_mcp.basket_builder import build_basket
from stock_risk_mcp.setup import SetupGrade, TradeDecision


def test_builder_filters_invalid_and_c_candidates() -> None:
    policy = BasketPolicy(account_equity=10_000, cash_available=5_000, min_candidates=1)
    candidates = [
        candidate("GOOD", SetupGrade.A, TradeDecision.PROPOSE),
        candidate("BLOCK", SetupGrade.A, TradeDecision.BLOCK),
        candidate("CSET", SetupGrade.C, TradeDecision.PROPOSE),
    ]

    plan = build_basket(candidates, policy)

    assert [item.ticker for item in plan.allocations] == ["GOOD"]
    assert {item.ticker for item in plan.blocked} == {"BLOCK", "CSET"}


def test_builder_blocks_low_score_candidates_for_sector_and_theme_concentration() -> None:
    policy = BasketPolicy(
        account_equity=10_000,
        cash_available=5_000,
        min_candidates=2,
        max_same_sector_count=2,
        max_same_theme_count=2,
    )
    candidates = [
        candidate("HIGH", SetupGrade.A, TradeDecision.PROPOSE, sector="BIO", theme="AI"),
        candidate("MID", SetupGrade.B, TradeDecision.REVIEW, sector="BIO", theme="AI"),
        candidate("LOW", SetupGrade.B, TradeDecision.REVIEW, rr=2.6, setup_score=60, sector="BIO", theme="AI"),
    ]

    plan = build_basket(candidates, policy)

    assert "LOW" in {item.ticker for item in plan.blocked}
    assert len(plan.allocations) == 2


def test_builder_decides_no_trade_for_too_few_candidates_and_proposes_normal_basket() -> None:
    no_trade = build_basket(
        [candidate("ONLY", SetupGrade.A, TradeDecision.PROPOSE)],
        BasketPolicy(account_equity=10_000, cash_available=5_000, min_candidates=3),
    )
    propose = build_basket(
        [
            candidate("AAA", SetupGrade.A, TradeDecision.PROPOSE, sector="BIO", theme="AI"),
            candidate("BBB", SetupGrade.A, TradeDecision.PROPOSE, sector="TECH", theme="CLOUD"),
            candidate("CCC", SetupGrade.B, TradeDecision.REVIEW, sector="ENERGY", theme="SOLAR"),
        ],
        BasketPolicy(account_equity=10_000, cash_available=5_000, min_candidates=3),
    )

    assert no_trade.decision == TradeDecision.NO_TRADE
    assert propose.decision in {TradeDecision.PROPOSE, TradeDecision.REVIEW}


def candidate(
    ticker: str,
    grade: SetupGrade,
    decision: TradeDecision,
    rr: float | None = 4,
    setup_score: int = 85,
    max_loss: float | None = 25,
    sector: str | None = None,
    theme: str | None = None,
) -> BasketCandidate:
    return BasketCandidate(
        ticker=ticker,
        setup_grade=grade,
        setup_score=setup_score,
        decision=decision,
        entry_price=10,
        stop_price=9,
        target_price=14,
        risk_reward_ratio=rr,
        max_loss_amount=max_loss,
        position_size=25,
        notional_value=250,
        sector=sector,
        theme=theme,
        score=0,
        reasons=[],
        warnings=[],
    )
