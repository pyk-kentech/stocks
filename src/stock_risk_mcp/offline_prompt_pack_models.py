from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from pydantic import Field, field_validator

from stock_risk_mcp.models import StrictModel
from stock_risk_mcp.strategy_track_models import StrategyTrack


def aware(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("timestamp must include timezone")
    return value


OFFLINE_PROMPT_PACK_METADATA = {
    "prompt_pack_fixture_run": True,
    "prompt_pack_validation_run": True,
    "prompt_pack_gap_report_run": True,
    "strategy_track_required_for_trading_advisory": True,
    "market_profile_required_for_trading_advisory": True,
    "profitability_context_checked": True,
    "model_runtime_called": False,
    "cloud_llm_called": False,
    "broker_api_called": False,
    "credentials_accessed": False,
    "external_network_calls": False,
    "orders_created": False,
    "live_or_prod_used": False,
}

REQUIRED_PROFITABILITY_FIELDS = {
    "FeeTaxProfile",
    "CurrencyProfile",
    "FXCostProfile",
    "NetProfitEstimate",
    "TrackAwareProfitabilityCheck",
}


class AdvisoryTaskType(StrEnum):
    SUMMARIZE_TECHNICAL_EVIDENCE = "SUMMARIZE_TECHNICAL_EVIDENCE"
    SUMMARIZE_MARKET_DISCOVERY = "SUMMARIZE_MARKET_DISCOVERY"
    EXPLAIN_TRADE_PLAN_RISK = "EXPLAIN_TRADE_PLAN_RISK"
    IDENTIFY_MISSING_DATA = "IDENTIFY_MISSING_DATA"
    CHALLENGE_ASSUMPTIONS = "CHALLENGE_ASSUMPTIONS"
    ADVISORY_BOUNDARY_REFUSAL = "ADVISORY_BOUNDARY_REFUSAL"
    UNSAFE_INSTRUCTION_REJECTION = "UNSAFE_INSTRUCTION_REJECTION"
    JSON_ONLY_RESPONSE = "JSON_ONLY_RESPONSE"
    EXPLAIN_NET_PROFITABILITY = "EXPLAIN_NET_PROFITABILITY"


class PromptPackLanguage(StrEnum):
    KOREAN = "KOREAN"
    ENGLISH = "ENGLISH"
    MIXED = "MIXED"


class PromptPackDomain(StrEnum):
    TECHNICAL_EVIDENCE = "TECHNICAL_EVIDENCE"
    MARKET_DISCOVERY = "MARKET_DISCOVERY"
    RISK_EXPLANATION = "RISK_EXPLANATION"
    MISSING_DATA = "MISSING_DATA"
    ASSUMPTION_CHALLENGE = "ASSUMPTION_CHALLENGE"
    ADVISORY_BOUNDARY = "ADVISORY_BOUNDARY"
    SAFETY_TRAP = "SAFETY_TRAP"


class PromptTaskContextClass(StrEnum):
    GENERIC_NON_TRADING = "GENERIC_NON_TRADING"
    TRACK_AWARE_ADVISORY = "TRACK_AWARE_ADVISORY"
    TRACK_AWARE_PROFITABILITY_ADVISORY = "TRACK_AWARE_PROFITABILITY_ADVISORY"


class SafetyTrapTag(StrEnum):
    UNSAFE_INSTRUCTION_REJECTION = "UNSAFE_INSTRUCTION_REJECTION"
    ADVISORY_BOUNDARY_REFUSAL = "ADVISORY_BOUNDARY_REFUSAL"
    EXECUTION_AUTHORITY_TRAP = "EXECUTION_AUTHORITY_TRAP"
    BROKER_ACCESS_REFUSAL = "BROKER_ACCESS_REFUSAL"
    ACCOUNT_ACCESS_REFUSAL = "ACCOUNT_ACCESS_REFUSAL"
    ORDER_ACCESS_REFUSAL = "ORDER_ACCESS_REFUSAL"
    CREDENTIAL_REQUEST_REFUSAL = "CREDENTIAL_REQUEST_REFUSAL"
    NETWORK_REQUEST_REFUSAL = "NETWORK_REQUEST_REFUSAL"
    OVERCONFIDENT_RECOMMENDATION_TRAP = "OVERCONFIDENT_RECOMMENDATION_TRAP"
    INSUFFICIENT_EVIDENCE_HANDLING = "INSUFFICIENT_EVIDENCE_HANDLING"
    JSON_ONLY_RESPONSE_ENFORCEMENT = "JSON_ONLY_RESPONSE_ENFORCEMENT"
    TRACK_MISSING_FAIL_CLOSED = "TRACK_MISSING_FAIL_CLOSED"
    TRACK_AMBIGUITY_FAIL_CLOSED = "TRACK_AMBIGUITY_FAIL_CLOSED"
    MARKET_PROFILE_REQUIRED = "MARKET_PROFILE_REQUIRED"
    REPORT_ONLY_PROFITABILITY_REFUSAL = "REPORT_ONLY_PROFITABILITY_REFUSAL"
    NON_ACTIONABLE_ESTIMATE_PRESERVATION = "NON_ACTIONABLE_ESTIMATE_PRESERVATION"
    DOMESTIC_OVERSEAS_ASSUMPTION_MIX_TRAP = "DOMESTIC_OVERSEAS_ASSUMPTION_MIX_TRAP"


class PromptPackReadinessStatus(StrEnum):
    PACK_INVALID = "PACK_INVALID"
    PACK_VALID_WITH_GAPS = "PACK_VALID_WITH_GAPS"
    PACK_READY_FOR_BENCHMARK_FEED = "PACK_READY_FOR_BENCHMARK_FEED"


class PromptPackValidationSeverity(StrEnum):
    ERROR = "ERROR"
    WARNING = "WARNING"


class PromptPackSafetyBoundary(StrictModel):
    order_intent_allowed: bool
    order_draft_allowed: bool
    execution_approval_allowed: bool
    live_prod_allowed: bool
    broker_access_allowed: bool
    account_access_allowed: bool
    credential_access_allowed: bool
    network_access_allowed: bool
    cloud_llm_allowed: bool
    model_runtime_allowed: bool


class PromptTaskMarketContextRequirement(StrictModel):
    supported_tracks: list[StrategyTrack] = Field(default_factory=list)
    requires_market_profile: bool = False
    market_assumption_tags: list[str] = Field(default_factory=list)

    @field_validator("market_assumption_tags")
    @classmethod
    def no_blank_tags(cls, values: list[str]) -> list[str]:
        cleaned = [value.strip().upper() for value in values]
        if any(not value for value in cleaned):
            raise ValueError("market_assumption_tags must not contain blank values")
        return cleaned


class PromptTaskProfitabilityContextRequirement(StrictModel):
    requires_profitability_context: bool = False
    required_profitability_fields: list[str] = Field(default_factory=list)
    supports_report_only_mode: bool = False
    allows_actionable_output: bool = False

    @field_validator("required_profitability_fields")
    @classmethod
    def no_blank_fields(cls, values: list[str]) -> list[str]:
        cleaned = [value.strip() for value in values]
        if any(not value for value in cleaned):
            raise ValueError("required_profitability_fields must not contain blank values")
        return cleaned


class PromptTaskSpec(StrictModel):
    task_id: str = Field(..., min_length=1)
    task_type: AdvisoryTaskType
    language: PromptPackLanguage
    domain: PromptPackDomain
    input_fixture_reference: str = Field(..., min_length=1)
    expected_output_schema: list[str] = Field(..., min_length=1)
    expected_safe_behavior: list[str] = Field(..., min_length=1)
    forbidden_output_patterns: list[str] = Field(..., min_length=1)
    scoring_rubric_reference: str = Field(..., min_length=1)
    safety_trap_tags: list[SafetyTrapTag] = Field(..., min_length=1)
    task_context_class: PromptTaskContextClass
    supported_tracks: list[StrategyTrack] = Field(default_factory=list)
    requires_market_profile: bool = False
    requires_profitability_context: bool = False
    required_profitability_fields: list[str] = Field(default_factory=list)
    supports_report_only_mode: bool = False
    allows_actionable_output: bool = False
    market_assumption_tags: list[str] = Field(default_factory=list)

    @field_validator(
        "task_id",
        "input_fixture_reference",
        "scoring_rubric_reference",
    )
    @classmethod
    def strip_text(cls, value: str) -> str:
        return value.strip()

    @field_validator(
        "expected_output_schema",
        "expected_safe_behavior",
        "forbidden_output_patterns",
        "required_profitability_fields",
        mode="before",
    )
    @classmethod
    def list_of_non_blank_strings(cls, values):
        cleaned = [str(value).strip() for value in values]
        if any(not value for value in cleaned):
            raise ValueError("list values must not be blank")
        return cleaned

    @field_validator("market_assumption_tags", mode="before")
    @classmethod
    def normalize_tags(cls, values):
        cleaned = [str(value).strip().upper() for value in values]
        if any(not value for value in cleaned):
            raise ValueError("market_assumption_tags must not contain blank values")
        return cleaned

    def market_context_requirement(self) -> PromptTaskMarketContextRequirement:
        return PromptTaskMarketContextRequirement(
            supported_tracks=self.supported_tracks,
            requires_market_profile=self.requires_market_profile,
            market_assumption_tags=self.market_assumption_tags,
        )

    def profitability_context_requirement(self) -> PromptTaskProfitabilityContextRequirement:
        return PromptTaskProfitabilityContextRequirement(
            requires_profitability_context=self.requires_profitability_context,
            required_profitability_fields=self.required_profitability_fields,
            supports_report_only_mode=self.supports_report_only_mode,
            allows_actionable_output=self.allows_actionable_output,
        )


class PromptPack(StrictModel):
    schema_version: str
    prompt_pack_id: str = Field(..., min_length=1)
    prompt_version: str = Field(..., min_length=1)
    created_at: datetime
    safety_boundary: PromptPackSafetyBoundary
    tasks: list[PromptTaskSpec] = Field(..., min_length=1)
    _created = field_validator("created_at")(aware)

    @field_validator("schema_version")
    @classmethod
    def exact_schema(cls, value: str) -> str:
        if value != "3.12-offline-prompt-pack-fixture":
            raise ValueError("schema_version must be exactly 3.12-offline-prompt-pack-fixture")
        return value


class PromptPackValidationIssue(StrictModel):
    code: str = Field(..., min_length=1)
    message: str = Field(..., min_length=1)
    severity: PromptPackValidationSeverity = PromptPackValidationSeverity.ERROR
    task_id: str | None = None


class PromptPackValidationReport(StrictModel):
    schema_version: str = "3.12-prompt-pack-validation-report"
    prompt_pack_id: str
    valid: bool
    readiness_status: PromptPackReadinessStatus
    issues: list[PromptPackValidationIssue] = Field(default_factory=list)
    summary: dict = Field(default_factory=dict)
    metadata_json: dict = Field(default_factory=lambda: dict(OFFLINE_PROMPT_PACK_METADATA))


class PromptTaskCoverageReport(StrictModel):
    schema_version: str = "3.12-prompt-pack-coverage-report"
    prompt_pack_id: str
    total_task_count: int = Field(..., ge=0)
    task_count_by_type: dict = Field(default_factory=dict)
    task_count_by_language: dict = Field(default_factory=dict)
    task_count_by_domain: dict = Field(default_factory=dict)
    safety_trap_count_by_tag: dict = Field(default_factory=dict)
    supported_tracks_seen: list[str] = Field(default_factory=list)
    metadata_json: dict = Field(default_factory=lambda: dict(OFFLINE_PROMPT_PACK_METADATA))


class PromptPackGapReport(StrictModel):
    schema_version: str = "3.12-prompt-pack-gap-report"
    prompt_pack_id: str
    validation_passed: bool
    readiness_status: PromptPackReadinessStatus
    missing_language_coverage: list[str] = Field(default_factory=list)
    missing_domain_coverage: list[str] = Field(default_factory=list)
    missing_safety_trap_coverage: list[str] = Field(default_factory=list)
    issues: list[dict] = Field(default_factory=list)
    metadata_json: dict = Field(default_factory=lambda: dict(OFFLINE_PROMPT_PACK_METADATA))
