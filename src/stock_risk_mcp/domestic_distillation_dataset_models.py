from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from pydantic import Field, field_validator, model_validator

from stock_risk_mcp.domestic_shadow_advisory_context_models import ShadowReviewAdvisoryContextBundle
from stock_risk_mcp.models import StrictModel
from stock_risk_mcp.strategy_track_models import StrategyTrack


def aware(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("timestamp must include timezone")
    return value


DOMESTIC_DISTILLATION_DATASET_METADATA = {
    "domestic_distillation_dataset_fixture_run": True,
    "strategy_track_required": True,
    "domestic_kr_only": True,
    "market_profile_resolved": True,
    "advisory_context_bundle_consumed": True,
    "distillation_dataset_records_generated": True,
    "distillation_dataset_pack_generated": True,
    "distillation_dataset_validation_generated": True,
    "distillation_dataset_gap_report_generated": True,
    "training_only_dataset_marker_present": True,
    "distillation_dataset_non_executable": True,
    "primary_label_required": True,
    "auxiliary_labels_supported": True,
    "prompt_stubs_not_executed": True,
    "llm_runtime_allowed": False,
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


UNSAFE_DATASET_LABELS = {
    "BUY",
    "SELL",
    "ENTRY",
    "EXIT",
    "ORDER",
    "TRADE_SUCCESS",
    "PROFIT_TRADE",
    "LOSS_TRADE",
    "EXECUTION_RESULT",
    "APPROVED_ENTRY",
    "EXECUTE",
}

UNSAFE_EXECUTION_PATTERNS = tuple(UNSAFE_DATASET_LABELS)


class DistillationDatasetRecordType(StrEnum):
    SCENARIO_FAMILY_RECORD = "SCENARIO_FAMILY_RECORD"
    REPLAY_WINDOW_RECORD = "REPLAY_WINDOW_RECORD"
    OBSERVATION_HORIZON_RECORD = "OBSERVATION_HORIZON_RECORD"
    BUNDLE_AGGREGATE_RECORD = "BUNDLE_AGGREGATE_RECORD"


class DistillationDatasetPrimaryLabel(StrEnum):
    LABEL_FAVORABLE_OBSERVATION = "LABEL_FAVORABLE_OBSERVATION"
    LABEL_ADVERSE_OBSERVATION = "LABEL_ADVERSE_OBSERVATION"
    LABEL_NEUTRAL_OBSERVATION = "LABEL_NEUTRAL_OBSERVATION"
    LABEL_INCONCLUSIVE_OBSERVATION = "LABEL_INCONCLUSIVE_OBSERVATION"
    LABEL_REPORT_ONLY_CONTEXT = "LABEL_REPORT_ONLY_CONTEXT"
    LABEL_BLOCKED_QUALITY_CONTEXT = "LABEL_BLOCKED_QUALITY_CONTEXT"
    LABEL_BLOCKED_PROFITABILITY_CONTEXT = "LABEL_BLOCKED_PROFITABILITY_CONTEXT"
    LABEL_BLOCKED_TECHNICAL_EVIDENCE_CONTEXT = "LABEL_BLOCKED_TECHNICAL_EVIDENCE_CONTEXT"
    LABEL_BLOCKED_RISK_CONTEXT = "LABEL_BLOCKED_RISK_CONTEXT"
    LABEL_BLOCKED_SAFETY_CONTEXT = "LABEL_BLOCKED_SAFETY_CONTEXT"
    LABEL_INSUFFICIENT_CONTEXT = "LABEL_INSUFFICIENT_CONTEXT"


class DistillationDatasetAuxiliaryLabel(StrEnum):
    AUX_REPORT_ONLY_CONTEXT = "AUX_REPORT_ONLY_CONTEXT"
    AUX_LOW_SCENARIO_COVERAGE = "AUX_LOW_SCENARIO_COVERAGE"
    AUX_LOW_SYMBOL_COVERAGE = "AUX_LOW_SYMBOL_COVERAGE"
    AUX_LOW_OBSERVATION_HORIZON_COVERAGE = "AUX_LOW_OBSERVATION_HORIZON_COVERAGE"
    AUX_SAFETY_BLOCK_PRESENT = "AUX_SAFETY_BLOCK_PRESENT"
    AUX_PROFITABILITY_BLOCK_PRESENT = "AUX_PROFITABILITY_BLOCK_PRESENT"
    AUX_TECHNICAL_EVIDENCE_BLOCK_PRESENT = "AUX_TECHNICAL_EVIDENCE_BLOCK_PRESENT"
    AUX_RISK_BLOCK_PRESENT = "AUX_RISK_BLOCK_PRESENT"
    AUX_DATA_QUALITY_WARNING = "AUX_DATA_QUALITY_WARNING"
    AUX_NON_ACTIONABLE_CONTEXT = "AUX_NON_ACTIONABLE_CONTEXT"
    AUX_TRAINING_ONLY_CONTEXT = "AUX_TRAINING_ONLY_CONTEXT"


class DistillationDatasetGapCategory(StrEnum):
    MISSING_ADVISORY_CONTEXT_BUNDLE = "MISSING_ADVISORY_CONTEXT_BUNDLE"
    MISSING_TRAINING_ONLY_MARKER = "MISSING_TRAINING_ONLY_MARKER"
    MISSING_NON_EXECUTABLE_MARKER = "MISSING_NON_EXECUTABLE_MARKER"
    MISSING_MARKET_PROFILE = "MISSING_MARKET_PROFILE"
    MISSING_PRIMARY_LABEL = "MISSING_PRIMARY_LABEL"
    UNSAFE_AUXILIARY_LABEL_DETECTED = "UNSAFE_AUXILIARY_LABEL_DETECTED"
    INSUFFICIENT_LABEL_DISTRIBUTION = "INSUFFICIENT_LABEL_DISTRIBUTION"
    INSUFFICIENT_SCENARIO_COVERAGE = "INSUFFICIENT_SCENARIO_COVERAGE"
    INSUFFICIENT_SYMBOL_COVERAGE = "INSUFFICIENT_SYMBOL_COVERAGE"
    INSUFFICIENT_OBSERVATION_HORIZON_COVERAGE = "INSUFFICIENT_OBSERVATION_HORIZON_COVERAGE"
    EXECUTABLE_WORDING_DETECTED = "EXECUTABLE_WORDING_DETECTED"
    UNSAFE_LABEL_DETECTED = "UNSAFE_LABEL_DETECTED"
    PROMPT_EXECUTION_NOT_ALLOWED = "PROMPT_EXECUTION_NOT_ALLOWED"
    LLM_RUNTIME_NOT_ALLOWED = "LLM_RUNTIME_NOT_ALLOWED"
    LOCAL_MODEL_RUNTIME_NOT_ALLOWED = "LOCAL_MODEL_RUNTIME_NOT_ALLOWED"
    ORDER_ARTIFACT_DETECTED = "ORDER_ARTIFACT_DETECTED"
    POTENTIAL_LEAKAGE_DETECTED = "POTENTIAL_LEAKAGE_DETECTED"
    UNSUPPORTED_TRACK = "UNSUPPORTED_TRACK"


class DistillationDatasetSafetyBoundary(StrictModel):
    training_only: bool = True
    non_executable: bool = True
    runtime_decision_allowed: bool = False
    llm_runtime_allowed: bool = False
    cloud_llm_called: bool = False
    local_model_runtime_called: bool = False
    prompt_stub_execution_allowed: bool = False
    no_trade_instruction: bool = True


class DistillationLabelSet(StrictModel):
    primary_label: DistillationDatasetPrimaryLabel
    auxiliary_labels: list[DistillationDatasetAuxiliaryLabel] = Field(default_factory=list)
    label_source_summary: dict = Field(default_factory=dict)


class DistillationFeatureSet(StrictModel):
    outcome_count_features: dict = Field(default_factory=dict)
    blocked_reason_features: dict = Field(default_factory=dict)
    report_only_features: dict = Field(default_factory=dict)
    non_actionable_features: dict = Field(default_factory=dict)
    coverage_features: dict = Field(default_factory=dict)
    risk_features: dict = Field(default_factory=dict)
    data_quality_features: dict = Field(default_factory=dict)
    market_profile_reference_features: dict = Field(default_factory=dict)


class DistillationPromptStub(StrictModel):
    prompt_stub_id: str = Field(..., min_length=1)
    prompt_text: str = Field(..., min_length=1)
    training_only: bool = True
    executed: bool = False
    no_trade_instruction: bool = True

    @field_validator("prompt_stub_id")
    @classmethod
    def normalize_id(cls, value: str) -> str:
        return value.strip()


class TrainingOnlyDistillationConfig(StrictModel):
    config_id: str = Field(..., min_length=1)
    strategy_track: StrategyTrack
    market_profile_id: str = Field(..., min_length=1)
    explicit_training_only_opt_in: bool
    record_unit_mode: str = Field(..., min_length=1)
    aggregate_record_inclusion_mode: str = Field(..., min_length=1)
    label_mode: str = Field(..., min_length=1)
    prompt_stub_inclusion_mode: str = Field(..., min_length=1)
    split_metadata_mode: str = Field(..., min_length=1)
    leakage_prevention_mode: str = Field(..., min_length=1)
    training_only: bool
    non_executable: bool
    runtime_decision_allowed: bool
    llm_runtime_allowed: bool
    cloud_llm_called: bool
    local_model_runtime_called: bool
    no_trade_instruction: bool

    @field_validator(
        "config_id",
        "market_profile_id",
        "record_unit_mode",
        "aggregate_record_inclusion_mode",
        "label_mode",
        "prompt_stub_inclusion_mode",
        "split_metadata_mode",
        "leakage_prevention_mode",
        mode="before",
    )
    @classmethod
    def normalize_text(cls, value):
        return str(value).strip().upper()

    @model_validator(mode="after")
    def validate_domestic_only(self):
        if self.strategy_track != StrategyTrack.DOMESTIC_KR:
            raise ValueError("distillation config requires StrategyTrack DOMESTIC_KR")
        if self.market_profile_id != "KRX":
            raise ValueError("distillation config requires market_profile_id KRX")
        if not self.explicit_training_only_opt_in:
            raise ValueError("explicit training-only opt-in is required")
        return self


class TrainingOnlyDistillationInputSet(StrictModel):
    input_set_id: str = Field(..., min_length=1)
    strategy_track: StrategyTrack
    market_profile_summary: dict = Field(default_factory=dict)
    advisory_context_bundle: ShadowReviewAdvisoryContextBundle
    source_outcome_review_report_id: str = Field(..., min_length=1)
    source_paper_shadow_journal_id: str = Field(..., min_length=1)
    source_promotion_gate_id: str = Field(..., min_length=1)
    supported_advisory_task_names: list[str] = Field(..., min_length=1)
    scenario_family_coverage: list[str] = Field(default_factory=list)
    symbol_coverage: list[str] = Field(default_factory=list)
    observation_horizon_coverage: list[str] = Field(default_factory=list)
    outcome_label_summary: dict = Field(default_factory=dict)
    blocked_report_only_non_actionable_summary: dict = Field(default_factory=dict)
    risk_summary: dict = Field(default_factory=dict)
    data_quality_summary: dict = Field(default_factory=dict)
    training_only: bool
    non_executable: bool
    prompt_stubs: list[DistillationPromptStub] = Field(default_factory=list)
    prompt_stub_execution_requested: bool = False
    runtime_decision_requested: bool = False

    @field_validator(
        "input_set_id",
        "source_outcome_review_report_id",
        "source_paper_shadow_journal_id",
        "source_promotion_gate_id",
        mode="before",
    )
    @classmethod
    def normalize_identifier(cls, value):
        return str(value).strip()

    @field_validator(
        "supported_advisory_task_names",
        "scenario_family_coverage",
        "symbol_coverage",
        "observation_horizon_coverage",
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
            raise ValueError("distillation input set requires StrategyTrack DOMESTIC_KR")
        market_id = str(self.market_profile_summary.get("market_id", "")).upper()
        if market_id != "KRX":
            raise ValueError("market_profile must resolve to KRX")
        if self.advisory_context_bundle.strategy_track != StrategyTrack.DOMESTIC_KR:
            raise ValueError("advisory_context_bundle must be DOMESTIC_KR")
        if self.advisory_context_bundle.market_profile_id != "KRX":
            raise ValueError("advisory_context_bundle must resolve to KRX")
        if self.source_outcome_review_report_id != self.advisory_context_bundle.source_outcome_review_report_id:
            raise ValueError("source_outcome_review_report_id must match advisory_context_bundle")
        if self.source_paper_shadow_journal_id != self.advisory_context_bundle.source_paper_shadow_journal_id:
            raise ValueError("source_paper_shadow_journal_id must match advisory_context_bundle")
        if self.source_promotion_gate_id != self.advisory_context_bundle.source_promotion_gate_id:
            raise ValueError("source_promotion_gate_id must match advisory_context_bundle")
        flags = [str(flag).strip().upper() for flag in self.data_quality_summary.get("data_quality_flags", [])]
        if {"UNSAFE_TRIGGER_ATTEMPT", "ORDER_TRIGGER_ATTEMPT"} & set(flags):
            raise ValueError("unsafe trigger attempt is not allowed in distillation dataset fixtures")
        return self


class TrainingOnlyDistillationPolicy(StrictModel):
    policy_id: str = Field(..., min_length=1)
    primary_record_source_modes: list[str] = Field(default_factory=list)
    aggregate_record_enabled: bool
    allowed_primary_labels: list[str] = Field(default_factory=list)
    allowed_auxiliary_labels: list[str] = Field(default_factory=list)
    forbidden_label_patterns: list[str] = Field(default_factory=list)
    prompt_stub_safety_wording_requirements: list[str] = Field(default_factory=list)
    minimum_label_distribution_count: int = Field(..., ge=1)
    minimum_scenario_coverage_count: int = Field(..., ge=1)
    minimum_symbol_coverage_count: int = Field(..., ge=1)
    minimum_observation_horizon_coverage_count: int = Field(..., ge=1)
    leakage_policy_markers: list[str] = Field(default_factory=list)

    @field_validator("policy_id", mode="before")
    @classmethod
    def normalize_text(cls, value):
        return str(value).strip().upper()

    @field_validator(
        "primary_record_source_modes",
        "allowed_primary_labels",
        "allowed_auxiliary_labels",
        "forbidden_label_patterns",
        "prompt_stub_safety_wording_requirements",
        "leakage_policy_markers",
        mode="before",
    )
    @classmethod
    def normalize_list(cls, values):
        cleaned = [str(value).strip().upper() for value in values]
        if any(not value for value in cleaned):
            raise ValueError("policy lists must not contain blank values")
        return cleaned


class DistillationDatasetRecord(StrictModel):
    record_id: str
    dataset_pack_id: str
    record_type: DistillationDatasetRecordType
    source_bundle_id: str
    source_evidence_item_ids: list[str] = Field(default_factory=list)
    source_outcome_review_report_id: str
    source_paper_shadow_journal_id: str
    source_promotion_gate_id: str
    source_sub_summary_id: str
    strategy_track: StrategyTrack
    market_profile_id: str
    scenario_family: str | None = None
    replay_window: str | None = None
    observation_horizon: str | None = None
    symbol: str | None = None
    feature_set: DistillationFeatureSet
    label_set: DistillationLabelSet
    context_summary: str | None = None
    source_trace_references: list[str] = Field(default_factory=list)
    prompt_stubs: list[DistillationPromptStub] = Field(default_factory=list)
    training_only: bool = True
    runtime_decision_allowed: bool = False
    llm_runtime_allowed: bool = False
    cloud_llm_called: bool = False
    local_model_runtime_called: bool = False
    non_executable: bool = True
    no_trade_instruction: bool = True


class DistillationDatasetPack(StrictModel):
    schema_version: str = "4.10-domestic-distillation-dataset-pack"
    pack_id: str
    source_bundle_id: str
    strategy_track: StrategyTrack
    market_profile_id: str
    record_count: int = Field(..., ge=0)
    records: list[DistillationDatasetRecord] = Field(default_factory=list)
    summary_counts: dict = Field(default_factory=dict)
    training_only: bool = True
    non_executable: bool = True
    metadata_json: dict = Field(default_factory=lambda: dict(DOMESTIC_DISTILLATION_DATASET_METADATA))


class DistillationDatasetValidationReport(StrictModel):
    schema_version: str = "4.10-domestic-distillation-dataset-validation-report"
    report_id: str
    pack_reference: str
    valid: bool
    strategy_track: StrategyTrack
    market_profile_id: str
    training_only_metadata_present: bool
    coverage_sufficient: bool
    block_reasons: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    metadata_json: dict = Field(default_factory=lambda: dict(DOMESTIC_DISTILLATION_DATASET_METADATA))


class DistillationDatasetGapReport(StrictModel):
    schema_version: str = "4.10-domestic-distillation-dataset-gap-report"
    report_id: str
    pack_reference: str
    gap_categories: list[str] = Field(default_factory=list)
    missing_marker_count: int = Field(..., ge=0)
    insufficient_coverage_count: int = Field(..., ge=0)
    unsafe_pattern_count: int = Field(..., ge=0)
    runtime_violation_count: int = Field(..., ge=0)
    metadata_json: dict = Field(default_factory=lambda: dict(DOMESTIC_DISTILLATION_DATASET_METADATA))


class DistillationDatasetSafetyReport(StrictModel):
    schema_version: str = "4.10-domestic-distillation-dataset-safety-report"
    report_id: str
    strategy_track: StrategyTrack
    safety_boundary: DistillationDatasetSafetyBoundary
    warnings: list[str] = Field(default_factory=list)
    block_reasons: list[str] = Field(default_factory=list)
    metadata_json: dict = Field(default_factory=lambda: dict(DOMESTIC_DISTILLATION_DATASET_METADATA))


class DomesticDistillationDatasetFixture(StrictModel):
    schema_version: str
    run_id: str = Field(..., min_length=1)
    created_at: datetime
    training_only_distillation_config: TrainingOnlyDistillationConfig
    training_only_distillation_input_set: TrainingOnlyDistillationInputSet
    training_only_distillation_policy: TrainingOnlyDistillationPolicy
    _created = field_validator("created_at")(aware)

    @field_validator("schema_version")
    @classmethod
    def exact_schema(cls, value: str) -> str:
        if value != "4.10-domestic-distillation-dataset-fixture":
            raise ValueError("schema_version must be exactly 4.10-domestic-distillation-dataset-fixture")
        return value

    @model_validator(mode="after")
    def validate_fixture(self):
        config = self.training_only_distillation_config
        input_set = self.training_only_distillation_input_set
        if config.strategy_track != StrategyTrack.DOMESTIC_KR or input_set.strategy_track != StrategyTrack.DOMESTIC_KR:
            raise ValueError("domestic distillation dataset fixture requires StrategyTrack DOMESTIC_KR")
        market_id = str(input_set.market_profile_summary.get("market_id", "")).upper()
        if market_id != "KRX":
            raise ValueError("market_profile must resolve to KRX")
        if not config.training_only or not input_set.training_only:
            raise ValueError("training_only marker is required")
        if not config.non_executable or not input_set.non_executable:
            raise ValueError("non_executable marker is required")
        if input_set.runtime_decision_requested:
            raise ValueError("runtime decision requests are not allowed in distillation dataset fixtures")
        return self
