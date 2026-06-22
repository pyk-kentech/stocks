from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from pydantic import Field, field_validator, model_validator

from stock_risk_mcp.kiwoom_mock_credential_boundary_guard import (
    validate_kiwoom_mock_credential_boundary_metadata_safety,
)
from stock_risk_mcp.models import StrictModel


_ALLOWED_ENV_NAMES = {
    "KIWOOM_MOCK_ONLY",
    "KIWOOM_MOCK_DRY_RUN",
    "KIWOOM_MOCK_EXPLICIT_OPT_IN",
    "KIWOOM_MOCK_APP_KEY_REF",
    "KIWOOM_MOCK_SECRET_KEY_REF",
    "KIWOOM_MOCK_ACCOUNT_REF",
}


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


def _validate_env_name(value, field_name: str) -> str:
    cleaned = _upper_required(value, field_name)
    if cleaned not in _ALLOWED_ENV_NAMES:
        raise ValueError(f"{field_name} must be one of the approved KIWOOM_MOCK_* environment names")
    return cleaned


def _validate_safety_flags(model, context: str):
    for flag_name in (
        "mock_only",
        "credential_boundary_only",
        "disabled_by_default",
        "explicit_opt_in_required",
        "local_file_only",
        "offline_only",
        "non_executable",
        "no_credentials_loaded",
        "no_environment_read",
        "no_credential_file_read",
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


class KiwoomMockExecutionMode(StrEnum):
    KIWOOM_MOCK_DISABLED = "KIWOOM_MOCK_DISABLED"
    KIWOOM_MOCK_DRY_RUN = "KIWOOM_MOCK_DRY_RUN"
    KIWOOM_MOCK_OPT_IN_EXECUTION_FUTURE = "KIWOOM_MOCK_OPT_IN_EXECUTION_FUTURE"


class KiwoomMockCredentialSourceType(StrEnum):
    ENVIRONMENT_REFERENCE = "ENVIRONMENT_REFERENCE"
    LOCAL_SECRET_STORE_REFERENCE = "LOCAL_SECRET_STORE_REFERENCE"
    MANUAL_OPERATOR_REFERENCE = "MANUAL_OPERATOR_REFERENCE"
    DISABLED = "DISABLED"


class KiwoomMockCredentialGapCategory(StrEnum):
    KIWOOM_CREDENTIAL_BOUNDARY_GENERATED = "KIWOOM_CREDENTIAL_BOUNDARY_GENERATED"
    KIWOOM_CREDENTIAL_BOUNDARY_ONLY = "KIWOOM_CREDENTIAL_BOUNDARY_ONLY"
    KIWOOM_CREDENTIAL_LOCAL_ONLY = "KIWOOM_CREDENTIAL_LOCAL_ONLY"
    KIWOOM_CREDENTIAL_OFFLINE_ONLY = "KIWOOM_CREDENTIAL_OFFLINE_ONLY"
    KIWOOM_CREDENTIAL_DISABLED_BY_DEFAULT = "KIWOOM_CREDENTIAL_DISABLED_BY_DEFAULT"
    KIWOOM_CREDENTIAL_EXPLICIT_OPT_IN_REQUIRED = "KIWOOM_CREDENTIAL_EXPLICIT_OPT_IN_REQUIRED"
    KIWOOM_CREDENTIAL_MISSING_INPUT = "KIWOOM_CREDENTIAL_MISSING_INPUT"
    KIWOOM_CREDENTIAL_MISSING_ENVIRONMENT = "KIWOOM_CREDENTIAL_MISSING_ENVIRONMENT"
    KIWOOM_CREDENTIAL_MISSING_DOMAIN_POLICY = "KIWOOM_CREDENTIAL_MISSING_DOMAIN_POLICY"
    KIWOOM_CREDENTIAL_MISSING_OPT_IN_GATE = "KIWOOM_CREDENTIAL_MISSING_OPT_IN_GATE"
    KIWOOM_CREDENTIAL_MOCK_DOMAIN_REQUIRED = "KIWOOM_CREDENTIAL_MOCK_DOMAIN_REQUIRED"
    KIWOOM_CREDENTIAL_PRODUCTION_DOMAIN_NOT_ALLOWED = "KIWOOM_CREDENTIAL_PRODUCTION_DOMAIN_NOT_ALLOWED"
    KIWOOM_CREDENTIAL_LIVE_PROD_NOT_ALLOWED = "KIWOOM_CREDENTIAL_LIVE_PROD_NOT_ALLOWED"
    KIWOOM_CREDENTIAL_CREDENTIAL_LOADING_NOT_ALLOWED = "KIWOOM_CREDENTIAL_CREDENTIAL_LOADING_NOT_ALLOWED"
    KIWOOM_CREDENTIAL_ENVIRONMENT_READ_NOT_ALLOWED = "KIWOOM_CREDENTIAL_ENVIRONMENT_READ_NOT_ALLOWED"
    KIWOOM_CREDENTIAL_CREDENTIAL_FILE_READ_NOT_ALLOWED = "KIWOOM_CREDENTIAL_CREDENTIAL_FILE_READ_NOT_ALLOWED"
    KIWOOM_CREDENTIAL_TOKEN_ISSUE_NOT_ALLOWED = "KIWOOM_CREDENTIAL_TOKEN_ISSUE_NOT_ALLOWED"
    KIWOOM_CREDENTIAL_TOKEN_REVOKE_NOT_ALLOWED = "KIWOOM_CREDENTIAL_TOKEN_REVOKE_NOT_ALLOWED"
    KIWOOM_CREDENTIAL_API_CALL_NOT_ALLOWED = "KIWOOM_CREDENTIAL_API_CALL_NOT_ALLOWED"
    KIWOOM_CREDENTIAL_MOCKAPI_CALL_NOT_ALLOWED = "KIWOOM_CREDENTIAL_MOCKAPI_CALL_NOT_ALLOWED"
    KIWOOM_CREDENTIAL_WEBSOCKET_NOT_ALLOWED = "KIWOOM_CREDENTIAL_WEBSOCKET_NOT_ALLOWED"
    KIWOOM_CREDENTIAL_NETWORK_CALL_NOT_ALLOWED = "KIWOOM_CREDENTIAL_NETWORK_CALL_NOT_ALLOWED"
    KIWOOM_CREDENTIAL_REAL_ORDER_NOT_ALLOWED = "KIWOOM_CREDENTIAL_REAL_ORDER_NOT_ALLOWED"
    KIWOOM_CREDENTIAL_LIVE_TRADING_NOT_ALLOWED = "KIWOOM_CREDENTIAL_LIVE_TRADING_NOT_ALLOWED"
    KIWOOM_CREDENTIAL_ACCOUNT_MUTATION_NOT_ALLOWED = "KIWOOM_CREDENTIAL_ACCOUNT_MUTATION_NOT_ALLOWED"
    KIWOOM_CREDENTIAL_SECRET_VALUE_NOT_ALLOWED = "KIWOOM_CREDENTIAL_SECRET_VALUE_NOT_ALLOWED"
    KIWOOM_CREDENTIAL_UNREDACTED_SECRET_NOT_ALLOWED = "KIWOOM_CREDENTIAL_UNREDACTED_SECRET_NOT_ALLOWED"
    KIWOOM_CREDENTIAL_CLOUD_LLM_NOT_ALLOWED = "KIWOOM_CREDENTIAL_CLOUD_LLM_NOT_ALLOWED"
    KIWOOM_CREDENTIAL_LOCAL_LLM_RUNTIME_NOT_ALLOWED = "KIWOOM_CREDENTIAL_LOCAL_LLM_RUNTIME_NOT_ALLOWED"
    KIWOOM_CREDENTIAL_PARQUET_NOT_ALLOWED = "KIWOOM_CREDENTIAL_PARQUET_NOT_ALLOWED"


class _CredentialBoundaryBase(StrictModel):
    mock_only: bool = True
    credential_boundary_only: bool = True
    disabled_by_default: bool = True
    explicit_opt_in_required: bool = True
    local_file_only: bool = True
    offline_only: bool = True
    non_executable: bool = True
    no_credentials_loaded: bool = True
    no_environment_read: bool = True
    no_credential_file_read: bool = True
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


class KiwoomMockEnvironment(_CredentialBoundaryBase):
    environment_id: str = Field(..., min_length=1)
    mock_only_env_name: str = Field(..., min_length=1)
    dry_run_env_name: str = Field(..., min_length=1)
    explicit_opt_in_env_name: str = Field(..., min_length=1)
    app_key_ref_env_name: str = Field(..., min_length=1)
    secret_key_ref_env_name: str = Field(..., min_length=1)
    account_ref_env_name: str = Field(..., min_length=1)
    reads_environment: bool = False

    @field_validator("environment_id", mode="before")
    @classmethod
    def normalize_environment_id(cls, value):
        return _upper_required(value, "environment_id")

    @field_validator(
        "mock_only_env_name",
        "dry_run_env_name",
        "explicit_opt_in_env_name",
        "app_key_ref_env_name",
        "secret_key_ref_env_name",
        "account_ref_env_name",
        mode="before",
    )
    @classmethod
    def validate_env_names(cls, value, info):
        return _validate_env_name(value, info.field_name)

    @model_validator(mode="after")
    def validate_environment(self):
        if self.reads_environment:
            raise ValueError("environment read is not allowed")
        if len(
            {
                self.mock_only_env_name,
                self.dry_run_env_name,
                self.explicit_opt_in_env_name,
                self.app_key_ref_env_name,
                self.secret_key_ref_env_name,
                self.account_ref_env_name,
            }
        ) != 6:
            raise ValueError("environment policy names must be distinct")
        return _validate_safety_flags(self, "kiwoom mock environment")


class KiwoomMockCredentialRef(_CredentialBoundaryBase):
    credential_ref_id: str = Field(..., min_length=1)
    source_type: KiwoomMockCredentialSourceType
    source_label: str = Field(..., min_length=1)
    reference_name: str = Field(..., min_length=1)
    loaded: bool = False
    secret_material_present: bool = False
    reads_credential_file: bool = False

    @field_validator("credential_ref_id", mode="before")
    @classmethod
    def normalize_credential_ref_id(cls, value):
        return _upper_required(value, "credential_ref_id")

    @field_validator("source_label", mode="before")
    @classmethod
    def normalize_source_label(cls, value):
        return _string_required(value, "source_label")

    @field_validator("reference_name", mode="before")
    @classmethod
    def validate_reference_name(cls, value):
        cleaned = _validate_env_name(value, "reference_name")
        return cleaned

    @model_validator(mode="after")
    def validate_credential_ref(self):
        if self.loaded:
            raise ValueError("credential loading is not allowed")
        if self.secret_material_present:
            raise ValueError("secret value is not allowed")
        if self.reads_credential_file:
            raise ValueError("credential file read is not allowed")
        return _validate_safety_flags(self, "kiwoom mock credential ref")


class KiwoomMockTokenBoundary(_CredentialBoundaryBase):
    token_boundary_id: str = Field(..., min_length=1)
    documented_issue_endpoint_path: str = Field(..., min_length=1)
    documented_revoke_endpoint_path: str = Field(..., min_length=1)
    issue_allowed_now: bool = False
    revoke_allowed_now: bool = False
    execution_mode_requirement: KiwoomMockExecutionMode = KiwoomMockExecutionMode.KIWOOM_MOCK_OPT_IN_EXECUTION_FUTURE
    token_issue_attempted: bool = False
    token_revoke_attempted: bool = False

    @field_validator("token_boundary_id", mode="before")
    @classmethod
    def normalize_token_boundary_id(cls, value):
        return _upper_required(value, "token_boundary_id")

    @field_validator("documented_issue_endpoint_path", "documented_revoke_endpoint_path", mode="before")
    @classmethod
    def normalize_endpoint_paths(cls, value, info):
        return _string_required(value, info.field_name)

    @model_validator(mode="after")
    def validate_token_boundary(self):
        if self.issue_allowed_now or self.token_issue_attempted:
            raise ValueError("token issue is not allowed")
        if self.revoke_allowed_now or self.token_revoke_attempted:
            raise ValueError("token revoke is not allowed")
        return _validate_safety_flags(self, "kiwoom mock token boundary")


class KiwoomMockDomainPolicy(_CredentialBoundaryBase):
    domain_policy_id: str = Field(..., min_length=1)
    allowed_mock_rest_domain: str = Field(..., min_length=1)
    forbidden_production_rest_domain: str = Field(..., min_length=1)
    allowed_mock_websocket_domain: str = Field(..., min_length=1)
    forbidden_production_websocket_domain: str = Field(..., min_length=1)
    krx_only: bool = True
    production_domain_execution_allowed: bool = False

    @field_validator("domain_policy_id", mode="before")
    @classmethod
    def normalize_domain_policy_id(cls, value):
        return _upper_required(value, "domain_policy_id")

    @field_validator(
        "allowed_mock_rest_domain",
        "forbidden_production_rest_domain",
        "allowed_mock_websocket_domain",
        "forbidden_production_websocket_domain",
        mode="before",
    )
    @classmethod
    def normalize_domain_values(cls, value, info):
        return _string_required(value, info.field_name)

    @model_validator(mode="after")
    def validate_domain_policy(self):
        if self.allowed_mock_rest_domain != "https://mockapi.kiwoom.com":
            raise ValueError("mock domain is required")
        if self.forbidden_production_rest_domain != "https://api.kiwoom.com":
            raise ValueError("production domain must remain blocked")
        if self.allowed_mock_websocket_domain != "wss://mockapi.kiwoom.com:10000":
            raise ValueError("mock websocket domain metadata must remain documented only")
        if self.forbidden_production_websocket_domain != "wss://api.kiwoom.com:10000":
            raise ValueError("production websocket domain must remain blocked")
        if not self.krx_only:
            raise ValueError("kiwoom mock domain policy must remain KRX only")
        if self.production_domain_execution_allowed:
            raise ValueError("production domain execution is not allowed")
        return _validate_safety_flags(self, "kiwoom mock domain policy")


class KiwoomMockOptInGate(_CredentialBoundaryBase):
    opt_in_gate_id: str = Field(..., min_length=1)
    gate_state: str = Field(default="BLOCKED_DEFAULT", min_length=1)
    explicit_opt_in_present: bool = False
    mock_execution_allowed_now: bool = False
    dry_run_only: bool = True

    @field_validator("opt_in_gate_id", "gate_state", mode="before")
    @classmethod
    def normalize_gate_strings(cls, value, info):
        return _upper_required(value, info.field_name)

    @model_validator(mode="after")
    def validate_opt_in_gate(self):
        if self.gate_state != "BLOCKED_DEFAULT":
            raise ValueError("explicit opt-in gate must remain blocked by default")
        if self.explicit_opt_in_present:
            raise ValueError("explicit opt-in remains future-only in v6.4")
        if self.mock_execution_allowed_now:
            raise ValueError("mock execution must remain disabled")
        if not self.dry_run_only:
            raise ValueError("only dry-run posture is allowed")
        return _validate_safety_flags(self, "kiwoom mock opt-in gate")


class KiwoomMockCredentialSafetyReport(_CredentialBoundaryBase):
    safety_report_id: str = Field(..., min_length=1)
    blocked: bool = False
    findings: list[str] = Field(default_factory=list)

    @field_validator("safety_report_id", mode="before")
    @classmethod
    def normalize_safety_report_id(cls, value):
        return _upper_required(value, "safety_report_id")

    @field_validator("findings", mode="before")
    @classmethod
    def validate_findings(cls, value):
        if value is None:
            return []
        if isinstance(value, (str, bytes)) or not isinstance(value, list):
            raise ValueError("findings must be a list")
        return [_string_required(item, "findings") for item in value]

    @model_validator(mode="after")
    def validate_safety_report(self):
        validate_kiwoom_mock_credential_boundary_metadata_safety({"findings": self.findings}, context="findings")
        return _validate_safety_flags(self, "kiwoom mock credential safety report")


class KiwoomMockCredentialGapReport(_CredentialBoundaryBase):
    gap_report_id: str = Field(..., min_length=1)
    gap_status: str = Field(..., min_length=1)
    gap_categories: list[KiwoomMockCredentialGapCategory] = Field(default_factory=list)
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
            raise ValueError("NO_GAPS report must not list gap categories")
        return _validate_safety_flags(self, "kiwoom mock credential gap report")


class KiwoomMockCredentialAuditRecord(_CredentialBoundaryBase):
    audit_record_id: str = Field(..., min_length=1)
    created_at: datetime
    source_path: str = Field(..., min_length=1)
    source_manifest_ids: list[str] = Field(default_factory=list)

    @field_validator("audit_record_id", mode="before")
    @classmethod
    def normalize_audit_record_id(cls, value):
        return _upper_required(value, "audit_record_id")

    @field_validator("created_at")
    @classmethod
    def validate_timestamp(cls, value):
        return _aware(value)

    @field_validator("source_path", mode="before")
    @classmethod
    def validate_source_path(cls, value):
        return _validate_local_path(value, "source_path")

    @field_validator("source_manifest_ids", mode="before")
    @classmethod
    def validate_manifest_ids(cls, value):
        if value is None:
            return []
        if isinstance(value, (str, bytes)) or not isinstance(value, list):
            raise ValueError("source_manifest_ids must be a list")
        return [_upper_required(item, "source_manifest_ids") for item in value]

    @model_validator(mode="after")
    def validate_audit_record(self):
        return _validate_safety_flags(self, "kiwoom mock credential audit record")


class KiwoomMockCredentialBoundaryConfig(_CredentialBoundaryBase):
    schema_version: str = Field(..., min_length=1)
    fixture_format: str = Field(default="json", min_length=1)
    config_id: str = Field(..., min_length=1)
    environment: KiwoomMockEnvironment
    credential_refs: list[KiwoomMockCredentialRef] = Field(default_factory=list)
    token_boundary: KiwoomMockTokenBoundary
    domain_policy: KiwoomMockDomainPolicy
    opt_in_gate: KiwoomMockOptInGate
    execution_mode: KiwoomMockExecutionMode = KiwoomMockExecutionMode.KIWOOM_MOCK_DRY_RUN
    safety_report: KiwoomMockCredentialSafetyReport
    gap_report: KiwoomMockCredentialGapReport
    audit_records: list[KiwoomMockCredentialAuditRecord] = Field(default_factory=list)

    @field_validator("schema_version", "config_id", mode="before")
    @classmethod
    def normalize_schema_strings(cls, value, info):
        return _upper_required(value, info.field_name)

    @field_validator("fixture_format", mode="before")
    @classmethod
    def validate_fixture_format(cls, value):
        cleaned = _string_required(value, "fixture_format").lower()
        if cleaned == "parquet":
            raise ValueError("parquet remains unsupported")
        if cleaned != "json":
            raise ValueError("kiwoom mock credential boundary fixture must remain json")
        return cleaned

    @model_validator(mode="after")
    def validate_boundary_config(self):
        if not self.credential_refs:
            raise ValueError("credential_refs must not be empty")
        if self.execution_mode not in {
            KiwoomMockExecutionMode.KIWOOM_MOCK_DISABLED,
            KiwoomMockExecutionMode.KIWOOM_MOCK_DRY_RUN,
            KiwoomMockExecutionMode.KIWOOM_MOCK_OPT_IN_EXECUTION_FUTURE,
        }:
            raise ValueError("unsupported execution mode")
        return _validate_safety_flags(self, "kiwoom mock credential boundary config")
