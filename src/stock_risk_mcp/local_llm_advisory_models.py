from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from pydantic import Field, field_validator, model_validator

from stock_risk_mcp.models import StrictModel


def aware(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("timestamp must include timezone")
    return value


def safe_metadata(value):
    forbidden = ("credential", "token", "secret", "api_key", "apikey", "authorization", "cookie", "endpoint", "url", "account", "broker", "network")
    if isinstance(value, dict):
        if any(any(term in str(key).lower() for term in forbidden) for key in value):
            raise ValueError("runtime_metadata contains unsafe key")
        for item in value.values():
            safe_metadata(item)
    elif isinstance(value, list):
        for item in value:
            safe_metadata(item)
    return value


LOCAL_LLM_ADVISORY_METADATA = {
    "advisory_only": True,
    "may_create_order": False,
    "may_bypass_gates": False,
    "orders_created": False,
    "order_intents_created": False,
    "order_drafts_created": False,
    "execution_approved": False,
    "gates_bypassed": False,
    "external_network_calls": False,
}


class AdvisoryTaskType(StrEnum):
    SUMMARIZE_TECHNICAL_EVIDENCE = "SUMMARIZE_TECHNICAL_EVIDENCE"
    SUMMARIZE_MARKET_DISCOVERY = "SUMMARIZE_MARKET_DISCOVERY"
    SUMMARIZE_LLM_SIGNAL_EVALUATION = "SUMMARIZE_LLM_SIGNAL_EVALUATION"
    EXPLAIN_TRADE_PLAN_RISK = "EXPLAIN_TRADE_PLAN_RISK"
    CHALLENGE_WEAK_ASSUMPTIONS = "CHALLENGE_WEAK_ASSUMPTIONS"
    LIST_MISSING_DATA = "LIST_MISSING_DATA"
    CLASSIFY_ADVISORY_RISK_LANGUAGE = "CLASSIFY_ADVISORY_RISK_LANGUAGE"


class AdvisoryBackendType(StrEnum):
    DISABLED = "DISABLED"
    LOCAL_MODEL = "LOCAL_MODEL"


class AdvisoryResultStatus(StrEnum):
    ADVISORY_RESPONSE = "ADVISORY_RESPONSE"
    SAFE_REFUSAL = "SAFE_REFUSAL"
    UNSAFE_OUTPUT_REJECTED = "UNSAFE_OUTPUT_REJECTED"
    INVALID_REQUEST = "INVALID_REQUEST"
    BACKEND_DISABLED = "BACKEND_DISABLED"


class LocalLLMAdvisoryBackendConfig(StrictModel):
    backend_type: AdvisoryBackendType
    model_name: str = Field(..., min_length=1)
    model_version: str = Field(..., min_length=1)
    runtime_metadata: dict = Field(default_factory=dict)
    _safe = field_validator("runtime_metadata")(safe_metadata)


class LocalLLMAdvisoryPromptMetadata(StrictModel):
    prompt_id: str = Field(..., min_length=1)
    prompt_version: str = Field(..., min_length=1)
    prompt_checksum: str = Field(..., min_length=1)


class LocalLLMAdvisoryInputs(StrictModel):
    ticker: str | None = None
    title: str = Field(..., min_length=1)
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


class LocalLLMAdvisorySafetyFlags(StrictModel):
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


class LocalLLMAdvisoryFixture(StrictModel):
    schema_version: str
    run_id: str = Field(..., min_length=1)
    created_at: datetime
    task_type: AdvisoryTaskType
    backend: LocalLLMAdvisoryBackendConfig
    prompt_metadata: LocalLLMAdvisoryPromptMetadata
    inputs: LocalLLMAdvisoryInputs
    safety: LocalLLMAdvisorySafetyFlags
    _created = field_validator("created_at")(aware)

    @field_validator("schema_version")
    @classmethod
    def exact_schema(cls, value: str) -> str:
        if value != "3.8-local-llm-advisory-fixture":
            raise ValueError("schema_version must be exactly 3.8-local-llm-advisory-fixture")
        return value


class LocalLLMAdvisoryResult(StrictModel):
    schema_version: str = "3.8-local-llm-advisory-result"
    fixture_checksum: str
    run_id: str
    created_at: datetime
    task_type: AdvisoryTaskType
    backend_type: AdvisoryBackendType
    status: AdvisoryResultStatus
    summary_text: str | None = None
    bullet_points: list[str] = Field(default_factory=list)
    risk_language_classification: str | None = None
    missing_data_items: list[str] = Field(default_factory=list)
    challenge_points: list[str] = Field(default_factory=list)
    refusal_reason: str | None = None
    metadata_json: dict = Field(default_factory=lambda: dict(LOCAL_LLM_ADVISORY_METADATA))
    _created = field_validator("created_at")(aware)

    @field_validator("schema_version")
    @classmethod
    def exact_result_schema(cls, value: str) -> str:
        if value != "3.8-local-llm-advisory-result":
            raise ValueError("schema_version must be exactly 3.8-local-llm-advisory-result")
        return value
