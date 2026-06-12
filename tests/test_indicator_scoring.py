from __future__ import annotations

from stock_risk_mcp.indicator_scoring import score_indicators
from stock_risk_mcp.indicators import IndicatorSignal, IndicatorValue
from stock_risk_mcp.models import Severity


def test_indicator_scoring_uses_signal_and_severity_weights() -> None:
    indicators = [
        _indicator("AVG_DOLLAR_VOLUME_20D", IndicatorSignal.POSITIVE, Severity.LOW),
        _indicator("RETURN_5D_PCT", IndicatorSignal.NEGATIVE, Severity.HIGH),
        _indicator("RSI_14", IndicatorSignal.NEUTRAL, Severity.MEDIUM),
    ]

    score = score_indicators("SAFE", indicators)

    assert score.positive_score == 1
    assert score.negative_score == 5
    assert score.risk_penalty == 5
    assert score.contributing_indicators == ["AVG_DOLLAR_VOLUME_20D", "RETURN_5D_PCT"]
    assert "위험 신호" in score.summary


def _indicator(code: str, signal: IndicatorSignal, severity: Severity) -> IndicatorValue:
    return IndicatorValue(
        ticker="SAFE",
        indicator_code=code,
        category="TEST",
        value=1,
        signal=signal,
        severity=severity,
        interpretation=code,
        beginner_explanation=code,
    )
