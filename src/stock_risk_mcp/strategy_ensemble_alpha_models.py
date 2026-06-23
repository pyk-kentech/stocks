from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from pydantic import Field, field_validator, model_validator

from stock_risk_mcp.models import StrictModel


def _aware(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("timestamp must include timezone")
    return value


def _string_required(value, field_name: str) -> str:
    if value is None:
        raise ValueError(f"{field_name} must not be null")
    cleaned = str(value).strip()
    if not cleaned:
        raise ValueError(f"{field_name} must not be blank")
    return cleaned


def _upper_required(value, field_name: str) -> str:
    return _string_required(value, field_name).upper()


def _normalize_list(value, field_name: str, *, upper: bool = False) -> list[str]:
    if value is None:
        return []
    if isinstance(value, (str, bytes)) or not isinstance(value, list):
        raise ValueError(f"{field_name} must be a list")
    if upper:
        return [_upper_required(item, field_name) for item in value]
    return [_string_required(item, field_name) for item in value]


def _validate_local_path(value: str, field_name: str) -> str:
    cleaned = _string_required(value, field_name)
    lowered = cleaned.lower()
    if "://" in lowered or lowered.startswith("//"):
        raise ValueError(f"{field_name} must be a local file path")
    if lowered.endswith(".parquet"):
        raise ValueError("parquet remains unsupported")
    return cleaned


def _validate_safety_flags(model, context: str):
    for flag in (
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
        "no_cloud_llm",
        "no_local_llm_runtime",
    ):
        if not getattr(model, flag):
            raise ValueError(f"{context} must remain {flag}")
    return model


class StrategyFamily(StrEnum):
    MOMENTUM = "MOMENTUM"
    MEAN_REVERSION = "MEAN_REVERSION"
    BREAKOUT = "BREAKOUT"
    VOLUME_SHOCK = "VOLUME_SHOCK"
    VOLATILITY_CONTRACTION_EXPANSION = "VOLATILITY_CONTRACTION_EXPANSION"
    QUALITY_FUNDAMENTAL = "QUALITY_FUNDAMENTAL"
    EARNINGS_EVENT_DRIFT = "EARNINGS_EVENT_DRIFT"
    SECTOR_ROTATION = "SECTOR_ROTATION"
    MACRO_RISK_ON_RISK_OFF = "MACRO_RISK_ON_RISK_OFF"
    DEFENSIVE_CASH_RISK_CONTROL = "DEFENSIVE_CASH_RISK_CONTROL"


class EnsemblePromotionDecision(StrEnum):
    BLOCKED = "BLOCKED"
    RESEARCH_ONLY = "RESEARCH_ONLY"
    ENSEMBLE_READY = "ENSEMBLE_READY"
    PAPER_CANDIDATE = "PAPER_CANDIDATE"
    GAP = "GAP"
    REJECTED = "REJECTED"


class StrategyEnsembleAlphaGapCategory(StrEnum):
    ENSEMBLE_REPORT_GENERATED = "ENSEMBLE_REPORT_GENERATED"
    MIN_ALPHA_COUNT_NOT_MET = "MIN_ALPHA_COUNT_NOT_MET"
    MIN_STRATEGY_FAMILY_COUNT_NOT_MET = "MIN_STRATEGY_FAMILY_COUNT_NOT_MET"
    MISSING_V73_PROMOTION_REF = "MISSING_V73_PROMOTION_REF"
    BLOCKED_ALPHA_DEPENDENCY = "BLOCKED_ALPHA_DEPENDENCY"
    HIGH_ALPHA_CORRELATION = "HIGH_ALPHA_CORRELATION"
    HIGH_DRAWDOWN_CO_MOVEMENT = "HIGH_DRAWDOWN_CO_MOVEMENT"
    EXCESSIVE_FAMILY_CONCENTRATION = "EXCESSIVE_FAMILY_CONCENTRATION"
    EXCESSIVE_SINGLE_ALPHA_CONCENTRATION = "EXCESSIVE_SINGLE_ALPHA_CONCENTRATION"
    MISSING_REGIME_COVERAGE = "MISSING_REGIME_COVERAGE"
    DUPLICATE_SIGNAL_DETECTED = "DUPLICATE_SIGNAL_DETECTED"
    REMOTE_SOURCE_NOT_ALLOWED = "REMOTE_SOURCE_NOT_ALLOWED"
    NETWORK_PATH_NOT_ALLOWED = "NETWORK_PATH_NOT_ALLOWED"
    ORDER_PATH_NOT_ALLOWED = "ORDER_PATH_NOT_ALLOWED"
    LIVE_PROD_NOT_ALLOWED = "LIVE_PROD_NOT_ALLOWED"
    PARQUET_NOT_ALLOWED = "PARQUET_NOT_ALLOWED"


class StrategyEnsembleAlphaGapEntry(StrictModel):
    gap_id: str = Field(..., min_length=1)
    gap_category: StrategyEnsembleAlphaGapCategory
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


class AlphaCandidate(StrictModel):
    alpha_id: str = Field(..., min_length=1)
    strategy_family: StrategyFamily
    feature_set_id: str = Field(..., min_length=1)
    signal_source: str = Field(..., min_length=1)
    horizon: str = Field(..., min_length=1)
    market: str = Field(..., min_length=1)
    expected_holding_period: str = Field(..., min_length=1)
    training_promotion_ref: str | None = None
    training_promotion_decision: str | None = None
    robustness_ref: str | None = None
    robustness_decision: str | None = None
    paper_candidate_eligibility_ref: str | None = None

    @field_validator("alpha_id", "feature_set_id", mode="before")
    @classmethod
    def normalize_ids(cls, value):
        return _upper_required(value, "id")

    @field_validator(
        "signal_source",
        "horizon",
        "market",
        "expected_holding_period",
        "training_promotion_decision",
        "robustness_decision",
        mode="before",
    )
    @classmethod
    def normalize_optional_upper(cls, value):
        if value is None:
            return None
        return _upper_required(value, "field")

    @field_validator(
        "training_promotion_ref",
        "robustness_ref",
        "paper_candidate_eligibility_ref",
        mode="before",
    )
    @classmethod
    def normalize_optional(cls, value):
        if value is None:
            return None
        cleaned = str(value).strip()
        return cleaned or None


class AlphaAllocation(StrictModel):
    alpha_id: str = Field(..., min_length=1)
    proposed_weight: float = Field(..., gt=0, le=1)

    @field_validator("alpha_id", mode="before")
    @classmethod
    def normalize_id(cls, value):
        return _upper_required(value, "alpha_id")


class AlphaPortfolio(StrictModel):
    portfolio_id: str = Field(..., min_length=1)
    rebalance_policy: str = Field(..., min_length=1)
    risk_budget_policy: str = Field(..., min_length=1)
    min_alpha_count: int = Field(default=2, ge=1)
    min_strategy_family_count: int = Field(default=2, ge=1)
    max_family_concentration: float = Field(default=0.50, gt=0, le=1)
    max_single_alpha_concentration: float = Field(default=0.40, gt=0, le=1)
    allocations: list[AlphaAllocation] = Field(default_factory=list)

    @field_validator("portfolio_id", "rebalance_policy", "risk_budget_policy", mode="before")
    @classmethod
    def normalize_upper(cls, value):
        return _upper_required(value, "field")

    @model_validator(mode="after")
    def validate_allocations(self):
        if not self.allocations:
            raise ValueError("allocations must not be empty")
        alpha_ids = [allocation.alpha_id for allocation in self.allocations]
        if len(alpha_ids) != len(set(alpha_ids)):
            raise ValueError("allocations must not contain duplicate alpha ids")
        weight_sum = sum(allocation.proposed_weight for allocation in self.allocations)
        if not 0.99 <= weight_sum <= 1.01:
            raise ValueError("allocation weights must sum to 1.0")
        return self


class CorrelationMatrixSummary(StrictModel):
    max_pair_correlation: float = Field(default=0, ge=0, le=1)
    high_correlation_pairs: list[list[str]] = Field(default_factory=list)


class DrawdownSummary(StrictModel):
    max_drawdown_co_movement: float = Field(default=0, ge=0, le=1)
    high_drawdown_pairs: list[list[str]] = Field(default_factory=list)


class RegimeOverlapSummary(StrictModel):
    regime_coverage_complete: bool = False
    overlap_ratio: float = Field(default=0, ge=0, le=1)
    covered_regimes: list[str] = Field(default_factory=list)

    @field_validator("covered_regimes", mode="before")
    @classmethod
    def normalize_covered_regimes(cls, value):
        return _normalize_list(value, "covered_regimes", upper=True)


class AlphaCandidateReport(StrictModel):
    report_id: str = Field(..., min_length=1)
    alpha_count: int = Field(default=0, ge=0)
    strategy_family_count: int = Field(default=0, ge=0)
    promotion_refs_complete: bool = False
    blocked_dependency_count: int = Field(default=0, ge=0)
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
    no_cloud_llm: bool = True
    no_local_llm_runtime: bool = True

    @field_validator("report_id", mode="before")
    @classmethod
    def normalize_id(cls, value):
        return _upper_required(value, "report_id")

    @model_validator(mode="after")
    def validate_report(self):
        return _validate_safety_flags(self, "alpha candidate report")


class StrategyFamilyDiversificationReport(StrictModel):
    report_id: str = Field(..., min_length=1)
    alpha_count: int = Field(default=0, ge=0)
    strategy_family_count: int = Field(default=0, ge=0)
    minimum_alpha_count_met: bool = False
    minimum_family_count_met: bool = False
    duplicate_signal_detected: bool = False
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
    no_cloud_llm: bool = True
    no_local_llm_runtime: bool = True

    @field_validator("report_id", mode="before")
    @classmethod
    def normalize_id(cls, value):
        return _upper_required(value, "report_id")

    @model_validator(mode="after")
    def validate_report(self):
        return _validate_safety_flags(self, "strategy family diversification report")


class AlphaCorrelationRiskReport(StrictModel):
    report_id: str = Field(..., min_length=1)
    max_pair_correlation: float = Field(default=0, ge=0, le=1)
    high_alpha_correlation_flagged: bool = False
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
    no_cloud_llm: bool = True
    no_local_llm_runtime: bool = True

    @field_validator("report_id", mode="before")
    @classmethod
    def normalize_id(cls, value):
        return _upper_required(value, "report_id")

    @model_validator(mode="after")
    def validate_report(self):
        return _validate_safety_flags(self, "alpha correlation risk report")


class DrawdownCoMovementReport(StrictModel):
    report_id: str = Field(..., min_length=1)
    max_drawdown_co_movement: float = Field(default=0, ge=0, le=1)
    high_drawdown_co_movement_flagged: bool = False
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
    no_cloud_llm: bool = True
    no_local_llm_runtime: bool = True

    @field_validator("report_id", mode="before")
    @classmethod
    def normalize_id(cls, value):
        return _upper_required(value, "report_id")

    @model_validator(mode="after")
    def validate_report(self):
        return _validate_safety_flags(self, "drawdown co movement report")


class RegimeOverlapReport(StrictModel):
    report_id: str = Field(..., min_length=1)
    regime_coverage_complete: bool = False
    overlap_ratio: float = Field(default=0, ge=0, le=1)
    covered_regime_count: int = Field(default=0, ge=0)
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
    no_cloud_llm: bool = True
    no_local_llm_runtime: bool = True

    @field_validator("report_id", mode="before")
    @classmethod
    def normalize_id(cls, value):
        return _upper_required(value, "report_id")

    @model_validator(mode="after")
    def validate_report(self):
        return _validate_safety_flags(self, "regime overlap report")


class AlphaPortfolioConcentrationReport(StrictModel):
    report_id: str = Field(..., min_length=1)
    max_family_weight: float = Field(default=0, ge=0, le=1)
    max_single_alpha_weight: float = Field(default=0, ge=0, le=1)
    family_concentration_blocked: bool = False
    single_alpha_concentration_blocked: bool = False
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
    no_cloud_llm: bool = True
    no_local_llm_runtime: bool = True

    @field_validator("report_id", mode="before")
    @classmethod
    def normalize_id(cls, value):
        return _upper_required(value, "report_id")

    @model_validator(mode="after")
    def validate_report(self):
        return _validate_safety_flags(self, "alpha portfolio concentration report")


class EnsemblePromotionReadinessReport(StrictModel):
    report_id: str = Field(..., min_length=1)
    decision: EnsemblePromotionDecision
    decision_reason: str = Field(..., min_length=1)
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
    no_cloud_llm: bool = True
    no_local_llm_runtime: bool = True

    @field_validator("report_id", mode="before")
    @classmethod
    def normalize_id(cls, value):
        return _upper_required(value, "report_id")

    @field_validator("decision_reason", mode="before")
    @classmethod
    def normalize_reason(cls, value):
        return _string_required(value, "decision_reason")

    @model_validator(mode="after")
    def validate_report(self):
        return _validate_safety_flags(self, "ensemble promotion readiness report")


class StrategyEnsembleAlphaSafetyReport(StrictModel):
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
    no_cloud_llm: bool = True
    no_local_llm_runtime: bool = True

    @field_validator("safety_report_id", mode="before")
    @classmethod
    def normalize_id(cls, value):
        return _upper_required(value, "safety_report_id")

    @field_validator("blocked_capabilities", mode="before")
    @classmethod
    def normalize_blocked(cls, value):
        return _normalize_list(value, "blocked_capabilities", upper=True)

    @model_validator(mode="after")
    def validate_report(self):
        return _validate_safety_flags(self, "strategy ensemble alpha safety report")


class StrategyEnsembleAlphaGapReport(StrictModel):
    gap_report_id: str = Field(..., min_length=1)
    decision: EnsemblePromotionDecision
    gap_entries: list[StrategyEnsembleAlphaGapEntry] = Field(default_factory=list)
    blocking_gap_count: int = Field(default=0, ge=0)
    warning_gap_count: int = Field(default=0, ge=0)
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
    no_cloud_llm: bool = True
    no_local_llm_runtime: bool = True

    @field_validator("gap_report_id", mode="before")
    @classmethod
    def normalize_id(cls, value):
        return _upper_required(value, "gap_report_id")

    @model_validator(mode="after")
    def validate_report(self):
        return _validate_safety_flags(self, "strategy ensemble alpha gap report")


class StrategyEnsembleAlphaAuditRecord(StrictModel):
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
        return _aware(datetime.fromisoformat(value) if isinstance(value, str) else value)

    @field_validator("source_path", mode="before")
    @classmethod
    def normalize_source_path(cls, value):
        return _validate_local_path(value, "source_path")

    @field_validator("operator_context", mode="before")
    @classmethod
    def normalize_context(cls, value):
        return _string_required(value, "operator_context")


class StrategyEnsembleAlphaInput(StrictModel):
    input_id: str = Field(..., min_length=1)
    portfolio: AlphaPortfolio
    alpha_candidates: list[AlphaCandidate] = Field(default_factory=list)
    correlation_matrix_summary: CorrelationMatrixSummary
    drawdown_summary: DrawdownSummary
    regime_overlap_summary: RegimeOverlapSummary
    duplicate_signal_detected: bool = False
    source_manifest_ids: list[str] = Field(default_factory=list)
    audit_records: list[StrategyEnsembleAlphaAuditRecord] = Field(default_factory=list)
    alpha_candidate_report: AlphaCandidateReport | None = None
    strategy_family_diversification_report: StrategyFamilyDiversificationReport | None = None
    alpha_correlation_risk_report: AlphaCorrelationRiskReport | None = None
    drawdown_co_movement_report: DrawdownCoMovementReport | None = None
    regime_overlap_report: RegimeOverlapReport | None = None
    alpha_portfolio_concentration_report: AlphaPortfolioConcentrationReport | None = None
    ensemble_promotion_readiness_report: EnsemblePromotionReadinessReport | None = None
    gap_report: StrategyEnsembleAlphaGapReport | None = None
    safety_report: StrategyEnsembleAlphaSafetyReport

    @field_validator("input_id", mode="before")
    @classmethod
    def normalize_id(cls, value):
        return _upper_required(value, "input_id")

    @field_validator("source_manifest_ids", mode="before")
    @classmethod
    def normalize_manifests(cls, value):
        return _normalize_list(value, "source_manifest_ids", upper=True)

    @model_validator(mode="after")
    def validate_input(self):
        if not self.alpha_candidates:
            raise ValueError("alpha_candidates must not be empty")
        if not self.audit_records:
            raise ValueError("audit_records must not be empty")
        candidate_ids = {candidate.alpha_id for candidate in self.alpha_candidates}
        allocation_ids = {allocation.alpha_id for allocation in self.portfolio.allocations}
        if candidate_ids != allocation_ids:
            raise ValueError("allocations must map exactly to alpha candidates")
        return self
