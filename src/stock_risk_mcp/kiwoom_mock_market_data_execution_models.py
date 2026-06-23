from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from pydantic import Field, field_validator, model_validator

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


class KiwoomMockMarketDataExecutionGapCategory(StrEnum):
    REAL_MARKET_DATA_STAGE_NOT_IMPLEMENTED = "REAL_MARKET_DATA_STAGE_NOT_IMPLEMENTED"
    ACCOUNT_STAGE_NOT_IMPLEMENTED = "ACCOUNT_STAGE_NOT_IMPLEMENTED"
    ORDER_STAGE_NOT_IMPLEMENTED = "ORDER_STAGE_NOT_IMPLEMENTED"
    WEBSOCKET_STAGE_NOT_IMPLEMENTED = "WEBSOCKET_STAGE_NOT_IMPLEMENTED"
    LIVE_STAGE_NOT_IMPLEMENTED = "LIVE_STAGE_NOT_IMPLEMENTED"


class _ExecutionBase(StrictModel):
    mock_only: bool = True
    execution_capable: bool = True
    read_only_market_data_execution_only: bool = True
    disabled_by_default: bool = True
    explicit_opt_in_required: bool = True
    non_executable_without_opt_in: bool = True
    redact_output: bool = True
    in_memory_token_only: bool = True
    no_token_persistence: bool = True
    no_token_refresh: bool = True
    no_production_domain_execution: bool = True
    no_account_path: bool = True
    no_order_path: bool = True
    no_websocket_path: bool = True
    no_live_prod: bool = True
    no_cloud_llm: bool = True
    no_local_llm_runtime: bool = True


class KiwoomMockMarketDataExecutionSafetyReport(_ExecutionBase):
    safety_report_id: str = Field(..., min_length=1)
    blocked_capabilities: list[str] = Field(default_factory=list)
    findings: list[str] = Field(default_factory=list)

    @field_validator("safety_report_id", mode="before")
    @classmethod
    def normalize_id(cls, value):
        return _upper_required(value, "safety_report_id")


class KiwoomMockMarketDataExecutionGapReport(_ExecutionBase):
    gap_report_id: str = Field(..., min_length=1)
    gap_status: str = Field(..., min_length=1)
    gap_categories: list[KiwoomMockMarketDataExecutionGapCategory] = Field(default_factory=list)
    blocking_gap_count: int = Field(..., ge=0)
    report_only_gap_count: int = Field(..., ge=0)
    gaps: list[str] = Field(default_factory=list)

    @field_validator("gap_report_id", "gap_status", mode="before")
    @classmethod
    def normalize_upper(cls, value):
        return _upper_required(value, "gap")


class KiwoomMockMarketDataExecutionAuditRecord(_ExecutionBase):
    audit_record_id: str = Field(..., min_length=1)
    created_at: datetime
    source_path: str = Field(..., min_length=1)
    redaction_applied: bool = True
    contains_secret_material: bool = False
    contains_token_material: bool = False
    contains_account_material: bool = False
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
    def normalize_refs(cls, value):
        if isinstance(value, (str, bytes)) or not isinstance(value, list) or not value:
            raise ValueError("evidence_refs must be a non-empty list")
        return [_upper_required(item, "evidence_ref") for item in value]


class KiwoomMockMarketDataExecutionConfig(_ExecutionBase):
    schema_version: str = Field(..., min_length=1)
    fixture_format: str = Field(..., min_length=1)
    config_id: str = Field(..., min_length=1)
    mock_domain: str = Field(..., min_length=1)
    documented_category: str = Field(..., min_length=1)
    documented_path: str = Field(..., min_length=1)
    preflight_readiness_decision: str = Field(..., min_length=1)
    token_reference_label: str = Field(..., min_length=1)
    timeout_seconds: int = Field(..., ge=1, le=10)
    max_retry_count: int = Field(..., ge=0, le=2)
    retry_backoff_seconds: float = Field(..., ge=0, le=1)
    persist_token_to_disk: bool = False
    allow_token_refresh: bool = False
    oauth_draft_boundary_ref: str = Field(..., min_length=1)
    transport_boundary_ref: str = Field(..., min_length=1)
    preflight_boundary_ref: str = Field(..., min_length=1)
    oauth_execution_boundary_ref: str = Field(..., min_length=1)
    safety_report: KiwoomMockMarketDataExecutionSafetyReport
    gap_report: KiwoomMockMarketDataExecutionGapReport
    audit_records: list[KiwoomMockMarketDataExecutionAuditRecord] = Field(default_factory=list)

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

    @field_validator("config_id", "documented_category", "preflight_readiness_decision", mode="before")
    @classmethod
    def normalize_upper_fields(cls, value):
        return _upper_required(value, "field")

    @field_validator("documented_path", "token_reference_label", mode="before")
    @classmethod
    def normalize_string_fields(cls, value):
        return _string_required(value, "field")

    @field_validator(
        "oauth_draft_boundary_ref",
        "transport_boundary_ref",
        "preflight_boundary_ref",
        "oauth_execution_boundary_ref",
        mode="before",
    )
    @classmethod
    def validate_ref_paths(cls, value):
        return _validate_local_path(value, "reference path")

    @field_validator("mock_domain", mode="before")
    @classmethod
    def validate_mock_domain(cls, value):
        cleaned = _string_required(value, "mock_domain")
        if cleaned != "https://mockapi.kiwoom.com":
            raise ValueError("production domain execution is blocked")
        return cleaned

    @model_validator(mode="after")
    def validate_config(self):
        if self.preflight_readiness_decision != "DRAFT_READY":
            raise ValueError("preflight must be DRAFT_READY")
        if self.documented_category == "QUOTE" and self.documented_path != "/api/dostk/mrkcond":
            raise ValueError("only documented read-only market-data path is allowed")
        if self.persist_token_to_disk:
            raise ValueError("token persistence is not allowed")
        if self.allow_token_refresh:
            raise ValueError("token refresh is not allowed")
        if not self.audit_records:
            raise ValueError("audit_records must not be empty")
        return self


class KiwoomMockMarketDataResponse(_ExecutionBase):
    response_object_id: str = Field(..., min_length=1)
    documented_category: str = Field(..., min_length=1)
    documented_path: str = Field(..., min_length=1)
    symbol: str = Field(..., min_length=1)
    payload: dict[str, object] = Field(default_factory=dict)
    sanitized: bool = True
    raw_token_exposed: bool = False
    persisted_to_disk: bool = False

    @field_validator("response_object_id", "documented_category", mode="before")
    @classmethod
    def normalize_upper_fields(cls, value):
        return _upper_required(value, "field")

    @field_validator("documented_path", "symbol", mode="before")
    @classmethod
    def normalize_string_fields(cls, value):
        return _string_required(value, "field")

    @model_validator(mode="after")
    def validate_response(self):
        if self.raw_token_exposed:
            raise ValueError("raw token must not be exposed")
        if self.persisted_to_disk:
            raise ValueError("response must not be persisted")
        return self


class KiwoomMockMarketDataExecutionResult(_ExecutionBase):
    execution_result_id: str = Field(..., min_length=1)
    executed: bool = False
    mock_transport_used: bool = False
    real_network_performed: bool = False
    token_used_in_memory_only: bool = True
    response: KiwoomMockMarketDataResponse
    safety_report: KiwoomMockMarketDataExecutionSafetyReport
    gap_report: KiwoomMockMarketDataExecutionGapReport
    audit_records: list[KiwoomMockMarketDataExecutionAuditRecord] = Field(default_factory=list)

    @field_validator("execution_result_id", mode="before")
    @classmethod
    def normalize_id(cls, value):
        return _upper_required(value, "execution_result_id")
