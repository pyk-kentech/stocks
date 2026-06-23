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


class PointInTimeUniverseSource(StrEnum):
    CURRENT_SURVIVORS_ONLY = "CURRENT_SURVIVORS_ONLY"
    POINT_IN_TIME_UNIVERSE = "POINT_IN_TIME_UNIVERSE"
    MIXED_OR_UNKNOWN = "MIXED_OR_UNKNOWN"
    INVALID = "INVALID"


class PointInTimeUniverseDecision(StrEnum):
    BLOCKED = "BLOCKED"
    RESEARCH_ONLY = "RESEARCH_ONLY"
    TRAINING_READY = "TRAINING_READY"
    GAP = "GAP"
    REJECTED = "REJECTED"


class SecurityLifecycleStatus(StrEnum):
    LISTED = "LISTED"
    DELISTED = "DELISTED"
    SUSPENDED = "SUSPENDED"
    RENAMED = "RENAMED"
    MERGED = "MERGED"
    INDEX_ADDED = "INDEX_ADDED"
    INDEX_REMOVED = "INDEX_REMOVED"
    UNKNOWN = "UNKNOWN"


class PointInTimeUniverseGapCategory(StrEnum):
    POINT_IN_TIME_UNIVERSE_REPORT_GENERATED = "POINT_IN_TIME_UNIVERSE_REPORT_GENERATED"
    CURRENT_SURVIVORS_ONLY_TRAINING_BLOCKED = "CURRENT_SURVIVORS_ONLY_TRAINING_BLOCKED"
    AVAILABLE_AT_MISSING = "AVAILABLE_AT_MISSING"
    DELISTING_COVERAGE_MISSING = "DELISTING_COVERAGE_MISSING"
    SUSPENSION_COVERAGE_MISSING = "SUSPENSION_COVERAGE_MISSING"
    RENAME_COVERAGE_MISSING = "RENAME_COVERAGE_MISSING"
    CORPORATE_ACTION_COVERAGE_MISSING = "CORPORATE_ACTION_COVERAGE_MISSING"
    INDEX_MEMBERSHIP_COVERAGE_MISSING = "INDEX_MEMBERSHIP_COVERAGE_MISSING"
    TRADABILITY_COVERAGE_MISSING = "TRADABILITY_COVERAGE_MISSING"
    MISSING_DATE_GAP_COVERAGE = "MISSING_DATE_GAP_COVERAGE"
    FUTURE_INDEX_MEMBERSHIP_LEAKAGE = "FUTURE_INDEX_MEMBERSHIP_LEAKAGE"
    CURRENT_CONSTITUENT_REPLAY_LEAKAGE = "CURRENT_CONSTITUENT_REPLAY_LEAKAGE"
    FUTURE_DELISTING_KNOWLEDGE_LEAKAGE = "FUTURE_DELISTING_KNOWLEDGE_LEAKAGE"
    SYMBOL_SURVIVORSHIP_LEAKAGE = "SYMBOL_SURVIVORSHIP_LEAKAGE"
    MIXED_OR_UNKNOWN_SOURCE = "MIXED_OR_UNKNOWN_SOURCE"
    INVALID_SOURCE = "INVALID_SOURCE"
    REMOTE_SOURCE_NOT_ALLOWED = "REMOTE_SOURCE_NOT_ALLOWED"
    NETWORK_PATH_NOT_ALLOWED = "NETWORK_PATH_NOT_ALLOWED"
    ORDER_PATH_NOT_ALLOWED = "ORDER_PATH_NOT_ALLOWED"
    LIVE_PROD_NOT_ALLOWED = "LIVE_PROD_NOT_ALLOWED"
    PARQUET_NOT_ALLOWED = "PARQUET_NOT_ALLOWED"


class PointInTimeUniverseGapEntry(StrictModel):
    gap_id: str = Field(..., min_length=1)
    gap_category: PointInTimeUniverseGapCategory
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


class PointInTimeUniverseSnapshot(StrictModel):
    snapshot_id: str = Field(..., min_length=1)
    trading_date: str = Field(..., min_length=1)
    market: str = Field(..., min_length=1)
    symbol_universe: list[str] = Field(default_factory=list)
    inclusion_reason: str | None = None
    exclusion_reason: str | None = None
    index_membership_ref: str | None = None
    tradability_status: str = Field(..., min_length=1)
    available_at: datetime

    @field_validator("snapshot_id", mode="before")
    @classmethod
    def normalize_snapshot_id(cls, value):
        return _upper_required(value, "snapshot_id")

    @field_validator("trading_date", "market", "tradability_status", mode="before")
    @classmethod
    def normalize_string_fields(cls, value, info):
        return _string_required(value, info.field_name)

    @field_validator("symbol_universe", mode="before")
    @classmethod
    def normalize_symbols(cls, value):
        return _normalize_str_list(value, "symbol_universe", upper=True)

    @field_validator("inclusion_reason", "exclusion_reason", "index_membership_ref", mode="before")
    @classmethod
    def normalize_optional(cls, value):
        if value is None:
            return None
        cleaned = str(value).strip()
        return cleaned or None

    @field_validator("available_at", mode="before")
    @classmethod
    def validate_available_at(cls, value):
        return _aware(datetime.fromisoformat(value) if isinstance(value, str) else value)


class SecurityLifecycleRecord(StrictModel):
    record_id: str = Field(..., min_length=1)
    symbol: str = Field(..., min_length=1)
    status: SecurityLifecycleStatus
    event_date: str = Field(..., min_length=1)
    available_at: datetime
    coverage_present: bool = True

    @field_validator("record_id", "symbol", mode="before")
    @classmethod
    def normalize_ids(cls, value, info):
        return _upper_required(value, info.field_name)

    @field_validator("event_date", mode="before")
    @classmethod
    def normalize_event_date(cls, value):
        return _string_required(value, "event_date")

    @field_validator("available_at", mode="before")
    @classmethod
    def validate_available_at(cls, value):
        return _aware(datetime.fromisoformat(value) if isinstance(value, str) else value)


class PointInTimeUniverseGateConfig(StrictModel):
    config_id: str = Field(..., min_length=1)
    fixture_format: str = Field(default="json", min_length=1)
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
        return _validate_safety_flags(self, "point in time universe gate config")


class PointInTimeUniverseSafetyReport(StrictModel):
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
        return _validate_safety_flags(self, "point in time universe safety report")


class PointInTimeUniverseGapReport(StrictModel):
    gap_report_id: str = Field(..., min_length=1)
    decision: PointInTimeUniverseDecision
    gap_entries: list[PointInTimeUniverseGapEntry] = Field(default_factory=list)
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
        return _validate_safety_flags(self, "point in time universe gap report")


class PointInTimeUniverseAuditRecord(StrictModel):
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
    def validate_created_at(cls, value):
        return _aware(datetime.fromisoformat(value) if isinstance(value, str) else value)

    @field_validator("source_path", mode="before")
    @classmethod
    def validate_source_path(cls, value):
        return _validate_local_path(value, "source_path")

    @field_validator("operator_context", mode="before")
    @classmethod
    def normalize_context(cls, value):
        return _string_required(value, "operator_context")


class PointInTimeUniverseReport(StrictModel):
    report_id: str = Field(..., min_length=1)
    universe_source: PointInTimeUniverseSource
    available_at_complete: bool = False
    snapshot_coverage_complete: bool = False
    tradability_coverage_complete: bool = False
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
        return _validate_safety_flags(self, "point in time universe report")


class SurvivorshipBiasDatasetReport(StrictModel):
    report_id: str = Field(..., min_length=1)
    current_survivors_only: bool = False
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

    @field_validator("findings", mode="before")
    @classmethod
    def normalize_findings(cls, value):
        return _normalize_str_list(value, "findings", upper=False)

    @model_validator(mode="after")
    def validate_report(self):
        return _validate_safety_flags(self, "survivorship bias dataset report")


class SecurityLifecycleCoverageReport(StrictModel):
    report_id: str = Field(..., min_length=1)
    lifecycle_statuses_present: list[SecurityLifecycleStatus] = Field(default_factory=list)
    delisting_coverage_complete: bool = False
    suspension_coverage_complete: bool = False
    rename_coverage_complete: bool = False
    corporate_action_coverage_complete: bool = False
    index_membership_coverage_complete: bool = False
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
        return _validate_safety_flags(self, "security lifecycle coverage report")


class DatasetLeakageReport(StrictModel):
    report_id: str = Field(..., min_length=1)
    future_index_membership_leakage_detected: bool = False
    current_constituent_replay_leakage_detected: bool = False
    future_delisting_knowledge_leakage_detected: bool = False
    symbol_survivorship_leakage_detected: bool = False
    missing_available_at_detected: bool = False
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
        return _validate_safety_flags(self, "dataset leakage report")


class DatasetPromotionReadinessReport(StrictModel):
    report_id: str = Field(..., min_length=1)
    decision: PointInTimeUniverseDecision
    decision_reason: str = Field(..., min_length=1)
    training_grade_candidate: bool = False
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
        return _validate_safety_flags(self, "dataset promotion readiness report")


class PointInTimeUniverseInput(StrictModel):
    input_id: str = Field(..., min_length=1)
    config: PointInTimeUniverseGateConfig
    universe_source: PointInTimeUniverseSource
    universe_snapshots: list[PointInTimeUniverseSnapshot] = Field(default_factory=list)
    security_lifecycle_records: list[SecurityLifecycleRecord] = Field(default_factory=list)
    available_at_coverage_complete: bool = False
    corporate_action_coverage_complete: bool = False
    index_membership_coverage_complete: bool = False
    tradability_coverage_complete: bool = False
    missing_date_gap_coverage_complete: bool = False
    future_index_membership_leakage_detected: bool = False
    current_constituent_replay_leakage_detected: bool = False
    future_delisting_knowledge_leakage_detected: bool = False
    symbol_survivorship_leakage_detected: bool = False
    source_manifest_ids: list[str] = Field(default_factory=list)
    audit_records: list[PointInTimeUniverseAuditRecord] = Field(default_factory=list)
    point_in_time_universe_report: PointInTimeUniverseReport | None = None
    survivorship_bias_report: SurvivorshipBiasDatasetReport | None = None
    security_lifecycle_coverage_report: SecurityLifecycleCoverageReport | None = None
    leakage_report: DatasetLeakageReport | None = None
    dataset_promotion_readiness_report: DatasetPromotionReadinessReport | None = None
    gap_report: PointInTimeUniverseGapReport | None = None
    safety_report: PointInTimeUniverseSafetyReport

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
