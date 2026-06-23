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


class AllocationPolicyPromotionDecision(StrEnum):
    BLOCKED = "BLOCKED"
    RESEARCH_ONLY = "RESEARCH_ONLY"
    TRAINED_OFFLINE = "TRAINED_OFFLINE"
    PAPER_CANDIDATE = "PAPER_CANDIDATE"
    GAP = "GAP"
    REJECTED = "REJECTED"


class AllocationPolicyFamily(StrEnum):
    RULE_BASELINE = "RULE_BASELINE"
    LINEAR_SCORER = "LINEAR_SCORER"
    TREE_LIKE_SCORER_PLACEHOLDER = "TREE_LIKE_SCORER_PLACEHOLDER"
    BANDIT_STYLE_OFFLINE_SCORER_PLACEHOLDER = "BANDIT_STYLE_OFFLINE_SCORER_PLACEHOLDER"
    OFFLINE_RL_POLICY_PLACEHOLDER = "OFFLINE_RL_POLICY_PLACEHOLDER"
    ENSEMBLE_POLICY_SCORER = "ENSEMBLE_POLICY_SCORER"


class AllocationPolicyTrainingGapCategory(StrEnum):
    SANDBOX_REPORT_GENERATED = "SANDBOX_REPORT_GENERATED"
    MISSING_V75_TRAINING_READY_DEPENDENCY = "MISSING_V75_TRAINING_READY_DEPENDENCY"
    INVALID_LEAKY_DATASET = "INVALID_LEAKY_DATASET"
    MISSING_WALK_FORWARD_EVIDENCE = "MISSING_WALK_FORWARD_EVIDENCE"
    BLOCKED_PROMOTION_DEPENDENCY = "BLOCKED_PROMOTION_DEPENDENCY"
    BLOCKED_ENSEMBLE_DEPENDENCY = "BLOCKED_ENSEMBLE_DEPENDENCY"
    MISSING_POINT_IN_TIME_EVIDENCE = "MISSING_POINT_IN_TIME_EVIDENCE"
    MISSING_AVAILABLE_AT_EVIDENCE = "MISSING_AVAILABLE_AT_EVIDENCE"
    MISSING_LEAKAGE_EVIDENCE = "MISSING_LEAKAGE_EVIDENCE"
    UNSTABLE_FOLD_PERFORMANCE = "UNSTABLE_FOLD_PERFORMANCE"
    EXCESSIVE_TURNOVER_SLIPPAGE = "EXCESSIVE_TURNOVER_SLIPPAGE"
    EXCESSIVE_DRAWDOWN = "EXCESSIVE_DRAWDOWN"
    REMOTE_SOURCE_NOT_ALLOWED = "REMOTE_SOURCE_NOT_ALLOWED"
    NETWORK_PATH_NOT_ALLOWED = "NETWORK_PATH_NOT_ALLOWED"
    ORDER_PATH_NOT_ALLOWED = "ORDER_PATH_NOT_ALLOWED"
    LIVE_PROD_NOT_ALLOWED = "LIVE_PROD_NOT_ALLOWED"
    PARQUET_NOT_ALLOWED = "PARQUET_NOT_ALLOWED"


class AllocationPolicyTrainingGapEntry(StrictModel):
    gap_id: str = Field(..., min_length=1)
    gap_category: AllocationPolicyTrainingGapCategory
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


class TrainingInputRefs(StrictModel):
    learning_dataset_readiness_ref: str | None = None
    learning_dataset_readiness_decision: str | None = None
    regime_feature_snapshot_refs: list[str] = Field(default_factory=list)
    action_candidate_refs: list[str] = Field(default_factory=list)
    forward_outcome_label_refs: list[str] = Field(default_factory=list)
    reward_scoring_refs: list[str] = Field(default_factory=list)
    point_in_time_safety_ref: str | None = None
    leakage_guard_ref: str | None = None
    walk_forward_split_ref: str | None = None

    @field_validator("learning_dataset_readiness_ref", "point_in_time_safety_ref", "leakage_guard_ref", "walk_forward_split_ref", mode="before")
    @classmethod
    def normalize_optional_ref(cls, value):
        if value is None:
            return None
        cleaned = str(value).strip()
        return cleaned or None

    @field_validator("learning_dataset_readiness_decision", mode="before")
    @classmethod
    def normalize_optional_decision(cls, value):
        if value is None:
            return None
        return _upper_required(value, "decision")

    @field_validator(
        "regime_feature_snapshot_refs",
        "action_candidate_refs",
        "forward_outcome_label_refs",
        "reward_scoring_refs",
        mode="before",
    )
    @classmethod
    def normalize_refs(cls, value, info):
        return _normalize_list(value, info.field_name, upper=True)


class PolicyArtifactMetadata(StrictModel):
    artifact_id: str = Field(..., min_length=1)
    local_only: bool = True
    offline_only: bool = True
    non_production: bool = True

    @field_validator("artifact_id", mode="before")
    @classmethod
    def normalize_id(cls, value):
        return _upper_required(value, "artifact_id")


class AllocationPolicyCandidateConfig(StrictModel):
    policy_id: str = Field(..., min_length=1)
    policy_family: AllocationPolicyFamily
    action_space: list[str] = Field(default_factory=list)
    regime_feature_set_id: str = Field(..., min_length=1)
    training_dataset_ref: str | None = None
    walk_forward_validation_ref: str | None = None
    strategy_ensemble_ref: str | None = None
    reward_scoring_ref: str | None = None
    random_seed_policy_present: bool = False
    reproducibility_hash: str | None = None
    artifact_metadata: PolicyArtifactMetadata

    @field_validator("policy_id", "regime_feature_set_id", mode="before")
    @classmethod
    def normalize_id(cls, value):
        return _upper_required(value, "field")

    @field_validator("training_dataset_ref", "walk_forward_validation_ref", "strategy_ensemble_ref", "reward_scoring_ref", "reproducibility_hash", mode="before")
    @classmethod
    def normalize_optional_ref(cls, value):
        if value is None:
            return None
        cleaned = str(value).strip()
        return cleaned or None

    @field_validator("action_space", mode="before")
    @classmethod
    def normalize_action_space(cls, value):
        return _normalize_list(value, "action_space", upper=True)


class TrainingEvaluationInput(StrictModel):
    policy_scores_by_action: dict[str, float]
    selected_action_distribution_by_regime: dict[str, dict[str, float]]
    train_score: float
    validation_score: float
    test_score: float
    forward_paper_score: float
    risk_adjusted_score: float
    turnover_score: float = Field(..., ge=0)
    slippage_score: float = Field(..., ge=0)
    max_drawdown_score: float = Field(..., ge=0)
    stable_fold_count: int = Field(..., ge=0)
    fold_count: int = Field(..., ge=1)


class TrainingDependencyStatus(StrictModel):
    walk_forward_validation_decision: str | None = None
    training_promotion_dependency_decision: str | None = None
    ensemble_dependency_decision: str | None = None
    point_in_time_evidence_present: bool = False
    available_at_evidence_present: bool = False
    leakage_evidence_present: bool = False

    @field_validator("walk_forward_validation_decision", "training_promotion_dependency_decision", "ensemble_dependency_decision", mode="before")
    @classmethod
    def normalize_optional_decision(cls, value):
        if value is None:
            return None
        return _upper_required(value, "decision")


class PolicyTrainingSummaryReport(StrictModel):
    report_id: str = Field(..., min_length=1)
    policy_score_deterministic: bool = False
    trained_action_count: int = Field(default=0, ge=0)
    best_action: str | None = None
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
        return _validate_safety_flags(self, "policy training summary report")


class RegimeActionSelectionReport(StrictModel):
    report_id: str = Field(..., min_length=1)
    regime_count: int = Field(default=0, ge=0)
    action_count: int = Field(default=0, ge=0)
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
        return _validate_safety_flags(self, "regime action selection report")


class AllocationPolicyWalkForwardReport(StrictModel):
    report_id: str = Field(..., min_length=1)
    train_score: float
    validation_score: float
    test_score: float
    forward_paper_score: float
    stable_fold_count: int = Field(default=0, ge=0)
    fold_count: int = Field(default=1, ge=1)
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
        return _validate_safety_flags(self, "allocation policy walk forward report")


class AllocationPolicyRiskAdjustedReport(StrictModel):
    report_id: str = Field(..., min_length=1)
    risk_adjusted_score: float
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
        return _validate_safety_flags(self, "allocation policy risk adjusted report")


class AllocationPolicyTurnoverSlippageReport(StrictModel):
    report_id: str = Field(..., min_length=1)
    turnover_score: float = Field(..., ge=0)
    slippage_score: float = Field(..., ge=0)
    excessive_turnover_slippage: bool = False
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
        return _validate_safety_flags(self, "allocation policy turnover slippage report")


class AllocationPolicyDrawdownStabilityReport(StrictModel):
    report_id: str = Field(..., min_length=1)
    max_drawdown_score: float = Field(..., ge=0)
    fold_stability_ratio: float = Field(..., ge=0)
    unstable_folds_flagged: bool = False
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
        return _validate_safety_flags(self, "allocation policy drawdown stability report")


class AllocationPolicyArtifactReport(StrictModel):
    report_id: str = Field(..., min_length=1)
    local_only: bool = True
    offline_only: bool = True
    non_production: bool = True
    read_only: bool = True
    report_only: bool = True
    non_executable: bool = True
    local_file_only: bool = True
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
        return _validate_safety_flags(self, "allocation policy artifact report")


class AllocationPolicyPromotionReadinessReport(StrictModel):
    report_id: str = Field(..., min_length=1)
    decision: AllocationPolicyPromotionDecision
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
        return _validate_safety_flags(self, "allocation policy promotion readiness report")


class AllocationPolicyTrainingSafetyReport(StrictModel):
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
        return _validate_safety_flags(self, "allocation policy training safety report")


class AllocationPolicyTrainingGapReport(StrictModel):
    gap_report_id: str = Field(..., min_length=1)
    decision: AllocationPolicyPromotionDecision
    gap_entries: list[AllocationPolicyTrainingGapEntry] = Field(default_factory=list)
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
        return _validate_safety_flags(self, "allocation policy training gap report")


class AllocationPolicyTrainingAuditRecord(StrictModel):
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


class AllocationPolicyCandidateInput(StrictModel):
    input_id: str = Field(..., min_length=1)
    training_input: TrainingInputRefs
    policy_candidate: AllocationPolicyCandidateConfig
    training_evaluation_input: TrainingEvaluationInput
    dependency_status: TrainingDependencyStatus
    future_outcome_leakage_detected: bool = False
    source_manifest_ids: list[str] = Field(default_factory=list)
    audit_records: list[AllocationPolicyTrainingAuditRecord] = Field(default_factory=list)
    policy_training_summary_report: PolicyTrainingSummaryReport | None = None
    regime_action_selection_report: RegimeActionSelectionReport | None = None
    allocation_policy_walk_forward_report: AllocationPolicyWalkForwardReport | None = None
    allocation_policy_risk_adjusted_report: AllocationPolicyRiskAdjustedReport | None = None
    allocation_policy_turnover_slippage_report: AllocationPolicyTurnoverSlippageReport | None = None
    allocation_policy_drawdown_stability_report: AllocationPolicyDrawdownStabilityReport | None = None
    model_artifact_policy_report: AllocationPolicyArtifactReport | None = None
    policy_promotion_readiness_report: AllocationPolicyPromotionReadinessReport | None = None
    gap_report: AllocationPolicyTrainingGapReport | None = None
    safety_report: AllocationPolicyTrainingSafetyReport

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
        if not self.audit_records:
            raise ValueError("audit_records must not be empty")
        return self
