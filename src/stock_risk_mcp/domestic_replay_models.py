from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from pydantic import Field, field_validator, model_validator

from stock_risk_mcp.domestic_candidate_evaluation_models import (
    CandidateEvaluationCompatibility,
    CandidateEvaluationState,
    DomesticCandidateEvaluationFixture,
)
from stock_risk_mcp.domestic_scanner_models import (
    ScannerCandidateState,
    ScannerDiscoveryCompatibility,
)
from stock_risk_mcp.models import StrictModel
from stock_risk_mcp.strategy_track_models import StrategyTrack


def aware(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("timestamp must include timezone")
    return value


DOMESTIC_REPLAY_METADATA = {
    "domestic_replay_fixture_run": True,
    "strategy_track_required": True,
    "domestic_kr_only": True,
    "market_profile_resolved": True,
    "normalized_realtime_event_sequence_consumed": True,
    "scanner_candidate_trace_generated": True,
    "candidate_evaluation_trace_generated": True,
    "replay_metrics_report_generated": True,
    "promotion_readiness_report_generated": True,
    "kiwoom_api_called": False,
    "broker_api_called": False,
    "credentials_accessed": False,
    "external_network_calls": False,
    "orders_created": False,
    "live_or_prod_used": False,
    "cloud_llm_called": False,
    "model_runtime_called": False,
}


class ReplayOrderingPolicy(StrEnum):
    PROVIDER_TIMESTAMP_THEN_RECEIVED = "PROVIDER_TIMESTAMP_THEN_RECEIVED"
    RECEIVED_TIMESTAMP_THEN_PROVIDER = "RECEIVED_TIMESTAMP_THEN_PROVIDER"


class ReplayDuplicatePolicy(StrEnum):
    KEEP_ALL = "KEEP_ALL"
    REJECT_EXACT_DUPLICATE_EVENT_ID = "REJECT_EXACT_DUPLICATE_EVENT_ID"


class ReplayMissingTimestampPolicy(StrEnum):
    FAIL_CLOSED = "FAIL_CLOSED"


class ReplayStalePolicy(StrEnum):
    FAIL_CLOSED = "FAIL_CLOSED"
    REPORT_ONLY = "REPORT_ONLY"


class ReplayPromotionReadinessStatus(StrEnum):
    REPLAY_PASS = "REPLAY_PASS"
    REPLAY_PASS_WITH_WARNINGS = "REPLAY_PASS_WITH_WARNINGS"
    REPLAY_REPORT_ONLY = "REPLAY_REPORT_ONLY"
    REPLAY_BLOCKED_QUALITY = "REPLAY_BLOCKED_QUALITY"
    REPLAY_BLOCKED_SAFETY = "REPLAY_BLOCKED_SAFETY"
    REPLAY_INSUFFICIENT_COVERAGE = "REPLAY_INSUFFICIENT_COVERAGE"


class ReplayClockPolicy(StrictModel):
    primary_ordering_field: str = Field(..., min_length=1)
    secondary_ordering_field: str = Field(..., min_length=1)
    deterministic_tie_breaker: str = Field(..., min_length=1)
    out_of_order_handling_policy: str = Field(..., min_length=1)
    impossible_timestamp_handling_policy: str = Field(..., min_length=1)
    gap_handling_policy: str = Field(..., min_length=1)
    replay_clock_advancement_mode: str = Field(..., min_length=1)

    @field_validator(
        "primary_ordering_field",
        "secondary_ordering_field",
        "deterministic_tie_breaker",
        "out_of_order_handling_policy",
        "impossible_timestamp_handling_policy",
        "gap_handling_policy",
        "replay_clock_advancement_mode",
    )
    @classmethod
    def normalize_text(cls, value: str) -> str:
        return value.strip().upper()


class ReplayEventSequence(StrictModel):
    sequence_id: str = Field(..., min_length=1)
    ordered_event_ids: list[str] = Field(..., min_length=1)
    sequence_start_timestamp: datetime
    sequence_end_timestamp: datetime
    symbol_universe_snapshot: list[str] = Field(..., min_length=1)
    source_fixture_markers: list[str] = Field(..., min_length=1)
    _start = field_validator("sequence_start_timestamp")(aware)
    _end = field_validator("sequence_end_timestamp")(aware)

    @field_validator("ordered_event_ids", "symbol_universe_snapshot", "source_fixture_markers", mode="before")
    @classmethod
    def normalize_list(cls, values):
        cleaned = [str(value).strip().upper() for value in values]
        if any(not value for value in cleaned):
            raise ValueError("replay sequence values must not contain blanks")
        return cleaned

    @model_validator(mode="after")
    def validate_timestamps(self):
        if self.sequence_end_timestamp < self.sequence_start_timestamp:
            raise ValueError("replay window end must be after start")
        return self


class DomesticReplayConfig(StrictModel):
    config_id: str = Field(..., min_length=1)
    strategy_track: StrategyTrack
    report_only_mode: bool = False
    replay_ordering_mode: ReplayOrderingPolicy
    replay_tie_breaker_mode: str = Field(..., min_length=1)
    duplicate_event_policy: ReplayDuplicatePolicy
    missing_timestamp_policy: ReplayMissingTimestampPolicy
    stale_event_policy: ReplayStalePolicy
    report_only_event_policy: str = Field(..., min_length=1)
    replay_window_size: int = Field(..., ge=1)
    replay_metrics_policy: str = Field(..., min_length=1)
    promotion_readiness_policy: str = Field(..., min_length=1)
    replay_clock_policy: ReplayClockPolicy

    @field_validator(
        "config_id",
        "replay_tie_breaker_mode",
        "report_only_event_policy",
        "replay_metrics_policy",
        "promotion_readiness_policy",
    )
    @classmethod
    def normalize_text(cls, value: str) -> str:
        return value.strip().upper()


class ReplayQualityGate(StrictModel):
    freshness_gate: str
    completeness_gate: str
    safety_gate: str
    report_only_gate: str
    preserved_quality_flags: list[str] = Field(default_factory=list)


class ReplayCandidateTrace(StrictModel):
    source_event_ids: list[str] = Field(default_factory=list)
    scanner_input_snapshot_id: str
    scanner_candidate_id: str
    scanner_state: ScannerCandidateState
    scanner_compatibility_status: ScannerDiscoveryCompatibility
    evaluation_state: CandidateEvaluationState
    evaluation_compatibility_status: CandidateEvaluationCompatibility
    blocked_reasons: list[str] = Field(default_factory=list)
    report_only_reasons: list[str] = Field(default_factory=list)
    non_actionable_reasons: list[str] = Field(default_factory=list)
    data_quality_flags: list[str] = Field(default_factory=list)
    non_actionable: bool = True


class ReplayStepResult(StrictModel):
    replay_step_id: str
    source_event_id: str
    replay_clock_timestamp: datetime
    normalized_event_state: dict = Field(default_factory=dict)
    scanner_input_snapshot: dict = Field(default_factory=dict)
    scanner_candidate_trace: ReplayCandidateTrace
    candidate_evaluation_trace: dict = Field(default_factory=dict)
    blocked_reasons: list[str] = Field(default_factory=list)
    report_only_reasons: list[str] = Field(default_factory=list)
    non_actionable_reasons: list[str] = Field(default_factory=list)
    data_quality_flags: list[str] = Field(default_factory=list)
    _clock = field_validator("replay_clock_timestamp")(aware)


class ReplayWindow(StrictModel):
    window_id: str
    window_start: datetime
    window_end: datetime
    included_event_ids: list[str] = Field(default_factory=list)
    aggregated_summary_metrics: dict = Field(default_factory=dict)
    warnings: list[str] = Field(default_factory=list)
    block_reasons: list[str] = Field(default_factory=list)
    _start = field_validator("window_start")(aware)
    _end = field_validator("window_end")(aware)


class ReplayEvaluationMetrics(StrictModel):
    total_events_processed: int = Field(..., ge=0)
    valid_events: int = Field(..., ge=0)
    stale_events: int = Field(..., ge=0)
    invalid_events: int = Field(..., ge=0)
    generated_scanner_candidates: int = Field(..., ge=0)
    candidates_by_scanner_state: dict[str, int] = Field(default_factory=dict)
    candidates_by_evaluation_state: dict[str, int] = Field(default_factory=dict)
    blocked_candidate_count: int = Field(..., ge=0)
    report_only_candidate_count: int = Field(..., ge=0)
    watchlist_add_count: int = Field(..., ge=0)
    watchlist_remove_count: int = Field(..., ge=0)
    domestic_only_rejection_count: int = Field(..., ge=0)
    unsafe_trigger_rejection_count: int = Field(..., ge=0)
    quality_failure_count: int = Field(..., ge=0)
    profitability_blocked_count: int = Field(..., ge=0)
    technical_evidence_blocked_count: int = Field(..., ge=0)
    non_actionable_candidate_count: int = Field(..., ge=0)


class ReplaySafetyBoundary(StrictModel):
    advisory_only: bool = True
    trade_approval_allowed: bool = False
    order_creation_allowed: bool = False
    order_intent_allowed: bool = False
    order_draft_allowed: bool = False
    execution_approval_allowed: bool = False
    live_or_prod_allowed: bool = False
    broker_access_allowed: bool = False
    network_access_allowed: bool = False
    model_runtime_allowed: bool = False


class ReplayPromotionReadinessReport(StrictModel):
    schema_version: str = "4.5-domestic-replay-promotion-readiness-report"
    report_id: str
    strategy_track: StrategyTrack
    readiness_status: ReplayPromotionReadinessStatus
    coverage_event_count: int = Field(..., ge=0)
    warnings: list[str] = Field(default_factory=list)
    block_reasons: list[str] = Field(default_factory=list)
    safety_boundary: ReplaySafetyBoundary = Field(default_factory=ReplaySafetyBoundary)
    metadata_json: dict = Field(default_factory=lambda: dict(DOMESTIC_REPLAY_METADATA))


class ReplayValidationReport(StrictModel):
    schema_version: str = "4.5-domestic-replay-validation-report"
    config_id: str
    strategy_track: StrategyTrack
    market_id: str
    sequence_id: str
    event_count: int = Field(..., ge=0)
    ordering_policy: str
    metadata_json: dict = Field(default_factory=lambda: dict(DOMESTIC_REPLAY_METADATA))


class ReplayEvaluationReport(StrictModel):
    schema_version: str = "4.5-domestic-replay-evaluation-report"
    report_id: str
    strategy_track: StrategyTrack
    market_profile_summary: dict = Field(default_factory=dict)
    event_sequence_summary: dict = Field(default_factory=dict)
    step_results: list[ReplayStepResult] = Field(default_factory=list)
    windows: list[ReplayWindow] = Field(default_factory=list)
    metrics: ReplayEvaluationMetrics
    safety_boundary: ReplaySafetyBoundary = Field(default_factory=ReplaySafetyBoundary)
    warnings: list[str] = Field(default_factory=list)
    block_reasons: list[str] = Field(default_factory=list)
    metadata_json: dict = Field(default_factory=lambda: dict(DOMESTIC_REPLAY_METADATA))


class DomesticReplayFixture(StrictModel):
    schema_version: str
    run_id: str = Field(..., min_length=1)
    created_at: datetime
    replay_config: DomesticReplayConfig
    domestic_candidate_evaluation_fixture: DomesticCandidateEvaluationFixture
    replay_event_sequence: ReplayEventSequence
    _created = field_validator("created_at")(aware)

    @field_validator("schema_version")
    @classmethod
    def exact_schema(cls, value: str) -> str:
        if value != "4.5-domestic-replay-fixture":
            raise ValueError("schema_version must be exactly 4.5-domestic-replay-fixture")
        return value

    @model_validator(mode="after")
    def validate_domestic_only(self):
        if self.replay_config.strategy_track != StrategyTrack.DOMESTIC_KR:
            raise ValueError("domestic replay fixture requires StrategyTrack DOMESTIC_KR")
        eval_fixture = self.domestic_candidate_evaluation_fixture
        if eval_fixture.evaluation_config.strategy_track != StrategyTrack.DOMESTIC_KR:
            raise ValueError("domestic candidate evaluation fixture must be DOMESTIC_KR")
        market_profile = eval_fixture.domestic_scanner_fixture.domestic_realtime_fixture.strategy_request.market_profile
        if market_profile.market_id != "KRX":
            raise ValueError("market_profile must resolve to KRX")
        events = eval_fixture.domestic_scanner_fixture.domestic_realtime_fixture.events
        source_ids = {event.source_fixture_id for event in events}
        if set(self.replay_event_sequence.ordered_event_ids) != source_ids:
            raise ValueError("replay ordered_event_ids must match domestic realtime event source ids")
        if set(self.replay_event_sequence.symbol_universe_snapshot) != {event.symbol for event in events}:
            raise ValueError("symbol universe snapshot must match replay event symbols")
        return self
