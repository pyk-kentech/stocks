from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from pydantic import Field, field_validator, model_validator

from stock_risk_mcp.broker_mock_adapter_guard import validate_broker_mock_adapter_metadata_safety
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


def _validate_safety_flags(model, context: str):
    for flag_name in (
        "mock_only",
        "paper_only",
        "disabled_by_default",
        "explicit_opt_in_required",
        "non_executable_by_default",
        "local_file_only",
        "offline_only",
        "no_real_order",
        "no_real_account_mutation",
        "no_live_trading",
        "no_live_prod",
        "no_production_broker",
        "no_credentials_loaded",
        "no_network_call",
        "no_kiwoom_api_call",
        "no_ls_api_call",
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


def _validate_metadata(value, field_name: str):
    if value is None:
        return {}
    if not isinstance(value, dict):
        raise ValueError(f"{field_name} must be a dict")
    return validate_broker_mock_adapter_metadata_safety(value, context=field_name)


class BrokerMockOrderSide(StrEnum):
    MOCK_BUY = "MOCK_BUY"
    MOCK_SELL = "MOCK_SELL"
    MOCK_CANCEL = "MOCK_CANCEL"
    MOCK_REPLACE = "MOCK_REPLACE"
    MOCK_CLOSE = "MOCK_CLOSE"


class BrokerMockGapCategory(StrEnum):
    BROKER_MOCK_BOUNDARY_GENERATED = "BROKER_MOCK_BOUNDARY_GENERATED"
    BROKER_MOCK_LOCAL_ONLY = "BROKER_MOCK_LOCAL_ONLY"
    BROKER_MOCK_OFFLINE_ONLY = "BROKER_MOCK_OFFLINE_ONLY"
    BROKER_MOCK_MOCK_ONLY = "BROKER_MOCK_MOCK_ONLY"
    BROKER_MOCK_PAPER_ONLY = "BROKER_MOCK_PAPER_ONLY"
    BROKER_MOCK_DISABLED_BY_DEFAULT = "BROKER_MOCK_DISABLED_BY_DEFAULT"
    BROKER_MOCK_EXPLICIT_OPT_IN_REQUIRED = "BROKER_MOCK_EXPLICIT_OPT_IN_REQUIRED"
    BROKER_MOCK_NON_EXECUTABLE_BY_DEFAULT = "BROKER_MOCK_NON_EXECUTABLE_BY_DEFAULT"
    BROKER_MOCK_MISSING_INPUT = "BROKER_MOCK_MISSING_INPUT"
    BROKER_MOCK_MISSING_PAPER_ORDER_INTENT_REF = "BROKER_MOCK_MISSING_PAPER_ORDER_INTENT_REF"
    BROKER_MOCK_MISSING_CAPABILITY = "BROKER_MOCK_MISSING_CAPABILITY"
    BROKER_MOCK_UNSUPPORTED_CAPABILITY = "BROKER_MOCK_UNSUPPORTED_CAPABILITY"
    BROKER_MOCK_UNSUPPORTED_ORDER_TYPE = "BROKER_MOCK_UNSUPPORTED_ORDER_TYPE"
    BROKER_MOCK_UNSUPPORTED_ORDER_SIDE = "BROKER_MOCK_UNSUPPORTED_ORDER_SIDE"
    BROKER_MOCK_REAL_ORDER_NOT_ALLOWED = "BROKER_MOCK_REAL_ORDER_NOT_ALLOWED"
    BROKER_MOCK_REAL_ORDER_INTENT_NOT_ALLOWED = "BROKER_MOCK_REAL_ORDER_INTENT_NOT_ALLOWED"
    BROKER_MOCK_REAL_ACCOUNT_MUTATION_NOT_ALLOWED = "BROKER_MOCK_REAL_ACCOUNT_MUTATION_NOT_ALLOWED"
    BROKER_MOCK_LIVE_TRADING_NOT_ALLOWED = "BROKER_MOCK_LIVE_TRADING_NOT_ALLOWED"
    BROKER_MOCK_LIVE_PROD_NOT_ALLOWED = "BROKER_MOCK_LIVE_PROD_NOT_ALLOWED"
    BROKER_MOCK_PRODUCTION_BROKER_NOT_ALLOWED = "BROKER_MOCK_PRODUCTION_BROKER_NOT_ALLOWED"
    BROKER_MOCK_CREDENTIALS_NOT_ALLOWED = "BROKER_MOCK_CREDENTIALS_NOT_ALLOWED"
    BROKER_MOCK_NETWORK_CALL_NOT_ALLOWED = "BROKER_MOCK_NETWORK_CALL_NOT_ALLOWED"
    BROKER_MOCK_KIWOOM_API_CALL_NOT_ALLOWED = "BROKER_MOCK_KIWOOM_API_CALL_NOT_ALLOWED"
    BROKER_MOCK_LS_API_CALL_NOT_ALLOWED = "BROKER_MOCK_LS_API_CALL_NOT_ALLOWED"
    BROKER_MOCK_BROKER_API_CALL_NOT_ALLOWED = "BROKER_MOCK_BROKER_API_CALL_NOT_ALLOWED"
    BROKER_MOCK_ORDER_API_CALL_NOT_ALLOWED = "BROKER_MOCK_ORDER_API_CALL_NOT_ALLOWED"
    BROKER_MOCK_ACCOUNT_API_CALL_NOT_ALLOWED = "BROKER_MOCK_ACCOUNT_API_CALL_NOT_ALLOWED"
    BROKER_MOCK_PROVIDER_API_CALL_NOT_ALLOWED = "BROKER_MOCK_PROVIDER_API_CALL_NOT_ALLOWED"
    BROKER_MOCK_CLOUD_LLM_NOT_ALLOWED = "BROKER_MOCK_CLOUD_LLM_NOT_ALLOWED"
    BROKER_MOCK_LOCAL_LLM_RUNTIME_NOT_ALLOWED = "BROKER_MOCK_LOCAL_LLM_RUNTIME_NOT_ALLOWED"
    BROKER_MOCK_PARQUET_NOT_ALLOWED = "BROKER_MOCK_PARQUET_NOT_ALLOWED"


class BrokerMockAdapterConfig(StrictModel):
    config_id: str = Field(..., min_length=1)
    strategy_track: StrategyTrack
    mock_adapter_family: str = Field(..., min_length=1)
    enabled: bool = False
    mock_only: bool = True
    paper_only: bool = True
    disabled_by_default: bool = True
    explicit_opt_in_required: bool = True
    non_executable_by_default: bool = True
    local_file_only: bool = True
    offline_only: bool = True
    no_real_order: bool = True
    no_real_account_mutation: bool = True
    no_live_trading: bool = True
    no_live_prod: bool = True
    no_production_broker: bool = True
    no_credentials_loaded: bool = True
    no_network_call: bool = True
    no_kiwoom_api_call: bool = True
    no_ls_api_call: bool = True
    no_broker_api_call: bool = True
    no_order_api_call: bool = True
    no_account_api_call: bool = True
    no_provider_api_call: bool = True
    no_cloud_llm: bool = True
    no_local_llm_runtime: bool = True

    @field_validator("config_id", "mock_adapter_family", mode="before")
    @classmethod
    def normalize_ids(cls, value, info):
        return _upper_required(value, info.field_name)

    @model_validator(mode="after")
    def validate_config(self):
        if self.strategy_track != StrategyTrack.DOMESTIC_KR:
            raise ValueError("broker mock adapter config requires StrategyTrack DOMESTIC_KR")
        if self.enabled:
            raise ValueError("broker mock adapter config must remain disabled by default in v6.2")
        return _validate_safety_flags(self, "broker mock adapter config")


class BrokerMockCapability(StrictModel):
    capability_id: str = Field(..., min_length=1)
    supported_markets: list[str] = Field(default_factory=list)
    supported_order_types: list[str] = Field(default_factory=list)
    supported_order_sides: list[BrokerMockOrderSide] = Field(default_factory=list)
    supports_mock_order_submission: bool = False
    supports_mock_cancellation: bool = False
    supports_mock_status_polling: bool = False
    supports_mock_account_snapshot: bool = False
    supports_mock_position_snapshot: bool = False
    supports_deterministic_replay_mode: bool = True
    supports_async_callback_simulation: bool = False
    mock_only: bool = True
    paper_only: bool = True
    disabled_by_default: bool = True
    explicit_opt_in_required: bool = True
    non_executable_by_default: bool = True
    local_file_only: bool = True
    offline_only: bool = True
    no_real_order: bool = True
    no_real_account_mutation: bool = True
    no_live_trading: bool = True
    no_live_prod: bool = True
    no_production_broker: bool = True
    no_credentials_loaded: bool = True
    no_network_call: bool = True
    no_kiwoom_api_call: bool = True
    no_ls_api_call: bool = True
    no_broker_api_call: bool = True
    no_order_api_call: bool = True
    no_account_api_call: bool = True
    no_provider_api_call: bool = True
    no_cloud_llm: bool = True
    no_local_llm_runtime: bool = True

    @field_validator("capability_id", mode="before")
    @classmethod
    def normalize_capability_id(cls, value):
        return _upper_required(value, "capability_id")

    @field_validator("supported_markets", "supported_order_types", mode="before")
    @classmethod
    def normalize_string_lists(cls, value):
        if value is None:
            return []
        if isinstance(value, (str, bytes)) or not isinstance(value, list):
            raise ValueError("supported values must be a list")
        return [_upper_required(item, "supported value") for item in value]

    @model_validator(mode="after")
    def validate_capability(self):
        return _validate_safety_flags(self, "broker mock capability")


class BrokerMockOrderIntent(StrictModel):
    mock_order_intent_id: str = Field(..., min_length=1)
    source_paper_order_intent_ref_id: str = Field(..., min_length=1)
    source_paper_decision_ref_id: str = Field(..., min_length=1)
    source_signal_candidate_ref_id: str = Field(..., min_length=1)
    symbol: str = Field(..., min_length=1)
    market: str = Field(..., min_length=1)
    strategy_track: StrategyTrack
    market_profile: str = Field(..., min_length=1)
    side: BrokerMockOrderSide
    mock_order_type: str = Field(..., min_length=1)
    requested_quantity: float = Field(..., gt=0)
    session_timestamp: datetime
    mock_adapter_target_id: str = Field(..., min_length=1)
    source_manifest_ids: list[str] = Field(default_factory=list)
    source_audit_record_ids: list[str] = Field(default_factory=list)
    provider_provenance_ids: list[str] = Field(default_factory=list)
    metadata: dict[str, object] = Field(default_factory=dict)
    mock_only: bool = True
    paper_only: bool = True
    disabled_by_default: bool = True
    explicit_opt_in_required: bool = True
    non_executable_by_default: bool = True
    local_file_only: bool = True
    offline_only: bool = True
    no_real_order: bool = True
    no_real_account_mutation: bool = True
    no_live_trading: bool = True
    no_live_prod: bool = True
    no_production_broker: bool = True
    no_credentials_loaded: bool = True
    no_network_call: bool = True
    no_kiwoom_api_call: bool = True
    no_ls_api_call: bool = True
    no_broker_api_call: bool = True
    no_order_api_call: bool = True
    no_account_api_call: bool = True
    no_provider_api_call: bool = True
    no_cloud_llm: bool = True
    no_local_llm_runtime: bool = True

    @field_validator(
        "mock_order_intent_id",
        "source_paper_order_intent_ref_id",
        "source_paper_decision_ref_id",
        "source_signal_candidate_ref_id",
        "symbol",
        "market",
        "market_profile",
        "mock_order_type",
        "mock_adapter_target_id",
        mode="before",
    )
    @classmethod
    def normalize_fields(cls, value, info):
        return _upper_required(value, info.field_name)

    @field_validator("session_timestamp", mode="after")
    @classmethod
    def validate_timestamp(cls, value):
        return aware(value)

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
        return BrokerMockOrderSide(candidate)

    @model_validator(mode="after")
    def validate_order_intent(self):
        if self.strategy_track != StrategyTrack.DOMESTIC_KR:
            raise ValueError("broker mock order intent requires StrategyTrack DOMESTIC_KR")
        return _validate_safety_flags(self, "broker mock order intent")


class BrokerMockOrderRequest(StrictModel):
    mock_order_request_id: str = Field(..., min_length=1)
    mock_order_intent_id: str = Field(..., min_length=1)
    request_created_at: datetime
    request_metadata: dict[str, object] = Field(default_factory=dict)
    mock_only: bool = True
    paper_only: bool = True
    disabled_by_default: bool = True
    explicit_opt_in_required: bool = True
    non_executable_by_default: bool = True
    local_file_only: bool = True
    offline_only: bool = True
    no_real_order: bool = True
    no_real_account_mutation: bool = True
    no_live_trading: bool = True
    no_live_prod: bool = True
    no_production_broker: bool = True
    no_credentials_loaded: bool = True
    no_network_call: bool = True
    no_kiwoom_api_call: bool = True
    no_ls_api_call: bool = True
    no_broker_api_call: bool = True
    no_order_api_call: bool = True
    no_account_api_call: bool = True
    no_provider_api_call: bool = True
    no_cloud_llm: bool = True
    no_local_llm_runtime: bool = True

    @field_validator("mock_order_request_id", "mock_order_intent_id", mode="before")
    @classmethod
    def normalize_ids(cls, value, info):
        return _upper_required(value, info.field_name)

    @field_validator("request_created_at", mode="after")
    @classmethod
    def validate_timestamp(cls, value):
        return aware(value)

    @field_validator("request_metadata", mode="before")
    @classmethod
    def validate_request_metadata(cls, value):
        return _validate_metadata(value, "request_metadata")

    @model_validator(mode="after")
    def validate_request(self):
        return _validate_safety_flags(self, "broker mock order request")


class BrokerMockOrderResponse(StrictModel):
    mock_order_response_id: str = Field(..., min_length=1)
    mock_order_request_id: str = Field(..., min_length=1)
    mock_status: str = Field(..., min_length=1)
    response_timestamp: datetime
    response_metadata: dict[str, object] = Field(default_factory=dict)
    mock_only: bool = True
    paper_only: bool = True
    disabled_by_default: bool = True
    explicit_opt_in_required: bool = True
    non_executable_by_default: bool = True
    local_file_only: bool = True
    offline_only: bool = True
    no_real_order: bool = True
    no_real_account_mutation: bool = True
    no_live_trading: bool = True
    no_live_prod: bool = True
    no_production_broker: bool = True
    no_credentials_loaded: bool = True
    no_network_call: bool = True
    no_kiwoom_api_call: bool = True
    no_ls_api_call: bool = True
    no_broker_api_call: bool = True
    no_order_api_call: bool = True
    no_account_api_call: bool = True
    no_provider_api_call: bool = True
    no_cloud_llm: bool = True
    no_local_llm_runtime: bool = True

    @field_validator("mock_order_response_id", "mock_order_request_id", "mock_status", mode="before")
    @classmethod
    def normalize_fields(cls, value, info):
        return _upper_required(value, info.field_name)

    @field_validator("response_timestamp", mode="after")
    @classmethod
    def validate_timestamp(cls, value):
        return aware(value)

    @field_validator("response_metadata", mode="before")
    @classmethod
    def validate_response_metadata(cls, value):
        return _validate_metadata(value, "response_metadata")

    @model_validator(mode="after")
    def validate_response(self):
        return _validate_safety_flags(self, "broker mock order response")


class BrokerMockExecutionReport(StrictModel):
    execution_report_id: str = Field(..., min_length=1)
    mock_order_intent_id: str = Field(..., min_length=1)
    mock_order_request_id: str = Field(..., min_length=1)
    mock_order_response_id: str = Field(..., min_length=1)
    symbol: str = Field(..., min_length=1)
    side: BrokerMockOrderSide
    mock_status: str = Field(..., min_length=1)
    mock_filled_quantity: float = Field(..., ge=0)
    mock_average_fill_price: float = Field(..., ge=0)
    mock_execution_timestamp: datetime
    execution_metadata: dict[str, object] = Field(default_factory=dict)
    mock_only: bool = True
    paper_only: bool = True
    disabled_by_default: bool = True
    explicit_opt_in_required: bool = True
    non_executable_by_default: bool = True
    local_file_only: bool = True
    offline_only: bool = True
    no_real_order: bool = True
    no_real_account_mutation: bool = True
    no_live_trading: bool = True
    no_live_prod: bool = True
    no_production_broker: bool = True
    no_credentials_loaded: bool = True
    no_network_call: bool = True
    no_kiwoom_api_call: bool = True
    no_ls_api_call: bool = True
    no_broker_api_call: bool = True
    no_order_api_call: bool = True
    no_account_api_call: bool = True
    no_provider_api_call: bool = True
    no_cloud_llm: bool = True
    no_local_llm_runtime: bool = True

    @field_validator(
        "execution_report_id",
        "mock_order_intent_id",
        "mock_order_request_id",
        "mock_order_response_id",
        "symbol",
        "mock_status",
        mode="before",
    )
    @classmethod
    def normalize_fields(cls, value, info):
        return _upper_required(value, info.field_name)

    @field_validator("mock_execution_timestamp", mode="after")
    @classmethod
    def validate_timestamp(cls, value):
        return aware(value)

    @field_validator("execution_metadata", mode="before")
    @classmethod
    def validate_execution_metadata(cls, value):
        return _validate_metadata(value, "execution_metadata")

    @model_validator(mode="after")
    def validate_execution_report(self):
        return _validate_safety_flags(self, "broker mock execution report")


class BrokerMockPositionSnapshot(StrictModel):
    position_snapshot_id: str = Field(..., min_length=1)
    symbol: str = Field(..., min_length=1)
    market: str = Field(..., min_length=1)
    quantity: float = Field(..., ge=0)
    average_price: float = Field(..., ge=0)
    mark_price: float = Field(..., ge=0)
    exposure_value: float = Field(..., ge=0)
    metadata: dict[str, object] = Field(default_factory=dict)
    mock_only: bool = True
    paper_only: bool = True
    disabled_by_default: bool = True
    explicit_opt_in_required: bool = True
    non_executable_by_default: bool = True
    local_file_only: bool = True
    offline_only: bool = True
    no_real_order: bool = True
    no_real_account_mutation: bool = True
    no_live_trading: bool = True
    no_live_prod: bool = True
    no_production_broker: bool = True
    no_credentials_loaded: bool = True
    no_network_call: bool = True
    no_kiwoom_api_call: bool = True
    no_ls_api_call: bool = True
    no_broker_api_call: bool = True
    no_order_api_call: bool = True
    no_account_api_call: bool = True
    no_provider_api_call: bool = True
    no_cloud_llm: bool = True
    no_local_llm_runtime: bool = True

    @field_validator("position_snapshot_id", "symbol", "market", mode="before")
    @classmethod
    def normalize_fields(cls, value, info):
        return _upper_required(value, info.field_name)

    @field_validator("metadata", mode="before")
    @classmethod
    def validate_position_metadata(cls, value):
        return _validate_metadata(value, "metadata")

    @model_validator(mode="after")
    def validate_position(self):
        return _validate_safety_flags(self, "broker mock position snapshot")


class BrokerMockAccountSnapshot(StrictModel):
    account_snapshot_id: str = Field(..., min_length=1)
    mock_adapter_id: str = Field(..., min_length=1)
    snapshot_timestamp: datetime
    base_currency: str = Field(..., min_length=1)
    reported_mock_cash: float = Field(..., ge=0)
    reported_mock_buying_power: float = Field(..., ge=0)
    reported_mock_equity: float = Field(..., ge=0)
    position_snapshots: list[BrokerMockPositionSnapshot] = Field(default_factory=list)
    metadata: dict[str, object] = Field(default_factory=dict)
    mock_only: bool = True
    paper_only: bool = True
    disabled_by_default: bool = True
    explicit_opt_in_required: bool = True
    non_executable_by_default: bool = True
    local_file_only: bool = True
    offline_only: bool = True
    no_real_order: bool = True
    no_real_account_mutation: bool = True
    no_live_trading: bool = True
    no_live_prod: bool = True
    no_production_broker: bool = True
    no_credentials_loaded: bool = True
    no_network_call: bool = True
    no_kiwoom_api_call: bool = True
    no_ls_api_call: bool = True
    no_broker_api_call: bool = True
    no_order_api_call: bool = True
    no_account_api_call: bool = True
    no_provider_api_call: bool = True
    no_cloud_llm: bool = True
    no_local_llm_runtime: bool = True

    @field_validator("account_snapshot_id", "mock_adapter_id", "base_currency", mode="before")
    @classmethod
    def normalize_fields(cls, value, info):
        return _upper_required(value, info.field_name)

    @field_validator("snapshot_timestamp", mode="after")
    @classmethod
    def validate_timestamp(cls, value):
        return aware(value)

    @field_validator("metadata", mode="before")
    @classmethod
    def validate_account_metadata(cls, value):
        return _validate_metadata(value, "metadata")

    @model_validator(mode="after")
    def validate_account_snapshot(self):
        return _validate_safety_flags(self, "broker mock account snapshot")


class KiwoomMockAdapterBoundary(StrictModel):
    boundary_id: str = Field(..., min_length=1)
    future_only: bool = True
    implementation_present: bool = False
    executable_transport_present: bool = False
    metadata: dict[str, object] = Field(default_factory=dict)
    mock_only: bool = True
    paper_only: bool = True
    disabled_by_default: bool = True
    explicit_opt_in_required: bool = True
    non_executable_by_default: bool = True
    local_file_only: bool = True
    offline_only: bool = True
    no_real_order: bool = True
    no_real_account_mutation: bool = True
    no_live_trading: bool = True
    no_live_prod: bool = True
    no_production_broker: bool = True
    no_credentials_loaded: bool = True
    no_network_call: bool = True
    no_kiwoom_api_call: bool = True
    no_ls_api_call: bool = True
    no_broker_api_call: bool = True
    no_order_api_call: bool = True
    no_account_api_call: bool = True
    no_provider_api_call: bool = True
    no_cloud_llm: bool = True
    no_local_llm_runtime: bool = True

    @field_validator("boundary_id", mode="before")
    @classmethod
    def normalize_boundary_id(cls, value):
        return _upper_required(value, "boundary_id")

    @field_validator("metadata", mode="before")
    @classmethod
    def validate_boundary_metadata(cls, value):
        return _validate_metadata(value, "metadata")

    @model_validator(mode="after")
    def validate_boundary(self):
        if not self.future_only or self.implementation_present or self.executable_transport_present:
            raise ValueError("Kiwoom mock adapter boundary must remain future-only and non-executable")
        return _validate_safety_flags(self, "Kiwoom mock adapter boundary")


class LSMockAdapterBoundary(StrictModel):
    boundary_id: str = Field(..., min_length=1)
    future_only: bool = True
    implementation_present: bool = False
    executable_transport_present: bool = False
    metadata: dict[str, object] = Field(default_factory=dict)
    mock_only: bool = True
    paper_only: bool = True
    disabled_by_default: bool = True
    explicit_opt_in_required: bool = True
    non_executable_by_default: bool = True
    local_file_only: bool = True
    offline_only: bool = True
    no_real_order: bool = True
    no_real_account_mutation: bool = True
    no_live_trading: bool = True
    no_live_prod: bool = True
    no_production_broker: bool = True
    no_credentials_loaded: bool = True
    no_network_call: bool = True
    no_kiwoom_api_call: bool = True
    no_ls_api_call: bool = True
    no_broker_api_call: bool = True
    no_order_api_call: bool = True
    no_account_api_call: bool = True
    no_provider_api_call: bool = True
    no_cloud_llm: bool = True
    no_local_llm_runtime: bool = True

    @field_validator("boundary_id", mode="before")
    @classmethod
    def normalize_boundary_id(cls, value):
        return _upper_required(value, "boundary_id")

    @field_validator("metadata", mode="before")
    @classmethod
    def validate_boundary_metadata(cls, value):
        return _validate_metadata(value, "metadata")

    @model_validator(mode="after")
    def validate_boundary(self):
        if not self.future_only or self.implementation_present or self.executable_transport_present:
            raise ValueError("LS mock adapter boundary must remain future-only and non-executable")
        return _validate_safety_flags(self, "LS mock adapter boundary")


class BrokerMockAdapterSafetyReport(StrictModel):
    safety_report_id: str = Field(..., min_length=1)
    blocked: bool = False
    findings: list[str] = Field(default_factory=list)
    mock_only: bool = True
    paper_only: bool = True
    disabled_by_default: bool = True
    explicit_opt_in_required: bool = True
    non_executable_by_default: bool = True
    local_file_only: bool = True
    offline_only: bool = True
    no_real_order: bool = True
    no_real_account_mutation: bool = True
    no_live_trading: bool = True
    no_live_prod: bool = True
    no_production_broker: bool = True
    no_credentials_loaded: bool = True
    no_network_call: bool = True
    no_kiwoom_api_call: bool = True
    no_ls_api_call: bool = True
    no_broker_api_call: bool = True
    no_order_api_call: bool = True
    no_account_api_call: bool = True
    no_provider_api_call: bool = True
    no_cloud_llm: bool = True
    no_local_llm_runtime: bool = True

    @field_validator("safety_report_id", mode="before")
    @classmethod
    def normalize_safety_report_id(cls, value):
        return _upper_required(value, "safety_report_id")

    @model_validator(mode="after")
    def validate_safety_report(self):
        return _validate_safety_flags(self, "broker mock adapter safety report")


class BrokerMockAdapterGapReport(StrictModel):
    gap_report_id: str = Field(..., min_length=1)
    adapter_input_id: str = Field(..., min_length=1)
    gap_status: str = Field(..., min_length=1)
    gap_categories: list[BrokerMockGapCategory] = Field(default_factory=list)
    blocking_gap_count: int = Field(default=0, ge=0)
    report_only_gap_count: int = Field(default=0, ge=0)
    gaps: list[str] = Field(default_factory=list)
    source_manifest_ids: list[str] = Field(default_factory=list)
    source_audit_record_ids: list[str] = Field(default_factory=list)
    provider_provenance_ids: list[str] = Field(default_factory=list)
    mock_only: bool = True
    paper_only: bool = True
    disabled_by_default: bool = True
    explicit_opt_in_required: bool = True
    non_executable_by_default: bool = True
    local_file_only: bool = True
    offline_only: bool = True
    no_real_order: bool = True
    no_real_account_mutation: bool = True
    no_live_trading: bool = True
    no_live_prod: bool = True
    no_production_broker: bool = True
    no_credentials_loaded: bool = True
    no_network_call: bool = True
    no_kiwoom_api_call: bool = True
    no_ls_api_call: bool = True
    no_broker_api_call: bool = True
    no_order_api_call: bool = True
    no_account_api_call: bool = True
    no_provider_api_call: bool = True
    no_cloud_llm: bool = True
    no_local_llm_runtime: bool = True

    @field_validator("gap_report_id", "adapter_input_id", "gap_status", mode="before")
    @classmethod
    def normalize_fields(cls, value, info):
        return _upper_required(value, info.field_name)

    @field_validator("source_manifest_ids", "source_audit_record_ids", "provider_provenance_ids", mode="before")
    @classmethod
    def normalize_id_lists(cls, value, info):
        return _normalize_id_list(value, info.field_name)

    @model_validator(mode="after")
    def validate_gap_report(self):
        return _validate_safety_flags(self, "broker mock adapter gap report")


class BrokerMockAdapterAuditRecord(StrictModel):
    audit_record_id: str = Field(..., min_length=1)
    adapter_input_id: str = Field(..., min_length=1)
    created_at: datetime
    operator_context: str = Field(..., min_length=1)
    source_path: str = Field(..., min_length=1)
    source_manifest_ids: list[str] = Field(default_factory=list)
    source_audit_record_ids: list[str] = Field(default_factory=list)
    provider_provenance_ids: list[str] = Field(default_factory=list)
    mock_only: bool = True
    paper_only: bool = True
    disabled_by_default: bool = True
    explicit_opt_in_required: bool = True
    non_executable_by_default: bool = True
    local_file_only: bool = True
    offline_only: bool = True
    no_real_order: bool = True
    no_real_account_mutation: bool = True
    no_live_trading: bool = True
    no_live_prod: bool = True
    no_production_broker: bool = True
    no_credentials_loaded: bool = True
    no_network_call: bool = True
    no_kiwoom_api_call: bool = True
    no_ls_api_call: bool = True
    no_broker_api_call: bool = True
    no_order_api_call: bool = True
    no_account_api_call: bool = True
    no_provider_api_call: bool = True
    no_cloud_llm: bool = True
    no_local_llm_runtime: bool = True

    @field_validator("audit_record_id", "adapter_input_id", "operator_context", mode="before")
    @classmethod
    def normalize_ids(cls, value, info):
        return _upper_required(value, info.field_name)

    @field_validator("source_path", mode="before")
    @classmethod
    def validate_source_path(cls, value):
        return _validate_local_path(value, "source_path")

    @field_validator("created_at", mode="after")
    @classmethod
    def validate_created_at(cls, value):
        return aware(value)

    @field_validator("source_manifest_ids", "source_audit_record_ids", "provider_provenance_ids", mode="before")
    @classmethod
    def normalize_lists(cls, value, info):
        return _normalize_id_list(value, info.field_name)

    @model_validator(mode="after")
    def validate_audit_record(self):
        return _validate_safety_flags(self, "broker mock adapter audit record")


class BrokerMockAdapterInput(StrictModel):
    schema_version: str = Field(..., min_length=1)
    adapter_input_id: str = Field(..., min_length=1)
    adapter_config: BrokerMockAdapterConfig
    capability: BrokerMockCapability
    broker_mock_order_intent: BrokerMockOrderIntent
    broker_mock_order_request: BrokerMockOrderRequest
    broker_mock_order_response: BrokerMockOrderResponse
    broker_mock_execution_report: BrokerMockExecutionReport
    broker_mock_account_snapshot: BrokerMockAccountSnapshot
    kiwoom_mock_adapter_boundary: KiwoomMockAdapterBoundary
    ls_mock_adapter_boundary: LSMockAdapterBoundary
    safety_report: BrokerMockAdapterSafetyReport
    gap_report: BrokerMockAdapterGapReport
    audit_records: list[BrokerMockAdapterAuditRecord] = Field(default_factory=list)

    @field_validator("schema_version", "adapter_input_id", mode="before")
    @classmethod
    def normalize_header_fields(cls, value, info):
        return _upper_required(value, info.field_name)

    @model_validator(mode="after")
    def validate_input(self):
        if not self.broker_mock_order_intent.source_paper_order_intent_ref_id:
            raise ValueError("broker mock adapter input requires source paper order intent ref")
        return self

