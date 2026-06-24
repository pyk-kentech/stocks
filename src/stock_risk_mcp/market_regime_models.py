from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from pydantic import Field, field_validator, model_validator

from stock_risk_mcp.models import StrictModel


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


class MarketRiskAppetite(StrEnum):
    RISK_ON = "RISK_ON"
    RISK_OFF = "RISK_OFF"
    MIXED = "MIXED"
    UNKNOWN = "UNKNOWN"


class MarketDirection(StrEnum):
    BULL = "BULL"
    BEAR = "BEAR"
    SIDEWAYS = "SIDEWAYS"
    TRANSITION = "TRANSITION"
    UNKNOWN = "UNKNOWN"


class MarketVolatilityState(StrEnum):
    HIGH_VOL = "HIGH_VOL"
    NORMAL_VOL = "NORMAL_VOL"
    LOW_VOL = "LOW_VOL"
    VOL_EXPANSION = "VOL_EXPANSION"
    UNKNOWN = "UNKNOWN"


class MarketStressState(StrEnum):
    NORMAL = "NORMAL"
    FX_STRESS = "FX_STRESS"
    RATE_STRESS = "RATE_STRESS"
    DOLLAR_STRESS = "DOLLAR_STRESS"
    CROSS_ASSET_STRESS = "CROSS_ASSET_STRESS"
    UNKNOWN = "UNKNOWN"


class MarketRegimeDecision(StrEnum):
    BLOCKED = "BLOCKED"
    RESEARCH_ONLY = "RESEARCH_ONLY"
    REGIME_READY = "REGIME_READY"
    TRAINING_FEATURE_READY = "TRAINING_FEATURE_READY"
    GAP = "GAP"
    REJECTED = "REJECTED"


class MarketRegimeGapCategory(StrEnum):
    REPORT_GENERATED = "REPORT_GENERATED"
    MISSING_AVAILABLE_AT = "MISSING_AVAILABLE_AT"
    FUTURE_FEATURE_LEAKAGE = "FUTURE_FEATURE_LEAKAGE"
    STALE_CRITICAL_DATA = "STALE_CRITICAL_DATA"
    MISSING_SOURCE_REF = "MISSING_SOURCE_REF"
    OPTIONAL_CNN_FEATURE_MISSING = "OPTIONAL_CNN_FEATURE_MISSING"
    CONFLICTING_EVIDENCE = "CONFLICTING_EVIDENCE"
    REMOTE_SOURCE_NOT_ALLOWED = "REMOTE_SOURCE_NOT_ALLOWED"
    PARQUET_NOT_ALLOWED = "PARQUET_NOT_ALLOWED"
    INVALID_SNAPSHOT = "INVALID_SNAPSHOT"


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


class AssetSnapshot(StrictModel):
    symbol: str = Field(..., min_length=1)
    last_value: float = Field(..., gt=0)
    pct_change_1d: float
    source_ref: str = Field(..., min_length=1)

    @field_validator("symbol", mode="before")
    @classmethod
    def normalize_symbol(cls, value):
        return _upper_required(value, "symbol")

    @field_validator("source_ref", mode="before")
    @classmethod
    def normalize_source_ref(cls, value):
        return _validate_local_path(value, "source_ref")


class DataFreshnessPolicy(StrictModel):
    max_age_minutes: int = Field(..., ge=1)
    critical_inputs: list[str] = Field(default_factory=list)

    @field_validator("critical_inputs", mode="before")
    @classmethod
    def normalize_inputs(cls, value):
        if value is None:
            return []
        if isinstance(value, (str, bytes)) or not isinstance(value, list):
            raise ValueError("critical_inputs must be a list")
        return [_upper_required(item, "critical_inputs") for item in value]


class MarketRegimeInputSnapshot(StrictModel):
    snapshot_id: str = Field(..., min_length=1)
    anchor_at: datetime
    observed_at: datetime
    available_at: datetime | None = None
    nq: AssetSnapshot
    es: AssetSnapshot
    vix: AssetSnapshot
    dxy: AssetSnapshot
    us10y: AssetSnapshot
    usdkrw: AssetSnapshot
    cnn_fear_greed_feature_ref: str | None = None
    data_freshness_policy: DataFreshnessPolicy

    @field_validator("snapshot_id", mode="before")
    @classmethod
    def normalize_id(cls, value):
        return _upper_required(value, "snapshot_id")

    @field_validator("anchor_at", "observed_at", "available_at", mode="before")
    @classmethod
    def normalize_dt(cls, value):
        return _aware(value)

    @field_validator("cnn_fear_greed_feature_ref", mode="before")
    @classmethod
    def normalize_optional_ref(cls, value):
        if value is None:
            return None
        return _validate_local_path(value, "cnn_fear_greed_feature_ref")


class MarketRegimeGapEntry(StrictModel):
    gap_id: str = Field(..., min_length=1)
    gap_category: MarketRegimeGapCategory
    severity: str = Field(default="REPORT_ONLY", min_length=1)
    message: str = Field(..., min_length=1)

    @field_validator("gap_id", "severity", mode="before")
    @classmethod
    def normalize_upper(cls, value):
        return _upper_required(value, "gap")

    @field_validator("message", mode="before")
    @classmethod
    def normalize_message(cls, value):
        return _string_required(value, "message")


class MarketRegimeSummaryReport(_BaseReport):
    report_id: str = Field(..., min_length=1)
    decision: MarketRegimeDecision
    final_regime_label: str = Field(..., min_length=1)
    risk_appetite: MarketRiskAppetite
    market_direction: MarketDirection
    volatility_state: MarketVolatilityState
    stress_state: MarketStressState
    confidence_bucket: str = Field(..., min_length=1)
    supporting_evidence: list[str] = Field(default_factory=list)
    conflicting_evidence: list[str] = Field(default_factory=list)
    missing_evidence: list[str] = Field(default_factory=list)
    stale_evidence: list[str] = Field(default_factory=list)

    @field_validator("report_id", "final_regime_label", "confidence_bucket", mode="before")
    @classmethod
    def normalize_upper(cls, value):
        return _upper_required(value, "field")

    @field_validator("supporting_evidence", "conflicting_evidence", "missing_evidence", "stale_evidence", mode="before")
    @classmethod
    def normalize_lists(cls, value):
        if value is None:
            return []
        if isinstance(value, (str, bytes)) or not isinstance(value, list):
            raise ValueError("evidence fields must be lists")
        return [_upper_required(item, "evidence") for item in value]

    @model_validator(mode="after")
    def validate_model(self):
        return _validate_safety_flags(self, "market regime summary report")


class CrossAssetInputSnapshotReport(_BaseReport):
    report_id: str = Field(..., min_length=1)
    snapshot: MarketRegimeInputSnapshot

    @field_validator("report_id", mode="before")
    @classmethod
    def normalize_id(cls, value):
        return _upper_required(value, "report_id")

    @model_validator(mode="after")
    def validate_model(self):
        return _validate_safety_flags(self, "cross asset input snapshot report")


class RiskAppetiteReport(_BaseReport):
    report_id: str = Field(..., min_length=1)
    risk_appetite: MarketRiskAppetite
    evidence: list[str] = Field(default_factory=list)

    @field_validator("report_id", mode="before")
    @classmethod
    def normalize_id(cls, value):
        return _upper_required(value, "report_id")

    @field_validator("evidence", mode="before")
    @classmethod
    def normalize_evidence(cls, value):
        if value is None:
            return []
        return [_upper_required(item, "evidence") for item in value]

    @model_validator(mode="after")
    def validate_model(self):
        return _validate_safety_flags(self, "risk appetite report")


class DirectionRegimeReport(_BaseReport):
    report_id: str = Field(..., min_length=1)
    market_direction: MarketDirection
    nq_trend: str = Field(..., min_length=1)
    es_trend: str = Field(..., min_length=1)

    @field_validator("report_id", "nq_trend", "es_trend", mode="before")
    @classmethod
    def normalize_upper(cls, value):
        return _upper_required(value, "field")

    @model_validator(mode="after")
    def validate_model(self):
        return _validate_safety_flags(self, "direction regime report")


class VolatilityRegimeReport(_BaseReport):
    report_id: str = Field(..., min_length=1)
    volatility_state: MarketVolatilityState
    vix_level_bucket: str = Field(..., min_length=1)
    vix_change_bucket: str = Field(..., min_length=1)

    @field_validator("report_id", "vix_level_bucket", "vix_change_bucket", mode="before")
    @classmethod
    def normalize_upper(cls, value):
        return _upper_required(value, "field")

    @model_validator(mode="after")
    def validate_model(self):
        return _validate_safety_flags(self, "volatility regime report")


class FXRateDollarStressReport(_BaseReport):
    report_id: str = Field(..., min_length=1)
    stress_state: MarketStressState
    dxy_trend: str = Field(..., min_length=1)
    us10y_trend: str = Field(..., min_length=1)
    usdkrw_stress_bucket: str = Field(..., min_length=1)

    @field_validator("report_id", "dxy_trend", "us10y_trend", "usdkrw_stress_bucket", mode="before")
    @classmethod
    def normalize_upper(cls, value):
        return _upper_required(value, "field")

    @model_validator(mode="after")
    def validate_model(self):
        return _validate_safety_flags(self, "fx rate dollar stress report")


class CrossAssetConflictReport(_BaseReport):
    report_id: str = Field(..., min_length=1)
    conflict_count: int = Field(..., ge=0)
    confirmation_score: int = Field(..., ge=0)
    conflict_score: int = Field(..., ge=0)
    conflicts: list[str] = Field(default_factory=list)

    @field_validator("report_id", mode="before")
    @classmethod
    def normalize_id(cls, value):
        return _upper_required(value, "report_id")

    @field_validator("conflicts", mode="before")
    @classmethod
    def normalize_conflicts(cls, value):
        if value is None:
            return []
        return [_upper_required(item, "conflict") for item in value]

    @model_validator(mode="after")
    def validate_model(self):
        return _validate_safety_flags(self, "cross asset conflict report")


class DownstreamConstraintReport(_BaseReport):
    report_id: str = Field(..., min_length=1)
    constraints: list[str] = Field(default_factory=list)
    block_promotion_if_insufficient_evidence: bool = False

    @field_validator("report_id", mode="before")
    @classmethod
    def normalize_id(cls, value):
        return _upper_required(value, "report_id")

    @field_validator("constraints", mode="before")
    @classmethod
    def normalize_constraints(cls, value):
        if value is None:
            return []
        return [_upper_required(item, "constraint") for item in value]

    @model_validator(mode="after")
    def validate_model(self):
        return _validate_safety_flags(self, "downstream constraint report")


class TrainingFeatureIntegrationReport(_BaseReport):
    report_id: str = Field(..., min_length=1)
    regime_feature_snapshot_id: str = Field(..., min_length=1)
    risk_state: str = Field(..., min_length=1)
    risk_appetite_label: str = Field(..., min_length=1)
    market_direction_label: str = Field(..., min_length=1)
    volatility_state_label: str = Field(..., min_length=1)
    stress_state_label: str = Field(..., min_length=1)
    cross_asset_confirmation_score: int = Field(..., ge=0)
    cross_asset_conflict_score: int = Field(..., ge=0)
    data_staleness_score: int = Field(..., ge=0)
    available_at_present: bool = False
    cnn_fear_greed_feature_present: bool = False
    cnn_fear_greed_source_ref: str | None = None
    training_feature_ready: bool = False

    @field_validator(
        "report_id",
        "regime_feature_snapshot_id",
        "risk_state",
        "risk_appetite_label",
        "market_direction_label",
        "volatility_state_label",
        "stress_state_label",
        mode="before",
    )
    @classmethod
    def normalize_upper(cls, value):
        return _upper_required(value, "field")

    @field_validator("cnn_fear_greed_source_ref", mode="before")
    @classmethod
    def normalize_optional_ref(cls, value):
        if value is None:
            return None
        return _validate_local_path(value, "cnn_fear_greed_source_ref")

    @model_validator(mode="after")
    def validate_model(self):
        return _validate_safety_flags(self, "training feature integration report")


class MarketRegimeGapReport(_BaseReport):
    gap_report_id: str = Field(..., min_length=1)
    decision: MarketRegimeDecision
    gap_entries: list[MarketRegimeGapEntry] = Field(default_factory=list)
    blocking_gap_count: int = Field(default=0, ge=0)
    warning_gap_count: int = Field(default=0, ge=0)

    @field_validator("gap_report_id", mode="before")
    @classmethod
    def normalize_id(cls, value):
        return _upper_required(value, "gap_report_id")

    @model_validator(mode="after")
    def validate_model(self):
        return _validate_safety_flags(self, "market regime gap report")


class MarketRegimeAuditRecord(_BaseReport):
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
        normalized = _aware(value)
        assert normalized is not None
        return normalized

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
        return _validate_safety_flags(self, "market regime audit record")


class MarketRegimeInput(_BaseReport):
    regime_id: str = Field(..., min_length=1)
    snapshot: MarketRegimeInputSnapshot
    audit_records: list[MarketRegimeAuditRecord] = Field(default_factory=list)
    summary_report: MarketRegimeSummaryReport | None = None
    input_snapshot_report: CrossAssetInputSnapshotReport | None = None
    risk_appetite_report: RiskAppetiteReport | None = None
    direction_regime_report: DirectionRegimeReport | None = None
    volatility_regime_report: VolatilityRegimeReport | None = None
    stress_report: FXRateDollarStressReport | None = None
    cross_asset_conflict_report: CrossAssetConflictReport | None = None
    downstream_constraint_report: DownstreamConstraintReport | None = None
    training_feature_integration_report: TrainingFeatureIntegrationReport | None = None
    gap_report: MarketRegimeGapReport | None = None

    @field_validator("regime_id", mode="before")
    @classmethod
    def normalize_id(cls, value):
        return _upper_required(value, "regime_id")

    @model_validator(mode="after")
    def validate_model(self):
        if not self.audit_records:
            raise ValueError("audit_records must not be empty")
        return _validate_safety_flags(self, "market regime input")
