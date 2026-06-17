from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from pydantic import Field, field_validator, model_validator

from stock_risk_mcp.domestic_calibration_models import PromotionGateReport, PromotionGateStatus
from stock_risk_mcp.domestic_candidate_evaluation_models import CandidateEvaluationReport
from stock_risk_mcp.models import StrictModel
from stock_risk_mcp.strategy_track_models import StrategyTrack


def aware(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("timestamp must include timezone")
    return value


DOMESTIC_PAPER_SHADOW_METADATA = {
    "domestic_paper_shadow_fixture_run": True,
    "strategy_track_required": True,
    "domestic_kr_only": True,
    "market_profile_resolved": True,
    "promotion_gate_report_consumed": True,
    "candidate_evaluation_report_consumed": True,
    "paper_shadow_explicit_opt_in_required": True,
    "paper_shadow_journal_generated": True,
    "paper_shadow_candidate_level_entries": True,
    "paper_shadow_review_report_generated": True,
    "paper_shadow_review_summary_derived_from_entries": True,
    "paper_shadow_non_executable": True,
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


class PaperShadowDecisionType(StrEnum):
    SHADOW_WATCH = "SHADOW_WATCH"
    SHADOW_REJECT = "SHADOW_REJECT"
    SHADOW_REPORT_ONLY = "SHADOW_REPORT_ONLY"
    SHADOW_BLOCKED_QUALITY = "SHADOW_BLOCKED_QUALITY"
    SHADOW_BLOCKED_PROFITABILITY = "SHADOW_BLOCKED_PROFITABILITY"
    SHADOW_BLOCKED_TECHNICAL_EVIDENCE = "SHADOW_BLOCKED_TECHNICAL_EVIDENCE"
    SHADOW_BLOCKED_RISK = "SHADOW_BLOCKED_RISK"
    SHADOW_BLOCKED_SAFETY = "SHADOW_BLOCKED_SAFETY"
    SHADOW_INSUFFICIENT_CONTEXT = "SHADOW_INSUFFICIENT_CONTEXT"


class PaperShadowDecisionReason(StrictModel):
    reason_code: str = Field(..., min_length=1)
    reason_category: str = Field(..., min_length=1)
    source_layer: str = Field(..., min_length=1)
    explanatory_summary: str = Field(..., min_length=1)

    @field_validator("reason_code", "reason_category", "source_layer")
    @classmethod
    def normalize_text(cls, value: str) -> str:
        return value.strip().upper()


class PaperShadowConfig(StrictModel):
    config_id: str = Field(..., min_length=1)
    strategy_track: StrategyTrack
    explicit_paper_shadow_opt_in: bool
    allowed_promotion_gate_statuses: list[PromotionGateStatus] = Field(..., min_length=1)
    blocked_promotion_gate_statuses: list[PromotionGateStatus] = Field(..., min_length=1)
    journal_generation_mode: str = Field(..., min_length=1)
    review_aggregation_mode: str = Field(..., min_length=1)
    report_only_preservation_mode: str = Field(..., min_length=1)
    non_actionable_preservation_mode: str = Field(..., min_length=1)

    @field_validator(
        "config_id",
        "journal_generation_mode",
        "review_aggregation_mode",
        "report_only_preservation_mode",
        "non_actionable_preservation_mode",
    )
    @classmethod
    def normalize_text(cls, value: str) -> str:
        return value.strip().upper()

    @model_validator(mode="after")
    def validate_opt_in(self):
        if self.strategy_track != StrategyTrack.DOMESTIC_KR:
            raise ValueError("paper shadow config requires StrategyTrack DOMESTIC_KR")
        if not self.explicit_paper_shadow_opt_in:
            raise ValueError("explicit paper-shadow opt-in is required")
        return self


class PaperShadowInputSet(StrictModel):
    input_set_id: str = Field(..., min_length=1)
    strategy_track: StrategyTrack
    market_profile_summary: dict = Field(default_factory=dict)
    promotion_gate_report: PromotionGateReport
    promotion_gate_criteria_reference: str = Field(..., min_length=1)
    calibration_pack_reference: str = Field(..., min_length=1)
    coverage_report_reference: str = Field(..., min_length=1)
    regression_report_reference: str = Field(..., min_length=1)
    candidate_evaluation_reports: list[CandidateEvaluationReport] = Field(default_factory=list)
    replay_provenance_markers: list[str] = Field(default_factory=list)
    scenario_family_markers: list[str] = Field(..., min_length=1)
    advisory_context_markers: list[str] = Field(default_factory=list)

    @field_validator(
        "promotion_gate_criteria_reference",
        "calibration_pack_reference",
        "coverage_report_reference",
        "regression_report_reference",
    )
    @classmethod
    def normalize_text(cls, value: str) -> str:
        return value.strip()

    @field_validator(
        "replay_provenance_markers",
        "scenario_family_markers",
        "advisory_context_markers",
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
            raise ValueError("paper shadow input set requires StrategyTrack DOMESTIC_KR")
        market_id = str(self.market_profile_summary.get("market_id", "")).upper()
        if market_id != "KRX":
            raise ValueError("market_profile must resolve to KRX")
        if not self.candidate_evaluation_reports:
            raise ValueError("candidate evaluation reports are required")
        return self


class PaperShadowDecision(StrictModel):
    journal_entry_id: str
    fixture_id: str
    strategy_track: StrategyTrack
    market_profile_id: str
    candidate_id: str
    source_scanner_candidate_id: str
    source_evaluation_report_id: str
    source_promotion_gate_id: str
    decision_type: PaperShadowDecisionType
    reasons: list[PaperShadowDecisionReason] = Field(default_factory=list)
    blocked_reasons: list[str] = Field(default_factory=list)
    report_only_reasons: list[str] = Field(default_factory=list)
    non_actionable_reasons: list[str] = Field(default_factory=list)
    non_actionable: bool = True
    data_quality_flags: list[str] = Field(default_factory=list)
    decision_timestamp: datetime
    technical_evidence_context_summary: dict = Field(default_factory=dict)
    profitability_context_summary: dict = Field(default_factory=dict)
    risk_safety_context_summary: dict = Field(default_factory=dict)
    _ts = field_validator("decision_timestamp")(aware)


class PaperShadowSafetyBoundary(StrictModel):
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


class PaperShadowDecisionJournal(StrictModel):
    schema_version: str = "4.7-domestic-paper-shadow-decision-journal"
    journal_id: str
    strategy_track: StrategyTrack
    market_profile_summary: dict = Field(default_factory=dict)
    promotion_gate_status: PromotionGateStatus
    source_candidate_evaluation_report_ids: list[str] = Field(default_factory=list)
    source_replay_calibration_provenance_markers: list[str] = Field(default_factory=list)
    entries: list[PaperShadowDecision] = Field(default_factory=list)
    entry_count: int = Field(..., ge=0)
    warnings: list[str] = Field(default_factory=list)
    block_reasons: list[str] = Field(default_factory=list)
    safety_boundary: PaperShadowSafetyBoundary = Field(default_factory=PaperShadowSafetyBoundary)
    metadata_json: dict = Field(default_factory=lambda: dict(DOMESTIC_PAPER_SHADOW_METADATA))


class PaperShadowReviewReport(StrictModel):
    schema_version: str = "4.7-domestic-paper-shadow-review-report"
    review_report_id: str
    journal_reference: str
    total_journal_entries: int = Field(..., ge=0)
    shadow_watch_count: int = Field(..., ge=0)
    rejected_count: int = Field(..., ge=0)
    report_only_count: int = Field(..., ge=0)
    blocked_quality_count: int = Field(..., ge=0)
    blocked_profitability_count: int = Field(..., ge=0)
    blocked_technical_evidence_count: int = Field(..., ge=0)
    blocked_risk_count: int = Field(..., ge=0)
    blocked_safety_count: int = Field(..., ge=0)
    insufficient_context_count: int = Field(..., ge=0)
    non_actionable_count: int = Field(..., ge=0)
    candidate_coverage_count: int = Field(..., ge=0)
    scenario_family_coverage_count: int = Field(..., ge=0)
    decision_type_counts: dict[str, int] = Field(default_factory=dict)
    replay_window_counts: dict[str, int] = Field(default_factory=dict)
    scenario_family_counts: dict[str, int] = Field(default_factory=dict)
    symbol_counts: dict[str, int] = Field(default_factory=dict)
    blocked_reason_counts: dict[str, int] = Field(default_factory=dict)
    report_only_reason_counts: dict[str, int] = Field(default_factory=dict)
    non_actionable_reason_counts: dict[str, int] = Field(default_factory=dict)
    promotion_gate_status_counts: dict[str, int] = Field(default_factory=dict)
    advisory_context_placeholders: dict = Field(default_factory=dict)
    metadata_json: dict = Field(default_factory=lambda: dict(DOMESTIC_PAPER_SHADOW_METADATA))


class PaperShadowSafetyReport(StrictModel):
    schema_version: str = "4.7-domestic-paper-shadow-safety-report"
    report_id: str
    strategy_track: StrategyTrack
    safety_boundary: PaperShadowSafetyBoundary
    block_reasons: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    metadata_json: dict = Field(default_factory=lambda: dict(DOMESTIC_PAPER_SHADOW_METADATA))


class PaperShadowGapReport(StrictModel):
    schema_version: str = "4.7-domestic-paper-shadow-gap-report"
    gap_report_id: str
    missing_promotion_gate_evidence_count: int = Field(..., ge=0)
    missing_candidate_evaluation_count: int = Field(..., ge=0)
    blocked_promotion_gate_count: int = Field(..., ge=0)
    single_run_only_evidence_count: int = Field(..., ge=0)
    missing_market_profile_count: int = Field(..., ge=0)
    missing_strategy_track_count: int = Field(..., ge=0)
    unsafe_trigger_attempt_count: int = Field(..., ge=0)
    gap_reasons: list[str] = Field(default_factory=list)
    metadata_json: dict = Field(default_factory=lambda: dict(DOMESTIC_PAPER_SHADOW_METADATA))


class PaperShadowValidationReport(StrictModel):
    schema_version: str = "4.7-domestic-paper-shadow-validation-report"
    config_id: str
    strategy_track: StrategyTrack
    market_id: str
    candidate_evaluation_report_count: int = Field(..., ge=0)
    metadata_json: dict = Field(default_factory=lambda: dict(DOMESTIC_PAPER_SHADOW_METADATA))


class DomesticPaperShadowFixture(StrictModel):
    schema_version: str
    run_id: str = Field(..., min_length=1)
    created_at: datetime
    paper_shadow_config: PaperShadowConfig
    paper_shadow_input_set: PaperShadowInputSet
    _created = field_validator("created_at")(aware)

    @field_validator("schema_version")
    @classmethod
    def exact_schema(cls, value: str) -> str:
        if value != "4.7-domestic-paper-shadow-fixture":
            raise ValueError("schema_version must be exactly 4.7-domestic-paper-shadow-fixture")
        return value

    @model_validator(mode="after")
    def validate_domestic_only(self):
        if self.paper_shadow_config.strategy_track != StrategyTrack.DOMESTIC_KR:
            raise ValueError("domestic paper shadow fixture requires StrategyTrack DOMESTIC_KR")
        if self.paper_shadow_input_set.strategy_track != StrategyTrack.DOMESTIC_KR:
            raise ValueError("paper shadow input set must be DOMESTIC_KR")
        market_id = str(self.paper_shadow_input_set.market_profile_summary.get("market_id", "")).upper()
        if market_id != "KRX":
            raise ValueError("market_profile must resolve to KRX")
        return self
