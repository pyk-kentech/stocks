from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from pydantic import Field, field_validator, model_validator

from stock_risk_mcp.local_llm_advisory_models import AdvisoryTaskType
from stock_risk_mcp.models import StrictModel


def aware(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("timestamp must include timezone")
    return value


def safe_metadata(value):
    forbidden = (
        "credential",
        "token",
        "secret",
        "api_key",
        "apikey",
        "authorization",
        "cookie",
        "endpoint",
        "url",
        "account",
        "broker",
        "network",
        "order",
    )
    if isinstance(value, dict):
        if any(any(term in str(key).lower() for term in forbidden) for key in value):
            raise ValueError("runtime_metadata contains unsafe key")
        for item in value.values():
            safe_metadata(item)
    elif isinstance(value, list):
        for item in value:
            safe_metadata(item)
    return value


LOCAL_MODEL_RUNTIME_METADATA = {
    "advisory_only": True,
    "real_model_called": False,
    "mock_runtime_used": False,
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


class LocalModelBackendType(StrEnum):
    DISABLED = "DISABLED"
    MOCK_LOCAL_RUNTIME = "MOCK_LOCAL_RUNTIME"
    OLLAMA_LOCAL = "OLLAMA_LOCAL"
    LLAMACPP_LOCAL = "LLAMACPP_LOCAL"
    PYTHON_LOCAL_WRAPPER = "PYTHON_LOCAL_WRAPPER"


class LocalModelFamily(StrEnum):
    QWEN = "QWEN"
    LLAMA = "LLAMA"
    MISTRAL = "MISTRAL"
    KOREAN_SMALL = "KOREAN_SMALL"


class StructuredOutputSuitability(StrEnum):
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


class HallucinationRisk(StrEnum):
    LOWER = "LOWER"
    MEDIUM = "MEDIUM"
    HIGHER = "HIGHER"


class LocalModelRuntimeStatus(StrEnum):
    BACKEND_DISABLED = "BACKEND_DISABLED"
    MOCK_RUNTIME_READY = "MOCK_RUNTIME_READY"
    ADVISORY_RESPONSE = "ADVISORY_RESPONSE"
    SAFE_REFUSAL = "SAFE_REFUSAL"
    UNSAFE_OUTPUT_REJECTED = "UNSAFE_OUTPUT_REJECTED"
    INVALID_RUNTIME_CONFIGURATION = "INVALID_RUNTIME_CONFIGURATION"
    UNIMPLEMENTED_BACKEND_REJECTED = "UNIMPLEMENTED_BACKEND_REJECTED"
    HEALTH_CHECK_FAILED = "HEALTH_CHECK_FAILED"


class LocalModelBackendCapabilities(StrictModel):
    supports_mock_execution: bool
    supports_structured_json_output: bool
    supports_korean: bool
    supports_english: bool
    supports_mixed_language: bool
    supports_refusal_mode: bool
    supports_timeout_budget: bool
    supports_resource_budget: bool
    supports_health_check: bool
    supports_streaming: bool = False
    requires_network: bool = False
    requires_credentials: bool = False
    may_create_order: bool = False
    may_bypass_gates: bool = False

    @model_validator(mode="after")
    def enforce_safe_values(self):
        if self.requires_network:
            raise ValueError("requires_network must be false")
        if self.requires_credentials:
            raise ValueError("requires_credentials must be false")
        if self.may_create_order:
            raise ValueError("may_create_order must be false")
        if self.may_bypass_gates:
            raise ValueError("may_bypass_gates must be false")
        return self


class LocalModelRuntimeBackendConfig(StrictModel):
    backend_type: LocalModelBackendType
    adapter_name: str = Field(..., min_length=1)
    model_name: str = Field(..., min_length=1)
    model_version: str = Field(..., min_length=1)
    capabilities: LocalModelBackendCapabilities
    runtime_metadata: dict = Field(default_factory=dict)
    _safe = field_validator("runtime_metadata")(safe_metadata)


class LocalModelRuntimeRequest(StrictModel):
    task_type: AdvisoryTaskType
    ticker: str | None = None
    text_blocks: list[str] = Field(..., min_length=1)

    @field_validator("ticker")
    @classmethod
    def normalize_ticker(cls, value: str | None):
        if value is None:
            return value
        return value.strip().upper()

    @field_validator("text_blocks")
    @classmethod
    def normalize_text_blocks(cls, values: list[str]) -> list[str]:
        cleaned = [value.strip() for value in values]
        if any(not value for value in cleaned):
            raise ValueError("text_blocks must not contain blank values")
        return cleaned


class LocalModelRuntimeLimits(StrictModel):
    timeout_ms: int = Field(..., gt=0, le=60000)
    max_output_tokens: int = Field(..., gt=0, le=4096)
    max_memory_mb: int = Field(..., gt=0, le=262144)


class LocalModelRuntimeMockResponse(StrictModel):
    response_text: str = Field(..., min_length=1)
    bullet_points: list[str] = Field(default_factory=list)
    risk_labels: list[str] = Field(default_factory=list)

    @field_validator("bullet_points", "risk_labels")
    @classmethod
    def no_blank_values(cls, values: list[str]) -> list[str]:
        cleaned = [value.strip() for value in values]
        if any(not value for value in cleaned):
            raise ValueError("list values must not be blank")
        return cleaned


class LocalModelRuntimeSafetyFlags(StrictModel):
    advisory_only: bool
    may_create_order: bool
    may_bypass_gates: bool

    @model_validator(mode="after")
    def enforce_safe_values(self):
        if self.advisory_only is not True:
            raise ValueError("advisory_only must be true")
        if self.may_create_order is not False:
            raise ValueError("may_create_order must be false")
        if self.may_bypass_gates is not False:
            raise ValueError("may_bypass_gates must be false")
        return self


class LocalModelRuntimeFixture(StrictModel):
    schema_version: str
    run_id: str = Field(..., min_length=1)
    created_at: datetime
    backend: LocalModelRuntimeBackendConfig
    request: LocalModelRuntimeRequest
    runtime_limits: LocalModelRuntimeLimits
    mock_response: LocalModelRuntimeMockResponse
    safety: LocalModelRuntimeSafetyFlags
    _created = field_validator("created_at")(aware)

    @field_validator("schema_version")
    @classmethod
    def exact_schema(cls, value: str) -> str:
        if value != "3.9-local-model-runtime-fixture":
            raise ValueError("schema_version must be exactly 3.9-local-model-runtime-fixture")
        return value


class LocalModelCandidate(StrictModel):
    candidate_id: str = Field(..., min_length=1)
    backend_type: LocalModelBackendType
    model_family: LocalModelFamily
    model_class: str = Field(..., min_length=1)
    mixed_language_support: bool
    structured_output_suitability: StructuredOutputSuitability
    hallucination_risk: HallucinationRisk
    hardware_tier: str = Field(..., min_length=1)
    recommended_for_future_eval: bool
    requires_network: bool = False

    @model_validator(mode="after")
    def enforce_local_only(self):
        if self.requires_network:
            raise ValueError("requires_network must be false")
        return self


class LocalModelCandidatesFixture(StrictModel):
    schema_version: str
    run_id: str = Field(..., min_length=1)
    created_at: datetime
    candidates: list[LocalModelCandidate] = Field(..., min_length=1)
    _created = field_validator("created_at")(aware)

    @field_validator("schema_version")
    @classmethod
    def exact_schema(cls, value: str) -> str:
        if value != "3.9-local-model-candidates-fixture":
            raise ValueError("schema_version must be exactly 3.9-local-model-candidates-fixture")
        return value


class LocalModelRuntimeResult(StrictModel):
    schema_version: str = "3.9-local-model-runtime-result"
    fixture_checksum: str
    run_id: str
    created_at: datetime
    backend_type: LocalModelBackendType
    status: LocalModelRuntimeStatus
    adapter_name: str
    model_name: str
    task_type: AdvisoryTaskType
    summary_text: str | None = None
    bullet_points: list[str] = Field(default_factory=list)
    risk_labels: list[str] = Field(default_factory=list)
    refusal_reason: str | None = None
    health_metadata: dict = Field(default_factory=dict)
    capability_metadata: dict = Field(default_factory=dict)
    validation_errors: list[str] = Field(default_factory=list)
    timeout_applied_ms: int | None = None
    resource_limits_applied: dict = Field(default_factory=dict)
    audit_metadata: dict = Field(default_factory=dict)
    metadata_json: dict = Field(default_factory=lambda: dict(LOCAL_MODEL_RUNTIME_METADATA))
    _created = field_validator("created_at")(aware)

    @field_validator("schema_version")
    @classmethod
    def exact_result_schema(cls, value: str) -> str:
        if value != "3.9-local-model-runtime-result":
            raise ValueError("schema_version must be exactly 3.9-local-model-runtime-result")
        return value


class LocalModelCandidatesResult(StrictModel):
    schema_version: str = "3.9-local-model-candidates-result"
    fixture_checksum: str
    run_id: str
    created_at: datetime
    candidate_count: int = Field(..., ge=0)
    candidates: list[LocalModelCandidate] = Field(default_factory=list)
    metadata_json: dict = Field(default_factory=lambda: dict(LOCAL_MODEL_RUNTIME_METADATA))
    _created = field_validator("created_at")(aware)

    @field_validator("schema_version")
    @classmethod
    def exact_result_schema(cls, value: str) -> str:
        if value != "3.9-local-model-candidates-result":
            raise ValueError("schema_version must be exactly 3.9-local-model-candidates-result")
        return value
