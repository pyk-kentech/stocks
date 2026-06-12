from __future__ import annotations

from enum import StrEnum
from datetime import datetime, time

from pydantic import Field, field_validator

from stock_risk_mcp.models import Evidence, PriceBar, Severity, SourceType, StrictModel


class IndicatorSignal(StrEnum):
    POSITIVE = "POSITIVE"
    NEGATIVE = "NEGATIVE"
    NEUTRAL = "NEUTRAL"
    UNKNOWN = "UNKNOWN"


class IndicatorValue(StrictModel):
    ticker: str = Field(..., min_length=1)
    indicator_code: str = Field(..., min_length=1)
    category: str = Field(..., min_length=1)
    value: float | str | bool | None
    unit: str | None = None
    signal: IndicatorSignal
    severity: Severity
    interpretation: str
    beginner_explanation: str
    evidence: Evidence | None = None

    @field_validator("ticker", "indicator_code")
    @classmethod
    def normalize_upper(cls, value: str) -> str:
        return value.strip().upper()


class IndicatorSet(StrictModel):
    ticker: str = Field(..., min_length=1)
    indicators: list[IndicatorValue]

    @field_validator("ticker")
    @classmethod
    def normalize_ticker(cls, value: str) -> str:
        return value.strip().upper()


class IndicatorScore(StrictModel):
    ticker: str = Field(..., min_length=1)
    positive_score: int = Field(..., ge=0)
    negative_score: int = Field(..., ge=0)
    risk_penalty: int = Field(..., ge=0)
    summary: str
    contributing_indicators: list[str]

    @field_validator("ticker")
    @classmethod
    def normalize_ticker(cls, value: str) -> str:
        return value.strip().upper()


def analyze_price_bars(
    ticker: str,
    bars: list[PriceBar],
    source_name: str,
    source_type: SourceType,
) -> tuple[IndicatorSet, IndicatorScore]:
    from stock_risk_mcp.indicator_calculators import calculate_indicators
    from stock_risk_mcp.indicator_interpreter import interpret_indicators
    from stock_risk_mcp.indicator_scoring import score_indicators
    from stock_risk_mcp.price_history import sort_price_bars

    symbol = ticker.strip().upper()
    ticker_bars = [bar for bar in sort_price_bars(bars) if bar.ticker == symbol]
    if not ticker_bars:
        raise ValueError(f"No price history found for ticker {symbol}")
    evidence = Evidence(
        source_name=source_name,
        source_type=source_type,
        observed_at=datetime.combine(ticker_bars[-1].date, time.min),
        raw_reference=f"{symbol}:{ticker_bars[-1].date.isoformat()}",
        confidence=1.0,
    )
    indicators = interpret_indicators(symbol, calculate_indicators(ticker_bars), evidence)
    return IndicatorSet(ticker=symbol, indicators=indicators), score_indicators(symbol, indicators)
