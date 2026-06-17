from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from pydantic import Field, field_validator, model_validator

from stock_risk_mcp.domestic_scanner_models import (
    AdvisoryContext,
    DomesticScannerFixture,
    ProfitabilityContext,
    ScannerCandidateState,
    ScannerDiscoveryCompatibility,
)
from stock_risk_mcp.models import StrictModel
from stock_risk_mcp.strategy_track_models import StrategyTrack


def aware(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("timestamp must include timezone")
    return value


DOMESTIC_CANDIDATE_EVALUATION_METADATA = {
    "domestic_candidate_evaluation_fixture_run": True,
    "strategy_track_required": True,
    "domestic_kr_only": True,
    "market_profile_resolved": True,
    "scanner_candidate_consumed": True,
    "technical_evidence_context_checked": True,
    "profitability_context_checked": True,
    "candidate_evaluation_report_generated": True,
    "kiwoom_api_called": False,
    "broker_api_called": False,
    "credentials_accessed": False,
    "external_network_calls": False,
    "orders_created": False,
    "live_or_prod_used": False,
    "cloud_llm_called": False,
    "model_runtime_called": False,
}


class CandidateEvaluationState(StrEnum):
    EVALUATION_READY = "EVALUATION_READY"
    WATCH_ONLY = "WATCH_ONLY"
    REPORT_ONLY = "REPORT_ONLY"
    BLOCKED_SCANNER_QUALITY = "BLOCKED_SCANNER_QUALITY"
    BLOCKED_STALE_DATA = "BLOCKED_STALE_DATA"
    BLOCKED_PROFITABILITY = "BLOCKED_PROFITABILITY"
    BLOCKED_TECHNICAL_EVIDENCE = "BLOCKED_TECHNICAL_EVIDENCE"
    BLOCKED_RISK = "BLOCKED_RISK"
    REJECTED_NON_DOMESTIC = "REJECTED_NON_DOMESTIC"
    REJECTED_UNSAFE_TRIGGER = "REJECTED_UNSAFE_TRIGGER"
    INSUFFICIENT_CONTEXT = "INSUFFICIENT_CONTEXT"


class CandidateEvaluationCompatibility(StrEnum):
    DISCOVER = ScannerDiscoveryCompatibility.DISCOVER.value
    WATCH = ScannerDiscoveryCompatibility.WATCH.value
    EXCLUDE = ScannerDiscoveryCompatibility.EXCLUDE.value


class CandidateEvaluationConfig(StrictModel):
    config_id: str = Field(..., min_length=1)
    strategy_track: StrategyTrack
    report_only_mode: bool = False
    minimum_technical_score_threshold: int = Field(..., ge=0, le=100)
    minimum_profitability_score_threshold: int = Field(..., ge=0, le=100)
    minimum_risk_acceptance_threshold: int = Field(..., ge=0, le=100)
    stale_evaluation_policy: str = Field(..., min_length=1)
    missing_evidence_policy: str = Field(..., min_length=1)
    scanner_compatibility_carry_forward_policy: str = Field(..., min_length=1)
    evaluation_compatibility_mapping_policy: str = Field(..., min_length=1)

    @field_validator(
        "config_id",
        "stale_evaluation_policy",
        "missing_evidence_policy",
        "scanner_compatibility_carry_forward_policy",
        "evaluation_compatibility_mapping_policy",
    )
    @classmethod
    def normalize_text(cls, value: str) -> str:
        return value.strip().upper()


class TechnicalEvidenceContext(StrictModel):
    evidence_id: str = Field(..., min_length=1)
    ticker: str = Field(..., min_length=1)
    macd_evidence_summary: str | None = None
    rsi_evidence_summary: str | None = None
    moving_average_evidence_summary: str | None = None
    hma_evidence_summary: str | None = None
    atr_risk_evidence_summary: str | None = None
    volume_evidence_summary: str | None = None
    divergence_evidence_summary: str | None = None
    setup_grade: str | None = None
    evidence_freshness: str | None = None
    missing_evidence_flags: list[str] = Field(default_factory=list)

    @field_validator("evidence_id", "ticker", "setup_grade", "evidence_freshness", mode="before")
    @classmethod
    def normalize_optional_text(cls, value):
        if value is None:
            return value
        return str(value).strip().upper()

    @field_validator("missing_evidence_flags", mode="before")
    @classmethod
    def normalize_flags(cls, values):
        cleaned = [str(item).strip().upper() for item in values]
        if any(not item for item in cleaned):
            raise ValueError("missing_evidence_flags must not contain blank values")
        return cleaned


class EvaluationProfitabilityContext(StrictModel):
    profitability_context_status: str = Field(..., min_length=1)
    track_aware_profitability_check: str | None = None
    expected_net_profit: float | None = None
    expected_net_return_percentage: float | None = None
    break_even_move: float | None = None
    cost_aware_minimum_target_move: float | None = None

    @field_validator("profitability_context_status")
    @classmethod
    def normalize_status(cls, value: str) -> str:
        return value.strip().upper()


class CandidateTechnicalScore(StrictModel):
    ticker: str
    score: int = Field(..., ge=0, le=100)
    contributing_indicators: list[str] = Field(default_factory=list)
    missing_indicators: list[str] = Field(default_factory=list)
    setup_grade: str | None = None
    evidence_freshness: str | None = None
    evaluation_warnings: list[str] = Field(default_factory=list)


class CandidateProfitabilityScore(StrictModel):
    ticker: str
    profitability_context_status: str
    expected_net_profit: float | None = None
    expected_net_return_percentage: float | None = None
    break_even_move: float | None = None
    cost_aware_minimum_target_move: float | None = None
    score: int = Field(..., ge=0, le=100)
    blocked_reason: str | None = None


class CandidateRiskSignal(StrictModel):
    ticker: str
    stale_risk: str
    scanner_quality_risk: str
    profitability_risk: str
    technical_evidence_risk: str
    unsafe_trigger_risk: str
    overall_risk_classification: str


class CandidateEvaluationDecision(StrictModel):
    candidate_id: str
    ticker: str
    scanner_state: ScannerCandidateState
    scanner_compatibility_status: ScannerDiscoveryCompatibility
    evaluation_state: CandidateEvaluationState
    evaluation_compatibility_status: CandidateEvaluationCompatibility
    technical_score: CandidateTechnicalScore
    profitability_score: CandidateProfitabilityScore
    risk_signal: CandidateRiskSignal
    warnings: list[str] = Field(default_factory=list)
    block_reasons: list[str] = Field(default_factory=list)
    supported_tracks: list[str] = Field(default_factory=list)
    prompt_pack_context_marker: str | None = None
    actionable_approval: bool = False


class CandidateEvaluationSafetyBoundary(StrictModel):
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


class CandidateEvaluationReport(StrictModel):
    schema_version: str = "4.4-domestic-candidate-evaluation-report"
    report_id: str
    strategy_track: StrategyTrack
    market_profile_summary: dict = Field(default_factory=dict)
    candidate_count: int = Field(..., ge=0)
    evaluation_ready_count: int = Field(..., ge=0)
    watch_only_count: int = Field(..., ge=0)
    report_only_count: int = Field(..., ge=0)
    blocked_count: int = Field(..., ge=0)
    rejected_count: int = Field(..., ge=0)
    gap_count: int = Field(..., ge=0)
    decisions: list[CandidateEvaluationDecision] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    block_reasons: list[str] = Field(default_factory=list)
    metadata_json: dict = Field(default_factory=lambda: dict(DOMESTIC_CANDIDATE_EVALUATION_METADATA))


class CandidateEvaluationGapReport(StrictModel):
    schema_version: str = "4.4-domestic-candidate-evaluation-gap-report"
    report_id: str
    missing_technical_evidence_count: int = Field(..., ge=0)
    missing_profitability_context_count: int = Field(..., ge=0)
    stale_candidate_count: int = Field(..., ge=0)
    blocked_candidate_count: int = Field(..., ge=0)
    unsupported_track_count: int = Field(..., ge=0)
    unsafe_trigger_count: int = Field(..., ge=0)
    unresolved_market_profile_count: int = Field(..., ge=0)
    gap_reasons: list[str] = Field(default_factory=list)
    metadata_json: dict = Field(default_factory=lambda: dict(DOMESTIC_CANDIDATE_EVALUATION_METADATA))


class CandidateEvaluationSafetyReport(StrictModel):
    schema_version: str = "4.4-domestic-candidate-evaluation-safety-report"
    report_id: str
    strategy_track: StrategyTrack
    safety_boundary: CandidateEvaluationSafetyBoundary
    decisions: list[CandidateEvaluationDecision] = Field(default_factory=list)
    metadata_json: dict = Field(default_factory=lambda: dict(DOMESTIC_CANDIDATE_EVALUATION_METADATA))


class CandidateEvaluationValidationReport(StrictModel):
    schema_version: str = "4.4-domestic-candidate-evaluation-validation-report"
    config_id: str
    strategy_track: StrategyTrack
    market_id: str
    provider_id: str
    metadata_json: dict = Field(default_factory=lambda: dict(DOMESTIC_CANDIDATE_EVALUATION_METADATA))


class DomesticCandidateEvaluationFixture(StrictModel):
    schema_version: str
    run_id: str = Field(..., min_length=1)
    created_at: datetime
    evaluation_config: CandidateEvaluationConfig
    domestic_scanner_fixture: DomesticScannerFixture
    technical_evidence_context: TechnicalEvidenceContext
    profitability_context: EvaluationProfitabilityContext
    advisory_context: AdvisoryContext
    _created = field_validator("created_at")(aware)

    @field_validator("schema_version")
    @classmethod
    def exact_schema(cls, value: str) -> str:
        if value != "4.4-domestic-candidate-evaluation-fixture":
            raise ValueError("schema_version must be exactly 4.4-domestic-candidate-evaluation-fixture")
        return value

    @model_validator(mode="after")
    def validate_domestic_only(self):
        if self.evaluation_config.strategy_track != StrategyTrack.DOMESTIC_KR:
            raise ValueError("domestic candidate evaluation fixture requires StrategyTrack DOMESTIC_KR")
        if self.domestic_scanner_fixture.scanner_config.strategy_track != StrategyTrack.DOMESTIC_KR:
            raise ValueError("domestic scanner fixture must be DOMESTIC_KR")
        if self.domestic_scanner_fixture.domestic_realtime_fixture.strategy_request.market_profile.market_id != "KRX":
            raise ValueError("market_profile must resolve to KRX")
        return self
