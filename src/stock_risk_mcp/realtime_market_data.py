from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from uuid import uuid4

from pydantic import Field, field_validator

from stock_risk_mcp.models import StrictModel


class MarketRegion(StrEnum):
    US = "US"
    KR = "KR"
    UNKNOWN = "UNKNOWN"


class MarketDataEventType(StrEnum):
    TRADE = "TRADE"
    QUOTE = "QUOTE"
    BAR_1M = "BAR_1M"
    BAR_5M = "BAR_5M"
    SNAPSHOT = "SNAPSHOT"
    MARKET_STATUS = "MARKET_STATUS"
    UNKNOWN = "UNKNOWN"


class WatchlistStatus(StrEnum):
    CANDIDATE = "CANDIDATE"
    HOT = "HOT"
    COOLING = "COOLING"
    REMOVED = "REMOVED"
    BLOCKED = "BLOCKED"


class RealtimeMonitorRunStatus(StrEnum):
    CREATED = "CREATED"
    COMPLETED = "COMPLETED"
    PARTIAL = "PARTIAL"
    FAILED = "FAILED"
    DISABLED = "DISABLED"


class MarketDataEvent(StrictModel):
    symbol: str = Field(..., min_length=1)
    region: MarketRegion
    event_type: MarketDataEventType
    event_time: datetime
    price: float | None = None
    open: float | None = None
    high: float | None = None
    low: float | None = None
    close: float | None = None
    volume: float | None = None
    dollar_volume: float | None = None
    bid: float | None = None
    ask: float | None = None
    source_name: str = Field(..., min_length=1)
    raw_payload_json: str | None = None

    @field_validator("symbol")
    @classmethod
    def normalize_symbol(cls, value: str) -> str:
        return value.strip().upper()


class RollingMarketMetrics(StrictModel):
    symbol: str = Field(..., min_length=1)
    region: MarketRegion
    as_of: datetime
    last_price: float | None = None
    return_1m_pct: float | None = None
    return_5m_pct: float | None = None
    return_15m_pct: float | None = None
    volume_1m: float | None = None
    volume_5m: float | None = None
    volume_15m: float | None = None
    dollar_volume_5m: float | None = None
    relative_volume: float | None = None
    high_15m: float | None = None
    low_15m: float | None = None
    breakout_15m: bool = False
    halt_or_bad_tick_warning: bool = False
    source_name: str = ""
    warnings: list[str] = Field(default_factory=list)

    @field_validator("symbol")
    @classmethod
    def normalize_symbol(cls, value: str) -> str:
        return value.strip().upper()


class WatchlistEntry(StrictModel):
    symbol: str = Field(..., min_length=1)
    region: MarketRegion
    status: WatchlistStatus
    first_seen_at: datetime
    last_seen_at: datetime
    promotion_reason: str
    score: float
    metrics_json: str
    warnings: list[str] = Field(default_factory=list)

    @field_validator("symbol")
    @classmethod
    def normalize_symbol(cls, value: str) -> str:
        return value.strip().upper()


class IntradayCandidateSignal(StrictModel):
    symbol: str
    region: MarketRegion
    status: WatchlistStatus
    score: float
    reasons: list[str] = Field(default_factory=list)
    metrics: dict = Field(default_factory=dict)
    warnings: list[str] = Field(default_factory=list)
    generated_at: datetime


class RealtimeMonitorRun(StrictModel):
    realtime_monitor_run_id: str = Field(default_factory=lambda: f"realtime_{uuid4().hex}")
    as_of: datetime
    status: RealtimeMonitorRunStatus
    provider_name: str
    universe_count: int = Field(..., ge=0)
    processed_event_count: int = Field(..., ge=0)
    candidate_count: int = Field(..., ge=0)
    hot_watchlist_count: int = Field(..., ge=0)
    warnings: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.now)
    completed_at: datetime | None = None


class RealtimeMonitorResult(StrictModel):
    run: RealtimeMonitorRun
    watchlist_entries: list[WatchlistEntry] = Field(default_factory=list)
    signals: list[IntradayCandidateSignal] = Field(default_factory=list)
    output_path: str | None = None
