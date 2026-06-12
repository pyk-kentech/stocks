from __future__ import annotations

from datetime import date

from stock_risk_mcp.candidate_universe import CandidateDecision, CandidateScanPolicy, CandidateScanResult
from stock_risk_mcp.setup import SetupGrade, TradeDecision


def evaluate_candidate(
    scan_run_id, ticker, as_of_date, policy, setup_grade, setup_score, trade_decision, price,
    return_1d, return_5d, return_20d, avg_dollar_volume, volume_spike, dollar_volume_spike,
    volatility, risk_reward, noncompliant, metadata=None,
) -> CandidateScanResult:
    score = {SetupGrade.A: 35, SetupGrade.B: 25, SetupGrade.C: 5, SetupGrade.NO_TRADE: -50}[setup_grade]
    score += {TradeDecision.PROPOSE: 20, TradeDecision.REVIEW: 10, TradeDecision.BLOCK: 0, TradeDecision.NO_TRADE: 0}[trade_decision]
    reasons, warnings, hard = [], [], []
    if risk_reward is not None:
        score += 15 if risk_reward >= 4 else 10 if risk_reward >= 3 else -20 if risk_reward < 2.5 else 0
    for value, label in ((volume_spike, "volume spike"), (dollar_volume_spike, "dollar volume spike")):
        if value is not None and value >= 2:
            score += 10
            reasons.append(f"strong {label}")
    if avg_dollar_volume is not None and avg_dollar_volume >= 50_000_000:
        score += 10
        reasons.append("sufficient dollar volume")
    if return_5d is not None and 5 <= return_5d <= 40:
        score += 10
    if return_5d is not None and return_5d > policy.max_return_5d_pct:
        score -= 30
    if volatility is not None and volatility > policy.max_volatility_20d_pct:
        score -= 20
    if price is None:
        score -= 30
        hard.append("no price data")
    elif price < policy.min_price:
        score -= 30
        hard.append("price below minimum")
    elif policy.max_price is not None and price > policy.max_price:
        hard.append("price above maximum")
    if avg_dollar_volume is None:
        score -= 30
    elif avg_dollar_volume < policy.min_avg_dollar_volume_20d:
        score -= 40
        if policy.exclude_low_liquidity:
            hard.append("low liquidity")
    if setup_grade == SetupGrade.C and not policy.include_c_setups:
        hard.append("C setup disabled")
    if setup_score < policy.min_setup_score:
        hard.append("setup score below minimum")
    if volume_spike is None or volume_spike < policy.min_volume_spike_ratio:
        hard.append("volume spike below minimum")
    if dollar_volume_spike is None or dollar_volume_spike < policy.min_dollar_volume_spike_ratio:
        hard.append("dollar volume spike below minimum")
    if policy.min_return_1d_pct is not None and (return_1d is None or return_1d < policy.min_return_1d_pct):
        hard.append("1-day return below minimum")
    if policy.min_return_5d_pct is not None and (return_5d is None or return_5d < policy.min_return_5d_pct):
        hard.append("5-day return below minimum")
    if setup_grade == SetupGrade.NO_TRADE:
        hard.append("NO_TRADE setup")
    if trade_decision in {TradeDecision.BLOCK, TradeDecision.NO_TRADE}:
        hard.append(f"trade plan decision {trade_decision.value}")
    if noncompliant is True and policy.exclude_nasdaq_noncompliant:
        hard.append("Nasdaq noncompliant")
    elif noncompliant is None:
        warnings.append("Compliance status unknown")
    score = max(0, min(100, score))
    if hard:
        decision = CandidateDecision.EXCLUDE
    elif score >= 70 and trade_decision == TradeDecision.PROPOSE:
        decision = CandidateDecision.INCLUDE
    elif score >= 50 and policy.include_review_setups:
        decision = CandidateDecision.WATCH
    elif score >= 40 and policy.include_c_setups:
        decision = CandidateDecision.WATCH
    else:
        decision = CandidateDecision.EXCLUDE
    return CandidateScanResult(
        scan_run_id=scan_run_id, ticker=ticker, as_of_date=as_of_date, decision=decision, score=score,
        setup_grade=setup_grade.value, setup_score=setup_score, trade_plan_decision=trade_decision.value,
        price=price, return_1d_pct=return_1d, return_5d_pct=return_5d, return_20d_pct=return_20d,
        avg_dollar_volume_20d=avg_dollar_volume, volume_spike_ratio=volume_spike,
        dollar_volume_spike_ratio=dollar_volume_spike, volatility_20d_pct=volatility,
        risk_reward_ratio=risk_reward, reasons=[*reasons, *hard], warnings=warnings, metadata=metadata or {},
    )
