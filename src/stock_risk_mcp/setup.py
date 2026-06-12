from __future__ import annotations

from enum import StrEnum

from pydantic import Field, field_validator

from stock_risk_mcp.models import StrictModel


class SetupDirection(StrEnum):
    LONG = "LONG"
    SHORT = "SHORT"
    NEUTRAL = "NEUTRAL"


class SetupGrade(StrEnum):
    A = "A"
    B = "B"
    C = "C"
    NO_TRADE = "NO_TRADE"


class TradeDecision(StrEnum):
    PROPOSE = "PROPOSE"
    REVIEW = "REVIEW"
    BLOCK = "BLOCK"
    NO_TRADE = "NO_TRADE"


class SetupSignal(StrictModel):
    ticker: str = Field(..., min_length=1)
    direction: SetupDirection
    grade: SetupGrade
    score: int
    reasons: list[str]
    warnings: list[str]
    indicator_codes_used: list[str]
    beginner_summary: str

    @field_validator("ticker")
    @classmethod
    def normalize_ticker(cls, value: str) -> str:
        return value.strip().upper()


class TradePlan(StrictModel):
    ticker: str = Field(..., min_length=1)
    direction: SetupDirection
    setup_grade: SetupGrade
    setup_score: int
    entry_price: float | None = None
    stop_price: float | None = None
    target_price: float | None = None
    risk_reward_ratio: float | None = None
    max_loss_amount: float | None = None
    max_loss_currency: str = "USD"
    position_size: float | None = None
    notional_value: float | None = None
    decision: TradeDecision
    reasons: list[str]
    warnings: list[str]
    beginner_summary: str

    @field_validator("ticker")
    @classmethod
    def normalize_ticker(cls, value: str) -> str:
        return value.strip().upper()


class TradeSizingPolicy(StrictModel):
    account_equity: float = Field(..., gt=0)
    cash_available: float = Field(..., ge=0)
    currency: str = "USD"
    max_single_trade_loss_pct: float = Field(0.25, ge=0)
    max_position_pct: float = Field(5.0, ge=0)
    setup_risk_multipliers: dict[SetupGrade, float] = Field(
        default_factory=lambda: {
            SetupGrade.A: 1.0,
            SetupGrade.B: 0.5,
            SetupGrade.C: 0.0,
            SetupGrade.NO_TRADE: 0.0,
        }
    )


class RiskRewardResult(StrictModel):
    entry_price: float = Field(..., gt=0)
    stop_price: float = Field(..., gt=0)
    target_price: float = Field(..., gt=0)
    risk_per_share: float = Field(..., gt=0)
    reward_per_share: float = Field(..., ge=0)
    risk_reward_ratio: float = Field(..., ge=0)


class TradeSizeResult(StrictModel):
    max_loss_amount: float = Field(..., ge=0)
    position_size: float = Field(..., ge=0)
    notional_value: float = Field(..., ge=0)
