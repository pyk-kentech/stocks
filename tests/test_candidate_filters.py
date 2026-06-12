from datetime import date

from stock_risk_mcp.candidate_filters import evaluate_candidate
from stock_risk_mcp.candidate_universe import CandidateDecision, CandidateScanPolicy
from stock_risk_mcp.setup import SetupGrade, TradeDecision


def test_filters_reward_volume_and_exclude_low_liquidity_and_no_trade() -> None:
    policy = CandidateScanPolicy()
    strong = evaluate_candidate("run", "AAA", date.today(), policy, SetupGrade.A, 85, TradeDecision.PROPOSE, 10, 10, 5, 20, 60_000_000, 2.5, 2.5, 3, 4, False)
    low = evaluate_candidate("run", "LOW", date.today(), policy, SetupGrade.A, 85, TradeDecision.PROPOSE, 10, 10, 5, 20, 1_000_000, 2.5, 2.5, 3, 4, False)
    no_trade = evaluate_candidate("run", "NO", date.today(), policy, SetupGrade.NO_TRADE, 10, TradeDecision.NO_TRADE, 10, None, None, None, None, None, None, None, None, False)

    assert strong.decision == CandidateDecision.INCLUDE
    assert strong.score > low.score
    assert low.decision == CandidateDecision.EXCLUDE
    assert no_trade.decision == CandidateDecision.EXCLUDE


def test_noncompliant_excludes_but_unknown_only_warns() -> None:
    policy = CandidateScanPolicy()
    bad = evaluate_candidate("run", "BAD", date.today(), policy, SetupGrade.A, 85, TradeDecision.PROPOSE, 10, 10, 5, 20, 60_000_000, 2, 2, 3, 4, True)
    unknown = evaluate_candidate("run", "UNK", date.today(), policy, SetupGrade.A, 85, TradeDecision.PROPOSE, 10, 10, 5, 20, 60_000_000, 2, 2, 3, 4, None)

    assert bad.decision == CandidateDecision.EXCLUDE
    assert unknown.decision != CandidateDecision.EXCLUDE
    assert any("unknown" in warning.lower() for warning in unknown.warnings)


def test_configured_scan_policy_thresholds_filter_candidates() -> None:
    policy = CandidateScanPolicy(
        max_price=20,
        min_volume_spike_ratio=2,
        min_dollar_volume_spike_ratio=2,
        min_return_1d_pct=1,
        min_return_5d_pct=5,
        min_setup_score=70,
    )
    result = evaluate_candidate(
        "run", "MISS", date.today(), policy, SetupGrade.B, 60, TradeDecision.PROPOSE,
        25, 0, 4, 20, 60_000_000, 1.5, 1.5, 3, 4, False,
    )

    assert result.decision == CandidateDecision.EXCLUDE
    assert any("maximum" in reason for reason in result.reasons)
    assert any("setup score" in reason for reason in result.reasons)
