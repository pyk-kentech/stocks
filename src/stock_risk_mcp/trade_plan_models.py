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


def normalize_strings(values: list[str]) -> list[str]:
    cleaned = [value.strip() for value in values]
    if any(not value for value in cleaned):
        raise ValueError("list values must not be blank")
    return sorted(set(cleaned))


TRADE_PLAN_METADATA = {
    "advisory_only": True,
    "orders_created": False,
    "order_intents_created": False,
    "strategy_decisions_created": False,
    "gates_bypassed": False,
    "external_network_calls": False,
}


class TradePlanSide(StrEnum):
    BUY = "BUY"
    SELL = "SELL"
    SHORT = "SHORT"


class TradePlanStatus(StrEnum):
    TRADE_PLAN_READY = "TRADE_PLAN_READY"
    WATCH_ONLY = "WATCH_ONLY"
    BLOCKED_INVALID_STOP = "BLOCKED_INVALID_STOP"
    BLOCKED_RISK_REWARD_TOO_LOW = "BLOCKED_RISK_REWARD_TOO_LOW"
    BLOCKED_BASKET_RISK_CAP = "BLOCKED_BASKET_RISK_CAP"
    BLOCKED_INSUFFICIENT_EVIDENCE = "BLOCKED_INSUFFICIENT_EVIDENCE"
    BLOCKED_UNSUPPORTED_SIDE = "BLOCKED_UNSUPPORTED_SIDE"
    NO_TRADE = "NO_TRADE"


class TradePlanConfig(StrictModel):
    portfolio_equity: float = Field(..., gt=0, allow_inf_nan=False)
    risk_pct_per_trade: float = Field(..., gt=0, le=1, allow_inf_nan=False)
    max_basket_risk_pct: float = Field(..., gt=0, le=1, allow_inf_nan=False)
    fixed_min_risk_reward: float = Field(..., gt=0, allow_inf_nan=False)

    @field_validator(
        "portfolio_equity",
        "risk_pct_per_trade",
        "max_basket_risk_pct",
        "fixed_min_risk_reward",
        mode="before",
    )
    @classmethod
    def numeric_only(cls, value):
        return reject_bool(value)


class TradePlanInput(StrictModel):
    ticker: str = Field(..., min_length=1)
    side: TradePlanSide
    setup_type: str = Field(..., min_length=1)
    setup_grade: str = Field(..., min_length=1)
    entry_reference: float = Field(..., gt=0, allow_inf_nan=False)
    stop_reference: float | None = Field(default=None, gt=0, allow_inf_nan=False)
    target_reference: float | None = Field(default=None, gt=0, allow_inf_nan=False)
    atr_value: float | None = Field(default=None, gt=0, allow_inf_nan=False)
    stop_distance_evidence: float | None = Field(default=None, gt=0, allow_inf_nan=False)
    support_level: float | None = Field(default=None, gt=0, allow_inf_nan=False)
    resistance_level: float | None = Field(default=None, gt=0, allow_inf_nan=False)
    technical_evidence_summary: str | None = None
    llm_signal_summary: str | None = None
    warnings: list[str] = Field(default_factory=list)

    @field_validator(
        "entry_reference",
        "stop_reference",
        "target_reference",
        "atr_value",
        "stop_distance_evidence",
        "support_level",
        "resistance_level",
        mode="before",
    )
    @classmethod
    def numeric_only(cls, value):
        if value is None:
            return value
        return reject_bool(value)

    @field_validator("ticker")
    @classmethod
    def normalize_ticker(cls, value: str) -> str:
        return value.strip().upper()

    @field_validator("setup_type")
    @classmethod
    def normalize_setup_type(cls, value: str) -> str:
        return value.strip()

    @field_validator("setup_grade")
    @classmethod
    def normalize_setup_grade(cls, value: str) -> str:
        normalized = value.strip().upper()
        if normalized not in {"A", "B", "C", "D", "F"}:
            raise ValueError("setup_grade must be one of A, B, C, D, F")
        return normalized

    @field_validator("warnings")
    @classmethod
    def normalize_warning_list(cls, values: list[str]) -> list[str]:
        return normalize_strings(values)


class TradePlanFixture(StrictModel):
    schema_version: str
    run_id: str = Field(..., min_length=1)
    created_at: datetime
    config: TradePlanConfig
    candidates: list[TradePlanInput] = Field(..., min_length=1)
    _created = field_validator("created_at")(aware)

    @field_validator("schema_version")
    @classmethod
    def exact_schema(cls, value: str) -> str:
        if value != "3.5-trade-plan-fixture":
            raise ValueError("schema_version must be exactly 3.5-trade-plan-fixture")
        return value

    @model_validator(mode="after")
    def validate_unique_candidates(self):
        keys = set()
        for candidate in self.candidates:
            key = (candidate.ticker, candidate.side, candidate.setup_type)
            if key in keys:
                raise ValueError("duplicate trade plan candidate key")
            keys.add(key)
        return self


class TradePlan(StrictModel):
    ticker: str
    side: TradePlanSide
    setup_type: str
    setup_grade: str
    entry_reference: float
    stop_reference: float | None = None
    target_reference: float | None = None
    stop_distance: float | None = None
    reward_distance: float | None = None
    risk_reward_ratio: float | None = None
    max_loss_amount: float = 0
    suggested_quantity: int = 0
    basket_risk_amount: float = 0
    plan_status: TradePlanStatus
    block_reasons: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    technical_evidence_summary: str | None = None
    llm_signal_summary: str | None = None


class BasketRiskState(StrictModel):
    running_basket_risk_amount: float = Field(default=0, ge=0, allow_inf_nan=False)
    max_basket_risk_amount: float = Field(..., ge=0, allow_inf_nan=False)


class BasketRiskDecision(StrictModel):
    accepted: bool
    block_reason: str | None = None
    updated_state: BasketRiskState


class TradePlanReport(StrictModel):
    schema_version: str = "3.5-trade-plan-report"
    fixture_checksum: str
    run_id: str
    created_at: datetime
    config: TradePlanConfig
    plans: list[TradePlan]
    summary_counts: dict[str, int]
    total_ready_basket_risk_amount: float
    max_basket_risk_amount: float
    metadata_json: dict = Field(default_factory=lambda: dict(TRADE_PLAN_METADATA))
    _created = field_validator("created_at")(aware)

    @field_validator("schema_version")
    @classmethod
    def exact_report_schema(cls, value: str) -> str:
        if value != "3.5-trade-plan-report":
            raise ValueError("schema_version must be exactly 3.5-trade-plan-report")
        return value

    @model_validator(mode="after")
    def finite_totals(self):
        if not math.isfinite(self.total_ready_basket_risk_amount):
            raise ValueError("total_ready_basket_risk_amount must be finite")
        if not math.isfinite(self.max_basket_risk_amount):
            raise ValueError("max_basket_risk_amount must be finite")
        return self
