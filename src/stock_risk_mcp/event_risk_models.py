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


def _normalize_list(value, field_name: str, *, upper: bool = False, local_paths: bool = False) -> list[str]:
    if value is None:
        return []
    if isinstance(value, (str, bytes)) or not isinstance(value, list):
        raise ValueError(f"{field_name} must be a list")
    if local_paths:
        return [_validate_local_path(item, field_name) for item in value]
    if upper:
        return [_upper_required(item, field_name) for item in value]
    return [_string_required(item, field_name) for item in value]


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


class EventType(StrEnum):
    FOMC_RATE_DECISION = "FOMC_RATE_DECISION"
    FOMC_PRESS_CONFERENCE = "FOMC_PRESS_CONFERENCE"
    CPI = "CPI"
    PCE = "PCE"
    NFP = "NFP"
    GDP = "GDP"
    FED_SPEECH = "FED_SPEECH"
    BOK_RATE_DECISION = "BOK_RATE_DECISION"
    KOREA_CPI = "KOREA_CPI"
    EARNINGS = "EARNINGS"
    UNKNOWN = "UNKNOWN"


class EventImportance(StrEnum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"
    UNKNOWN = "UNKNOWN"


class EventRiskDecision(StrEnum):
    ALLOW = "ALLOW"
    REDUCE_SIZE = "REDUCE_SIZE"
    BLOCK_NEW_ENTRY = "BLOCK_NEW_ENTRY"
    REDUCE_ONLY = "REDUCE_ONLY"
    WATCH_ONLY = "WATCH_ONLY"
    EVENT_ACTIVE = "EVENT_ACTIVE"
    COOLDOWN = "COOLDOWN"
    DATA_GAP = "DATA_GAP"
    BLOCKED = "BLOCKED"
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


class EventRiskSafetyReport(_BaseReport):
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
        return _validate_safety_flags(self, "event risk safety report")


class EventRiskAuditRecord(StrictModel):
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


class EconomicEventRecord(StrictModel):
    event_id: str = Field(..., min_length=1)
    event_type: EventType
    country_scope: str = Field(..., min_length=1)
    market_scope: str = Field(..., min_length=1)
    affected_markets: list[str] = Field(default_factory=list)
    scheduled_at: datetime
    available_at: datetime | None = None
    source_provider_ref: str = Field(..., min_length=1)
    source_calendar_ref: str = Field(..., min_length=1)
    importance_level: EventImportance
    expected_impact: str = Field(..., min_length=1)
    actual_value: str | None = None
    forecast_value: str | None = None
    previous_value: str | None = None
    event_status: str = Field(..., min_length=1)
    timezone: str = Field(..., min_length=1)
    event_window_policy_ref: str = Field(..., min_length=1)

    @field_validator("event_id", "country_scope", "market_scope", "expected_impact", "event_status", "timezone", mode="before")
    @classmethod
    def normalize_upper(cls, value):
        return _upper_required(value, "field")

    @field_validator("affected_markets", mode="before")
    @classmethod
    def normalize_markets(cls, value):
        return _normalize_list(value, "affected_markets", upper=True)

    @field_validator("scheduled_at", "available_at", mode="before")
    @classmethod
    def normalize_dt(cls, value):
        return _aware(value)

    @field_validator("source_provider_ref", "source_calendar_ref", "event_window_policy_ref", mode="before")
    @classmethod
    def normalize_ref(cls, value):
        return _validate_local_path(value, "ref")

    @field_validator("actual_value", "forecast_value", "previous_value", mode="before")
    @classmethod
    def normalize_optional_text(cls, value):
        if value is None:
            return None
        return _string_required(value, "field")


class EventWindowPolicy(StrictModel):
    window_id: str = Field(..., min_length=1)
    event_type: EventType
    importance_level: EventImportance
    pre_event_block_window_minutes: int = Field(default=0, ge=0)
    pre_event_reduce_window_minutes: int = Field(default=0, ge=0)
    post_event_cooldown_minutes: int = Field(default=0, ge=0)
    event_active_window_minutes: int = Field(default=0, ge=0)
    new_entry_allowed: bool = True
    position_increase_allowed: bool = True
    reduce_only: bool = False
    watch_only: bool = False
    event_size_multiplier: float = Field(default=1.0, ge=0)
    forced_gap_if_calendar_missing: bool = False
    policy_reason: str = Field(..., min_length=1)

    @field_validator("window_id", mode="before")
    @classmethod
    def normalize_id(cls, value):
        return _upper_required(value, "window_id")

    @field_validator("policy_reason", mode="before")
    @classmethod
    def normalize_reason(cls, value):
        return _string_required(value, "policy_reason")


class EventRiskSummaryReport(_BaseReport):
    report_id: str = Field(..., min_length=1)
    decision: EventRiskDecision
    decision_reason: str = Field(..., min_length=1)
    applicable_event_ids: list[str] = Field(default_factory=list)
    event_size_multiplier: float = Field(default=1.0, ge=0)
    position_sizing_decision_after_gate: str = Field(..., min_length=1)

    @field_validator("report_id", "position_sizing_decision_after_gate", mode="before")
    @classmethod
    def normalize_upper(cls, value):
        return _upper_required(value, "field")

    @field_validator("decision_reason", mode="before")
    @classmethod
    def normalize_reason(cls, value):
        return _string_required(value, "decision_reason")

    @field_validator("applicable_event_ids", mode="before")
    @classmethod
    def normalize_ids(cls, value):
        return _normalize_list(value, "applicable_event_ids", upper=True)

    @model_validator(mode="after")
    def validate_model(self):
        return _validate_safety_flags(self, "event risk summary report")


class EconomicCalendarSnapshotReport(_BaseReport):
    report_id: str = Field(..., min_length=1)
    event_count: int = Field(default=0, ge=0)
    event_ids: list[str] = Field(default_factory=list)
    stale_calendar: bool = False

    @field_validator("report_id", mode="before")
    @classmethod
    def normalize_id(cls, value):
        return _upper_required(value, "report_id")

    @field_validator("event_ids", mode="before")
    @classmethod
    def normalize_event_ids(cls, value):
        return _normalize_list(value, "event_ids", upper=True)

    @model_validator(mode="after")
    def validate_model(self):
        return _validate_safety_flags(self, "economic calendar snapshot report")


class EventWindowReport(_BaseReport):
    report_id: str = Field(..., min_length=1)
    matched_window_id: str | None = None
    matched_event_id: str | None = None
    phase: str = Field(..., min_length=1)
    event_size_multiplier: float = Field(default=1.0, ge=0)

    @field_validator("report_id", "matched_window_id", "matched_event_id", "phase", mode="before")
    @classmethod
    def normalize_optional_upper(cls, value):
        if value is None:
            return None
        return _upper_required(value, "field")

    @model_validator(mode="after")
    def validate_model(self):
        return _validate_safety_flags(self, "event window report")


class EventRestrictionReport(_BaseReport):
    report_id: str = Field(..., min_length=1)
    new_entry_allowed: bool = True
    position_increase_allowed: bool = True
    reduce_only: bool = False
    watch_only: bool = False
    restrictions: list[str] = Field(default_factory=list)

    @field_validator("report_id", mode="before")
    @classmethod
    def normalize_id(cls, value):
        return _upper_required(value, "report_id")

    @field_validator("restrictions", mode="before")
    @classmethod
    def normalize_restrictions(cls, value):
        return _normalize_list(value, "restrictions", upper=True)

    @model_validator(mode="after")
    def validate_model(self):
        return _validate_safety_flags(self, "event restriction report")


class PositionSizingEventAdjustmentReport(_BaseReport):
    report_id: str = Field(..., min_length=1)
    upstream_position_sizing_decision: str = Field(..., min_length=1)
    adjusted_position_sizing_decision: str = Field(..., min_length=1)
    adjusted_size_multiplier: float = Field(default=1.0, ge=0)

    @field_validator("report_id", "upstream_position_sizing_decision", "adjusted_position_sizing_decision", mode="before")
    @classmethod
    def normalize_upper(cls, value):
        return _upper_required(value, "field")

    @model_validator(mode="after")
    def validate_model(self):
        return _validate_safety_flags(self, "position sizing event adjustment report")


class EventCalendarProviderReadinessReport(_BaseReport):
    report_id: str = Field(..., min_length=1)
    provider_ready: bool = False
    provider_readiness_level: str = Field(..., min_length=1)
    calendar_ready: bool = False
    stale_calendar: bool = False
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
        return _validate_safety_flags(self, "event provider readiness report")


class EventRiskLeakageReport(_BaseReport):
    report_id: str = Field(..., min_length=1)
    future_event_knowledge_leakage: bool = False
    future_actual_value_leakage: bool = False
    missing_available_at: bool = False
    findings: list[str] = Field(default_factory=list)

    @field_validator("report_id", mode="before")
    @classmethod
    def normalize_id(cls, value):
        return _upper_required(value, "report_id")

    @field_validator("findings", mode="before")
    @classmethod
    def normalize_findings(cls, value):
        return _normalize_list(value, "findings", upper=True)

    @model_validator(mode="after")
    def validate_model(self):
        return _validate_safety_flags(self, "event risk leakage report")


class EventRiskGapEntry(StrictModel):
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


class EventRiskGapReport(_BaseReport):
    gap_report_id: str = Field(..., min_length=1)
    decision: EventRiskDecision
    gap_entries: list[EventRiskGapEntry] = Field(default_factory=list)
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
        return _validate_safety_flags(self, "event risk gap report")


class EventRiskInput(StrictModel):
    event_risk_review_id: str = Field(..., min_length=1)
    candidate_symbol: str = Field(..., min_length=1)
    market: str = Field(..., min_length=1)
    country_scope: str = Field(..., min_length=1)
    candidate_action_type: str = Field(..., min_length=1)
    candidate_side: str = Field(..., min_length=1)
    decision_timestamp: datetime
    available_at: datetime | None = None
    provider_readiness_ref: str | None = None
    provider_readiness_level: str = Field(..., min_length=1)
    calendar_source_ref: str | None = None
    calendar_provider_ref: str | None = None
    calendar_freshness_minutes: int = Field(default=0, ge=0)
    calendar_max_age_minutes: int = Field(default=0, ge=0)
    fail_closed_if_calendar_missing: bool = False
    position_sizing_ref: str | None = None
    position_sizing_decision: str | None = None
    position_sizing_quantity: int | None = Field(default=None, ge=0)
    position_sizing_notional: float | None = Field(default=None, ge=0)
    position_sizing_size_multiplier: float = Field(default=1.0, ge=0)
    market_regime_ref: str | None = None
    market_regime_label: str | None = None
    existing_position: bool = False
    is_single_name: bool = False
    is_inverse_or_hedge: bool = False
    net_exposure_reducing_action: bool = False
    events: list[EconomicEventRecord] = Field(default_factory=list)
    event_windows: list[EventWindowPolicy] = Field(default_factory=list)
    source_refs: list[str] = Field(default_factory=list)
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
    safety_report: EventRiskSafetyReport
    audit_records: list[EventRiskAuditRecord] = Field(default_factory=list)
    summary_report: EventRiskSummaryReport | None = None
    calendar_snapshot_report: EconomicCalendarSnapshotReport | None = None
    event_window_report: EventWindowReport | None = None
    restriction_report: EventRestrictionReport | None = None
    position_sizing_adjustment_report: PositionSizingEventAdjustmentReport | None = None
    provider_readiness_report: EventCalendarProviderReadinessReport | None = None
    leakage_report: EventRiskLeakageReport | None = None
    gap_report: EventRiskGapReport | None = None

    @field_validator(
        "event_risk_review_id",
        "candidate_symbol",
        "market",
        "country_scope",
        "candidate_action_type",
        "candidate_side",
        "provider_readiness_level",
        "position_sizing_decision",
        "market_regime_label",
        mode="before",
    )
    @classmethod
    def normalize_upper(cls, value):
        if value is None:
            return None
        return _upper_required(value, "field")

    @field_validator("decision_timestamp", "available_at", mode="before")
    @classmethod
    def normalize_dt(cls, value):
        return _aware(value)

    @field_validator(
        "provider_readiness_ref",
        "calendar_source_ref",
        "calendar_provider_ref",
        "position_sizing_ref",
        "market_regime_ref",
        mode="before",
    )
    @classmethod
    def normalize_optional_ref(cls, value):
        if value is None:
            return None
        return _validate_local_path(value, "ref")

    @field_validator("source_refs", mode="before")
    @classmethod
    def normalize_source_refs(cls, value):
        return _normalize_list(value, "source_refs", local_paths=True)

    @model_validator(mode="after")
    def validate_model(self):
        _validate_safety_flags(self, "event risk input")
        for audit in self.audit_records:
            if not audit.redaction_applied:
                raise ValueError("audit records must be redacted")
        return self
