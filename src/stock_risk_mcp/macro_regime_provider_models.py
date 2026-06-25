from __future__ import annotations

from datetime import date, datetime
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


def _date_value(value: date | str | None) -> date | None:
    if value is None:
        return None
    return date.fromisoformat(value) if isinstance(value, str) else value


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


class MacroRegimeProvider(StrEnum):
    LOCAL_FIXTURE = "LOCAL_FIXTURE"
    MANUAL_JSON = "MANUAL_JSON"
    MANUAL_CSV = "MANUAL_CSV"
    FRED = "FRED"
    DATABENTO = "DATABENTO"
    CME = "CME"
    BLS = "BLS"
    BEA = "BEA"
    FEDERAL_RESERVE = "FEDERAL_RESERVE"
    BOK_ECOS = "BOK_ECOS"
    INVESTING_CALENDAR_MANUAL = "INVESTING_CALENDAR_MANUAL"
    YAHOO_DELAYED_REFERENCE = "YAHOO_DELAYED_REFERENCE"
    LS_OPEN_API_FUTURE = "LS_OPEN_API_FUTURE"
    UNKNOWN = "UNKNOWN"


class MacroRegimeProviderCapability(StrEnum):
    NQ_FUTURES = "NQ_FUTURES"
    ES_FUTURES = "ES_FUTURES"
    VIX = "VIX"
    DOLLAR_STRENGTH = "DOLLAR_STRENGTH"
    US10Y = "US10Y"
    USDKRW = "USDKRW"
    CPI_EVENT = "CPI_EVENT"
    NFP_EVENT = "NFP_EVENT"
    PCE_EVENT = "PCE_EVENT"
    GDP_EVENT = "GDP_EVENT"
    FOMC_EVENT = "FOMC_EVENT"
    BOK_EVENT = "BOK_EVENT"
    MANUAL_EVENT_CALENDAR = "MANUAL_EVENT_CALENDAR"


class MacroRegimeProviderStatus(StrEnum):
    AVAILABLE = "AVAILABLE"
    MOCKED_ONLY = "MOCKED_ONLY"
    MANUAL_ONLY = "MANUAL_ONLY"
    OPT_IN_REQUIRED = "OPT_IN_REQUIRED"
    PROVIDER_SETUP_REQUIRED = "PROVIDER_SETUP_REQUIRED"
    DATA_GAP = "DATA_GAP"
    BLOCKED = "BLOCKED"
    REJECTED = "REJECTED"


class MacroRegimeProviderCredentialPolicy(StrEnum):
    NOT_REQUIRED = "NOT_REQUIRED"
    KEY_REF_ONLY = "KEY_REF_ONLY"
    MANUAL_IMPORT_ONLY = "MANUAL_IMPORT_ONLY"
    PROVIDER_SETUP_REQUIRED = "PROVIDER_SETUP_REQUIRED"
    DISABLED = "DISABLED"


class MacroRegimeSeriesId(StrEnum):
    NQ_CONTINUOUS = "NQ_CONTINUOUS"
    ES_CONTINUOUS = "ES_CONTINUOUS"
    VIX = "VIX"
    DOLLAR_STRENGTH = "DOLLAR_STRENGTH"
    US10Y = "US10Y"
    USDKRW = "USDKRW"


class MacroRegimeAssetClass(StrEnum):
    FUTURES = "FUTURES"
    VOLATILITY = "VOLATILITY"
    FX = "FX"
    RATES = "RATES"
    INDEX = "INDEX"
    EVENT = "EVENT"


class MacroRegimeEventType(StrEnum):
    FOMC = "FOMC"
    CPI = "CPI"
    PCE = "PCE"
    NFP = "NFP"
    GDP = "GDP"
    BOK_RATE = "BOK_RATE"
    UNKNOWN = "UNKNOWN"


class MacroRegimeEventImportance(StrEnum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"
    UNKNOWN = "UNKNOWN"


class MacroRegimeSnapshotReadiness(StrEnum):
    SNAPSHOT_READY = "SNAPSHOT_READY"
    PARTIAL = "PARTIAL"
    STALE = "STALE"
    CONFLICT = "CONFLICT"
    DATA_GAP = "DATA_GAP"
    BLOCKED = "BLOCKED"


class MacroRegimeClassificationLabel(StrEnum):
    MACRO_RISK_ON = "MACRO_RISK_ON"
    MACRO_RISK_OFF = "MACRO_RISK_OFF"
    MACRO_MIXED = "MACRO_MIXED"
    MACRO_EVENT_RISK = "MACRO_EVENT_RISK"
    MACRO_DATA_GAP = "MACRO_DATA_GAP"


class MacroRegimeRuntimeContext(StrEnum):
    CLI = "CLI"
    PYTEST = "PYTEST"
    OFFLINE = "OFFLINE"


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


class MacroRegimeAuditRecord(StrictModel):
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
    def normalize_source_path(cls, value):
        return _validate_local_path(value, "source_path")

    @field_validator("operator_context", mode="before")
    @classmethod
    def normalize_context(cls, value):
        return _string_required(value, "operator_context")


class MacroRegimeProviderDefinition(StrictModel):
    provider: MacroRegimeProvider
    capabilities: list[MacroRegimeProviderCapability] = Field(default_factory=list)
    status: MacroRegimeProviderStatus
    credential_policy: MacroRegimeProviderCredentialPolicy
    supports_real_http: bool = False
    opt_in_required: bool = True
    key_ref_required: bool = False
    notes: str = Field(..., min_length=1)

    @field_validator("notes", mode="before")
    @classmethod
    def normalize_notes(cls, value):
        return _string_required(value, "notes")


class FredSeriesRequest(StrictModel):
    request_id: str = Field(..., min_length=1)
    provider: MacroRegimeProvider = MacroRegimeProvider.FRED
    series_id: MacroRegimeSeriesId
    fred_series_code: str = Field(..., min_length=1)
    observation_start: date | None = None
    observation_end: date | None = None
    file_type: str = Field(default="json", min_length=1)
    api_key_ref: str | None = None
    explicit_opt_in: bool = False
    allow_real_http: bool = False
    key_env_var_name: str | None = None

    @field_validator("request_id", "fred_series_code", "file_type", "key_env_var_name", mode="before")
    @classmethod
    def normalize_upper(cls, value, info):
        if value is None and info.field_name == "key_env_var_name":
            return None
        return _upper_required(value, info.field_name)

    @field_validator("api_key_ref", mode="before")
    @classmethod
    def normalize_api_key_ref(cls, value):
        if value is None:
            return None
        return _string_required(value, "api_key_ref")

    @field_validator("observation_start", "observation_end", mode="before")
    @classmethod
    def normalize_dates(cls, value):
        return _date_value(value)


class MacroRegimeRequestPreview(_BaseReport):
    preview_id: str = Field(..., min_length=1)
    provider: MacroRegimeProvider
    method: str = Field(default="GET", min_length=1)
    url: str = Field(..., min_length=1)
    query_params: dict[str, str] = Field(default_factory=dict)
    redacted_fields: list[str] = Field(default_factory=list)
    status: MacroRegimeProviderStatus
    decision_reason: str = Field(..., min_length=1)

    @field_validator("preview_id", "method", mode="before")
    @classmethod
    def normalize_upper(cls, value, info):
        return _upper_required(value, info.field_name)

    @field_validator("url", "decision_reason", mode="before")
    @classmethod
    def normalize_text(cls, value, info):
        return _string_required(value, info.field_name)

    @field_validator("redacted_fields", mode="before")
    @classmethod
    def normalize_fields(cls, value):
        return _normalize_list(value, "redacted_fields")

    @model_validator(mode="after")
    def validate_report(self):
        return _validate_safety_flags(self, "macro regime request preview")


class CanonicalMacroSeriesPoint(StrictModel):
    series_id: MacroRegimeSeriesId
    asset_class: MacroRegimeAssetClass
    provider: MacroRegimeProvider
    provider_symbol: str = Field(..., min_length=1)
    observed_at: datetime
    available_at: datetime | None = None
    value: float
    pct_change_1d: float | None = None
    unit: str = Field(..., min_length=1)
    source_ref: str = Field(..., min_length=1)
    quality_flags: list[str] = Field(default_factory=list)
    stale_flag: bool = False

    @field_validator("provider_symbol", "unit", mode="before")
    @classmethod
    def normalize_upper(cls, value, info):
        return _upper_required(value, info.field_name)

    @field_validator("observed_at", "available_at", mode="before")
    @classmethod
    def normalize_dt(cls, value):
        return _aware(value)

    @field_validator("source_ref", mode="before")
    @classmethod
    def normalize_source_ref(cls, value):
        return _validate_local_path(value, "source_ref")

    @field_validator("quality_flags", mode="before")
    @classmethod
    def normalize_flags(cls, value):
        return _normalize_list(value, "quality_flags")


class CanonicalMacroEvent(StrictModel):
    event_id: str = Field(..., min_length=1)
    event_type: MacroRegimeEventType
    provider: MacroRegimeProvider
    country: str = Field(..., min_length=1)
    title: str = Field(..., min_length=1)
    event_time: datetime
    timezone: str = Field(..., min_length=1)
    importance: MacroRegimeEventImportance
    affected_assets: list[str] = Field(default_factory=list)
    pre_event_block_window_minutes: int = Field(default=0, ge=0)
    pre_event_reduce_window_minutes: int = Field(default=0, ge=0)
    post_event_cooldown_minutes: int = Field(default=0, ge=0)
    event_active_window_minutes: int = Field(default=0, ge=0)
    source_ref: str = Field(..., min_length=1)
    available_at: datetime | None = None

    @field_validator("event_id", "country", "timezone", mode="before")
    @classmethod
    def normalize_upper(cls, value, info):
        return _upper_required(value, info.field_name)

    @field_validator("title", mode="before")
    @classmethod
    def normalize_title(cls, value):
        return _string_required(value, "title")

    @field_validator("event_time", "available_at", mode="before")
    @classmethod
    def normalize_dt(cls, value):
        return _aware(value)

    @field_validator("affected_assets", mode="before")
    @classmethod
    def normalize_assets(cls, value):
        return _normalize_list(value, "affected_assets")

    @field_validator("source_ref", mode="before")
    @classmethod
    def normalize_source_ref(cls, value):
        return _validate_local_path(value, "source_ref")


class CanonicalMacroEventWindow(StrictModel):
    window_id: str = Field(..., min_length=1)
    event_id: str = Field(..., min_length=1)
    event_type: MacroRegimeEventType
    starts_at: datetime
    event_time: datetime
    ends_at: datetime
    phase: str = Field(..., min_length=1)
    active: bool = False
    source_ref: str = Field(..., min_length=1)

    @field_validator("window_id", "event_id", "phase", mode="before")
    @classmethod
    def normalize_upper(cls, value, info):
        return _upper_required(value, info.field_name)

    @field_validator("starts_at", "event_time", "ends_at", mode="before")
    @classmethod
    def normalize_dt(cls, value):
        return _aware(value)

    @field_validator("source_ref", mode="before")
    @classmethod
    def normalize_source(cls, value):
        return _validate_local_path(value, "source_ref")


class MacroRegimeProviderCapabilityRow(StrictModel):
    provider: MacroRegimeProvider
    capability: MacroRegimeProviderCapability
    status: MacroRegimeProviderStatus
    manual_fixture_supplied: bool = False
    notes: str = Field(..., min_length=1)

    @field_validator("notes", mode="before")
    @classmethod
    def normalize_notes(cls, value):
        return _string_required(value, "notes")


class MacroRegimeProviderCapabilityReport(_BaseReport):
    report_id: str = Field(..., min_length=1)
    rows: list[MacroRegimeProviderCapabilityRow] = Field(default_factory=list)

    @field_validator("report_id", mode="before")
    @classmethod
    def normalize_id(cls, value):
        return _upper_required(value, "report_id")

    @model_validator(mode="after")
    def validate_report(self):
        return _validate_safety_flags(self, "macro regime provider capability report")


class MacroRegimeFreshnessEntry(StrictModel):
    series_id: MacroRegimeSeriesId
    latest_observed_at: datetime | None = None
    latest_available_at: datetime | None = None
    stale: bool = False
    age_minutes: int | None = Field(default=None, ge=0)
    reason: str | None = None

    @field_validator("latest_observed_at", "latest_available_at", mode="before")
    @classmethod
    def normalize_dt(cls, value):
        return _aware(value)

    @field_validator("reason", mode="before")
    @classmethod
    def normalize_reason(cls, value):
        if value is None:
            return None
        return _upper_required(value, "reason")


class MacroRegimeFreshnessReport(_BaseReport):
    report_id: str = Field(..., min_length=1)
    entries: list[MacroRegimeFreshnessEntry] = Field(default_factory=list)
    stale_series_count: int = Field(default=0, ge=0)

    @field_validator("report_id", mode="before")
    @classmethod
    def normalize_id(cls, value):
        return _upper_required(value, "report_id")

    @model_validator(mode="after")
    def validate_report(self):
        return _validate_safety_flags(self, "macro regime freshness report")


class MacroRegimeConflictEntry(StrictModel):
    conflict_id: str = Field(..., min_length=1)
    field_name: str = Field(..., min_length=1)
    message: str = Field(..., min_length=1)

    @field_validator("conflict_id", "field_name", mode="before")
    @classmethod
    def normalize_upper(cls, value, info):
        return _upper_required(value, info.field_name)

    @field_validator("message", mode="before")
    @classmethod
    def normalize_message(cls, value):
        return _string_required(value, "message")


class MacroRegimeConflictReport(_BaseReport):
    report_id: str = Field(..., min_length=1)
    conflicts: list[MacroRegimeConflictEntry] = Field(default_factory=list)
    conflict_count: int = Field(default=0, ge=0)

    @field_validator("report_id", mode="before")
    @classmethod
    def normalize_id(cls, value):
        return _upper_required(value, "report_id")

    @model_validator(mode="after")
    def validate_report(self):
        return _validate_safety_flags(self, "macro regime conflict report")


class MacroRegimeGapEntry(StrictModel):
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


class MacroRegimeGapReport(_BaseReport):
    report_id: str = Field(..., min_length=1)
    readiness: MacroRegimeSnapshotReadiness
    gap_entries: list[MacroRegimeGapEntry] = Field(default_factory=list)

    @field_validator("report_id", mode="before")
    @classmethod
    def normalize_id(cls, value):
        return _upper_required(value, "report_id")

    @model_validator(mode="after")
    def validate_report(self):
        return _validate_safety_flags(self, "macro regime gap report")


class MacroRegimeEventWindowReport(_BaseReport):
    report_id: str = Field(..., min_length=1)
    windows: list[CanonicalMacroEventWindow] = Field(default_factory=list)
    active_window_count: int = Field(default=0, ge=0)
    upcoming_window_count: int = Field(default=0, ge=0)

    @field_validator("report_id", mode="before")
    @classmethod
    def normalize_id(cls, value):
        return _upper_required(value, "report_id")

    @model_validator(mode="after")
    def validate_report(self):
        return _validate_safety_flags(self, "macro regime event window report")


class CanonicalMacroRegimeSnapshot(_BaseReport):
    snapshot_id: str = Field(..., min_length=1)
    anchor_at: datetime
    available_at: datetime | None = None
    readiness: MacroRegimeSnapshotReadiness
    nq: CanonicalMacroSeriesPoint | None = None
    es: CanonicalMacroSeriesPoint | None = None
    vix: CanonicalMacroSeriesPoint | None = None
    dollar_strength: CanonicalMacroSeriesPoint | None = None
    us10y: CanonicalMacroSeriesPoint | None = None
    usdkrw: CanonicalMacroSeriesPoint | None = None
    active_event_ids: list[str] = Field(default_factory=list)
    upcoming_event_ids: list[str] = Field(default_factory=list)
    blocking_gap_categories: list[str] = Field(default_factory=list)

    @field_validator("snapshot_id", mode="before")
    @classmethod
    def normalize_id(cls, value):
        return _upper_required(value, "snapshot_id")

    @field_validator("anchor_at", "available_at", mode="before")
    @classmethod
    def normalize_dt(cls, value):
        return _aware(value)

    @field_validator("active_event_ids", "upcoming_event_ids", "blocking_gap_categories", mode="before")
    @classmethod
    def normalize_lists(cls, value, info):
        return _normalize_list(value, info.field_name)

    @model_validator(mode="after")
    def validate_report(self):
        return _validate_safety_flags(self, "macro regime snapshot")


class CanonicalRegimeClassification(_BaseReport):
    classification_id: str = Field(..., min_length=1)
    label: MacroRegimeClassificationLabel
    confidence_bucket: str = Field(..., min_length=1)
    rationale: str = Field(..., min_length=1)
    supporting_series_ids: list[str] = Field(default_factory=list)
    blocking_gap_categories: list[str] = Field(default_factory=list)

    @field_validator("classification_id", "confidence_bucket", mode="before")
    @classmethod
    def normalize_upper(cls, value, info):
        return _upper_required(value, info.field_name)

    @field_validator("rationale", mode="before")
    @classmethod
    def normalize_rationale(cls, value):
        return _string_required(value, "rationale")

    @field_validator("supporting_series_ids", "blocking_gap_categories", mode="before")
    @classmethod
    def normalize_lists(cls, value, info):
        return _normalize_list(value, info.field_name)

    @model_validator(mode="after")
    def validate_report(self):
        return _validate_safety_flags(self, "macro regime classification")


class MacroRegimeV7IntegrationReport(_BaseReport):
    report_id: str = Field(..., min_length=1)
    market_regime_context: str = Field(..., min_length=1)
    sizing_risk_context: str = Field(..., min_length=1)
    event_risk_context: str = Field(..., min_length=1)
    breadth_routing_context: str = Field(..., min_length=1)
    blocking_gap_categories: list[str] = Field(default_factory=list)

    @field_validator(
        "report_id",
        "market_regime_context",
        "sizing_risk_context",
        "event_risk_context",
        "breadth_routing_context",
        mode="before",
    )
    @classmethod
    def normalize_upper(cls, value, info):
        return _upper_required(value, info.field_name)

    @field_validator("blocking_gap_categories", mode="before")
    @classmethod
    def normalize_gaps(cls, value):
        return _normalize_list(value, "blocking_gap_categories")

    @model_validator(mode="after")
    def validate_report(self):
        return _validate_safety_flags(self, "macro regime v7 integration report")


class MacroRegimeV8IntegrationReport(_BaseReport):
    report_id: str = Field(..., min_length=1)
    domestic_snapshot_macro_context: str = Field(..., min_length=1)
    macro_bias: str = Field(..., min_length=1)
    event_overlay: str = Field(..., min_length=1)
    attachable_to_v8_snapshot: bool = True
    blocking_gap_categories: list[str] = Field(default_factory=list)

    @field_validator("report_id", "domestic_snapshot_macro_context", "macro_bias", "event_overlay", mode="before")
    @classmethod
    def normalize_upper(cls, value, info):
        return _upper_required(value, info.field_name)

    @field_validator("blocking_gap_categories", mode="before")
    @classmethod
    def normalize_gaps(cls, value):
        return _normalize_list(value, "blocking_gap_categories")

    @model_validator(mode="after")
    def validate_report(self):
        return _validate_safety_flags(self, "macro regime v8 integration report")


class MacroRegimeSafetyReport(_BaseReport):
    report_id: str = Field(..., min_length=1)
    findings: list[str] = Field(default_factory=list)

    @field_validator("report_id", mode="before")
    @classmethod
    def normalize_id(cls, value):
        return _upper_required(value, "report_id")

    @field_validator("findings", mode="before")
    @classmethod
    def normalize_findings(cls, value):
        return _normalize_list(value, "findings")

    @model_validator(mode="after")
    def validate_report(self):
        return _validate_safety_flags(self, "macro regime safety report")


class MockedProviderPayload(StrictModel):
    payload_id: str = Field(..., min_length=1)
    provider: MacroRegimeProvider
    series_id: MacroRegimeSeriesId | None = None
    source_ref: str = Field(..., min_length=1)
    payload: dict[str, object] = Field(default_factory=dict)

    @field_validator("payload_id", mode="before")
    @classmethod
    def normalize_payload_id(cls, value):
        return _upper_required(value, "payload_id")

    @field_validator("source_ref", mode="before")
    @classmethod
    def normalize_source_ref(cls, value):
        return _validate_local_path(value, "source_ref")


class MacroRegimePipelineInput(_BaseReport):
    pipeline_id: str = Field(..., min_length=1)
    anchor_at: datetime
    available_at: datetime | None = None
    max_data_age_minutes: int = Field(default=1440, ge=1)
    provider_definitions: list[MacroRegimeProviderDefinition] = Field(default_factory=list)
    fred_series_requests: list[FredSeriesRequest] = Field(default_factory=list)
    manual_series_points: list[CanonicalMacroSeriesPoint] = Field(default_factory=list)
    manual_events: list[CanonicalMacroEvent] = Field(default_factory=list)
    mocked_provider_payloads: list[MockedProviderPayload] = Field(default_factory=list)
    audit_records: list[MacroRegimeAuditRecord] = Field(default_factory=list)

    @field_validator("pipeline_id", mode="before")
    @classmethod
    def normalize_id(cls, value):
        return _upper_required(value, "pipeline_id")

    @field_validator("anchor_at", "available_at", mode="before")
    @classmethod
    def normalize_dt(cls, value):
        return _aware(value)

    @model_validator(mode="after")
    def validate_report(self):
        return _validate_safety_flags(self, "macro regime pipeline input")


class MacroRegimePipelineResult(StrictModel):
    snapshot: CanonicalMacroRegimeSnapshot
    classification: CanonicalRegimeClassification
    provider_capability_report: MacroRegimeProviderCapabilityReport
    freshness_report: MacroRegimeFreshnessReport
    conflict_report: MacroRegimeConflictReport
    event_window_report: MacroRegimeEventWindowReport
    v7_integration_report: MacroRegimeV7IntegrationReport
    v8_integration_report: MacroRegimeV8IntegrationReport
    gap_report: MacroRegimeGapReport
    safety_report: MacroRegimeSafetyReport
