from __future__ import annotations

from stock_risk_mcp.indicators import IndicatorSignal, IndicatorValue
from stock_risk_mcp.models import Evidence, Severity


CATEGORIES = {
    "RETURN_1D_PCT": "PRICE_TREND",
    "RETURN_5D_PCT": "PRICE_TREND",
    "RETURN_20D_PCT": "PRICE_TREND",
    "RETURN_60D_PCT": "PRICE_TREND",
    "SMA_20": "PRICE_TREND",
    "SMA_60": "PRICE_TREND",
    "SMA_120": "PRICE_TREND",
    "DISTANCE_FROM_SMA_20_PCT": "PRICE_TREND",
    "DISTANCE_FROM_SMA_60_PCT": "PRICE_TREND",
    "AVG_DOLLAR_VOLUME_20D": "LIQUIDITY",
    "VOLUME_SPIKE_RATIO": "LIQUIDITY",
    "DOLLAR_VOLUME_SPIKE_RATIO": "LIQUIDITY",
    "VOLATILITY_20D_PCT": "VOLATILITY",
    "ATR_14_PCT": "VOLATILITY",
    "MAX_DRAWDOWN_60D_PCT": "VOLATILITY",
    "RSI_14": "TECHNICAL",
    "BOLLINGER_POSITION": "TECHNICAL",
}


def interpret_indicators(
    ticker: str,
    raw_values: dict[str, float | None],
    evidence: Evidence | None = None,
) -> list[IndicatorValue]:
    return [_interpret(ticker, code, value, raw_values, evidence) for code, value in raw_values.items()]


def _interpret(
    ticker: str,
    code: str,
    value: float | None,
    all_values: dict[str, float | None],
    evidence: Evidence | None,
) -> IndicatorValue:
    signal, severity, message = _rule(code, value, all_values)
    return IndicatorValue(
        ticker=ticker,
        indicator_code=code,
        category=CATEGORIES.get(code, "OTHER"),
        value=value,
        unit=_unit(code),
        signal=signal,
        severity=severity,
        interpretation=message,
        beginner_explanation=message,
        evidence=evidence,
    )


def _rule(
    code: str,
    value: float | None,
    all_values: dict[str, float | None],
) -> tuple[IndicatorSignal, Severity, str]:
    if value is None:
        return IndicatorSignal.UNKNOWN, Severity.LOW, "계산에 필요한 가격 데이터가 부족합니다."
    if code == "RETURN_5D_PCT":
        if value > 80:
            return IndicatorSignal.NEGATIVE, Severity.HIGH, "최근 5일 급등으로 추격매수 위험이 큽니다."
        if value > 40:
            return IndicatorSignal.NEGATIVE, Severity.MEDIUM, "단기 과열 가능성이 있습니다."
        if -10 <= value <= 15:
            return IndicatorSignal.NEUTRAL, Severity.LOW, "단기 과열 수준은 아닙니다."
    if code == "AVG_DOLLAR_VOLUME_20D":
        if value < 10_000_000:
            return IndicatorSignal.NEGATIVE, Severity.HIGH, "평균 거래대금이 부족해 진입/청산이 어려울 수 있습니다."
        if value >= 50_000_000:
            return IndicatorSignal.POSITIVE, Severity.LOW, "거래대금이 충분해 유동성은 양호합니다."
    if code == "VOLATILITY_20D_PCT":
        if value > 8:
            return IndicatorSignal.NEGATIVE, Severity.HIGH, "최근 변동성이 높아 손절폭과 포지션 크기를 줄여야 합니다."
        if value < 3:
            return IndicatorSignal.POSITIVE, Severity.LOW, "최근 변동성은 비교적 낮습니다."
    if code == "RSI_14":
        if value > 70:
            return IndicatorSignal.NEGATIVE, Severity.MEDIUM, "RSI가 과매수 구간이라 신규 진입은 조심해야 합니다."
        if value < 30:
            return IndicatorSignal.NEUTRAL, Severity.MEDIUM, "RSI가 과매도 구간이지만 무조건 매수 신호는 아닙니다."
        if 40 <= value <= 60:
            return IndicatorSignal.NEUTRAL, Severity.LOW, "RSI는 중립 구간입니다."
    if code == "MAX_DRAWDOWN_60D_PCT":
        if value < -30:
            return IndicatorSignal.NEGATIVE, Severity.HIGH, "최근 60일 동안 큰 낙폭을 경험한 종목입니다."
        if value < -15:
            return IndicatorSignal.NEGATIVE, Severity.MEDIUM, "최근 낙폭 위험이 존재합니다."
    if code == "VOLUME_SPIKE_RATIO":
        if value > 5 and (all_values.get("RETURN_5D_PCT") or 0) > 40:
            return IndicatorSignal.NEGATIVE, Severity.HIGH, "거래량 급증과 단기 급등이 함께 나타나 추격매수 위험이 큽니다."
        if value > 3:
            return IndicatorSignal.NEUTRAL, Severity.MEDIUM, "시장 관심이 급격히 증가했습니다."
    if code == "BOLLINGER_POSITION":
        if value > 1:
            return IndicatorSignal.NEGATIVE, Severity.MEDIUM, "볼린저 밴드 상단을 넘어 단기 과열 가능성이 있습니다."
        if value < 0:
            return IndicatorSignal.NEUTRAL, Severity.MEDIUM, "볼린저 밴드 하단 아래로 내려와 낙폭이 큰 상태입니다."
    return IndicatorSignal.NEUTRAL, Severity.LOW, "현재 지표만으로 뚜렷한 위험 또는 긍정 신호는 없습니다."


def _unit(code: str) -> str | None:
    if code.endswith("_PCT"):
        return "PCT"
    if code.startswith("SMA_") or code == "AVG_DOLLAR_VOLUME_20D":
        return "USD"
    if code.endswith("_RATIO") or code in {"RSI_14", "BOLLINGER_POSITION"}:
        return "RATIO"
    return None
