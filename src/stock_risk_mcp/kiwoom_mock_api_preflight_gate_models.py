from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from pydantic import Field, field_validator, model_validator

from stock_risk_mcp.kiwoom_mock_api_transport_draft_models import (
    KiwoomMockApiTransportDraftConfig,
)
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


def _validate_local_path(value: str, field_name: str) -> str:
    cleaned = _string_required(value, field_name)
    lowered = cleaned.lower()
    if "://" in lowered or lowered.startswith("//"):
        raise ValueError(f"{field_name} must be a local file path")
    if lowered.endswith(".parquet"):
        raise ValueError("parquet remains unsupported")
    return cleaned


def _validate_safety_flags(model, context: str):
    for flag_name in (
        "preflight_gate_only",
        "mock_only",
        "disabled_by_default",
        "explicit_opt_in_required",
        "local_file_only",
        "offline_only",
        "non_executable",
        "no_environment_read",
        "no_credential_file_read",
        "no_credentials_loaded",
        "no_token_loaded",
        "no_token_used",
        "no_token_refreshed",
        "no_authorization_header_generated",
        "no_http_client_created",
        "no_http_session_created",
        "no_transport_created",
        "no_api_call",
        "no_mockapi_call",
        "no_websocket_connection",
        "no_network_call",
        "no_account_read",
        "no_account_mutation",
        "no_real_order",
        "no_live_trading",
        "no_live_prod",
        "no_cloud_llm",
        "no_local_llm_runtime",
    ):
        if not getattr(model, flag_name):
            raise ValueError(f"{context} must remain {flag_name}")
    return model


class KiwoomMockApiPreflightRequestCategory(StrEnum):
    OAUTH = "OAUTH"
    QUOTE = "QUOTE"
    ACCOUNT = "ACCOUNT"
    ORDER = "ORDER"
    WEBSOCKET = "WEBSOCKET"
    UNKNOWN = "UNKNOWN"


class KiwoomMockApiExecutionReadiness(StrEnum):
    BLOCKED = "BLOCKED"
    DRAFT_READY = "DRAFT_READY"
    GAP = "GAP"
    REJECTED = "REJECTED"


class KiwoomMockApiPreflightGapCategory(StrEnum):
    PREFLIGHT_EXECUTION_NOT_IMPLEMENTED = "PREFLIGHT_EXECUTION_NOT_IMPLEMENTED"
    PREFLIGHT_HTTP_CLIENT_NOT_ALLOWED = "PREFLIGHT_HTTP_CLIENT_NOT_ALLOWED"
    PREFLIGHT_HTTP_SESSION_NOT_ALLOWED = "PREFLIGHT_HTTP_SESSION_NOT_ALLOWED"
    PREFLIGHT_TRANSPORT_NOT_ALLOWED = "PREFLIGHT_TRANSPORT_NOT_ALLOWED"
    PREFLIGHT_TOKEN_LOADING_NOT_ALLOWED = "PREFLIGHT_TOKEN_LOADING_NOT_ALLOWED"
    PREFLIGHT_TOKEN_USAGE_NOT_ALLOWED = "PREFLIGHT_TOKEN_USAGE_NOT_ALLOWED"
    PREFLIGHT_TOKEN_REFRESH_NOT_ALLOWED = "PREFLIGHT_TOKEN_REFRESH_NOT_ALLOWED"
    PREFLIGHT_AUTHORIZATION_HEADER_NOT_ALLOWED = "PREFLIGHT_AUTHORIZATION_HEADER_NOT_ALLOWED"
    PREFLIGHT_OAUTH_ENDPOINT_BLOCKED = "PREFLIGHT_OAUTH_ENDPOINT_BLOCKED"
    PREFLIGHT_ACCOUNT_ENDPOINT_BLOCKED = "PREFLIGHT_ACCOUNT_ENDPOINT_BLOCKED"
    PREFLIGHT_ORDER_ENDPOINT_BLOCKED = "PREFLIGHT_ORDER_ENDPOINT_BLOCKED"
    PREFLIGHT_WEBSOCKET_ENDPOINT_BLOCKED = "PREFLIGHT_WEBSOCKET_ENDPOINT_BLOCKED"
    PREFLIGHT_UNKNOWN_ENDPOINT_REJECTED = "PREFLIGHT_UNKNOWN_ENDPOINT_REJECTED"
    PREFLIGHT_PRODUCTION_DOMAIN_BLOCKED = "PREFLIGHT_PRODUCTION_DOMAIN_BLOCKED"
    PREFLIGHT_REMOTE_SOURCE_NOT_ALLOWED = "PREFLIGHT_REMOTE_SOURCE_NOT_ALLOWED"
    PREFLIGHT_PARQUET_NOT_ALLOWED = "PREFLIGHT_PARQUET_NOT_ALLOWED"


class _PreflightBase(StrictModel):
    preflight_gate_only: bool = True
    mock_only: bool = True
    disabled_by_default: bool = True
    explicit_opt_in_required: bool = True
    local_file_only: bool = True
    offline_only: bool = True
    non_executable: bool = True
    no_environment_read: bool = True
    no_credential_file_read: bool = True
    no_credentials_loaded: bool = True
    no_token_loaded: bool = True
    no_token_used: bool = True
    no_token_refreshed: bool = True
    no_authorization_header_generated: bool = True
    no_http_client_created: bool = True
    no_http_session_created: bool = True
    no_transport_created: bool = True
    no_api_call: bool = True
    no_mockapi_call: bool = True
    no_websocket_connection: bool = True
    no_network_call: bool = True
    no_account_read: bool = True
    no_account_mutation: bool = True
    no_real_order: bool = True
    no_live_trading: bool = True
    no_live_prod: bool = True
    no_cloud_llm: bool = True
    no_local_llm_runtime: bool = True


class KiwoomMockApiPreflightDependencyRef(_PreflightBase):
    ref_id: str = Field(..., min_length=1)
    ref_kind: str = Field(..., min_length=1)
    local_path: str = Field(..., min_length=1)

    @field_validator("ref_id", "ref_kind", mode="before")
    @classmethod
    def normalize_upper_fields(cls, value):
        return _upper_required(value, "ref")

    @field_validator("local_path", mode="before")
    @classmethod
    def validate_local_path(cls, value):
        return _validate_local_path(value, "local_path")

    @model_validator(mode="after")
    def validate_dependency_ref(self):
        return _validate_safety_flags(self, "dependency ref")


class KiwoomMockApiPreflightReadinessReport(_PreflightBase):
    readiness_report_id: str = Field(..., min_length=1)
    request_category: KiwoomMockApiPreflightRequestCategory
    readiness_decision: KiwoomMockApiExecutionReadiness
    rationale: str = Field(..., min_length=1)
    blocked_capabilities: list[str] = Field(default_factory=list)

    @field_validator("readiness_report_id", mode="before")
    @classmethod
    def normalize_id(cls, value):
        return _upper_required(value, "readiness_report_id")

    @field_validator("rationale", mode="before")
    @classmethod
    def normalize_rationale(cls, value):
        return _string_required(value, "rationale")

    @model_validator(mode="after")
    def validate_report(self):
        return _validate_safety_flags(self, "readiness report")


class KiwoomMockApiPreflightSafetyReport(_PreflightBase):
    safety_report_id: str = Field(..., min_length=1)
    blocked_capabilities: list[str] = Field(default_factory=list)
    findings: list[str] = Field(default_factory=list)

    @field_validator("safety_report_id", mode="before")
    @classmethod
    def normalize_id(cls, value):
        return _upper_required(value, "safety_report_id")

    @model_validator(mode="after")
    def validate_report(self):
        if not self.blocked_capabilities:
            raise ValueError("safety report must expose blocked capabilities")
        return _validate_safety_flags(self, "safety report")


class KiwoomMockApiPreflightGapReport(_PreflightBase):
    gap_report_id: str = Field(..., min_length=1)
    gap_status: str = Field(..., min_length=1)
    gap_categories: list[KiwoomMockApiPreflightGapCategory] = Field(default_factory=list)
    blocking_gap_count: int = Field(..., ge=0)
    report_only_gap_count: int = Field(..., ge=0)
    gaps: list[str] = Field(default_factory=list)

    @field_validator("gap_report_id", "gap_status", mode="before")
    @classmethod
    def normalize_upper(cls, value):
        return _upper_required(value, "gap")

    @model_validator(mode="after")
    def validate_report(self):
        if self.blocking_gap_count < len(self.gap_categories):
            raise ValueError("blocking_gap_count must cover gap categories")
        return _validate_safety_flags(self, "gap report")


class KiwoomMockApiPreflightAuditRecord(_PreflightBase):
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
    def validate_record(self):
        if not self.redaction_applied:
            raise ValueError("audit record must remain redacted")
        if self.contains_secret_material:
            raise ValueError("audit record must not contain secret material")
        return _validate_safety_flags(self, "audit record")


class KiwoomMockApiPreflightGateConfig(_PreflightBase):
    schema_version: str = Field(..., min_length=1)
    fixture_format: str = Field(..., min_length=1)
    config_id: str = Field(..., min_length=1)
    credential_boundary_ref: KiwoomMockApiPreflightDependencyRef
    oauth_draft_boundary_ref: KiwoomMockApiPreflightDependencyRef
    transport_draft_ref: KiwoomMockApiPreflightDependencyRef
    transport_draft_config: KiwoomMockApiTransportDraftConfig
    readiness_report: KiwoomMockApiPreflightReadinessReport | None = None
    safety_report: KiwoomMockApiPreflightSafetyReport | None = None
    gap_report: KiwoomMockApiPreflightGapReport | None = None
    audit_records: list[KiwoomMockApiPreflightAuditRecord] = Field(default_factory=list)

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
        if self.transport_draft_config.endpoint_evidence_ref.documented_mock_domain != "https://mockapi.kiwoom.com":
            raise ValueError("production domain execution is blocked")
        return _validate_safety_flags(self, "preflight gate config")
