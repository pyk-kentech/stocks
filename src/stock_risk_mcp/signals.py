from __future__ import annotations

from datetime import date, datetime
from enum import StrEnum
from typing import Any

from pydantic import Field, field_validator

from stock_risk_mcp.models import StrictModel


class SignalType(StrEnum):
    NEWS = "NEWS"
    DILUTION = "DILUTION"
    TOSS_PORTFOLIO = "TOSS_PORTFOLIO"
    FOREIGN_INSTITUTION_FLOW = "FOREIGN_INSTITUTION_FLOW"
    COMPLIANCE = "COMPLIANCE"
    UNKNOWN = "UNKNOWN"


class SignalDirection(StrEnum):
    POSITIVE = "POSITIVE"
    NEGATIVE = "NEGATIVE"
    NEUTRAL = "NEUTRAL"
    UNKNOWN = "UNKNOWN"


class SignalSeverity(StrEnum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class TickerSignal(StrictModel):
    ticker: str
    signal_type: SignalType
    as_of_date: date
    observed_at: date | datetime
    direction: SignalDirection
    severity: SignalSeverity
    score_delta: int
    source_name: str
    title: str | None = None
    summary: str | None = None
    raw_event_type: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    reasons: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)

    @field_validator("ticker")
    @classmethod
    def normalize_ticker(cls, value: str) -> str:
        return value.strip().upper()


class SignalEnrichmentResult(StrictModel):
    ticker: str
    as_of_date: date
    signals: list[TickerSignal] = Field(default_factory=list)
    total_score_delta: int = 0
    has_critical_negative: bool = False
    has_high_negative: bool = False
    summary: str
    warnings: list[str] = Field(default_factory=list)

    @field_validator("ticker")
    @classmethod
    def normalize_ticker(cls, value: str) -> str:
        return value.strip().upper()


def parse_observed_at(value: Any) -> date | datetime:
    if isinstance(value, (date, datetime)):
        return value
    text = str(value).strip()
    try:
        return datetime.fromisoformat(text)
    except ValueError:
        return date.fromisoformat(text)


def observed_date(value: date | datetime) -> date:
    return value.date() if isinstance(value, datetime) else value


def signal_dedupe_key(signal: TickerSignal) -> tuple[str, str, str, str, str | None, str | None]:
    return (
        signal.ticker,
        signal.signal_type.value,
        signal.observed_at.isoformat(),
        signal.source_name,
        signal.raw_event_type,
        signal.title,
    )
