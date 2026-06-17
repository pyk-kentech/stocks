from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from pydantic import Field, field_validator, model_validator

from stock_risk_mcp.domestic_replay_models import ReplayEvaluationReport
from stock_risk_mcp.models import StrictModel
from stock_risk_mcp.strategy_track_models import StrategyTrack


def aware(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("timestamp must include timezone")
    return value


DOMESTIC_CALIBRATION_METADATA = {
    "domestic_calibration_fixture_run": True,
    "strategy_track_required": True,
    "domestic_kr_only": True,
    "market_profile_resolved": True,
    "replay_evaluation_report_consumed": True,
    "single_replay_comparison_generated": True,
    "calibration_pack_aggregated": True,
    "policy_candidate_comparison_generated": True,
    "promotion_gate_report_generated": True,
    "promotion_gate_pack_level_only": True,
    "kiwoom_api_called": False,
    "broker_api_called": False,
    "credentials_accessed": False,
    "external_network_calls": False,
    "orders_created": False,
    "live_or_prod_used": False,
    "cloud_llm_called": False,
    "model_runtime_called": False,
}


class PromotionGateStatus(StrEnum):
    PROMOTION_REJECTED = "PROMOTION_REJECTED"
    PROMOTION_REPORT_ONLY = "PROMOTION_REPORT_ONLY"
    PROMOTION_READY_FOR_MORE_REPLAY = "PROMOTION_READY_FOR_MORE_REPLAY"
    PROMOTION_READY_FOR_PAPER_SHADOW = "PROMOTION_READY_FOR_PAPER_SHADOW"
    PROMOTION_BLOCKED_SAFETY = "PROMOTION_BLOCKED_SAFETY"
    PROMOTION_BLOCKED_COVERAGE = "PROMOTION_BLOCKED_COVERAGE"
    PROMOTION_BLOCKED_REGRESSION = "PROMOTION_BLOCKED_REGRESSION"


class ScannerThresholdConfig(StrictModel):
    volume_spike_threshold: float = Field(..., gt=0)
    momentum_threshold: float = Field(..., gt=0)
    liquidity_threshold: float = Field(..., gt=0)
    stale_data_strictness: str = Field(..., min_length=1)
    report_only_handling: str = Field(..., min_length=1)
    watchlist_add_threshold: int = Field(..., ge=0, le=100)
    watchlist_remove_threshold: int = Field(..., ge=0, le=100)
    scanner_candidate_explosion_guardrail: int = Field(..., ge=1)

    @field_validator("stale_data_strictness", "report_only_handling")
    @classmethod
    def normalize_text(cls, value: str) -> str:
        return value.strip().upper()


class EvaluationThresholdConfig(StrictModel):
    minimum_technical_score: int = Field(..., ge=0, le=100)
    minimum_net_profit_threshold: float = Field(..., ge=0)
    maximum_break_even_move: float = Field(..., ge=0)
    risk_block_threshold: int = Field(..., ge=0, le=100)
    technical_evidence_missing_policy: str = Field(..., min_length=1)
    profitability_context_missing_policy: str = Field(..., min_length=1)
    compatibility_mapping_preservation_policy: str = Field(..., min_length=1)

    @field_validator(
        "technical_evidence_missing_policy",
        "profitability_context_missing_policy",
        "compatibility_mapping_preservation_policy",
    )
    @classmethod
    def normalize_text(cls, value: str) -> str:
        return value.strip().upper()


class PolicyCandidateConfig(StrictModel):
    policy_id: str = Field(..., min_length=1)
    label: str = Field(..., min_length=1)
    strategy_track: StrategyTrack
    market_profile_summary: dict = Field(default_factory=dict)
    scanner_threshold_config: ScannerThresholdConfig
    evaluation_threshold_config: EvaluationThresholdConfig
    report_only_policy_markers: list[str] = Field(default_factory=list)
    stale_data_handling_markers: list[str] = Field(default_factory=list)
    provenance_markers: list[str] = Field(default_factory=list)

    @field_validator("policy_id", "label")
    @classmethod
    def normalize_text(cls, value: str) -> str:
        return value.strip()

    @model_validator(mode="after")
    def validate_market_profile(self):
        market_id = str(self.market_profile_summary.get("market_id", "")).upper()
        if self.strategy_track != StrategyTrack.DOMESTIC_KR:
            raise ValueError("policy candidate config requires StrategyTrack DOMESTIC_KR")
        if market_id != "KRX":
            raise ValueError("market_profile must resolve to KRX")
        return self


class PromotionGateCriteria(StrictModel):
    minimum_calibration_pack_size: int = Field(..., ge=1)
    minimum_scenario_family_count: int = Field(..., ge=1)
    minimum_window_coverage: int = Field(..., ge=1)
    maximum_safety_regression_count: int = Field(..., ge=0)
    maximum_stale_data_regression_count: int = Field(..., ge=0)
    maximum_domestic_only_regression_count: int = Field(..., ge=0)
    maximum_report_only_invariant_regression_count: int = Field(..., ge=0)
    maximum_non_actionable_invariant_regression_count: int = Field(..., ge=0)
    maximum_unsafe_trigger_regression_count: int = Field(..., ge=0)
    minimum_safety_score: int = Field(..., ge=0, le=100)
    minimum_coverage_score: int = Field(..., ge=0, le=100)
    minimum_stability_score: int = Field(..., ge=0, le=100)


class CalibrationRunConfig(StrictModel):
    calibration_run_id: str = Field(..., min_length=1)
    strategy_track: StrategyTrack
    baseline_policy_id: str = Field(..., min_length=1)
    candidate_policy_ids: list[str] = Field(..., min_length=1)
    comparison_mode: str = Field(..., min_length=1)
    required_scenario_families: list[str] = Field(..., min_length=1)
    minimum_replay_count: int = Field(..., ge=1)
    minimum_window_count: int = Field(..., ge=1)
    regression_policy: str = Field(..., min_length=1)
    coverage_policy: str = Field(..., min_length=1)
    promotion_gate_criteria: PromotionGateCriteria

    @field_validator(
        "calibration_run_id",
        "baseline_policy_id",
        "comparison_mode",
        "regression_policy",
        "coverage_policy",
        mode="before",
    )
    @classmethod
    def normalize_text(cls, value):
        return str(value).strip().upper()

    @field_validator("candidate_policy_ids", "required_scenario_families", mode="before")
    @classmethod
    def normalize_list(cls, values):
        cleaned = [str(value).strip().upper() for value in values]
        if any(not value for value in cleaned):
            raise ValueError("list values must not be blank")
        return cleaned


class CalibrationInputSet(StrictModel):
    input_set_id: str = Field(..., min_length=1)
    market_profile_summary: dict = Field(default_factory=dict)
    scenario_family_labels: list[str] = Field(..., min_length=1)
    advisory_context_markers: list[str] = Field(default_factory=list)
    replay_reports: list[ReplayEvaluationReport] = Field(..., min_length=1)
    replay_fixture_provenance_markers: list[str] = Field(default_factory=list)

    @field_validator("scenario_family_labels", "advisory_context_markers", "replay_fixture_provenance_markers", mode="before")
    @classmethod
    def normalize_list(cls, values):
        cleaned = [str(value).strip().upper() for value in values]
        if any(not value for value in cleaned):
            raise ValueError("list values must not be blank")
        return cleaned

    @model_validator(mode="after")
    def validate_market_profile(self):
        market_id = str(self.market_profile_summary.get("market_id", "")).upper()
        if market_id != "KRX":
            raise ValueError("market_profile must resolve to KRX")
        if not self.replay_reports:
            raise ValueError("replay reports are required")
        return self


class CandidatePolicySummary(StrictModel):
    candidate_policy_id: str
    coverage_score: int = Field(..., ge=0, le=100)
    safety_score: int = Field(..., ge=0, le=100)
    stability_score: int = Field(..., ge=0, le=100)
    candidates_generated: int = Field(..., ge=0)
    candidates_blocked: int = Field(..., ge=0)
    report_only_count: int = Field(..., ge=0)
    non_actionable_count: int = Field(..., ge=0)
    stale_data_block_count: int = Field(..., ge=0)
    quality_block_count: int = Field(..., ge=0)
    profitability_block_count: int = Field(..., ge=0)
    technical_evidence_block_count: int = Field(..., ge=0)
    unsafe_trigger_rejection_count: int = Field(..., ge=0)
    false_positive_proxy_placeholder: int = Field(..., ge=0)
    missed_opportunity_proxy_placeholder: int = Field(..., ge=0)


class SingleReplayComparisonResult(StrictModel):
    comparison_result_id: str
    replay_report_id: str
    baseline_policy_id: str
    candidate_summaries: list[CandidatePolicySummary] = Field(default_factory=list)
    event_trace_reference: str
    window_summary_reference: str
    regression_findings: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    block_reasons: list[str] = Field(default_factory=list)
    promotion_eligible: bool = False


class CalibrationPackMetrics(StrictModel):
    runs_evaluated: int = Field(..., ge=0)
    windows_evaluated: int = Field(..., ge=0)
    scenario_family_count: int = Field(..., ge=0)
    replay_fixture_count: int = Field(..., ge=0)
    candidates_generated: int = Field(..., ge=0)
    candidates_blocked: int = Field(..., ge=0)
    report_only_count: int = Field(..., ge=0)
    non_actionable_count: int = Field(..., ge=0)
    watchlist_add_remove_count: int = Field(..., ge=0)
    stale_data_block_count: int = Field(..., ge=0)
    quality_block_count: int = Field(..., ge=0)
    profitability_block_count: int = Field(..., ge=0)
    technical_evidence_block_count: int = Field(..., ge=0)
    unsafe_trigger_rejection_count: int = Field(..., ge=0)
    safety_regression_count: int = Field(..., ge=0)
    stale_data_regression_count: int = Field(..., ge=0)
    domestic_only_regression_count: int = Field(..., ge=0)
    coverage_score: int = Field(..., ge=0, le=100)
    safety_score: int = Field(..., ge=0, le=100)
    stability_score: int = Field(..., ge=0, le=100)
    false_positive_proxy_placeholder: int = Field(..., ge=0)
    missed_opportunity_proxy_placeholder: int = Field(..., ge=0)


class CalibrationPackCoverageReport(StrictModel):
    required_scenario_families: list[str] = Field(default_factory=list)
    observed_scenario_families: list[str] = Field(default_factory=list)
    missing_scenario_families: list[str] = Field(default_factory=list)
    required_replay_count: int = Field(..., ge=0)
    observed_replay_count: int = Field(..., ge=0)
    required_window_count: int = Field(..., ge=0)
    observed_window_count: int = Field(..., ge=0)
    diversity_warnings: list[str] = Field(default_factory=list)
    coverage_pass: bool = False


class CalibrationPack(StrictModel):
    calibration_pack_id: str
    strategy_track: StrategyTrack
    market_profile_summary: dict = Field(default_factory=dict)
    included_single_run_comparison_ids: list[str] = Field(default_factory=list)
    included_replay_report_ids: list[str] = Field(default_factory=list)
    included_scenario_families: list[str] = Field(default_factory=list)
    included_fixture_families: list[str] = Field(default_factory=list)
    pack_metrics: CalibrationPackMetrics
    pack_coverage_report: CalibrationPackCoverageReport
    regression_summaries: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    block_reasons: list[str] = Field(default_factory=list)


class PolicyRegressionReport(StrictModel):
    report_id: str
    safety_boundary_regressions: list[str] = Field(default_factory=list)
    domestic_only_regressions: list[str] = Field(default_factory=list)
    stale_data_policy_regressions: list[str] = Field(default_factory=list)
    report_only_policy_regressions: list[str] = Field(default_factory=list)
    scanner_candidate_explosion_regressions: list[str] = Field(default_factory=list)
    blocked_candidate_collapse_regressions: list[str] = Field(default_factory=list)
    technical_evidence_missing_regressions: list[str] = Field(default_factory=list)
    profitability_context_missing_regressions: list[str] = Field(default_factory=list)
    compatibility_status_mapping_regressions: list[str] = Field(default_factory=list)
    unsafe_trigger_rejection_regressions: list[str] = Field(default_factory=list)


class CalibrationSafetyBoundary(StrictModel):
    advisory_only: bool = True
    production_policy_changed: bool = False
    order_creation_allowed: bool = False
    order_intent_allowed: bool = False
    order_draft_allowed: bool = False
    execution_approval_allowed: bool = False
    live_or_prod_allowed: bool = False
    broker_access_allowed: bool = False
    network_access_allowed: bool = False
    cloud_llm_allowed: bool = False
    model_runtime_allowed: bool = False


class PolicyComparisonReport(StrictModel):
    schema_version: str = "4.6-domestic-policy-comparison-report"
    report_id: str
    baseline_policy_id: str
    candidate_policy_ids: list[str] = Field(default_factory=list)
    single_run_summaries: list[dict] = Field(default_factory=list)
    pack_level_summaries: dict = Field(default_factory=dict)
    metric_deltas: list[dict] = Field(default_factory=list)
    coverage_summary: dict = Field(default_factory=dict)
    safety_summary: dict = Field(default_factory=dict)
    stability_summary: dict = Field(default_factory=dict)
    recommendation_notes: list[str] = Field(default_factory=list)
    metadata_json: dict = Field(default_factory=lambda: dict(DOMESTIC_CALIBRATION_METADATA))


class CalibrationRunResult(StrictModel):
    schema_version: str = "4.6-domestic-calibration-run-result"
    calibration_run_id: str
    baseline_policy_summary: dict = Field(default_factory=dict)
    candidate_policy_summaries: list[dict] = Field(default_factory=list)
    single_run_results: list[SingleReplayComparisonResult] = Field(default_factory=list)
    calibration_pack: CalibrationPack
    policy_comparison_report: PolicyComparisonReport
    regression_report: PolicyRegressionReport
    warnings: list[str] = Field(default_factory=list)
    block_reasons: list[str] = Field(default_factory=list)
    metadata_json: dict = Field(default_factory=lambda: dict(DOMESTIC_CALIBRATION_METADATA))


class PromotionGateReport(StrictModel):
    schema_version: str = "4.6-domestic-promotion-gate-report"
    report_id: str
    calibration_pack_id: str
    gate_status: PromotionGateStatus
    status_reasons: list[str] = Field(default_factory=list)
    coverage_findings: list[str] = Field(default_factory=list)
    regression_findings: list[str] = Field(default_factory=list)
    safety_boundary: CalibrationSafetyBoundary = Field(default_factory=CalibrationSafetyBoundary)
    warnings: list[str] = Field(default_factory=list)
    block_reasons: list[str] = Field(default_factory=list)
    metadata_json: dict = Field(default_factory=lambda: dict(DOMESTIC_CALIBRATION_METADATA))


class CalibrationValidationReport(StrictModel):
    schema_version: str = "4.6-domestic-calibration-validation-report"
    calibration_run_id: str
    strategy_track: StrategyTrack
    market_id: str
    replay_report_count: int = Field(..., ge=0)
    metadata_json: dict = Field(default_factory=lambda: dict(DOMESTIC_CALIBRATION_METADATA))


class DomesticCalibrationFixture(StrictModel):
    schema_version: str
    run_id: str = Field(..., min_length=1)
    created_at: datetime
    calibration_run_config: CalibrationRunConfig
    calibration_input_set: CalibrationInputSet
    baseline_policy: PolicyCandidateConfig
    candidate_policies: list[PolicyCandidateConfig] = Field(..., min_length=1)
    _created = field_validator("created_at")(aware)

    @field_validator("schema_version")
    @classmethod
    def exact_schema(cls, value: str) -> str:
        if value != "4.6-domestic-calibration-fixture":
            raise ValueError("schema_version must be exactly 4.6-domestic-calibration-fixture")
        return value

    @model_validator(mode="after")
    def validate_domestic_only(self):
        if self.calibration_run_config.strategy_track != StrategyTrack.DOMESTIC_KR:
            raise ValueError("domestic calibration fixture requires StrategyTrack DOMESTIC_KR")
        market_id = str(self.calibration_input_set.market_profile_summary.get("market_id", "")).upper()
        if market_id != "KRX":
            raise ValueError("market_profile must resolve to KRX")
        if not self.calibration_input_set.replay_reports:
            raise ValueError("replay reports are required")
        for report in self.calibration_input_set.replay_reports:
            if report.strategy_track != StrategyTrack.DOMESTIC_KR:
                raise ValueError("replay reports must be DOMESTIC_KR")
            if str(report.market_profile_summary.get("market_id", "")).upper() != "KRX":
                raise ValueError("replay report market_profile must resolve to KRX")
        candidate_ids = {candidate.policy_id for candidate in self.candidate_policies}
        expected_ids = set(self.calibration_run_config.candidate_policy_ids)
        if candidate_ids != expected_ids:
            raise ValueError("candidate policies must match calibration_run_config candidate_policy_ids")
        if self.baseline_policy.policy_id != self.calibration_run_config.baseline_policy_id:
            raise ValueError("baseline policy must match calibration_run_config baseline_policy_id")
        return self
