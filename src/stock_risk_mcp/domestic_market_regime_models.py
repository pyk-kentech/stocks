from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from pydantic import Field, field_validator, model_validator

from stock_risk_mcp.models import StrictModel
from stock_risk_mcp.strategy_track_models import StrategyTrack


def aware(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("timestamp must include timezone")
    return value


DOMESTIC_MARKET_REGIME_METADATA = {
    "domestic_market_regime_fixture_run": True,
    "strategy_track_required": True,
    "domestic_kr_only": True,
    "market_profile_resolved": True,
    "market_regime_evidence_consumed": True,
    "market_regime_classification_generated": True,
    "market_regime_report_generated": True,
    "market_regime_gap_report_generated": True,
    "market_regime_non_executable": True,
    "kiwoom_api_called": False,
    "broker_api_called": False,
    "credentials_accessed": False,
    "external_network_calls": False,
    "orders_created": False,
    "order_intent_created": False,
    "order_drafts_created": False,
    "execution_approval_enabled": False,
    "live_or_prod_used": False,
    "cloud_llm_called": False,
    "model_runtime_called": False,
    "prompt_pack_executed": False,
    "prompt_stub_executed": False,
    "ml_model_trained": False,
    "real_market_data_fetched": False,
}


UNSAFE_REGIME_LABELS = {
    "BUY_MARKET",
    "SELL_MARKET",
    "ENTER_LONG",
    "EXIT_POSITION",
    "TRADE_APPROVED",
    "BUY",
    "SELL",
    "ORDER",
    "EXECUTE",
}

UNSAFE_EXECUTION_PATTERNS = tuple(UNSAFE_REGIME_LABELS)


class MarketRegimeLabel(StrEnum):
    REGIME_RISK_ON = "REGIME_RISK_ON"
    REGIME_RISK_OFF = "REGIME_RISK_OFF"
    REGIME_INDEX_UPTREND = "REGIME_INDEX_UPTREND"
    REGIME_INDEX_DOWNTREND = "REGIME_INDEX_DOWNTREND"
    REGIME_SECTOR_MOMENTUM = "REGIME_SECTOR_MOMENTUM"
    REGIME_SECTOR_ROTATION = "REGIME_SECTOR_ROTATION"
    REGIME_BREADTH_STRONG = "REGIME_BREADTH_STRONG"
    REGIME_BREADTH_WEAK = "REGIME_BREADTH_WEAK"
    REGIME_VOLATILITY_SPIKE = "REGIME_VOLATILITY_SPIKE"
    REGIME_LIQUIDITY_THIN = "REGIME_LIQUIDITY_THIN"
    REGIME_CHOPPY_MARKET = "REGIME_CHOPPY_MARKET"
    REGIME_INSUFFICIENT_DATA = "REGIME_INSUFFICIENT_DATA"
    REGIME_REPORT_ONLY = "REGIME_REPORT_ONLY"


class MarketRegimeEvidenceStrengthBucket(StrEnum):
    EVIDENCE_STRONG = "EVIDENCE_STRONG"
    EVIDENCE_MODERATE = "EVIDENCE_MODERATE"
    EVIDENCE_WEAK = "EVIDENCE_WEAK"
    EVIDENCE_INSUFFICIENT = "EVIDENCE_INSUFFICIENT"


class MarketRegimeGapCategory(StrEnum):
    MISSING_MARKET_PROFILE = "MISSING_MARKET_PROFILE"
    MISSING_REGIME_FIXTURE = "MISSING_REGIME_FIXTURE"
    MISSING_INDEX_EVIDENCE = "MISSING_INDEX_EVIDENCE"
    MISSING_SECTOR_EVIDENCE = "MISSING_SECTOR_EVIDENCE"
    MISSING_BREADTH_EVIDENCE = "MISSING_BREADTH_EVIDENCE"
    MISSING_LIQUIDITY_EVIDENCE = "MISSING_LIQUIDITY_EVIDENCE"
    MISSING_VOLATILITY_EVIDENCE = "MISSING_VOLATILITY_EVIDENCE"
    STALE_REGIME_EVIDENCE = "STALE_REGIME_EVIDENCE"
    INSUFFICIENT_REGIME_EVIDENCE = "INSUFFICIENT_REGIME_EVIDENCE"
    UNSUPPORTED_TRACK = "UNSUPPORTED_TRACK"
    EXECUTABLE_WORDING_DETECTED = "EXECUTABLE_WORDING_DETECTED"
    UNSAFE_TRIGGER_DETECTED = "UNSAFE_TRIGGER_DETECTED"


class ObservationWindowMetadata(StrictModel):
    window_id: str = Field(..., min_length=1)
    start_timestamp: datetime
    end_timestamp: datetime
    _start = field_validator("start_timestamp")(aware)
    _end = field_validator("end_timestamp")(aware)

    @field_validator("window_id", mode="before")
    @classmethod
    def normalize_window_id(cls, value):
        return str(value).strip().upper()

    @model_validator(mode="after")
    def validate_order(self):
        if self.end_timestamp <= self.start_timestamp:
            raise ValueError("impossible timestamp ordering in observation_window_metadata")
        return self


class IndexRegimeEvidence(StrictModel):
    index_id: str = Field(..., min_length=1)
    short_return_pct: float | None = None
    medium_return_pct: float | None = None
    drawdown_proxy_pct: float | None = None
    stale: bool = False
    data_quality_flags: list[str] = Field(default_factory=list)

    @field_validator("index_id", mode="before")
    @classmethod
    def normalize_id(cls, value):
        return str(value).strip().upper()

    @field_validator("data_quality_flags", mode="before")
    @classmethod
    def normalize_flags(cls, values):
        cleaned = [str(value).strip().upper() for value in values]
        if any(not value for value in cleaned):
            raise ValueError("data_quality_flags must not contain blank values")
        return cleaned


class SectorRegimeEvidence(StrictModel):
    sector_universe_id: str = Field(..., min_length=1)
    sector_return_distribution: dict[str, float] = Field(default_factory=dict)
    leadership_concentration_pct: float | None = None
    rotation_proxy: float | None = None
    stale: bool = False
    data_quality_flags: list[str] = Field(default_factory=list)

    @field_validator("sector_universe_id", mode="before")
    @classmethod
    def normalize_id(cls, value):
        return str(value).strip().upper()

    @field_validator("sector_return_distribution", mode="before")
    @classmethod
    def normalize_distribution(cls, values):
        normalized = {str(key).strip().upper(): float(value) for key, value in values.items()}
        if any(not key for key in normalized):
            raise ValueError("sector_return_distribution keys must not be blank")
        return normalized

    @field_validator("data_quality_flags", mode="before")
    @classmethod
    def normalize_flags(cls, values):
        cleaned = [str(value).strip().upper() for value in values]
        if any(not value for value in cleaned):
            raise ValueError("data_quality_flags must not contain blank values")
        return cleaned


class BreadthRegimeEvidence(StrictModel):
    breadth_proxy_pct: float | None = None
    advancing_count_proxy: int | None = None
    declining_count_proxy: int | None = None
    stale: bool = False
    data_quality_flags: list[str] = Field(default_factory=list)

    @field_validator("data_quality_flags", mode="before")
    @classmethod
    def normalize_flags(cls, values):
        cleaned = [str(value).strip().upper() for value in values]
        if any(not value for value in cleaned):
            raise ValueError("data_quality_flags must not contain blank values")
        return cleaned


class LiquidityRegimeEvidence(StrictModel):
    turnover_proxy_ratio: float | None = None
    volume_expansion_proxy_ratio: float | None = None
    stale: bool = False
    data_quality_flags: list[str] = Field(default_factory=list)

    @field_validator("data_quality_flags", mode="before")
    @classmethod
    def normalize_flags(cls, values):
        cleaned = [str(value).strip().upper() for value in values]
        if any(not value for value in cleaned):
            raise ValueError("data_quality_flags must not contain blank values")
        return cleaned


class VolatilityRegimeEvidence(StrictModel):
    volatility_proxy_pct: float | None = None
    volatility_expansion_proxy_ratio: float | None = None
    stale: bool = False
    data_quality_flags: list[str] = Field(default_factory=list)

    @field_validator("data_quality_flags", mode="before")
    @classmethod
    def normalize_flags(cls, values):
        cleaned = [str(value).strip().upper() for value in values]
        if any(not value for value in cleaned):
            raise ValueError("data_quality_flags must not contain blank values")
        return cleaned


class RiskRegimeEvidence(StrictModel):
    risk_off_warning_score: float | None = None
    stress_marker_count: int | None = None
    defensive_condition_markers: list[str] = Field(default_factory=list)
    stale: bool = False
    data_quality_flags: list[str] = Field(default_factory=list)

    @field_validator("defensive_condition_markers", "data_quality_flags", mode="before")
    @classmethod
    def normalize_flags(cls, values):
        cleaned = [str(value).strip().upper() for value in values]
        if any(not value for value in cleaned):
            raise ValueError("risk evidence lists must not contain blank values")
        return cleaned


class MarketRegimeConfig(StrictModel):
    config_id: str = Field(..., min_length=1)
    strategy_track: StrategyTrack
    market_profile_id: str = Field(..., min_length=1)
    explicit_regime_classification_opt_in: bool
    stale_evidence_policy: str = Field(..., min_length=1)
    report_only_eligibility_mode: str = Field(..., min_length=1)
    threshold_profile_id: str = Field(..., min_length=1)
    evidence_sufficiency_mode: str = Field(..., min_length=1)
    wording_validation_mode: str = Field(..., min_length=1)
    non_executable_enforcement_mode: str = Field(..., min_length=1)
    non_executable: bool
    signal_generation_allowed: bool
    cloud_llm_called: bool
    model_runtime_called: bool
    prompt_pack_executed: bool
    prompt_stub_executed: bool
    ml_model_trained: bool

    @field_validator(
        "config_id",
        "market_profile_id",
        "stale_evidence_policy",
        "report_only_eligibility_mode",
        "threshold_profile_id",
        "evidence_sufficiency_mode",
        "wording_validation_mode",
        "non_executable_enforcement_mode",
        mode="before",
    )
    @classmethod
    def normalize_text(cls, value):
        return str(value).strip().upper()

    @model_validator(mode="after")
    def validate_domestic_only(self):
        if self.strategy_track != StrategyTrack.DOMESTIC_KR:
            raise ValueError("market regime config requires StrategyTrack DOMESTIC_KR")
        if self.market_profile_id != "KRX":
            raise ValueError("market regime config requires market_profile_id KRX")
        if not self.explicit_regime_classification_opt_in:
            raise ValueError("explicit regime classification opt-in is required")
        return self


class MarketRegimeInputSet(StrictModel):
    input_set_id: str = Field(..., min_length=1)
    strategy_track: StrategyTrack
    market_profile_summary: dict = Field(default_factory=dict)
    observation_window_metadata: ObservationWindowMetadata
    index_evidence: IndexRegimeEvidence
    sector_evidence: SectorRegimeEvidence
    breadth_evidence: BreadthRegimeEvidence
    liquidity_evidence: LiquidityRegimeEvidence
    volatility_evidence: VolatilityRegimeEvidence
    risk_evidence: RiskRegimeEvidence
    data_quality_flags: list[str] = Field(default_factory=list)
    explicit_report_only: bool = False
    source_trace_references: list[str] = Field(default_factory=list)

    @field_validator("input_set_id", mode="before")
    @classmethod
    def normalize_id(cls, value):
        return str(value).strip()

    @field_validator("data_quality_flags", "source_trace_references", mode="before")
    @classmethod
    def normalize_list(cls, values):
        cleaned = [str(value).strip().upper() for value in values]
        if any(not value for value in cleaned):
            raise ValueError("list values must not be blank")
        return cleaned

    @model_validator(mode="after")
    def validate_input_set(self):
        if self.strategy_track != StrategyTrack.DOMESTIC_KR:
            raise ValueError("market regime input set requires StrategyTrack DOMESTIC_KR")
        market_id = str(self.market_profile_summary.get("market_id", "")).upper()
        if market_id != "KRX":
            raise ValueError("market_profile must resolve to KRX")
        if {"UNSAFE_TRIGGER_ATTEMPT", "ORDER_TRIGGER_ATTEMPT"} & set(self.data_quality_flags):
            raise ValueError("unsafe trigger attempt is not allowed in market regime fixtures")
        return self


class MarketRegimeEvidenceSnapshot(StrictModel):
    snapshot_id: str
    fixture_id: str
    strategy_track: StrategyTrack
    market_profile_id: str
    observation_window_metadata: ObservationWindowMetadata
    index_evidence: IndexRegimeEvidence
    sector_evidence: SectorRegimeEvidence
    breadth_evidence: BreadthRegimeEvidence
    liquidity_evidence: LiquidityRegimeEvidence
    volatility_evidence: VolatilityRegimeEvidence
    risk_evidence: RiskRegimeEvidence
    data_quality_flags: list[str] = Field(default_factory=list)
    stale_evidence_summary: dict = Field(default_factory=dict)
    missing_evidence_summary: dict = Field(default_factory=dict)
    non_executable: bool = True
    source_trace_references: list[str] = Field(default_factory=list)


class MarketRegimeClassification(StrictModel):
    classification_id: str
    evidence_snapshot_id: str
    primary_regime_label: MarketRegimeLabel
    secondary_regime_labels: list[MarketRegimeLabel] = Field(default_factory=list)
    evidence_strength_bucket: MarketRegimeEvidenceStrengthBucket
    blocked_reasons: list[str] = Field(default_factory=list)
    report_only: bool = False
    non_actionable: bool = True
    stale_evidence_summary: dict = Field(default_factory=dict)
    missing_evidence_summary: dict = Field(default_factory=dict)
    source_trace_references: list[str] = Field(default_factory=list)
    integration_context_placeholders: dict = Field(default_factory=dict)


class RegimeAwareContextReference(StrictModel):
    context_reference_id: str
    source_report_id: str
    source_evidence_snapshot_id: str
    evidence_category_references: dict = Field(default_factory=dict)
    strategy_track: StrategyTrack
    market_profile_id: str
    primary_regime_label: MarketRegimeLabel
    secondary_regime_labels: list[MarketRegimeLabel] = Field(default_factory=list)
    report_only: bool = False
    stale: bool = False
    missing_evidence: bool = False
    non_executable: bool = True


class MarketRegimeReport(StrictModel):
    schema_version: str = "4.11-domestic-market-regime-report"
    report_id: str
    fixture_id: str
    strategy_track: StrategyTrack
    market_profile_id: str
    evidence_snapshot_id: str
    primary_regime_label: MarketRegimeLabel
    secondary_regime_labels: list[MarketRegimeLabel] = Field(default_factory=list)
    evidence_strength_bucket: MarketRegimeEvidenceStrengthBucket
    data_quality_flags: list[str] = Field(default_factory=list)
    blocked_reasons: list[str] = Field(default_factory=list)
    missing_evidence_summary: dict = Field(default_factory=dict)
    stale_evidence_summary: dict = Field(default_factory=dict)
    report_only: bool = False
    non_executable: bool = True
    source_trace_references: list[str] = Field(default_factory=list)
    integration_context_placeholders: dict = Field(default_factory=dict)
    context_reference: RegimeAwareContextReference
    metadata_json: dict = Field(default_factory=lambda: dict(DOMESTIC_MARKET_REGIME_METADATA))


class MarketRegimeGapReport(StrictModel):
    schema_version: str = "4.11-domestic-market-regime-gap-report"
    report_id: str
    fixture_id: str
    strategy_track: StrategyTrack
    market_profile_id: str
    gap_categories: list[str] = Field(default_factory=list)
    missing_critical_evidence_count: int = Field(..., ge=0)
    stale_evidence_count: int = Field(..., ge=0)
    wording_violation_count: int = Field(..., ge=0)
    unsupported_track_count: int = Field(..., ge=0)
    metadata_json: dict = Field(default_factory=lambda: dict(DOMESTIC_MARKET_REGIME_METADATA))


class MarketRegimeSafetyBoundary(StrictModel):
    evidence_only: bool = True
    non_executable_only: bool = True
    signal_generation_allowed: bool = False
    order_creation_allowed: bool = False
    order_intent_creation_allowed: bool = False
    order_draft_creation_allowed: bool = False
    execution_approval_allowed: bool = False
    cloud_llm_allowed: bool = False
    model_runtime_allowed: bool = False
    live_or_prod_allowed: bool = False


class MarketRegimeSafetyReport(StrictModel):
    schema_version: str = "4.11-domestic-market-regime-safety-report"
    report_id: str
    strategy_track: StrategyTrack
    safety_boundary: MarketRegimeSafetyBoundary
    warnings: list[str] = Field(default_factory=list)
    block_reasons: list[str] = Field(default_factory=list)
    metadata_json: dict = Field(default_factory=lambda: dict(DOMESTIC_MARKET_REGIME_METADATA))


class MarketRegimeFixture(StrictModel):
    schema_version: str
    fixture_id: str = Field(..., min_length=1)
    created_at: datetime
    market_regime_config: MarketRegimeConfig
    market_regime_input_set: MarketRegimeInputSet
    _created = field_validator("created_at")(aware)

    @field_validator("schema_version")
    @classmethod
    def exact_schema(cls, value: str) -> str:
        if value != "4.11-domestic-market-regime-fixture":
            raise ValueError("schema_version must be exactly 4.11-domestic-market-regime-fixture")
        return value

    @model_validator(mode="after")
    def validate_fixture(self):
        if self.market_regime_config.strategy_track != StrategyTrack.DOMESTIC_KR:
            raise ValueError("market regime fixture requires StrategyTrack DOMESTIC_KR")
        if self.market_regime_input_set.strategy_track != StrategyTrack.DOMESTIC_KR:
            raise ValueError("market regime input set must be DOMESTIC_KR")
        if str(self.market_regime_input_set.market_profile_summary.get("market_id", "")).upper() != "KRX":
            raise ValueError("market_profile must resolve to KRX")
        return self
