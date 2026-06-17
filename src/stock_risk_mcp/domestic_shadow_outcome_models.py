from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from pydantic import Field, field_validator, model_validator

from stock_risk_mcp.domestic_paper_shadow_models import (
    PaperShadowDecision,
    PaperShadowDecisionJournal,
    PaperShadowDecisionType,
)
from stock_risk_mcp.models import StrictModel
from stock_risk_mcp.strategy_track_models import StrategyTrack


def aware(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("timestamp must include timezone")
    return value


DOMESTIC_SHADOW_OUTCOME_METADATA = {
    "domestic_shadow_outcome_fixture_run": True,
    "strategy_track_required": True,
    "domestic_kr_only": True,
    "market_profile_resolved": True,
    "paper_shadow_journal_consumed": True,
    "outcome_fixture_consumed": True,
    "outcome_labels_generated": True,
    "outcome_review_report_generated": True,
    "outcome_labels_non_executable": True,
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
}


class PaperShadowOutcomeLabelType(StrEnum):
    OUTCOME_FAVORABLE = "OUTCOME_FAVORABLE"
    OUTCOME_ADVERSE = "OUTCOME_ADVERSE"
    OUTCOME_NEUTRAL = "OUTCOME_NEUTRAL"
    OUTCOME_INCONCLUSIVE = "OUTCOME_INCONCLUSIVE"
    OUTCOME_BLOCKED_CONFIRMED = "OUTCOME_BLOCKED_CONFIRMED"
    OUTCOME_REPORT_ONLY = "OUTCOME_REPORT_ONLY"
    OUTCOME_INSUFFICIENT_DATA = "OUTCOME_INSUFFICIENT_DATA"
    OUTCOME_REJECTED_SAFETY = "OUTCOME_REJECTED_SAFETY"


class ShadowOutcomeConfig(StrictModel):
    config_id: str = Field(..., min_length=1)
    strategy_track: StrategyTrack
    market_profile_id: str = Field(..., min_length=1)
    explicit_shadow_outcome_opt_in: bool
    report_only_preservation_mode: str = Field(..., min_length=1)
    blocked_context_preservation_mode: str = Field(..., min_length=1)
    inconclusive_labeling_mode: str = Field(..., min_length=1)
    aggregation_mode: str = Field(..., min_length=1)

    @field_validator(
        "config_id",
        "market_profile_id",
        "report_only_preservation_mode",
        "blocked_context_preservation_mode",
        "inconclusive_labeling_mode",
        "aggregation_mode",
    )
    @classmethod
    def normalize_text(cls, value: str) -> str:
        return value.strip().upper()

    @model_validator(mode="after")
    def validate_domestic_only(self):
        if self.strategy_track != StrategyTrack.DOMESTIC_KR:
            raise ValueError("shadow outcome config requires StrategyTrack DOMESTIC_KR")
        if not self.explicit_shadow_outcome_opt_in:
            raise ValueError("explicit shadow-outcome opt-in is required")
        if self.market_profile_id != "KRX":
            raise ValueError("shadow outcome config requires market_profile_id KRX")
        return self


class ShadowOutcomeInputSet(StrictModel):
    input_set_id: str = Field(..., min_length=1)
    strategy_track: StrategyTrack
    market_profile_summary: dict = Field(default_factory=dict)
    paper_shadow_journal: PaperShadowDecisionJournal
    promotion_gate_context_reference: str = Field(..., min_length=1)
    replay_window_references: list[str] = Field(..., min_length=1)
    scenario_family_markers: list[str] = Field(..., min_length=1)
    advisory_context_markers: list[str] = Field(default_factory=list)

    @field_validator("input_set_id", "promotion_gate_context_reference")
    @classmethod
    def normalize_text(cls, value: str) -> str:
        return value.strip()

    @field_validator("replay_window_references", "scenario_family_markers", "advisory_context_markers", mode="before")
    @classmethod
    def normalize_list(cls, values):
        cleaned = [str(value).strip().upper() for value in values]
        if any(not value for value in cleaned):
            raise ValueError("list values must not be blank")
        return cleaned

    @model_validator(mode="after")
    def validate_inputs(self):
        if self.strategy_track != StrategyTrack.DOMESTIC_KR:
            raise ValueError("shadow outcome input set requires StrategyTrack DOMESTIC_KR")
        market_id = str(self.market_profile_summary.get("market_id", "")).upper()
        if market_id != "KRX":
            raise ValueError("market_profile must resolve to KRX")
        if self.paper_shadow_journal.strategy_track != StrategyTrack.DOMESTIC_KR:
            raise ValueError("paper_shadow_journal must be DOMESTIC_KR")
        if self.paper_shadow_journal.entry_count <= 0 or not self.paper_shadow_journal.entries:
            raise ValueError("paper_shadow_journal entries are required")
        return self


class OutcomeObservationWindow(StrictModel):
    window_id: str = Field(..., min_length=1)
    start_timestamp: datetime
    end_timestamp: datetime
    horizon_label: str = Field(..., min_length=1)
    minimum_point_count: int = Field(..., ge=1)
    expected_cadence: str = Field(..., min_length=1)
    stale_tolerance_seconds: int = Field(..., ge=0)
    _start = field_validator("start_timestamp")(aware)
    _end = field_validator("end_timestamp")(aware)

    @field_validator("window_id", "horizon_label", "expected_cadence")
    @classmethod
    def normalize_text(cls, value: str) -> str:
        return value.strip().upper()

    @model_validator(mode="after")
    def validate_ordering(self):
        if self.end_timestamp <= self.start_timestamp:
            raise ValueError("impossible timestamp ordering in observation_window")
        return self


class OutcomePoint(StrictModel):
    timestamp: datetime
    price: float | None = None
    volume: float | None = None
    _timestamp = field_validator("timestamp")(aware)

    @model_validator(mode="after")
    def validate_non_negative(self):
        if self.price is not None and self.price < 0:
            raise ValueError("price must not be negative")
        if self.volume is not None and self.volume < 0:
            raise ValueError("volume must not be negative")
        return self


class ShadowOutcomeFixture(StrictModel):
    fixture_id: str = Field(..., min_length=1)
    strategy_track: StrategyTrack
    market_profile_id: str = Field(..., min_length=1)
    source_paper_shadow_journal_id: str = Field(..., min_length=1)
    source_paper_shadow_decision_id: str = Field(..., min_length=1)
    candidate_id: str = Field(..., min_length=1)
    symbol: str = Field(..., min_length=1)
    fixture_timestamp: datetime
    observation_window: OutcomeObservationWindow
    reference_price: float = Field(..., gt=0)
    future_points: list[OutcomePoint] = Field(..., min_length=1)
    benchmark_points: list[OutcomePoint] = Field(default_factory=list)
    data_quality_flags: list[str] = Field(default_factory=list)
    scenario_family: str = Field(..., min_length=1)
    replay_window_id: str = Field(..., min_length=1)
    promotion_gate_status: str = Field(..., min_length=1)
    _ts = field_validator("fixture_timestamp")(aware)

    @field_validator(
        "fixture_id",
        "source_paper_shadow_journal_id",
        "source_paper_shadow_decision_id",
        "candidate_id",
        "symbol",
    )
    @classmethod
    def normalize_identifier(cls, value: str) -> str:
        return value.strip()

    @field_validator(
        "market_profile_id",
        "scenario_family",
        "replay_window_id",
        "promotion_gate_status",
    )
    @classmethod
    def normalize_code(cls, value: str) -> str:
        return value.strip().upper()

    @field_validator("data_quality_flags", mode="before")
    @classmethod
    def normalize_flags(cls, values):
        cleaned = [str(item).strip().upper() for item in values]
        if any(not item for item in cleaned):
            raise ValueError("data_quality_flags must not contain blank values")
        if {"ORDER_TRIGGER_ATTEMPT", "UNSAFE_TRIGGER_ATTEMPT"} & set(cleaned):
            raise ValueError("unsafe trigger attempt is not allowed in outcome fixtures")
        return cleaned

    @model_validator(mode="after")
    def validate_fixture(self):
        if self.strategy_track != StrategyTrack.DOMESTIC_KR:
            raise ValueError("shadow outcome fixture requires StrategyTrack DOMESTIC_KR")
        if self.market_profile_id != "KRX":
            raise ValueError("shadow outcome fixture requires market_profile_id KRX")
        if self.fixture_timestamp < self.observation_window.start_timestamp:
            raise ValueError("fixture_timestamp must not be earlier than observation_window start")
        return self


class OutcomeLabelPolicy(StrictModel):
    policy_id: str = Field(..., min_length=1)
    favorable_threshold_pct: float = Field(..., ge=0)
    adverse_threshold_pct: float = Field(..., ge=0)
    neutral_band_pct: float = Field(..., ge=0)
    minimum_point_count: int = Field(..., ge=1)
    allow_report_only_observation_label: bool = False
    stale_data_policy: str = Field(..., min_length=1)
    threshold_precedence_rule: str = Field(..., min_length=1)
    insufficient_data_rule: str = Field(..., min_length=1)
    safety_rejection_rule: str = Field(..., min_length=1)

    @field_validator(
        "policy_id",
        "stale_data_policy",
        "threshold_precedence_rule",
        "insufficient_data_rule",
        "safety_rejection_rule",
    )
    @classmethod
    def normalize_text(cls, value: str) -> str:
        return value.strip().upper()


class PaperShadowOutcomeLabel(StrictModel):
    label_id: str
    source_paper_shadow_journal_id: str
    source_paper_shadow_decision_id: str
    candidate_id: str
    symbol: str
    strategy_track: StrategyTrack
    market_profile_id: str
    decision_type: PaperShadowDecisionType
    outcome_label: PaperShadowOutcomeLabelType
    label_rationale: str
    scenario_family: str
    replay_window_id: str
    promotion_gate_status: str
    observation_horizon: str
    maximum_favorable_observation_move: float = Field(..., ge=0)
    maximum_adverse_observation_move: float = Field(..., ge=0)
    final_observation_move: float
    observation_volatility_proxy: float = Field(..., ge=0)
    observation_volume_confirmation: bool
    threshold_touched: bool
    adverse_threshold_touched: bool
    neutral_range_marker: bool
    missing_data_marker: bool
    stale_data_marker: bool
    blocked_reasons: list[str] = Field(default_factory=list)
    report_only_reasons: list[str] = Field(default_factory=list)
    non_actionable_reasons: list[str] = Field(default_factory=list)
    data_quality_flags: list[str] = Field(default_factory=list)
    non_executable: bool = True


class PaperShadowOutcomeLabelBatch(StrictModel):
    schema_version: str = "4.8-domestic-shadow-outcome-label-batch"
    label_batch_id: str
    journal_reference: str
    label_count: int = Field(..., ge=0)
    labels: list[PaperShadowOutcomeLabel] = Field(default_factory=list)
    metadata_json: dict = Field(default_factory=lambda: dict(DOMESTIC_SHADOW_OUTCOME_METADATA))


class PaperShadowOutcomeSafetyBoundary(StrictModel):
    advisory_only: bool = True
    non_executable_only: bool = True
    order_creation_allowed: bool = False
    order_intent_allowed: bool = False
    order_draft_allowed: bool = False
    execution_approval_allowed: bool = False
    account_access_allowed: bool = False
    broker_access_allowed: bool = False
    live_or_prod_allowed: bool = False
    cloud_llm_allowed: bool = False
    model_runtime_allowed: bool = False


class PaperShadowOutcomeReviewReport(StrictModel):
    schema_version: str = "4.8-domestic-shadow-outcome-review-report"
    review_report_id: str
    journal_reference: str
    total_outcome_labels: int = Field(..., ge=0)
    favorable_count: int = Field(..., ge=0)
    adverse_count: int = Field(..., ge=0)
    neutral_count: int = Field(..., ge=0)
    inconclusive_count: int = Field(..., ge=0)
    report_only_count: int = Field(..., ge=0)
    insufficient_data_count: int = Field(..., ge=0)
    safety_rejected_count: int = Field(..., ge=0)
    blocked_confirmed_count: int = Field(..., ge=0)
    favorable_rate_among_shadow_watch_entries: float = Field(..., ge=0)
    adverse_rate_among_shadow_watch_entries: float = Field(..., ge=0)
    inconclusive_rate: float = Field(..., ge=0)
    average_maximum_favorable_observation_move: float = Field(..., ge=0)
    average_maximum_adverse_observation_move: float = Field(..., ge=0)
    scenario_family_coverage_count: int = Field(..., ge=0)
    symbol_coverage_count: int = Field(..., ge=0)
    observation_window_coverage_count: int = Field(..., ge=0)
    outcome_label_counts: dict[str, int] = Field(default_factory=dict)
    scenario_family_counts: dict[str, int] = Field(default_factory=dict)
    replay_window_counts: dict[str, int] = Field(default_factory=dict)
    symbol_counts: dict[str, int] = Field(default_factory=dict)
    decision_type_counts: dict[str, int] = Field(default_factory=dict)
    blocked_reason_counts: dict[str, int] = Field(default_factory=dict)
    report_only_reason_counts: dict[str, int] = Field(default_factory=dict)
    promotion_gate_status_counts: dict[str, int] = Field(default_factory=dict)
    observation_horizon_counts: dict[str, int] = Field(default_factory=dict)
    advisory_context_placeholders: dict = Field(default_factory=dict)
    metadata_json: dict = Field(default_factory=lambda: dict(DOMESTIC_SHADOW_OUTCOME_METADATA))


class PaperShadowOutcomeSafetyReport(StrictModel):
    schema_version: str = "4.8-domestic-shadow-outcome-safety-report"
    report_id: str
    strategy_track: StrategyTrack
    safety_boundary: PaperShadowOutcomeSafetyBoundary
    block_reasons: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    metadata_json: dict = Field(default_factory=lambda: dict(DOMESTIC_SHADOW_OUTCOME_METADATA))


class PaperShadowOutcomeGapReport(StrictModel):
    schema_version: str = "4.8-domestic-shadow-outcome-gap-report"
    gap_report_id: str
    missing_journal_entry_count: int = Field(..., ge=0)
    missing_outcome_fixture_count: int = Field(..., ge=0)
    insufficient_data_count: int = Field(..., ge=0)
    stale_data_count: int = Field(..., ge=0)
    invalid_timestamp_count: int = Field(..., ge=0)
    gap_reasons: list[str] = Field(default_factory=list)
    metadata_json: dict = Field(default_factory=lambda: dict(DOMESTIC_SHADOW_OUTCOME_METADATA))


class ShadowOutcomeValidationReport(StrictModel):
    schema_version: str = "4.8-domestic-shadow-outcome-validation-report"
    config_id: str
    strategy_track: StrategyTrack
    market_id: str
    paper_shadow_journal_id: str
    journal_entry_count: int = Field(..., ge=0)
    outcome_fixture_count: int = Field(..., ge=0)
    metadata_json: dict = Field(default_factory=lambda: dict(DOMESTIC_SHADOW_OUTCOME_METADATA))


class DomesticShadowOutcomeFixture(StrictModel):
    schema_version: str
    run_id: str = Field(..., min_length=1)
    created_at: datetime
    shadow_outcome_config: ShadowOutcomeConfig
    shadow_outcome_input_set: ShadowOutcomeInputSet
    outcome_label_policy: OutcomeLabelPolicy
    outcome_fixtures: list[ShadowOutcomeFixture] = Field(..., min_length=1)
    _created = field_validator("created_at")(aware)

    @field_validator("schema_version")
    @classmethod
    def exact_schema(cls, value: str) -> str:
        if value != "4.8-domestic-shadow-outcome-fixture":
            raise ValueError("schema_version must be exactly 4.8-domestic-shadow-outcome-fixture")
        return value

    @model_validator(mode="after")
    def validate_fixture(self):
        if self.shadow_outcome_config.strategy_track != StrategyTrack.DOMESTIC_KR:
            raise ValueError("domestic shadow outcome fixture requires StrategyTrack DOMESTIC_KR")
        if self.shadow_outcome_input_set.strategy_track != StrategyTrack.DOMESTIC_KR:
            raise ValueError("shadow outcome input set must be DOMESTIC_KR")
        market_id = str(self.shadow_outcome_input_set.market_profile_summary.get("market_id", "")).upper()
        if market_id != "KRX":
            raise ValueError("market_profile must resolve to KRX")
        journal = self.shadow_outcome_input_set.paper_shadow_journal
        journal_entries = {entry.journal_entry_id: entry for entry in journal.entries}
        if not journal_entries:
            raise ValueError("paper_shadow_journal entries are required")
        fixture_decision_ids = {item.source_paper_shadow_decision_id for item in self.outcome_fixtures}
        missing_decisions = set(journal_entries) - fixture_decision_ids
        if missing_decisions:
            raise ValueError("missing outcome fixture for paper shadow decision")
        if len(fixture_decision_ids) != len(self.outcome_fixtures):
            raise ValueError("duplicate outcome fixture decision references are not allowed")
        for item in self.outcome_fixtures:
            if item.source_paper_shadow_journal_id != journal.journal_id:
                raise ValueError("outcome fixture journal reference does not match paper_shadow_journal")
            if item.source_paper_shadow_decision_id not in journal_entries:
                raise ValueError("missing paper shadow decision reference in outcome fixture")
            if item.candidate_id != journal_entries[item.source_paper_shadow_decision_id].candidate_id:
                raise ValueError("outcome fixture candidate_id does not match paper shadow decision")
        return self


def decision_lookup(journal: PaperShadowDecisionJournal) -> dict[str, PaperShadowDecision]:
    return {entry.journal_entry_id: entry for entry in journal.entries}
