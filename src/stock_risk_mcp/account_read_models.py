from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from pathlib import Path
from typing import Any

from pydantic import Field, field_validator, model_validator

from stock_risk_mcp.feature_store_models import FeatureStoreAuditRecord
from stock_risk_mcp.models import StrictModel


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
    blocked = ("credential", "token", "secret", "authorization", "api_key", "account_number")
    normalized: dict[str, ScalarValue] = {}
    for key, raw in value.items():
        name = _string_required(key, f"{field_name}.key")
        if any(marker in name.lower() for marker in blocked):
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
        "no_broker_paper_api",
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
        "account_read_only",
    ):
        if not getattr(model, flag_name):
            raise ValueError(f"{context} must remain {flag_name}")
    return model


class AccountReadProvider(StrEnum):
    LOCAL_MANUAL = "LOCAL_MANUAL"
    LOCAL_MOCK = "LOCAL_MOCK"
    REDACTED_CAPTURE = "REDACTED_CAPTURE"
    KIWOOM = "KIWOOM"
    LS = "LS"
    UNKNOWN = "UNKNOWN"


class AccountReadMode(StrEnum):
    MANUAL_FIXTURE = "MANUAL_FIXTURE"
    MOCKED_ADAPTER = "MOCKED_ADAPTER"
    REDACTED_CAPTURE = "REDACTED_CAPTURE"
    OPT_IN_REAL_READONLY_BOUNDARY = "OPT_IN_REAL_READONLY_BOUNDARY"


class AccountReadSourceKind(StrEnum):
    MANUAL_ACCOUNT_SNAPSHOT_FIXTURE = "MANUAL_ACCOUNT_SNAPSHOT_FIXTURE"
    MOCKED_ACCOUNT_READ_RESPONSE = "MOCKED_ACCOUNT_READ_RESPONSE"
    REDACTED_ACCOUNT_CAPTURE = "REDACTED_ACCOUNT_CAPTURE"
    OFFICIAL_API_EVIDENCE = "OFFICIAL_API_EVIDENCE"
    UNKNOWN = "UNKNOWN"


class AccountReadCredentialPolicy(StrEnum):
    NOT_REQUIRED = "NOT_REQUIRED"
    MOCK_ONLY = "MOCK_ONLY"
    KEY_REF_ONLY = "KEY_REF_ONLY"
    TOKEN_PROVIDER_ONLY = "TOKEN_PROVIDER_ONLY"
    BLOCKED = "BLOCKED"


class AccountReadProviderCapabilityStatus(StrEnum):
    SCHEMA_READY_READONLY = "SCHEMA_READY_READONLY"
    MOCKED_ADAPTER_READY = "MOCKED_ADAPTER_READY"
    OPT_IN_REAL_READONLY_BOUNDARY = "OPT_IN_REAL_READONLY_BOUNDARY"
    SCHEMA_GAP = "SCHEMA_GAP"
    PROVIDER_SETUP_REQUIRED = "PROVIDER_SETUP_REQUIRED"
    MANUAL_FIXTURE_ONLY = "MANUAL_FIXTURE_ONLY"


class AccountReadReadinessStatus(StrEnum):
    ACCOUNT_READ_READY = "ACCOUNT_READ_READY"
    ACCOUNT_READ_PREVIEW_READY = "ACCOUNT_READ_PREVIEW_READY"
    ACCOUNT_READ_FIXTURE_READY = "ACCOUNT_READ_FIXTURE_READY"
    ACCOUNT_READ_SNAPSHOT_READY = "ACCOUNT_READ_SNAPSHOT_READY"
    ACCOUNT_READ_BLOCKED_DEFAULT = "ACCOUNT_READ_BLOCKED_DEFAULT"
    ACCOUNT_READ_OPT_IN_REQUIRED = "ACCOUNT_READ_OPT_IN_REQUIRED"
    ACCOUNT_READ_SCHEMA_GAP = "ACCOUNT_READ_SCHEMA_GAP"
    ACCOUNT_READ_PROVIDER_SETUP_REQUIRED = "ACCOUNT_READ_PROVIDER_SETUP_REQUIRED"
    ACCOUNT_READ_STALE = "ACCOUNT_READ_STALE"
    ACCOUNT_READ_INCOMPLETE = "ACCOUNT_READ_INCOMPLETE"
    DATA_GAP = "DATA_GAP"
    STALE = "STALE"
    BLOCKED_ACCOUNT_MUTATION = "BLOCKED_ACCOUNT_MUTATION"
    BLOCKED_ORDER_API = "BLOCKED_ORDER_API"
    BLOCKED_CREDENTIAL_POLICY = "BLOCKED_CREDENTIAL_POLICY"
    BLOCKED_NETWORK_IN_TEST = "BLOCKED_NETWORK_IN_TEST"
    BLOCKED_EXECUTABLE_OUTPUT = "BLOCKED_EXECUTABLE_OUTPUT"
    RESEARCH_ONLY = "RESEARCH_ONLY"
    REJECTED = "REJECTED"


class AccountReadOptIn(StrictModel):
    allow_real_account_read: bool = False
    acknowledge_readonly_only: bool = False
    acknowledge_no_orders: bool = False
    acknowledge_no_account_mutation: bool = False
    acknowledge_user_initiated: bool = False


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
    no_broker_paper_api: bool = True
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
    account_read_only: bool = True


class AccountReadProviderCapabilityRow(StrictModel):
    provider: AccountReadProvider
    capability_status: AccountReadProviderCapabilityStatus
    credential_policy: AccountReadCredentialPolicy
    exact_api_evidence_present: bool = False
    notes: str = Field(..., min_length=1)

    @field_validator("notes", mode="before")
    @classmethod
    def normalize_notes(cls, value):
        return _string_required(value, "notes")


class AccountReadProviderCapabilityReport(_BaseSafety):
    report_id: str = Field(..., min_length=1)
    readiness_status: AccountReadReadinessStatus
    capability_rows: list[AccountReadProviderCapabilityRow] = Field(default_factory=list)

    @field_validator("report_id", mode="before")
    @classmethod
    def normalize_report_id(cls, value):
        return _upper_required(value, "report_id")

    @model_validator(mode="after")
    def validate_model(self):
        return _validate_safety_flags(self, "account read provider capability report")


class AccountReadRequestPreview(_BaseSafety):
    preview_id: str = Field(..., min_length=1)
    provider: AccountReadProvider
    mode: AccountReadMode
    readiness_status: AccountReadReadinessStatus
    request_path: str = Field(..., min_length=1)
    request_method: str = Field(default="GET", min_length=1)
    credential_policy: AccountReadCredentialPolicy
    account_ref: str = Field(..., min_length=1)
    requires_opt_in: bool = True
    can_execute_real_read: bool = False
    exact_api_evidence_present: bool = False
    query_params: dict[str, ScalarValue] = Field(default_factory=dict)
    header_keys: list[str] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)

    @field_validator("preview_id", "request_method", "account_ref", mode="before")
    @classmethod
    def normalize_upper(cls, value, info):
        if info.field_name == "account_ref":
            return _string_required(value, info.field_name)
        return _upper_required(value, info.field_name)

    @field_validator("request_path", mode="before")
    @classmethod
    def normalize_request_path(cls, value):
        return _string_required(value, "request_path")

    @field_validator("query_params", mode="before")
    @classmethod
    def normalize_query_params(cls, value):
        return _validate_scalar_map(value or {}, "query_params")

    @field_validator("header_keys", mode="before")
    @classmethod
    def normalize_header_keys(cls, value):
        return _normalize_list(value, "header_keys", upper=True)

    @field_validator("notes", mode="before")
    @classmethod
    def normalize_notes(cls, value):
        return _normalize_list(value, "notes")

    @model_validator(mode="after")
    def validate_model(self):
        return _validate_safety_flags(self, "account read request preview")


class AccountReadExecutionDecision(_BaseSafety):
    decision_id: str = Field(..., min_length=1)
    provider: AccountReadProvider
    readiness_status: AccountReadReadinessStatus
    approved: bool = False
    blocked_reasons: list[str] = Field(default_factory=list)

    @field_validator("decision_id", mode="before")
    @classmethod
    def normalize_id(cls, value):
        return _upper_required(value, "decision_id")

    @field_validator("blocked_reasons", mode="before")
    @classmethod
    def normalize_reasons(cls, value):
        return _normalize_list(value, "blocked_reasons", upper=True)

    @model_validator(mode="after")
    def validate_model(self):
        return _validate_safety_flags(self, "account read execution decision")


class AccountReadSourceRef(StrictModel):
    source_id: str = Field(..., min_length=1)
    source_kind: AccountReadSourceKind
    sanitized_basename: str = Field(..., min_length=1)
    relative_path: str | None = None
    available_at: datetime | None = None

    @field_validator("source_id", mode="before")
    @classmethod
    def normalize_id(cls, value):
        return _upper_required(value, "source_id")

    @field_validator("sanitized_basename", mode="before")
    @classmethod
    def normalize_basename(cls, value):
        return _string_required(value, "sanitized_basename")

    @field_validator("relative_path", mode="before")
    @classmethod
    def normalize_relative_path(cls, value):
        return _validate_relative_path(value, "relative_path")

    @field_validator("available_at", mode="before")
    @classmethod
    def normalize_dt(cls, value):
        return _aware(value)


class AccountReadCashBalance(StrictModel):
    currency: str = Field(..., min_length=1)
    available_cash: float
    settled_cash: float | None = None
    buying_power: float | None = None

    @field_validator("currency", mode="before")
    @classmethod
    def normalize_currency(cls, value):
        return _upper_required(value, "currency")


class AccountReadHolding(StrictModel):
    instrument_id: str = Field(..., min_length=1)
    market: str = Field(..., min_length=1)
    currency: str = Field(..., min_length=1)
    quantity: float
    average_cost: float | None = Field(default=None, gt=0)
    last_price: float | None = Field(default=None, gt=0)
    market_value: float | None = None
    unrealized_pnl: float | None = None
    weight: float | None = None
    long_only: bool = True
    source_ref: AccountReadSourceRef

    @field_validator("instrument_id", "market", "currency", mode="before")
    @classmethod
    def normalize_upper(cls, value, info):
        return _upper_required(value, info.field_name)


class AccountReadSnapshotMetadata(StrictModel):
    snapshot_id: str = Field(..., min_length=1)
    provider: AccountReadProvider
    mode: AccountReadMode
    account_ref: str = Field(..., min_length=1)
    account_ref_policy: str = Field(default="REDACTED_TEXT_PLUS_HASH", min_length=1)
    observed_at: datetime
    available_at: datetime
    account_base_currency: str = Field(default="KRW", min_length=1)
    source_ref: AccountReadSourceRef
    metadata: dict[str, ScalarValue] = Field(default_factory=dict)

    @field_validator("snapshot_id", "account_base_currency", mode="before")
    @classmethod
    def normalize_upper(cls, value, info):
        return _upper_required(value, info.field_name)

    @field_validator("account_ref", "account_ref_policy", mode="before")
    @classmethod
    def normalize_strings(cls, value, info):
        return _string_required(value, info.field_name)

    @field_validator("observed_at", "available_at", mode="before")
    @classmethod
    def normalize_dt(cls, value):
        return _aware(value)

    @field_validator("metadata", mode="before")
    @classmethod
    def normalize_metadata(cls, value):
        return _validate_scalar_map(value or {}, "metadata")


class AccountReadSnapshot(_BaseSafety):
    metadata: AccountReadSnapshotMetadata
    cash_balances: list[AccountReadCashBalance] = Field(default_factory=list)
    holdings: list[AccountReadHolding] = Field(default_factory=list)
    total_market_value: float | None = None
    total_equity: float | None = None
    total_unrealized_pnl: float | None = None

    @model_validator(mode="after")
    def validate_model(self):
        if self.metadata.available_at < self.metadata.observed_at:
            raise ValueError("snapshot available_at must be on or after observed_at")
        return _validate_safety_flags(self, "account read snapshot")


class AccountReadFreshnessReport(_BaseSafety):
    report_id: str = Field(..., min_length=1)
    snapshot_id: str = Field(..., min_length=1)
    readiness_status: AccountReadReadinessStatus
    stale_threshold_minutes: int = Field(default=1440, ge=1)
    age_minutes: int = Field(default=0, ge=0)
    stale: bool = False

    @field_validator("report_id", "snapshot_id", mode="before")
    @classmethod
    def normalize_upper(cls, value, info):
        return _upper_required(value, info.field_name)

    @model_validator(mode="after")
    def validate_model(self):
        return _validate_safety_flags(self, "account read freshness report")


class AccountReadCompletenessReport(_BaseSafety):
    report_id: str = Field(..., min_length=1)
    snapshot_id: str = Field(..., min_length=1)
    readiness_status: AccountReadReadinessStatus
    holdings_present: bool = False
    cash_present: bool = False
    average_cost_coverage: float = Field(default=0.0, ge=0, le=1)
    total_market_value_present: bool = False
    missing_fields: list[str] = Field(default_factory=list)

    @field_validator("report_id", "snapshot_id", mode="before")
    @classmethod
    def normalize_upper(cls, value, info):
        return _upper_required(value, info.field_name)

    @field_validator("missing_fields", mode="before")
    @classmethod
    def normalize_missing_fields(cls, value):
        return _normalize_list(value, "missing_fields", upper=True)

    @model_validator(mode="after")
    def validate_model(self):
        return _validate_safety_flags(self, "account read completeness report")


class AccountReadSafetyReport(_BaseSafety):
    report_id: str = Field(..., min_length=1)
    snapshot_id: str | None = None
    findings: list[str] = Field(default_factory=list)

    @field_validator("report_id", mode="before")
    @classmethod
    def normalize_id(cls, value):
        return _upper_required(value, "report_id")

    @field_validator("snapshot_id", mode="before")
    @classmethod
    def normalize_snapshot_id(cls, value):
        if value is None:
            return None
        return _upper_required(value, "snapshot_id")

    @field_validator("findings", mode="before")
    @classmethod
    def normalize_findings(cls, value):
        return _normalize_list(value, "findings", upper=True)

    @model_validator(mode="after")
    def validate_model(self):
        return _validate_safety_flags(self, "account read safety report")


class AccountReadGapEntry(StrictModel):
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


class AccountReadGapReport(_BaseSafety):
    report_id: str = Field(..., min_length=1)
    snapshot_id: str | None = None
    readiness_status: AccountReadReadinessStatus
    gap_entries: list[AccountReadGapEntry] = Field(default_factory=list)

    @field_validator("report_id", mode="before")
    @classmethod
    def normalize_id(cls, value):
        return _upper_required(value, "report_id")

    @field_validator("snapshot_id", mode="before")
    @classmethod
    def normalize_snapshot_id(cls, value):
        if value is None:
            return None
        return _upper_required(value, "snapshot_id")

    @model_validator(mode="after")
    def validate_model(self):
        return _validate_safety_flags(self, "account read gap report")


class AccountReadPipelineInput(_BaseSafety):
    pipeline_id: str = Field(..., min_length=1)
    provider: AccountReadProvider
    mode: AccountReadMode
    opt_in: AccountReadOptIn = Field(default_factory=AccountReadOptIn)
    snapshot_fixture: AccountReadSnapshot | None = None
    official_api_reference_url: str | None = None
    requested_at: datetime
    audit_records: list[FeatureStoreAuditRecord] = Field(default_factory=list)

    @field_validator("pipeline_id", mode="before")
    @classmethod
    def normalize_id(cls, value):
        return _upper_required(value, "pipeline_id")

    @field_validator("official_api_reference_url", mode="before")
    @classmethod
    def normalize_url(cls, value):
        if value is None:
            return None
        cleaned = _string_required(value, "official_api_reference_url")
        if any(marker in cleaned.lower() for marker in ("token", "secret", "authorization")):
            raise ValueError("official_api_reference_url must be sanitized")
        return cleaned

    @field_validator("requested_at", mode="before")
    @classmethod
    def normalize_requested_at(cls, value):
        return _aware(value)

    @model_validator(mode="after")
    def validate_input(self):
        return _validate_safety_flags(self, "account read pipeline input")


class AccountReadPipelineResult(StrictModel):
    capability_report: AccountReadProviderCapabilityReport
    request_preview: AccountReadRequestPreview
    execution_decision: AccountReadExecutionDecision
    snapshot: AccountReadSnapshot | None
    freshness_report: AccountReadFreshnessReport | None
    completeness_report: AccountReadCompletenessReport | None
    safety_report: AccountReadSafetyReport
    gap_report: AccountReadGapReport
