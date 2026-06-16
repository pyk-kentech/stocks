from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from pydantic import Field, field_validator, model_validator

from stock_risk_mcp.local_model_benchmark_models import BenchmarkEligibility
from stock_risk_mcp.models import StrictModel


def aware(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("timestamp must include timezone")
    return value


LOCAL_MODEL_DECISION_METADATA = {
    "decision_report_offline_only": True,
    "real_model_called": False,
    "external_network_calls": False,
    "cloud_backend_used": False,
    "model_downloaded": False,
    "orders_created": False,
    "order_intents_created": False,
    "order_drafts_created": False,
    "execution_approved": False,
    "gates_bypassed": False,
    "production_policy_changed": False,
}


class BenchmarkPackType(StrEnum):
    DECISION_PACK = "DECISION_PACK"


class DecisionRecommendationStatus(StrEnum):
    NO_ELIGIBLE_BACKEND = "NO_ELIGIBLE_BACKEND"
    NEEDS_MORE_BENCHMARKS = "NEEDS_MORE_BENCHMARKS"
    CANDIDATE_SHORTLIST_READY = "CANDIDATE_SHORTLIST_READY"
    MOCK_ONLY_READY = "MOCK_ONLY_READY"


class CoverageLanguageTag(StrEnum):
    KOREAN = "KOREAN"
    ENGLISH = "ENGLISH"
    MIXED = "MIXED"


class CoverageDomainTag(StrEnum):
    TECHNICAL_EVIDENCE = "TECHNICAL_EVIDENCE"
    MARKET_DISCOVERY = "MARKET_DISCOVERY"
    RISK_EXPLANATION = "RISK_EXPLANATION"
    MISSING_DATA = "MISSING_DATA"
    ASSUMPTION_CHALLENGE = "ASSUMPTION_CHALLENGE"


class LocalModelBenchmarkPackFixture(StrictModel):
    schema_version: str
    pack_id: str = Field(..., min_length=1)
    created_at: datetime
    pack_type: BenchmarkPackType
    required_language_tags: list[CoverageLanguageTag] = Field(..., min_length=3)
    required_domain_tags: list[CoverageDomainTag] = Field(..., min_length=4)
    benchmark_report_files: list[str] = Field(..., min_length=1)
    _created = field_validator("created_at")(aware)

    @field_validator("schema_version")
    @classmethod
    def exact_schema(cls, value: str) -> str:
        if value != "3.11-local-model-benchmark-pack-fixture":
            raise ValueError("schema_version must be exactly 3.11-local-model-benchmark-pack-fixture")
        return value

    @field_validator("benchmark_report_files")
    @classmethod
    def no_blank_files(cls, values: list[str]) -> list[str]:
        cleaned = [item.strip() for item in values]
        if any(not item for item in cleaned):
            raise ValueError("benchmark_report_files must not contain blank values")
        return cleaned


class LocalModelReportTraceSummary(StrictModel):
    report_ref: str
    run_id: str
    language_tags: list[str] = Field(default_factory=list)
    domain_tags: list[str] = Field(default_factory=list)
    candidate_eligibility_snapshot: dict = Field(default_factory=dict)
    top_candidate_ids: list[str] = Field(default_factory=list)
    failed_candidate_ids: list[str] = Field(default_factory=list)


class LocalModelCandidatePackSummary(StrictModel):
    candidate_model_id: str
    report_count_seen: int = Field(..., ge=0)
    eligible_report_count: int = Field(..., ge=0)
    hard_fail_count: int = Field(..., ge=0)
    final_pack_eligibility: BenchmarkEligibility
    eligibility_stability_across_reports: float = Field(..., ge=0, le=1)
    average_overall_score: float = Field(..., ge=0, le=1)
    per_domain_score: dict = Field(default_factory=dict)
    per_language_score: dict = Field(default_factory=dict)
    schema_reliability: float = Field(..., ge=0, le=1)
    safety_failure_rate: float = Field(..., ge=0, le=1)
    advisory_boundary_failure_rate: float = Field(..., ge=0, le=1)
    missing_data_awareness_rate: float = Field(..., ge=0, le=1)
    json_parse_success_rate: float = Field(..., ge=0, le=1)
    fail_reason_counts: dict = Field(default_factory=dict)
    language_coverage: list[str] = Field(default_factory=list)
    domain_coverage: list[str] = Field(default_factory=list)


class LocalModelDecisionRankingEntry(StrictModel):
    rank: int = Field(..., ge=1)
    candidate_model_id: str
    average_overall_score: float = Field(..., ge=0, le=1)
    final_pack_eligibility: BenchmarkEligibility


class LocalModelBackendDecisionReport(StrictModel):
    schema_version: str = "3.11-local-model-decision-report"
    pack_id: str
    report_count: int = Field(..., ge=0)
    candidate_count: int = Field(..., ge=0)
    eligible_candidate_count: int = Field(..., ge=0)
    recommendation_status: DecisionRecommendationStatus
    shortlisted_candidates: list[dict] = Field(default_factory=list)
    rejected_candidates: list[dict] = Field(default_factory=list)
    trace_reports: list[LocalModelReportTraceSummary] = Field(default_factory=list)
    coverage_summary: dict = Field(default_factory=dict)
    aggregation_summary: dict = Field(default_factory=dict)
    metadata_json: dict = Field(default_factory=lambda: dict(LOCAL_MODEL_DECISION_METADATA))
    created_at: datetime
    _created = field_validator("created_at")(aware)

    @field_validator("schema_version")
    @classmethod
    def exact_schema(cls, value: str) -> str:
        if value != "3.11-local-model-decision-report":
            raise ValueError("schema_version must be exactly 3.11-local-model-decision-report")
        return value
