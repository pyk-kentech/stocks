from __future__ import annotations

from datetime import date, datetime
from enum import StrEnum
from uuid import uuid4

from pydantic import Field, field_validator

from stock_risk_mcp.models import StrictModel
from stock_risk_mcp.setup import SetupGrade, TradeDecision, TradePlan


class BasketMode(StrEnum):
    PAPER_TRADING = "PAPER_TRADING"
    PROPOSE_ONLY = "PROPOSE_ONLY"


class BasketCandidate(StrictModel):
    ticker: str = Field(..., min_length=1)
    trade_plan_id: int | None = Field(default=None, ge=1)
    setup_grade: SetupGrade
    setup_score: int
    decision: TradeDecision
    entry_price: float | None = None
    stop_price: float | None = None
    target_price: float | None = None
    risk_reward_ratio: float | None = None
    max_loss_amount: float | None = None
    position_size: float | None = None
    notional_value: float | None = None
    sector: str | None = None
    theme: str | None = None
    score: int
    reasons: list[str]
    warnings: list[str]

    @field_validator("ticker")
    @classmethod
    def normalize_ticker(cls, value: str) -> str:
        return value.strip().upper()


class BasketPolicy(StrictModel):
    basket_name: str = "momentum_event_basket"
    account_equity: float = Field(..., gt=0)
    cash_available: float = Field(..., ge=0)
    currency: str = "USD"
    max_basket_loss_pct: float = Field(1.0, ge=0)
    max_basket_notional_pct: float = Field(25.0, ge=0)
    max_single_candidate_loss_pct: float = Field(0.25, ge=0)
    max_single_position_pct: float = Field(5.0, ge=0)
    max_candidates: int = Field(10, ge=1)
    min_candidates: int = Field(3, ge=1)
    max_same_sector_count: int = Field(3, ge=1)
    max_same_theme_count: int = Field(3, ge=1)
    allow_review_candidates: bool = True
    allow_c_setup: bool = False
    setup_risk_units: dict[SetupGrade, float] = Field(
        default_factory=lambda: {
            SetupGrade.A: 1.0,
            SetupGrade.B: 0.5,
            SetupGrade.C: 0.0,
            SetupGrade.NO_TRADE: 0.0,
        }
    )


class BasketAllocation(StrictModel):
    ticker: str
    setup_grade: SetupGrade
    allocated_loss_amount: float
    allocated_notional_value: float
    position_size: float
    entry_price: float
    stop_price: float
    target_price: float | None = None
    risk_reward_ratio: float | None = None
    allocation_reason: str
    account_currency: str | None = None
    trading_currency: str | None = None
    fx_rate: float | None = None
    allocated_loss_account: float | None = None
    allocated_loss_trading: float | None = None
    notional_account: float | None = None
    notional_trading: float | None = None
    fx_warnings_json: list[str] = Field(default_factory=list)


class BasketRiskSummary(StrictModel):
    total_allocated_loss: float
    max_allowed_loss: float
    total_notional_value: float
    max_allowed_notional: float
    candidate_count: int
    sector_counts: dict[str, int]
    theme_counts: dict[str, int]
    blocked_reasons: list[str]
    warnings: list[str]
    risk_ok: bool
    account_currency: str | None = None
    trading_currency: str | None = None
    fx_rate: float | None = None
    fx_date: date | None = None
    total_notional_account: float | None = None
    total_notional_trading: float | None = None
    total_max_loss_account: float | None = None
    total_max_loss_trading: float | None = None
    fx_warnings_json: list[str] = Field(default_factory=list)


class BasketPlan(StrictModel):
    basket_id: str
    basket_name: str
    mode: BasketMode
    policy: BasketPolicy
    candidates: list[BasketCandidate]
    allocations: list[BasketAllocation]
    blocked: list[BasketCandidate]
    risk_summary: BasketRiskSummary
    decision: TradeDecision
    beginner_summary: str
    created_at: datetime
    policy_id: str | None = None
    policy_version: str | None = None
    basket_scoring_mode: str = "FIXED_RULES"
    account_currency: str | None = None
    trading_currency: str | None = None
    fx_rate: float | None = None
    fx_date: date | None = None
    total_notional_account: float | None = None
    total_notional_trading: float | None = None
    total_max_loss_account: float | None = None
    total_max_loss_trading: float | None = None
    fx_warnings_json: list[str] = Field(default_factory=list)


def candidate_from_trade_plan(plan: TradePlan, trade_plan_id: int | None = None) -> BasketCandidate:
    return BasketCandidate(
        ticker=plan.ticker,
        trade_plan_id=trade_plan_id,
        setup_grade=plan.setup_grade,
        setup_score=plan.setup_score,
        decision=plan.decision,
        entry_price=plan.entry_price,
        stop_price=plan.stop_price,
        target_price=plan.target_price,
        risk_reward_ratio=plan.risk_reward_ratio,
        max_loss_amount=plan.max_loss_amount,
        position_size=plan.position_size,
        notional_value=plan.notional_value,
        score=0,
        reasons=plan.reasons,
        warnings=plan.warnings,
    )


def new_basket_id() -> str:
    return uuid4().hex
