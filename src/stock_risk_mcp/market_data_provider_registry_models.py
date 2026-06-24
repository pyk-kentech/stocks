from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from pydantic import Field, field_validator, model_validator

from stock_risk_mcp.models import StrictModel


def _aware(value: datetime | str) -> datetime:
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


def _validate_local_path(value: str, field_name: str) -> str:
    cleaned = _string_required(value, field_name)
    lowered = cleaned.lower()
    if "://" in lowered or lowered.startswith("//"):
        raise ValueError(f"{field_name} must be a local file path")
    if lowered.endswith(".parquet"):
        raise ValueError("parquet remains unsupported")
    return cleaned


def _normalize_list(value, field_name: str, *, upper: bool = True) -> list[str]:
    if value is None:
        return []
    if isinstance(value, (str, bytes)) or not isinstance(value, list):
        raise ValueError(f"{field_name} must be a list")
    if upper:
        return [_upper_required(item, field_name) for item in value]
    return [_string_required(item, field_name) for item in value]


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
        "no_websocket",
        "no_cloud_llm",
        "no_local_llm_runtime",
    ):
        if not getattr(model, flag_name):
            raise ValueError(f"{context} must remain {flag_name}")
    return model


class ProviderCandidateName(StrEnum):
    DATABENTO = "DATABENTO"
    IBKR = "IBKR"
    CME_DATAMINE = "CME_DATAMINE"
    CME_REALTIME_API = "CME_REALTIME_API"
    YAHOO_DELAYED = "YAHOO_DELAYED"
    CME_DELAYED_WEB = "CME_DELAYED_WEB"
    FRED = "FRED"
    INVESTING_CALENDAR = "INVESTING_CALENDAR"
    BLS = "BLS"
    BEA = "BEA"
    FED = "FED"
    ECOS_BOK = "ECOS_BOK"
    KRX = "KRX"
    NAVER_FINANCE = "NAVER_FINANCE"
    KIWOOM_READONLY = "KIWOOM_READONLY"
    CNN_FEAR_GREED = "CNN_FEAR_GREED"
    MANUAL_CSV = "MANUAL_CSV"
    LOCAL_FIXTURE = "LOCAL_FIXTURE"
    UNKNOWN = "UNKNOWN"


class DataClass(StrEnum):
    EQUITY_PRICE_OHLCV = "EQUITY_PRICE_OHLCV"
    FUTURES = "FUTURES"
    VOLATILITY_INDEX = "VOLATILITY_INDEX"
    FX = "FX"
    RATES_YIELDS = "RATES_YIELDS"
    ECONOMIC_CALENDAR = "ECONOMIC_CALENDAR"
    EARNINGS_CALENDAR = "EARNINGS_CALENDAR"
    BREADTH_MARKET_INTERNALS = "BREADTH_MARKET_INTERNALS"
    VOLUME_RELATIVE_VOLUME = "VOLUME_RELATIVE_VOLUME"
    FLOW_FOREIGN_INSTITUTIONAL_SHORT = "FLOW_FOREIGN_INSTITUTIONAL_SHORT"
    SENTIMENT_FEAR_INDEX = "SENTIMENT_FEAR_INDEX"
    FEE_TAX_SLIPPAGE = "FEE_TAX_SLIPPAGE"
    CORPORATE_ACTIONS = "CORPORATE_ACTIONS"
    BENCHMARK_INDEX_CONSTITUENTS = "BENCHMARK_INDEX_CONSTITUENTS"


class ModuleName(StrEnum):
    MARKET_REGIME_ENGINE = "MARKET_REGIME_ENGINE"
    REGIME_ALLOCATION_LEARNING_DATASET = "REGIME_ALLOCATION_LEARNING_DATASET"
    ALLOCATION_POLICY_TRAINING = "ALLOCATION_POLICY_TRAINING"
    RISK_ADJUSTED_PAPER_EVALUATION = "RISK_ADJUSTED_PAPER_EVALUATION"
    POSITION_SIZING_ENGINE = "POSITION_SIZING_ENGINE"
    EVENT_RISK_GATE = "EVENT_RISK_GATE"
    BREADTH_ENGINE = "BREADTH_ENGINE"
    FLOW_SENTIMENT_ENGINE = "FLOW_SENTIMENT_ENGINE"
    CONTROLLED_MOCK_READINESS = "CONTROLLED_MOCK_READINESS"
    CONTROLLED_MOCK_DRY_RUN_LATER = "CONTROLLED_MOCK_DRY_RUN_LATER"


class ProviderReadinessLevel(StrEnum):
    FIXTURE_ONLY = "FIXTURE_ONLY"
    SANITY_CHECK_ONLY = "SANITY_CHECK_ONLY"
    RESEARCH_READY = "RESEARCH_READY"
    BACKTEST_READY = "BACKTEST_READY"
    TRAINING_READY = "TRAINING_READY"
    PAPER_READY = "PAPER_READY"
    LIVE_READ_ONLY_READY = "LIVE_READ_ONLY_READY"
    GAP = "GAP"
    REJECTED = "REJECTED"


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
    no_websocket: bool = True
    no_cloud_llm: bool = True
    no_local_llm_runtime: bool = True


class ProviderCandidate(StrictModel):
    provider_name: ProviderCandidateName
    provider_type: str = Field(..., min_length=1)
    access_mode: str = Field(..., min_length=1)
    official: bool = False
    unofficial: bool = False
    internal: bool = False
    delayed: bool = False
    historical_support: bool = False
    live_support: bool = False
    delayed_support: bool = False
    read_only_support: bool = False
    api_key_required: bool = False
    subscription_required: bool = False
    license_terms_note_ref: str = Field(..., min_length=1)
    latency_class: str = Field(..., min_length=1)
    expected_freshness: str = Field(..., min_length=1)
    allowed_use_cases: list[str] = Field(default_factory=list)
    disallowed_use_cases: list[str] = Field(default_factory=list)
    implementation_status: str = Field(..., min_length=1)
    risk_note: str = Field(..., min_length=1)
    readiness_level: ProviderReadinessLevel
    subscription_evidence_ref: str | None = None
    api_key_evidence_ref: str | None = None

    @field_validator(
        "provider_type",
        "access_mode",
        "latency_class",
        "expected_freshness",
        "implementation_status",
        mode="before",
    )
    @classmethod
    def normalize_upper(cls, value):
        return _upper_required(value, "field")

    @field_validator("risk_note", mode="before")
    @classmethod
    def normalize_note(cls, value):
        return _string_required(value, "risk_note")

    @field_validator("license_terms_note_ref", "subscription_evidence_ref", "api_key_evidence_ref", mode="before")
    @classmethod
    def normalize_refs(cls, value, info):
        if value is None:
            return None
        return _validate_local_path(value, info.field_name)

    @field_validator("allowed_use_cases", "disallowed_use_cases", mode="before")
    @classmethod
    def normalize_use_cases(cls, value, info):
        return _normalize_list(value, info.field_name)


class ModuleDataRequirement(StrictModel):
    module_name: ModuleName
    required_data_classes: list[DataClass] = Field(default_factory=list)
    optional_data_classes: list[DataClass] = Field(default_factory=list)
    minimum_readiness_level: ProviderReadinessLevel
    freshness_requirement: str = Field(..., min_length=1)
    available_at_required: bool = False
    source_ref_required: bool = False
    historical_depth_requirement: str = Field(..., min_length=1)
    training_grade_required: bool = False
    live_read_only_required: bool = False
    fallback_policy: str = Field(..., min_length=1)

    @field_validator("freshness_requirement", "historical_depth_requirement", "fallback_policy", mode="before")
    @classmethod
    def normalize_upper(cls, value):
        return _upper_required(value, "field")


class CanonicalDataContractRecord(StrictModel):
    instrument_key: str = Field(..., min_length=1)
    provider_symbol: str = Field(..., min_length=1)
    data_class: DataClass
    observed_at: datetime
    available_at: datetime | None = None
    value: float | None = None
    open: float | None = None
    high: float | None = None
    low: float | None = None
    close: float | None = None
    volume: float | None = None
    percent_change: float | None = None
    currency: str = Field(..., min_length=1)
    market: str = Field(..., min_length=1)
    timezone: str = Field(..., min_length=1)
    data_delay_seconds: int = Field(default=0, ge=0)
    source_provider: ProviderCandidateName
    source_ref: str = Field(..., min_length=1)
    quality_flags: list[str] = Field(default_factory=list)
    stale: bool = False
    gap_reason: str | None = None
    corporate_action_adjusted: bool = False
    survivorship_safe: bool = False

    @field_validator("instrument_key", "provider_symbol", "currency", "market", "timezone", "gap_reason", mode="before")
    @classmethod
    def normalize_strings(cls, value, info):
        if value is None and info.field_name == "gap_reason":
            return None
        if info.field_name == "provider_symbol":
            return _string_required(value, info.field_name)
        return _upper_required(value, info.field_name)

    @field_validator("observed_at", "available_at", mode="before")
    @classmethod
    def normalize_dt(cls, value):
        if value is None:
            return None
        return _aware(value)

    @field_validator("source_ref", mode="before")
    @classmethod
    def normalize_source_ref(cls, value):
        return _validate_local_path(value, "source_ref")

    @field_validator("quality_flags", mode="before")
    @classmethod
    def normalize_flags(cls, value):
        return _normalize_list(value, "quality_flags")


class SymbolMappingRecord(StrictModel):
    mapping_id: str = Field(..., min_length=1)
    canonical_key: str = Field(..., min_length=1)
    provider_symbol: str = Field(..., min_length=1)
    provider_name: ProviderCandidateName
    data_class: DataClass

    @field_validator("mapping_id", "canonical_key", mode="before")
    @classmethod
    def normalize_upper(cls, value):
        return _upper_required(value, "field")

    @field_validator("provider_symbol", mode="before")
    @classmethod
    def normalize_symbol(cls, value):
        return _string_required(value, "provider_symbol")


class ProviderRegistryGapEntry(StrictModel):
    gap_id: str = Field(..., min_length=1)
    gap_category: str = Field(..., min_length=1)
    severity: str = Field(default="REPORT_ONLY", min_length=1)
    message: str = Field(..., min_length=1)

    @field_validator("gap_id", "gap_category", "severity", mode="before")
    @classmethod
    def normalize_upper(cls, value):
        return _upper_required(value, "field")

    @field_validator("message", mode="before")
    @classmethod
    def normalize_message(cls, value):
        return _string_required(value, "message")


class GlobalProviderRegistryReport(_BaseReport):
    report_id: str = Field(..., min_length=1)
    providers: list[ProviderCandidate] = Field(default_factory=list)

    @field_validator("report_id", mode="before")
    @classmethod
    def normalize_id(cls, value):
        return _upper_required(value, "report_id")

    @model_validator(mode="after")
    def validate_model(self):
        return _validate_safety_flags(self, "global provider registry report")


class ModuleDataRequirementReport(_BaseReport):
    report_id: str = Field(..., min_length=1)
    requirements: list[ModuleDataRequirement] = Field(default_factory=list)

    @field_validator("report_id", mode="before")
    @classmethod
    def normalize_id(cls, value):
        return _upper_required(value, "report_id")

    @model_validator(mode="after")
    def validate_model(self):
        return _validate_safety_flags(self, "module data requirement report")


class ProviderReadinessMatrixReport(_BaseReport):
    report_id: str = Field(..., min_length=1)
    readiness_by_provider: dict[str, str] = Field(default_factory=dict)

    @field_validator("report_id", mode="before")
    @classmethod
    def normalize_id(cls, value):
        return _upper_required(value, "report_id")

    @field_validator("readiness_by_provider", mode="before")
    @classmethod
    def normalize_map(cls, value):
        normalized = {}
        for key, item in dict(value).items():
            normalized[_upper_required(key, "provider_name")] = _upper_required(item, "readiness_level")
        return normalized

    @model_validator(mode="after")
    def validate_model(self):
        return _validate_safety_flags(self, "provider readiness matrix report")


class CanonicalDataContractReport(_BaseReport):
    report_id: str = Field(..., min_length=1)
    contracts: list[CanonicalDataContractRecord] = Field(default_factory=list)

    @field_validator("report_id", mode="before")
    @classmethod
    def normalize_id(cls, value):
        return _upper_required(value, "report_id")

    @model_validator(mode="after")
    def validate_model(self):
        return _validate_safety_flags(self, "canonical data contract report")


class SymbolMappingReport(_BaseReport):
    report_id: str = Field(..., min_length=1)
    mappings: list[SymbolMappingRecord] = Field(default_factory=list)

    @field_validator("report_id", mode="before")
    @classmethod
    def normalize_id(cls, value):
        return _upper_required(value, "report_id")

    @model_validator(mode="after")
    def validate_model(self):
        return _validate_safety_flags(self, "symbol mapping report")


class ProviderSelectionDecision(StrEnum):
    RESEARCH_READY = "RESEARCH_READY"
    BACKTEST_READY = "BACKTEST_READY"
    TRAINING_READY = "TRAINING_READY"
    PAPER_READY = "PAPER_READY"
    GAP = "GAP"
    REJECTED = "REJECTED"


class ProviderSelectionReport(_BaseReport):
    report_id: str = Field(..., min_length=1)
    selection_decision: ProviderSelectionDecision
    preferred_provider_by_data_class: dict[str, str] = Field(default_factory=dict)
    fallback_provider_by_data_class: dict[str, str] = Field(default_factory=dict)
    rejected_providers: list[str] = Field(default_factory=list)
    missing_evidence: list[str] = Field(default_factory=list)
    subscription_cost_gaps: list[str] = Field(default_factory=list)
    license_terms_gaps: list[str] = Field(default_factory=list)
    latency_gaps: list[str] = Field(default_factory=list)
    coverage_gaps: list[str] = Field(default_factory=list)
    symbol_mapping_gaps: list[str] = Field(default_factory=list)

    @field_validator("report_id", mode="before")
    @classmethod
    def normalize_id(cls, value):
        return _upper_required(value, "report_id")

    @field_validator(
        "rejected_providers",
        "missing_evidence",
        "subscription_cost_gaps",
        "license_terms_gaps",
        "latency_gaps",
        "coverage_gaps",
        "symbol_mapping_gaps",
        mode="before",
    )
    @classmethod
    def normalize_lists(cls, value, info):
        return _normalize_list(value, info.field_name)

    @field_validator("preferred_provider_by_data_class", "fallback_provider_by_data_class", mode="before")
    @classmethod
    def normalize_maps(cls, value):
        normalized = {}
        for key, item in dict(value).items():
            normalized[_upper_required(key, "data_class")] = _upper_required(item, "provider_name")
        return normalized

    @model_validator(mode="after")
    def validate_model(self):
        return _validate_safety_flags(self, "provider selection report")


class MarketDataProviderGapReport(_BaseReport):
    gap_report_id: str = Field(..., min_length=1)
    selection_decision: ProviderSelectionDecision
    gap_entries: list[ProviderRegistryGapEntry] = Field(default_factory=list)

    @field_validator("gap_report_id", mode="before")
    @classmethod
    def normalize_id(cls, value):
        return _upper_required(value, "gap_report_id")

    @model_validator(mode="after")
    def validate_model(self):
        return _validate_safety_flags(self, "market data provider gap report")


class MarketDataProviderAuditRecord(_BaseReport):
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
    def normalize_created_at(cls, value):
        return _aware(value)

    @field_validator("source_path", mode="before")
    @classmethod
    def normalize_source_path(cls, value):
        return _validate_local_path(value, "source_path")

    @field_validator("operator_context", mode="before")
    @classmethod
    def normalize_context(cls, value):
        return _string_required(value, "operator_context")

    @model_validator(mode="after")
    def validate_model(self):
        if not self.redaction_applied:
            raise ValueError("audit record must remain redacted")
        if self.contains_secret_material or self.contains_token_material or self.contains_account_material:
            raise ValueError("audit record must remain secret-free")
        return _validate_safety_flags(self, "market data provider audit record")


class MarketDataProviderRegistryInput(_BaseReport):
    registry_id: str = Field(..., min_length=1)
    provider_candidates: list[ProviderCandidate] = Field(default_factory=list)
    module_requirements: list[ModuleDataRequirement] = Field(default_factory=list)
    canonical_contracts: list[CanonicalDataContractRecord] = Field(default_factory=list)
    symbol_mappings: list[SymbolMappingRecord] = Field(default_factory=list)
    audit_records: list[MarketDataProviderAuditRecord] = Field(default_factory=list)
    global_provider_registry_report: GlobalProviderRegistryReport | None = None
    module_data_requirement_report: ModuleDataRequirementReport | None = None
    provider_readiness_matrix_report: ProviderReadinessMatrixReport | None = None
    canonical_data_contract_report: CanonicalDataContractReport | None = None
    symbol_mapping_report: SymbolMappingReport | None = None
    provider_selection_report: ProviderSelectionReport | None = None
    gap_report: MarketDataProviderGapReport | None = None

    @field_validator("registry_id", mode="before")
    @classmethod
    def normalize_id(cls, value):
        return _upper_required(value, "registry_id")

    @model_validator(mode="after")
    def validate_model(self):
        if not self.audit_records:
            raise ValueError("audit_records must not be empty")
        return _validate_safety_flags(self, "market data provider registry input")
