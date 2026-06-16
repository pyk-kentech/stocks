from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from pydantic import Field, field_validator, model_validator

from stock_risk_mcp.local_llm_advisory_models import AdvisoryTaskType
from stock_risk_mcp.local_model_runtime_models import LocalModelBackendType, LocalModelFamily, StructuredOutputSuitability
from stock_risk_mcp.models import StrictModel


def aware(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("timestamp must include timezone")
    return value


LOCAL_MODEL_BENCHMARK_METADATA = {
    "benchmark_offline_only": True,
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


class BenchmarkLanguageTag(StrEnum):
    KOREAN = "KOREAN"
    ENGLISH = "ENGLISH"
    MIXED = "MIXED"


class BenchmarkDomainTag(StrEnum):
    TECHNICAL_EVIDENCE = "TECHNICAL_EVIDENCE"
    MARKET_DISCOVERY = "MARKET_DISCOVERY"
    RISK_EXPLANATION = "RISK_EXPLANATION"
    MISSING_DATA = "MISSING_DATA"
    ASSUMPTION_CHALLENGE = "ASSUMPTION_CHALLENGE"


class BenchmarkEligibility(StrEnum):
    ELIGIBLE = "ELIGIBLE"
    FAIL_SCHEMA = "FAIL_SCHEMA"
    FAIL_SAFETY = "FAIL_SAFETY"
    FAIL_ADVISORY_BOUNDARY = "FAIL_ADVISORY_BOUNDARY"
    FAIL_EXECUTION_AUTHORITY_HALLUCINATION = "FAIL_EXECUTION_AUTHORITY_HALLUCINATION"
    FAIL_REAL_MODEL_CALLED = "FAIL_REAL_MODEL_CALLED"
    FAIL_EXTERNAL_NETWORK = "FAIL_EXTERNAL_NETWORK"
    FAIL_CLOUD_BACKEND = "FAIL_CLOUD_BACKEND"
    FAIL_MODEL_DOWNLOAD = "FAIL_MODEL_DOWNLOAD"
    FAIL_UNSUPPORTED_BACKEND = "FAIL_UNSUPPORTED_BACKEND"
    FAIL_MISSING_DATA_AWARENESS = "FAIL_MISSING_DATA_AWARENESS"


class LocalModelBenchmarkRubric(StrictModel):
    schema_validity_weight: float = Field(..., ge=0, le=1)
    safety_weight: float = Field(..., ge=0, le=1)
    advisory_boundary_weight: float = Field(..., ge=0, le=1)
    missing_data_awareness_weight: float = Field(..., ge=0, le=1)
    language_handling_weight: float = Field(..., ge=0, le=1)
    json_reliability_weight: float = Field(..., ge=0, le=1)
    hallucination_risk_weight: float = Field(..., ge=0, le=1)
    local_advisory_suitability_weight: float = Field(..., ge=0, le=1)

    @model_validator(mode="after")
    def validate_sum(self):
        total = (
            self.schema_validity_weight
            + self.safety_weight
            + self.advisory_boundary_weight
            + self.missing_data_awareness_weight
            + self.language_handling_weight
            + self.json_reliability_weight
            + self.hallucination_risk_weight
            + self.local_advisory_suitability_weight
        )
        if abs(total - 1.0) > 1e-9:
            raise ValueError("scoring rubric weights must sum to exactly 1.0")
        return self


class LocalModelBenchmarkCase(StrictModel):
    benchmark_id: str = Field(..., min_length=1)
    task_type: AdvisoryTaskType
    language_tag: BenchmarkLanguageTag
    domain_tag: BenchmarkDomainTag
    input_text: str = Field(..., min_length=1)
    expected_safe_behavior: list[str] = Field(..., min_length=1)
    expected_schema_fields: list[str] = Field(..., min_length=1)
    forbidden_output_patterns: list[str] = Field(..., min_length=1)
    scoring_rubric: LocalModelBenchmarkRubric

    @field_validator("expected_safe_behavior", "expected_schema_fields", "forbidden_output_patterns")
    @classmethod
    def no_blank_values(cls, values: list[str]) -> list[str]:
        cleaned = [value.strip() for value in values]
        if any(not value for value in cleaned):
            raise ValueError("list values must not be blank")
        return cleaned


class LocalModelBenchmarkFixture(StrictModel):
    schema_version: str
    run_id: str = Field(..., min_length=1)
    created_at: datetime
    benchmarks: list[LocalModelBenchmarkCase] = Field(..., min_length=1)
    _created = field_validator("created_at")(aware)

    @field_validator("schema_version")
    @classmethod
    def exact_schema(cls, value: str) -> str:
        if value != "3.10-local-model-benchmark-fixture":
            raise ValueError("schema_version must be exactly 3.10-local-model-benchmark-fixture")
        return value


class CandidateJsonReliability(StrEnum):
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


class CandidateModelMetadata(StrictModel):
    model_family: LocalModelFamily
    parameter_class: str = Field(..., min_length=1)
    quantization_target: str = Field(..., min_length=1)
    expected_ram_gb: float = Field(..., gt=0)
    expected_vram_gb: float = Field(..., gt=0)
    context_length: int = Field(..., gt=0)
    supports_korean: bool
    supports_english: bool
    supports_mixed_language: bool
    json_output_reliability: CandidateJsonReliability
    summarization_suitability: StructuredOutputSuitability
    license_notes: str = Field(..., min_length=1)
    local_only_feasible: bool

    @model_validator(mode="after")
    def ensure_local_only(self):
        if self.local_only_feasible is not True:
            raise ValueError("local_only_feasible must be true")
        return self


class LocalModelCandidateOutput(StrictModel):
    candidate_model_id: str = Field(..., min_length=1)
    backend_type: LocalModelBackendType
    candidate_metadata: CandidateModelMetadata
    benchmark_id: str = Field(..., min_length=1)
    output_text: str | None = None
    output_json: dict | None = None
    latency_ms: int | None = Field(default=None, gt=0)
    token_count: int | None = Field(default=None, gt=0)
    real_model_called: bool
    external_network_calls: bool
    cloud_backend_used: bool
    model_downloaded: bool

    @model_validator(mode="after")
    def require_output(self):
        if not self.output_text and not self.output_json:
            raise ValueError("output_text or output_json must be present")
        if isinstance(self.output_json, dict):
            for key, value in self.output_json.items():
                if not str(key).strip():
                    raise ValueError("output_json keys must not be blank")
                if isinstance(value, str) and not value.strip():
                    raise ValueError("output_json string values must not be blank")
        return self


class LocalModelCandidateOutputFixture(StrictModel):
    schema_version: str
    run_id: str = Field(..., min_length=1)
    created_at: datetime
    candidate_outputs: list[LocalModelCandidateOutput] = Field(..., min_length=1)
    _created = field_validator("created_at")(aware)

    @field_validator("schema_version")
    @classmethod
    def exact_schema(cls, value: str) -> str:
        if value != "3.10-local-model-candidate-output-fixture":
            raise ValueError("schema_version must be exactly 3.10-local-model-candidate-output-fixture")
        return value


class LocalModelBenchmarkEvaluation(StrictModel):
    candidate_model_id: str
    backend_type: LocalModelBackendType
    benchmark_id: str
    eligibility_result: BenchmarkEligibility
    schema_validity_score: float = Field(..., ge=0, le=1)
    safety_score: float = Field(..., ge=0, le=1)
    advisory_boundary_score: float = Field(..., ge=0, le=1)
    missing_data_awareness_score: float = Field(..., ge=0, le=1)
    language_handling_score: float = Field(..., ge=0, le=1)
    json_reliability_score: float = Field(..., ge=0, le=1)
    hallucination_risk_score: float = Field(..., ge=0, le=1)
    local_advisory_suitability_score: float = Field(..., ge=0, le=1)
    overall_suitability_score: float = Field(..., ge=0, le=1)
    parse_success: bool
    matched_forbidden_patterns: list[str] = Field(default_factory=list)
    matched_safe_behavior: list[str] = Field(default_factory=list)
    fail_gate_reasons: list[str] = Field(default_factory=list)
    advisory_only: bool = True
    audit_metadata: dict = Field(default_factory=dict)


class LocalModelBenchmarkRankingEntry(StrictModel):
    rank: int = Field(..., ge=1)
    candidate_model_id: str
    benchmark_id: str
    overall_suitability_score: float = Field(..., ge=0, le=1)
    safety_score: float = Field(..., ge=0, le=1)
    advisory_boundary_score: float = Field(..., ge=0, le=1)
    eligibility_result: BenchmarkEligibility


class LocalModelBenchmarkReport(StrictModel):
    schema_version: str = "3.10-local-model-benchmark-report"
    benchmark_fixture_checksum: str
    candidate_output_fixture_checksum: str
    run_id: str
    created_at: datetime
    evaluations: list[LocalModelBenchmarkEvaluation] = Field(default_factory=list)
    rankings: list[LocalModelBenchmarkRankingEntry] = Field(default_factory=list)
    summary_counts: dict = Field(default_factory=dict)
    metadata_json: dict = Field(default_factory=lambda: dict(LOCAL_MODEL_BENCHMARK_METADATA))
    _created = field_validator("created_at")(aware)

    @field_validator("schema_version")
    @classmethod
    def exact_schema(cls, value: str) -> str:
        if value != "3.10-local-model-benchmark-report":
            raise ValueError("schema_version must be exactly 3.10-local-model-benchmark-report")
        return value
