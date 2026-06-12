from __future__ import annotations

from datetime import date, datetime
from enum import StrEnum
from pathlib import Path
from typing import Any

from pydantic import Field, field_validator

from stock_risk_mcp.adapters.file_price_history import FilePriceHistoryAdapter
from stock_risk_mcp.models import StrictModel


class CandidateSource(StrEnum):
    PRICE_HISTORY_DB = "PRICE_HISTORY_DB"
    PRICE_HISTORY_FILE = "PRICE_HISTORY_FILE"
    MANUAL_LIST = "MANUAL_LIST"
    REPLAY_SNAPSHOT = "REPLAY_SNAPSHOT"
    UNKNOWN = "UNKNOWN"


class ScanRunStatus(StrEnum):
    CREATED = "CREATED"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    NO_DATA = "NO_DATA"


class CandidateDecision(StrEnum):
    INCLUDE = "INCLUDE"
    WATCH = "WATCH"
    EXCLUDE = "EXCLUDE"


class ScanRun(StrictModel):
    scan_run_id: str
    as_of_date: date
    source: CandidateSource
    policy_id: str | None = None
    policy_version: str | None = None
    universe_size: int
    included_count: int
    watch_count: int
    excluded_count: int
    status: ScanRunStatus
    notes: list[str] = Field(default_factory=list)
    created_at: datetime


class CandidateScanPolicy(StrictModel):
    min_price: float = 1.0
    max_price: float | None = None
    min_avg_dollar_volume_20d: float = 10_000_000
    min_volume_spike_ratio: float = 1.5
    min_dollar_volume_spike_ratio: float = 1.5
    min_return_1d_pct: float | None = None
    min_return_5d_pct: float | None = None
    max_return_5d_pct: float = 80.0
    max_volatility_20d_pct: float = 12.0
    min_setup_score: int = 40
    include_review_setups: bool = True
    include_c_setups: bool = False
    exclude_nasdaq_noncompliant: bool = True
    exclude_low_liquidity: bool = True
    max_candidates: int = 100


class CandidateScanResult(StrictModel):
    scan_run_id: str
    ticker: str
    as_of_date: date
    decision: CandidateDecision
    score: int
    setup_grade: str | None = None
    setup_score: int | None = None
    trade_plan_decision: str | None = None
    price: float | None = None
    return_1d_pct: float | None = None
    return_5d_pct: float | None = None
    return_20d_pct: float | None = None
    avg_dollar_volume_20d: float | None = None
    volume_spike_ratio: float | None = None
    dollar_volume_spike_ratio: float | None = None
    volatility_20d_pct: float | None = None
    risk_reward_ratio: float | None = None
    sector: str | None = None
    theme: str | None = None
    reasons: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("ticker")
    @classmethod
    def normalize_ticker(cls, value: str) -> str:
        return value.strip().upper()


def load_db_universe(repository, as_of_date: date) -> list[str]:
    return repository.list_price_history_tickers(as_of_date)


def load_file_universe(path: str | Path, as_of_date: date) -> list[str]:
    return sorted({bar.ticker for bar in FilePriceHistoryAdapter(Path(path)).load_price_bars() if bar.date <= as_of_date})


def load_manual_universe(tickers: list[str]) -> list[str]:
    return list(dict.fromkeys(ticker.strip().upper() for ticker in tickers if ticker.strip()))
