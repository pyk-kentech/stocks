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


def _normalize_str_list(value, field_name: str, *, upper: bool = False) -> list[str]:
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


class WalkForwardMode(StrEnum):
    ANCHORED = "ANCHORED"
    ROLLING = "ROLLING"


class WalkForwardValidationDecision(StrEnum):
    BLOCKED = "BLOCKED"
    RESEARCH_ONLY = "RESEARCH_ONLY"
    VALIDATION_READY = "VALIDATION_READY"
    PAPER_READY = "PAPER_READY"
    GAP = "GAP"
    REJECTED = "REJECTED"


class WalkForwardValidationGapCategory(StrEnum):
    WALK_FORWARD_REPORT_GENERATED = "WALK_FORWARD_REPORT_GENERATED"
    OVERLAPPING_WINDOWS_DETECTED = "OVERLAPPING_WINDOWS_DETECTED"
    FINAL_TEST_REPEATED_TUNING = "FINAL_TEST_REPEATED_TUNING"
    EXCESSIVE_PARAMETER_SEARCH = "EXCESSIVE_PARAMETER_SEARCH"
    UNREGISTERED_PARAMETER_MUTATION = "UNREGISTERED_PARAMETER_MUTATION"
    SINGLE_PERIOD_ONLY_SUCCESS = "SINGLE_PERIOD_ONLY_SUCCESS"
    MULTI_FOLD_STABILITY_MISSING = "MULTI_FOLD_STABILITY_MISSING"
    EXPERIMENT_LINEAGE_MISSING = "EXPERIMENT_LINEAGE_MISSING"
    FORWARD_PAPER_WINDOW_MISSING = "FORWARD_PAPER_WINDOW_MISSING"
    FINAL_TEST_CONTAMINATION_DETECTED = "FINAL_TEST_CONTAMINATION_DETECTED"
    HIDDEN_FAILED_TRIAL_PRESSURE = "HIDDEN_FAILED_TRIAL_PRESSURE"
    TEST_PERIOD_CHERRY_PICKING = "TEST_PERIOD_CHERRY_PICKING"
    REGIME_BUCKET_REFERENCE_MISSING = "REGIME_BUCKET_REFERENCE_MISSING"
    REMOTE_SOURCE_NOT_ALLOWED = "REMOTE_SOURCE_NOT_ALLOWED"
    NETWORK_PATH_NOT_ALLOWED = "NETWORK_PATH_NOT_ALLOWED"
    ORDER_PATH_NOT_ALLOWED = "ORDER_PATH_NOT_ALLOWED"
    LIVE_PROD_NOT_ALLOWED = "LIVE_PROD_NOT_ALLOWED"
    PARQUET_NOT_ALLOWED = "PARQUET_NOT_ALLOWED"


class WalkForwardValidationGapEntry(StrictModel):
    gap_id: str = Field(..., min_length=1)
    gap_category: WalkForwardValidationGapCategory
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


class TimeWindow(StrictModel):
    start_at: datetime
    end_at: datetime

    @field_validator("start_at", "end_at", mode="before")
    @classmethod
    def normalize_dt(cls, value):
        return _aware(datetime.fromisoformat(value) if isinstance(value, str) else value)

    @model_validator(mode="after")
    def validate_window(self):
        if self.end_at <= self.start_at:
            raise ValueError("time window end_at must be after start_at")
        return self


class WalkForwardSplit(StrictModel):
    split_id: str = Field(..., min_length=1)
    mode: WalkForwardMode
    train_window: TimeWindow
    validation_window: TimeWindow
    test_window: TimeWindow
    forward_paper_window: TimeWindow | None = None

    @field_validator("split_id", mode="before")
    @classmethod
    def normalize_id(cls, value):
        return _upper_required(value, "split_id")


class ExperimentLineage(StrictModel):
    experiment_id: str = Field(..., min_length=1)
    dataset_id: str = Field(..., min_length=1)
    feature_set_id: str = Field(..., min_length=1)
    strategy_id: str = Field(..., min_length=1)
    parameter_set_id: str = Field(..., min_length=1)
    search_run_id: str = Field(..., min_length=1)
    parent_experiment_refs: list[str] = Field(default_factory=list)
    final_test_access_count: int = Field(default=0, ge=0)
    validation_reuse_count: int = Field(default=0, ge=0)
    registered_parameter_mutations: list[str] = Field(default_factory=list)
    unregistered_parameter_mutation_detected: bool = False

    @field_validator(
        "experiment_id",
        "dataset_id",
        "feature_set_id",
        "strategy_id",
        "parameter_set_id",
        "search_run_id",
        mode="before",
    )
    @classmethod
    def normalize_ids(cls, value):
        return _upper_required(value, "lineage_id")

    @field_validator("parent_experiment_refs", "registered_parameter_mutations", mode="before")
    @classmethod
    def normalize_lists(cls, value, info):
        return _normalize_str_list(value, info.field_name, upper=True)


class StabilityEvidence(StrictModel):
    fold_count: int = Field(default=0, ge=0)
    stable_fold_count: int = Field(default=0, ge=0)
    drawdown_stable: bool = False
    hit_rate_stable: bool = False
    return_stable: bool = False
    risk_adjusted_metric_stable: bool = False
    single_period_only_success: bool = False
    regime_bucket_reference_present: bool = False


class WalkForwardValidationConfig(StrictModel):
    config_id: str = Field(..., min_length=1)
    fixture_format: str = Field(default="json", min_length=1)
    max_parameter_search_count: int = Field(default=20, ge=0)
    max_hidden_failed_trials: int = Field(default=10, ge=0)
    paper_ready_requires_forward_window: bool = True
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

    @field_validator("config_id", mode="before")
    @classmethod
    def normalize_id(cls, value):
        return _upper_required(value, "config_id")

    @field_validator("fixture_format", mode="before")
    @classmethod
    def normalize_fixture_format(cls, value):
        cleaned = _string_required(value, "fixture_format").lower()
        if cleaned != "json":
            raise ValueError("fixture_format must remain json")
        return cleaned

    @model_validator(mode="after")
    def validate_config(self):
        return _validate_safety_flags(self, "walk forward validation config")


class WalkForwardValidationSafetyReport(StrictModel):
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
        return _normalize_str_list(value, "blocked_capabilities", upper=True)

    @model_validator(mode="after")
    def validate_report(self):
        return _validate_safety_flags(self, "walk forward validation safety report")


class WalkForwardValidationGapReport(StrictModel):
    gap_report_id: str = Field(..., min_length=1)
    decision: WalkForwardValidationDecision
    gap_entries: list[WalkForwardValidationGapEntry] = Field(default_factory=list)
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
        return _validate_safety_flags(self, "walk forward validation gap report")


class WalkForwardValidationAuditRecord(StrictModel):
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


class WalkForwardSplitReport(StrictModel):
    report_id: str = Field(..., min_length=1)
    clean_non_overlapping_split: bool = False
    mode: WalkForwardMode
    forward_paper_window_present: bool = False
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
        return _validate_safety_flags(self, "walk forward split report")


class DataSnoopingReport(StrictModel):
    report_id: str = Field(..., min_length=1)
    excessive_parameter_search_flagged: bool = False
    hidden_failed_trial_pressure_flagged: bool = False
    test_period_cherry_picking_flagged: bool = False
    unregistered_parameter_mutation_flagged: bool = False
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
        return _validate_safety_flags(self, "data snooping report")


class ExperimentLineageReport(StrictModel):
    report_id: str = Field(..., min_length=1)
    lineage_present: bool = False
    final_test_access_count: int = Field(default=0, ge=0)
    validation_reuse_count: int = Field(default=0, ge=0)
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
        return _validate_safety_flags(self, "experiment lineage report")


class ParameterSearchPressureReport(StrictModel):
    report_id: str = Field(..., min_length=1)
    parameter_search_count: int = Field(default=0, ge=0)
    hidden_failed_trial_count: int = Field(default=0, ge=0)
    excessive_parameter_search_flagged: bool = False
    hidden_failed_trial_pressure_flagged: bool = False
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
        return _validate_safety_flags(self, "parameter search pressure report")


class FinalTestContaminationReport(StrictModel):
    report_id: str = Field(..., min_length=1)
    repeated_final_test_tuning_flagged: bool = False
    final_test_contamination_detected: bool = False
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
        return _validate_safety_flags(self, "final test contamination report")


class StabilityReport(StrictModel):
    report_id: str = Field(..., min_length=1)
    multiple_stable_folds_present: bool = False
    single_period_only_success_flagged: bool = False
    drawdown_stable: bool = False
    hit_rate_stable: bool = False
    return_stable: bool = False
    risk_adjusted_metric_stable: bool = False
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
        return _validate_safety_flags(self, "stability report")


class PromotionReadinessReport(StrictModel):
    report_id: str = Field(..., min_length=1)
    decision: WalkForwardValidationDecision
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
        return _validate_safety_flags(self, "promotion readiness report")


class WalkForwardValidationInput(StrictModel):
    input_id: str = Field(..., min_length=1)
    config: WalkForwardValidationConfig
    split: WalkForwardSplit
    experiment_lineage: ExperimentLineage | None = None
    stability_evidence: StabilityEvidence
    parameter_search_count: int = Field(default=0, ge=0)
    hidden_failed_trial_count: int = Field(default=0, ge=0)
    test_period_cherry_picking_detected: bool = False
    regime_bucket_reference_present: bool = False
    source_manifest_ids: list[str] = Field(default_factory=list)
    audit_records: list[WalkForwardValidationAuditRecord] = Field(default_factory=list)
    walk_forward_split_report: WalkForwardSplitReport | None = None
    data_snooping_report: DataSnoopingReport | None = None
    experiment_lineage_report: ExperimentLineageReport | None = None
    parameter_search_pressure_report: ParameterSearchPressureReport | None = None
    final_test_contamination_report: FinalTestContaminationReport | None = None
    stability_report: StabilityReport | None = None
    promotion_readiness_report: PromotionReadinessReport | None = None
    gap_report: WalkForwardValidationGapReport | None = None
    safety_report: WalkForwardValidationSafetyReport

    @field_validator("input_id", mode="before")
    @classmethod
    def normalize_id(cls, value):
        return _upper_required(value, "input_id")

    @field_validator("source_manifest_ids", mode="before")
    @classmethod
    def normalize_manifests(cls, value):
        return _normalize_str_list(value, "source_manifest_ids", upper=True)

    @model_validator(mode="after")
    def validate_input(self):
        if not self.audit_records:
            raise ValueError("audit_records must not be empty")
        return self
