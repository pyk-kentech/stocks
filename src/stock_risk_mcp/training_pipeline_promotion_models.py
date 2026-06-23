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


class TrainingPipelinePromotionDecision(StrEnum):
    BLOCKED = "BLOCKED"
    RESEARCH_ONLY = "RESEARCH_ONLY"
    TRAINING_READY = "TRAINING_READY"
    PAPER_CANDIDATE = "PAPER_CANDIDATE"
    PROMOTION_GAP = "PROMOTION_GAP"
    REJECTED = "REJECTED"


class TrainingPipelinePromotionGapCategory(StrEnum):
    TRAINING_PROMOTION_REPORT_GENERATED = "TRAINING_PROMOTION_REPORT_GENERATED"
    MISSING_V71_DEPENDENCY = "MISSING_V71_DEPENDENCY"
    MISSING_V72_DEPENDENCY = "MISSING_V72_DEPENDENCY"
    MISSING_V70_DEPENDENCY = "MISSING_V70_DEPENDENCY"
    DATASET_NOT_TRAINING_READY = "DATASET_NOT_TRAINING_READY"
    VALIDATION_NOT_READY = "VALIDATION_NOT_READY"
    ROBUSTNESS_BLOCKED = "ROBUSTNESS_BLOCKED"
    LEAKAGE_DETECTED = "LEAKAGE_DETECTED"
    SNOOPING_DETECTED = "SNOOPING_DETECTED"
    FINAL_TEST_CONTAMINATION_DETECTED = "FINAL_TEST_CONTAMINATION_DETECTED"
    AVAILABLE_AT_DISCIPLINE_MISSING = "AVAILABLE_AT_DISCIPLINE_MISSING"
    LABEL_LEAKAGE_DETECTED = "LABEL_LEAKAGE_DETECTED"
    REPRODUCIBLE_SEED_POLICY_MISSING = "REPRODUCIBLE_SEED_POLICY_MISSING"
    EXPERIMENT_LINEAGE_MISSING = "EXPERIMENT_LINEAGE_MISSING"
    EXCESSIVE_PARAMETER_SEARCH = "EXCESSIVE_PARAMETER_SEARCH"
    ARTIFACT_POLICY_INVALID = "ARTIFACT_POLICY_INVALID"
    REMOTE_SOURCE_NOT_ALLOWED = "REMOTE_SOURCE_NOT_ALLOWED"
    NETWORK_PATH_NOT_ALLOWED = "NETWORK_PATH_NOT_ALLOWED"
    ORDER_PATH_NOT_ALLOWED = "ORDER_PATH_NOT_ALLOWED"
    LIVE_PROD_NOT_ALLOWED = "LIVE_PROD_NOT_ALLOWED"
    PARQUET_NOT_ALLOWED = "PARQUET_NOT_ALLOWED"


class TrainingPipelinePromotionGapEntry(StrictModel):
    gap_id: str = Field(..., min_length=1)
    gap_category: TrainingPipelinePromotionGapCategory
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


class TrainingDatasetEligibility(StrictModel):
    dataset_id: str = Field(..., min_length=1)
    point_in_time_gate_decision: str | None = None
    survivorship_safety_ref: str | None = None
    available_at_discipline_ref: str | None = None
    leakage_audit_ref: str | None = None
    feature_set_id: str = Field(..., min_length=1)
    label_horizon: str = Field(..., min_length=1)
    target_type: str = Field(..., min_length=1)
    train_split_ref: str | None = None
    validation_split_ref: str | None = None
    test_split_ref: str | None = None
    forward_paper_split_ref: str | None = None
    label_leakage_detected: bool = False

    @field_validator("dataset_id", "feature_set_id", mode="before")
    @classmethod
    def normalize_ids(cls, value):
        return _upper_required(value, "id")

    @field_validator("label_horizon", "target_type", mode="before")
    @classmethod
    def normalize_strings(cls, value):
        return _string_required(value, "field")

    @field_validator(
        "point_in_time_gate_decision",
        "survivorship_safety_ref",
        "available_at_discipline_ref",
        "leakage_audit_ref",
        "train_split_ref",
        "validation_split_ref",
        "test_split_ref",
        "forward_paper_split_ref",
        mode="before",
    )
    @classmethod
    def normalize_optional(cls, value):
        if value is None:
            return None
        cleaned = str(value).strip()
        return cleaned or None


class TrainingRunCandidate(StrictModel):
    training_run_id: str = Field(..., min_length=1)
    model_family: str = Field(..., min_length=1)
    hyperparameter_set_id: str = Field(..., min_length=1)
    feature_set_id: str = Field(..., min_length=1)
    dataset_id: str = Field(..., min_length=1)
    experiment_id: str | None = None
    random_seed_policy_present: bool = False
    reproducibility_hash: str | None = None
    training_window_refs: list[str] = Field(default_factory=list)
    validation_window_refs: list[str] = Field(default_factory=list)
    test_window_refs: list[str] = Field(default_factory=list)
    forward_paper_window_refs: list[str] = Field(default_factory=list)

    @field_validator("training_run_id", "model_family", "hyperparameter_set_id", "feature_set_id", "dataset_id", mode="before")
    @classmethod
    def normalize_required(cls, value):
        return _upper_required(value, "field")

    @field_validator("experiment_id", "reproducibility_hash", mode="before")
    @classmethod
    def normalize_optional(cls, value):
        if value is None:
            return None
        cleaned = str(value).strip()
        return cleaned or None

    @field_validator(
        "training_window_refs",
        "validation_window_refs",
        "test_window_refs",
        "forward_paper_window_refs",
        mode="before",
    )
    @classmethod
    def normalize_refs(cls, value, info):
        return _normalize_list(value, info.field_name, upper=True)


class TrainingDependencyReport(StrictModel):
    report_id: str = Field(..., min_length=1)
    v71_dataset_decision: str | None = None
    v72_validation_decision: str | None = None
    v70_robustness_decision: str | None = None
    dependency_complete: bool = False
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

    @field_validator("v71_dataset_decision", "v72_validation_decision", "v70_robustness_decision", mode="before")
    @classmethod
    def normalize_optional_decisions(cls, value):
        if value is None:
            return None
        return _upper_required(value, "decision")

    @model_validator(mode="after")
    def validate_report(self):
        return _validate_safety_flags(self, "training dependency report")


class TrainingEligibilityReport(StrictModel):
    report_id: str = Field(..., min_length=1)
    dataset_training_eligible: bool = False
    available_at_discipline_present: bool = False
    leakage_audit_present: bool = False
    label_leakage_detected: bool = False
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
        return _validate_safety_flags(self, "training eligibility report")


class LeakageOverfitRiskReport(StrictModel):
    report_id: str = Field(..., min_length=1)
    leakage_detected: bool = False
    snooping_detected: bool = False
    final_test_contamination_detected: bool = False
    excessive_parameter_search_flagged: bool = False
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
        return _validate_safety_flags(self, "leakage overfit risk report")


class ReproducibilityReport(StrictModel):
    report_id: str = Field(..., min_length=1)
    random_seed_policy_present: bool = False
    reproducibility_hash_present: bool = False
    experiment_lineage_present: bool = False
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
        return _validate_safety_flags(self, "reproducibility report")


class ModelArtifactPolicyReport(StrictModel):
    report_id: str = Field(..., min_length=1)
    local_offline_only: bool = True
    non_production_only: bool = True
    no_live_inference_deployment: bool = True
    no_order_connection: bool = True
    no_account_connection: bool = True
    metadata_reproducible: bool = False
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
        return _validate_safety_flags(self, "model artifact policy report")


class TrainingPipelinePromotionSafetyReport(StrictModel):
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
        return _validate_safety_flags(self, "training pipeline promotion safety report")


class TrainingPipelinePromotionGapReport(StrictModel):
    gap_report_id: str = Field(..., min_length=1)
    decision: TrainingPipelinePromotionDecision
    gap_entries: list[TrainingPipelinePromotionGapEntry] = Field(default_factory=list)
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
        return _validate_safety_flags(self, "training pipeline promotion gap report")


class TrainingPipelinePromotionAuditRecord(StrictModel):
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


class ModelPromotionReadinessReport(StrictModel):
    report_id: str = Field(..., min_length=1)
    decision: TrainingPipelinePromotionDecision
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
        return _validate_safety_flags(self, "model promotion readiness report")


class TrainingPipelinePromotionInput(StrictModel):
    input_id: str = Field(..., min_length=1)
    dataset_eligibility: TrainingDatasetEligibility
    training_run_candidate: TrainingRunCandidate
    v71_dataset_decision: str | None = None
    v72_validation_decision: str | None = None
    v70_robustness_decision: str | None = None
    excessive_parameter_search_flagged: bool = False
    final_test_contamination_detected: bool = False
    leakage_detected: bool = False
    snooping_detected: bool = False
    model_artifact_metadata_reproducible: bool = False
    config_read_only_flags: dict[str, bool] | None = None
    source_manifest_ids: list[str] = Field(default_factory=list)
    audit_records: list[TrainingPipelinePromotionAuditRecord] = Field(default_factory=list)
    training_eligibility_report: TrainingEligibilityReport | None = None
    dependency_report: TrainingDependencyReport | None = None
    leakage_overfit_risk_report: LeakageOverfitRiskReport | None = None
    reproducibility_report: ReproducibilityReport | None = None
    model_artifact_policy_report: ModelArtifactPolicyReport | None = None
    model_promotion_readiness_report: ModelPromotionReadinessReport | None = None
    gap_report: TrainingPipelinePromotionGapReport | None = None
    safety_report: TrainingPipelinePromotionSafetyReport

    @field_validator("input_id", mode="before")
    @classmethod
    def normalize_id(cls, value):
        return _upper_required(value, "input_id")

    @field_validator("v71_dataset_decision", "v72_validation_decision", "v70_robustness_decision", mode="before")
    @classmethod
    def normalize_optional_decisions(cls, value):
        if value is None:
            return None
        return _upper_required(value, "decision")

    @field_validator("source_manifest_ids", mode="before")
    @classmethod
    def normalize_manifests(cls, value):
        return _normalize_list(value, "source_manifest_ids", upper=True)

    @model_validator(mode="after")
    def validate_input(self):
        if not self.audit_records:
            raise ValueError("audit_records must not be empty")
        return self
