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


def _normalize_list(value, field_name: str, *, upper: bool = False, local_paths: bool = False) -> list[str]:
    if value is None:
        return []
    if isinstance(value, (str, bytes)) or not isinstance(value, list):
        raise ValueError(f"{field_name} must be a list")
    if local_paths:
        return [_validate_local_path(item, field_name) for item in value]
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


class BreadthState(StrEnum):
    BROAD_STRENGTH = "BROAD_STRENGTH"
    HEALTHY = "HEALTHY"
    MIXED = "MIXED"
    NARROW_LEADERSHIP = "NARROW_LEADERSHIP"
    BROAD_WEAKNESS = "BROAD_WEAKNESS"
    UNKNOWN = "UNKNOWN"


class LeadershipState(StrEnum):
    NO_CLEAR_LEADERSHIP = "NO_CLEAR_LEADERSHIP"
    HEALTHY_SECTOR_LEADERSHIP = "HEALTHY_SECTOR_LEADERSHIP"
    CROWDED_LEADERSHIP = "CROWDED_LEADERSHIP"
    LEADERSHIP_ANOMALY = "LEADERSHIP_ANOMALY"
    INDEX_DISTORTION = "INDEX_DISTORTION"
    UNKNOWN = "UNKNOWN"


class OutlierMomentumState(StrEnum):
    NO_OUTLIER = "NO_OUTLIER"
    OUTLIER_WATCH = "OUTLIER_WATCH"
    OUTLIER_MOMENTUM_ALLOWED = "OUTLIER_MOMENTUM_ALLOWED"
    OUTLIER_MOMENTUM_RESTRICTED = "OUTLIER_MOMENTUM_RESTRICTED"
    OUTLIER_BLOCKED = "OUTLIER_BLOCKED"
    UNKNOWN = "UNKNOWN"


class InternalRiskState(StrEnum):
    LOW_INTERNAL_RISK = "LOW_INTERNAL_RISK"
    MODERATE_INTERNAL_RISK = "MODERATE_INTERNAL_RISK"
    HIGH_INTERNAL_RISK = "HIGH_INTERNAL_RISK"
    INTERNAL_STRESS = "INTERNAL_STRESS"
    UNKNOWN = "UNKNOWN"


class BreadthLeadershipRoutingDecision(StrEnum):
    BROAD_MARKET_OK = "BROAD_MARKET_OK"
    LEADERSHIP_ONLY = "LEADERSHIP_ONLY"
    SECTOR_ONLY = "SECTOR_ONLY"
    LARGE_CAP_ONLY = "LARGE_CAP_ONLY"
    WATCH_NON_LEADERS = "WATCH_NON_LEADERS"
    OUTLIER_MOMENTUM_ALLOWED = "OUTLIER_MOMENTUM_ALLOWED"
    OUTLIER_MOMENTUM_RESTRICTED = "OUTLIER_MOMENTUM_RESTRICTED"
    REDUCE_SIZE = "REDUCE_SIZE"
    BLOCK_CHASING = "BLOCK_CHASING"
    DATA_GAP = "DATA_GAP"
    BLOCKED = "BLOCKED"
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


class BreadthLeadershipRoutingSafetyReport(_BaseReport):
    safety_report_id: str = Field(..., min_length=1)
    blocked_capabilities: list[str] = Field(default_factory=list)
    findings: list[str] = Field(default_factory=list)

    @field_validator("safety_report_id", mode="before")
    @classmethod
    def normalize_id(cls, value):
        return _upper_required(value, "safety_report_id")

    @field_validator("blocked_capabilities", "findings", mode="before")
    @classmethod
    def normalize_lists(cls, value, info):
        return _normalize_list(value, info.field_name, upper=True)

    @model_validator(mode="after")
    def validate_model(self):
        return _validate_safety_flags(self, "breadth leadership routing safety report")


class BreadthLeadershipRoutingAuditRecord(StrictModel):
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
    def normalize_dt(cls, value):
        return _aware(value)

    @field_validator("source_path", mode="before")
    @classmethod
    def normalize_path(cls, value):
        return _validate_local_path(value, "source_path")

    @field_validator("operator_context", mode="before")
    @classmethod
    def normalize_context(cls, value):
        return _string_required(value, "operator_context")


class BreadthInputSnapshot(StrictModel):
    snapshot_id: str = Field(..., min_length=1)
    market: str = Field(..., min_length=1)
    benchmark_ref: str = Field(..., min_length=1)
    observed_at: datetime
    available_at: datetime | None = None
    source_provider_ref: str = Field(..., min_length=1)
    total_listed_universe_count: int = Field(..., ge=0)
    tradable_universe_count: int = Field(..., ge=0)
    advancing_count: int = Field(..., ge=0)
    declining_count: int = Field(..., ge=0)
    unchanged_count: int = Field(..., ge=0)
    new_highs_count: int = Field(..., ge=0)
    new_lows_count: int = Field(..., ge=0)
    above_moving_average_count: int | None = Field(default=None, ge=0)
    below_moving_average_count: int | None = Field(default=None, ge=0)
    up_volume: float = Field(..., ge=0)
    down_volume: float = Field(..., ge=0)
    total_volume: float = Field(..., ge=0)
    relative_volume: float | None = Field(default=None, ge=0)
    index_return_percent: float
    equal_weight_proxy_return_percent: float | None = None
    large_cap_proxy_return_percent: float | None = None
    small_mid_cap_proxy_return_percent: float | None = None
    data_freshness_policy_ref: str = Field(..., min_length=1)

    @field_validator("snapshot_id", "market", mode="before")
    @classmethod
    def normalize_upper(cls, value):
        return _upper_required(value, "field")

    @field_validator("benchmark_ref", "source_provider_ref", "data_freshness_policy_ref", mode="before")
    @classmethod
    def normalize_ref(cls, value):
        return _validate_local_path(value, "ref")

    @field_validator("observed_at", "available_at", mode="before")
    @classmethod
    def normalize_dt(cls, value):
        return _aware(value)


class SectorLeadershipSnapshot(StrictModel):
    sector_id: str = Field(..., min_length=1)
    sector_name: str = Field(..., min_length=1)
    sector_return_percent: float
    sector_relative_strength: float
    sector_volume_share: float = Field(..., ge=0)
    sector_trading_value_share: float = Field(..., ge=0)
    sector_advancing_count: int = Field(..., ge=0)
    sector_declining_count: int = Field(..., ge=0)
    sector_new_highs_count: int = Field(..., ge=0)
    sector_new_lows_count: int = Field(..., ge=0)
    sector_internal_breadth_score: float = Field(..., ge=0)
    top_contributors: list[str] = Field(default_factory=list)
    leadership_concentration_score: float = Field(..., ge=0)
    source_refs: list[str] = Field(default_factory=list)
    available_at: datetime | None = None

    @field_validator("sector_id", "sector_name", mode="before")
    @classmethod
    def normalize_upper(cls, value):
        return _upper_required(value, "field")

    @field_validator("top_contributors", mode="before")
    @classmethod
    def normalize_contributors(cls, value):
        return _normalize_list(value, "top_contributors", upper=True)

    @field_validator("source_refs", mode="before")
    @classmethod
    def normalize_refs(cls, value):
        return _normalize_list(value, "source_refs", local_paths=True)

    @field_validator("available_at", mode="before")
    @classmethod
    def normalize_dt(cls, value):
        return _aware(value)


class IndexDistortionSnapshot(StrictModel):
    snapshot_id: str = Field(..., min_length=1)
    top_1_contribution_share: float = Field(..., ge=0)
    top_2_contribution_share: float = Field(..., ge=0)
    top_5_contribution_share: float = Field(..., ge=0)
    top_10_contribution_share: float = Field(..., ge=0)
    mega_cap_contribution_share: float = Field(..., ge=0)
    index_return_excluding_top_contributors_percent: float | None = None
    equal_weight_divergence_percent: float | None = None
    large_cap_vs_small_mid_divergence_percent: float | None = None
    index_distortion_score: float = Field(..., ge=0)
    distorted_index_warning: bool = False
    source_refs: list[str] = Field(default_factory=list)
    available_at: datetime | None = None

    @field_validator("snapshot_id", mode="before")
    @classmethod
    def normalize_id(cls, value):
        return _upper_required(value, "snapshot_id")

    @field_validator("source_refs", mode="before")
    @classmethod
    def normalize_refs(cls, value):
        return _normalize_list(value, "source_refs", local_paths=True)

    @field_validator("available_at", mode="before")
    @classmethod
    def normalize_dt(cls, value):
        return _aware(value)


class OutlierMomentumCandidate(StrictModel):
    candidate_id: str = Field(..., min_length=1)
    symbol: str = Field(..., min_length=1)
    market: str = Field(..., min_length=1)
    sector: str = Field(..., min_length=1)
    price_change_percent: float
    gap_percent: float
    relative_volume: float = Field(..., ge=0)
    trading_value_surge: float = Field(..., ge=0)
    new_high_breakout_flag: bool = False
    volatility_interruption_flag: bool = False
    news_catalyst_ref: str | None = None
    disclosure_theme_catalyst_ref: str | None = None
    low_float_scarcity_proxy: float | None = Field(default=None, ge=0)
    ipo_new_listing_flag: bool = False
    liquidity_evidence_ref: str | None = None
    slippage_risk_note: str | None = None
    max_outlier_sleeve_allocation: float = Field(..., ge=0)
    max_per_name_risk: float = Field(..., ge=0)
    required_stop_discipline: str | None = None
    no_execution_flag: bool = True
    available_at: datetime | None = None

    @field_validator("candidate_id", "symbol", "market", "sector", mode="before")
    @classmethod
    def normalize_upper(cls, value):
        return _upper_required(value, "field")

    @field_validator("news_catalyst_ref", "disclosure_theme_catalyst_ref", "liquidity_evidence_ref", mode="before")
    @classmethod
    def normalize_optional_ref(cls, value):
        if value is None:
            return None
        return _validate_local_path(value, "ref")

    @field_validator("slippage_risk_note", "required_stop_discipline", mode="before")
    @classmethod
    def normalize_optional_text(cls, value):
        if value is None:
            return None
        return _string_required(value, "field").upper()

    @field_validator("available_at", mode="before")
    @classmethod
    def normalize_dt(cls, value):
        return _aware(value)


class OutlierSleevePolicy(StrictModel):
    policy_id: str = Field(..., min_length=1)
    max_portfolio_allocation: float = Field(..., ge=0)
    max_per_name_risk: float = Field(..., ge=0)
    max_daily_loss: float = Field(..., ge=0)
    max_outlier_names: int = Field(..., ge=0)
    mandatory_stop_discipline: bool = True
    mandatory_liquidity_evidence: bool = True
    mandatory_slippage_note: bool = True
    mandatory_no_execution_flag: bool = True
    event_risk_compatibility_required: bool = True
    watch_only_fallback_when_evidence_missing: bool = True

    @field_validator("policy_id", mode="before")
    @classmethod
    def normalize_id(cls, value):
        return _upper_required(value, "policy_id")


class BreadthRoutingSummaryReport(_BaseReport):
    report_id: str = Field(..., min_length=1)
    primary_decision: BreadthLeadershipRoutingDecision
    breadth_state: BreadthState
    leadership_state: LeadershipState
    outlier_momentum_state: OutlierMomentumState
    internal_risk_state: InternalRiskState
    decision_reason: str = Field(..., min_length=1)
    downstream_constraints: list[str] = Field(default_factory=list)
    approved_sector_ids: list[str] = Field(default_factory=list)

    @field_validator("report_id", mode="before")
    @classmethod
    def normalize_id(cls, value):
        return _upper_required(value, "report_id")

    @field_validator("decision_reason", mode="before")
    @classmethod
    def normalize_reason(cls, value):
        return _string_required(value, "decision_reason")

    @field_validator("downstream_constraints", "approved_sector_ids", mode="before")
    @classmethod
    def normalize_lists(cls, value, info):
        return _normalize_list(value, info.field_name, upper=True)

    @model_validator(mode="after")
    def validate_model(self):
        return _validate_safety_flags(self, "breadth routing summary report")


class BreadthInputSnapshotReport(_BaseReport):
    report_id: str = Field(..., min_length=1)
    snapshot: BreadthInputSnapshot

    @field_validator("report_id", mode="before")
    @classmethod
    def normalize_id(cls, value):
        return _upper_required(value, "report_id")

    @model_validator(mode="after")
    def validate_model(self):
        return _validate_safety_flags(self, "breadth input snapshot report")


class AdvanceDeclineReport(_BaseReport):
    report_id: str = Field(..., min_length=1)
    advance_decline_ratio: float = Field(..., ge=0)
    advance_decline_spread: int
    percent_advancing: float = Field(..., ge=0)
    percent_declining: float = Field(..., ge=0)
    participation_score: int = Field(..., ge=0)
    breadth_state: BreadthState

    @field_validator("report_id", mode="before")
    @classmethod
    def normalize_id(cls, value):
        return _upper_required(value, "report_id")

    @model_validator(mode="after")
    def validate_model(self):
        return _validate_safety_flags(self, "advance decline report")


class NewHighLowReport(_BaseReport):
    report_id: str = Field(..., min_length=1)
    new_high_low_ratio: float = Field(..., ge=0)
    new_high_low_spread: int
    breadth_deterioration_score: int = Field(..., ge=0)

    @field_validator("report_id", mode="before")
    @classmethod
    def normalize_id(cls, value):
        return _upper_required(value, "report_id")

    @model_validator(mode="after")
    def validate_model(self):
        return _validate_safety_flags(self, "new high low report")


class UpDownVolumeParticipationReport(_BaseReport):
    report_id: str = Field(..., min_length=1)
    up_volume_ratio: float = Field(..., ge=0)
    down_volume_ratio: float = Field(..., ge=0)
    breadth_thrust_proxy: float = Field(..., ge=0)
    relative_volume: float | None = Field(default=None, ge=0)
    market_health_score: int = Field(..., ge=0)

    @field_validator("report_id", mode="before")
    @classmethod
    def normalize_id(cls, value):
        return _upper_required(value, "report_id")

    @model_validator(mode="after")
    def validate_model(self):
        return _validate_safety_flags(self, "up down volume participation report")


class SectorLeadershipReport(_BaseReport):
    report_id: str = Field(..., min_length=1)
    approved_sector_ids: list[str] = Field(default_factory=list)
    sector_count: int = Field(..., ge=0)
    healthy_sector_count: int = Field(..., ge=0)
    crowded_sector_count: int = Field(..., ge=0)
    leadership_state: LeadershipState

    @field_validator("report_id", mode="before")
    @classmethod
    def normalize_id(cls, value):
        return _upper_required(value, "report_id")

    @field_validator("approved_sector_ids", mode="before")
    @classmethod
    def normalize_ids(cls, value):
        return _normalize_list(value, "approved_sector_ids", upper=True)

    @model_validator(mode="after")
    def validate_model(self):
        return _validate_safety_flags(self, "sector leadership report")


class LeadershipConcentrationReport(_BaseReport):
    report_id: str = Field(..., min_length=1)
    leadership_state: LeadershipState
    crowded_sector_ids: list[str] = Field(default_factory=list)
    maximum_concentration_score: float = Field(..., ge=0)
    concentration_warning: bool = False

    @field_validator("report_id", mode="before")
    @classmethod
    def normalize_id(cls, value):
        return _upper_required(value, "report_id")

    @field_validator("crowded_sector_ids", mode="before")
    @classmethod
    def normalize_ids(cls, value):
        return _normalize_list(value, "crowded_sector_ids", upper=True)

    @model_validator(mode="after")
    def validate_model(self):
        return _validate_safety_flags(self, "leadership concentration report")


class IndexDistortionReport(_BaseReport):
    report_id: str = Field(..., min_length=1)
    distortion_snapshot: IndexDistortionSnapshot
    leadership_state: LeadershipState
    distortion_warning: bool = False

    @field_validator("report_id", mode="before")
    @classmethod
    def normalize_id(cls, value):
        return _upper_required(value, "report_id")

    @model_validator(mode="after")
    def validate_model(self):
        return _validate_safety_flags(self, "index distortion report")


class EqualWeightDivergenceReport(_BaseReport):
    report_id: str = Field(..., min_length=1)
    equal_weight_divergence_percent: float | None = None
    large_cap_vs_small_mid_divergence_percent: float | None = None
    breadth_divergence_score: float = Field(..., ge=0)
    divergence_warning: bool = False

    @field_validator("report_id", mode="before")
    @classmethod
    def normalize_id(cls, value):
        return _upper_required(value, "report_id")

    @model_validator(mode="after")
    def validate_model(self):
        return _validate_safety_flags(self, "equal weight divergence report")


class OutlierMomentumCandidateReport(_BaseReport):
    report_id: str = Field(..., min_length=1)
    selected_candidate_id: str | None = None
    selected_symbol: str | None = None
    outlier_momentum_state: OutlierMomentumState
    eligible_candidate_ids: list[str] = Field(default_factory=list)
    restricted_candidate_ids: list[str] = Field(default_factory=list)

    @field_validator("report_id", "selected_candidate_id", "selected_symbol", mode="before")
    @classmethod
    def normalize_optional_upper(cls, value):
        if value is None:
            return None
        return _upper_required(value, "field")

    @field_validator("eligible_candidate_ids", "restricted_candidate_ids", mode="before")
    @classmethod
    def normalize_ids(cls, value):
        return _normalize_list(value, "candidate_ids", upper=True)

    @model_validator(mode="after")
    def validate_model(self):
        return _validate_safety_flags(self, "outlier momentum candidate report")


class OutlierSleeveRiskReport(_BaseReport):
    report_id: str = Field(..., min_length=1)
    policy_id: str = Field(..., min_length=1)
    max_portfolio_allocation: float = Field(..., ge=0)
    max_per_name_risk: float = Field(..., ge=0)
    max_daily_loss: float = Field(..., ge=0)
    max_outlier_names: int = Field(..., ge=0)
    liquidity_evidence_required: bool = True
    stop_discipline_required: bool = True
    slippage_note_required: bool = True
    no_execution_required: bool = True
    event_risk_compatibility_required: bool = True

    @field_validator("report_id", "policy_id", mode="before")
    @classmethod
    def normalize_upper(cls, value):
        return _upper_required(value, "field")

    @model_validator(mode="after")
    def validate_model(self):
        return _validate_safety_flags(self, "outlier sleeve risk report")


class DownstreamRoutingConstraintReport(_BaseReport):
    report_id: str = Field(..., min_length=1)
    constraints: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    block_promotion: bool = False

    @field_validator("report_id", mode="before")
    @classmethod
    def normalize_id(cls, value):
        return _upper_required(value, "report_id")

    @field_validator("constraints", "warnings", mode="before")
    @classmethod
    def normalize_lists(cls, value, info):
        return _normalize_list(value, info.field_name, upper=True)

    @model_validator(mode="after")
    def validate_model(self):
        return _validate_safety_flags(self, "downstream routing constraint report")


class BreadthRoutingProviderReadinessReport(_BaseReport):
    report_id: str = Field(..., min_length=1)
    provider_ready: bool = False
    missing_refs: list[str] = Field(default_factory=list)
    missing_levels: list[str] = Field(default_factory=list)
    canonical_contract_present: bool = False

    @field_validator("report_id", mode="before")
    @classmethod
    def normalize_id(cls, value):
        return _upper_required(value, "report_id")

    @field_validator("missing_refs", "missing_levels", mode="before")
    @classmethod
    def normalize_lists(cls, value, info):
        return _normalize_list(value, info.field_name, upper=True)

    @model_validator(mode="after")
    def validate_model(self):
        return _validate_safety_flags(self, "breadth routing provider readiness report")


class BreadthRoutingLeakageReport(_BaseReport):
    report_id: str = Field(..., min_length=1)
    future_breadth_leakage: bool = False
    future_sector_leadership_leakage: bool = False
    future_outlier_catalyst_leakage: bool = False
    missing_available_at: bool = False
    stale_data_detected: bool = False
    findings: list[str] = Field(default_factory=list)

    @field_validator("report_id", mode="before")
    @classmethod
    def normalize_id(cls, value):
        return _upper_required(value, "report_id")

    @field_validator("findings", mode="before")
    @classmethod
    def normalize_findings(cls, value):
        return _normalize_list(value, "findings", upper=True)

    @model_validator(mode="after")
    def validate_model(self):
        return _validate_safety_flags(self, "breadth routing leakage report")


class BreadthRoutingGapEntry(StrictModel):
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


class BreadthRoutingGapReport(_BaseReport):
    gap_report_id: str = Field(..., min_length=1)
    primary_decision: BreadthLeadershipRoutingDecision
    gap_entries: list[BreadthRoutingGapEntry] = Field(default_factory=list)
    blocking_gap_count: int = Field(default=0, ge=0)
    warning_gap_count: int = Field(default=0, ge=0)
    gap_categories: list[str] = Field(default_factory=list)

    @field_validator("gap_report_id", mode="before")
    @classmethod
    def normalize_id(cls, value):
        return _upper_required(value, "gap_report_id")

    @model_validator(mode="after")
    def validate_model(self):
        if not self.gap_categories:
            self.gap_categories = [entry.gap_category for entry in self.gap_entries]
        return _validate_safety_flags(self, "breadth routing gap report")


class BreadthRoutingTrainingFeatureIntegrationReport(_BaseReport):
    report_id: str = Field(..., min_length=1)
    routing_feature_snapshot_id: str = Field(..., min_length=1)
    breadth_state_label: str = Field(..., min_length=1)
    leadership_state_label: str = Field(..., min_length=1)
    outlier_momentum_state_label: str = Field(..., min_length=1)
    internal_risk_state_label: str = Field(..., min_length=1)
    primary_routing_decision: str = Field(..., min_length=1)
    participation_score: int = Field(..., ge=0)
    breadth_deterioration_score: int = Field(..., ge=0)
    breadth_divergence_score: float = Field(..., ge=0)
    market_health_score: int = Field(..., ge=0)
    outlier_eligible_flag: bool = False
    event_risk_blocked_flag: bool = False
    risk_budget_blocked_flag: bool = False
    available_at_present: bool = False
    training_feature_ready: bool = False

    @field_validator(
        "report_id",
        "routing_feature_snapshot_id",
        "breadth_state_label",
        "leadership_state_label",
        "outlier_momentum_state_label",
        "internal_risk_state_label",
        "primary_routing_decision",
        mode="before",
    )
    @classmethod
    def normalize_upper(cls, value):
        return _upper_required(value, "field")

    @model_validator(mode="after")
    def validate_model(self):
        return _validate_safety_flags(self, "breadth routing training feature integration report")


class BreadthLeadershipRoutingInput(StrictModel):
    routing_review_id: str = Field(..., min_length=1)
    candidate_symbol: str = Field(..., min_length=1)
    candidate_market: str = Field(..., min_length=1)
    candidate_sector_id: str = Field(..., min_length=1)
    candidate_sector_name: str = Field(..., min_length=1)
    candidate_action_type: str = Field(..., min_length=1)
    decision_timestamp: datetime
    candidate_is_large_cap: bool = False
    candidate_is_leadership_sector: bool = False
    candidate_is_outlier_momentum: bool = False
    candidate_news_catalyst_available: bool = False
    candidate_disclosure_catalyst_available: bool = False
    breadth_snapshot: BreadthInputSnapshot
    sector_leadership_snapshots: list[SectorLeadershipSnapshot] = Field(default_factory=list)
    index_distortion_snapshot: IndexDistortionSnapshot
    outlier_momentum_candidates: list[OutlierMomentumCandidate] = Field(default_factory=list)
    outlier_sleeve_policy: OutlierSleevePolicy
    market_regime_ref: str | None = None
    market_regime_label: str | None = None
    market_regime_risk_appetite: str | None = None
    position_sizing_ref: str | None = None
    position_sizing_decision: str | None = None
    event_risk_ref: str | None = None
    event_risk_decision: str | None = None
    breadth_provider_readiness_ref: str | None = None
    breadth_provider_readiness_level: str | None = None
    sector_mapping_provider_readiness_ref: str | None = None
    sector_mapping_provider_readiness_level: str | None = None
    market_internals_provider_readiness_ref: str | None = None
    market_internals_provider_readiness_level: str | None = None
    relative_volume_provider_readiness_ref: str | None = None
    relative_volume_provider_readiness_level: str | None = None
    news_catalyst_provider_ref: str | None = None
    canonical_data_contract_ref: str | None = None
    source_refs: list[str] = Field(default_factory=list)
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
    safety_report: BreadthLeadershipRoutingSafetyReport
    audit_records: list[BreadthLeadershipRoutingAuditRecord] = Field(default_factory=list)
    summary_report: BreadthRoutingSummaryReport | None = None
    breadth_input_snapshot_report: BreadthInputSnapshotReport | None = None
    advance_decline_report: AdvanceDeclineReport | None = None
    new_high_low_report: NewHighLowReport | None = None
    up_down_volume_participation_report: UpDownVolumeParticipationReport | None = None
    sector_leadership_report: SectorLeadershipReport | None = None
    leadership_concentration_report: LeadershipConcentrationReport | None = None
    index_distortion_report: IndexDistortionReport | None = None
    equal_weight_divergence_report: EqualWeightDivergenceReport | None = None
    outlier_momentum_candidate_report: OutlierMomentumCandidateReport | None = None
    outlier_sleeve_risk_report: OutlierSleeveRiskReport | None = None
    downstream_constraint_report: DownstreamRoutingConstraintReport | None = None
    provider_readiness_report: BreadthRoutingProviderReadinessReport | None = None
    leakage_report: BreadthRoutingLeakageReport | None = None
    gap_report: BreadthRoutingGapReport | None = None
    training_feature_integration_report: BreadthRoutingTrainingFeatureIntegrationReport | None = None

    @field_validator(
        "routing_review_id",
        "candidate_symbol",
        "candidate_market",
        "candidate_sector_id",
        "candidate_sector_name",
        "candidate_action_type",
        "market_regime_label",
        "market_regime_risk_appetite",
        "position_sizing_decision",
        "event_risk_decision",
        "breadth_provider_readiness_level",
        "sector_mapping_provider_readiness_level",
        "market_internals_provider_readiness_level",
        "relative_volume_provider_readiness_level",
        mode="before",
    )
    @classmethod
    def normalize_upper(cls, value):
        if value is None:
            return None
        return _upper_required(value, "field")

    @field_validator("decision_timestamp", mode="before")
    @classmethod
    def normalize_dt(cls, value):
        return _aware(value)

    @field_validator(
        "market_regime_ref",
        "position_sizing_ref",
        "event_risk_ref",
        "breadth_provider_readiness_ref",
        "sector_mapping_provider_readiness_ref",
        "market_internals_provider_readiness_ref",
        "relative_volume_provider_readiness_ref",
        "news_catalyst_provider_ref",
        "canonical_data_contract_ref",
        mode="before",
    )
    @classmethod
    def normalize_optional_ref(cls, value):
        if value is None:
            return None
        return _validate_local_path(value, "ref")

    @field_validator("source_refs", mode="before")
    @classmethod
    def normalize_refs(cls, value):
        return _normalize_list(value, "source_refs", local_paths=True)

    @model_validator(mode="after")
    def validate_model(self):
        return _validate_safety_flags(self, "breadth leadership routing input")
