from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from pydantic import Field, field_validator, model_validator

from stock_risk_mcp.domestic_realtime_models import DomesticRealtimeFixture
from stock_risk_mcp.market_discovery_models import MarketDiscoveryClassification
from stock_risk_mcp.models import StrictModel
from stock_risk_mcp.strategy_track_models import StrategyTrack


def aware(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("timestamp must include timezone")
    return value


DOMESTIC_SCANNER_METADATA = {
    "domestic_scanner_fixture_run": True,
    "strategy_track_required": True,
    "domestic_kr_only": True,
    "market_profile_resolved": True,
    "normalized_realtime_event_consumed": True,
    "scanner_candidate_report_generated": True,
    "kiwoom_api_called": False,
    "broker_api_called": False,
    "credentials_accessed": False,
    "external_network_calls": False,
    "orders_created": False,
    "live_or_prod_used": False,
    "cloud_llm_called": False,
    "local_model_runtime_called": False,
}


class ScannerCandidateState(StrEnum):
    SCANNER_READY = "SCANNER_READY"
    REPORT_ONLY_STALE = "REPORT_ONLY_STALE"
    BLOCKED_QUALITY = "BLOCKED_QUALITY"
    WATCHLIST_ADD = "WATCHLIST_ADD"
    WATCHLIST_REMOVE = "WATCHLIST_REMOVE"
    INSUFFICIENT_DATA = "INSUFFICIENT_DATA"
    REJECTED_NON_DOMESTIC = "REJECTED_NON_DOMESTIC"
    REJECTED_UNSAFE_TRIGGER = "REJECTED_UNSAFE_TRIGGER"


class ScannerDiscoveryCompatibility(StrEnum):
    DISCOVER = MarketDiscoveryClassification.DISCOVER.value
    WATCH = MarketDiscoveryClassification.WATCH.value
    EXCLUDE = MarketDiscoveryClassification.EXCLUDE.value


class RealtimeScannerConfig(StrictModel):
    config_id: str = Field(..., min_length=1)
    strategy_track: StrategyTrack
    report_only_mode: bool = False
    volume_spike_ratio_threshold: float = Field(..., gt=0)
    price_momentum_pct_threshold: float = Field(..., gt=0)
    max_spread_pct: float = Field(..., gt=0)
    min_bid_ask_size: float = Field(..., gt=0)
    watchlist_add_score_threshold: int = Field(..., ge=0, le=100)
    watchlist_remove_score_threshold: int = Field(..., ge=0, le=100)
    candidate_mapping_policy: str = Field(..., min_length=1)
    compatibility_mapping_policy: str = Field(..., min_length=1)

    @field_validator("config_id", "candidate_mapping_policy", "compatibility_mapping_policy")
    @classmethod
    def normalize_text(cls, value: str) -> str:
        return value.strip().upper()


class ScannerInputSnapshot(StrictModel):
    snapshot_id: str
    strategy_track: StrategyTrack
    provider_id: str
    symbol: str
    event_type: str
    price: float | None = None
    volume: float | None = None
    best_bid: float | None = None
    best_ask: float | None = None
    bid_size: float | None = None
    ask_size: float | None = None
    volume_spike_ratio: float | None = None
    freshness_status: str
    report_only: bool
    preserved_quality_flags: list[str] = Field(default_factory=list)
    fixture_source_marker: str


class VolumeSpikeSignal(StrictModel):
    symbol: str
    observed_volume: float | None = None
    baseline_volume: float | None = None
    spike_ratio: float | None = None
    threshold: float
    signal_pass: bool
    freshness_status: str
    quality_flags: list[str] = Field(default_factory=list)


class PriceMomentumSignal(StrictModel):
    symbol: str
    recent_price: float | None = None
    reference_price: float | None = None
    price_change_pct: float | None = None
    threshold: float
    direction: str
    signal_pass: bool
    quality_flags: list[str] = Field(default_factory=list)


class LiquiditySignal(StrictModel):
    symbol: str
    best_bid: float | None = None
    best_ask: float | None = None
    spread_pct: float | None = None
    bid_size: float | None = None
    ask_size: float | None = None
    signal_pass: bool
    quality_flags: list[str] = Field(default_factory=list)


class ScannerDataQualityGate(StrictModel):
    freshness_gate: str
    completeness_gate: str
    unsafe_trigger_gate: str
    report_only_downgrade_gate: str
    preserved_quality_flags: list[str] = Field(default_factory=list)
    decision_outcome: str


class ScannerSafetyBoundary(StrictModel):
    advisory_only: bool = True
    trade_approval_allowed: bool = False
    order_creation_allowed: bool = False
    order_intent_allowed: bool = False
    order_draft_allowed: bool = False
    execution_approval_allowed: bool = False
    live_or_prod_allowed: bool = False
    broker_access_allowed: bool = False
    network_access_allowed: bool = False


class ScannerCandidate(StrictModel):
    candidate_id: str
    snapshot_id: str
    symbol: str
    internal_state: ScannerCandidateState
    compatibility_discovery_status: ScannerDiscoveryCompatibility
    candidate_reason_codes: list[str] = Field(default_factory=list)
    block_reasons: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    preserved_quality_flags: list[str] = Field(default_factory=list)
    volume_spike_signal: VolumeSpikeSignal
    price_momentum_signal: PriceMomentumSignal
    liquidity_signal: LiquiditySignal
    quality_gate: ScannerDataQualityGate
    watchlist_intent: str
    technical_setup_summary: str | None = None
    technical_indicator_markers: list[str] = Field(default_factory=list)
    setup_grade: str | None = None
    evidence_freshness: str | None = None
    profitability_context_summary: dict = Field(default_factory=dict)
    supported_tracks: list[str] = Field(default_factory=list)
    prompt_pack_context_marker: str | None = None
    advisory_context_allowed: bool = True
    actionable_approval: bool = False


class WatchlistUpdatePlan(StrictModel):
    schema_version: str = "4.3-domestic-scanner-watchlist-plan"
    plan_id: str
    strategy_track: StrategyTrack
    additions: list[str] = Field(default_factory=list)
    removals: list[str] = Field(default_factory=list)
    retained_symbols: list[str] = Field(default_factory=list)
    blocked_symbols: list[str] = Field(default_factory=list)
    report_only_symbols: list[str] = Field(default_factory=list)
    plan_reason_codes: list[str] = Field(default_factory=list)
    source_candidate_ids: list[str] = Field(default_factory=list)
    metadata_json: dict = Field(default_factory=lambda: dict(DOMESTIC_SCANNER_METADATA))


class ScannerDecisionReport(StrictModel):
    schema_version: str = "4.3-domestic-scanner-report"
    report_id: str
    strategy_track: StrategyTrack
    market_profile_summary: dict = Field(default_factory=dict)
    provider_profile_summary: dict = Field(default_factory=dict)
    candidate_count: int = Field(..., ge=0)
    ready_count: int = Field(..., ge=0)
    watchlist_add_count: int = Field(..., ge=0)
    watchlist_remove_count: int = Field(..., ge=0)
    blocked_count: int = Field(..., ge=0)
    report_only_count: int = Field(..., ge=0)
    compatibility_decision_counts: dict[str, int] = Field(default_factory=dict)
    warnings: list[str] = Field(default_factory=list)
    block_reasons: list[str] = Field(default_factory=list)
    candidates: list[ScannerCandidate] = Field(default_factory=list)
    watchlist_update_plan: WatchlistUpdatePlan | None = None
    metadata_json: dict = Field(default_factory=lambda: dict(DOMESTIC_SCANNER_METADATA))


class ScannerConfigValidationReport(StrictModel):
    schema_version: str = "4.3-domestic-scanner-validation-report"
    config_id: str
    strategy_track: StrategyTrack
    provider_id: str
    market_id: str
    metadata_json: dict = Field(default_factory=lambda: dict(DOMESTIC_SCANNER_METADATA))


class TechnicalContext(StrictModel):
    technical_setup_summary: str | None = None
    indicator_markers: list[str] = Field(default_factory=list)
    setup_grade: str | None = None
    evidence_freshness: str | None = None


class ProfitabilityContext(StrictModel):
    profitability_context_status: str = Field(..., min_length=1)
    track_aware_profitability_check: str | None = None
    expected_net_profit_pct: float | None = None
    break_even_move_pct: float | None = None
    cost_aware_minimum_target_move_pct: float | None = None

    @field_validator("profitability_context_status")
    @classmethod
    def normalize_status(cls, value: str) -> str:
        return value.strip().upper()


class AdvisoryContext(StrictModel):
    supported_tracks: list[str] = Field(default_factory=list)
    prompt_pack_context_marker: str | None = None
    supports_report_only_mode: bool = False


class DomesticScannerFixture(StrictModel):
    schema_version: str
    run_id: str = Field(..., min_length=1)
    created_at: datetime
    scanner_config: RealtimeScannerConfig
    domestic_realtime_fixture: DomesticRealtimeFixture
    technical_context: TechnicalContext = Field(default_factory=TechnicalContext)
    profitability_context: ProfitabilityContext
    advisory_context: AdvisoryContext
    _created = field_validator("created_at")(aware)

    @field_validator("schema_version")
    @classmethod
    def exact_schema(cls, value: str) -> str:
        if value != "4.3-domestic-scanner-fixture":
            raise ValueError("schema_version must be exactly 4.3-domestic-scanner-fixture")
        return value

    @model_validator(mode="after")
    def validate_domestic_only(self):
        if self.scanner_config.strategy_track != StrategyTrack.DOMESTIC_KR:
            raise ValueError("domestic scanner fixture requires StrategyTrack DOMESTIC_KR")
        if self.domestic_realtime_fixture.strategy_request.strategy_track != StrategyTrack.DOMESTIC_KR:
            raise ValueError("domestic realtime fixture must be DOMESTIC_KR")
        if self.domestic_realtime_fixture.strategy_request.market_profile.market_id != "KRX":
            raise ValueError("market_profile must resolve to KRX")
        if self.domestic_realtime_fixture.provider_profile.provider_id == "KIWOOM" and self.domestic_realtime_fixture.provider_profile.strategy_track != StrategyTrack.DOMESTIC_KR:
            raise ValueError("KIWOOM must remain DOMESTIC_KR only")
        return self
