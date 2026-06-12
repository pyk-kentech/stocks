from __future__ import annotations

from stock_risk_mcp.indicators import IndicatorSet
from stock_risk_mcp.setup import SetupDirection, SetupGrade, SetupSignal


class SetupGrader:
    def grade(self, indicator_set: IndicatorSet) -> SetupSignal:
        values = {indicator.indicator_code: indicator.value for indicator in indicator_set.indicators}
        score = 20
        reasons: list[str] = []
        warnings: list[str] = []
        used: list[str] = []

        def apply(code: str, points: int, message: str, warning: bool = False) -> None:
            nonlocal score
            score += points
            used.append(code)
            (warnings if warning else reasons).append(message)

        return_5d = _number(values.get("RETURN_5D_PCT"))
        if return_5d is not None:
            if 0 <= return_5d <= 40:
                apply("RETURN_5D_PCT", 10, "최근 5일 수익률이 LONG 후보 범위입니다.")
            elif return_5d <= 80:
                apply("RETURN_5D_PCT", -10, "최근 5일 가격이 과열될 수 있습니다.", True)
            else:
                apply("RETURN_5D_PCT", -30, "최근 5일 급등으로 추격매수 위험이 큽니다.", True)

        for code in ("DISTANCE_FROM_SMA_20_PCT", "DISTANCE_FROM_SMA_60_PCT"):
            value = _number(values.get(code))
            if value is not None and value > 0:
                apply(code, 10, f"가격이 {code.replace('DISTANCE_FROM_', '').replace('_PCT', '')} 위에 있습니다.")

        rsi = _number(values.get("RSI_14"))
        if rsi is not None:
            if 40 <= rsi <= 65:
                apply("RSI_14", 10, "RSI가 LONG 후보 중립 구간입니다.")
            elif rsi > 70:
                apply("RSI_14", -10, "RSI가 과매수 구간입니다.", True)

        volume_spike = _number(values.get("VOLUME_SPIKE_RATIO"))
        if volume_spike is not None:
            if 2 <= volume_spike <= 5:
                apply("VOLUME_SPIKE_RATIO", 15, "거래량 증가로 시장 관심이 확인됩니다.")
            elif volume_spike > 5 and return_5d is not None and return_5d > 40:
                apply("VOLUME_SPIKE_RATIO", -15, "급등과 거래량 급증이 함께 나타났습니다.", True)

        dollar_volume = _number(values.get("AVG_DOLLAR_VOLUME_20D"))
        if dollar_volume is not None:
            if dollar_volume >= 50_000_000:
                apply("AVG_DOLLAR_VOLUME_20D", 15, "평균 거래대금이 충분합니다.")
            elif dollar_volume < 10_000_000:
                apply("AVG_DOLLAR_VOLUME_20D", -30, "평균 거래대금이 부족합니다.", True)

        volatility = _number(values.get("VOLATILITY_20D_PCT"))
        if volatility is not None and volatility > 8:
            apply("VOLATILITY_20D_PCT", -15, "최근 변동성이 높습니다.", True)

        drawdown = _number(values.get("MAX_DRAWDOWN_60D_PCT"))
        if drawdown is not None and drawdown < -30:
            apply("MAX_DRAWDOWN_60D_PCT", -15, "최근 최대 낙폭이 큽니다.", True)

        bollinger = _number(values.get("BOLLINGER_POSITION"))
        if bollinger is not None:
            if 0.2 <= bollinger <= 0.8:
                apply("BOLLINGER_POSITION", 5, "볼린저 밴드 안쪽의 안정 구간입니다.")
            elif bollinger > 1:
                apply("BOLLINGER_POSITION", -10, "볼린저 밴드 상단을 넘어 과열 가능성이 있습니다.", True)

        score = max(0, min(100, score))
        grade = _grade(score)
        direction = SetupDirection.LONG if grade != SetupGrade.NO_TRADE else SetupDirection.NEUTRAL
        return SetupSignal(
            ticker=indicator_set.ticker,
            direction=direction,
            grade=grade,
            score=score,
            reasons=reasons,
            warnings=warnings,
            indicator_codes_used=list(dict.fromkeys(used)),
            beginner_summary=_summary(grade),
        )


def _grade(score: int) -> SetupGrade:
    if score >= 80:
        return SetupGrade.A
    if score >= 60:
        return SetupGrade.B
    if score >= 40:
        return SetupGrade.C
    return SetupGrade.NO_TRADE


def _summary(grade: SetupGrade) -> str:
    if grade == SetupGrade.A:
        return "A 셋업 후보지만 실제 주문 전 뉴스와 기존 Risk Engine 검사가 필요합니다."
    if grade == SetupGrade.B:
        return "B 셋업 후보로 추가 검토가 필요합니다."
    return "현재 기준으로는 매매하지 않는 편이 안전합니다."


def _number(value) -> float | None:
    return float(value) if isinstance(value, (int, float)) else None
