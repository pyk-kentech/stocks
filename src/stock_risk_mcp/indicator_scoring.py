from __future__ import annotations

from stock_risk_mcp.indicators import IndicatorScore, IndicatorSignal, IndicatorValue
from stock_risk_mcp.models import Severity


WEIGHTS = {
    Severity.LOW: 1,
    Severity.MEDIUM: 3,
    Severity.HIGH: 5,
    Severity.CRITICAL: 10,
}


def score_indicators(ticker: str, indicators: list[IndicatorValue]) -> IndicatorScore:
    positive = [indicator for indicator in indicators if indicator.signal == IndicatorSignal.POSITIVE]
    negative = [indicator for indicator in indicators if indicator.signal == IndicatorSignal.NEGATIVE]
    positive_score = sum(WEIGHTS[indicator.severity] for indicator in positive)
    negative_score = sum(WEIGHTS[indicator.severity] for indicator in negative)
    return IndicatorScore(
        ticker=ticker,
        positive_score=positive_score,
        negative_score=negative_score,
        risk_penalty=negative_score,
        summary=_summary(positive_score, negative_score),
        contributing_indicators=[indicator.indicator_code for indicator in [*positive, *negative]],
    )


def _summary(positive_score: int, negative_score: int) -> str:
    if negative_score > positive_score:
        return "위험 신호가 긍정 신호보다 강해 추가 확인이 필요합니다."
    if positive_score > negative_score:
        return "긍정 신호가 우세하지만 매수 추천이 아닌 보조 분석 결과입니다."
    return "긍정과 위험 신호가 균형적이거나 뚜렷한 신호가 없습니다."
