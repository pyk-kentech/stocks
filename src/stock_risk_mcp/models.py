from __future__ import annotations

from datetime import date, datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, field_validator


class TradeSide(StrEnum):
    BUY = "BUY"
    SELL = "SELL"


class DilutionRisk(StrEnum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    UNKNOWN = "UNKNOWN"


class SignalLevel(StrEnum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


class PolicyMode(StrEnum):
    READ_ONLY = "READ_ONLY"
    PROPOSE_ONLY = "PROPOSE_ONLY"
    AUTO_SMALL = "AUTO_SMALL"


class Decision(StrEnum):
    ALLOW = "ALLOW"
    REVIEW = "REVIEW"
    BLOCK = "BLOCK"


class BacktestOutcome(StrEnum):
    WIN = "WIN"
    LOSS = "LOSS"
    FLAT = "FLAT"
    NO_DATA = "NO_DATA"


class ReasonType(StrEnum):
    HARD_BLOCK = "HARD_BLOCK"
    WARNING = "WARNING"
    POSITIVE = "POSITIVE"
    NEGATIVE = "NEGATIVE"


class Severity(StrEnum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class SourceType(StrEnum):
    MOCK = "MOCK"
    FILE = "FILE"
    API = "API"
    SCRAPE = "SCRAPE"
    USER_INPUT = "USER_INPUT"
    LLM = "LLM"
    SYSTEM = "SYSTEM"


class IngestionStatus(StrEnum):
    STARTED = "STARTED"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", use_enum_values=False)


class TradeProposal(StrictModel):
    ticker: str = Field(..., min_length=1)
    side: TradeSide
    reason: str = Field(..., min_length=1)
    llm_confidence: float = Field(..., ge=0, le=1)
    intended_holding_days: int = Field(1, ge=1)

    @field_validator("ticker")
    @classmethod
    def normalize_ticker(cls, value: str) -> str:
        return value.strip().upper()


class MarketSnapshot(StrictModel):
    ticker: str = Field(..., min_length=1)
    price: float = Field(..., gt=0)
    market_cap_usd: float | None = Field(default=None, gt=0)
    avg_dollar_volume_20d: float | None = Field(default=None, gt=0)
    return_5d_pct: float | None = None
    return_20d_pct: float | None = None
    volatility_20d_pct: float | None = Field(default=None, ge=0)
    sector: str | None = None

    @field_validator("ticker")
    @classmethod
    def normalize_ticker(cls, value: str) -> str:
        return value.strip().upper()


class CompanyRisk(StrictModel):
    ticker: str = Field(..., min_length=1)
    nasdaq_noncompliant: bool = False
    nasdaq_noncompliance_evidence: Evidence | None = None
    dilution_risk: DilutionRisk = DilutionRisk.UNKNOWN
    recent_reverse_split_days: int | None = Field(default=None, ge=0)
    recent_offering_days: int | None = Field(default=None, ge=0)
    has_warrants: bool = False
    has_convertibles: bool = False
    has_going_concern_warning: bool = False

    @field_validator("ticker")
    @classmethod
    def normalize_ticker(cls, value: str) -> str:
        return value.strip().upper()


class PortfolioState(StrictModel):
    total_equity_usd: float = Field(..., gt=0)
    cash_usd: float = Field(..., ge=0)
    current_position_pct: float = Field(..., ge=0)
    sector_exposure_pct: float = Field(..., ge=0)
    daily_pnl_pct: float
    open_orders_count: int = Field(..., ge=0)


class TossSignal(StrictModel):
    tracked_investors_holding: int = Field(..., ge=0)
    new_buy_count_7d: int = Field(..., ge=0)
    consensus_level: SignalLevel
    signal_quality: SignalLevel
    historical_follow_return_30d_pct: float | None = None


class NewsEvent(StrictModel):
    ticker: str = Field(..., min_length=1)
    headline: str = Field(..., min_length=1)
    source: str | None = None
    published_at: str | None = None
    url: str | None = None
    sentiment: str | None = None
    summary: str | None = None

    @field_validator("ticker")
    @classmethod
    def normalize_ticker(cls, value: str) -> str:
        return value.strip().upper()


class PriceBar(StrictModel):
    ticker: str = Field(..., min_length=1)
    date: date
    open: float | None = Field(default=None, gt=0)
    high: float | None = Field(default=None, gt=0)
    low: float | None = Field(default=None, gt=0)
    close: float = Field(..., gt=0)
    volume: float | None = Field(default=None, ge=0)

    @field_validator("ticker")
    @classmethod
    def normalize_ticker(cls, value: str) -> str:
        return value.strip().upper()


class BacktestResult(StrictModel):
    risk_evaluation_id: int = Field(..., ge=1)
    ticker: str = Field(..., min_length=1)
    decision: Decision
    score: int = Field(..., ge=0, le=100)
    horizon_days: int = Field(..., ge=1)
    entry_price: float = Field(..., ge=0)
    exit_price: float | None = Field(default=None, gt=0)
    return_pct: float | None = None
    max_drawdown_pct: float | None = None
    max_gain_pct: float | None = None
    outcome: BacktestOutcome

    @field_validator("ticker")
    @classmethod
    def normalize_backtest_ticker(cls, value: str) -> str:
        return value.strip().upper()


class Evidence(StrictModel):
    source_name: str = Field(..., min_length=1)
    source_type: SourceType
    source_url: str | None = None
    observed_at: datetime | None = None
    raw_reference: str | None = None
    confidence: float | None = Field(default=None, ge=0, le=1)


class EvaluationReason(StrictModel):
    risk_evaluation_id: int | None = Field(default=None, ge=1)
    ticker: str = Field(..., min_length=1)
    reason_type: ReasonType
    reason_code: str = Field(..., min_length=1)
    message: str = Field(..., min_length=1)
    severity: Severity
    evidence: Evidence | None = None

    @field_validator("ticker")
    @classmethod
    def normalize_reason_ticker(cls, value: str) -> str:
        return value.strip().upper()

    @field_validator("reason_code")
    @classmethod
    def normalize_reason_code(cls, value: str) -> str:
        return value.strip().upper()


class DataSource(StrictModel):
    name: str = Field(..., min_length=1)
    source_type: SourceType
    description: str | None = None
    base_url: str | None = None
    enabled: bool = True


class IngestionRun(StrictModel):
    source_name: str = Field(..., min_length=1)
    source_type: SourceType
    started_at: datetime
    finished_at: datetime | None = None
    status: IngestionStatus
    records_seen: int = Field(0, ge=0)
    records_saved: int = Field(0, ge=0)
    error_message: str | None = None
    metadata_json: dict | None = None


class RiskPolicy(StrictModel):
    mode: PolicyMode = PolicyMode.PROPOSE_ONLY
    min_market_cap_usd: float = Field(..., ge=0)
    min_avg_dollar_volume_usd: float = Field(..., ge=0)
    max_5d_return_pct: float
    max_single_position_pct: float = Field(..., ge=0, le=100)
    max_sector_exposure_pct: float = Field(..., ge=0, le=100)
    max_daily_loss_pct: float
    max_order_pct: float = Field(..., ge=0, le=100)
    min_cash_pct: float = Field(..., ge=0, le=100)
    block_unknown_dilution: bool
    block_missing_core_data: bool
    block_nasdaq_noncompliant: bool
    block_dilution_high: bool
    block_reverse_split_within_days: int = Field(..., ge=0)
    block_offering_within_days: int = Field(..., ge=0)
    block_warrants: bool
    block_convertibles: bool
    allow_market_order: bool
    allow_margin: bool
    allow_options: bool
    require_human_approval: bool


class RiskResult(StrictModel):
    ticker: str
    decision: Decision
    score: int = Field(..., ge=0, le=100)
    max_order_usd: float = Field(..., ge=0)
    max_position_pct: float = Field(..., ge=0, le=100)
    hard_blocks: list[str]
    warnings: list[str]
    positive_factors: list[str]
    negative_factors: list[str]
    beginner_summary: str
    human_approval_required: bool
    reason_details: list[EvaluationReason] = Field(default_factory=list)
