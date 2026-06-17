from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from pydantic import Field, field_validator, model_validator

from stock_risk_mcp.models import StrictModel
from stock_risk_mcp.strategy_track_models import MarketProfile, StrategyTrack, StrategyTrackRequest


def aware(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("timestamp must include timezone")
    return value


DOMESTIC_REALTIME_METADATA = {
    "domestic_realtime_fixture_run": True,
    "strategy_track_required": True,
    "domestic_kr_only": True,
    "market_profile_resolved": True,
    "kiwoom_api_called": False,
    "broker_api_called": False,
    "credentials_accessed": False,
    "external_network_calls": False,
    "orders_created": False,
    "live_or_prod_used": False,
}


class RealtimeProviderStatus(StrEnum):
    SIMULATION_ONLY = "SIMULATION_ONLY"
    FUTURE_PROVIDER_CANDIDATE = "FUTURE_PROVIDER_CANDIDATE"
    NEEDS_EVIDENCE = "NEEDS_EVIDENCE"
    DISABLED = "DISABLED"


class RealtimeEventType(StrEnum):
    TRADE = "TRADE"
    QUOTE = "QUOTE"
    ORDERBOOK = "ORDERBOOK"


class RealtimeStalePolicy(StrEnum):
    FAIL_CLOSED = "FAIL_CLOSED"
    REPORT_ONLY = "REPORT_ONLY"


class RealtimeQualityStatus(StrEnum):
    READY = "READY"
    FAILED_STALE = "FAILED_STALE"
    REPORT_ONLY_STALE = "REPORT_ONLY_STALE"
    FAILED_INVALID = "FAILED_INVALID"


class RealtimeProviderProfile(StrictModel):
    provider_id: str = Field(..., min_length=1)
    strategy_track: StrategyTrack
    market_id: str = Field(..., min_length=1)
    supported_asset_types: list[str] = Field(..., min_length=1)
    provider_mode: str = Field(..., min_length=1)
    max_symbol_capacity: int = Field(..., gt=0)
    subscription_grouping: str = Field(..., min_length=1)
    event_types_supported: list[RealtimeEventType] = Field(..., min_length=1)
    normalized_field_availability: list[str] = Field(..., min_length=1)
    provider_staleness_threshold_seconds: int = Field(..., gt=0)
    received_timestamp_tolerance_seconds: int = Field(..., gt=0)
    status: RealtimeProviderStatus

    @field_validator("provider_id", "market_id", "provider_mode", "subscription_grouping")
    @classmethod
    def strip_fields(cls, value: str) -> str:
        return value.strip().upper()

    @field_validator("supported_asset_types", "normalized_field_availability", mode="before")
    @classmethod
    def normalize_list(cls, values):
        cleaned = [str(value).strip().upper() for value in values]
        if any(not value for value in cleaned):
            raise ValueError("list values must not be blank")
        return cleaned


class RealtimeSubscriptionGroup(StrictModel):
    group_id: str = Field(..., min_length=1)
    symbols: list[str] = Field(..., min_length=1)
    priority_tier: int = Field(..., ge=1)

    @field_validator("group_id")
    @classmethod
    def strip_group_id(cls, value: str) -> str:
        return value.strip()

    @field_validator("symbols", mode="before")
    @classmethod
    def normalize_symbols(cls, values):
        cleaned = [str(value).strip().upper() for value in values]
        if any(not value for value in cleaned):
            raise ValueError("symbols must not contain blank values")
        return cleaned


class RealtimeSubscriptionPlan(StrictModel):
    plan_id: str = Field(..., min_length=1)
    strategy_track: StrategyTrack
    provider_id: str = Field(..., min_length=1)
    watch_universe: str = Field(..., min_length=1)
    symbols: list[str] = Field(..., min_length=1)
    subscription_groups: list[RealtimeSubscriptionGroup] = Field(..., min_length=1)
    dynamic_add_policy: str = Field(..., min_length=1)
    dynamic_remove_policy: str = Field(..., min_length=1)
    stale_subscription_handling: str = Field(..., min_length=1)
    fallback_mode: str = Field(..., min_length=1)

    @field_validator("provider_id", "watch_universe", "dynamic_add_policy", "dynamic_remove_policy", "stale_subscription_handling", "fallback_mode")
    @classmethod
    def strip_fields(cls, value: str) -> str:
        return value.strip().upper()

    @field_validator("symbols", mode="before")
    @classmethod
    def normalize_symbols(cls, values):
        cleaned = [str(value).strip().upper() for value in values]
        if any(not value for value in cleaned):
            raise ValueError("symbols must not contain blank values")
        return cleaned


class RealtimeSubscriptionLimit(StrictModel):
    provider_id: str = Field(..., min_length=1)
    max_subscribed_symbols: int = Field(..., gt=0)
    max_groups: int = Field(..., gt=0)
    priority_tier_policy: str = Field(..., min_length=1)
    overflow_policy: str = Field(..., min_length=1)
    downgrade_policy: str = Field(..., min_length=1)
    limit_evidence: str = Field(..., min_length=1)

    @field_validator("provider_id", "priority_tier_policy", "overflow_policy", "downgrade_policy", "limit_evidence")
    @classmethod
    def strip_fields(cls, value: str) -> str:
        return value.strip().upper()


class RealtimeStalenessPolicy(StrictModel):
    default_policy: RealtimeStalePolicy
    provider_timestamp_required: bool
    received_timestamp_required: bool
    maximum_provider_to_received_lag_seconds: int = Field(..., gt=0)
    maximum_event_age_seconds: int = Field(..., gt=0)
    impossible_timestamp_rejection: bool
    timestamp_mismatch_treatment: str = Field(..., min_length=1)
    allow_report_only_downgrade: bool = False

    @field_validator("timestamp_mismatch_treatment")
    @classmethod
    def strip_fields(cls, value: str) -> str:
        return value.strip().upper()


class RealtimeMarketEvent(StrictModel):
    provider_id: str = Field(..., min_length=1)
    strategy_track: StrategyTrack
    market_id: str = Field(..., min_length=1)
    symbol: str = Field(..., min_length=1)
    event_type: RealtimeEventType
    provider_timestamp: datetime
    received_timestamp: datetime
    source_fixture_id: str = Field(..., min_length=1)
    price: float | None = Field(default=None, gt=0)
    volume: float | None = Field(default=None, ge=0)
    cumulative_volume: float | None = Field(default=None, ge=0)
    best_bid: float | None = Field(default=None, ge=0)
    best_ask: float | None = Field(default=None, ge=0)
    bid_size: float | None = Field(default=None, ge=0)
    ask_size: float | None = Field(default=None, ge=0)
    orderbook_bid_levels: list[dict] = Field(default_factory=list)
    orderbook_ask_levels: list[dict] = Field(default_factory=list)
    baseline_volume: float | None = Field(default=None, gt=0)
    data_quality_flags: list[str] = Field(default_factory=list)
    _provider = field_validator("provider_timestamp")(aware)
    _received = field_validator("received_timestamp")(aware)

    @field_validator("provider_id", "market_id", "symbol", "source_fixture_id", mode="before")
    @classmethod
    def normalize_fields(cls, value):
        return str(value).strip().upper()

    @field_validator("data_quality_flags", mode="before")
    @classmethod
    def normalize_flags(cls, values):
        cleaned = [str(value).strip().upper() for value in values]
        if any(not value for value in cleaned):
            raise ValueError("data_quality_flags must not contain blank values")
        return cleaned


class RealtimeQuoteEvent(RealtimeMarketEvent):
    pass


class RealtimeTradeEvent(RealtimeMarketEvent):
    pass


class RealtimeOrderbookEvent(RealtimeMarketEvent):
    pass


class RealtimeVolumeSpikeEvent(StrictModel):
    symbol: str
    event_timestamp: datetime
    observed_volume: float = Field(..., ge=0)
    baseline_volume: float = Field(..., gt=0)
    spike_ratio: float = Field(..., ge=0)
    supporting_price: float | None = Field(default=None, gt=0)
    quality_flags: list[str] = Field(default_factory=list)
    source_snapshot_id: str
    _timestamp = field_validator("event_timestamp")(aware)


class RealtimeScannerInputSnapshot(StrictModel):
    strategy_track: StrategyTrack
    market_profile: MarketProfile
    provider_id: str
    symbol: str
    freshness_status: str
    quality_status: RealtimeQualityStatus
    report_only: bool
    volume_spike_ratio: float | None = None


class DomesticRealtimeFixture(StrictModel):
    schema_version: str
    run_id: str = Field(..., min_length=1)
    created_at: datetime
    report_only_mode: bool = False
    strategy_request: StrategyTrackRequest
    provider_profile: RealtimeProviderProfile
    subscription_limit: RealtimeSubscriptionLimit
    subscription_plan: RealtimeSubscriptionPlan
    staleness_policy: RealtimeStalenessPolicy
    events: list[RealtimeMarketEvent] = Field(..., min_length=1)
    _created = field_validator("created_at")(aware)

    @field_validator("schema_version")
    @classmethod
    def exact_schema(cls, value: str) -> str:
        if value != "4.2-domestic-realtime-fixture":
            raise ValueError("schema_version must be exactly 4.2-domestic-realtime-fixture")
        return value

    @model_validator(mode="after")
    def validate_domestic_only(self):
        if self.strategy_request.strategy_track != StrategyTrack.DOMESTIC_KR:
            raise ValueError("domestic realtime fixture requires StrategyTrack DOMESTIC_KR")
        if self.provider_profile.strategy_track != StrategyTrack.DOMESTIC_KR:
            raise ValueError("provider profile must be DOMESTIC_KR")
        if self.strategy_request.market_profile.market_id != "KRX":
            raise ValueError("market_profile must resolve to KRX")
        if self.provider_profile.market_id != "KRX":
            raise ValueError("provider profile must resolve to KRX")
        if self.provider_profile.provider_id == "KIWOOM" and self.provider_profile.strategy_track != StrategyTrack.DOMESTIC_KR:
            raise ValueError("KIWOOM must remain DOMESTIC_KR only")
        if self.subscription_plan.strategy_track != StrategyTrack.DOMESTIC_KR:
            raise ValueError("subscription plan must be DOMESTIC_KR")
        if self.subscription_plan.provider_id != self.provider_profile.provider_id:
            raise ValueError("subscription plan provider_id must match provider profile")
        if self.subscription_limit.provider_id != self.provider_profile.provider_id:
            raise ValueError("subscription limit provider_id must match provider profile")
        for event in self.events:
            if event.strategy_track != StrategyTrack.DOMESTIC_KR:
                raise ValueError("all events must be DOMESTIC_KR")
            if event.market_id != "KRX":
                raise ValueError("all events must resolve to KRX")
        return self


class DomesticRealtimePlanReport(StrictModel):
    schema_version: str = "4.2-domestic-realtime-plan-report"
    plan_id: str
    provider_id: str
    strategy_track: StrategyTrack
    symbol_count: int
    max_subscribed_symbols: int
    limit_exceeded: bool
    fallback_applied: str
    overflow_symbols: list[str] = Field(default_factory=list)
    subscription_plan: dict = Field(default_factory=dict)
    metadata_json: dict = Field(default_factory=lambda: dict(DOMESTIC_REALTIME_METADATA))


class RealtimeDataQualityReport(StrictModel):
    schema_version: str = "4.2-domestic-realtime-quality-report"
    provider_id: str
    strategy_track: StrategyTrack
    market_id: str
    symbol_count: int = Field(..., ge=0)
    event_count: int = Field(..., ge=0)
    stale_event_count: int = Field(..., ge=0)
    invalid_timestamp_count: int = Field(..., ge=0)
    incomplete_field_count: int = Field(..., ge=0)
    dropped_event_count: int = Field(default=0, ge=0)
    quality_status: RealtimeQualityStatus
    warnings: list[str] = Field(default_factory=list)
    block_reasons: list[str] = Field(default_factory=list)
    scanner_input_snapshots: list[RealtimeScannerInputSnapshot] = Field(default_factory=list)
    metadata_json: dict = Field(default_factory=lambda: dict(DOMESTIC_REALTIME_METADATA))
