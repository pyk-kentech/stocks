from __future__ import annotations

from stock_risk_mcp.indicators import IndicatorSet, IndicatorSignal, IndicatorValue
from stock_risk_mcp.models import Severity
from stock_risk_mcp.setup import SetupDirection, SetupGrade
from stock_risk_mcp.setup_grading import SetupGrader


def test_setup_grader_scores_strong_liquid_non_overheated_long_as_a() -> None:
    indicator_set = _indicator_set(
        RETURN_5D_PCT=10,
        DISTANCE_FROM_SMA_20_PCT=5,
        DISTANCE_FROM_SMA_60_PCT=10,
        RSI_14=55,
        VOLUME_SPIKE_RATIO=3,
        AVG_DOLLAR_VOLUME_20D=60_000_000,
        VOLATILITY_20D_PCT=3,
        MAX_DRAWDOWN_60D_PCT=-10,
        BOLLINGER_POSITION=0.5,
    )

    setup = SetupGrader().grade(indicator_set)

    assert setup.direction == SetupDirection.LONG
    assert setup.grade == SetupGrade.A
    assert setup.score >= 80
    assert "AVG_DOLLAR_VOLUME_20D" in setup.indicator_codes_used


def test_setup_grader_reduces_score_for_overheating_and_low_liquidity() -> None:
    overheated = SetupGrader().grade(
        _indicator_set(RETURN_5D_PCT=90, VOLUME_SPIKE_RATIO=6, AVG_DOLLAR_VOLUME_20D=60_000_000)
    )
    illiquid = SetupGrader().grade(_indicator_set(RETURN_5D_PCT=10, AVG_DOLLAR_VOLUME_20D=1_000_000))

    assert overheated.score < 40
    assert overheated.grade == SetupGrade.NO_TRADE
    assert illiquid.score < 40
    assert illiquid.grade == SetupGrade.NO_TRADE


def _indicator_set(**values: float) -> IndicatorSet:
    return IndicatorSet(
        ticker="SAFE",
        indicators=[
            IndicatorValue(
                ticker="SAFE",
                indicator_code=code,
                category="TEST",
                value=value,
                signal=IndicatorSignal.NEUTRAL,
                severity=Severity.LOW,
                interpretation=code,
                beginner_explanation=code,
            )
            for code, value in values.items()
        ],
    )
