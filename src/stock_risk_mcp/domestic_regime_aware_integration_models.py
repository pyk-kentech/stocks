from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from pydantic import Field, field_validator, model_validator

from stock_risk_mcp.domestic_market_regime_models import (
    MarketRegimeClassification,
    MarketRegimeEvidenceStrengthBucket,
    MarketRegimeLabel,
    MarketRegimeReport,
)
from stock_risk_mcp.models import StrictModel
from stock_risk_mcp.strategy_track_models import StrategyTrack


def aware(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("timestamp must include timezone")
    return value


DOMESTIC_REGIME_AWARE_INTEGRATION_METADATA = {
    "domestic_regime_aware_integration_fixture_run": True,
    "strategy_track_required": True,
    "domestic_kr_only": True,
    "market_profile_resolved": True,
    "market_regime_report_consumed": True,
    "regime_aware_context_reference_generated": True,
    "regime_aware_integration_report_generated": True,
    "regime_aware_gap_report_generated": True,
    "regime_context_non_executable": True,
    "report_only_integration_mode_supported": True,
    "missing_regime_report_fails_closed_by_default": True,
    "downstream_sub_context_sections_required": True,
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
    "ml_training_run": False,
    "real_market_data_fetched": False,
    "prompt_pack_executed": False,
    "prompt_stub_executed": False,
}


UNSAFE_EXECUTION_PATTERNS = (
    "BUY",
    "SELL",
    "ENTRY",
    "EXIT",
    "ORDER",
    "EXECUTE",
    "TRADE_APPROVED",
)


class RegimeAwareGapCategory(StrEnum):
    MISSING_MARKET_REGIME_REPORT = "MISSING_MARKET_REGIME_REPORT"
    MISSING_REGIME_CLASSIFICATION = "MISSING_REGIME_CLASSIFICATION"
    MISSING_PRIMARY_REGIME_LABEL = "MISSING_PRIMARY_REGIME_LABEL"
    STALE_REGIME_CONTEXT = "STALE_REGIME_CONTEXT"
    REPORT_ONLY_REGIME_CONTEXT = "REPORT_ONLY_REGIME_CONTEXT"
    INSUFFICIENT_REGIME_COVERAGE = "INSUFFICIENT_REGIME_COVERAGE"
    REGIME_CONTEXT_TRACK_MISMATCH = "REGIME_CONTEXT_TRACK_MISMATCH"
    REGIME_CONTEXT_MARKET_PROFILE_MISMATCH = "REGIME_CONTEXT_MARKET_PROFILE_MISMATCH"
    UNSUPPORTED_TRACK = "UNSUPPORTED_TRACK"
    EXECUTABLE_WORDING_DETECTED = "EXECUTABLE_WORDING_DETECTED"
    UNSAFE_TRIGGER_DETECTED = "UNSAFE_TRIGGER_DETECTED"


class RegimeAwareIntegrationConfig(StrictModel):
    config_id: str = Field(..., min_length=1)
    strategy_track: StrategyTrack
    market_profile_id: str = Field(..., min_length=1)
    explicit_regime_aware_integration_opt_in: bool
    report_only_integration_mode: bool = False
    stale_regime_context_policy: str = Field(..., min_length=1)
    missing_regime_report_policy: str = Field(..., min_length=1)
    coverage_sufficiency_mode: str = Field(..., min_length=1)
    wording_validation_mode: str = Field(..., min_length=1)
    non_executable_enforcement_mode: str = Field(..., min_length=1)
    non_executable: bool
    orders_created: bool
    order_intent_created: bool
    order_drafts_created: bool
    execution_approval_enabled: bool
    cloud_llm_called: bool
    model_runtime_called: bool
    ml_training_run: bool
    real_market_data_fetched: bool
    prompt_pack_executed: bool
    prompt_stub_executed: bool

    @field_validator(
        "config_id",
        "market_profile_id",
        "stale_regime_context_policy",
        "missing_regime_report_policy",
        "coverage_sufficiency_mode",
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
            raise ValueError("regime-aware integration config requires StrategyTrack DOMESTIC_KR")
        if self.market_profile_id != "KRX":
            raise ValueError("regime-aware integration config requires market_profile_id KRX")
        if not self.explicit_regime_aware_integration_opt_in:
            raise ValueError("explicit regime-aware integration opt-in is required")
        return self


class RegimeAwareBaseSection(StrictModel):
    section_id: str = Field(..., min_length=1)
    source_artifact_ids: list[str] = Field(default_factory=list)
    has_regime_attachment: bool
    non_actionable: bool = True

    @field_validator("section_id", mode="before")
    @classmethod
    def normalize_id(cls, value):
        return str(value).strip()

    @field_validator("source_artifact_ids", mode="before")
    @classmethod
    def normalize_ids(cls, values):
        cleaned = [str(value).strip() for value in values]
        if any(not value for value in cleaned):
            raise ValueError("source_artifact_ids must not contain blank values")
        return cleaned


class RegimeAwareCandidateEvaluationContext(RegimeAwareBaseSection):
    watch_only_reason_count: int = Field(..., ge=0)
    blocked_reason_count: int = Field(..., ge=0)
    report_only_reason_count: int = Field(..., ge=0)
    primary_regime_label: MarketRegimeLabel | None = None
    secondary_regime_labels: list[MarketRegimeLabel] = Field(default_factory=list)
    evidence_strength_bucket: MarketRegimeEvidenceStrengthBucket | None = None
    data_quality_flags: list[str] = Field(default_factory=list)
    report_only: bool = False


class RegimeAwareReplayContext(RegimeAwareBaseSection):
    replay_window_ids: list[str] = Field(default_factory=list)
    grouped_metric_counts: dict = Field(default_factory=dict)
    regime_report_id: str | None = None
    primary_regime_label: MarketRegimeLabel | None = None
    secondary_regime_labels: list[MarketRegimeLabel] = Field(default_factory=list)
    evidence_strength_bucket: MarketRegimeEvidenceStrengthBucket | None = None
    stale_regime_context: bool = False
    report_only: bool = False


class RegimeAwareCalibrationContext(RegimeAwareBaseSection):
    candidates_generated_by_regime: dict = Field(default_factory=dict)
    blocked_candidates_by_regime: dict = Field(default_factory=dict)
    report_only_candidates_by_regime: dict = Field(default_factory=dict)
    coverage_by_regime: dict = Field(default_factory=dict)


class RegimeAwarePaperShadowContext(RegimeAwareBaseSection):
    journal_entry_ids: list[str] = Field(default_factory=list)
    candidate_ids: list[str] = Field(default_factory=list)
    regime_context_marker: str = Field(..., min_length=1)

    @field_validator("journal_entry_ids", "candidate_ids", mode="before")
    @classmethod
    def normalize_ids(cls, values):
        cleaned = [str(value).strip() for value in values]
        if any(not value for value in cleaned):
            raise ValueError("paper-shadow ids must not contain blank values")
        return cleaned


class RegimeAwareOutcomeReviewContext(RegimeAwareBaseSection):
    favorable_count_by_regime: dict = Field(default_factory=dict)
    adverse_count_by_regime: dict = Field(default_factory=dict)
    neutral_count_by_regime: dict = Field(default_factory=dict)
    inconclusive_count_by_regime: dict = Field(default_factory=dict)
    report_only_count_by_regime: dict = Field(default_factory=dict)
    blocked_confirmed_count_by_regime: dict = Field(default_factory=dict)
    insufficient_data_count_by_regime: dict = Field(default_factory=dict)


class RegimeAwareAdvisoryContext(RegimeAwareBaseSection):
    regime_distribution_summary: dict = Field(default_factory=dict)
    outcome_label_summary_by_regime: dict = Field(default_factory=dict)
    blocked_report_only_non_actionable_summary_by_regime: dict = Field(default_factory=dict)
    data_quality_summary_by_regime: dict = Field(default_factory=dict)
    deterministic_regime_summary: str = Field(..., min_length=1)


class RegimeAwareDistillationContext(RegimeAwareBaseSection):
    primary_regime_label_feature: MarketRegimeLabel
    secondary_regime_label_features: list[MarketRegimeLabel] = Field(default_factory=list)
    regime_evidence_strength_feature: MarketRegimeEvidenceStrengthBucket
    regime_data_quality_feature: list[str] = Field(default_factory=list)
    regime_report_only_marker: bool
    regime_stale_marker: bool
    regime_conditioned_label_distribution_metadata: dict = Field(default_factory=dict)
    training_only: bool = True


class RegimeAwareContextReference(StrictModel):
    context_reference_id: str
    source_market_regime_report_id: str | None = None
    source_market_regime_classification_id: str | None = None
    primary_regime_label: MarketRegimeLabel
    secondary_regime_labels: list[MarketRegimeLabel] = Field(default_factory=list)
    evidence_strength_bucket: MarketRegimeEvidenceStrengthBucket
    data_quality_flags: list[str] = Field(default_factory=list)
    stale_evidence_summary: dict = Field(default_factory=dict)
    missing_evidence_summary: dict = Field(default_factory=dict)
    report_only: bool = False
    non_executable: bool = True
    strategy_track: StrategyTrack
    market_profile_id: str
    source_trace_references: list[str] = Field(default_factory=list)


class RegimeAwareInputSet(StrictModel):
    input_set_id: str = Field(..., min_length=1)
    strategy_track: StrategyTrack
    market_profile_summary: dict = Field(default_factory=dict)
    market_regime_report: MarketRegimeReport | None = None
    market_regime_classification: MarketRegimeClassification | None = None
    primary_regime_label: MarketRegimeLabel
    secondary_regime_labels: list[MarketRegimeLabel] = Field(default_factory=list)
    evidence_strength_bucket: MarketRegimeEvidenceStrengthBucket
    data_quality_flags: list[str] = Field(default_factory=list)
    missing_evidence_summary: dict = Field(default_factory=dict)
    stale_evidence_summary: dict = Field(default_factory=dict)
    report_only: bool = False
    source_trace_references: list[str] = Field(default_factory=list)
    candidate_evaluation_context: RegimeAwareCandidateEvaluationContext
    replay_context: RegimeAwareReplayContext
    calibration_context: RegimeAwareCalibrationContext
    paper_shadow_context: RegimeAwarePaperShadowContext
    outcome_review_context: RegimeAwareOutcomeReviewContext
    advisory_context: RegimeAwareAdvisoryContext
    distillation_context: RegimeAwareDistillationContext

    @field_validator("input_set_id", mode="before")
    @classmethod
    def normalize_id(cls, value):
        return str(value).strip()

    @field_validator("data_quality_flags", "source_trace_references", mode="before")
    @classmethod
    def normalize_lists(cls, values):
        cleaned = [str(value).strip().upper() for value in values]
        if any(not value for value in cleaned):
            raise ValueError("list values must not contain blank values")
        return cleaned

    @model_validator(mode="after")
    def validate_domestic_only(self):
        if self.strategy_track != StrategyTrack.DOMESTIC_KR:
            raise ValueError("regime-aware integration input set requires StrategyTrack DOMESTIC_KR")
        if str(self.market_profile_summary.get("market_id", "")).upper() != "KRX":
            raise ValueError("market_profile must resolve to KRX")
        if {"UNSAFE_TRIGGER_ATTEMPT", "ORDER_TRIGGER_ATTEMPT"} & set(self.data_quality_flags):
            raise ValueError("unsafe trigger attempt is not allowed in regime-aware integration fixtures")
        return self


class RegimeAwareIntegrationReport(StrictModel):
    schema_version: str = "4.12-domestic-regime-aware-integration-report"
    integration_report_id: str
    fixture_id: str
    strategy_track: StrategyTrack
    market_profile_id: str
    source_market_regime_report_id: str | None = None
    source_market_regime_classification_id: str | None = None
    primary_regime_label: MarketRegimeLabel
    secondary_regime_labels: list[MarketRegimeLabel] = Field(default_factory=list)
    evidence_strength_bucket: MarketRegimeEvidenceStrengthBucket
    data_quality_flags: list[str] = Field(default_factory=list)
    report_only: bool = False
    non_executable: bool = True
    candidate_evaluation_context: RegimeAwareCandidateEvaluationContext
    replay_context: RegimeAwareReplayContext
    calibration_context: RegimeAwareCalibrationContext
    paper_shadow_context: RegimeAwarePaperShadowContext
    outcome_review_context: RegimeAwareOutcomeReviewContext
    advisory_context: RegimeAwareAdvisoryContext
    distillation_context: RegimeAwareDistillationContext
    gap_report_id: str
    safety_report_id: str
    source_trace_references: list[str] = Field(default_factory=list)
    context_reference: RegimeAwareContextReference
    metadata_json: dict = Field(default_factory=lambda: dict(DOMESTIC_REGIME_AWARE_INTEGRATION_METADATA))


class RegimeAwareGapReport(StrictModel):
    schema_version: str = "4.12-domestic-regime-aware-gap-report"
    report_id: str
    fixture_id: str
    strategy_track: StrategyTrack
    market_profile_id: str
    gap_categories: list[str] = Field(default_factory=list)
    missing_regime_context_count: int = Field(..., ge=0)
    stale_regime_context_count: int = Field(..., ge=0)
    coverage_failure_count: int = Field(..., ge=0)
    wording_violation_count: int = Field(..., ge=0)
    unsupported_track_count: int = Field(..., ge=0)
    metadata_json: dict = Field(default_factory=lambda: dict(DOMESTIC_REGIME_AWARE_INTEGRATION_METADATA))


class RegimeAwareSafetyBoundary(StrictModel):
    context_only: bool = True
    non_executable_only: bool = True
    order_creation_allowed: bool = False
    order_intent_creation_allowed: bool = False
    order_draft_creation_allowed: bool = False
    execution_approval_allowed: bool = False
    cloud_llm_allowed: bool = False
    model_runtime_allowed: bool = False
    ml_training_allowed: bool = False
    live_or_prod_allowed: bool = False


class RegimeAwareSafetyReport(StrictModel):
    schema_version: str = "4.12-domestic-regime-aware-safety-report"
    report_id: str
    strategy_track: StrategyTrack
    safety_boundary: RegimeAwareSafetyBoundary
    warnings: list[str] = Field(default_factory=list)
    block_reasons: list[str] = Field(default_factory=list)
    metadata_json: dict = Field(default_factory=lambda: dict(DOMESTIC_REGIME_AWARE_INTEGRATION_METADATA))


class DomesticRegimeAwareIntegrationFixture(StrictModel):
    schema_version: str
    fixture_id: str = Field(..., min_length=1)
    created_at: datetime
    regime_aware_integration_config: RegimeAwareIntegrationConfig
    regime_aware_input_set: RegimeAwareInputSet
    _created = field_validator("created_at")(aware)

    @field_validator("schema_version")
    @classmethod
    def exact_schema(cls, value: str) -> str:
        if value != "4.12-domestic-regime-aware-integration-fixture":
            raise ValueError("schema_version must be exactly 4.12-domestic-regime-aware-integration-fixture")
        return value

    @model_validator(mode="after")
    def validate_fixture(self):
        if self.regime_aware_integration_config.strategy_track != StrategyTrack.DOMESTIC_KR:
            raise ValueError("domestic regime-aware integration fixture requires StrategyTrack DOMESTIC_KR")
        if self.regime_aware_input_set.strategy_track != StrategyTrack.DOMESTIC_KR:
            raise ValueError("regime-aware integration input set must be DOMESTIC_KR")
        if str(self.regime_aware_input_set.market_profile_summary.get("market_id", "")).upper() != "KRX":
            raise ValueError("market_profile must resolve to KRX")
        return self
