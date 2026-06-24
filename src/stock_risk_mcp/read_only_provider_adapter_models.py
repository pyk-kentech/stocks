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


def _normalize_list(value, field_name: str, *, upper: bool = True, local_paths: bool = False) -> list[str]:
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
        "no_ls_api",
        "no_websocket",
        "no_cloud_llm",
        "no_local_llm_runtime",
        "no_env_read",
        "no_credential_read",
        "no_token_loading",
        "no_auth_header_generation",
    ):
        if not getattr(model, flag_name):
            raise ValueError(f"{context} must remain {flag_name}")
    return model


class ReadOnlyProvider(StrEnum):
    KIWOOM_REST = "KIWOOM_REST"
    LS_OPEN_API = "LS_OPEN_API"
    LOCAL_FIXTURE = "LOCAL_FIXTURE"
    MANUAL_CSV = "MANUAL_CSV"
    UNKNOWN = "UNKNOWN"


class ProviderRole(StrEnum):
    CURRENT_PRIMARY = "CURRENT_PRIMARY"
    FUTURE_MIGRATION_TARGET = "FUTURE_MIGRATION_TARGET"
    FALLBACK = "FALLBACK"
    FIXTURE_ONLY = "FIXTURE_ONLY"
    REJECTED = "REJECTED"


class ReadOnlyAdapterReadiness(StrEnum):
    BOUNDARY_READY = "BOUNDARY_READY"
    KIWOOM_READONLY_EVIDENCE_READY = "KIWOOM_READONLY_EVIDENCE_READY"
    LS_FUTURE_PLACEHOLDER = "LS_FUTURE_PLACEHOLDER"
    CANONICAL_CONTRACT_READY = "CANONICAL_CONTRACT_READY"
    DATA_GAP = "DATA_GAP"
    BLOCKED = "BLOCKED"
    REJECTED = "REJECTED"


class CapabilityStatus(StrEnum):
    AVAILABLE_NOW = "AVAILABLE_NOW"
    FUTURE_PLACEHOLDER = "FUTURE_PLACEHOLDER"
    EXTERNAL_REQUIRED = "EXTERNAL_REQUIRED"
    BLOCKED = "BLOCKED"
    UNKNOWN = "UNKNOWN"


class CanonicalRecordType(StrEnum):
    QUOTE = "QUOTE"
    OHLCV = "OHLCV"
    RANK_SIGNAL = "RANK_SIGNAL"
    FLOW_SIGNAL = "FLOW_SIGNAL"
    SECTOR_THEME_SIGNAL = "SECTOR_THEME_SIGNAL"
    REALTIME_EVENT = "REALTIME_EVENT"
    PROVIDER_CAPABILITY = "PROVIDER_CAPABILITY"


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
    no_ls_api: bool = True
    no_websocket: bool = True
    no_cloud_llm: bool = True
    no_local_llm_runtime: bool = True
    no_env_read: bool = True
    no_credential_read: bool = True
    no_token_loading: bool = True
    no_auth_header_generation: bool = True


class ProviderDefinition(StrictModel):
    provider: ReadOnlyProvider
    role: ProviderRole
    markets_supported: list[str] = Field(default_factory=list)
    read_only_supported: bool = True
    implemented: bool = False
    placeholder_only: bool = False
    future_api_evidence_required: bool = False
    evidence_ref: str | None = None
    notes: str = Field(..., min_length=1)

    @field_validator("markets_supported", mode="before")
    @classmethod
    def normalize_markets(cls, value):
        return _normalize_list(value, "markets_supported")

    @field_validator("evidence_ref", mode="before")
    @classmethod
    def normalize_evidence_ref(cls, value):
        if value is None:
            return None
        return _validate_local_path(value, "evidence_ref")

    @field_validator("notes", mode="before")
    @classmethod
    def normalize_notes(cls, value):
        return _string_required(value, "notes")


class CanonicalReadOnlyRecord(StrictModel):
    provider: ReadOnlyProvider
    provider_api_id: str = Field(..., min_length=1)
    canonical_instrument_key: str = Field(..., min_length=1)
    provider_symbol: str = Field(..., min_length=1)
    market: str = Field(..., min_length=1)
    currency: str = Field(..., min_length=1)
    observed_at: datetime
    available_at: datetime | None = None
    source_ref: str = Field(..., min_length=1)
    quality_flags: list[str] = Field(default_factory=list)
    stale_flag: bool = False
    gap_reason: str | None = None
    raw_payload_redacted: bool = True
    non_executable: bool = True

    @field_validator(
        "provider_api_id",
        "canonical_instrument_key",
        "provider_symbol",
        "market",
        "currency",
        "gap_reason",
        mode="before",
    )
    @classmethod
    def normalize_strings(cls, value, info):
        if value is None and info.field_name == "gap_reason":
            return None
        return _upper_required(value, info.field_name)

    @field_validator("observed_at", "available_at", mode="before")
    @classmethod
    def normalize_datetimes(cls, value):
        return _aware(value)

    @field_validator("source_ref", mode="before")
    @classmethod
    def normalize_source_ref(cls, value):
        return _validate_local_path(value, "source_ref")

    @field_validator("quality_flags", mode="before")
    @classmethod
    def normalize_quality_flags(cls, value):
        return _normalize_list(value, "quality_flags")


class CanonicalQuote(CanonicalReadOnlyRecord):
    last_price: float | None = None
    bid_price: float | None = None
    ask_price: float | None = None
    bid_size: int | None = Field(default=None, ge=0)
    ask_size: int | None = Field(default=None, ge=0)


class CanonicalOHLCV(CanonicalReadOnlyRecord):
    interval: str = Field(..., min_length=1)
    open_price: float
    high_price: float
    low_price: float
    close_price: float
    volume: float = Field(..., ge=0)

    @field_validator("interval", mode="before")
    @classmethod
    def normalize_interval(cls, value):
        return _upper_required(value, "interval")


class CanonicalRankSignal(CanonicalReadOnlyRecord):
    rank_metric: str = Field(..., min_length=1)
    rank_value: float
    rank_order: int = Field(..., ge=1)

    @field_validator("rank_metric", mode="before")
    @classmethod
    def normalize_metric(cls, value):
        return _upper_required(value, "rank_metric")


class CanonicalFlowSignal(CanonicalReadOnlyRecord):
    flow_metric: str = Field(..., min_length=1)
    net_flow_value: float

    @field_validator("flow_metric", mode="before")
    @classmethod
    def normalize_metric(cls, value):
        return _upper_required(value, "flow_metric")


class CanonicalSectorThemeSignal(CanonicalReadOnlyRecord):
    sector_or_theme_id: str = Field(..., min_length=1)
    signal_metric: str = Field(..., min_length=1)
    signal_value: float

    @field_validator("sector_or_theme_id", "signal_metric", mode="before")
    @classmethod
    def normalize_metric(cls, value, info):
        return _upper_required(value, info.field_name)


class CanonicalRealtimeEvent(CanonicalReadOnlyRecord):
    event_code: str = Field(..., min_length=1)
    event_type: str = Field(..., min_length=1)
    event_summary: str = Field(..., min_length=1)

    @field_validator("event_code", "event_type", mode="before")
    @classmethod
    def normalize_event_fields(cls, value, info):
        return _upper_required(value, info.field_name)

    @field_validator("event_summary", mode="before")
    @classmethod
    def normalize_summary(cls, value):
        return _string_required(value, "event_summary")


class CanonicalProviderCapability(CanonicalReadOnlyRecord):
    record_type: CanonicalRecordType = CanonicalRecordType.PROVIDER_CAPABILITY
    capability_name: str = Field(..., min_length=1)
    capability_status: CapabilityStatus
    notes: str = Field(..., min_length=1)

    @field_validator("capability_name", mode="before")
    @classmethod
    def normalize_capability_name(cls, value):
        return _upper_required(value, "capability_name")

    @field_validator("notes", mode="before")
    @classmethod
    def normalize_notes(cls, value):
        return _string_required(value, "notes")


class CanonicalReadOnlyAuditRecord(StrictModel):
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
    def normalize_audit_id(cls, value):
        return _upper_required(value, "audit_record_id")

    @field_validator("created_at", mode="before")
    @classmethod
    def normalize_datetime(cls, value):
        return _aware(value)

    @field_validator("source_path", mode="before")
    @classmethod
    def normalize_source_path(cls, value):
        return _validate_local_path(value, "source_path")

    @field_validator("operator_context", mode="before")
    @classmethod
    def normalize_operator_context(cls, value):
        return _string_required(value, "operator_context")


class KiwoomRequestEnvelopeBoundary(_BaseReport):
    operation_domain: str = "https://api.kiwoom.com"
    mock_domain: str = "https://mockapi.kiwoom.com"
    method: str = "POST"
    content_type: str = "application/json;charset=UTF-8"
    header_names: list[str] = Field(default_factory=lambda: ["API-ID", "AUTHORIZATION", "CONT-YN", "NEXT-KEY"])
    authorization_template: str = "Bearer <TOKEN_REF_ONLY>"
    continuation_request_headers: list[str] = Field(default_factory=lambda: ["CONT-YN", "NEXT-KEY"])
    continuation_response_headers: list[str] = Field(default_factory=lambda: ["CONT-YN", "NEXT-KEY"])
    token_ref_only: bool = True

    @field_validator("header_names", "continuation_request_headers", "continuation_response_headers", mode="before")
    @classmethod
    def normalize_headers(cls, value, info):
        return _normalize_list(value, info.field_name)

    @field_validator("authorization_template", mode="before")
    @classmethod
    def normalize_auth_template(cls, value):
        return _string_required(value, "authorization_template")

    @model_validator(mode="after")
    def validate_boundary(self):
        _validate_safety_flags(self, "kiwoom request envelope boundary")
        if self.authorization_template != "Bearer <TOKEN_REF_ONLY>":
            raise ValueError("authorization template must remain token-ref-only")
        return self


class KiwoomRestApiEvidenceEntry(StrictModel):
    api_id: str = Field(..., min_length=1)
    title: str = Field(..., min_length=1)
    category: str = Field(..., min_length=1)
    maps_to: list[str] = Field(default_factory=list)
    blocked_in_readonly: bool = False
    realtime_stream: bool = False
    account_or_order_api: bool = False

    @field_validator("api_id", "category", mode="before")
    @classmethod
    def normalize_upper(cls, value, info):
        return _upper_required(value, info.field_name)

    @field_validator("title", mode="before")
    @classmethod
    def normalize_title(cls, value):
        return _string_required(value, "title")

    @field_validator("maps_to", mode="before")
    @classmethod
    def normalize_maps_to(cls, value):
        return _normalize_list(value, "maps_to")


class LsFutureCompatibilityPlaceholder(_BaseReport):
    provider: ReadOnlyProvider = ReadOnlyProvider.LS_OPEN_API
    expected_base_url_placeholder: str = Field(..., min_length=1)
    expected_rest_header_shape_placeholder: str = Field(..., min_length=1)
    expected_tr_code_shape_placeholder: str = Field(..., min_length=1)
    future_api_evidence_required: bool = True
    migration_readiness_status: str = Field(..., min_length=1)
    implemented_now: bool = False
    coverage_claimed_now: bool = False

    @field_validator(
        "expected_base_url_placeholder",
        "expected_rest_header_shape_placeholder",
        "expected_tr_code_shape_placeholder",
        "migration_readiness_status",
        mode="before",
    )
    @classmethod
    def normalize_placeholder_fields(cls, value, info):
        if info.field_name == "expected_base_url_placeholder":
            return _string_required(value, info.field_name)
        return _upper_required(value, info.field_name)

    @model_validator(mode="after")
    def validate_placeholder(self):
        _validate_safety_flags(self, "ls future compatibility placeholder")
        if self.implemented_now or self.coverage_claimed_now:
            raise ValueError("LS placeholder must not claim implemented coverage now")
        return self


class BlockedAccountOrderApiRecord(StrictModel):
    api_id: str = Field(..., min_length=1)
    title: str = Field(..., min_length=1)
    block_reason: str = Field(..., min_length=1)
    realtime_stream: bool = False

    @field_validator("api_id", "block_reason", mode="before")
    @classmethod
    def normalize_upper(cls, value, info):
        return _upper_required(value, info.field_name)

    @field_validator("title", mode="before")
    @classmethod
    def normalize_title(cls, value):
        return _string_required(value, "title")


class ReadOnlyProviderAdapterSafetyReport(_BaseReport):
    safety_report_id: str = Field(..., min_length=1)
    blocked_capabilities: list[str] = Field(default_factory=list)
    findings: list[str] = Field(default_factory=list)

    @field_validator("safety_report_id", mode="before")
    @classmethod
    def normalize_id(cls, value):
        return _upper_required(value, "safety_report_id")

    @field_validator("blocked_capabilities", "findings", mode="before")
    @classmethod
    def normalize_list_fields(cls, value, info):
        return _normalize_list(value, info.field_name)

    @model_validator(mode="after")
    def validate_report(self):
        return _validate_safety_flags(self, "read-only provider adapter safety report")


class ReadOnlyProviderAdapterSummaryReport(_BaseReport):
    report_id: str = Field(..., min_length=1)
    readiness: ReadOnlyAdapterReadiness
    current_primary_provider: ReadOnlyProvider
    future_provider: ReadOnlyProvider
    decision_reason: str = Field(..., min_length=1)

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
        return _validate_safety_flags(self, "read-only provider adapter summary report")


class KiwoomRestEvidenceMapReport(_BaseReport):
    report_id: str = Field(..., min_length=1)
    entries: list[KiwoomRestApiEvidenceEntry] = Field(default_factory=list)

    @field_validator("report_id", mode="before")
    @classmethod
    def normalize_id(cls, value):
        return _upper_required(value, "report_id")

    @model_validator(mode="after")
    def validate_report(self):
        return _validate_safety_flags(self, "kiwoom rest evidence map report")


class LsFutureCompatibilityReport(_BaseReport):
    report_id: str = Field(..., min_length=1)
    placeholder: LsFutureCompatibilityPlaceholder

    @field_validator("report_id", mode="before")
    @classmethod
    def normalize_id(cls, value):
        return _upper_required(value, "report_id")

    @model_validator(mode="after")
    def validate_report(self):
        return _validate_safety_flags(self, "ls future compatibility report")


class CanonicalReadOnlyContractReport(_BaseReport):
    report_id: str = Field(..., min_length=1)
    request_envelope_boundary: KiwoomRequestEnvelopeBoundary
    quotes: list[CanonicalQuote] = Field(default_factory=list)
    ohlcv_records: list[CanonicalOHLCV] = Field(default_factory=list)
    rank_signals: list[CanonicalRankSignal] = Field(default_factory=list)
    flow_signals: list[CanonicalFlowSignal] = Field(default_factory=list)
    sector_theme_signals: list[CanonicalSectorThemeSignal] = Field(default_factory=list)
    realtime_events: list[CanonicalRealtimeEvent] = Field(default_factory=list)
    capability_records: list[CanonicalProviderCapability] = Field(default_factory=list)

    @field_validator("report_id", mode="before")
    @classmethod
    def normalize_id(cls, value):
        return _upper_required(value, "report_id")

    @model_validator(mode="after")
    def validate_report(self):
        return _validate_safety_flags(self, "canonical read-only contract report")


class ProviderCapabilityMatrixRow(StrictModel):
    capability_name: str = Field(..., min_length=1)
    provider: ReadOnlyProvider
    status: CapabilityStatus
    notes: str = Field(..., min_length=1)

    @field_validator("capability_name", mode="before")
    @classmethod
    def normalize_name(cls, value):
        return _upper_required(value, "capability_name")

    @field_validator("notes", mode="before")
    @classmethod
    def normalize_notes(cls, value):
        return _string_required(value, "notes")


class ProviderCapabilityMatrixReport(_BaseReport):
    report_id: str = Field(..., min_length=1)
    rows: list[ProviderCapabilityMatrixRow] = Field(default_factory=list)

    @field_validator("report_id", mode="before")
    @classmethod
    def normalize_id(cls, value):
        return _upper_required(value, "report_id")

    @model_validator(mode="after")
    def validate_report(self):
        return _validate_safety_flags(self, "provider capability matrix report")


class BlockedAccountOrderApiReport(_BaseReport):
    report_id: str = Field(..., min_length=1)
    blocked_records: list[BlockedAccountOrderApiRecord] = Field(default_factory=list)

    @field_validator("report_id", mode="before")
    @classmethod
    def normalize_id(cls, value):
        return _upper_required(value, "report_id")

    @model_validator(mode="after")
    def validate_report(self):
        return _validate_safety_flags(self, "blocked account order api report")


class ProviderMigrationReadinessReport(_BaseReport):
    report_id: str = Field(..., min_length=1)
    kiwoom_primary_ready: bool = False
    ls_placeholder_only: bool = True
    canonical_contract_ready: bool = False
    migration_blockers: list[str] = Field(default_factory=list)

    @field_validator("report_id", mode="before")
    @classmethod
    def normalize_id(cls, value):
        return _upper_required(value, "report_id")

    @field_validator("migration_blockers", mode="before")
    @classmethod
    def normalize_blockers(cls, value):
        return _normalize_list(value, "migration_blockers")

    @model_validator(mode="after")
    def validate_report(self):
        return _validate_safety_flags(self, "provider migration readiness report")


class ReadOnlyProviderAdapterGapEntry(StrictModel):
    gap_id: str = Field(..., min_length=1)
    gap_category: str = Field(..., min_length=1)
    severity: str = Field(..., min_length=1)
    message: str = Field(..., min_length=1)

    @field_validator("gap_id", "gap_category", "severity", mode="before")
    @classmethod
    def normalize_upper(cls, value, info):
        return _upper_required(value, info.field_name)

    @field_validator("message", mode="before")
    @classmethod
    def normalize_message(cls, value):
        return _string_required(value, "message")


class ReadOnlyProviderAdapterGapReport(_BaseReport):
    gap_report_id: str = Field(..., min_length=1)
    readiness: ReadOnlyAdapterReadiness
    gap_entries: list[ReadOnlyProviderAdapterGapEntry] = Field(default_factory=list)

    @field_validator("gap_report_id", mode="before")
    @classmethod
    def normalize_id(cls, value):
        return _upper_required(value, "gap_report_id")

    @model_validator(mode="after")
    def validate_report(self):
        return _validate_safety_flags(self, "read-only provider adapter gap report")


class ReadOnlyProviderAdapterInput(StrictModel):
    adapter_id: str = Field(..., min_length=1)
    current_provider: ReadOnlyProvider
    future_provider: ReadOnlyProvider
    provider_definitions: list[ProviderDefinition] = Field(default_factory=list)
    request_envelope_boundary: KiwoomRequestEnvelopeBoundary
    kiwoom_rest_evidence_entries: list[KiwoomRestApiEvidenceEntry] = Field(default_factory=list)
    ls_future_placeholder: LsFutureCompatibilityPlaceholder
    canonical_quotes: list[CanonicalQuote] = Field(default_factory=list)
    canonical_ohlcv_records: list[CanonicalOHLCV] = Field(default_factory=list)
    canonical_rank_signals: list[CanonicalRankSignal] = Field(default_factory=list)
    canonical_flow_signals: list[CanonicalFlowSignal] = Field(default_factory=list)
    canonical_sector_theme_signals: list[CanonicalSectorThemeSignal] = Field(default_factory=list)
    canonical_realtime_events: list[CanonicalRealtimeEvent] = Field(default_factory=list)
    canonical_capability_records: list[CanonicalProviderCapability] = Field(default_factory=list)
    blocked_account_order_api_records: list[BlockedAccountOrderApiRecord] = Field(default_factory=list)
    external_gap_markets: list[str] = Field(default_factory=list)
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
    no_ls_api: bool = True
    no_websocket: bool = True
    no_cloud_llm: bool = True
    no_local_llm_runtime: bool = True
    no_env_read: bool = True
    no_credential_read: bool = True
    no_token_loading: bool = True
    no_auth_header_generation: bool = True
    safety_report: ReadOnlyProviderAdapterSafetyReport
    audit_records: list[CanonicalReadOnlyAuditRecord] = Field(default_factory=list)
    summary_report: ReadOnlyProviderAdapterSummaryReport | None = None
    kiwoom_rest_evidence_map_report: KiwoomRestEvidenceMapReport | None = None
    ls_future_compatibility_report: LsFutureCompatibilityReport | None = None
    canonical_readonly_contract_report: CanonicalReadOnlyContractReport | None = None
    provider_capability_matrix_report: ProviderCapabilityMatrixReport | None = None
    blocked_account_order_api_report: BlockedAccountOrderApiReport | None = None
    provider_migration_readiness_report: ProviderMigrationReadinessReport | None = None
    gap_report: ReadOnlyProviderAdapterGapReport | None = None

    @field_validator("adapter_id", mode="before")
    @classmethod
    def normalize_id(cls, value):
        return _upper_required(value, "adapter_id")

    @field_validator("external_gap_markets", mode="before")
    @classmethod
    def normalize_external_gaps(cls, value):
        return _normalize_list(value, "external_gap_markets")

    @model_validator(mode="after")
    def validate_input(self):
        return _validate_safety_flags(self, "read-only provider adapter input")
