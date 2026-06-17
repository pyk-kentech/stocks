from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from pydantic import Field, field_validator, model_validator

from stock_risk_mcp.domestic_paper_shadow_models import PaperShadowDecisionJournal
from stock_risk_mcp.domestic_shadow_outcome_models import PaperShadowOutcomeReviewReport
from stock_risk_mcp.models import StrictModel
from stock_risk_mcp.offline_prompt_pack_models import AdvisoryTaskType
from stock_risk_mcp.strategy_track_models import StrategyTrack


def aware(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("timestamp must include timezone")
    return value


DOMESTIC_SHADOW_ADVISORY_CONTEXT_METADATA = {
    "domestic_shadow_advisory_context_fixture_run": True,
    "strategy_track_required": True,
    "domestic_kr_only": True,
    "market_profile_resolved": True,
    "paper_shadow_journal_consumed": True,
    "outcome_review_report_consumed": True,
    "promotion_gate_reference_consumed": True,
    "advisory_context_bundle_generated": True,
    "advisory_context_validation_generated": True,
    "advisory_context_gap_report_generated": True,
    "advisory_context_non_executable": True,
    "training_only_context_marker_present": True,
    "llm_runtime_allowed": False,
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
}


SAFE_ADVISORY_TASK_NAMES = {task.value for task in AdvisoryTaskType}
UNSAFE_EXECUTION_PATTERNS = ("BUY", "SELL", "ENTRY", "EXIT", "ORDER", "EXECUTE")
UNSAFE_EVIDENCE_ITEM_TYPES = {
    "BUY_SIGNAL",
    "SELL_SIGNAL",
    "ENTRY_SIGNAL",
    "EXIT_SIGNAL",
    "ORDER_RECOMMENDATION",
    "EXECUTION_ADVICE",
    "TRADE_APPROVAL",
    "POSITION_OPEN",
    "POSITION_CLOSE",
}


class AdvisoryContextEvidenceItemType(StrEnum):
    SHADOW_DECISION_SUMMARY = "SHADOW_DECISION_SUMMARY"
    OUTCOME_LABEL_SUMMARY = "OUTCOME_LABEL_SUMMARY"
    BLOCKED_REASON_SUMMARY = "BLOCKED_REASON_SUMMARY"
    REPORT_ONLY_REASON_SUMMARY = "REPORT_ONLY_REASON_SUMMARY"
    NON_ACTIONABLE_SUMMARY = "NON_ACTIONABLE_SUMMARY"
    SCENARIO_COVERAGE_SUMMARY = "SCENARIO_COVERAGE_SUMMARY"
    SYMBOL_COVERAGE_SUMMARY = "SYMBOL_COVERAGE_SUMMARY"
    RISK_OBSERVATION_SUMMARY = "RISK_OBSERVATION_SUMMARY"
    DATA_QUALITY_SUMMARY = "DATA_QUALITY_SUMMARY"
    GAP_SUMMARY = "GAP_SUMMARY"
    TRAINING_CONTEXT_SUMMARY = "TRAINING_CONTEXT_SUMMARY"


class AdvisoryContextGapCategory(StrEnum):
    MISSING_JOURNAL = "MISSING_JOURNAL"
    MISSING_OUTCOME_REVIEW = "MISSING_OUTCOME_REVIEW"
    MISSING_PROMOTION_GATE = "MISSING_PROMOTION_GATE"
    MISSING_MARKET_PROFILE = "MISSING_MARKET_PROFILE"
    INSUFFICIENT_SCENARIO_COVERAGE = "INSUFFICIENT_SCENARIO_COVERAGE"
    INSUFFICIENT_SYMBOL_COVERAGE = "INSUFFICIENT_SYMBOL_COVERAGE"
    INSUFFICIENT_OBSERVATION_WINDOW_COVERAGE = "INSUFFICIENT_OBSERVATION_WINDOW_COVERAGE"
    EXECUTABLE_WORDING_DETECTED = "EXECUTABLE_WORDING_DETECTED"
    UNSAFE_TRIGGER_DETECTED = "UNSAFE_TRIGGER_DETECTED"
    UNSUPPORTED_TRACK = "UNSUPPORTED_TRACK"
    ADVISORY_TASK_UNSUPPORTED = "ADVISORY_TASK_UNSUPPORTED"
    LLM_RUNTIME_NOT_ALLOWED = "LLM_RUNTIME_NOT_ALLOWED"
    MISSING_TRAINING_ONLY_MARKER = "MISSING_TRAINING_ONLY_MARKER"
    UNSAFE_EVIDENCE_ITEM_TYPE = "UNSAFE_EVIDENCE_ITEM_TYPE"


class AdvisoryContextSafetyBoundary(StrictModel):
    advisory_only: bool = True
    non_executable_only: bool = True
    order_creation_allowed: bool = False
    order_intent_allowed: bool = False
    order_draft_allowed: bool = False
    execution_approval_allowed: bool = False
    live_or_prod_allowed: bool = False
    cloud_llm_allowed: bool = False
    llm_runtime_allowed: bool = False
    local_model_runtime_called: bool = False
    prompt_pack_execution_allowed: bool = False


class AdvisoryContextEvidenceItem(StrictModel):
    evidence_item_id: str = Field(..., min_length=1)
    evidence_type: AdvisoryContextEvidenceItemType
    summary_text: str = Field(..., min_length=1)
    structured_counts: dict = Field(default_factory=dict)
    source_ids: list[str] = Field(default_factory=list)
    trace_references: list[str] = Field(default_factory=list)
    data_quality_flags: list[str] = Field(default_factory=list)
    non_executable: bool = True

    @field_validator("evidence_item_id", "summary_text")
    @classmethod
    def normalize_text(cls, value: str) -> str:
        return value.strip()


class AdvisoryContextRiskSummary(StrictModel):
    safety_rejected_count: int = Field(..., ge=0)
    blocked_confirmed_count: int = Field(..., ge=0)
    report_only_count: int = Field(..., ge=0)
    non_actionable_count: int = Field(..., ge=0)
    data_quality_flags: list[str] = Field(default_factory=list)
    summary_text: str = Field(..., min_length=1)


class AdvisoryContextOutcomeSummary(StrictModel):
    favorable_count: int = Field(..., ge=0)
    adverse_count: int = Field(..., ge=0)
    neutral_count: int = Field(..., ge=0)
    inconclusive_count: int = Field(..., ge=0)
    insufficient_data_count: int = Field(..., ge=0)
    summary_text: str = Field(..., min_length=1)


class ShadowReviewAdvisoryContextConfig(StrictModel):
    config_id: str = Field(..., min_length=1)
    strategy_track: StrategyTrack
    market_profile_id: str = Field(..., min_length=1)
    explicit_advisory_context_opt_in: bool
    supported_advisory_task_names: list[str] = Field(..., min_length=1)
    supported_tracks: list[StrategyTrack] = Field(..., min_length=1)
    report_level_bundle_mode: str = Field(..., min_length=1)
    sub_summary_inclusion_mode: str = Field(..., min_length=1)
    wording_validation_mode: str = Field(..., min_length=1)
    coverage_sufficiency_mode: str = Field(..., min_length=1)
    distillation_eligible: bool
    training_only_context: bool
    llm_training_context_allowed: bool
    llm_runtime_allowed: bool
    cloud_llm_called: bool
    local_model_runtime_called: bool
    non_executable: bool
    no_trade_instruction: bool

    @field_validator(
        "config_id",
        "market_profile_id",
        "report_level_bundle_mode",
        "sub_summary_inclusion_mode",
        "wording_validation_mode",
        "coverage_sufficiency_mode",
        mode="before",
    )
    @classmethod
    def normalize_text(cls, value):
        return str(value).strip().upper()

    @field_validator("supported_advisory_task_names", mode="before")
    @classmethod
    def normalize_task_names(cls, values):
        cleaned = [str(value).strip().upper() for value in values]
        if any(not value for value in cleaned):
            raise ValueError("supported_advisory_task_names must not contain blank values")
        return cleaned

    @model_validator(mode="after")
    def validate_domestic_only(self):
        if self.strategy_track != StrategyTrack.DOMESTIC_KR:
            raise ValueError("shadow advisory context config requires StrategyTrack DOMESTIC_KR")
        if not self.explicit_advisory_context_opt_in:
            raise ValueError("explicit advisory-context opt-in is required")
        if self.market_profile_id != "KRX":
            raise ValueError("shadow advisory context config requires market_profile_id KRX")
        if self.supported_tracks != [StrategyTrack.DOMESTIC_KR]:
            raise ValueError("supported_tracks must be exactly [DOMESTIC_KR]")
        return self


class ShadowReviewAdvisoryInputSet(StrictModel):
    input_set_id: str = Field(..., min_length=1)
    strategy_track: StrategyTrack
    market_profile_summary: dict = Field(default_factory=dict)
    paper_shadow_journal: PaperShadowDecisionJournal
    source_paper_shadow_review_report_id: str | None = None
    outcome_review_report: PaperShadowOutcomeReviewReport
    source_promotion_gate_id: str = Field(..., min_length=1)
    calibration_pack_reference: str = Field(..., min_length=1)
    scenario_family_coverage: list[str] = Field(default_factory=list)
    symbol_coverage: list[str] = Field(default_factory=list)
    observation_window_coverage: list[str] = Field(default_factory=list)
    supported_advisory_task_names: list[str] = Field(..., min_length=1)
    accepts_shadow_review_context: bool
    non_actionable_marker: bool
    training_only_context: bool
    advisory_context_markers: list[str] = Field(default_factory=list)
    data_quality_flags: list[str] = Field(default_factory=list)

    @field_validator(
        "input_set_id",
        "source_promotion_gate_id",
        "calibration_pack_reference",
        mode="before",
    )
    @classmethod
    def normalize_identifier(cls, value):
        return str(value).strip()

    @field_validator(
        "scenario_family_coverage",
        "symbol_coverage",
        "observation_window_coverage",
        "supported_advisory_task_names",
        "advisory_context_markers",
        "data_quality_flags",
        mode="before",
    )
    @classmethod
    def normalize_list(cls, values):
        cleaned = [str(value).strip().upper() for value in values]
        if any(not value for value in cleaned):
            raise ValueError("list values must not be blank")
        return cleaned

    @model_validator(mode="after")
    def validate_inputs(self):
        if self.strategy_track != StrategyTrack.DOMESTIC_KR:
            raise ValueError("shadow advisory input set requires StrategyTrack DOMESTIC_KR")
        market_id = str(self.market_profile_summary.get("market_id", "")).upper()
        if market_id != "KRX":
            raise ValueError("market_profile must resolve to KRX")
        if self.paper_shadow_journal.strategy_track != StrategyTrack.DOMESTIC_KR:
            raise ValueError("paper_shadow_journal must be DOMESTIC_KR")
        if self.paper_shadow_journal.journal_id != self.outcome_review_report.journal_reference:
            raise ValueError("outcome review report journal reference does not match paper_shadow_journal")
        journal_gate_ids = {entry.source_promotion_gate_id for entry in self.paper_shadow_journal.entries}
        if self.source_promotion_gate_id not in journal_gate_ids:
            raise ValueError("source_promotion_gate_id must match paper_shadow_journal entries")
        return self


class AdvisoryContextPolicy(StrictModel):
    policy_id: str = Field(..., min_length=1)
    allowed_evidence_item_types: list[str] = Field(..., min_length=1)
    forbidden_wording_patterns: list[str] = Field(..., min_length=1)
    deterministic_summary_length_cap: int = Field(..., ge=40, le=240)
    minimum_scenario_coverage_count: int = Field(..., ge=1)
    minimum_symbol_coverage_count: int = Field(..., ge=1)
    minimum_observation_window_coverage_count: int = Field(..., ge=1)
    supported_advisory_task_compatibility_mode: str = Field(..., min_length=1)
    non_executable_enforcement_mode: str = Field(..., min_length=1)
    gap_preservation_mode: str = Field(..., min_length=1)

    @field_validator(
        "policy_id",
        "supported_advisory_task_compatibility_mode",
        "non_executable_enforcement_mode",
        "gap_preservation_mode",
        mode="before",
    )
    @classmethod
    def normalize_text(cls, value):
        return str(value).strip().upper()

    @field_validator("allowed_evidence_item_types", "forbidden_wording_patterns", mode="before")
    @classmethod
    def normalize_list(cls, values):
        cleaned = [str(value).strip().upper() for value in values]
        if any(not value for value in cleaned):
            raise ValueError("policy lists must not contain blank values")
        return cleaned


class AdvisoryContextSectionSummary(StrictModel):
    section_key: str = Field(..., min_length=1)
    summary_text: str = Field(..., min_length=1)
    structured_counts: dict = Field(default_factory=dict)
    trace_references: list[str] = Field(default_factory=list)


class ShadowReviewAdvisoryContextBundle(StrictModel):
    schema_version: str = "4.9-domestic-shadow-advisory-context-bundle"
    bundle_id: str
    fixture_id: str
    source_outcome_review_report_id: str
    source_paper_shadow_journal_id: str
    source_promotion_gate_id: str
    strategy_track: StrategyTrack
    market_profile_id: str
    supported_advisory_task_names: list[str] = Field(default_factory=list)
    supported_tracks: list[str] = Field(default_factory=list)
    review_level_summary: dict = Field(default_factory=dict)
    scenario_family_sub_summaries: list[dict] = Field(default_factory=list)
    replay_window_sub_summaries: list[dict] = Field(default_factory=list)
    observation_horizon_sub_summaries: list[dict] = Field(default_factory=list)
    symbol_coverage_summary: dict = Field(default_factory=dict)
    outcome_label_summary: dict = Field(default_factory=dict)
    blocked_report_only_non_actionable_summary: dict = Field(default_factory=dict)
    risk_summary: AdvisoryContextRiskSummary
    data_quality_summary: dict = Field(default_factory=dict)
    gap_summary: dict = Field(default_factory=dict)
    evidence_items: list[AdvisoryContextEvidenceItem] = Field(default_factory=list)
    distillation_eligible: bool
    training_only_context: bool
    llm_training_context_allowed: bool
    llm_runtime_allowed: bool
    cloud_llm_called: bool
    local_model_runtime_called: bool
    non_executable: bool = True
    no_trade_instruction: bool = True
    metadata_json: dict = Field(default_factory=lambda: dict(DOMESTIC_SHADOW_ADVISORY_CONTEXT_METADATA))


class AdvisoryContextValidationReport(StrictModel):
    schema_version: str = "4.9-domestic-shadow-advisory-context-validation-report"
    report_id: str
    bundle_reference: str
    valid: bool
    strategy_track: StrategyTrack
    market_profile_id: str
    training_only_metadata_present: bool
    coverage_sufficient: bool
    block_reasons: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    metadata_json: dict = Field(default_factory=lambda: dict(DOMESTIC_SHADOW_ADVISORY_CONTEXT_METADATA))


class AdvisoryContextGapReport(StrictModel):
    schema_version: str = "4.9-domestic-shadow-advisory-context-gap-report"
    report_id: str
    bundle_reference: str
    gap_categories: list[str] = Field(default_factory=list)
    missing_source_count: int = Field(..., ge=0)
    insufficient_coverage_count: int = Field(..., ge=0)
    wording_violation_count: int = Field(..., ge=0)
    unsupported_task_count: int = Field(..., ge=0)
    metadata_json: dict = Field(default_factory=lambda: dict(DOMESTIC_SHADOW_ADVISORY_CONTEXT_METADATA))


class AdvisoryContextSafetyReport(StrictModel):
    schema_version: str = "4.9-domestic-shadow-advisory-context-safety-report"
    report_id: str
    strategy_track: StrategyTrack
    safety_boundary: AdvisoryContextSafetyBoundary
    warnings: list[str] = Field(default_factory=list)
    block_reasons: list[str] = Field(default_factory=list)
    metadata_json: dict = Field(default_factory=lambda: dict(DOMESTIC_SHADOW_ADVISORY_CONTEXT_METADATA))


class DomesticShadowAdvisoryContextFixture(StrictModel):
    schema_version: str
    run_id: str = Field(..., min_length=1)
    created_at: datetime
    shadow_review_advisory_context_config: ShadowReviewAdvisoryContextConfig
    shadow_review_advisory_input_set: ShadowReviewAdvisoryInputSet
    advisory_context_policy: AdvisoryContextPolicy
    _created = field_validator("created_at")(aware)

    @field_validator("schema_version")
    @classmethod
    def exact_schema(cls, value: str) -> str:
        if value != "4.9-domestic-shadow-advisory-context-fixture":
            raise ValueError("schema_version must be exactly 4.9-domestic-shadow-advisory-context-fixture")
        return value

    @model_validator(mode="after")
    def validate_fixture(self):
        if self.shadow_review_advisory_context_config.strategy_track != StrategyTrack.DOMESTIC_KR:
            raise ValueError("domestic shadow advisory context fixture requires StrategyTrack DOMESTIC_KR")
        if self.shadow_review_advisory_input_set.strategy_track != StrategyTrack.DOMESTIC_KR:
            raise ValueError("shadow advisory context input set must be DOMESTIC_KR")
        market_id = str(self.shadow_review_advisory_input_set.market_profile_summary.get("market_id", "")).upper()
        if market_id != "KRX":
            raise ValueError("market_profile must resolve to KRX")
        if "UNSAFE_TRIGGER_ATTEMPT" in self.shadow_review_advisory_input_set.data_quality_flags:
            raise ValueError("unsafe trigger attempt is not allowed in advisory context fixtures")
        return self

