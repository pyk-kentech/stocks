from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from pydantic import Field, field_validator, model_validator

from stock_risk_mcp.models import StrictModel


def _aware(value: datetime | str | None) -> datetime | None:
    if value is None:
        return None
    parsed = datetime.fromisoformat(value) if isinstance(value, str) else value
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError("timestamp must include timezone")
    return parsed


def _string_required(value, field_name: str) -> str:
    if value is None:
        raise ValueError(f"{field_name} must not be null")
    cleaned = str(value).strip()
    if not cleaned:
        raise ValueError(f"{field_name} must not be blank")
    return cleaned


def _upper_required(value, field_name: str) -> str:
    return _string_required(value, field_name).upper()


def _validate_local_path(value: str, field_name: str) -> str:
    cleaned = _string_required(value, field_name)
    lowered = cleaned.lower()
    if "://" in lowered or lowered.startswith("//"):
        raise ValueError(f"{field_name} must be a local file path")
    if lowered.endswith(".parquet"):
        raise ValueError("parquet remains unsupported")
    return cleaned


def _normalize_list(value, field_name: str, *, upper: bool = False) -> list[str]:
    if value is None:
        return []
    if isinstance(value, (str, bytes)) or not isinstance(value, list):
        raise ValueError(f"{field_name} must be a list")
    if upper:
        return [_upper_required(item, field_name) for item in value]
    return [_validate_local_path(item, field_name) for item in value]


def _validate_safety_flags(model, context: str):
    for flag_name in (
        "read_only",
        "report_only",
        "non_executable",
        "local_file_only",
        "offline_only",
        "no_network",
        "no_provider_api",
        "no_order",
        "no_account_mutation",
        "no_live_prod",
        "no_autonomous_trading",
        "no_broker_api",
        "no_kiwoom_api",
        "no_websocket",
        "no_cloud_llm",
        "no_local_llm_runtime",
    ):
        if not getattr(model, flag_name):
            raise ValueError(f"{context} must remain {flag_name}")
    return model


class StopDistanceMode(StrEnum):
    FIXED_PERCENT = "FIXED_PERCENT"
    ATR_MULTIPLE = "ATR_MULTIPLE"
    EXPLICIT_STOP_PRICE = "EXPLICIT_STOP_PRICE"
    VOLATILITY_ADJUSTED = "VOLATILITY_ADJUSTED"
    UNKNOWN = "UNKNOWN"


class PositionSizingDecision(StrEnum):
    BLOCKED = "BLOCKED"
    WATCH_ONLY = "WATCH_ONLY"
    SIZE_READY = "SIZE_READY"
    REDUCE_SIZE = "REDUCE_SIZE"
    CASH_LIMITED = "CASH_LIMITED"
    RISK_BUDGET_LIMITED = "RISK_BUDGET_LIMITED"
    DATA_GAP = "DATA_GAP"
    GAP = "GAP"
    REJECTED = "REJECTED"


class _BaseReport(StrictModel):
    read_only: bool = True
    report_only: bool = True
    non_executable: bool = True
    local_file_only: bool = True
    offline_only: bool = True
    no_network: bool = True
    no_provider_api: bool = True
    no_order: bool = True
    no_account_mutation: bool = True
    no_live_prod: bool = True
    no_autonomous_trading: bool = True
    no_broker_api: bool = True
    no_kiwoom_api: bool = True
    no_websocket: bool = True
    no_cloud_llm: bool = True
    no_local_llm_runtime: bool = True


class PositionSizingSafetyReport(_BaseReport):
    safety_report_id: str = Field(..., min_length=1)
    blocked_capabilities: list[str] = Field(default_factory=list)
    findings: list[str] = Field(default_factory=list)

    @field_validator("safety_report_id", mode="before")
    @classmethod
    def normalize_id(cls, value):
        return _upper_required(value, "safety_report_id")

    @field_validator("blocked_capabilities", "findings", mode="before")
    @classmethod
    def normalize_lists(cls, value, info):
        return _normalize_list(value, info.field_name, upper=True)

    @model_validator(mode="after")
    def validate_model(self):
        return _validate_safety_flags(self, "position sizing safety report")


class PositionSizingAuditRecord(StrictModel):
    audit_record_id: str = Field(..., min_length=1)
    created_at: datetime
    source_path: str = Field(..., min_length=1)
    operator_context: str = Field(..., min_length=1)
    redaction_applied: bool = True
    contains_secret_material: bool = False
    contains_token_material: bool = False
    contains_account_material: bool = False

    @field_validator("audit_record_id", mode="before")
    @classmethod
    def normalize_id(cls, value):
        return _upper_required(value, "audit_record_id")

    @field_validator("created_at", mode="before")
    @classmethod
    def normalize_dt(cls, value):
        return _aware(value)

    @field_validator("source_path", mode="before")
    @classmethod
    def normalize_source(cls, value):
        return _validate_local_path(value, "source_path")

    @field_validator("operator_context", mode="before")
    @classmethod
    def normalize_context(cls, value):
        return _string_required(value, "operator_context")


class PositionSizingSummaryReport(_BaseReport):
    report_id: str = Field(..., min_length=1)
    decision: PositionSizingDecision
    decision_reason: str = Field(..., min_length=1)
    candidate_symbol: str = Field(..., min_length=1)
    risk_cash: float = Field(..., ge=0)
    effective_risk_cash: float = Field(..., ge=0)
    rounded_quantity: int = Field(..., ge=0)
    notional_value: float = Field(..., ge=0)
    capital_usage_percent: float = Field(..., ge=0)
    risk_usage_percent: float = Field(..., ge=0)
    remaining_cash_estimate: float
    remaining_daily_risk_budget_estimate: float

    @field_validator("report_id", "candidate_symbol", mode="before")
    @classmethod
    def normalize_upper(cls, value):
        return _upper_required(value, "field")

    @field_validator("decision_reason", mode="before")
    @classmethod
    def normalize_reason(cls, value):
        return _string_required(value, "decision_reason")

    @model_validator(mode="after")
    def validate_model(self):
        return _validate_safety_flags(self, "position sizing summary report")


class StopDistanceReport(_BaseReport):
    report_id: str = Field(..., min_length=1)
    stop_mode: StopDistanceMode
    stop_price: float | None = None
    stop_distance_absolute: float | None = None
    stop_distance_percent: float | None = None
    atr_multiple: float | None = None
    stop_valid: bool = False
    stop_evidence_ref: str | None = None

    @field_validator("report_id", mode="before")
    @classmethod
    def normalize_id(cls, value):
        return _upper_required(value, "report_id")

    @field_validator("stop_evidence_ref", mode="before")
    @classmethod
    def normalize_optional_ref(cls, value):
        if value is None:
            return None
        return _validate_local_path(value, "stop_evidence_ref")

    @model_validator(mode="after")
    def validate_model(self):
        return _validate_safety_flags(self, "stop distance report")


class RiskBudgetReport(_BaseReport):
    report_id: str = Field(..., min_length=1)
    risk_per_trade_cap: float = Field(..., ge=0)
    max_daily_loss_cap: float = Field(..., ge=0)
    max_open_risk_cap: float = Field(..., ge=0)
    market_regime_size_multiplier: float = Field(..., ge=0)
    volatility_size_multiplier: float = Field(..., ge=0)
    confidence_multiplier: float = Field(..., ge=0)
    learned_multiplier_requested: float = Field(..., ge=0)
    learned_multiplier_applied: float = Field(..., ge=0)
    fail_closed: bool = True

    @field_validator("report_id", mode="before")
    @classmethod
    def normalize_id(cls, value):
        return _upper_required(value, "report_id")

    @model_validator(mode="after")
    def validate_model(self):
        return _validate_safety_flags(self, "risk budget report")


class PositionSizingDataReadinessReport(_BaseReport):
    report_id: str = Field(..., min_length=1)
    price_ready: bool = False
    atr_ready: bool = False
    fx_ready: bool = False
    cost_ready: bool = False
    provider_readiness_level: str = Field(..., min_length=1)
    research_only_policy_allowed: bool = False
    missing_refs: list[str] = Field(default_factory=list)

    @field_validator("report_id", "provider_readiness_level", mode="before")
    @classmethod
    def normalize_upper(cls, value):
        return _upper_required(value, "field")

    @field_validator("missing_refs", mode="before")
    @classmethod
    def normalize_missing_refs(cls, value):
        return _normalize_list(value, "missing_refs", upper=True)

    @model_validator(mode="after")
    def validate_model(self):
        return _validate_safety_flags(self, "position sizing data readiness report")


class PositionQuantityNotionalReport(_BaseReport):
    report_id: str = Field(..., min_length=1)
    stop_distance_per_share: float = Field(..., ge=0)
    raw_quantity: float = Field(..., ge=0)
    rounded_quantity: int = Field(..., ge=0)
    notional_value: float = Field(..., ge=0)
    exposure_after_trade: float = Field(..., ge=0)

    @field_validator("report_id", mode="before")
    @classmethod
    def normalize_id(cls, value):
        return _upper_required(value, "report_id")

    @model_validator(mode="after")
    def validate_model(self):
        return _validate_safety_flags(self, "position quantity report")


class PositionCostAssumptionReport(_BaseReport):
    report_id: str = Field(..., min_length=1)
    estimated_fees: float = Field(..., ge=0)
    estimated_tax: float = Field(..., ge=0)
    estimated_slippage: float = Field(..., ge=0)
    total_estimated_cost: float = Field(..., ge=0)
    fee_tax_slippage_assumption_ref: str = Field(..., min_length=1)

    @field_validator("report_id", mode="before")
    @classmethod
    def normalize_id(cls, value):
        return _upper_required(value, "report_id")

    @field_validator("fee_tax_slippage_assumption_ref", mode="before")
    @classmethod
    def normalize_ref(cls, value):
        return _validate_local_path(value, "fee_tax_slippage_assumption_ref")

    @model_validator(mode="after")
    def validate_model(self):
        return _validate_safety_flags(self, "position cost assumption report")


class MarketRegimeSizingAdjustmentReport(_BaseReport):
    report_id: str = Field(..., min_length=1)
    market_regime_label: str | None = None
    market_volatility_state: str | None = None
    market_stress_state: str | None = None
    applied_size_multiplier: float = Field(..., ge=0)
    regime_gap_noted: bool = False
    watch_only_triggered: bool = False

    @field_validator("report_id", "market_regime_label", "market_volatility_state", "market_stress_state", mode="before")
    @classmethod
    def normalize_optional_upper(cls, value):
        if value is None:
            return None
        return _upper_required(value, "field")

    @model_validator(mode="after")
    def validate_model(self):
        return _validate_safety_flags(self, "market regime sizing adjustment report")


class InverseHedgeSizingReport(_BaseReport):
    report_id: str = Field(..., min_length=1)
    inverse_hedge_review_required: bool = False
    inverse_hedge_cap_breached: bool = False
    leverage_flag_present: bool = False
    daily_reset_warning_present: bool = False
    short_holding_period_warning_present: bool = False
    basis_risk_note: str | None = None

    @field_validator("report_id", mode="before")
    @classmethod
    def normalize_id(cls, value):
        return _upper_required(value, "report_id")

    @field_validator("basis_risk_note", mode="before")
    @classmethod
    def normalize_note(cls, value):
        if value is None:
            return None
        return _string_required(value, "basis_risk_note")

    @model_validator(mode="after")
    def validate_model(self):
        return _validate_safety_flags(self, "inverse hedge sizing report")


class PositionSizingBoundaryViolationReport(_BaseReport):
    report_id: str = Field(..., min_length=1)
    violations: list[str] = Field(default_factory=list)

    @field_validator("report_id", mode="before")
    @classmethod
    def normalize_id(cls, value):
        return _upper_required(value, "report_id")

    @field_validator("violations", mode="before")
    @classmethod
    def normalize_violations(cls, value):
        return _normalize_list(value, "violations", upper=True)

    @model_validator(mode="after")
    def validate_model(self):
        return _validate_safety_flags(self, "boundary violation report")


class PositionSizingGapEntry(StrictModel):
    gap_id: str = Field(..., min_length=1)
    gap_category: str = Field(..., min_length=1)
    severity: str = Field(default="REPORT_ONLY", min_length=1)
    message: str = Field(..., min_length=1)

    @field_validator("gap_id", "gap_category", "severity", mode="before")
    @classmethod
    def normalize_upper(cls, value):
        return _upper_required(value, "field")

    @field_validator("message", mode="before")
    @classmethod
    def normalize_message(cls, value):
        return _string_required(value, "message")


class PositionSizingGapReport(_BaseReport):
    gap_report_id: str = Field(..., min_length=1)
    decision: PositionSizingDecision
    gap_entries: list[PositionSizingGapEntry] = Field(default_factory=list)
    blocking_gap_count: int = Field(default=0, ge=0)
    warning_gap_count: int = Field(default=0, ge=0)
    gap_categories: list[str] = Field(default_factory=list)

    @field_validator("gap_report_id", mode="before")
    @classmethod
    def normalize_id(cls, value):
        return _upper_required(value, "gap_report_id")

    @model_validator(mode="after")
    def validate_model(self):
        if not self.gap_categories:
            self.gap_categories = [entry.gap_category for entry in self.gap_entries]
        return _validate_safety_flags(self, "position sizing gap report")


class PositionSizingInput(StrictModel):
    sizing_review_id: str = Field(..., min_length=1)
    candidate_symbol: str = Field(..., min_length=1)
    market: str = Field(..., min_length=1)
    currency: str = Field(..., min_length=1)
    side: str = Field(..., min_length=1)
    candidate_action_type: str = Field(..., min_length=1)
    entry_price: float | None = Field(default=None, gt=0)
    current_price: float | None = Field(default=None, gt=0)
    atr_value: float | None = Field(default=None, gt=0)
    atr_period: int | None = Field(default=None, ge=1)
    atr_multiplier: float | None = Field(default=None, gt=0)
    fixed_stop_percent: float | None = Field(default=None, gt=0, lt=1)
    explicit_stop_price: float | None = Field(default=None, gt=0)
    account_equity: float = Field(..., gt=0)
    available_cash: float = Field(..., ge=0)
    risk_per_trade_percent: float = Field(..., gt=0, le=1)
    max_risk_cash_per_trade: float = Field(..., ge=0)
    daily_risk_budget: float = Field(..., ge=0)
    remaining_daily_risk_budget: float = Field(..., ge=0)
    current_gross_exposure: float = Field(default=0, ge=0)
    current_net_exposure: float = Field(default=0, ge=0)
    current_open_risk_percent: float = Field(default=0, ge=0)
    max_portfolio_exposure: float = Field(..., gt=0)
    max_gross_exposure: float = Field(..., gt=0)
    max_net_exposure: float = Field(..., gt=0)
    max_single_position_exposure: float = Field(..., gt=0)
    max_sector_exposure: float | None = Field(default=None, gt=0)
    max_inverse_hedge_exposure: float = Field(..., ge=0)
    sector_name: str | None = None
    sector_exposure_after_trade_estimate: float | None = Field(default=None, ge=0)
    is_inverse_or_hedge: bool = False
    instrument_eligibility_ref: str | None = None
    liquidity_evidence_ref: str | None = None
    leverage_flag: bool = False
    daily_reset_warning: bool = False
    short_holding_period_warning: bool = False
    basis_risk_note: str | None = None
    fee_bps: float = Field(default=0, ge=0)
    tax_bps: float = Field(default=0, ge=0)
    slippage_bps: float = Field(default=0, ge=0)
    fee_tax_slippage_assumption_ref: str = Field(..., min_length=1)
    fx_conversion_rate: float | None = Field(default=None, gt=0)
    fx_conversion_ref: str | None = None
    market_regime_constraint_ref: str | None = None
    market_regime_label: str | None = None
    market_volatility_state: str | None = None
    market_stress_state: str | None = None
    market_regime_size_multiplier: float = Field(default=1.0, ge=0)
    provider_readiness_ref: str | None = None
    provider_readiness_level: str = Field(..., min_length=1)
    provider_policy_allows_research_only: bool = False
    price_contract_ref: str | None = None
    atr_contract_ref: str | None = None
    fx_contract_ref: str | None = None
    cost_contract_ref: str | None = None
    paper_evaluation_ref: str | None = None
    available_at: datetime | None = None
    observed_at: datetime | None = None
    decision_anchor_at: datetime | None = None
    source_refs: list[str] = Field(default_factory=list)
    stop_mode: StopDistanceMode = StopDistanceMode.UNKNOWN
    requested_allocation_percent: float | None = Field(default=None, ge=0)
    requested_quantity: int | None = Field(default=None, ge=0)
    round_lot_size: int = Field(default=1, ge=1)
    confidence_multiplier: float = Field(default=1.0, ge=0)
    volatility_size_multiplier: float = Field(default=1.0, ge=0)
    learned_size_multiplier: float = Field(default=1.0, ge=0)
    max_daily_loss_cap: float = Field(default=0, ge=0)
    max_open_risk_cap: float = Field(default=0, ge=0)
    max_order_count_per_day: int = Field(default=0, ge=0)
    cool_down_policy: str = Field(default="NONE", min_length=1)
    fail_closed: bool = True
    report_only_preview_allowed: bool = True
    read_only: bool = True
    report_only: bool = True
    non_executable: bool = True
    local_file_only: bool = True
    offline_only: bool = True
    no_network: bool = True
    no_provider_api: bool = True
    no_order: bool = True
    no_account_mutation: bool = True
    no_live_prod: bool = True
    no_autonomous_trading: bool = True
    no_broker_api: bool = True
    no_kiwoom_api: bool = True
    no_websocket: bool = True
    no_cloud_llm: bool = True
    no_local_llm_runtime: bool = True
    safety_report: PositionSizingSafetyReport
    audit_records: list[PositionSizingAuditRecord] = Field(default_factory=list)
    summary_report: PositionSizingSummaryReport | None = None
    stop_distance_report: StopDistanceReport | None = None
    risk_budget_report: RiskBudgetReport | None = None
    data_readiness_report: PositionSizingDataReadinessReport | None = None
    quantity_notional_report: PositionQuantityNotionalReport | None = None
    cost_assumption_report: PositionCostAssumptionReport | None = None
    market_regime_adjustment_report: MarketRegimeSizingAdjustmentReport | None = None
    inverse_hedge_sizing_report: InverseHedgeSizingReport | None = None
    boundary_violation_report: PositionSizingBoundaryViolationReport | None = None
    gap_report: PositionSizingGapReport | None = None

    @field_validator(
        "sizing_review_id",
        "candidate_symbol",
        "market",
        "currency",
        "side",
        "candidate_action_type",
        "market_regime_label",
        "market_volatility_state",
        "market_stress_state",
        "provider_readiness_level",
        "cool_down_policy",
        mode="before",
    )
    @classmethod
    def normalize_upper(cls, value):
        if value is None:
            return None
        return _upper_required(value, "field")

    @field_validator("sector_name", "basis_risk_note", mode="before")
    @classmethod
    def normalize_optional_string(cls, value):
        if value is None:
            return None
        return _string_required(value, "field")

    @field_validator("instrument_eligibility_ref", "liquidity_evidence_ref", "fee_tax_slippage_assumption_ref", "fx_conversion_ref", "market_regime_constraint_ref", "provider_readiness_ref", "price_contract_ref", "atr_contract_ref", "fx_contract_ref", "cost_contract_ref", "paper_evaluation_ref", mode="before")
    @classmethod
    def normalize_optional_ref(cls, value):
        if value is None:
            return None
        return _validate_local_path(value, "ref")

    @field_validator("available_at", "observed_at", "decision_anchor_at", mode="before")
    @classmethod
    def normalize_dt(cls, value):
        return _aware(value)

    @field_validator("source_refs", mode="before")
    @classmethod
    def normalize_source_refs(cls, value):
        return _normalize_list(value, "source_refs")

    @model_validator(mode="after")
    def validate_model(self):
        _validate_safety_flags(self, "position sizing input")
        if self.audit_records:
            for audit in self.audit_records:
                if not audit.redaction_applied:
                    raise ValueError("audit records must be redacted")
        return self
