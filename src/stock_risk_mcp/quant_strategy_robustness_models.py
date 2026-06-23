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


def _normalize_id_list(value, field_name: str) -> list[str]:
    if value is None:
        return []
    if isinstance(value, (str, bytes)) or not isinstance(value, list):
        raise ValueError(f"{field_name} must be a list")
    return [_upper_required(item, field_name) for item in value]


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


class QuantStrategyRobustnessDecision(StrEnum):
    BLOCKED = "BLOCKED"
    RESEARCH_READY = "RESEARCH_READY"
    TRAINING_READY = "TRAINING_READY"
    GAP = "GAP"
    REJECTED = "REJECTED"


class QuantStrategyRobustnessGapCategory(StrEnum):
    ROBUSTNESS_REPORT_GENERATED = "ROBUSTNESS_REPORT_GENERATED"
    SURVIVORSHIP_CURRENT_ONLY_TRAINING_CLAIM_BLOCKED = "SURVIVORSHIP_CURRENT_ONLY_TRAINING_CLAIM_BLOCKED"
    SURVIVORSHIP_HISTORICAL_UNIVERSE_MISSING = "SURVIVORSHIP_HISTORICAL_UNIVERSE_MISSING"
    POINT_IN_TIME_AVAILABLE_AT_MISSING = "POINT_IN_TIME_AVAILABLE_AT_MISSING"
    FUTURE_DATA_LEAKAGE_DETECTED = "FUTURE_DATA_LEAKAGE_DETECTED"
    CORPORATE_ACTION_POLICY_MISSING = "CORPORATE_ACTION_POLICY_MISSING"
    DELISTING_POLICY_MISSING = "DELISTING_POLICY_MISSING"
    WALK_FORWARD_POLICY_MISSING = "WALK_FORWARD_POLICY_MISSING"
    FINAL_TEST_RETUNING_DETECTED = "FINAL_TEST_RETUNING_DETECTED"
    EXCESSIVE_PARAMETER_SEARCH = "EXCESSIVE_PARAMETER_SEARCH"
    PERIOD_STABILITY_MISSING = "PERIOD_STABILITY_MISSING"
    STRATEGY_DIVERSIFICATION_TOO_NARROW = "STRATEGY_DIVERSIFICATION_TOO_NARROW"
    STRATEGY_CORRELATION_TOO_HIGH = "STRATEGY_CORRELATION_TOO_HIGH"
    DRAWDOWN_COMOVEMENT_TOO_HIGH = "DRAWDOWN_COMOVEMENT_TOO_HIGH"
    REGIME_BUCKET_EVIDENCE_MISSING = "REGIME_BUCKET_EVIDENCE_MISSING"
    EXPERIMENT_LINEAGE_MISSING = "EXPERIMENT_LINEAGE_MISSING"
    REMOTE_SOURCE_NOT_ALLOWED = "REMOTE_SOURCE_NOT_ALLOWED"
    NETWORK_PATH_NOT_ALLOWED = "NETWORK_PATH_NOT_ALLOWED"
    ORDER_PATH_NOT_ALLOWED = "ORDER_PATH_NOT_ALLOWED"
    LIVE_PROD_NOT_ALLOWED = "LIVE_PROD_NOT_ALLOWED"
    LLM_PATH_NOT_ALLOWED = "LLM_PATH_NOT_ALLOWED"
    PARQUET_NOT_ALLOWED = "PARQUET_NOT_ALLOWED"


class QuantUniverseMode(StrEnum):
    CURRENT_SURVIVORS_ONLY = "CURRENT_SURVIVORS_ONLY"
    POINT_IN_TIME_HISTORICAL = "POINT_IN_TIME_HISTORICAL"


class WalkForwardMode(StrEnum):
    ROLLING = "ROLLING"
    ANCHORED = "ANCHORED"


class QuantStrategyRobustnessGapEntry(StrictModel):
    gap_id: str = Field(..., min_length=1)
    gap_category: QuantStrategyRobustnessGapCategory
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


class QuantStrategySurvivorshipBiasPolicy(StrictModel):
    universe_mode: QuantUniverseMode
    historical_universe_snapshots_required: bool = True
    historical_universe_snapshots_available: bool = False
    delisted_handled: bool = False
    suspended_handled: bool = False
    merged_handled: bool = False
    renamed_handled: bool = False
    index_removed_handled: bool = False


class QuantStrategyPointInTimePolicy(StrictModel):
    available_at_required: bool = True
    price_features_have_available_at: bool = False
    fundamental_features_have_available_at: bool = False
    index_features_have_available_at: bool = False
    macro_features_have_available_at: bool = False
    event_features_have_available_at: bool = False
    future_data_leakage_blocked: bool = True
    corporate_action_policy_present: bool = False
    split_policy_present: bool = False
    dividend_policy_present: bool = False
    symbol_change_policy_present: bool = False
    delisting_policy_present: bool = False


class QuantStrategyWalkForwardPolicy(StrictModel):
    walk_forward_mode: WalkForwardMode
    train_window_count: int = Field(..., ge=1)
    validation_window_count: int = Field(..., ge=1)
    test_window_count: int = Field(..., ge=1)
    forward_paper_window_count: int = Field(..., ge=1)
    repeated_final_test_tuning_count: int = Field(default=0, ge=0)
    parameter_search_count: int = Field(default=0, ge=0)
    max_parameter_search_count: int = Field(default=20, ge=0)
    final_test_period_reused_for_tuning: bool = False
    period_stability_metrics_present: bool = False


class QuantStrategyDiversificationPolicy(StrictModel):
    alpha_candidate_families: list[str] = Field(default_factory=list)
    max_pairwise_strategy_correlation: float = Field(default=0.0, ge=0.0, le=1.0)
    max_drawdown_comovement: float = Field(default=0.0, ge=0.0, le=1.0)

    @field_validator("alpha_candidate_families", mode="before")
    @classmethod
    def normalize_families(cls, value):
        if value is None:
            return []
        if isinstance(value, (str, bytes)) or not isinstance(value, list):
            raise ValueError("alpha_candidate_families must be a list")
        return [_upper_required(item, "alpha family") for item in value]


class QuantStrategyRegimeReadinessPolicy(StrictModel):
    regime_buckets: list[str] = Field(default_factory=list)
    required_bucket_count: int = Field(default=6, ge=1)
    evaluated_bucket_count: int = Field(default=0, ge=0)

    @field_validator("regime_buckets", mode="before")
    @classmethod
    def normalize_regimes(cls, value):
        if value is None:
            return []
        if isinstance(value, (str, bytes)) or not isinstance(value, list):
            raise ValueError("regime_buckets must be a list")
        return [_upper_required(item, "regime bucket") for item in value]


class QuantStrategyRobustnessConfig(StrictModel):
    config_id: str = Field(..., min_length=1)
    fixture_format: str = Field(default="json", min_length=1)
    research_only: bool = True
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
    def normalize_config_id(cls, value):
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
        return _validate_safety_flags(self, "quant strategy robustness config")


class QuantStrategyRobustnessSafetyReport(StrictModel):
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
        return _normalize_id_list(value, "blocked_capabilities")

    @model_validator(mode="after")
    def validate_safety(self):
        return _validate_safety_flags(self, "quant strategy robustness safety report")


class QuantStrategyRobustnessGapReport(StrictModel):
    gap_report_id: str = Field(..., min_length=1)
    decision: QuantStrategyRobustnessDecision
    gap_entries: list[QuantStrategyRobustnessGapEntry] = Field(default_factory=list)
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
    def validate_gap(self):
        return _validate_safety_flags(self, "quant strategy robustness gap report")


class QuantStrategyRobustnessAuditRecord(StrictModel):
    audit_record_id: str = Field(..., min_length=1)
    created_at: datetime
    source_path: str = Field(..., min_length=1)
    operator_context: str = Field(..., min_length=1)
    redaction_applied: bool = True
    contains_secret_material: bool = False
    contains_token_material: bool = False
    contains_account_material: bool = False
    experiment_registry_ref: str | None = None

    @field_validator("audit_record_id", mode="before")
    @classmethod
    def normalize_id(cls, value):
        return _upper_required(value, "audit_record_id")

    @field_validator("created_at", mode="before")
    @classmethod
    def validate_created_at(cls, value):
        return _aware(datetime.fromisoformat(value) if isinstance(value, str) else value)

    @field_validator("source_path", mode="before")
    @classmethod
    def validate_source_path(cls, value):
        return _validate_local_path(value, "source_path")

    @field_validator("operator_context", mode="before")
    @classmethod
    def normalize_operator_context(cls, value):
        return _string_required(value, "operator_context")

    @field_validator("experiment_registry_ref", mode="before")
    @classmethod
    def normalize_registry_ref(cls, value):
        if value is None:
            return None
        return _validate_local_path(value, "experiment_registry_ref")


class QuantStrategyRobustnessReport(StrictModel):
    readiness_report_id: str = Field(..., min_length=1)
    decision: QuantStrategyRobustnessDecision
    decision_reason: str = Field(..., min_length=1)
    current_survivors_only: bool = False
    point_in_time_ready: bool = False
    walk_forward_ready: bool = False
    data_snooping_risk_flagged: bool = False
    diversification_ready: bool = False
    regime_ready: bool = False
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

    @field_validator("readiness_report_id", mode="before")
    @classmethod
    def normalize_id(cls, value):
        return _upper_required(value, "readiness_report_id")

    @field_validator("decision_reason", mode="before")
    @classmethod
    def normalize_reason(cls, value):
        return _string_required(value, "decision_reason")

    @model_validator(mode="after")
    def validate_report(self):
        return _validate_safety_flags(self, "quant strategy robustness report")


class QuantStrategySurvivorshipBiasReport(StrictModel):
    report_id: str = Field(..., min_length=1)
    universe_mode: QuantUniverseMode
    training_grade_allowed: bool = False
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

    @field_validator("report_id", mode="before")
    @classmethod
    def normalize_id(cls, value):
        return _upper_required(value, "report_id")

    @model_validator(mode="after")
    def validate_report(self):
        return _validate_safety_flags(self, "survivorship bias report")


class QuantStrategyPointInTimeLeakageReport(StrictModel):
    report_id: str = Field(..., min_length=1)
    available_at_complete: bool = False
    future_leakage_detected: bool = False
    corporate_action_policy_complete: bool = False
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

    @field_validator("report_id", mode="before")
    @classmethod
    def normalize_id(cls, value):
        return _upper_required(value, "report_id")

    @model_validator(mode="after")
    def validate_report(self):
        return _validate_safety_flags(self, "point in time leakage report")


class QuantStrategyWalkForwardPolicyReport(StrictModel):
    report_id: str = Field(..., min_length=1)
    walk_forward_ready: bool = False
    repeated_final_test_tuning_flagged: bool = False
    excessive_parameter_search_flagged: bool = False
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

    @field_validator("report_id", mode="before")
    @classmethod
    def normalize_id(cls, value):
        return _upper_required(value, "report_id")

    @model_validator(mode="after")
    def validate_report(self):
        return _validate_safety_flags(self, "walk forward policy report")


class QuantStrategyDataSnoopingReport(StrictModel):
    report_id: str = Field(..., min_length=1)
    parameter_search_count: int = Field(default=0, ge=0)
    excessive_parameter_search_flagged: bool = False
    period_stability_metrics_present: bool = False
    experiment_lineage_present: bool = False
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

    @field_validator("report_id", mode="before")
    @classmethod
    def normalize_id(cls, value):
        return _upper_required(value, "report_id")

    @model_validator(mode="after")
    def validate_report(self):
        return _validate_safety_flags(self, "data snooping report")


class QuantStrategyDiversificationReport(StrictModel):
    report_id: str = Field(..., min_length=1)
    family_count: int = Field(default=0, ge=0)
    diversification_ready: bool = False
    strategy_correlation_flagged: bool = False
    drawdown_comovement_flagged: bool = False
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

    @field_validator("report_id", mode="before")
    @classmethod
    def normalize_id(cls, value):
        return _upper_required(value, "report_id")

    @model_validator(mode="after")
    def validate_report(self):
        return _validate_safety_flags(self, "diversification report")


class QuantStrategyRegimeReadinessReport(StrictModel):
    report_id: str = Field(..., min_length=1)
    regime_ready: bool = False
    evaluated_bucket_count: int = Field(default=0, ge=0)
    missing_bucket_count: int = Field(default=0, ge=0)
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

    @field_validator("report_id", mode="before")
    @classmethod
    def normalize_id(cls, value):
        return _upper_required(value, "report_id")

    @model_validator(mode="after")
    def validate_report(self):
        return _validate_safety_flags(self, "regime readiness report")


class QuantStrategyRobustnessInput(StrictModel):
    input_id: str = Field(..., min_length=1)
    config: QuantStrategyRobustnessConfig
    universe_policy: QuantStrategySurvivorshipBiasPolicy
    point_in_time_policy: QuantStrategyPointInTimePolicy
    walk_forward_policy: QuantStrategyWalkForwardPolicy
    diversification_policy: QuantStrategyDiversificationPolicy
    regime_policy: QuantStrategyRegimeReadinessPolicy
    experiment_registry_ref: str | None = None
    source_manifest_ids: list[str] = Field(default_factory=list)
    audit_records: list[QuantStrategyRobustnessAuditRecord] = Field(default_factory=list)
    robustness_readiness_report: QuantStrategyRobustnessReport | None = None
    survivorship_bias_report: QuantStrategySurvivorshipBiasReport | None = None
    point_in_time_leakage_report: QuantStrategyPointInTimeLeakageReport | None = None
    walk_forward_policy_report: QuantStrategyWalkForwardPolicyReport | None = None
    data_snooping_report: QuantStrategyDataSnoopingReport | None = None
    strategy_diversification_report: QuantStrategyDiversificationReport | None = None
    regime_readiness_report: QuantStrategyRegimeReadinessReport | None = None
    robustness_gap_report: QuantStrategyRobustnessGapReport | None = None
    robustness_safety_report: QuantStrategyRobustnessSafetyReport

    @field_validator("input_id", mode="before")
    @classmethod
    def normalize_input_id(cls, value):
        return _upper_required(value, "input_id")

    @field_validator("experiment_registry_ref", mode="before")
    @classmethod
    def normalize_experiment_registry_ref(cls, value):
        if value is None:
            return None
        return _validate_local_path(value, "experiment_registry_ref")

    @field_validator("source_manifest_ids", mode="before")
    @classmethod
    def normalize_manifests(cls, value):
        return _normalize_id_list(value, "source_manifest_ids")

    @model_validator(mode="after")
    def validate_input(self):
        if not self.audit_records:
            raise ValueError("audit_records must not be empty")
        return self
