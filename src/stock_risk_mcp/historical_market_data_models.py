from __future__ import annotations

from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any

from pydantic import Field, field_validator, model_validator

from stock_risk_mcp.feature_store_models import FeatureStorePriceBar, FeatureStoreSourceKind, FeatureStoreSourceRef
from stock_risk_mcp.models import StrictModel


class StrEnum(str, Enum):
    pass


ScalarValue = int | float | str | bool | None


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


def _normalize_list(value, field_name: str, *, upper: bool = False) -> list[str]:
    if value is None:
        return []
    if isinstance(value, (str, bytes)) or not isinstance(value, list):
        raise ValueError(f"{field_name} must be a list")
    if upper:
        return [_upper_required(item, field_name) for item in value]
    return [_string_required(item, field_name) for item in value]


def _validate_relative_path(value: str | None, field_name: str) -> str | None:
    if value is None:
        return None
    cleaned = _string_required(value, field_name)
    lowered = cleaned.lower()
    if "://" in lowered or lowered.startswith("//"):
        raise ValueError(f"{field_name} must be a local path")
    path = Path(cleaned)
    if path.is_absolute():
        raise ValueError(f"{field_name} must be relative")
    if ".." in path.parts:
        raise ValueError(f"{field_name} must not contain path traversal")
    return cleaned


def _validate_scalar_map(value: dict[str, Any], field_name: str) -> dict[str, ScalarValue]:
    if not isinstance(value, dict):
        raise ValueError(f"{field_name} must be a dict")
    blocked = ("credential", "token", "secret", "authorization", "api_key", "account", "order")
    normalized: dict[str, ScalarValue] = {}
    for key, raw in value.items():
        name = _string_required(key, f"{field_name}.key")
        lowered = name.lower()
        if any(marker in lowered for marker in blocked):
            raise ValueError(f"{field_name} contains blocked field name: {name}")
        if isinstance(raw, bool) or raw is None or isinstance(raw, (int, float, str)):
            normalized[name] = raw
            continue
        raise ValueError(f"{field_name} values must be scalar only")
    return normalized


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
        "no_model_training",
        "no_paper_trading",
    ):
        if not getattr(model, flag_name):
            raise ValueError(f"{context} must remain {flag_name}")
    return model


class HistoricalMarketDataProvider(StrEnum):
    KIWOOM_REST = "KIWOOM_REST"
    LOCAL_FIXTURE = "LOCAL_FIXTURE"
    MOCK_CAPTURE = "MOCK_CAPTURE"


class HistoricalMarketDataApiId(StrEnum):
    KA10079 = "KA10079"
    KA10080 = "KA10080"
    KA10081 = "KA10081"
    KA10082 = "KA10082"
    KA10083 = "KA10083"
    KA10094 = "KA10094"


class HistoricalMarketDataInterval(StrEnum):
    TICK = "TICK"
    ONE_MINUTE = "1M"
    ONE_DAY = "1D"
    ONE_WEEK = "1W"
    ONE_MONTH = "1MO"
    ONE_YEAR = "1Y"


class HistoricalMarketDataMode(StrEnum):
    CAPTURE_PLAN_ONLY = "CAPTURE_PLAN_ONLY"
    MANUAL_IMPORT_ONLY = "MANUAL_IMPORT_ONLY"
    MOCK_CAPTURE_ONLY = "MOCK_CAPTURE_ONLY"
    REAL_OPT_IN_BOUNDARY = "REAL_OPT_IN_BOUNDARY"


class HistoricalMarketDataSourceKind(StrEnum):
    MANUAL_IMPORT_JSON = "MANUAL_IMPORT_JSON"
    MOCK_CAPTURE_PAYLOAD = "MOCK_CAPTURE_PAYLOAD"
    RAW_LAKE_RECORD = "RAW_LAKE_RECORD"
    NORMALIZED_OHLCV = "NORMALIZED_OHLCV"
    V8_CHART_EVIDENCE = "V8_CHART_EVIDENCE"
    V10_PRICE_HISTORY_MANIFEST = "V10_PRICE_HISTORY_MANIFEST"
    UNKNOWN = "UNKNOWN"


class HistoricalMarketDataCaptureProfile(StrEnum):
    SMOKE_PROFILE = "SMOKE_PROFILE"
    DAILY_RESEARCH_PROFILE = "DAILY_RESEARCH_PROFILE"
    INTRADAY_CANDIDATE_PROFILE = "INTRADAY_CANDIDATE_PROFILE"
    FULL_INTRADAY_PROFILE = "FULL_INTRADAY_PROFILE"
    FULL_INTRADAY_DISABLED = "FULL_INTRADAY_DISABLED"


class HistoricalMarketDataStorageFormat(StrEnum):
    IN_MEMORY = "IN_MEMORY"
    JSON = "JSON"
    JSONL = "JSONL"
    PARQUET = "PARQUET"
    DUCKDB = "DUCKDB"


class HistoricalMarketDataSchemaStatus(StrEnum):
    SCHEMA_READY = "SCHEMA_READY"
    CAPABILITY_ONLY = "CAPABILITY_ONLY"
    SCHEMA_GAP = "SCHEMA_GAP"
    BLOCKED = "BLOCKED"


class HistoricalMarketDataCredentialPolicy(StrEnum):
    NOT_REQUIRED = "NOT_REQUIRED"
    MANUAL_IMPORT_ONLY = "MANUAL_IMPORT_ONLY"
    KEY_REF_ONLY = "KEY_REF_ONLY"
    TOKEN_PROVIDER_ONLY = "TOKEN_PROVIDER_ONLY"
    BLOCKED = "BLOCKED"


class HistoricalMarketDataReadinessStatus(StrEnum):
    API_CATALOG_READY = "API_CATALOG_READY"
    CAPTURE_PLAN_READY = "CAPTURE_PLAN_READY"
    MANUAL_IMPORT_READY = "MANUAL_IMPORT_READY"
    RAW_LAKE_READY = "RAW_LAKE_READY"
    NORMALIZED_READY = "NORMALIZED_READY"
    COVERAGE_READY = "COVERAGE_READY"
    V10_MANIFEST_READY = "V10_MANIFEST_READY"
    PROVIDER_SETUP_REQUIRED = "PROVIDER_SETUP_REQUIRED"
    PREFLIGHT_READY = "PREFLIGHT_READY"
    REAL_CAPTURE_READY = "REAL_CAPTURE_READY"
    REAL_CAPTURE_EXECUTED = "REAL_CAPTURE_EXECUTED"
    PROVIDER_CHART_ERROR = "PROVIDER_CHART_ERROR"
    PROVIDER_EMPTY_RESPONSE = "PROVIDER_EMPTY_RESPONSE"
    BLOCKED_AUTH_OR_TOKEN = "BLOCKED_AUTH_OR_TOKEN"
    DEPENDENCY_GAP_KIWOOM_ENDPOINT_SCHEMA = "DEPENDENCY_GAP_KIWOOM_ENDPOINT_SCHEMA"
    BLOCKED_REAL_NETWORK_NOT_IMPLEMENTED = "BLOCKED_REAL_NETWORK_NOT_IMPLEMENTED"
    AUDIT_READY = "AUDIT_READY"
    DATA_GAP = "DATA_GAP"
    STALE = "STALE"
    CONFLICT = "CONFLICT"
    BLOCKED = "BLOCKED"
    RESEARCH_ONLY = "RESEARCH_ONLY"


class HistoricalChartCaptureDecision(StrEnum):
    ALLOWED = "ALLOWED"
    BLOCKED = "BLOCKED"


class HistoricalOhlcvPartitionSpec(StrictModel):
    partition_keys: list[str] = Field(default_factory=list)

    @field_validator("partition_keys", mode="before")
    @classmethod
    def normalize_keys(cls, value):
        return _normalize_list(value, "partition_keys", upper=True)


class HistoricalMarketDataOptIn(StrictModel):
    allow_real_chart_capture: bool = False
    acknowledge_readonly_only: bool = False
    acknowledge_no_orders: bool = False
    acknowledge_user_initiated: bool = False
    acknowledge_rate_limit_and_capacity: bool = False
    acknowledge_credential_redaction: bool = False


class HistoricalMarketDataTransportKind(StrEnum):
    MOCK = "MOCK"
    REAL_KIWOOM_CHART = "REAL_KIWOOM_CHART"


class HistoricalMarketDataRedactionStatus(StrEnum):
    PASSED = "PASSED"
    BLOCKED = "BLOCKED"


class HistoricalMarketDataCredentialRef(StrictModel):
    credential_ref_id: str = Field(..., min_length=1)
    credential_ref_dir: str | None = Field(default=None, min_length=1)
    appkey_ref_path: str | None = Field(default=None, min_length=1)
    secretkey_ref_path: str | None = Field(default=None, min_length=1)
    redaction_status: HistoricalMarketDataRedactionStatus = HistoricalMarketDataRedactionStatus.PASSED

    @field_validator("credential_ref_id", mode="before")
    @classmethod
    def normalize_id(cls, value):
        return _upper_required(value, "credential_ref_id")

    @field_validator("credential_ref_dir", "appkey_ref_path", "secretkey_ref_path", mode="before")
    @classmethod
    def normalize_paths(cls, value, info):
        if value is None:
            return None
        return _string_required(value, info.field_name)

    @model_validator(mode="after")
    def validate_ref(self):
        has_dir = bool(self.credential_ref_dir)
        has_explicit = bool(self.appkey_ref_path and self.secretkey_ref_path)
        if not has_dir and not has_explicit:
            raise ValueError("credential ref requires credential_ref_dir or both appkey_ref_path and secretkey_ref_path")
        if (self.appkey_ref_path is None) != (self.secretkey_ref_path is None):
            raise ValueError("explicit credential ref paths must include both appkey_ref_path and secretkey_ref_path")
        return self


class HistoricalMarketDataRealCaptureConfig(StrictModel):
    provider: HistoricalMarketDataProvider = HistoricalMarketDataProvider.KIWOOM_REST
    credential_ref: HistoricalMarketDataCredentialRef | None = None
    max_request_count: int = Field(default=20, ge=1, le=500)
    max_continuation_pages: int = Field(default=3, ge=1, le=100)
    timeout_seconds: int = Field(default=10, ge=1, le=60)
    retry_count: int = Field(default=1, ge=0, le=3)
    allow_partial_success: bool = True
    transport_kind: HistoricalMarketDataTransportKind = HistoricalMarketDataTransportKind.MOCK


class _BaseSafety(StrictModel):
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
    no_model_training: bool = True
    no_paper_trading: bool = True


class HistoricalChartCaptureRunTaskResult(_BaseSafety):
    task_id: str = Field(..., min_length=1)
    request_id: str = Field(..., min_length=1)
    execution_decision: HistoricalChartCaptureDecision
    success: bool = False
    page_count: int = Field(default=0, ge=0)
    raw_response_count: int = Field(default=0, ge=0)
    normalized_row_count: int = Field(default=0, ge=0)
    provider_return_code: int | None = None
    provider_return_msg: str | None = None
    chart_response_received: bool = False
    row_count: int = Field(default=0, ge=0)
    blocked_reasons: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)

    @field_validator("task_id", "request_id", mode="before")
    @classmethod
    def normalize_upper(cls, value, info):
        return _upper_required(value, info.field_name)

    @field_validator("blocked_reasons", "errors", mode="before")
    @classmethod
    def normalize_lists(cls, value, info):
        return _normalize_list(value, info.field_name, upper=info.field_name == "blocked_reasons")

    @model_validator(mode="after")
    def validate_result(self):
        return _validate_safety_flags(self, "capture run task result")


class HistoricalChartCaptureRunAudit(_BaseSafety):
    audit_id: str = Field(..., min_length=1)
    dataset_id: str = Field(..., min_length=1)
    transport_kind: HistoricalMarketDataTransportKind
    credential_ref_present: bool = False
    credential_policy: HistoricalMarketDataCredentialPolicy = HistoricalMarketDataCredentialPolicy.BLOCKED
    redaction_status: HistoricalMarketDataRedactionStatus = HistoricalMarketDataRedactionStatus.PASSED
    auth_header_present: bool = False
    task_results: list[HistoricalChartCaptureRunTaskResult] = Field(default_factory=list)
    blocked_reasons: list[str] = Field(default_factory=list)

    @field_validator("audit_id", "dataset_id", mode="before")
    @classmethod
    def normalize_upper(cls, value, info):
        return _upper_required(value, info.field_name)

    @field_validator("blocked_reasons", mode="before")
    @classmethod
    def normalize_blocked(cls, value):
        return _normalize_list(value, "blocked_reasons", upper=True)

    @model_validator(mode="after")
    def validate_audit(self):
        return _validate_safety_flags(self, "capture run audit")


class HistoricalChartCaptureRunResult(_BaseSafety):
    run_id: str = Field(..., min_length=1)
    dataset_id: str = Field(..., min_length=1)
    readiness_status: HistoricalMarketDataReadinessStatus
    task_results: list[HistoricalChartCaptureRunTaskResult] = Field(default_factory=list)
    raw_response_count: int = Field(default=0, ge=0)
    normalized_row_count: int = Field(default=0, ge=0)
    manifest: "HistoricalOhlcvDatasetManifest | None" = None
    coverage_report: "HistoricalMarketDataCoverageReport | None" = None
    freshness_report: "HistoricalMarketDataFreshnessReport | None" = None
    completeness_report: "HistoricalMarketDataCompletenessReport | None" = None
    gap_report: "HistoricalMarketDataGapReport | None" = None
    safety_report: "HistoricalMarketDataSafetyReport | None" = None
    audit_report: HistoricalChartCaptureRunAudit | None = None

    @field_validator("run_id", "dataset_id", mode="before")
    @classmethod
    def normalize_upper(cls, value, info):
        return _upper_required(value, info.field_name)

    @model_validator(mode="after")
    def validate_result(self):
        return _validate_safety_flags(self, "capture run result")


class _BaseSafety(StrictModel):
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
    no_model_training: bool = True
    no_paper_trading: bool = True


class HistoricalMarketDataAuditRecord(StrictModel):
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


class HistoricalMarketDataGapEntry(StrictModel):
    gap_id: str = Field(..., min_length=1)
    gap_category: str = Field(..., min_length=1)
    severity: str = Field(..., min_length=1)
    message: str = Field(..., min_length=1)

    @field_validator("gap_id", "gap_category", "severity", mode="before")
    @classmethod
    def normalize_upper(cls, value, info):
        return _upper_required(value, info.field_name)


class HistoricalMarketDataGapReport(_BaseSafety):
    report_id: str = Field(..., min_length=1)
    readiness_status: HistoricalMarketDataReadinessStatus
    gap_entries: list[HistoricalMarketDataGapEntry] = Field(default_factory=list)

    @field_validator("report_id", mode="before")
    @classmethod
    def normalize_report_id(cls, value):
        return _upper_required(value, "report_id")

    @model_validator(mode="after")
    def validate_report(self):
        return _validate_safety_flags(self, "gap report")


class HistoricalMarketDataApiCapability(StrictModel):
    api_id: HistoricalMarketDataApiId
    provider: HistoricalMarketDataProvider
    interval: HistoricalMarketDataInterval
    schema_status: HistoricalMarketDataSchemaStatus
    credential_policy: HistoricalMarketDataCredentialPolicy
    request_path: str = Field(..., min_length=1)
    request_fields: list[str] = Field(default_factory=list)
    continuation_supported: bool = True
    manual_import_supported: bool = True
    mocked_capture_supported: bool = True
    real_capture_boundary_supported: bool = False
    notes: list[str] = Field(default_factory=list)

    @field_validator("request_path", mode="before")
    @classmethod
    def normalize_path(cls, value):
        return _string_required(value, "request_path")

    @field_validator("request_fields", "notes", mode="before")
    @classmethod
    def normalize_lists(cls, value, info):
        return _normalize_list(value, info.field_name, upper=info.field_name == "request_fields")


class HistoricalMarketDataApiCatalogReport(_BaseSafety):
    report_id: str = Field(..., min_length=1)
    capabilities: list[HistoricalMarketDataApiCapability] = Field(default_factory=list)
    schema_ready_api_ids: list[str] = Field(default_factory=list)
    capability_only_api_ids: list[str] = Field(default_factory=list)
    schema_gap_api_ids: list[str] = Field(default_factory=list)

    @field_validator("report_id", mode="before")
    @classmethod
    def normalize_report_id(cls, value):
        return _upper_required(value, "report_id")

    @field_validator("schema_ready_api_ids", "capability_only_api_ids", "schema_gap_api_ids", mode="before")
    @classmethod
    def normalize_api_ids(cls, value):
        return _normalize_list(value, "api_ids", upper=True)

    @model_validator(mode="after")
    def validate_report(self):
        return _validate_safety_flags(self, "api catalog report")


class HistoricalChartRequestSpec(StrictModel):
    request_id: str = Field(..., min_length=1)
    api_id: HistoricalMarketDataApiId
    provider_symbol: str = Field(..., min_length=1)
    canonical_instrument_id: str = Field(..., min_length=1)
    interval: HistoricalMarketDataInterval
    base_dt: str | None = None
    start_at: datetime | None = None
    end_at: datetime | None = None
    tic_scope: str | None = None
    upd_stkpc_tp: str = "1"
    cont_yn: str = "N"
    next_key: str = ""
    source_ref: str = Field(..., min_length=1)

    @field_validator("request_id", "provider_symbol", "canonical_instrument_id", "upd_stkpc_tp", "cont_yn", "next_key", "source_ref", mode="before")
    @classmethod
    def normalize_upper(cls, value, info):
        if info.field_name == "source_ref":
            return _string_required(value, info.field_name)
        if info.field_name == "next_key":
            return "" if value is None else str(value).strip().upper()
        return _upper_required(value, info.field_name)

    @field_validator("base_dt", mode="before")
    @classmethod
    def normalize_base_dt(cls, value):
        if value is None:
            return None
        return _string_required(value, "base_dt")

    @field_validator("start_at", "end_at", mode="before")
    @classmethod
    def normalize_dt(cls, value):
        return _aware(value)


class HistoricalChartRequestPreview(_BaseSafety):
    report_id: str = Field(..., min_length=1)
    api_id: HistoricalMarketDataApiId
    provider: HistoricalMarketDataProvider
    method: str = "POST"
    path: str = Field(..., min_length=1)
    headers: dict[str, str] = Field(default_factory=dict)
    body_json: dict[str, ScalarValue] = Field(default_factory=dict)
    token_reference_label: str = "TOKEN_REF_ONLY"

    @field_validator("report_id", "method", "path", "token_reference_label", mode="before")
    @classmethod
    def normalize_strings(cls, value, info):
        if info.field_name == "path":
            return _string_required(value, "path")
        return _upper_required(value, info.field_name)

    @field_validator("body_json", mode="before")
    @classmethod
    def normalize_body(cls, value):
        return _validate_scalar_map(value or {}, "body_json")

    @model_validator(mode="after")
    def validate_preview(self):
        return _validate_safety_flags(self, "request preview")


class HistoricalChartCaptureTask(StrictModel):
    task_id: str = Field(..., min_length=1)
    request_spec: HistoricalChartRequestSpec
    request_preview: HistoricalChartRequestPreview
    capability: HistoricalMarketDataApiCapability
    execution_decision: HistoricalChartCaptureDecision
    blocking_reasons: list[str] = Field(default_factory=list)

    @field_validator("task_id", mode="before")
    @classmethod
    def normalize_id(cls, value):
        return _upper_required(value, "task_id")

    @field_validator("blocking_reasons", mode="before")
    @classmethod
    def normalize_reasons(cls, value):
        return _normalize_list(value, "blocking_reasons", upper=True)


class HistoricalChartCapturePlan(_BaseSafety):
    plan_id: str = Field(..., min_length=1)
    dataset_id: str = Field(..., min_length=1)
    capture_profile: HistoricalMarketDataCaptureProfile
    mode: HistoricalMarketDataMode
    tasks: list[HistoricalChartCaptureTask] = Field(default_factory=list)
    readiness_status: HistoricalMarketDataReadinessStatus
    bounded: bool = True

    @field_validator("plan_id", "dataset_id", mode="before")
    @classmethod
    def normalize_upper(cls, value, info):
        return _upper_required(value, info.field_name)

    @model_validator(mode="after")
    def validate_plan(self):
        return _validate_safety_flags(self, "capture plan")


class HistoricalChartRawResponse(_BaseSafety):
    response_id: str = Field(..., min_length=1)
    request_id: str = Field(..., min_length=1)
    api_id: HistoricalMarketDataApiId
    provider: HistoricalMarketDataProvider
    provider_symbol: str = Field(..., min_length=1)
    canonical_instrument_id: str = Field(..., min_length=1)
    imported_at: datetime
    available_at: datetime
    source_kind: HistoricalMarketDataSourceKind
    source_ref: str = Field(..., min_length=1)
    cont_yn: str = "N"
    next_key: str = ""
    payload_summary: dict[str, ScalarValue] = Field(default_factory=dict)
    raw_payload_redacted: bool = True
    raw_payload: dict[str, Any] = Field(default_factory=dict)

    @field_validator(
        "response_id",
        "request_id",
        "provider_symbol",
        "canonical_instrument_id",
        "source_ref",
        "cont_yn",
        "next_key",
        mode="before",
    )
    @classmethod
    def normalize_upper(cls, value, info):
        if info.field_name == "source_ref":
            return _string_required(value, info.field_name)
        if info.field_name == "next_key":
            return "" if value is None else str(value).strip().upper()
        return _upper_required(value, info.field_name)

    @field_validator("imported_at", "available_at", mode="before")
    @classmethod
    def normalize_dt(cls, value):
        return _aware(value)

    @field_validator("payload_summary", mode="before")
    @classmethod
    def normalize_summary(cls, value):
        return _validate_scalar_map(value or {}, "payload_summary")

    @model_validator(mode="after")
    def validate_response(self):
        return _validate_safety_flags(self, "raw response")


class HistoricalChartImportFile(StrictModel):
    import_id: str = Field(..., min_length=1)
    file_path: str = Field(..., min_length=1)
    request_id: str = Field(..., min_length=1)
    api_id: HistoricalMarketDataApiId
    provider_symbol: str = Field(..., min_length=1)
    canonical_instrument_id: str = Field(..., min_length=1)
    available_at: datetime
    source_kind: HistoricalMarketDataSourceKind = HistoricalMarketDataSourceKind.MANUAL_IMPORT_JSON

    @field_validator("import_id", "request_id", "provider_symbol", "canonical_instrument_id", mode="before")
    @classmethod
    def normalize_upper(cls, value, info):
        return _upper_required(value, info.field_name)

    @field_validator("file_path", mode="before")
    @classmethod
    def normalize_path(cls, value):
        return _string_required(value, "file_path")

    @field_validator("available_at", mode="before")
    @classmethod
    def normalize_dt(cls, value):
        return _aware(value)


class HistoricalChartRawLakeRecord(_BaseSafety):
    record_id: str = Field(..., min_length=1)
    response_id: str = Field(..., min_length=1)
    dataset_id: str = Field(..., min_length=1)
    relative_path: str = Field(..., min_length=1)
    storage_format: HistoricalMarketDataStorageFormat
    source_kind: HistoricalMarketDataSourceKind
    redacted: bool = True
    persisted_at: datetime

    @field_validator("record_id", "response_id", "dataset_id", mode="before")
    @classmethod
    def normalize_upper(cls, value, info):
        return _upper_required(value, info.field_name)

    @field_validator("relative_path", mode="before")
    @classmethod
    def normalize_relative(cls, value):
        normalized = _validate_relative_path(value, "relative_path")
        if normalized is None:
            raise ValueError("relative_path is required")
        return normalized

    @field_validator("persisted_at", mode="before")
    @classmethod
    def normalize_dt(cls, value):
        return _aware(value)

    @model_validator(mode="after")
    def validate_record(self):
        return _validate_safety_flags(self, "raw lake record")


class HistoricalOhlcvRow(_BaseSafety):
    row_id: str = Field(..., min_length=1)
    dataset_id: str = Field(..., min_length=1)
    instrument_id: str = Field(..., min_length=1)
    provider_symbol: str = Field(..., min_length=1)
    interval: HistoricalMarketDataInterval
    api_id: HistoricalMarketDataApiId
    observed_at: datetime
    available_at: datetime
    open_price: float | None = None
    high_price: float | None = None
    low_price: float | None = None
    close_price: float = Field(..., gt=0)
    volume: float | None = Field(default=None, ge=0)
    adjusted: bool = True
    adjustment_policy: str = Field(..., min_length=1)
    continuation_cont_yn: str = "N"
    continuation_next_key: str = ""
    source_ref: str = Field(..., min_length=1)
    quality_flags: list[str] = Field(default_factory=list)

    @field_validator(
        "row_id",
        "dataset_id",
        "instrument_id",
        "provider_symbol",
        "adjustment_policy",
        "continuation_cont_yn",
        "continuation_next_key",
        "source_ref",
        mode="before",
    )
    @classmethod
    def normalize_upper(cls, value, info):
        if info.field_name in {"adjustment_policy", "source_ref"}:
            return _string_required(value, info.field_name)
        if info.field_name == "continuation_next_key":
            return "" if value is None else str(value).strip().upper()
        return _upper_required(value, info.field_name)

    @field_validator("observed_at", "available_at", mode="before")
    @classmethod
    def normalize_dt(cls, value):
        return _aware(value)

    @field_validator("quality_flags", mode="before")
    @classmethod
    def normalize_flags(cls, value):
        return _normalize_list(value, "quality_flags", upper=True)

    @model_validator(mode="after")
    def validate_row(self):
        return _validate_safety_flags(self, "ohlcv row")


class HistoricalOhlcvDatasetManifest(_BaseSafety):
    manifest_id: str = Field(..., min_length=1)
    dataset_id: str = Field(..., min_length=1)
    store_root: str = Field(..., min_length=1)
    manifest_path: str | None = None
    ohlcv_rows_path: str | None = None
    partition_spec: HistoricalOhlcvPartitionSpec
    row_count: int = Field(0, ge=0)
    intervals: list[str] = Field(default_factory=list)
    instrument_ids: list[str] = Field(default_factory=list)
    storage_format: HistoricalMarketDataStorageFormat
    storage_refs: list[str] = Field(default_factory=list)
    readiness_status: HistoricalMarketDataReadinessStatus

    @field_validator("manifest_id", "dataset_id", "store_root", mode="before")
    @classmethod
    def normalize_strings(cls, value, info):
        if info.field_name == "store_root":
            return _string_required(value, "store_root")
        return _upper_required(value, info.field_name)

    @field_validator("manifest_path", "ohlcv_rows_path", mode="before")
    @classmethod
    def normalize_optional_paths(cls, value, info):
        if value is None:
            return None
        return _string_required(value, info.field_name)

    @field_validator("intervals", "instrument_ids", "storage_refs", mode="before")
    @classmethod
    def normalize_lists(cls, value, info):
        return _normalize_list(value, info.field_name, upper=info.field_name != "storage_refs")

    @model_validator(mode="after")
    def validate_manifest(self):
        return _validate_safety_flags(self, "dataset manifest")


class HistoricalMarketDataCoverageReport(_BaseSafety):
    report_id: str = Field(..., min_length=1)
    readiness_status: HistoricalMarketDataReadinessStatus
    covered_instrument_ids: list[str] = Field(default_factory=list)
    covered_intervals: list[str] = Field(default_factory=list)
    missing_instrument_ids: list[str] = Field(default_factory=list)
    continuation_incomplete_request_ids: list[str] = Field(default_factory=list)
    row_count: int = Field(0, ge=0)

    @field_validator("report_id", mode="before")
    @classmethod
    def normalize_id(cls, value):
        return _upper_required(value, "report_id")

    @field_validator(
        "covered_instrument_ids",
        "covered_intervals",
        "missing_instrument_ids",
        "continuation_incomplete_request_ids",
        mode="before",
    )
    @classmethod
    def normalize_lists(cls, value, info):
        return _normalize_list(value, info.field_name, upper=True)

    @model_validator(mode="after")
    def validate_report(self):
        return _validate_safety_flags(self, "coverage report")


class HistoricalMarketDataFreshnessReport(_BaseSafety):
    report_id: str = Field(..., min_length=1)
    readiness_status: HistoricalMarketDataReadinessStatus
    newest_observed_at: datetime | None = None
    oldest_observed_at: datetime | None = None
    stale: bool = False

    @field_validator("report_id", mode="before")
    @classmethod
    def normalize_id(cls, value):
        return _upper_required(value, "report_id")

    @field_validator("newest_observed_at", "oldest_observed_at", mode="before")
    @classmethod
    def normalize_dt(cls, value):
        return _aware(value)

    @model_validator(mode="after")
    def validate_report(self):
        return _validate_safety_flags(self, "freshness report")


class HistoricalMarketDataCompletenessReport(_BaseSafety):
    report_id: str = Field(..., min_length=1)
    readiness_status: HistoricalMarketDataReadinessStatus
    duplicate_row_count: int = Field(0, ge=0)
    out_of_order_row_count: int = Field(0, ge=0)
    missing_field_row_count: int = Field(0, ge=0)
    continuation_gap_count: int = Field(0, ge=0)

    @field_validator("report_id", mode="before")
    @classmethod
    def normalize_id(cls, value):
        return _upper_required(value, "report_id")

    @model_validator(mode="after")
    def validate_report(self):
        return _validate_safety_flags(self, "completeness report")


class HistoricalMarketDataStorageCapabilityRow(StrictModel):
    storage_format: HistoricalMarketDataStorageFormat
    supported: bool = False
    status: HistoricalMarketDataReadinessStatus
    notes: list[str] = Field(default_factory=list)

    @field_validator("notes", mode="before")
    @classmethod
    def normalize_notes(cls, value):
        return _normalize_list(value, "notes")


class HistoricalMarketDataStorageCapabilityReport(_BaseSafety):
    report_id: str = Field(..., min_length=1)
    rows: list[HistoricalMarketDataStorageCapabilityRow] = Field(default_factory=list)

    @field_validator("report_id", mode="before")
    @classmethod
    def normalize_id(cls, value):
        return _upper_required(value, "report_id")

    @model_validator(mode="after")
    def validate_report(self):
        return _validate_safety_flags(self, "storage capability report")


class HistoricalMarketDataV8IntegrationReport(_BaseSafety):
    report_id: str = Field(..., min_length=1)
    chart_schema_alignment_ready: bool = False
    manual_import_lineage_ready: bool = False
    readonly_capture_boundary_preserved: bool = True

    @field_validator("report_id", mode="before")
    @classmethod
    def normalize_id(cls, value):
        return _upper_required(value, "report_id")

    @model_validator(mode="after")
    def validate_report(self):
        return _validate_safety_flags(self, "v8 integration report")


class HistoricalMarketDataV10IntegrationReport(_BaseSafety):
    report_id: str = Field(..., min_length=1)
    price_history_rows_ready: bool = False
    normalized_manifest_ready: bool = False
    feature_store_dataset_compatible: bool = False
    v10_price_history_rows: list[FeatureStorePriceBar] = Field(default_factory=list)

    @field_validator("report_id", mode="before")
    @classmethod
    def normalize_id(cls, value):
        return _upper_required(value, "report_id")

    @model_validator(mode="after")
    def validate_report(self):
        return _validate_safety_flags(self, "v10 integration report")


class HistoricalMarketDataV11IntegrationReport(_BaseSafety):
    report_id: str = Field(..., min_length=1)
    paper_evaluation_replay_ready: bool = False
    interval_support_ready: bool = False
    ohlcv_label_simulation_ready: bool = False

    @field_validator("report_id", mode="before")
    @classmethod
    def normalize_id(cls, value):
        return _upper_required(value, "report_id")

    @model_validator(mode="after")
    def validate_report(self):
        return _validate_safety_flags(self, "v11 integration report")


class HistoricalMarketDataStrategyResearchSupport(StrEnum):
    SUPPORTED = "SUPPORTED"
    PARTIAL = "PARTIAL"
    UNSUPPORTED = "UNSUPPORTED"


class HistoricalMarketDataStrategyResearchReadinessItem(StrictModel):
    strategy_family: str = Field(..., min_length=1)
    support: HistoricalMarketDataStrategyResearchSupport
    rationale: str = Field(..., min_length=1)

    @field_validator("strategy_family", mode="before")
    @classmethod
    def normalize_family(cls, value):
        return _string_required(value, "strategy_family")


class HistoricalMarketDataStrategyResearchReadinessReport(_BaseSafety):
    report_id: str = Field(..., min_length=1)
    rows: list[HistoricalMarketDataStrategyResearchReadinessItem] = Field(default_factory=list)

    @field_validator("report_id", mode="before")
    @classmethod
    def normalize_id(cls, value):
        return _upper_required(value, "report_id")

    @model_validator(mode="after")
    def validate_report(self):
        return _validate_safety_flags(self, "strategy research readiness report")


class HistoricalMarketDataSafetyReport(_BaseSafety):
    report_id: str = Field(..., min_length=1)
    readiness_status: HistoricalMarketDataReadinessStatus
    findings: list[str] = Field(default_factory=list)
    real_capture_blocked: bool = True

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
        return _validate_safety_flags(self, "safety report")


class HistoricalMarketDataPipelineInput(StrictModel):
    pipeline_id: str = Field(..., min_length=1)
    dataset_id: str = Field(..., min_length=1)
    mode: HistoricalMarketDataMode
    capture_profile: HistoricalMarketDataCaptureProfile
    store_root: str = Field(..., min_length=1)
    raw_lake_root: str = Field(..., min_length=1)
    requested_storage_formats: list[HistoricalMarketDataStorageFormat] = Field(default_factory=list)
    partition_spec: HistoricalOhlcvPartitionSpec
    opt_in: HistoricalMarketDataOptIn = Field(default_factory=HistoricalMarketDataOptIn)
    real_capture_config: HistoricalMarketDataRealCaptureConfig | None = None
    request_specs: list[HistoricalChartRequestSpec] = Field(default_factory=list)
    manual_response_files: list[HistoricalChartImportFile] = Field(default_factory=list)
    mocked_responses: list[HistoricalChartRawResponse] = Field(default_factory=list)
    audit_records: list[HistoricalMarketDataAuditRecord] = Field(default_factory=list)

    @field_validator("pipeline_id", "dataset_id", mode="before")
    @classmethod
    def normalize_upper(cls, value, info):
        return _upper_required(value, info.field_name)

    @field_validator("store_root", "raw_lake_root", mode="before")
    @classmethod
    def normalize_roots(cls, value, info):
        return _string_required(value, info.field_name)

    @model_validator(mode="after")
    def validate_input(self):
        if self.capture_profile in {HistoricalMarketDataCaptureProfile.FULL_INTRADAY_PROFILE, HistoricalMarketDataCaptureProfile.FULL_INTRADAY_DISABLED} and self.mode != HistoricalMarketDataMode.CAPTURE_PLAN_ONLY:
            raise ValueError("full intraday profile remains blocked outside capture-plan-only mode")
        return self


class HistoricalMarketDataPipelineResult(_BaseSafety):
    api_catalog_report: HistoricalMarketDataApiCatalogReport
    capture_plan: HistoricalChartCapturePlan
    raw_responses: list[HistoricalChartRawResponse] = Field(default_factory=list)
    raw_lake_records: list[HistoricalChartRawLakeRecord] = Field(default_factory=list)
    ohlcv_rows: list[HistoricalOhlcvRow] = Field(default_factory=list)
    dataset_manifest: HistoricalOhlcvDatasetManifest
    coverage_report: HistoricalMarketDataCoverageReport
    freshness_report: HistoricalMarketDataFreshnessReport
    completeness_report: HistoricalMarketDataCompletenessReport
    storage_capability_report: HistoricalMarketDataStorageCapabilityReport
    v8_integration_report: HistoricalMarketDataV8IntegrationReport
    v10_integration_report: HistoricalMarketDataV10IntegrationReport
    v11_integration_report: HistoricalMarketDataV11IntegrationReport
    strategy_research_readiness_report: HistoricalMarketDataStrategyResearchReadinessReport
    safety_report: HistoricalMarketDataSafetyReport
    gap_report: HistoricalMarketDataGapReport

    @model_validator(mode="after")
    def validate_result(self):
        return _validate_safety_flags(self, "pipeline result")


def to_feature_store_price_bar(row: HistoricalOhlcvRow) -> FeatureStorePriceBar:
    return FeatureStorePriceBar(
        instrument_id=row.instrument_id,
        observed_at=row.observed_at,
        available_at=row.available_at,
        open_price=row.open_price,
        high_price=row.high_price,
        low_price=row.low_price,
        close_price=row.close_price,
        volume=row.volume,
        source_ref=FeatureStoreSourceRef(
            source_id=f"{row.row_id}-V10",
            source_kind=FeatureStoreSourceKind.LOCAL_PRICE_HISTORY_FIXTURE,
            sanitized_basename=Path(row.source_ref).name or f"{row.row_id}.json",
            relative_path=f"historical_market_data/{Path(row.source_ref).name or f'{row.row_id}.json'}",
            available_at=row.available_at,
        ),
    )
