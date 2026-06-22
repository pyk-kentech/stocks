from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from pydantic import Field, field_validator, model_validator

from stock_risk_mcp.models import StrictModel


def _aware(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("timestamp must include timezone")
    return value


def _upper_required(value, field_name: str) -> str:
    if value is None:
        raise ValueError(f"{field_name} must not be null")
    cleaned = str(value).strip().upper()
    if not cleaned:
        raise ValueError(f"{field_name} must not be blank")
    return cleaned


def _string_required(value, field_name: str) -> str:
    if value is None:
        raise ValueError(f"{field_name} must not be null")
    cleaned = str(value).strip()
    if not cleaned:
        raise ValueError(f"{field_name} must not be blank")
    return cleaned


def _validate_local_path(value: str, field_name: str) -> str:
    cleaned = _string_required(value, field_name)
    lowered = cleaned.lower()
    if "://" in lowered or lowered.startswith("//"):
        raise ValueError(f"{field_name} must be a local file path")
    if lowered.endswith(".parquet"):
        raise ValueError("parquet remains unsupported")
    return cleaned


def _validate_symbolic_ref(value, field_name: str) -> str:
    cleaned = _upper_required(value, field_name)
    if any(token in cleaned for token in ("BEARER", "TOKEN=", "SECRET=", "APPKEY=", "ACCOUNT", "AUTH")):
        raise ValueError(f"{field_name} must be symbolic and redacted")
    if not cleaned.endswith("_REF") and "_REF_" not in cleaned:
        raise ValueError(f"{field_name} must be a symbolic reference only")
    return cleaned


def _validate_safe_preview(value, field_name: str) -> str:
    cleaned = _string_required(value, field_name)
    upper = cleaned.upper()
    lowered = cleaned.lower()
    if cleaned.startswith("Bearer ") or "authorization:" in lowered:
        raise ValueError(f"{field_name} must not include authorization material")
    if upper.startswith("RAW_") or upper.startswith("RAW-"):
        raise ValueError(f"{field_name} must not include raw secret material")
    if "ACCESS_TOKEN" in upper or "REFRESH_TOKEN" in upper:
        raise ValueError(f"{field_name} must not include token values")
    if "ACCOUNT_NUMBER" in upper or "ACCT_NO" in upper:
        raise ValueError(f"{field_name} must not include account values")
    return cleaned


def _validate_safety_flags(model, context: str):
    for flag_name in (
        "kiwoom_mock_api_transport_draft_only",
        "mock_only",
        "transport_boundary_only",
        "request_envelope_only",
        "credential_ref_only",
        "token_ref_only",
        "disabled_by_default",
        "explicit_opt_in_required",
        "local_file_only",
        "offline_only",
        "non_executable",
        "no_environment_read",
        "no_credential_file_read",
        "no_credentials_loaded",
        "no_raw_secret_values",
        "no_authorization_header_generated",
        "no_token_loaded",
        "no_token_used",
        "no_token_refreshed",
        "no_http_client_created",
        "no_http_session_created",
        "no_api_call",
        "no_mockapi_call",
        "no_websocket_connection",
        "no_network_call",
        "no_real_order",
        "no_live_trading",
        "no_live_prod",
        "no_account_read",
        "no_account_mutation",
        "no_production_domain_execution",
        "no_cloud_llm",
        "no_local_llm_runtime",
    ):
        if not getattr(model, flag_name):
            raise ValueError(f"{context} must remain {flag_name}")
    return model


class KiwoomMockApiValueSource(StrEnum):
    LITERAL_SAFE = "LITERAL_SAFE"
    CREDENTIAL_REF_ONLY = "CREDENTIAL_REF_ONLY"
    TOKEN_REF_BLOCKED = "TOKEN_REF_BLOCKED"
    FUTURE_GENERATED_BLOCKED = "FUTURE_GENERATED_BLOCKED"


class KiwoomMockApiTransportGapCategory(StrEnum):
    KIWOOM_MOCK_API_TRANSPORT_DRAFT_GENERATED = "KIWOOM_MOCK_API_TRANSPORT_DRAFT_GENERATED"
    KIWOOM_MOCK_API_TRANSPORT_DRAFT_ONLY = "KIWOOM_MOCK_API_TRANSPORT_DRAFT_ONLY"
    KIWOOM_MOCK_API_TRANSPORT_LOCAL_ONLY = "KIWOOM_MOCK_API_TRANSPORT_LOCAL_ONLY"
    KIWOOM_MOCK_API_TRANSPORT_OFFLINE_ONLY = "KIWOOM_MOCK_API_TRANSPORT_OFFLINE_ONLY"
    KIWOOM_MOCK_API_MISSING_INPUT = "KIWOOM_MOCK_API_MISSING_INPUT"
    KIWOOM_MOCK_API_MISSING_ENDPOINT_EVIDENCE_REF = "KIWOOM_MOCK_API_MISSING_ENDPOINT_EVIDENCE_REF"
    KIWOOM_MOCK_API_MISSING_REQUEST_ENVELOPE_DRAFT = "KIWOOM_MOCK_API_MISSING_REQUEST_ENVELOPE_DRAFT"
    KIWOOM_MOCK_API_MISSING_TRANSPORT_POLICY = "KIWOOM_MOCK_API_MISSING_TRANSPORT_POLICY"
    KIWOOM_MOCK_API_MISSING_RETRY_TIMEOUT_POLICY = "KIWOOM_MOCK_API_MISSING_RETRY_TIMEOUT_POLICY"
    KIWOOM_MOCK_API_MISSING_ERROR_RESPONSE_DRAFT = "KIWOOM_MOCK_API_MISSING_ERROR_RESPONSE_DRAFT"
    KIWOOM_MOCK_API_MISSING_SAFETY_REPORT = "KIWOOM_MOCK_API_MISSING_SAFETY_REPORT"
    KIWOOM_MOCK_API_MISSING_GAP_REPORT = "KIWOOM_MOCK_API_MISSING_GAP_REPORT"
    KIWOOM_MOCK_API_TRANSPORT_MISSING_EXECUTABLE_TRANSPORT = (
        "KIWOOM_MOCK_API_TRANSPORT_MISSING_EXECUTABLE_TRANSPORT"
    )
    KIWOOM_MOCK_API_AUTHORIZATION_HEADER_GENERATION_NOT_ALLOWED = "KIWOOM_MOCK_API_AUTHORIZATION_HEADER_GENERATION_NOT_ALLOWED"
    KIWOOM_MOCK_API_TOKEN_LOAD_NOT_ALLOWED = "KIWOOM_MOCK_API_TOKEN_LOAD_NOT_ALLOWED"
    KIWOOM_MOCK_API_TOKEN_USE_NOT_ALLOWED = "KIWOOM_MOCK_API_TOKEN_USE_NOT_ALLOWED"
    KIWOOM_MOCK_API_HTTP_CLIENT_NOT_ALLOWED = "KIWOOM_MOCK_API_HTTP_CLIENT_NOT_ALLOWED"
    KIWOOM_MOCK_API_HTTP_SESSION_NOT_ALLOWED = "KIWOOM_MOCK_API_HTTP_SESSION_NOT_ALLOWED"
    KIWOOM_MOCK_API_API_CALL_NOT_ALLOWED = "KIWOOM_MOCK_API_API_CALL_NOT_ALLOWED"
    KIWOOM_MOCK_API_MOCKAPI_CALL_NOT_ALLOWED = "KIWOOM_MOCK_API_MOCKAPI_CALL_NOT_ALLOWED"
    KIWOOM_MOCK_API_WEBSOCKET_NOT_ALLOWED = "KIWOOM_MOCK_API_WEBSOCKET_NOT_ALLOWED"
    KIWOOM_MOCK_API_NETWORK_CALL_NOT_ALLOWED = "KIWOOM_MOCK_API_NETWORK_CALL_NOT_ALLOWED"
    KIWOOM_MOCK_API_PRODUCTION_DOMAIN_NOT_ALLOWED = "KIWOOM_MOCK_API_PRODUCTION_DOMAIN_NOT_ALLOWED"
    KIWOOM_MOCK_API_RAW_SECRET_NOT_ALLOWED = "KIWOOM_MOCK_API_RAW_SECRET_NOT_ALLOWED"
    KIWOOM_MOCK_API_RAW_TOKEN_NOT_ALLOWED = "KIWOOM_MOCK_API_RAW_TOKEN_NOT_ALLOWED"
    KIWOOM_MOCK_API_ACCOUNT_VALUE_NOT_ALLOWED = "KIWOOM_MOCK_API_ACCOUNT_VALUE_NOT_ALLOWED"
    KIWOOM_MOCK_API_AUTH_VALUE_NOT_ALLOWED = "KIWOOM_MOCK_API_AUTH_VALUE_NOT_ALLOWED"
    KIWOOM_MOCK_API_LIVE_PROD_NOT_ALLOWED = "KIWOOM_MOCK_API_LIVE_PROD_NOT_ALLOWED"
    KIWOOM_MOCK_API_CLOUD_LLM_NOT_ALLOWED = "KIWOOM_MOCK_API_CLOUD_LLM_NOT_ALLOWED"
    KIWOOM_MOCK_API_LOCAL_LLM_RUNTIME_NOT_ALLOWED = "KIWOOM_MOCK_API_LOCAL_LLM_RUNTIME_NOT_ALLOWED"
    KIWOOM_MOCK_API_PARQUET_NOT_ALLOWED = "KIWOOM_MOCK_API_PARQUET_NOT_ALLOWED"


class _TransportDraftBase(StrictModel):
    kiwoom_mock_api_transport_draft_only: bool = True
    mock_only: bool = True
    transport_boundary_only: bool = True
    request_envelope_only: bool = True
    credential_ref_only: bool = True
    token_ref_only: bool = True
    disabled_by_default: bool = True
    explicit_opt_in_required: bool = True
    local_file_only: bool = True
    offline_only: bool = True
    non_executable: bool = True
    no_environment_read: bool = True
    no_credential_file_read: bool = True
    no_credentials_loaded: bool = True
    no_raw_secret_values: bool = True
    no_authorization_header_generated: bool = True
    no_token_loaded: bool = True
    no_token_used: bool = True
    no_token_refreshed: bool = True
    no_http_client_created: bool = True
    no_http_session_created: bool = True
    no_api_call: bool = True
    no_mockapi_call: bool = True
    no_websocket_connection: bool = True
    no_network_call: bool = True
    no_real_order: bool = True
    no_live_trading: bool = True
    no_live_prod: bool = True
    no_account_read: bool = True
    no_account_mutation: bool = True
    no_production_domain_execution: bool = True
    no_cloud_llm: bool = True
    no_local_llm_runtime: bool = True


class KiwoomMockApiEndpointEvidenceRef(_TransportDraftBase):
    endpoint_ref_id: str = Field(..., min_length=1)
    source_evidence_document_id: str = Field(..., min_length=1)
    documented_api_id: str = Field(..., min_length=1)
    documented_category: str = Field(..., min_length=1)
    documented_method: str = Field(..., min_length=1)
    documented_path: str = Field(..., min_length=1)
    documented_mock_domain: str = Field(..., min_length=1)
    documented_production_domain: str = Field(..., min_length=1)
    documented_mock_support: bool = True
    documented_krx_only_note: str = Field(..., min_length=1)
    evidence_only: bool = True
    executable: bool = False
    production_domain_blocked: bool = True

    @field_validator("endpoint_ref_id", "source_evidence_document_id", "documented_api_id", mode="before")
    @classmethod
    def normalize_upper_ids(cls, value):
        return _upper_required(value, "reference")

    @field_validator("documented_category", "documented_krx_only_note", mode="before")
    @classmethod
    def normalize_text(cls, value):
        return _string_required(value, "text")

    @field_validator("documented_method", mode="before")
    @classmethod
    def validate_method(cls, value):
        cleaned = _upper_required(value, "documented_method")
        if cleaned != "POST":
            raise ValueError("HTTP method refs must remain documented-only POST metadata")
        return cleaned

    @field_validator("documented_path", mode="before")
    @classmethod
    def validate_path(cls, value):
        cleaned = _string_required(value, "documented_path")
        if not cleaned.startswith("/"):
            raise ValueError("documented_path must remain a documented relative path")
        return cleaned

    @field_validator("documented_mock_domain", mode="before")
    @classmethod
    def validate_mock_domain(cls, value):
        cleaned = _string_required(value, "documented_mock_domain")
        if cleaned != "https://mockapi.kiwoom.com":
            raise ValueError("production domain execution is blocked")
        return cleaned

    @field_validator("documented_production_domain", mode="before")
    @classmethod
    def validate_prod_domain(cls, value):
        cleaned = _string_required(value, "documented_production_domain")
        if cleaned != "https://api.kiwoom.com":
            raise ValueError("documented production domain must remain blocked evidence")
        return cleaned

    @model_validator(mode="after")
    def validate_endpoint(self):
        if not self.evidence_only or self.executable:
            raise ValueError("endpoint evidence refs must remain non-executable")
        if not self.documented_mock_support:
            raise ValueError("endpoint must remain mock-supported evidence only")
        if not self.production_domain_blocked:
            raise ValueError("production domain execution must remain blocked")
        return _validate_safety_flags(self, "endpoint evidence ref")


class KiwoomMockApiHeaderDraft(_TransportDraftBase):
    header_name: str = Field(..., min_length=1)
    required: bool = True
    value_source: KiwoomMockApiValueSource
    value_preview: str = Field(..., min_length=1)
    redaction_applied: bool = True

    @field_validator("header_name", mode="before")
    @classmethod
    def normalize_header_name(cls, value):
        return _string_required(value, "header_name").lower()

    @field_validator("value_preview", mode="before")
    @classmethod
    def normalize_preview(cls, value):
        return _validate_safe_preview(value, "value_preview")

    @model_validator(mode="after")
    def validate_header(self):
        allowed = {"content-type", "authorization"}
        if self.header_name not in allowed:
            raise ValueError("header_name must remain a documented draft header")
        if self.header_name == "authorization":
            if self.value_source != KiwoomMockApiValueSource.TOKEN_REF_BLOCKED:
                raise ValueError("authorization header draft must remain token-ref-only and blocked")
            if not self.redaction_applied:
                raise ValueError("authorization header draft must remain redacted")
            if self.value_preview != "TOKEN_REF_ONLY":
                raise ValueError("authorization header generation must remain impossible")
        return _validate_safety_flags(self, "header draft")


class KiwoomMockApiQueryParamDraft(_TransportDraftBase):
    param_name: str = Field(..., min_length=1)
    value_source: KiwoomMockApiValueSource
    value_preview: str = Field(..., min_length=1)
    redaction_applied: bool = False

    @field_validator("param_name", "value_preview", mode="before")
    @classmethod
    def normalize_text(cls, value, info):
        return _validate_safe_preview(value, info.field_name)

    @model_validator(mode="after")
    def validate_param(self):
        return _validate_safety_flags(self, "query param draft")


class KiwoomMockApiPathParamDraft(_TransportDraftBase):
    param_name: str = Field(..., min_length=1)
    value_source: KiwoomMockApiValueSource
    value_preview: str = Field(..., min_length=1)
    redaction_applied: bool = False

    @field_validator("param_name", "value_preview", mode="before")
    @classmethod
    def normalize_text(cls, value, info):
        return _validate_safe_preview(value, info.field_name)

    @model_validator(mode="after")
    def validate_param(self):
        return _validate_safety_flags(self, "path param draft")


class KiwoomMockApiBodyDraft(_TransportDraftBase):
    field_names: list[str] = Field(default_factory=list)
    field_value_sources: dict[str, KiwoomMockApiValueSource] = Field(default_factory=dict)
    field_value_previews: dict[str, str] = Field(default_factory=dict)
    redaction_applied: bool = True
    serializable_report_only: bool = True

    @field_validator("field_names", mode="before")
    @classmethod
    def validate_field_names(cls, value):
        if isinstance(value, (str, bytes)) or not isinstance(value, list) or not value:
            raise ValueError("field_names must be a non-empty list")
        normalized = [_string_required(item, "field_name") for item in value]
        allowed = {"appkey", "secretkey", "stk_cd"}
        if set(normalized) - allowed:
            raise ValueError("body draft field_names must remain documented-only")
        return normalized

    @field_validator("field_value_previews", mode="before")
    @classmethod
    def validate_previews(cls, value):
        if not isinstance(value, dict) or not value:
            raise ValueError("field_value_previews must not be empty")
        normalized: dict[str, str] = {}
        for key, raw in value.items():
            field_name = _string_required(key, "field_value_previews key")
            if field_name in {"appkey", "secretkey"}:
                normalized[field_name] = _validate_symbolic_ref(raw, field_name)
            else:
                normalized[field_name] = _validate_safe_preview(raw, field_name)
        return normalized

    @model_validator(mode="after")
    def validate_body(self):
        if not self.serializable_report_only:
            raise ValueError("body draft must remain serializable report-only")
        if not self.redaction_applied:
            raise ValueError("body draft must remain redacted")
        if set(self.field_names) != set(self.field_value_sources) or set(self.field_names) != set(
            self.field_value_previews
        ):
            raise ValueError("body draft fields, value sources, and previews must stay aligned")
        if self.field_value_sources.get("appkey") != KiwoomMockApiValueSource.CREDENTIAL_REF_ONLY:
            raise ValueError("appkey must remain credential-ref-only")
        if self.field_value_sources.get("secretkey") != KiwoomMockApiValueSource.CREDENTIAL_REF_ONLY:
            raise ValueError("secretkey must remain credential-ref-only")
        return _validate_safety_flags(self, "body draft")


class KiwoomMockApiRequestEnvelopeDraft(_TransportDraftBase):
    draft_id: str = Field(..., min_length=1)
    endpoint_ref_id: str = Field(..., min_length=1)
    documented_method: str = Field(..., min_length=1)
    mock_domain_reference: str = Field(..., min_length=1)
    request_path: str = Field(..., min_length=1)
    credential_ref_ids: list[str] = Field(default_factory=list)
    token_ref_id: str = Field(..., min_length=1)
    headers: list[KiwoomMockApiHeaderDraft] = Field(default_factory=list)
    query_params: list[KiwoomMockApiQueryParamDraft] = Field(default_factory=list)
    path_params: list[KiwoomMockApiPathParamDraft] = Field(default_factory=list)
    body_draft: KiwoomMockApiBodyDraft
    authorization_header_generation_available: bool = False
    http_client_available: bool = False
    http_session_available: bool = False
    network_execution_enabled: bool = False

    @field_validator("draft_id", "endpoint_ref_id", mode="before")
    @classmethod
    def normalize_upper_ids(cls, value):
        return _upper_required(value, "id")

    @field_validator("documented_method", mode="before")
    @classmethod
    def normalize_method(cls, value):
        cleaned = _upper_required(value, "documented_method")
        if cleaned != "POST":
            raise ValueError("HTTP method refs do not create executable requests")
        return cleaned

    @field_validator("mock_domain_reference", "token_ref_id", mode="before")
    @classmethod
    def normalize_symbolic_ref(cls, value):
        return _validate_symbolic_ref(value, "symbolic_ref")

    @field_validator("request_path", mode="before")
    @classmethod
    def normalize_path(cls, value):
        cleaned = _string_required(value, "request_path")
        if not cleaned.startswith("/"):
            raise ValueError("request_path must remain a documented relative path")
        return cleaned

    @field_validator("credential_ref_ids", mode="before")
    @classmethod
    def validate_credential_refs(cls, value):
        if isinstance(value, (str, bytes)) or not isinstance(value, list) or not value:
            raise ValueError("credential_ref_ids must be a non-empty list")
        return [_validate_symbolic_ref(item, "credential_ref_ids") for item in value]

    @model_validator(mode="after")
    def validate_request_envelope(self):
        if self.mock_domain_reference != "MOCK_DOMAIN_REF":
            raise ValueError("request envelope draft must remain mock-domain-only")
        if self.authorization_header_generation_available:
            raise ValueError("authorization header generation must be impossible")
        if self.http_client_available:
            raise ValueError("HTTP client creation is not allowed")
        if self.http_session_available:
            raise ValueError("HTTP session creation is not allowed")
        if self.network_execution_enabled:
            raise ValueError("network execution is not allowed")
        return _validate_safety_flags(self, "request envelope draft")


class KiwoomMockApiTransportPolicy(_TransportDraftBase):
    policy_id: str = Field(..., min_length=1)
    allowed_mock_rest_domain: str = Field(..., min_length=1)
    forbidden_production_rest_domain: str = Field(..., min_length=1)
    krx_only: bool = True

    @field_validator("policy_id", mode="before")
    @classmethod
    def normalize_id(cls, value):
        return _upper_required(value, "policy_id")

    @field_validator("allowed_mock_rest_domain", mode="before")
    @classmethod
    def validate_allowed_domain(cls, value):
        cleaned = _string_required(value, "allowed_mock_rest_domain")
        if cleaned != "https://mockapi.kiwoom.com":
            raise ValueError("only the documented mock REST domain is allowed")
        return cleaned

    @field_validator("forbidden_production_rest_domain", mode="before")
    @classmethod
    def validate_forbidden_domain(cls, value):
        cleaned = _string_required(value, "forbidden_production_rest_domain")
        if cleaned != "https://api.kiwoom.com":
            raise ValueError("production domain execution must remain blocked")
        return cleaned

    @model_validator(mode="after")
    def validate_policy(self):
        if not self.krx_only:
            raise ValueError("mock transport policy must remain KRX-only")
        return _validate_safety_flags(self, "transport policy")


class KiwoomMockApiRetryTimeoutPolicy(_TransportDraftBase):
    policy_id: str = Field(..., min_length=1)
    request_timeout_class: str = Field(..., min_length=1)
    retry_policy_class: str = Field(..., min_length=1)
    rate_limit_note_ref: str = Field(..., min_length=1)
    timeout_execution_enabled: bool = False
    retry_loop_enabled: bool = False
    sleep_backoff_enabled: bool = False

    @field_validator("policy_id", "rate_limit_note_ref", mode="before")
    @classmethod
    def normalize_upper_ids(cls, value):
        return _upper_required(value, "policy_ref")

    @field_validator("request_timeout_class", "retry_policy_class", mode="before")
    @classmethod
    def normalize_text(cls, value):
        return _upper_required(value, "policy_class")

    @model_validator(mode="after")
    def validate_policy(self):
        if self.timeout_execution_enabled or self.retry_loop_enabled or self.sleep_backoff_enabled:
            raise ValueError("retry/timeout policy must remain representation-only")
        return _validate_safety_flags(self, "retry timeout policy")


class KiwoomMockApiErrorResponseDraft(_TransportDraftBase):
    error_draft_id: str = Field(..., min_length=1)
    documented_error_fields: list[str] = Field(default_factory=list)
    captures_live_response: bool = False
    wraps_transport_exception: bool = False
    contains_credential_material: bool = False

    @field_validator("error_draft_id", mode="before")
    @classmethod
    def normalize_id(cls, value):
        return _upper_required(value, "error_draft_id")

    @field_validator("documented_error_fields", mode="before")
    @classmethod
    def validate_error_fields(cls, value):
        if isinstance(value, (str, bytes)) or not isinstance(value, list) or not value:
            raise ValueError("documented_error_fields must be a non-empty list")
        normalized = [_string_required(item, "documented_error_field") for item in value]
        if set(normalized) != {"return_code", "return_msg"}:
            raise ValueError("error response draft must remain documented-only")
        return normalized

    @model_validator(mode="after")
    def validate_error_draft(self):
        if self.captures_live_response:
            raise ValueError("error response draft must remain local only")
        if self.wraps_transport_exception:
            raise ValueError("transport exception wrapping is not allowed")
        if self.contains_credential_material:
            raise ValueError("error response draft must not contain credential material")
        return _validate_safety_flags(self, "error response draft")


class KiwoomMockApiTransportSafetyReport(_TransportDraftBase):
    safety_report_id: str = Field(..., min_length=1)
    blocked_capabilities: list[str] = Field(default_factory=list)
    findings: list[str] = Field(default_factory=list)

    @field_validator("safety_report_id", mode="before")
    @classmethod
    def normalize_id(cls, value):
        return _upper_required(value, "safety_report_id")

    @model_validator(mode="after")
    def validate_safety_report(self):
        required = {
            "AUTHORIZATION_HEADER_GENERATION_BLOCKED",
            "TOKEN_LOADING_BLOCKED",
            "HTTP_CLIENT_CREATION_BLOCKED",
            "HTTP_SESSION_CREATION_BLOCKED",
            "NETWORK_EXECUTION_BLOCKED",
            "PRODUCTION_DOMAIN_EXECUTION_BLOCKED",
        }
        if not required.issubset(set(self.blocked_capabilities)):
            raise ValueError("safety report must expose blocked transport capabilities")
        return _validate_safety_flags(self, "safety report")


class KiwoomMockApiTransportGapReport(_TransportDraftBase):
    gap_report_id: str = Field(..., min_length=1)
    gap_status: str = Field(..., min_length=1)
    gap_categories: list[KiwoomMockApiTransportGapCategory] = Field(default_factory=list)
    blocking_gap_count: int = Field(..., ge=0)
    report_only_gap_count: int = Field(..., ge=0)
    gaps: list[str] = Field(default_factory=list)

    @field_validator("gap_report_id", mode="before")
    @classmethod
    def normalize_id(cls, value):
        return _upper_required(value, "gap_report_id")

    @field_validator("gap_status", mode="before")
    @classmethod
    def normalize_status(cls, value):
        return _upper_required(value, "gap_status")

    @model_validator(mode="after")
    def validate_gap_report(self):
        if self.blocking_gap_count != len(self.gap_categories):
            raise ValueError("blocking_gap_count must match gap_categories length")
        return _validate_safety_flags(self, "gap report")


class KiwoomMockApiTransportAuditRecord(_TransportDraftBase):
    audit_record_id: str = Field(..., min_length=1)
    created_at: datetime
    source_path: str = Field(..., min_length=1)
    redaction_applied: bool = True
    contains_secret_material: bool = False
    evidence_refs: list[str] = Field(default_factory=list)

    @field_validator("audit_record_id", mode="before")
    @classmethod
    def normalize_id(cls, value):
        return _upper_required(value, "audit_record_id")

    @field_validator("created_at", mode="before")
    @classmethod
    def validate_timestamp(cls, value):
        return _aware(datetime.fromisoformat(value) if isinstance(value, str) else value)

    @field_validator("source_path", mode="before")
    @classmethod
    def validate_source_path(cls, value):
        return _validate_local_path(value, "source_path")

    @field_validator("evidence_refs", mode="before")
    @classmethod
    def normalize_evidence_refs(cls, value):
        if isinstance(value, (str, bytes)) or not isinstance(value, list) or not value:
            raise ValueError("evidence_refs must be a non-empty list")
        return [_upper_required(item, "evidence_ref") for item in value]

    @model_validator(mode="after")
    def validate_audit_record(self):
        if not self.redaction_applied:
            raise ValueError("audit record must remain redacted")
        if self.contains_secret_material:
            raise ValueError("audit record must not contain secret material")
        return _validate_safety_flags(self, "audit record")


class KiwoomMockApiTransportDraftConfig(_TransportDraftBase):
    schema_version: str = Field(..., min_length=1)
    fixture_format: str = Field(..., min_length=1)
    config_id: str = Field(..., min_length=1)
    endpoint_evidence_ref: KiwoomMockApiEndpointEvidenceRef
    request_envelope_draft: KiwoomMockApiRequestEnvelopeDraft
    transport_policy: KiwoomMockApiTransportPolicy
    retry_timeout_policy: KiwoomMockApiRetryTimeoutPolicy
    error_response_draft: KiwoomMockApiErrorResponseDraft
    safety_report: KiwoomMockApiTransportSafetyReport
    gap_report: KiwoomMockApiTransportGapReport
    audit_records: list[KiwoomMockApiTransportAuditRecord] = Field(default_factory=list)

    @field_validator("schema_version", mode="before")
    @classmethod
    def normalize_schema_version(cls, value):
        return _string_required(value, "schema_version")

    @field_validator("fixture_format", mode="before")
    @classmethod
    def normalize_fixture_format(cls, value):
        cleaned = _string_required(value, "fixture_format").lower()
        if cleaned != "json":
            raise ValueError("fixture_format must remain json")
        return cleaned

    @field_validator("config_id", mode="before")
    @classmethod
    def normalize_config_id(cls, value):
        return _upper_required(value, "config_id")

    @model_validator(mode="after")
    def validate_config(self):
        if not self.audit_records:
            raise ValueError("audit_records must not be empty")
        if self.request_envelope_draft.endpoint_ref_id != self.endpoint_evidence_ref.endpoint_ref_id:
            raise ValueError("request envelope draft must match endpoint evidence ref")
        if self.request_envelope_draft.request_path != self.endpoint_evidence_ref.documented_path:
            raise ValueError("request path must match documented endpoint path")
        if self.request_envelope_draft.documented_method != self.endpoint_evidence_ref.documented_method:
            raise ValueError("documented method must match endpoint evidence ref")
        return _validate_safety_flags(self, "transport draft config")
