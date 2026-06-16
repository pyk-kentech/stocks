from __future__ import annotations

import math
from datetime import datetime
from enum import StrEnum

from pydantic import Field, field_validator, model_validator

from stock_risk_mcp.models import StrictModel


def aware(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("timestamp must include timezone")
    return value


def reject_bool(value):
    if isinstance(value, bool):
        raise ValueError("numeric value must not be boolean")
    return value


PAPER_EVAL_METADATA = {
    "paper_only": True,
    "advisory_only": True,
    "orders_submitted": False,
    "order_intents_created": False,
    "order_drafts_created": False,
    "execution_approved": False,
    "gates_bypassed": False,
    "external_network_calls": False,
}


class PaperEvalSide(StrEnum):
    BUY = "BUY"
    SELL = "SELL"
    SHORT = "SHORT"


class PaperEvalExitPolicy(StrEnum):
    STOP_FIRST = "STOP_FIRST"


class PaperEvalInput(StrictModel):
    ticker: str = Field(..., min_length=1)
    source_type: str = Field(..., min_length=1)
    decision_time: datetime
    side: PaperEvalSide
    setup_grade: str = Field(..., min_length=1)
    entry_reference: float = Field(..., gt=0, allow_inf_nan=False)
    stop_reference: float | None = Field(default=None, gt=0, allow_inf_nan=False)
    target_reference: float | None = Field(default=None, gt=0, allow_inf_nan=False)
    suggested_quantity: int = Field(..., ge=0)
    plan_status: str = Field(..., min_length=1)
    technical_evidence_summary: str | None = None
    market_discovery_summary: str | None = None
    llm_signal_summary: str | None = None
    _decision_time = field_validator("decision_time")(aware)

    @field_validator("entry_reference", "stop_reference", "target_reference", mode="before")
    @classmethod
    def numeric_only(cls, value):
        if value is None:
            return value
        return reject_bool(value)

    @field_validator("ticker")
    @classmethod
    def normalize_ticker(cls, value: str) -> str:
        return value.strip().upper()


class PaperPriceBar(StrictModel):
    timestamp: datetime
    open: float = Field(..., gt=0, allow_inf_nan=False)
    high: float = Field(..., gt=0, allow_inf_nan=False)
    low: float = Field(..., gt=0, allow_inf_nan=False)
    close: float = Field(..., gt=0, allow_inf_nan=False)
    _timestamp = field_validator("timestamp")(aware)

    @field_validator("open", "high", "low", "close", mode="before")
    @classmethod
    def numeric_only(cls, value):
        return reject_bool(value)

    @model_validator(mode="after")
    def validate_ohlc(self):
        if self.low > min(self.open, self.high, self.close):
            raise ValueError("low must be <= open/high/close")
        if self.high < max(self.open, self.low, self.close):
            raise ValueError("high must be >= open/low/close")
        return self


class PaperPricePath(StrictModel):
    ticker: str = Field(..., min_length=1)
    bars: list[PaperPriceBar] = Field(..., min_length=1)

    @field_validator("ticker")
    @classmethod
    def normalize_ticker(cls, value: str) -> str:
        return value.strip().upper()

    @model_validator(mode="after")
    def validate_bars(self):
        timestamps = [bar.timestamp for bar in self.bars]
        if timestamps != sorted(timestamps):
            raise ValueError("bars must be ordered")
        if len(set(timestamps)) != len(timestamps):
            raise ValueError("duplicate bar timestamp")
        return self


class PaperEvalConfig(StrictModel):
    initial_cash: float = Field(..., gt=0, allow_inf_nan=False)
    allow_limit_entry_only: bool = True
    fee_per_trade: float = Field(default=0, ge=0, allow_inf_nan=False)
    slippage_per_share: float = Field(default=0, ge=0, allow_inf_nan=False)
    same_bar_exit_policy: PaperEvalExitPolicy
    max_open_positions: int = Field(..., ge=1)

    @field_validator("initial_cash", "fee_per_trade", "slippage_per_share", mode="before")
    @classmethod
    def numeric_only(cls, value):
        return reject_bool(value)


class PaperEvalFixture(StrictModel):
    schema_version: str
    run_id: str = Field(..., min_length=1)
    created_at: datetime
    config: PaperEvalConfig
    inputs: list[PaperEvalInput] = Field(..., min_length=1)
    price_paths: list[PaperPricePath] = Field(..., min_length=1)
    _created = field_validator("created_at")(aware)

    @field_validator("schema_version")
    @classmethod
    def exact_schema(cls, value: str) -> str:
        if value != "3.6-paper-eval-fixture":
            raise ValueError("schema_version must be exactly 3.6-paper-eval-fixture")
        return value

    @model_validator(mode="after")
    def validate_unique_tickers(self):
        if len({path.ticker for path in self.price_paths}) != len(self.price_paths):
            raise ValueError("duplicate price path ticker")
        return self


class PaperPosition(StrictModel):
    ticker: str
    entry_time: datetime
    entry_price: float
    stop_price: float
    target_price: float
    quantity: int
    entry_notional: float
    source_type: str
    _entry_time = field_validator("entry_time")(aware)


class PaperTrade(StrictModel):
    ticker: str
    source_type: str
    decision_time: datetime
    entry_reference: float
    planned_quantity: int
    simulated_entry_time: datetime | None = None
    simulated_entry_price: float | None = None
    simulated_exit_time: datetime | None = None
    simulated_exit_price: float | None = None
    exit_reason: str | None = None
    gross_pnl: float = 0
    net_pnl: float = 0
    holding_bars: int = 0
    holding_seconds: float = 0
    stop_hit: bool = False
    target_hit: bool = False
    blocked: bool = False
    missing_data: bool = False
    warnings: list[str] = Field(default_factory=list)
    block_reasons: list[str] = Field(default_factory=list)
    _decision_time = field_validator("decision_time")(aware)


class PaperPortfolioState(StrictModel):
    timestamp: datetime
    cash_available: float
    realized_pnl: float
    equity: float
    peak_equity: float
    drawdown_amount: float
    drawdown_pct: float
    _timestamp = field_validator("timestamp")(aware)


class PaperEvalMetrics(StrictModel):
    total_return_pct: float | None = None
    max_drawdown_pct: float | None = None
    win_rate: float | None = None
    average_win_amount: float | None = None
    average_loss_amount: float | None = None
    profit_factor: float | None = None
    expectancy_amount: float | None = None
    exposure_time_pct: float | None = None
    trade_count: int = 0
    stop_hit_count: int = 0
    target_hit_count: int = 0
    blocked_plan_count: int = 0
    missing_data_count: int = 0


class PaperEvalReport(StrictModel):
    schema_version: str = "3.6-paper-eval-report"
    fixture_checksum: str
    run_id: str
    created_at: datetime
    config: PaperEvalConfig
    inputs: list[PaperEvalInput]
    paper_trades: list[PaperTrade]
    equity_curve: list[PaperPortfolioState]
    metrics: PaperEvalMetrics
    blocked_reasons: list[str] = Field(default_factory=list)
    metadata_json: dict = Field(default_factory=lambda: dict(PAPER_EVAL_METADATA))
    _created = field_validator("created_at")(aware)

    @field_validator("schema_version")
    @classmethod
    def exact_report_schema(cls, value: str) -> str:
        if value != "3.6-paper-eval-report":
            raise ValueError("schema_version must be exactly 3.6-paper-eval-report")
        return value

    @model_validator(mode="after")
    def finite_curve(self):
        for point in self.equity_curve:
            if not math.isfinite(point.equity):
                raise ValueError("equity must be finite")
        return self
