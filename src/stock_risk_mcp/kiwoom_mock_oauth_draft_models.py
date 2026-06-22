from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from pydantic import Field, field_validator, model_validator

from stock_risk_mcp.kiwoom_mock_oauth_draft_guard import (
    validate_kiwoom_mock_oauth_draft_metadata_safety,
)
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
    if not cleaned.endswith("_REF"):
        raise ValueError(f"{field_name} must be a symbolic reference only")
    if any(bad in cleaned for bad in ("BEARER", "TOKEN=", "APPKEY-", "RAW-SECRET", "RAW_SECRET")):
        raise ValueError(f"{field_name} must be a symbolic reference only")
    return cleaned


def _validate_safety_flags(model, context: str):
    for flag_name in (
        "mock_only",
        "oauth_draft_only",
        "credential_boundary_only",
        "disabled_by_default",
        "explicit_opt_in_required",
        "non_executable",
        "local_file_only",
        "offline_only",
        "no_credentials_loaded",
        "no_env_read",
        "no_token_issued",
        "no_token_revoked",
        "no_api_call",
        "no_mockapi_call",
        "no_websocket_connection",
        "no_network_call",
        "no_real_order",
        "no_live_trading",
        "no_live_prod",
        "no_account_mutation",
        "no_production_domain_execution",
        "no_cloud_llm",
        "no_local_llm_runtime",
    ):
        if not getattr(model, flag_name):
            raise ValueError(f"{context} must remain {flag_name}")
    return model


class KiwoomMockOAuthPurpose(StrEnum):
    TOKEN_ISSUE = "TOKEN_ISSUE"
    TOKEN_REVOKE = "TOKEN_REVOKE"


class KiwoomMockOAuthGapCategory(StrEnum):
    KIWOOM_MOCK_OAUTH_DRAFT_GENERATED = "KIWOOM_MOCK_OAUTH_DRAFT_GENERATED"
    KIWOOM_MOCK_OAUTH_DRAFT_ONLY = "KIWOOM_MOCK_OAUTH_DRAFT_ONLY"
    KIWOOM_MOCK_OAUTH_LOCAL_ONLY = "KIWOOM_MOCK_OAUTH_LOCAL_ONLY"
    KIWOOM_MOCK_OAUTH_OFFLINE_ONLY = "KIWOOM_MOCK_OAUTH_OFFLINE_ONLY"
    KIWOOM_MOCK_OAUTH_MISSING_INPUT = "KIWOOM_MOCK_OAUTH_MISSING_INPUT"
    KIWOOM_MOCK_OAUTH_MISSING_ENDPOINT_REF = "KIWOOM_MOCK_OAUTH_MISSING_ENDPOINT_REF"
    KIWOOM_MOCK_OAUTH_MISSING_LIFECYCLE_POLICY = "KIWOOM_MOCK_OAUTH_MISSING_LIFECYCLE_POLICY"
    KIWOOM_MOCK_OAUTH_MISSING_SAFETY_REPORT = "KIWOOM_MOCK_OAUTH_MISSING_SAFETY_REPORT"
    KIWOOM_MOCK_OAUTH_MISSING_GAP_REPORT = "KIWOOM_MOCK_OAUTH_MISSING_GAP_REPORT"
    KIWOOM_MOCK_OAUTH_MISSING_EXECUTABLE_TRANSPORT = "KIWOOM_MOCK_OAUTH_MISSING_EXECUTABLE_TRANSPORT"
    KIWOOM_MOCK_OAUTH_EXECUTION_MODE_NOT_ALLOWED = "KIWOOM_MOCK_OAUTH_EXECUTION_MODE_NOT_ALLOWED"
    KIWOOM_MOCK_OAUTH_RAW_CREDENTIAL_DETECTED = "KIWOOM_MOCK_OAUTH_RAW_CREDENTIAL_DETECTED"
    KIWOOM_MOCK_OAUTH_TOKEN_VALUE_DETECTED = "KIWOOM_MOCK_OAUTH_TOKEN_VALUE_DETECTED"
    KIWOOM_MOCK_OAUTH_AUTH_HEADER_DETECTED = "KIWOOM_MOCK_OAUTH_AUTH_HEADER_DETECTED"
    KIWOOM_MOCK_OAUTH_ENV_VALUE_INGESTION_DETECTED = "KIWOOM_MOCK_OAUTH_ENV_VALUE_INGESTION_DETECTED"
    KIWOOM_MOCK_OAUTH_CREDENTIAL_FILE_REFERENCE_DETECTED = "KIWOOM_MOCK_OAUTH_CREDENTIAL_FILE_REFERENCE_DETECTED"
    KIWOOM_MOCK_OAUTH_PRODUCTION_DOMAIN_NOT_ALLOWED = "KIWOOM_MOCK_OAUTH_PRODUCTION_DOMAIN_NOT_ALLOWED"
    KIWOOM_MOCK_OAUTH_API_CALL_NOT_ALLOWED = "KIWOOM_MOCK_OAUTH_API_CALL_NOT_ALLOWED"
    KIWOOM_MOCK_OAUTH_MOCKAPI_CALL_NOT_ALLOWED = "KIWOOM_MOCK_OAUTH_MOCKAPI_CALL_NOT_ALLOWED"
    KIWOOM_MOCK_OAUTH_WEBSOCKET_NOT_ALLOWED = "KIWOOM_MOCK_OAUTH_WEBSOCKET_NOT_ALLOWED"
    KIWOOM_MOCK_OAUTH_NETWORK_CALL_NOT_ALLOWED = "KIWOOM_MOCK_OAUTH_NETWORK_CALL_NOT_ALLOWED"
    KIWOOM_MOCK_OAUTH_REAL_ORDER_NOT_ALLOWED = "KIWOOM_MOCK_OAUTH_REAL_ORDER_NOT_ALLOWED"
    KIWOOM_MOCK_OAUTH_LIVE_PROD_NOT_ALLOWED = "KIWOOM_MOCK_OAUTH_LIVE_PROD_NOT_ALLOWED"
    KIWOOM_MOCK_OAUTH_CLOUD_LLM_NOT_ALLOWED = "KIWOOM_MOCK_OAUTH_CLOUD_LLM_NOT_ALLOWED"
    KIWOOM_MOCK_OAUTH_LOCAL_LLM_RUNTIME_NOT_ALLOWED = "KIWOOM_MOCK_OAUTH_LOCAL_LLM_RUNTIME_NOT_ALLOWED"
    KIWOOM_MOCK_OAUTH_PARQUET_NOT_ALLOWED = "KIWOOM_MOCK_OAUTH_PARQUET_NOT_ALLOWED"


class _OAuthDraftBase(StrictModel):
    mock_only: bool = True
    oauth_draft_only: bool = True
    credential_boundary_only: bool = True
    disabled_by_default: bool = True
    explicit_opt_in_required: bool = True
    non_executable: bool = True
    local_file_only: bool = True
    offline_only: bool = True
    no_credentials_loaded: bool = True
    no_env_read: bool = True
    no_token_issued: bool = True
    no_token_revoked: bool = True
    no_api_call: bool = True
    no_mockapi_call: bool = True
    no_websocket_connection: bool = True
    no_network_call: bool = True
    no_real_order: bool = True
    no_live_trading: bool = True
    no_live_prod: bool = True
    no_account_mutation: bool = True
    no_production_domain_execution: bool = True
    no_cloud_llm: bool = True
    no_local_llm_runtime: bool = True


class KiwoomMockOAuthEndpointRef(_OAuthDraftBase):
    endpoint_ref_id: str = Field(..., min_length=1)
    documented_purpose: KiwoomMockOAuthPurpose
    method: str = Field(..., min_length=1)
    domain: str = Field(..., min_length=1)
    path: str = Field(..., min_length=1)
    evidence_only: bool = True
    executable: bool = False
    production_domain_blocked: bool = True
    krx_only: bool = True

    @field_validator("endpoint_ref_id", mode="before")
    @classmethod
    def normalize_endpoint_ref_id(cls, value):
        return _upper_required(value, "endpoint_ref_id")

    @field_validator("method", mode="before")
    @classmethod
    def normalize_method(cls, value):
        cleaned = _upper_required(value, "method")
        if cleaned != "POST":
            raise ValueError("only documented POST oauth endpoints are allowed")
        return cleaned

    @field_validator("domain", "path", mode="before")
    @classmethod
    def normalize_strings(cls, value, info):
        return _string_required(value, info.field_name)

    @model_validator(mode="after")
    def validate_endpoint(self):
        if not self.evidence_only or self.executable:
            raise ValueError("mock oauth endpoint refs must remain evidence-only and non-executable")
        if self.domain != "https://mockapi.kiwoom.com":
            raise ValueError("production domain execution is blocked")
        expected_path = "/oauth2/token" if self.documented_purpose == KiwoomMockOAuthPurpose.TOKEN_ISSUE else "/oauth2/revoke"
        if self.path != expected_path:
            raise ValueError("documented oauth endpoint path mismatch")
        if not self.production_domain_blocked:
            raise ValueError("production domain execution must remain blocked")
        if not self.krx_only:
            raise ValueError("mock oauth boundary must remain KRX-only")
        return _validate_safety_flags(self, "kiwoom mock oauth endpoint ref")


class KiwoomMockTokenRequestDraft(_OAuthDraftBase):
    draft_id: str = Field(..., min_length=1)
    endpoint_ref_id: str = Field(..., min_length=1)
    credential_ref_ids: list[str] = Field(default_factory=list)
    request_field_names: list[str] = Field(default_factory=list)
    response_field_names: list[str] = Field(default_factory=list)
    credential_ref_only: bool = True
    authorization_header_available: bool = False
    request_execution_enabled: bool = False

    @field_validator("draft_id", "endpoint_ref_id", mode="before")
    @classmethod
    def normalize_ids(cls, value, info):
        return _upper_required(value, info.field_name)

    @field_validator("credential_ref_ids", mode="before")
    @classmethod
    def validate_credential_refs(cls, value):
        if isinstance(value, (str, bytes)) or not isinstance(value, list) or not value:
            raise ValueError("credential_ref_ids must be a non-empty list")
        return [_validate_symbolic_ref(item, "credential_ref_ids") for item in value]

    @field_validator("request_field_names", mode="before")
    @classmethod
    def validate_request_fields(cls, value):
        if value != ["grant_type", "appkey", "secretkey"]:
            raise ValueError("token request draft must keep only documented request field names")
        return value

    @field_validator("response_field_names", mode="before")
    @classmethod
    def validate_response_fields(cls, value):
        if value != ["expires_dt", "token_type", "token"]:
            raise ValueError("token request draft must keep only documented response field names")
        return value

    @model_validator(mode="after")
    def validate_request_draft(self):
        if not self.credential_ref_only:
            raise ValueError("token request draft must remain credential-ref only")
        if self.authorization_header_available:
            raise ValueError("authorization header generation is not available")
        if self.request_execution_enabled:
            raise ValueError("oauth token request execution is not allowed")
        return _validate_safety_flags(self, "kiwoom mock token request draft")


class KiwoomMockTokenResponseDraft(_OAuthDraftBase):
    response_draft_id: str = Field(..., min_length=1)
    documented_response_field_names: list[str] = Field(default_factory=list)
    stores_real_token: bool = False
    token_storage_enabled: bool = False
    token_refresh_enabled: bool = False

    @field_validator("response_draft_id", mode="before")
    @classmethod
    def normalize_response_draft_id(cls, value):
        return _upper_required(value, "response_draft_id")

    @field_validator("documented_response_field_names", mode="before")
    @classmethod
    def validate_documented_response_fields(cls, value):
        if value != ["expires_dt", "token_type", "token"]:
            raise ValueError("token response draft must keep only documented response field names")
        return value

    @model_validator(mode="after")
    def validate_response_draft(self):
        if self.stores_real_token:
            raise ValueError("token response draft must not store real tokens")
        if self.token_storage_enabled:
            raise ValueError("token storage is not allowed")
        if self.token_refresh_enabled:
            raise ValueError("token refresh is not allowed")
        return _validate_safety_flags(self, "kiwoom mock token response draft")


class KiwoomMockTokenRevokeDraft(_OAuthDraftBase):
    draft_id: str = Field(..., min_length=1)
    endpoint_ref_id: str = Field(..., min_length=1)
    credential_ref_ids: list[str] = Field(default_factory=list)
    token_reference_label: str = Field(..., min_length=1)
    request_field_names: list[str] = Field(default_factory=list)
    credential_ref_only: bool = True
    request_execution_enabled: bool = False

    @field_validator("draft_id", "endpoint_ref_id", mode="before")
    @classmethod
    def normalize_ids(cls, value, info):
        return _upper_required(value, info.field_name)

    @field_validator("credential_ref_ids", mode="before")
    @classmethod
    def validate_revoke_credential_refs(cls, value):
        if isinstance(value, (str, bytes)) or not isinstance(value, list) or not value:
            raise ValueError("credential_ref_ids must be a non-empty list")
        return [_validate_symbolic_ref(item, "credential_ref_ids") for item in value]

    @field_validator("token_reference_label", mode="before")
    @classmethod
    def validate_token_reference_label(cls, value):
        cleaned = _upper_required(value, "token_reference_label")
        if "BEARER" in cleaned or "TOKEN=" in cleaned:
            raise ValueError("token_reference_label must stay symbolic and redacted")
        return cleaned

    @field_validator("request_field_names", mode="before")
    @classmethod
    def validate_revoke_request_fields(cls, value):
        if value != ["appkey", "secretkey", "token"]:
            raise ValueError("token revoke draft must keep only documented request field names")
        return value

    @model_validator(mode="after")
    def validate_revoke_draft(self):
        if not self.credential_ref_only:
            raise ValueError("token revoke draft must remain credential-ref only")
        if self.request_execution_enabled:
            raise ValueError("oauth token revoke execution is not allowed")
        return _validate_safety_flags(self, "kiwoom mock token revoke draft")


class KiwoomMockTokenLifecyclePolicy(_OAuthDraftBase):
    policy_id: str = Field(..., min_length=1)
    issue_execution_allowed: bool = False
    revoke_execution_allowed: bool = False
    refresh_execution_allowed: bool = False
    storage_execution_allowed: bool = False
    documented_lifetime_field_name: str = Field(..., min_length=1)
    token_value_retained: bool = False

    @field_validator("policy_id", mode="before")
    @classmethod
    def normalize_policy_id(cls, value):
        return _upper_required(value, "policy_id")

    @field_validator("documented_lifetime_field_name", mode="before")
    @classmethod
    def validate_lifetime_field_name(cls, value):
        cleaned = _string_required(value, "documented_lifetime_field_name")
        if cleaned != "expires_dt":
            raise ValueError("documented token lifetime field must remain expires_dt")
        return cleaned

    @model_validator(mode="after")
    def validate_lifecycle_policy(self):
        if self.issue_execution_allowed:
            raise ValueError("token issue execution is not allowed")
        if self.revoke_execution_allowed:
            raise ValueError("token revoke execution is not allowed")
        if self.refresh_execution_allowed:
            raise ValueError("token refresh is not allowed")
        if self.storage_execution_allowed:
            raise ValueError("token storage is not allowed")
        if self.token_value_retained:
            raise ValueError("token values must not be retained")
        return _validate_safety_flags(self, "kiwoom mock token lifecycle policy")


class KiwoomMockOAuthSafetyReport(_OAuthDraftBase):
    safety_report_id: str = Field(..., min_length=1)
    blocked_capabilities: list[str] = Field(default_factory=list)
    findings: list[str] = Field(default_factory=list)

    @field_validator("safety_report_id", mode="before")
    @classmethod
    def normalize_safety_report_id(cls, value):
        return _upper_required(value, "safety_report_id")

    @field_validator("blocked_capabilities", "findings", mode="before")
    @classmethod
    def validate_string_list(cls, value, info):
        if value is None:
            return []
        if isinstance(value, (str, bytes)) or not isinstance(value, list):
            raise ValueError(f"{info.field_name} must be a list")
        return [_string_required(item, info.field_name) for item in value]

    @model_validator(mode="after")
    def validate_safety_report(self):
        if not self.blocked_capabilities:
            raise ValueError("blocked_capabilities must not be empty")
        validate_kiwoom_mock_oauth_draft_metadata_safety({"findings": self.findings}, context="findings")
        return _validate_safety_flags(self, "kiwoom mock oauth safety report")


class KiwoomMockOAuthGapReport(_OAuthDraftBase):
    gap_report_id: str = Field(..., min_length=1)
    gap_status: str = Field(..., min_length=1)
    gap_categories: list[KiwoomMockOAuthGapCategory] = Field(default_factory=list)
    blocking_gap_count: int = Field(0, ge=0)
    report_only_gap_count: int = Field(0, ge=0)
    gaps: list[str] = Field(default_factory=list)

    @field_validator("gap_report_id", "gap_status", mode="before")
    @classmethod
    def normalize_gap_strings(cls, value, info):
        return _upper_required(value, info.field_name)

    @field_validator("gaps", mode="before")
    @classmethod
    def validate_gaps(cls, value):
        if value is None:
            return []
        if isinstance(value, (str, bytes)) or not isinstance(value, list):
            raise ValueError("gaps must be a list")
        return [_string_required(item, "gaps") for item in value]

    @model_validator(mode="after")
    def validate_gap_report(self):
        if self.gap_status == "NO_GAPS" and self.gap_categories:
            raise ValueError("NO_GAPS report must not include gap categories")
        return _validate_safety_flags(self, "kiwoom mock oauth gap report")


class KiwoomMockOAuthAuditRecord(_OAuthDraftBase):
    audit_record_id: str = Field(..., min_length=1)
    created_at: datetime
    source_path: str = Field(..., min_length=1)
    redaction_applied: bool = True
    contains_secret_material: bool = False
    evidence_refs: list[str] = Field(default_factory=list)

    @field_validator("audit_record_id", mode="before")
    @classmethod
    def normalize_audit_record_id(cls, value):
        return _upper_required(value, "audit_record_id")

    @field_validator("created_at")
    @classmethod
    def validate_created_at(cls, value):
        return _aware(value)

    @field_validator("source_path", mode="before")
    @classmethod
    def validate_source_path(cls, value):
        return _validate_local_path(value, "source_path")

    @field_validator("evidence_refs", mode="before")
    @classmethod
    def validate_evidence_refs(cls, value):
        if value is None:
            return []
        if isinstance(value, (str, bytes)) or not isinstance(value, list):
            raise ValueError("evidence_refs must be a list")
        return [_upper_required(item, "evidence_refs") for item in value]

    @model_validator(mode="after")
    def validate_audit_record(self):
        if not self.redaction_applied:
            raise ValueError("audit records must remain redacted")
        if self.contains_secret_material:
            raise ValueError("audit records must not contain secret material")
        return _validate_safety_flags(self, "kiwoom mock oauth audit record")


class KiwoomMockOAuthDraftConfig(_OAuthDraftBase):
    schema_version: str = Field(..., min_length=1)
    fixture_format: str = Field(default="json", min_length=1)
    config_id: str = Field(..., min_length=1)
    endpoint_refs: list[KiwoomMockOAuthEndpointRef] = Field(default_factory=list)
    token_request_draft: KiwoomMockTokenRequestDraft
    token_response_draft: KiwoomMockTokenResponseDraft
    token_revoke_draft: KiwoomMockTokenRevokeDraft
    token_lifecycle_policy: KiwoomMockTokenLifecyclePolicy
    safety_report: KiwoomMockOAuthSafetyReport
    gap_report: KiwoomMockOAuthGapReport
    audit_records: list[KiwoomMockOAuthAuditRecord] = Field(default_factory=list)

    @field_validator("schema_version", "config_id", mode="before")
    @classmethod
    def normalize_top_strings(cls, value, info):
        return _upper_required(value, info.field_name)

    @field_validator("fixture_format", mode="before")
    @classmethod
    def validate_fixture_format(cls, value):
        cleaned = _string_required(value, "fixture_format").lower()
        if cleaned == "parquet":
            raise ValueError("parquet remains unsupported")
        if cleaned != "json":
            raise ValueError("kiwoom mock oauth draft fixture must remain json")
        return cleaned

    @model_validator(mode="after")
    def validate_config(self):
        if len(self.endpoint_refs) < 2:
            raise ValueError("endpoint_refs must include token issue and token revoke evidence refs")
        endpoint_ids = {item.endpoint_ref_id for item in self.endpoint_refs}
        if self.token_request_draft.endpoint_ref_id not in endpoint_ids:
            raise ValueError("token_request_draft endpoint_ref_id must reference a known endpoint")
        if self.token_revoke_draft.endpoint_ref_id not in endpoint_ids:
            raise ValueError("token_revoke_draft endpoint_ref_id must reference a known endpoint")
        return _validate_safety_flags(self, "kiwoom mock oauth draft config")
