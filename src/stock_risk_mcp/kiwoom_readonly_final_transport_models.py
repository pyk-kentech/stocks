from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from pydantic import Field, field_validator, model_validator

from stock_risk_mcp.kiwoom_readonly_snapshot_models import KiwoomReadonlyDomesticStockSnapshotReport
from stock_risk_mcp.kiwoom_manual_response_import_models import (
    KiwoomManualResponseCanonicalOutputReport,
    KiwoomManualResponseGapReport,
    KiwoomManualResponseImportResult,
    KiwoomManualResponseRoutingReport,
    KiwoomManualResponseSafetyReport,
)
from stock_risk_mcp.models import StrictModel


def _aware(value: datetime | str | None) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        parsed = value
    else:
        parsed = datetime.fromisoformat(str(value).strip())
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


def _normalize_string_list(value, field_name: str, *, upper: bool = True) -> list[str]:
    if value is None:
        return []
    if isinstance(value, (str, bytes)) or not isinstance(value, list):
        raise ValueError(f"{field_name} must be a list")
    if upper:
        return [_upper_required(item, field_name) for item in value]
    return [_string_required(item, field_name) for item in value]


def _normalize_dict(value, field_name: str) -> dict[str, object]:
    if value is None:
        return {}
    if not isinstance(value, dict):
        raise ValueError(f"{field_name} must be an object")
    return {str(key): item for key, item in value.items()}


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


class KiwoomReadonlyFinalTransportMode(StrEnum):
    BLOCKED_BY_DEFAULT = "BLOCKED_BY_DEFAULT"
    DRY_RUN_PREVIEW_ONLY = "DRY_RUN_PREVIEW_ONLY"
    MOCKED_TRANSPORT_ONLY = "MOCKED_TRANSPORT_ONLY"
    REAL_READONLY_OPT_IN = "REAL_READONLY_OPT_IN"
    REAL_READONLY_SINGLE_CALL_SMOKE = "REAL_READONLY_SINGLE_CALL_SMOKE"
    REJECTED = "REJECTED"


class KiwoomReadonlyFinalDomain(StrEnum):
    KIWOOM_MOCK_KRX = "KIWOOM_MOCK_KRX"
    KIWOOM_PROD_READONLY = "KIWOOM_PROD_READONLY"
    UNKNOWN_BLOCKED = "UNKNOWN_BLOCKED"


class KiwoomReadonlyFinalTokenProviderKind(StrEnum):
    DISABLED = "DISABLED"
    FAKE_PROVIDER = "FAKE_PROVIDER"
    ENV_EXPLICIT = "ENV_EXPLICIT"


class KiwoomReadonlyFinalStatus(StrEnum):
    PREVIEW_READY = "PREVIEW_READY"
    MOCKED_CALL_READY = "MOCKED_CALL_READY"
    REAL_READONLY_READY = "REAL_READONLY_READY"
    REAL_READONLY_SINGLE_CALL_READY = "REAL_READONLY_SINGLE_CALL_READY"
    REAL_READONLY_EXECUTED = "REAL_READONLY_EXECUTED"
    RESPONSE_CAPTURED = "RESPONSE_CAPTURED"
    RESPONSE_ROUTED = "RESPONSE_ROUTED"
    SNAPSHOT_VALIDATED = "SNAPSHOT_VALIDATED"
    V8_FINAL_READY = "V8_FINAL_READY"
    BLOCKED_DEFAULT = "BLOCKED_DEFAULT"
    BLOCKED_MISSING_OPT_IN = "BLOCKED_MISSING_OPT_IN"
    BLOCKED_API_NOT_ALLOWLISTED = "BLOCKED_API_NOT_ALLOWLISTED"
    BLOCKED_ACCOUNT_API = "BLOCKED_ACCOUNT_API"
    BLOCKED_ORDER_API = "BLOCKED_ORDER_API"
    BLOCKED_SENSITIVE_CONTENT = "BLOCKED_SENSITIVE_CONTENT"
    BLOCKED_NETWORK_IN_TEST = "BLOCKED_NETWORK_IN_TEST"
    BLOCKED_TOKEN_POLICY = "BLOCKED_TOKEN_POLICY"
    BLOCKED_CAPTURE_POLICY = "BLOCKED_CAPTURE_POLICY"
    BLOCKED_UNSAFE_PATH = "BLOCKED_UNSAFE_PATH"
    DATA_GAP = "DATA_GAP"
    SCHEMA_GAP = "SCHEMA_GAP"
    CAPTURE_GAP = "CAPTURE_GAP"
    REJECTED = "REJECTED"


class KiwoomReadonlyFinalCaptureStatus(StrEnum):
    CAPTURE_DISABLED = "CAPTURE_DISABLED"
    CAPTURE_READY = "CAPTURE_READY"
    CAPTURE_WRITTEN = "CAPTURE_WRITTEN"
    CAPTURE_BLOCKED_SENSITIVE_CONTENT = "CAPTURE_BLOCKED_SENSITIVE_CONTENT"
    CAPTURE_BLOCKED_ACCOUNT_ORDER_CONTENT = "CAPTURE_BLOCKED_ACCOUNT_ORDER_CONTENT"
    CAPTURE_SCHEMA_GAP = "CAPTURE_SCHEMA_GAP"
    CAPTURE_FAILED = "CAPTURE_FAILED"


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


class KiwoomReadonlyFinalOptIn(StrictModel):
    allow_real_readonly_network: bool = False
    acknowledge_readonly_only: bool = False
    acknowledge_no_orders: bool = False
    acknowledge_user_initiated: bool = False
    acknowledge_single_call_smoke: bool = False


class KiwoomReadonlyFinalTokenProviderSpec(_BaseReport):
    provider_kind: KiwoomReadonlyFinalTokenProviderKind = KiwoomReadonlyFinalTokenProviderKind.DISABLED
    env_var_name: str | None = None
    token_reference_label: str = "<REDACTED_TOKEN_REF>"

    @field_validator("env_var_name", mode="before")
    @classmethod
    def normalize_env_var_name(cls, value):
        if value in (None, ""):
            return None
        return _upper_required(value, "env_var_name")

    @field_validator("token_reference_label", mode="before")
    @classmethod
    def normalize_label(cls, value):
        return _string_required(value, "token_reference_label")

    @model_validator(mode="after")
    def validate_spec(self):
        _validate_safety_flags(self, "final token provider spec")
        if self.provider_kind == KiwoomReadonlyFinalTokenProviderKind.ENV_EXPLICIT and not self.env_var_name:
            raise ValueError("env_var_name is required for env token provider")
        if self.provider_kind != KiwoomReadonlyFinalTokenProviderKind.ENV_EXPLICIT and self.env_var_name:
            raise ValueError("env_var_name is only allowed for env token provider")
        return self


class KiwoomReadonlyFinalContinuation(StrictModel):
    cont_yn: str = "N"
    next_key: str = ""

    @field_validator("cont_yn", mode="before")
    @classmethod
    def normalize_cont_yn(cls, value):
        cleaned = _upper_required(value or "N", "cont_yn")
        if cleaned not in {"Y", "N"}:
            raise ValueError("cont_yn must be Y or N")
        return cleaned

    @field_validator("next_key", mode="before")
    @classmethod
    def normalize_next_key(cls, value):
        if value in (None, ""):
            return ""
        return _string_required(value, "next_key")


class KiwoomReadonlyFinalCapturePolicy(_BaseReport):
    enabled: bool = False
    capture_dir: str = "local_data/kiwoom_readonly_captures"

    @field_validator("capture_dir", mode="before")
    @classmethod
    def normalize_capture_dir(cls, value):
        return _validate_local_path(value, "capture_dir")

    @model_validator(mode="after")
    def validate_policy(self):
        return _validate_safety_flags(self, "final capture policy")


class KiwoomReadonlyFinalRequest(_BaseReport):
    request_id: str = Field(..., min_length=1)
    mode: KiwoomReadonlyFinalTransportMode = KiwoomReadonlyFinalTransportMode.DRY_RUN_PREVIEW_ONLY
    api_id: str = Field(..., min_length=1)
    domain: KiwoomReadonlyFinalDomain = KiwoomReadonlyFinalDomain.UNKNOWN_BLOCKED
    method: str = "POST"
    body_json: dict[str, object] = Field(default_factory=dict)
    continuation: KiwoomReadonlyFinalContinuation = Field(default_factory=KiwoomReadonlyFinalContinuation)
    opt_in: KiwoomReadonlyFinalOptIn = Field(default_factory=KiwoomReadonlyFinalOptIn)
    token_provider: KiwoomReadonlyFinalTokenProviderSpec = Field(default_factory=KiwoomReadonlyFinalTokenProviderSpec)
    capture_policy: KiwoomReadonlyFinalCapturePolicy = Field(default_factory=KiwoomReadonlyFinalCapturePolicy)
    provider_symbol: str | None = None
    canonical_instrument_key: str | None = None
    observed_at: datetime | None = None
    available_at: datetime | None = None
    validate_snapshot: bool = False
    mocked_response_payload: dict[str, object] | None = None
    operator_context: str = "user initiated kiwoom readonly final transport"

    @field_validator("request_id", "api_id", "method", "provider_symbol", "canonical_instrument_key", mode="before")
    @classmethod
    def normalize_upper_fields(cls, value, info):
        if value in (None, "") and info.field_name in {"provider_symbol", "canonical_instrument_key"}:
            return None
        return _upper_required(value, info.field_name)

    @field_validator("body_json", "mocked_response_payload", mode="before")
    @classmethod
    def normalize_dict_fields(cls, value, info):
        if value is None and info.field_name == "mocked_response_payload":
            return None
        return _normalize_dict(value, info.field_name)

    @field_validator("observed_at", "available_at", mode="before")
    @classmethod
    def normalize_datetimes(cls, value):
        return _aware(value)

    @field_validator("operator_context", mode="before")
    @classmethod
    def normalize_context(cls, value):
        return _string_required(value, "operator_context")

    @model_validator(mode="after")
    def validate_request(self):
        _validate_safety_flags(self, "final readonly transport request")
        if self.method != "POST":
            raise ValueError("only POST is supported")
        return self


class KiwoomReadonlyFinalRequestPreview(_BaseReport):
    report_id: str = Field(..., min_length=1)
    api_id: str = Field(..., min_length=1)
    domain: KiwoomReadonlyFinalDomain
    url: str = Field(..., min_length=1)
    method: str = Field(..., min_length=1)
    path: str = Field(..., min_length=1)
    headers: dict[str, object] = Field(default_factory=dict)
    body_json: dict[str, object] = Field(default_factory=dict)
    continuation: KiwoomReadonlyFinalContinuation

    @field_validator("report_id", "api_id", "method", "path", mode="before")
    @classmethod
    def normalize_upper_fields(cls, value, info):
        if info.field_name == "path":
            return _string_required(value, info.field_name)
        return _upper_required(value, info.field_name)

    @field_validator("url", mode="before")
    @classmethod
    def normalize_url(cls, value):
        return _string_required(value, "url")

    @field_validator("headers", "body_json", mode="before")
    @classmethod
    def normalize_dict_fields(cls, value, info):
        return _normalize_dict(value, info.field_name)

    @model_validator(mode="after")
    def validate_report(self):
        return _validate_safety_flags(self, "final request preview")


class KiwoomReadonlyFinalResponse(_BaseReport):
    response_id: str = Field(..., min_length=1)
    api_id: str = Field(..., min_length=1)
    domain: KiwoomReadonlyFinalDomain
    status_code: int = Field(default=200, ge=100, le=599)
    continuation: KiwoomReadonlyFinalContinuation = Field(default_factory=KiwoomReadonlyFinalContinuation)
    headers: dict[str, object] = Field(default_factory=dict)
    body_json: dict[str, object] = Field(default_factory=dict)

    @field_validator("response_id", "api_id", mode="before")
    @classmethod
    def normalize_upper_fields(cls, value, info):
        return _upper_required(value, info.field_name)

    @field_validator("headers", "body_json", mode="before")
    @classmethod
    def normalize_dict_fields(cls, value, info):
        return _normalize_dict(value, info.field_name)

    @model_validator(mode="after")
    def validate_report(self):
        return _validate_safety_flags(self, "final readonly response")


class KiwoomReadonlyFinalExecutionDecision(_BaseReport):
    report_id: str = Field(..., min_length=1)
    status: KiwoomReadonlyFinalStatus
    allowed: bool = False
    execute_transport: bool = False
    capture_allowed: bool = False
    reasons: list[str] = Field(default_factory=list)

    @field_validator("report_id", mode="before")
    @classmethod
    def normalize_id(cls, value):
        return _upper_required(value, "report_id")

    @field_validator("reasons", mode="before")
    @classmethod
    def normalize_reasons(cls, value):
        return _normalize_string_list(value, "reasons", upper=False)

    @model_validator(mode="after")
    def validate_report(self):
        return _validate_safety_flags(self, "final execution decision")


class KiwoomReadonlyFinalCapturedFile(StrictModel):
    file_path: str = Field(..., min_length=1)
    file_name: str = Field(..., min_length=1)
    file_size: int = Field(default=0, ge=0)
    source_ref: str = Field(..., min_length=1)

    @field_validator("file_path", mode="before")
    @classmethod
    def normalize_file_path(cls, value):
        return _validate_local_path(value, "file_path")

    @field_validator("file_name", "source_ref", mode="before")
    @classmethod
    def normalize_strings(cls, value, info):
        return _string_required(value, info.field_name)


class KiwoomReadonlyFinalCaptureRecord(_BaseReport):
    report_id: str = Field(..., min_length=1)
    status: KiwoomReadonlyFinalCaptureStatus
    provider: str = "KIWOOM_REST"
    api_id: str = Field(..., min_length=1)
    domain: KiwoomReadonlyFinalDomain
    provider_symbol: str | None = None
    canonical_instrument_key: str | None = None
    captured_at: datetime | None = None
    observed_at: datetime | None = None
    available_at: datetime | None = None
    response_status_code: int | None = Field(default=None, ge=100, le=599)
    return_code: int | None = None
    return_msg: str | None = None
    source_ref: str | None = None
    captured_files: list[KiwoomReadonlyFinalCapturedFile] = Field(default_factory=list)
    findings: list[str] = Field(default_factory=list)

    @field_validator("report_id", "api_id", mode="before")
    @classmethod
    def normalize_upper_fields(cls, value, info):
        return _upper_required(value, info.field_name)

    @field_validator("provider", "provider_symbol", "canonical_instrument_key", "return_msg", "source_ref", mode="before")
    @classmethod
    def normalize_optional_strings(cls, value, info):
        if value in (None, "") and info.field_name in {"provider_symbol", "canonical_instrument_key", "return_msg", "source_ref"}:
            return None
        if info.field_name == "provider":
            return _upper_required(value, info.field_name)
        return _string_required(value, info.field_name)

    @field_validator("captured_at", "observed_at", "available_at", mode="before")
    @classmethod
    def normalize_datetimes(cls, value):
        return _aware(value)

    @field_validator("findings", mode="before")
    @classmethod
    def normalize_findings(cls, value):
        return _normalize_string_list(value, "findings", upper=False)

    @model_validator(mode="after")
    def validate_report(self):
        return _validate_safety_flags(self, "final capture record")


class KiwoomReadonlyFinalCaptureIndex(_BaseReport):
    report_id: str = Field(..., min_length=1)
    capture_records: list[KiwoomReadonlyFinalCaptureRecord] = Field(default_factory=list)

    @field_validator("report_id", mode="before")
    @classmethod
    def normalize_id(cls, value):
        return _upper_required(value, "report_id")

    @model_validator(mode="after")
    def validate_report(self):
        return _validate_safety_flags(self, "final capture index")


class KiwoomReadonlyFinalSmokeRequest(_BaseReport):
    report_id: str = Field(..., min_length=1)
    request: KiwoomReadonlyFinalRequest

    @field_validator("report_id", mode="before")
    @classmethod
    def normalize_id(cls, value):
        return _upper_required(value, "report_id")

    @model_validator(mode="after")
    def validate_report(self):
        return _validate_safety_flags(self, "final smoke request")


class KiwoomReadonlyFinalParserRoutingResult(_BaseReport):
    report_id: str = Field(..., min_length=1)
    status: KiwoomReadonlyFinalStatus
    imported_file_path: str | None = None
    import_result: KiwoomManualResponseImportResult | None = None
    routing_report: KiwoomManualResponseRoutingReport | None = None
    canonical_output_report: KiwoomManualResponseCanonicalOutputReport | None = None
    safety_report: KiwoomManualResponseSafetyReport | None = None
    gap_report: KiwoomManualResponseGapReport | None = None

    @field_validator("report_id", mode="before")
    @classmethod
    def normalize_id(cls, value):
        return _upper_required(value, "report_id")

    @field_validator("imported_file_path", mode="before")
    @classmethod
    def normalize_imported_file_path(cls, value):
        if value in (None, ""):
            return None
        return _validate_local_path(value, "imported_file_path")

    @model_validator(mode="after")
    def validate_report(self):
        return _validate_safety_flags(self, "final parser routing result")


class KiwoomReadonlyFinalSnapshotValidationResult(_BaseReport):
    report_id: str = Field(..., min_length=1)
    status: KiwoomReadonlyFinalStatus
    snapshot_report: KiwoomReadonlyDomesticStockSnapshotReport | None = None
    composed: bool = False
    findings: list[str] = Field(default_factory=list)

    @field_validator("report_id", mode="before")
    @classmethod
    def normalize_id(cls, value):
        return _upper_required(value, "report_id")

    @field_validator("findings", mode="before")
    @classmethod
    def normalize_findings(cls, value):
        return _normalize_string_list(value, "findings", upper=False)

    @model_validator(mode="after")
    def validate_report(self):
        return _validate_safety_flags(self, "final snapshot validation result")


class KiwoomReadonlyFinalAllowlistReport(_BaseReport):
    report_id: str = Field(..., min_length=1)
    allowed_api_ids: list[str] = Field(default_factory=list)
    schema_gap_api_ids: list[str] = Field(default_factory=list)
    blocked_api_prefixes: list[str] = Field(default_factory=list)

    @field_validator("report_id", mode="before")
    @classmethod
    def normalize_id(cls, value):
        return _upper_required(value, "report_id")

    @field_validator("allowed_api_ids", "schema_gap_api_ids", "blocked_api_prefixes", mode="before")
    @classmethod
    def normalize_lists(cls, value, info):
        return _normalize_string_list(value, info.field_name)

    @model_validator(mode="after")
    def validate_report(self):
        return _validate_safety_flags(self, "final allowlist report")


class KiwoomReadonlyFinalTokenProviderReport(_BaseReport):
    report_id: str = Field(..., min_length=1)
    provider_kind: KiwoomReadonlyFinalTokenProviderKind
    enabled: bool = False
    env_var_name: str | None = None
    token_loaded: bool = False
    reference_label: str = "<REDACTED_TOKEN_REF>"
    findings: list[str] = Field(default_factory=list)

    @field_validator("report_id", "env_var_name", "reference_label", mode="before")
    @classmethod
    def normalize_strings(cls, value, info):
        if value in (None, "") and info.field_name == "env_var_name":
            return None
        if info.field_name == "env_var_name":
            return _upper_required(value, info.field_name)
        if info.field_name == "report_id":
            return _upper_required(value, info.field_name)
        return _string_required(value, info.field_name)

    @field_validator("findings", mode="before")
    @classmethod
    def normalize_findings(cls, value):
        return _normalize_string_list(value, "findings", upper=False)

    @model_validator(mode="after")
    def validate_report(self):
        return _validate_safety_flags(self, "final token provider report")


class KiwoomReadonlyFinalReadinessReport(_BaseReport):
    report_id: str = Field(..., min_length=1)
    status: KiwoomReadonlyFinalStatus
    mocked_mode_ready: bool = False
    manual_response_import_ready: bool = False
    parser_routing_ready: bool = False
    snapshot_validation_ready: bool = False
    real_readonly_single_call_path_defined: bool = False
    default_real_network_blocked: bool = True
    tests_use_real_network: bool = False
    account_order_apis_blocked: bool = True
    v8_complete: bool = False
    scope_notes: list[str] = Field(default_factory=list)

    @field_validator("report_id", mode="before")
    @classmethod
    def normalize_id(cls, value):
        return _upper_required(value, "report_id")

    @field_validator("scope_notes", mode="before")
    @classmethod
    def normalize_scope_notes(cls, value):
        return _normalize_string_list(value, "scope_notes", upper=False)

    @model_validator(mode="after")
    def validate_report(self):
        return _validate_safety_flags(self, "final readiness report")


class KiwoomReadonlyFinalSafetyReport(_BaseReport):
    safety_report_id: str = Field(..., min_length=1)
    blocked: bool = False
    findings: list[str] = Field(default_factory=list)

    @field_validator("safety_report_id", mode="before")
    @classmethod
    def normalize_id(cls, value):
        return _upper_required(value, "safety_report_id")

    @field_validator("findings", mode="before")
    @classmethod
    def normalize_findings(cls, value):
        return _normalize_string_list(value, "findings", upper=False)

    @model_validator(mode="after")
    def validate_report(self):
        return _validate_safety_flags(self, "final safety report")


class KiwoomReadonlyFinalGapEntry(StrictModel):
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


class KiwoomReadonlyFinalGapReport(_BaseReport):
    gap_report_id: str = Field(..., min_length=1)
    status: KiwoomReadonlyFinalStatus
    gap_entries: list[KiwoomReadonlyFinalGapEntry] = Field(default_factory=list)

    @field_validator("gap_report_id", mode="before")
    @classmethod
    def normalize_id(cls, value):
        return _upper_required(value, "gap_report_id")

    @model_validator(mode="after")
    def validate_report(self):
        return _validate_safety_flags(self, "final gap report")


class KiwoomReadonlyFinalAuditRecord(StrictModel):
    audit_record_id: str = Field(..., min_length=1)
    created_at: datetime
    source_path: str = Field(..., min_length=1)
    operator_context: str = Field(..., min_length=1)
    redaction_applied: bool = True
    contains_secret_material: bool = False
    contains_token_material: bool = False
    contains_account_material: bool = False
    findings: list[str] = Field(default_factory=list)

    @field_validator("audit_record_id", mode="before")
    @classmethod
    def normalize_id(cls, value):
        return _upper_required(value, "audit_record_id")

    @field_validator("created_at", mode="before")
    @classmethod
    def normalize_created_at(cls, value):
        parsed = _aware(value)
        if parsed is None:
            raise ValueError("created_at must not be null")
        return parsed

    @field_validator("source_path", mode="before")
    @classmethod
    def normalize_source_path(cls, value):
        return _validate_local_path(value, "source_path")

    @field_validator("operator_context", mode="before")
    @classmethod
    def normalize_context(cls, value):
        return _string_required(value, "operator_context")

    @field_validator("findings", mode="before")
    @classmethod
    def normalize_findings(cls, value):
        return _normalize_string_list(value, "findings", upper=False)


class KiwoomReadonlyFinalSmokeResult(_BaseReport):
    report_id: str = Field(..., min_length=1)
    status: KiwoomReadonlyFinalStatus
    executed: bool = False
    response: KiwoomReadonlyFinalResponse | None = None
    capture_record: KiwoomReadonlyFinalCaptureRecord | None = None
    parser_routing_result: KiwoomReadonlyFinalParserRoutingResult | None = None
    snapshot_validation_result: KiwoomReadonlyFinalSnapshotValidationResult | None = None

    @field_validator("report_id", mode="before")
    @classmethod
    def normalize_id(cls, value):
        return _upper_required(value, "report_id")

    @model_validator(mode="after")
    def validate_report(self):
        return _validate_safety_flags(self, "final smoke result")


class KiwoomReadonlyFinalSummaryReport(_BaseReport):
    report_id: str = Field(..., min_length=1)
    status: KiwoomReadonlyFinalStatus
    message: str = Field(..., min_length=1)

    @field_validator("report_id", mode="before")
    @classmethod
    def normalize_id(cls, value):
        return _upper_required(value, "report_id")

    @field_validator("message", mode="before")
    @classmethod
    def normalize_message(cls, value):
        return _string_required(value, "message")

    @model_validator(mode="after")
    def validate_report(self):
        return _validate_safety_flags(self, "final summary report")


class KiwoomReadonlyFinalResult(_BaseReport):
    adapter_result_id: str = Field(..., min_length=1)
    summary_report: KiwoomReadonlyFinalSummaryReport
    request_preview_report: KiwoomReadonlyFinalRequestPreview
    execution_decision_report: KiwoomReadonlyFinalExecutionDecision
    allowlist_report: KiwoomReadonlyFinalAllowlistReport
    token_provider_report: KiwoomReadonlyFinalTokenProviderReport
    response_report: KiwoomReadonlyFinalResponse | None = None
    smoke_result: KiwoomReadonlyFinalSmokeResult | None = None
    capture_report: KiwoomReadonlyFinalCaptureRecord | None = None
    capture_index_report: KiwoomReadonlyFinalCaptureIndex | None = None
    parser_routing_report: KiwoomReadonlyFinalParserRoutingResult | None = None
    snapshot_validation_report: KiwoomReadonlyFinalSnapshotValidationResult | None = None
    readiness_report: KiwoomReadonlyFinalReadinessReport
    safety_report: KiwoomReadonlyFinalSafetyReport
    gap_report: KiwoomReadonlyFinalGapReport
    audit_records: list[KiwoomReadonlyFinalAuditRecord] = Field(default_factory=list)

    @field_validator("adapter_result_id", mode="before")
    @classmethod
    def normalize_id(cls, value):
        return _upper_required(value, "adapter_result_id")

    @model_validator(mode="after")
    def validate_report(self):
        return _validate_safety_flags(self, "final readonly transport result")
