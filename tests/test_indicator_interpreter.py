from __future__ import annotations

from stock_risk_mcp.indicator_interpreter import interpret_indicators
from stock_risk_mcp.indicators import IndicatorSignal
from stock_risk_mcp.models import Evidence, Severity, SourceType


def test_interpreter_applies_defined_rules_and_evidence() -> None:
    evidence = Evidence(source_name="price_history_file", source_type=SourceType.FILE)
    indicators = interpret_indicators(
        ticker="SAFE",
        raw_values={
            "RETURN_5D_PCT": 90,
            "AVG_DOLLAR_VOLUME_20D": 60_000_000,
            "VOLATILITY_20D_PCT": 9,
            "RSI_14": 75,
            "MAX_DRAWDOWN_60D_PCT": -35,
            "VOLUME_SPIKE_RATIO": 6,
            "BOLLINGER_POSITION": 1.1,
        },
        evidence=evidence,
    )
    by_code = {indicator.indicator_code: indicator for indicator in indicators}

    assert by_code["RETURN_5D_PCT"].signal == IndicatorSignal.NEGATIVE
    assert by_code["RETURN_5D_PCT"].severity == Severity.HIGH
    assert by_code["AVG_DOLLAR_VOLUME_20D"].signal == IndicatorSignal.POSITIVE
    assert by_code["VOLATILITY_20D_PCT"].severity == Severity.HIGH
    assert by_code["RSI_14"].signal == IndicatorSignal.NEGATIVE
    assert by_code["MAX_DRAWDOWN_60D_PCT"].severity == Severity.HIGH
    assert by_code["VOLUME_SPIKE_RATIO"].signal == IndicatorSignal.NEGATIVE
    assert by_code["BOLLINGER_POSITION"].signal == IndicatorSignal.NEGATIVE
    assert by_code["RETURN_5D_PCT"].evidence == evidence


def test_interpreter_marks_missing_values_unknown() -> None:
    indicator = interpret_indicators("SAFE", {"SMA_120": None})[0]

    assert indicator.signal == IndicatorSignal.UNKNOWN
    assert indicator.value is None
    assert indicator.severity == Severity.LOW
