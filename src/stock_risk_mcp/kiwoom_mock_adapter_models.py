from __future__ import annotations

import json
from datetime import datetime
from enum import StrEnum
from functools import lru_cache
from pathlib import Path

from pydantic import Field, field_validator, model_validator

from stock_risk_mcp.kiwoom_mock_adapter_guard import validate_kiwoom_mock_adapter_metadata_safety
from stock_risk_mcp.models import StrictModel
from stock_risk_mcp.strategy_track_models import StrategyTrack


def aware(value: datetime) -> datetime:
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


def _normalize_id_list(value, field_name: str) -> list[str]:
    if value is None:
        return []
    if isinstance(value, (str, bytes)) or not isinstance(value, list):
        raise ValueError(f"{field_name} must be a list")
    return [_upper_required(item, field_name) for item in value]


def _validate_local_path(value: str, field_name: str) -> str:
    cleaned = _string_required(value, field_name)
    lowered = cleaned.lower()
    if "://" in lowered or lowered.startswith("//"):
        raise ValueError(f"{field_name} must be a local file path")
    if lowered.endswith(".parquet"):
        raise ValueError("parquet remains unsupported")
    return cleaned


def _validate_metadata(value, field_name: str):
    if value is None:
        return {}
    if not isinstance(value, dict):
        raise ValueError(f"{field_name} must be a dict")
    return validate_kiwoom_mock_adapter_metadata_safety(value, context=field_name)


def _validate_safety_flags(model, context: str):
    for flag_name in (
        "kiwoom_mock_only",
        "draft_only",
        "paper_only",
        "disabled_by_default",
        "explicit_opt_in_required",
        "non_executable",
        "local_file_only",
        "offline_only",
        "evidence_backed",
        "no_credentials_loaded",
        "no_oauth_token_request",
        "no_api_call",
        "no_mockapi_call",
        "no_network_call",
        "no_websocket_connection",
        "no_real_order",
        "no_real_account_mutation",
        "no_live_trading",
        "no_live_prod",
        "no_broker_api_call",
        "no_order_api_call",
        "no_account_api_call",
        "no_provider_api_call",
        "no_cloud_llm",
        "no_local_llm_runtime",
    ):
        if not getattr(model, flag_name):
            raise ValueError(f"{context} must remain {flag_name}")
    return model


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


@lru_cache(maxsize=1)
def _load_kiwoom_evidence_matrix() -> dict[str, object]:
    matrix_path = _repo_root() / "docs/superpowers/specs/2026-06-18-kiwoom-rest-api-capability-matrix.json"
    return json.loads(matrix_path.read_text(encoding="utf-8"))


@lru_cache(maxsize=1)
def _build_supported_endpoint_map() -> dict[str, dict[str, object]]:
    matrix = _load_kiwoom_evidence_matrix()
    endpoints = matrix.get("endpoints", [])
    supported_ids = {"KT10000", "KT10001", "KT10002", "KT10003"}
    mapping = {}
    for endpoint in endpoints:
        api_id = str(endpoint.get("api_id", "")).strip().upper()
        if api_id in supported_ids:
            mapping[api_id] = endpoint
    return mapping


_CAPABILITY_TO_ENDPOINT = {
    "DOMESTIC_STOCK_ORDER_CREATE_MOCK": {"KT10000", "KT10001"},
    "DOMESTIC_STOCK_ORDER_MODIFY_MOCK": {"KT10002"},
    "DOMESTIC_STOCK_ORDER_CANCEL_MOCK": {"KT10003"},
}


class KiwoomMockDraftSide(StrEnum):
    KIWOOM_MOCK_BUY_DRAFT = "KIWOOM_MOCK_BUY_DRAFT"
    KIWOOM_MOCK_SELL_DRAFT = "KIWOOM_MOCK_SELL_DRAFT"
    KIWOOM_MOCK_CANCEL_DRAFT = "KIWOOM_MOCK_CANCEL_DRAFT"
    KIWOOM_MOCK_REPLACE_DRAFT = "KIWOOM_MOCK_REPLACE_DRAFT"
    KIWOOM_MOCK_CLOSE_DRAFT = "KIWOOM_MOCK_CLOSE_DRAFT"


class KiwoomMockGapCategory(StrEnum):
    KIWOOM_MOCK_DRAFT_GENERATED = "KIWOOM_MOCK_DRAFT_GENERATED"
    KIWOOM_MOCK_EVIDENCE_BACKED = "KIWOOM_MOCK_EVIDENCE_BACKED"
    KIWOOM_MOCK_DRAFT_ONLY = "KIWOOM_MOCK_DRAFT_ONLY"
    KIWOOM_MOCK_LOCAL_ONLY = "KIWOOM_MOCK_LOCAL_ONLY"
    KIWOOM_MOCK_OFFLINE_ONLY = "KIWOOM_MOCK_OFFLINE_ONLY"
    KIWOOM_MOCK_DISABLED_BY_DEFAULT = "KIWOOM_MOCK_DISABLED_BY_DEFAULT"
    KIWOOM_MOCK_EXPLICIT_OPT_IN_REQUIRED = "KIWOOM_MOCK_EXPLICIT_OPT_IN_REQUIRED"
    KIWOOM_MOCK_NON_EXECUTABLE = "KIWOOM_MOCK_NON_EXECUTABLE"
    KIWOOM_MOCK_MISSING_INPUT = "KIWOOM_MOCK_MISSING_INPUT"
    KIWOOM_MOCK_MISSING_CAPABILITY_REF = "KIWOOM_MOCK_MISSING_CAPABILITY_REF"
    KIWOOM_MOCK_MISSING_BROKER_MOCK_ORDER_INTENT_REF = "KIWOOM_MOCK_MISSING_BROKER_MOCK_ORDER_INTENT_REF"
    KIWOOM_MOCK_MISSING_EVIDENCE_ENDPOINT_REF = "KIWOOM_MOCK_MISSING_EVIDENCE_ENDPOINT_REF"
    KIWOOM_MOCK_UNSUPPORTED_CAPABILITY = "KIWOOM_MOCK_UNSUPPORTED_CAPABILITY"
    KIWOOM_MOCK_UNSUPPORTED_ORDER_SIDE = "KIWOOM_MOCK_UNSUPPORTED_ORDER_SIDE"
    KIWOOM_MOCK_UNSUPPORTED_ORDER_TYPE = "KIWOOM_MOCK_UNSUPPORTED_ORDER_TYPE"
    KIWOOM_MOCK_MOCK_DOMAIN_REQUIRED = "KIWOOM_MOCK_MOCK_DOMAIN_REQUIRED"
    KIWOOM_MOCK_KRX_ONLY_CONSTRAINT = "KIWOOM_MOCK_KRX_ONLY_CONSTRAINT"
    KIWOOM_MOCK_CREDENTIALS_NOT_ALLOWED = "KIWOOM_MOCK_CREDENTIALS_NOT_ALLOWED"
    KIWOOM_MOCK_OAUTH_TOKEN_REQUEST_NOT_ALLOWED = "KIWOOM_MOCK_OAUTH_TOKEN_REQUEST_NOT_ALLOWED"
    KIWOOM_MOCK_API_CALL_NOT_ALLOWED = "KIWOOM_MOCK_API_CALL_NOT_ALLOWED"
    KIWOOM_MOCK_MOCKAPI_CALL_NOT_ALLOWED = "KIWOOM_MOCK_MOCKAPI_CALL_NOT_ALLOWED"
    KIWOOM_MOCK_NETWORK_CALL_NOT_ALLOWED = "KIWOOM_MOCK_NETWORK_CALL_NOT_ALLOWED"
    KIWOOM_MOCK_WEBSOCKET_NOT_ALLOWED = "KIWOOM_MOCK_WEBSOCKET_NOT_ALLOWED"
    KIWOOM_MOCK_REAL_ORDER_NOT_ALLOWED = "KIWOOM_MOCK_REAL_ORDER_NOT_ALLOWED"
    KIWOOM_MOCK_REAL_ACCOUNT_MUTATION_NOT_ALLOWED = "KIWOOM_MOCK_REAL_ACCOUNT_MUTATION_NOT_ALLOWED"
    KIWOOM_MOCK_LIVE_TRADING_NOT_ALLOWED = "KIWOOM_MOCK_LIVE_TRADING_NOT_ALLOWED"
    KIWOOM_MOCK_LIVE_PROD_NOT_ALLOWED = "KIWOOM_MOCK_LIVE_PROD_NOT_ALLOWED"
    KIWOOM_MOCK_BROKER_API_CALL_NOT_ALLOWED = "KIWOOM_MOCK_BROKER_API_CALL_NOT_ALLOWED"
    KIWOOM_MOCK_ORDER_API_CALL_NOT_ALLOWED = "KIWOOM_MOCK_ORDER_API_CALL_NOT_ALLOWED"
    KIWOOM_MOCK_ACCOUNT_API_CALL_NOT_ALLOWED = "KIWOOM_MOCK_ACCOUNT_API_CALL_NOT_ALLOWED"
    KIWOOM_MOCK_PROVIDER_API_CALL_NOT_ALLOWED = "KIWOOM_MOCK_PROVIDER_API_CALL_NOT_ALLOWED"
    KIWOOM_MOCK_CLOUD_LLM_NOT_ALLOWED = "KIWOOM_MOCK_CLOUD_LLM_NOT_ALLOWED"
    KIWOOM_MOCK_LOCAL_LLM_RUNTIME_NOT_ALLOWED = "KIWOOM_MOCK_LOCAL_LLM_RUNTIME_NOT_ALLOWED"
    KIWOOM_MOCK_PARQUET_NOT_ALLOWED = "KIWOOM_MOCK_PARQUET_NOT_ALLOWED"


class _KiwoomMockBase(StrictModel):
    kiwoom_mock_only: bool = True
    draft_only: bool = True
    paper_only: bool = True
    disabled_by_default: bool = True
    explicit_opt_in_required: bool = True
    non_executable: bool = True
    local_file_only: bool = True
    offline_only: bool = True
    evidence_backed: bool = True
    no_credentials_loaded: bool = True
    no_oauth_token_request: bool = True
    no_api_call: bool = True
    no_mockapi_call: bool = True
    no_network_call: bool = True
    no_websocket_connection: bool = True
    no_real_order: bool = True
    no_real_account_mutation: bool = True
    no_live_trading: bool = True
    no_live_prod: bool = True
    no_broker_api_call: bool = True
    no_order_api_call: bool = True
    no_account_api_call: bool = True
    no_provider_api_call: bool = True
    no_cloud_llm: bool = True
    no_local_llm_runtime: bool = True


class KiwoomMockAdapterConfig(_KiwoomMockBase):
    config_id: str = Field(..., min_length=1)
    strategy_track: StrategyTrack
    market: str = Field(..., min_length=1)
    broker_mock_adapter_id: str = Field(..., min_length=1)
    evidence_pack_ref: str = Field(..., min_length=1)
    capability_matrix_ref: str = Field(..., min_length=1)

    @field_validator("config_id", "market", "broker_mock_adapter_id", mode="before")
    @classmethod
    def normalize_ids(cls, value, info):
        return _upper_required(value, info.field_name)

    @field_validator("evidence_pack_ref", "capability_matrix_ref", mode="before")
    @classmethod
    def validate_local_refs(cls, value, info):
        return _validate_local_path(value, info.field_name)

    @model_validator(mode="after")
    def validate_config(self):
        if self.strategy_track != StrategyTrack.DOMESTIC_KR:
            raise ValueError("kiwoom mock adapter config requires StrategyTrack DOMESTIC_KR")
        if self.market != "KRX":
            raise ValueError("kiwoom mock adapter config requires KRX market")
        return _validate_safety_flags(self, "kiwoom mock adapter config")


class KiwoomMockCapabilityRef(_KiwoomMockBase):
    capability_ref_id: str = Field(..., min_length=1)
    evidence_endpoint_ref: str = Field(..., min_length=1)
    evidence_category: str = Field(..., min_length=1)
    endpoint_path: str = Field(..., min_length=1)
    http_method: str = Field(..., min_length=1)
    mock_domain: str = Field(..., min_length=1)
    mock_krx_only: bool = True
    documented_request_fields: list[str] = Field(default_factory=list)
    documented_response_fields: list[str] = Field(default_factory=list)
    supported_draft_sides: list[KiwoomMockDraftSide] = Field(default_factory=list)
    supported_order_types: list[str] = Field(default_factory=list)

    @field_validator("capability_ref_id", "evidence_endpoint_ref", "http_method", mode="before")
    @classmethod
    def normalize_core_ids(cls, value, info):
        return _upper_required(value, info.field_name)

    @field_validator("evidence_category", "endpoint_path", "mock_domain", mode="before")
    @classmethod
    def normalize_strings(cls, value, info):
        return _string_required(value, info.field_name)

    @field_validator("documented_request_fields", "documented_response_fields", mode="before")
    @classmethod
    def validate_field_lists(cls, value):
        if value is None:
            return []
        if isinstance(value, (str, bytes)) or not isinstance(value, list):
            raise ValueError("documented fields must be a list")
        return [str(item).strip() for item in value]

    @field_validator("supported_order_types", mode="before")
    @classmethod
    def validate_order_types(cls, value):
        if value is None:
            return []
        if isinstance(value, (str, bytes)) or not isinstance(value, list):
            raise ValueError("supported_order_types must be a list")
        return [_upper_required(item, "supported_order_type") for item in value]

    @model_validator(mode="after")
    def validate_capability_ref(self):
        if self.capability_ref_id not in _CAPABILITY_TO_ENDPOINT:
            raise ValueError("unsupported capability")
        if self.evidence_endpoint_ref not in _CAPABILITY_TO_ENDPOINT[self.capability_ref_id]:
            raise ValueError("unsupported capability")
        endpoint_map = _build_supported_endpoint_map()
        if self.evidence_endpoint_ref not in endpoint_map:
            raise ValueError("evidence_endpoint_ref must reference a supported official order endpoint")
        official = endpoint_map[self.evidence_endpoint_ref]
        if self.endpoint_path != str(official.get("url_path", "")).strip():
            raise ValueError("endpoint_path must match official evidence")
        if self.http_method != str(official.get("http_method", "")).strip().upper():
            raise ValueError("http_method must match official evidence")
        if self.mock_domain != "https://mockapi.kiwoom.com":
            raise ValueError("mock domain is required")
        if not self.mock_krx_only:
            raise ValueError("KRX-only mock constraint must be represented")
        return _validate_safety_flags(self, "kiwoom mock capability ref")


class KiwoomMockOrderDraft(_KiwoomMockBase):
    order_draft_id: str = Field(..., min_length=1)
    source_broker_mock_order_intent_ref_id: str = Field(..., min_length=1)
    source_paper_order_intent_ref_id: str = Field(..., min_length=1)
    source_signal_candidate_ref_id: str = Field(..., min_length=1)
    symbol: str = Field(..., min_length=1)
    market: str = Field(..., min_length=1)
    market_profile: str = Field(..., min_length=1)
    strategy_track: StrategyTrack
    side: KiwoomMockDraftSide
    order_type: str = Field(..., min_length=1)
    quantity: float = Field(..., gt=0)
    price: float = Field(..., ge=0)
    documented_endpoint_path: str = Field(..., min_length=1)
    documented_api_id: str = Field(..., min_length=1)
    documented_required_fields: list[str] = Field(default_factory=list)
    source_manifest_ids: list[str] = Field(default_factory=list)
    source_audit_record_ids: list[str] = Field(default_factory=list)
    provider_provenance_ids: list[str] = Field(default_factory=list)
    metadata: dict[str, object] = Field(default_factory=dict)

    @field_validator(
        "order_draft_id",
        "source_broker_mock_order_intent_ref_id",
        "source_paper_order_intent_ref_id",
        "source_signal_candidate_ref_id",
        "symbol",
        "market",
        "market_profile",
        "order_type",
        "documented_api_id",
        mode="before",
    )
    @classmethod
    def normalize_fields(cls, value, info):
        return _upper_required(value, info.field_name)

    @field_validator("documented_endpoint_path", mode="before")
    @classmethod
    def normalize_endpoint_path(cls, value):
        return _string_required(value, "documented_endpoint_path")

    @field_validator("documented_required_fields", mode="before")
    @classmethod
    def validate_required_fields(cls, value):
        if value is None:
            return []
        if isinstance(value, (str, bytes)) or not isinstance(value, list):
            raise ValueError("documented_required_fields must be a list")
        return [str(item).strip() for item in value]

    @field_validator("source_manifest_ids", "source_audit_record_ids", "provider_provenance_ids", mode="before")
    @classmethod
    def normalize_id_lists(cls, value, info):
        return _normalize_id_list(value, info.field_name)

    @field_validator("metadata", mode="before")
    @classmethod
    def validate_metadata(cls, value):
        return _validate_metadata(value, "metadata")

    @field_validator("side", mode="before")
    @classmethod
    def validate_side(cls, value):
        candidate = _upper_required(value, "side")
        if candidate in {"BUY", "SELL", "CANCEL", "REPLACE", "CLOSE", "ORDER"}:
            raise ValueError("bare order/action values are not allowed")
        return KiwoomMockDraftSide(candidate)

    @model_validator(mode="after")
    def validate_order_draft(self):
        if self.strategy_track != StrategyTrack.DOMESTIC_KR:
            raise ValueError("kiwoom mock order draft requires StrategyTrack DOMESTIC_KR")
        if self.market != "KRX":
            raise ValueError("kiwoom mock order draft requires KRX market")
        return _validate_safety_flags(self, "kiwoom mock order draft")


class KiwoomMockOrderRequestDraft(_KiwoomMockBase):
    request_draft_id: str = Field(..., min_length=1)
    order_draft_id: str = Field(..., min_length=1)
    request_body_fields: dict[str, object] = Field(default_factory=dict)
    metadata: dict[str, object] = Field(default_factory=dict)

    @field_validator("request_draft_id", "order_draft_id", mode="before")
    @classmethod
    def normalize_ids(cls, value, info):
        return _upper_required(value, info.field_name)

    @field_validator("request_body_fields", "metadata", mode="before")
    @classmethod
    def validate_request_parts(cls, value, info):
        return _validate_metadata(value, info.field_name)

    @model_validator(mode="after")
    def validate_request(self):
        return _validate_safety_flags(self, "kiwoom mock order request draft")


class KiwoomMockOrderResponseDraft(_KiwoomMockBase):
    response_draft_id: str = Field(..., min_length=1)
    request_draft_id: str = Field(..., min_length=1)
    documented_response_fields: list[str] = Field(default_factory=list)
    metadata: dict[str, object] = Field(default_factory=dict)

    @field_validator("response_draft_id", "request_draft_id", mode="before")
    @classmethod
    def normalize_ids(cls, value, info):
        return _upper_required(value, info.field_name)

    @field_validator("documented_response_fields", mode="before")
    @classmethod
    def validate_documented_fields(cls, value):
        if value is None:
            return []
        if isinstance(value, (str, bytes)) or not isinstance(value, list):
            raise ValueError("documented_response_fields must be a list")
        return [str(item).strip() for item in value]

    @field_validator("metadata", mode="before")
    @classmethod
    def validate_metadata(cls, value):
        return _validate_metadata(value, "metadata")

    @model_validator(mode="after")
    def validate_response(self):
        return _validate_safety_flags(self, "kiwoom mock order response draft")


class KiwoomMockExecutionDraft(_KiwoomMockBase):
    execution_draft_id: str = Field(..., min_length=1)
    order_draft_id: str = Field(..., min_length=1)
    request_draft_id: str = Field(..., min_length=1)
    response_draft_id: str = Field(..., min_length=1)
    symbol: str = Field(..., min_length=1)
    side: KiwoomMockDraftSide
    documented_status: str = Field(..., min_length=1)
    metadata: dict[str, object] = Field(default_factory=dict)

    @field_validator(
        "execution_draft_id",
        "order_draft_id",
        "request_draft_id",
        "response_draft_id",
        "symbol",
        "documented_status",
        mode="before",
    )
    @classmethod
    def normalize_fields(cls, value, info):
        return _upper_required(value, info.field_name)

    @field_validator("metadata", mode="before")
    @classmethod
    def validate_metadata(cls, value):
        return _validate_metadata(value, "metadata")

    @model_validator(mode="after")
    def validate_execution(self):
        return _validate_safety_flags(self, "kiwoom mock execution draft")


class KiwoomMockPositionSnapshotDraft(_KiwoomMockBase):
    position_snapshot_draft_id: str = Field(..., min_length=1)
    symbol: str = Field(..., min_length=1)
    market: str = Field(..., min_length=1)
    quantity: float = Field(..., ge=0)
    average_price: float = Field(..., ge=0)
    mark_price: float = Field(..., ge=0)
    exposure_value: float = Field(..., ge=0)
    metadata: dict[str, object] = Field(default_factory=dict)

    @field_validator("position_snapshot_draft_id", "symbol", "market", mode="before")
    @classmethod
    def normalize_fields(cls, value, info):
        return _upper_required(value, info.field_name)

    @field_validator("metadata", mode="before")
    @classmethod
    def validate_metadata(cls, value):
        return _validate_metadata(value, "metadata")

    @model_validator(mode="after")
    def validate_position(self):
        if self.market != "KRX":
            raise ValueError("kiwoom mock position snapshot draft requires KRX market")
        return _validate_safety_flags(self, "kiwoom mock position snapshot draft")


class KiwoomMockAccountSnapshotDraft(_KiwoomMockBase):
    account_snapshot_draft_id: str = Field(..., min_length=1)
    base_currency: str = Field(..., min_length=1)
    position_snapshots: list[KiwoomMockPositionSnapshotDraft] = Field(default_factory=list)
    metadata: dict[str, object] = Field(default_factory=dict)

    @field_validator("account_snapshot_draft_id", "base_currency", mode="before")
    @classmethod
    def normalize_fields(cls, value, info):
        return _upper_required(value, info.field_name)

    @field_validator("metadata", mode="before")
    @classmethod
    def validate_metadata(cls, value):
        return _validate_metadata(value, "metadata")

    @model_validator(mode="after")
    def validate_account(self):
        return _validate_safety_flags(self, "kiwoom mock account snapshot draft")


class KiwoomMockAdapterSafetyReport(_KiwoomMockBase):
    safety_report_id: str = Field(..., min_length=1)
    blocked: bool = False
    findings: list[str] = Field(default_factory=list)

    @field_validator("safety_report_id", mode="before")
    @classmethod
    def normalize_id(cls, value):
        return _upper_required(value, "safety_report_id")

    @model_validator(mode="after")
    def validate_report(self):
        return _validate_safety_flags(self, "kiwoom mock adapter safety report")


class KiwoomMockAdapterGapReport(_KiwoomMockBase):
    gap_report_id: str = Field(..., min_length=1)
    adapter_input_id: str = Field(..., min_length=1)
    gap_status: str = Field(..., min_length=1)
    gap_categories: list[KiwoomMockGapCategory] = Field(default_factory=list)
    blocking_gap_count: int = Field(default=0, ge=0)
    report_only_gap_count: int = Field(default=0, ge=0)
    gaps: list[str] = Field(default_factory=list)
    source_manifest_ids: list[str] = Field(default_factory=list)
    source_audit_record_ids: list[str] = Field(default_factory=list)
    provider_provenance_ids: list[str] = Field(default_factory=list)

    @field_validator("gap_report_id", "adapter_input_id", "gap_status", mode="before")
    @classmethod
    def normalize_ids(cls, value, info):
        return _upper_required(value, info.field_name)

    @field_validator("source_manifest_ids", "source_audit_record_ids", "provider_provenance_ids", mode="before")
    @classmethod
    def normalize_lists(cls, value, info):
        return _normalize_id_list(value, info.field_name)

    @model_validator(mode="after")
    def validate_gap_report(self):
        return _validate_safety_flags(self, "kiwoom mock adapter gap report")


class KiwoomMockAdapterAuditRecord(_KiwoomMockBase):
    audit_record_id: str = Field(..., min_length=1)
    adapter_input_id: str = Field(..., min_length=1)
    created_at: datetime
    operator_context: str = Field(..., min_length=1)
    source_path: str = Field(..., min_length=1)
    source_manifest_ids: list[str] = Field(default_factory=list)
    source_audit_record_ids: list[str] = Field(default_factory=list)
    provider_provenance_ids: list[str] = Field(default_factory=list)

    @field_validator("audit_record_id", "adapter_input_id", "operator_context", mode="before")
    @classmethod
    def normalize_ids(cls, value, info):
        return _upper_required(value, info.field_name)

    @field_validator("created_at", mode="after")
    @classmethod
    def validate_created_at(cls, value):
        return aware(value)

    @field_validator("source_path", mode="before")
    @classmethod
    def validate_source_path(cls, value):
        return _validate_local_path(value, "source_path")

    @field_validator("source_manifest_ids", "source_audit_record_ids", "provider_provenance_ids", mode="before")
    @classmethod
    def normalize_lists(cls, value, info):
        return _normalize_id_list(value, info.field_name)

    @model_validator(mode="after")
    def validate_record(self):
        return _validate_safety_flags(self, "kiwoom mock adapter audit record")


class KiwoomMockAdapterInput(_KiwoomMockBase):
    schema_version: str = Field(..., min_length=1)
    adapter_input_id: str = Field(..., min_length=1)
    adapter_config: KiwoomMockAdapterConfig
    capability_ref: KiwoomMockCapabilityRef
    order_draft: KiwoomMockOrderDraft
    order_request_draft: KiwoomMockOrderRequestDraft
    order_response_draft: KiwoomMockOrderResponseDraft
    execution_draft: KiwoomMockExecutionDraft
    account_snapshot_draft: KiwoomMockAccountSnapshotDraft
    safety_report: KiwoomMockAdapterSafetyReport
    gap_report: KiwoomMockAdapterGapReport
    audit_records: list[KiwoomMockAdapterAuditRecord] = Field(default_factory=list)

    @field_validator("schema_version", "adapter_input_id", mode="before")
    @classmethod
    def normalize_headers(cls, value, info):
        return _upper_required(value, info.field_name)

    @model_validator(mode="after")
    def validate_input(self):
        if not self.capability_ref.evidence_endpoint_ref:
            raise ValueError("evidence_endpoint_ref must not be blank")
        if not self.order_draft.source_broker_mock_order_intent_ref_id:
            raise ValueError("source_broker_mock_order_intent_ref_id must not be blank")
        if self.order_draft.documented_api_id != self.capability_ref.evidence_endpoint_ref:
            raise ValueError("documented_api_id must match evidence_endpoint_ref")
        if self.order_draft.documented_endpoint_path != self.capability_ref.endpoint_path:
            raise ValueError("documented_endpoint_path must match capability endpoint_path")
        if self.order_draft.order_type not in self.capability_ref.supported_order_types:
            raise ValueError("unsupported order type")
        if self.adapter_config.market != "KRX" or self.order_draft.market != "KRX":
            raise ValueError("mock KRX-only constraint must be preserved")
        return _validate_safety_flags(self, "kiwoom mock adapter input")
