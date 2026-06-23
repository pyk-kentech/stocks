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


class AllocationActionType(StrEnum):
    KEEP_LONG = "KEEP_LONG"
    REDUCE_SIZE = "REDUCE_SIZE"
    ROTATE_DEFENSIVE = "ROTATE_DEFENSIVE"
    ROTATE_SECTOR = "ROTATE_SECTOR"
    CASH_CONTROL = "CASH_CONTROL"
    INDEX_HEDGE = "INDEX_HEDGE"
    INVERSE_CANDIDATE = "INVERSE_CANDIDATE"
    WATCH_ONLY = "WATCH_ONLY"
    BLOCK = "BLOCK"


class LearningDatasetReadinessDecision(StrEnum):
    BLOCKED = "BLOCKED"
    RESEARCH_READY = "RESEARCH_READY"
    TRAINING_READY = "TRAINING_READY"
    GAP = "GAP"
    REJECTED = "REJECTED"


class RegimeAllocationLearningGapCategory(StrEnum):
    DATASET_REPORT_GENERATED = "DATASET_REPORT_GENERATED"
    MISSING_AVAILABLE_AT = "MISSING_AVAILABLE_AT"
    FUTURE_REGIME_EVENT_LEAKAGE = "FUTURE_REGIME_EVENT_LEAKAGE"
    FUTURE_OUTCOME_LEAKAGE = "FUTURE_OUTCOME_LEAKAGE"
    CURRENT_SURVIVORS_ONLY_DEPENDENCY = "CURRENT_SURVIVORS_ONLY_DEPENDENCY"
    MISSING_POINT_IN_TIME_GATE = "MISSING_POINT_IN_TIME_GATE"
    MISSING_WALK_FORWARD_EVIDENCE = "MISSING_WALK_FORWARD_EVIDENCE"
    MISSING_ENSEMBLE_REFS = "MISSING_ENSEMBLE_REFS"
    INVERSE_POLICY_EVIDENCE_MISSING = "INVERSE_POLICY_EVIDENCE_MISSING"
    MAX_ALLOCATION_MULTIPLIER_EXCEEDED = "MAX_ALLOCATION_MULTIPLIER_EXCEEDED"
    HEDGE_INVERSE_EXECUTION_FLAG_DETECTED = "HEDGE_INVERSE_EXECUTION_FLAG_DETECTED"
    REMOTE_SOURCE_NOT_ALLOWED = "REMOTE_SOURCE_NOT_ALLOWED"
    NETWORK_PATH_NOT_ALLOWED = "NETWORK_PATH_NOT_ALLOWED"
    ORDER_PATH_NOT_ALLOWED = "ORDER_PATH_NOT_ALLOWED"
    LIVE_PROD_NOT_ALLOWED = "LIVE_PROD_NOT_ALLOWED"
    PARQUET_NOT_ALLOWED = "PARQUET_NOT_ALLOWED"


class RegimeAllocationLearningGapEntry(StrictModel):
    gap_id: str = Field(..., min_length=1)
    gap_category: RegimeAllocationLearningGapCategory
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


class DependencyStatus(StrictModel):
    point_in_time_dataset_decision: str | None = None
    walk_forward_validation_decision: str | None = None
    ensemble_promotion_refs_present: bool = False
    current_survivors_only_dependency: bool = False

    @field_validator("point_in_time_dataset_decision", "walk_forward_validation_decision", mode="before")
    @classmethod
    def normalize_optional_decision(cls, value):
        if value is None:
            return None
        return _upper_required(value, "decision")


class RegimeFeatureSnapshot(StrictModel):
    snapshot_id: str = Field(..., min_length=1)
    market: str = Field(..., min_length=1)
    trading_timestamp: datetime
    available_at: datetime | None = None
    index_trend: str = Field(..., min_length=1)
    realized_volatility_bucket: str = Field(..., min_length=1)
    drawdown_bucket: str = Field(..., min_length=1)
    fx_regime: str = Field(..., min_length=1)
    rate_liquidity_regime: str = Field(..., min_length=1)
    sector_breadth: str = Field(..., min_length=1)
    macro_event_pressure: str = Field(..., min_length=1)
    risk_state: str = Field(..., min_length=1)

    @field_validator(
        "snapshot_id",
        "market",
        "index_trend",
        "realized_volatility_bucket",
        "drawdown_bucket",
        "fx_regime",
        "rate_liquidity_regime",
        "sector_breadth",
        "macro_event_pressure",
        "risk_state",
        mode="before",
    )
    @classmethod
    def normalize_upper(cls, value):
        return _upper_required(value, "field")

    @field_validator("trading_timestamp", "available_at", mode="before")
    @classmethod
    def normalize_dt(cls, value):
        if value is None:
            return None
        return _aware(datetime.fromisoformat(value) if isinstance(value, str) else value)


class ActionCandidate(StrictModel):
    action_type: AllocationActionType
    target_strategy_family_or_instrument_class: str = Field(..., min_length=1)
    max_allocation_multiplier: float = Field(..., gt=0, le=1)
    expected_holding_period_constraint: str = Field(..., min_length=1)
    liquidity_evidence_ref: str | None = None
    eligibility_ref: str | None = None
    risk_note: str = Field(..., min_length=1)
    no_execution: bool = True
    instrument_eligibility_ref: str | None = None
    leverage_flag: bool = False
    daily_reset_warning: bool = False
    max_allocation_cap: float | None = Field(default=None, gt=0, le=1)
    short_holding_period_warning: bool = False
    tracking_error_basis_risk_note: str | None = None

    @field_validator(
        "target_strategy_family_or_instrument_class",
        "expected_holding_period_constraint",
        "risk_note",
        "tracking_error_basis_risk_note",
        mode="before",
    )
    @classmethod
    def normalize_strings(cls, value):
        if value is None:
            return None
        return _string_required(value, "field")

    @field_validator("liquidity_evidence_ref", "eligibility_ref", "instrument_eligibility_ref", mode="before")
    @classmethod
    def normalize_optional_refs(cls, value):
        if value is None:
            return None
        cleaned = str(value).strip()
        return cleaned or None

    @model_validator(mode="after")
    def validate_inverse_policy(self):
        if self.action_type in {AllocationActionType.INDEX_HEDGE, AllocationActionType.INVERSE_CANDIDATE}:
            if not self.no_execution:
                raise ValueError("inverse or hedge candidates must remain report-only")
        return self


class ForwardOutcomeLabel(StrictModel):
    label_id: str = Field(..., min_length=1)
    forward_return: float
    forward_drawdown: float = Field(..., ge=0)
    volatility: float = Field(..., ge=0)
    turnover: float = Field(..., ge=0)
    slippage_estimate_ref: str | None = None
    risk_adjusted_score: float
    benchmark_relative_score: float
    action_label_horizon: str = Field(..., min_length=1)
    available_at_safe_label_boundary: bool = False

    @field_validator("label_id", "action_label_horizon", mode="before")
    @classmethod
    def normalize_upper(cls, value):
        return _upper_required(value, "field")

    @field_validator("slippage_estimate_ref", mode="before")
    @classmethod
    def normalize_optional_ref(cls, value):
        if value is None:
            return None
        cleaned = str(value).strip()
        return cleaned or None


class RewardScoringPolicy(StrictModel):
    risk_adjusted_return: float
    max_drawdown_penalty: float = Field(..., ge=0)
    turnover_penalty: float = Field(..., ge=0)
    volatility_penalty: float = Field(..., ge=0)
    benchmark_relative_performance: float
    tail_risk_penalty: float = Field(..., ge=0)
    action_feasibility_penalty: float = Field(..., ge=0)


class RegimeFeatureReport(StrictModel):
    report_id: str = Field(..., min_length=1)
    available_at_present: bool = False
    risk_state: str = Field(..., min_length=1)
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

    @field_validator("report_id", "risk_state", mode="before")
    @classmethod
    def normalize_upper(cls, value):
        return _upper_required(value, "field")

    @model_validator(mode="after")
    def validate_report(self):
        return _validate_safety_flags(self, "regime feature report")


class ActionCandidateReport(StrictModel):
    report_id: str = Field(..., min_length=1)
    action_candidate_count: int = Field(default=0, ge=0)
    inverse_or_hedge_candidate_count: int = Field(default=0, ge=0)
    max_allocation_multiplier_capped: bool = False
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
        return _validate_safety_flags(self, "action candidate report")


class HedgeInverseEligibilityReport(StrictModel):
    report_id: str = Field(..., min_length=1)
    inverse_or_hedge_candidates_present: bool = False
    full_policy_evidence_present: bool = False
    report_only: bool = True
    non_executable: bool = True
    read_only: bool = True
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
        return _validate_safety_flags(self, "hedge inverse eligibility report")


class ForwardOutcomeLabelReport(StrictModel):
    report_id: str = Field(..., min_length=1)
    available_at_safe_label_boundary: bool = False
    forward_label_present: bool = False
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
        return _validate_safety_flags(self, "forward outcome label report")


class AllocationRewardScoringReport(StrictModel):
    report_id: str = Field(..., min_length=1)
    risk_adjusted_return: float
    max_drawdown_penalty: float = Field(..., ge=0)
    turnover_penalty: float = Field(..., ge=0)
    volatility_penalty: float = Field(..., ge=0)
    benchmark_relative_performance: float
    tail_risk_penalty: float = Field(..., ge=0)
    action_feasibility_penalty: float = Field(..., ge=0)
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
        return _validate_safety_flags(self, "allocation reward scoring report")


class RegimeAllocationLeakageReport(StrictModel):
    report_id: str = Field(..., min_length=1)
    regime_event_leakage_detected: bool = False
    future_outcome_leakage_detected: bool = False
    current_survivors_only_dependency: bool = False
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
        return _validate_safety_flags(self, "regime allocation leakage report")


class LearningDatasetReadinessReport(StrictModel):
    report_id: str = Field(..., min_length=1)
    decision: LearningDatasetReadinessDecision
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

    @field_validator("report_id", "decision_reason", mode="before")
    @classmethod
    def normalize_fields(cls, value):
        return _string_required(value, "field") if not isinstance(value, LearningDatasetReadinessDecision) else value

    @model_validator(mode="after")
    def validate_report(self):
        return _validate_safety_flags(self, "learning dataset readiness report")


class RegimeAllocationLearningSafetyReport(StrictModel):
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
        return _validate_safety_flags(self, "regime allocation learning safety report")


class RegimeAllocationLearningGapReport(StrictModel):
    gap_report_id: str = Field(..., min_length=1)
    decision: LearningDatasetReadinessDecision
    gap_entries: list[RegimeAllocationLearningGapEntry] = Field(default_factory=list)
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
        return _validate_safety_flags(self, "regime allocation learning gap report")


class RegimeAllocationLearningAuditRecord(StrictModel):
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


class RegimeAllocationLearningInput(StrictModel):
    input_id: str = Field(..., min_length=1)
    dependency_status: DependencyStatus
    regime_feature_snapshot: RegimeFeatureSnapshot
    action_candidates: list[ActionCandidate] = Field(default_factory=list)
    forward_outcome_label: ForwardOutcomeLabel
    reward_scoring_policy: RewardScoringPolicy
    regime_event_leakage_detected: bool = False
    future_outcome_leakage_detected: bool = False
    source_manifest_ids: list[str] = Field(default_factory=list)
    audit_records: list[RegimeAllocationLearningAuditRecord] = Field(default_factory=list)
    regime_feature_report: RegimeFeatureReport | None = None
    action_candidate_report: ActionCandidateReport | None = None
    hedge_inverse_eligibility_report: HedgeInverseEligibilityReport | None = None
    forward_outcome_label_report: ForwardOutcomeLabelReport | None = None
    allocation_reward_scoring_report: AllocationRewardScoringReport | None = None
    regime_allocation_leakage_report: RegimeAllocationLeakageReport | None = None
    learning_dataset_readiness_report: LearningDatasetReadinessReport | None = None
    gap_report: RegimeAllocationLearningGapReport | None = None
    safety_report: RegimeAllocationLearningSafetyReport

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
        if not self.action_candidates:
            raise ValueError("action_candidates must not be empty")
        if not self.audit_records:
            raise ValueError("audit_records must not be empty")
        return self
