from __future__ import annotations

from datetime import date, datetime
from enum import StrEnum

from pydantic import Field, field_validator, model_validator

from stock_risk_mcp.models import StrictModel
from stock_risk_mcp.strategy_track_models import MarketProfile, StrategyTrack, StrategyTrackRequest


def aware(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("timestamp must include timezone")
    return value


MARKET_PROFIT_METADATA = {
    "market_profit_fixture_run": True,
    "strategy_track_required": True,
    "market_profile_resolved": True,
    "broker_api_called": False,
    "credentials_accessed": False,
    "external_network_calls": False,
    "orders_created": False,
    "live_or_prod_used": False,
}


class FeeTaxProfileStatus(StrEnum):
    ACTIVE = "ACTIVE"
    PLACEHOLDER = "PLACEHOLDER"
    NEEDS_EVIDENCE = "NEEDS_EVIDENCE"
    DISABLED = "DISABLED"


class TaxEstimateMode(StrEnum):
    EXCLUDED = "EXCLUDED"
    ESTIMATED_PER_TRADE = "ESTIMATED_PER_TRADE"
    ESTIMATED_ANNUALIZED = "ESTIMATED_ANNUALIZED"
    REPORT_ONLY = "REPORT_ONLY"


class MissingFXPolicy(StrEnum):
    FAIL_CLOSED = "FAIL_CLOSED"


class FXProfileStatus(StrEnum):
    ACTIVE = "ACTIVE"
    PLACEHOLDER = "PLACEHOLDER"
    NEEDS_EVIDENCE = "NEEDS_EVIDENCE"
    DISABLED = "DISABLED"


class ProfitabilityEligibilityStatus(StrEnum):
    ELIGIBLE = "ELIGIBLE"
    NON_ACTIONABLE_REPORT_ONLY = "NON_ACTIONABLE_REPORT_ONLY"
    BLOCKED_NON_POSITIVE_NET_PROFIT = "BLOCKED_NON_POSITIVE_NET_PROFIT"
    BLOCKED_MIN_NET_RETURN = "BLOCKED_MIN_NET_RETURN"
    BLOCKED_BREAK_EVEN_MOVE = "BLOCKED_BREAK_EVEN_MOVE"
    BLOCKED_MISSING_FX = "BLOCKED_MISSING_FX"
    BLOCKED_STALE_FX = "BLOCKED_STALE_FX"
    BLOCKED_INVALID_PROFILE = "BLOCKED_INVALID_PROFILE"


class FeeTaxProfile(StrictModel):
    track: StrategyTrack
    market_id: str = Field(..., min_length=1)
    asset_type: str = Field(..., min_length=1)
    buy_commission_rate: float = Field(..., ge=0)
    sell_commission_rate: float = Field(..., ge=0)
    transaction_tax_rate: float = Field(..., ge=0)
    regulatory_fee_rate: float = Field(..., ge=0)
    annual_tax_treatment: str = Field(..., min_length=1)
    tax_estimate_mode: TaxEstimateMode
    effective_date: date | None = None
    evidence_source: str | None = None
    status: FeeTaxProfileStatus
    simulation_only: bool = False
    estimated_tax_rate: float = Field(default=0.0, ge=0)

    @field_validator("market_id", "asset_type")
    @classmethod
    def normalize_text(cls, value: str) -> str:
        return value.strip().upper()

    @model_validator(mode="after")
    def apply_placeholder_rules(self):
        if self.status in {FeeTaxProfileStatus.PLACEHOLDER, FeeTaxProfileStatus.NEEDS_EVIDENCE}:
            if self.simulation_only:
                return self
            if self.tax_estimate_mode == TaxEstimateMode.EXCLUDED:
                self.tax_estimate_mode = TaxEstimateMode.REPORT_ONLY
                return self
            if self.tax_estimate_mode != TaxEstimateMode.REPORT_ONLY:
                raise ValueError("PLACEHOLDER or NEEDS_EVIDENCE profiles must default to REPORT_ONLY unless simulation_only is explicit")
        return self


class CurrencyProfile(StrictModel):
    base_currency: str = Field(..., min_length=3)
    settlement_currency: str = Field(..., min_length=3)
    reporting_currency: str = Field(..., min_length=3)
    fx_reference_pair: str | None = None
    fx_rate_source: str | None = None
    fx_timestamp: datetime | None = None
    fx_rate: float | None = Field(default=None, gt=0)
    stale_fx_after_hours: int | None = Field(default=None, gt=0)
    missing_fx_policy: MissingFXPolicy = MissingFXPolicy.FAIL_CLOSED

    @field_validator("base_currency", "settlement_currency", "reporting_currency")
    @classmethod
    def normalize_currency(cls, value: str) -> str:
        return value.strip().upper()

    @field_validator("fx_timestamp")
    @classmethod
    def validate_fx_timestamp(cls, value: datetime | None):
        if value is None:
            return value
        return aware(value)


class FXCostProfile(StrictModel):
    fx_spread_rate: float = Field(..., ge=0)
    conversion_fee_rate: float = Field(..., ge=0)
    buy_side_conversion: bool
    sell_side_conversion: bool
    realized_fx_only: bool
    status: FXProfileStatus


class MarketProfitTradeInput(StrictModel):
    entry_price: float = Field(..., gt=0)
    exit_price: float = Field(..., gt=0)
    quantity: int = Field(..., gt=0)
    min_expected_net_return_pct: float = Field(..., ge=0)
    max_break_even_move_pct: float = Field(..., ge=0)
    target_price: float = Field(..., gt=0)
    risk_reference_price: float = Field(..., gt=0)

    @model_validator(mode="after")
    def validate_trade_shape(self):
        if self.risk_reference_price >= self.entry_price:
            raise ValueError("risk_reference_price must be below entry_price")
        return self


class MarketProfitFixture(StrictModel):
    schema_version: str
    run_id: str = Field(..., min_length=1)
    created_at: datetime
    strategy_request: StrategyTrackRequest
    fee_tax_profile: FeeTaxProfile
    currency_profile: CurrencyProfile
    fx_cost_profile: FXCostProfile | None = None
    trade_input: MarketProfitTradeInput
    _created = field_validator("created_at")(aware)

    @field_validator("schema_version")
    @classmethod
    def exact_schema(cls, value: str) -> str:
        if value != "4.1-market-profit-fixture":
            raise ValueError("schema_version must be exactly 4.1-market-profit-fixture")
        return value

    @model_validator(mode="after")
    def validate_track_awareness(self):
        if self.strategy_request.market_profile is None:
            raise ValueError("market_profile is required")
        if self.fee_tax_profile.track != self.strategy_request.strategy_track:
            raise ValueError("fee/tax profile track conflicts with strategy_track")
        if self.fee_tax_profile.market_id != self.strategy_request.market_profile.market_id:
            raise ValueError("fee/tax profile market_id conflicts with market_profile")
        if self.currency_profile.base_currency != self.strategy_request.market_profile.base_currency:
            raise ValueError("currency_profile base_currency conflicts with market_profile")
        needs_fx = (
            self.currency_profile.reporting_currency != self.currency_profile.base_currency
            or self.strategy_request.strategy_track == StrategyTrack.OVERSEAS_US
        )
        if needs_fx:
            if self.currency_profile.fx_rate is None or self.currency_profile.fx_timestamp is None:
                raise ValueError("FX rate and timestamp are required for cross-currency reporting")
            if self.fx_cost_profile is None:
                raise ValueError("FX cost profile is required for cross-currency reporting")
        return self


class TradeCostEstimate(StrictModel):
    track: StrategyTrack
    market_id: str
    trade_currency: str
    reporting_currency: str
    entry_price: float
    exit_price: float
    quantity: int
    gross_entry_amount: float
    gross_exit_amount: float
    buy_commission_amount: float
    sell_commission_amount: float
    transaction_tax_amount: float
    regulatory_fee_amount: float
    fx_spread_cost_amount: float
    fx_conversion_fee_amount: float
    estimated_tax_amount: float
    total_estimated_costs: float
    profile_status_summary: dict = Field(default_factory=dict)


class NetProfitEstimate(StrictModel):
    gross_pnl_amount: float
    total_estimated_costs: float
    expected_net_pnl_amount: float
    expected_net_return_pct: float
    reporting_currency: str
    tax_estimate_mode: TaxEstimateMode
    actionable_status: bool
    non_actionable_reasons: list[str] = Field(default_factory=list)
    evidence_completeness_status: str


class BreakEvenMoveEstimate(StrictModel):
    break_even_exit_price: float
    break_even_move_pct: float
    minimum_target_price_after_costs: float
    minimum_required_move_after_costs: float
    minimum_risk_reward_after_costs: float
    tick_size_placeholder: str = "TRACK_SPECIFIC_PLACEHOLDER"


class TrackAwareProfitabilityCheck(StrictModel):
    strategy_track: StrategyTrack
    market_profile: MarketProfile
    fee_tax_profile: FeeTaxProfile
    currency_profile: CurrencyProfile
    fx_cost_profile: FXCostProfile | None = None
    trade_cost_estimate: TradeCostEstimate
    net_profit_estimate: NetProfitEstimate
    break_even_estimate: BreakEvenMoveEstimate
    eligibility_status: ProfitabilityEligibilityStatus
    warnings: list[str] = Field(default_factory=list)
    block_reasons: list[str] = Field(default_factory=list)


class MarketProfitReport(StrictModel):
    schema_version: str = "4.1-market-profit-report"
    fixture_checksum: str
    run_id: str
    created_at: datetime
    check: TrackAwareProfitabilityCheck
    metadata_json: dict = Field(default_factory=lambda: dict(MARKET_PROFIT_METADATA))
    _created = field_validator("created_at")(aware)


class MarketProfitValidationReport(StrictModel):
    schema_version: str = "4.1-market-profit-validation-report"
    run_id: str
    created_at: datetime
    summary: dict = Field(default_factory=dict)
    metadata_json: dict = Field(default_factory=lambda: dict(MARKET_PROFIT_METADATA))
    _created = field_validator("created_at")(aware)


class MarketProfitComparisonReport(StrictModel):
    schema_version: str = "4.1-market-profit-comparison-report"
    run_id: str
    created_at: datetime
    comparison_count: int = Field(..., ge=0)
    comparisons: list[dict] = Field(default_factory=list)
    metadata_json: dict = Field(default_factory=lambda: dict(MARKET_PROFIT_METADATA))
    _created = field_validator("created_at")(aware)


class MarketProfitCompareFixture(StrictModel):
    fixture_files: list[str] = Field(..., min_length=2)

    @field_validator("fixture_files")
    @classmethod
    def no_blank_files(cls, values: list[str]) -> list[str]:
        cleaned = [item.strip() for item in values]
        if any(not item for item in cleaned):
            raise ValueError("fixture_files must not contain blank values")
        return cleaned
