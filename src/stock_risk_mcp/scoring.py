from __future__ import annotations

from dataclasses import dataclass

from stock_risk_mcp.models import CompanyRisk, DilutionRisk, MarketSnapshot, SignalLevel, TossSignal


@dataclass(frozen=True)
class ScoreBreakdown:
    score: int
    positive_factors: list[str]
    negative_factors: list[str]


def clamp_score(score: int) -> int:
    return max(0, min(100, score))


def calculate_soft_score(
    market: MarketSnapshot,
    company: CompanyRisk,
    toss_signal: TossSignal,
) -> ScoreBreakdown:
    score = 50
    positive_factors: list[str] = []
    negative_factors: list[str] = []

    if market.avg_dollar_volume_20d is not None and market.avg_dollar_volume_20d >= 50_000_000:
        score += 8
        positive_factors.append("20일 평균 거래대금이 5천만 달러 이상입니다.")
    if market.volatility_20d_pct is not None and market.volatility_20d_pct < 3:
        score += 5
        positive_factors.append("20일 변동성이 3% 미만입니다.")
    if market.return_5d_pct is not None and -10 <= market.return_5d_pct <= 15:
        score += 5
        positive_factors.append("5일 수익률이 과열 구간이 아닙니다.")
    if company.dilution_risk == DilutionRisk.LOW:
        score += 5
        positive_factors.append("희석 리스크가 낮습니다.")
    if toss_signal.consensus_level == SignalLevel.HIGH:
        score += 8
        positive_factors.append("토스 추적 투자자 합의 수준이 높습니다.")
    elif toss_signal.consensus_level == SignalLevel.MEDIUM:
        score += 4
        positive_factors.append("토스 추적 투자자 합의 수준이 중간입니다.")
    if toss_signal.signal_quality == SignalLevel.HIGH:
        score += 8
        positive_factors.append("토스 신호 품질이 높습니다.")
    elif toss_signal.signal_quality == SignalLevel.MEDIUM:
        score += 4
        positive_factors.append("토스 신호 품질이 중간입니다.")
    if (
        toss_signal.historical_follow_return_30d_pct is not None
        and toss_signal.historical_follow_return_30d_pct > 5
    ):
        score += 5
        positive_factors.append("과거 추종 30일 수익률이 5%를 초과했습니다.")

    if market.avg_dollar_volume_20d is not None and market.avg_dollar_volume_20d < 20_000_000:
        score -= 8
        negative_factors.append("20일 평균 거래대금이 2천만 달러 미만입니다.")
    if market.volatility_20d_pct is not None and market.volatility_20d_pct > 8:
        score -= 10
        negative_factors.append("20일 변동성이 8%를 초과했습니다.")
    if market.return_5d_pct is not None and market.return_5d_pct > 40:
        score -= 12
        negative_factors.append("5일 수익률이 40%를 초과해 급등 리스크가 있습니다.")
    if company.dilution_risk == DilutionRisk.MEDIUM:
        score -= 15
        negative_factors.append("희석 리스크가 중간 수준입니다.")
    if toss_signal.signal_quality == SignalLevel.LOW:
        score -= 5
        negative_factors.append("토스 신호 품질이 낮습니다.")
    if (
        toss_signal.historical_follow_return_30d_pct is not None
        and toss_signal.historical_follow_return_30d_pct < 0
    ):
        score -= 5
        negative_factors.append("과거 추종 30일 수익률이 음수입니다.")

    return ScoreBreakdown(
        score=clamp_score(score),
        positive_factors=positive_factors,
        negative_factors=negative_factors,
    )
