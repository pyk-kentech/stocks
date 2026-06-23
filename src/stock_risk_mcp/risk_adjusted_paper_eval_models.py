from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from pydantic import Field, field_validator, model_validator

from stock_risk_mcp.models import StrictModel


def _aware(value: datetime | str) -> datetime:
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


class RiskAdjustedPaperEvalDecision(StrEnum):
    BLOCKED = "BLOCKED"
    RESEARCH_ONLY = "RESEARCH_ONLY"
    PAPER_EVALUATED = "PAPER_EVALUATED"
    PAPER_PASS = "PAPER_PASS"
    GAP = "GAP"
    REJECTED = "REJECTED"


class RiskAdjustedPaperEvalGapCategory(StrEnum):
    EVALUATION_REPORT_GENERATED = "EVALUATION_REPORT_GENERATED"
    MISSING_V76_POLICY_DEPENDENCY = "MISSING_V76_POLICY_DEPENDENCY"
    INVALID_POLICY_PROMOTION_DECISION = "INVALID_POLICY_PROMOTION_DECISION"
    MISSING_POINT_IN_TIME_DATASET = "MISSING_POINT_IN_TIME_DATASET"
    MISSING_WALK_FORWARD_SPLIT = "MISSING_WALK_FORWARD_SPLIT"
    MISSING_MARKET_DATA_FIXTURE = "MISSING_MARKET_DATA_FIXTURE"
    MISSING_COST_SLIPPAGE_ASSUMPTIONS = "MISSING_COST_SLIPPAGE_ASSUMPTIONS"
    MISSING_CNN_FEATURE = "MISSING_CNN_FEATURE"
    FUTURE_PRICE_LEAKAGE_DETECTED = "FUTURE_PRICE_LEAKAGE_DETECTED"
    FUTURE_REGIME_FEAR_LEAKAGE_DETECTED = "FUTURE_REGIME_FEAR_LEAKAGE_DETECTED"
    MAX_DRAWDOWN_BREACH = "MAX_DRAWDOWN_BREACH"
    DAILY_LOSS_BREACH = "DAILY_LOSS_BREACH"
    EXCESSIVE_TURNOVER = "EXCESSIVE_TURNOVER"
    EXCESSIVE_INVERSE_HEDGE_EXPOSURE = "EXCESSIVE_INVERSE_HEDGE_EXPOSURE"
    REMOTE_SOURCE_NOT_ALLOWED = "REMOTE_SOURCE_NOT_ALLOWED"
    NETWORK_PATH_NOT_ALLOWED = "NETWORK_PATH_NOT_ALLOWED"
    ORDER_PATH_NOT_ALLOWED = "ORDER_PATH_NOT_ALLOWED"
    LIVE_PROD_NOT_ALLOWED = "LIVE_PROD_NOT_ALLOWED"
    PARQUET_NOT_ALLOWED = "PARQUET_NOT_ALLOWED"


class RiskAdjustedPaperEvalGapEntry(StrictModel):
    gap_id: str = Field(..., min_length=1)
    gap_category: RiskAdjustedPaperEvalGapCategory
    severity: str = Field(default="REPORT_ONLY", min_length=1)
    message: str = Field(..., min_length=1)

    @field_validator("gap_id", "severity", mode="before")
    @classmethod
    def normalize_upper(cls, value):
        return _upper_required(value, "gap")

    @field_validator("message", mode="before")
    @classmethod
    def normalize_message(cls, value):
        return _string_required(value, "message")


class VirtualOrder(StrictModel):
    virtual_order_id: str = Field(..., min_length=1)
    symbol: str = Field(..., min_length=1)
    side: str = Field(..., min_length=1)
    decision_timestamp: datetime
    simulated_fill_timestamp: datetime
    simulated_fill_price: float = Field(..., gt=0)
    quantity: float = Field(..., gt=0)
    executable: bool = False

    @field_validator("virtual_order_id", "symbol", "side", mode="before")
    @classmethod
    def normalize_string(cls, value, info):
        if info.field_name == "symbol":
            return _string_required(value, info.field_name).upper()
        return _upper_required(value, info.field_name)

    @field_validator("decision_timestamp", "simulated_fill_timestamp", mode="before")
    @classmethod
    def normalize_dt(cls, value):
        return _aware(value)


class VirtualTrade(StrictModel):
    virtual_trade_id: str = Field(..., min_length=1)
    symbol: str = Field(..., min_length=1)
    side: str = Field(..., min_length=1)
    fill_price: float = Field(..., gt=0)
    quantity: float = Field(..., gt=0)
    fee_estimate: float = Field(default=0.0, ge=0)
    tax_estimate: float = Field(default=0.0, ge=0)
    slippage_estimate: float = Field(default=0.0, ge=0)
    rejected_virtual_order_reason: str | None = None
    executable: bool = False

    @field_validator("virtual_trade_id", "symbol", "side", mode="before")
    @classmethod
    def normalize_string(cls, value, info):
        if info.field_name == "symbol":
            return _string_required(value, info.field_name).upper()
        return _upper_required(value, info.field_name)


class VirtualPosition(StrictModel):
    symbol: str = Field(..., min_length=1)
    quantity: float = Field(..., ge=0)
    average_price: float = Field(..., ge=0)
    market_value: float = Field(..., ge=0)

    @field_validator("symbol", mode="before")
    @classmethod
    def normalize_symbol(cls, value):
        return _string_required(value, "symbol").upper()


class VirtualPortfolioReport(StrictModel):
    report_id: str = Field(..., min_length=1)
    cash: float
    virtual_positions: list[VirtualPosition] = Field(default_factory=list)
    virtual_orders: list[VirtualOrder] = Field(default_factory=list)
    virtual_trades: list[VirtualTrade] = Field(default_factory=list)
    equity_curve: list[float] = Field(default_factory=list)
    realized_pnl: float
    unrealized_pnl: float
    exposure: float = Field(..., ge=0)
    gross_exposure: float = Field(..., ge=0)
    net_exposure: float
    turnover: float = Field(..., ge=0)
    max_drawdown: float = Field(..., ge=0)
    daily_loss_estimate: float = Field(..., ge=0)
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

    @field_validator("report_id", mode="before")
    @classmethod
    def normalize_id(cls, value):
        return _upper_required(value, "report_id")

    @model_validator(mode="after")
    def validate_report(self):
        return _validate_safety_flags(self, "virtual portfolio report")


class PaperEvaluationSummaryReport(VirtualPortfolioReport):
    decision: RiskAdjustedPaperEvalDecision
    decision_reason: str = Field(..., min_length=1)
    total_return: float
    benchmark_relative_return: float


class VirtualTradeLedgerReport(VirtualPortfolioReport):
    pass


class PaperCostSlippageReport(VirtualPortfolioReport):
    total_fees: float = Field(..., ge=0)
    total_taxes: float = Field(..., ge=0)
    total_slippage: float = Field(..., ge=0)
    cost_adjusted_return: float
    slippage_adjusted_return: float


class PaperRiskAdjustedPerformanceReport(VirtualPortfolioReport):
    volatility: float = Field(..., ge=0)
    sharpe_like_score: float
    sortino_like_score: float
    calmar_like_score: float
    hit_rate: float = Field(..., ge=0, le=1)
    average_win: float
    average_loss: float
    tail_risk_estimate: float = Field(..., ge=0)


class PaperDrawdownExposureReport(VirtualPortfolioReport):
    max_drawdown_limit_breached: bool = False
    daily_loss_limit_breached: bool = False
    max_gross_exposure_breached: bool = False
    max_single_action_exposure_breached: bool = False
    max_inverse_hedge_exposure_breached: bool = False
    turnover_limit_breached: bool = False


class PaperRegimeFearBucketReport(VirtualPortfolioReport):
    regime_bucket_performance: dict[str, float] = Field(default_factory=dict)
    fear_bucket_performance: dict[str, float] = Field(default_factory=dict)
    cnn_fear_greed_feature_used: bool = False
    missing_cnn_feature_gap_noted: bool = False


class PaperPassReadinessReport(VirtualPortfolioReport):
    decision: RiskAdjustedPaperEvalDecision
    policy_promotion_decision: str = Field(..., min_length=1)
    costs_included_for_pass: bool = False
    point_in_time_evidence_present: bool = False
    walk_forward_evidence_present: bool = False
    no_future_leakage_detected: bool = False

    @field_validator("policy_promotion_decision", mode="before")
    @classmethod
    def normalize_policy_decision(cls, value):
        return _upper_required(value, "policy_promotion_decision")


class RiskAdjustedPaperEvalSafetyReport(StrictModel):
    safety_report_id: str = Field(..., min_length=1)
    blocked_capabilities: list[str] = Field(default_factory=list)
    findings: list[str] = Field(default_factory=list)
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

    @field_validator("safety_report_id", mode="before")
    @classmethod
    def normalize_id(cls, value):
        return _upper_required(value, "safety_report_id")

    @model_validator(mode="after")
    def validate_report(self):
        if not self.blocked_capabilities:
            raise ValueError("safety report must expose blocked capabilities")
        return _validate_safety_flags(self, "paper eval safety report")


class RiskAdjustedPaperEvalGapReport(StrictModel):
    gap_report_id: str = Field(..., min_length=1)
    decision: RiskAdjustedPaperEvalDecision
    gap_entries: list[RiskAdjustedPaperEvalGapEntry] = Field(default_factory=list)
    blocking_gap_count: int = Field(..., ge=0)
    warning_gap_count: int = Field(..., ge=0)
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

    @field_validator("gap_report_id", mode="before")
    @classmethod
    def normalize_id(cls, value):
        return _upper_required(value, "gap_report_id")

    @model_validator(mode="after")
    def validate_report(self):
        return _validate_safety_flags(self, "paper eval gap report")


class RiskAdjustedPaperEvalAuditRecord(StrictModel):
    audit_record_id: str = Field(..., min_length=1)
    created_at: datetime
    source_path: str = Field(..., min_length=1)
    operator_context: str = Field(..., min_length=1)
    redaction_applied: bool = True
    contains_secret_material: bool = False
    contains_token_material: bool = False
    contains_account_material: bool = False
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
    def normalize_source_path(cls, value):
        return _validate_local_path(value, "source_path")

    @field_validator("operator_context", mode="before")
    @classmethod
    def normalize_context(cls, value):
        return _string_required(value, "operator_context")

    @model_validator(mode="after")
    def validate_report(self):
        if not self.redaction_applied or self.contains_secret_material or self.contains_token_material or self.contains_account_material:
            raise ValueError("audit record must remain redacted and non-secret-bearing")
        return _validate_safety_flags(self, "paper eval audit record")


class RiskAdjustedPaperEvalInput(StrictModel):
    evaluation_id: str = Field(..., min_length=1)
    allocation_policy_candidate_ref: str | None = None
    policy_promotion_decision: str | None = None
    point_in_time_dataset_ref: str | None = None
    walk_forward_split_ref: str | None = None
    ensemble_candidate_ref: str | None = None
    regime_feature_refs: list[str] = Field(default_factory=list)
    cnn_fear_greed_feature_ref: str | None = None
    market_data_fixture_ref: str | None = None
    fee_tax_slippage_assumptions_ref: str | None = None
    initial_cash: float = Field(..., gt=0)
    evaluation_window_start: datetime
    evaluation_window_end: datetime
    benchmark_ref: str | None = None
    symbol: str = Field(..., min_length=1)
    quantity: float = Field(..., gt=0)
    decision_timestamp: datetime
    simulated_fill_timestamp: datetime
    simulated_fill_price: float = Field(..., gt=0)
    benchmark_return: float = 0.0
    end_price: float = Field(..., gt=0)
    volatility: float = Field(default=0.0, ge=0)
    max_drawdown_limit: float = Field(default=0.15, ge=0)
    daily_loss_limit: float = Field(default=0.05, ge=0)
    max_gross_exposure: float = Field(default=1.0, ge=0)
    max_single_action_exposure: float = Field(default=0.5, ge=0)
    max_inverse_hedge_exposure: float = Field(default=0.2, ge=0)
    turnover_limit: float = Field(default=1.0, ge=0)
    inverse_hedge_exposure: float = Field(default=0.0, ge=0)
    turnover: float = Field(default=0.0, ge=0)
    fee_bps: float = Field(default=0.0, ge=0)
    tax_bps: float = Field(default=0.0, ge=0)
    slippage_bps: float = Field(default=0.0, ge=0)
    future_price_leakage_detected: bool = False
    future_regime_fear_leakage_detected: bool = False
    available_at_safe_market_data: bool = True
    regime_bucket_name: str = Field(default="NEUTRAL", min_length=1)
    fear_bucket_name: str | None = None
    policy_score: float = 0.0
    safety_report: RiskAdjustedPaperEvalSafetyReport
    audit_records: list[RiskAdjustedPaperEvalAuditRecord] = Field(default_factory=list)
    summary_report: PaperEvaluationSummaryReport | None = None
    virtual_portfolio_report: VirtualPortfolioReport | None = None
    virtual_trade_ledger_report: VirtualTradeLedgerReport | None = None
    cost_slippage_report: PaperCostSlippageReport | None = None
    risk_adjusted_performance_report: PaperRiskAdjustedPerformanceReport | None = None
    drawdown_exposure_report: PaperDrawdownExposureReport | None = None
    regime_fear_bucket_report: PaperRegimeFearBucketReport | None = None
    pass_readiness_report: PaperPassReadinessReport | None = None
    gap_report: RiskAdjustedPaperEvalGapReport | None = None
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

    @field_validator(
        "evaluation_id",
        "regime_bucket_name",
        "symbol",
        mode="before",
    )
    @classmethod
    def normalize_upper_fields(cls, value):
        return _upper_required(value, "field")

    @field_validator(
        "allocation_policy_candidate_ref",
        "policy_promotion_decision",
        "point_in_time_dataset_ref",
        "walk_forward_split_ref",
        "ensemble_candidate_ref",
        "cnn_fear_greed_feature_ref",
        "market_data_fixture_ref",
        "fee_tax_slippage_assumptions_ref",
        "benchmark_ref",
        "fear_bucket_name",
        mode="before",
    )
    @classmethod
    def normalize_optional_fields(cls, value, info):
        if value is None:
            return None
        if info.field_name in {"policy_promotion_decision", "fear_bucket_name"}:
            return _upper_required(value, info.field_name)
        cleaned = str(value).strip()
        return cleaned or None

    @field_validator("regime_feature_refs", mode="before")
    @classmethod
    def normalize_regime_refs(cls, value):
        if value is None:
            return []
        if isinstance(value, (str, bytes)) or not isinstance(value, list):
            raise ValueError("regime_feature_refs must be a list")
        return [_upper_required(item, "regime_feature_ref") for item in value]

    @field_validator("evaluation_window_start", "evaluation_window_end", "decision_timestamp", "simulated_fill_timestamp", mode="before")
    @classmethod
    def normalize_dt(cls, value):
        return _aware(value)

    @model_validator(mode="after")
    def validate_input(self):
        if not self.audit_records:
            raise ValueError("audit_records must not be empty")
        if self.evaluation_window_end < self.evaluation_window_start:
            raise ValueError("evaluation window must be ordered")
        if self.simulated_fill_timestamp < self.decision_timestamp:
            raise ValueError("simulated fill timestamp must not precede decision timestamp")
        if self.policy_promotion_decision is None:
            pass
        return _validate_safety_flags(self, "risk adjusted paper eval input")
