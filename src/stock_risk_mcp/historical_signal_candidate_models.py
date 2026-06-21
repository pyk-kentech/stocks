from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from pydantic import Field, field_validator, model_validator

from stock_risk_mcp.historical_signal_candidate_guard import validate_historical_signal_candidate_metadata_safety
from stock_risk_mcp.models import StrictModel
from stock_risk_mcp.strategy_track_models import StrategyTrack


def aware(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("timestamp must include timezone")
    return value


def _upper_required(value, field_name: str) -> str:
    if value is None:
        raise ValueError(f"{field_name} must not be null")
    cleaned = str(value).strip().upper()
    if not cleaned:
        raise ValueError(f"{field_name} must not be blank")
    return cleaned


def _string_required(value, field_name: str) -> str:
    if value is None:
        raise ValueError(f"{field_name} must not be null")
    cleaned = str(value).strip()
    if not cleaned:
        raise ValueError(f"{field_name} must not be blank")
    return cleaned


def _normalize_id_list(value, field_name: str) -> list[str]:
    if value is None:
        return []
    if isinstance(value, (str, bytes)) or not isinstance(value, list):
        raise ValueError(f"{field_name} must be a list")
    return [_upper_required(item, field_name) for item in value]


def _validate_local_path(value: str, field_name: str) -> str:
    cleaned = _string_required(value, field_name)
    lowered = cleaned.lower()
    if "://" in lowered or lowered.startswith("//"):
        raise ValueError(f"{field_name} must be a local file path")
    if lowered.endswith(".parquet"):
        raise ValueError("parquet remains unsupported")
    return cleaned


def _validate_safety_flags(model, context: str):
    for flag_name in (
        "read_only",
        "report_only",
        "non_executable",
        "local_file_only",
        "offline_only",
        "no_network",
        "no_provider_api",
        "no_order",
        "no_broker_path",
        "no_live_prod",
        "no_cloud_llm",
        "no_local_llm_runtime",
        "no_runtime_trading_signal",
        "no_order_candidate",
        "no_live_inference",
        "no_deployment",
        "no_paper_trading",
    ):
        if not getattr(model, flag_name):
            raise ValueError(f"{context} must remain {flag_name}")
    return model


def _validate_outcome_label(value, field_name: str) -> str:
    cleaned = _upper_required(value, field_name)
    if cleaned in {"BUY", "SELL", "HOLD", "ENTRY", "EXIT", "LONG", "SHORT", "ORDER"}:
        raise ValueError("predicted outcome label must remain an outcome label")
    return cleaned


class HistoricalSignalCandidateScoreBucket(StrEnum):
    VERY_LOW = "VERY_LOW"
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    VERY_HIGH = "VERY_HIGH"


class HistoricalSignalCandidateConfidenceBucket(StrEnum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    UNKNOWN = "UNKNOWN"


class HistoricalSignalCandidateGapCategory(StrEnum):
    SIGNAL_CANDIDATE_REPORT_GENERATED = "SIGNAL_CANDIDATE_REPORT_GENERATED"
    SIGNAL_CANDIDATE_REPORT_ONLY = "SIGNAL_CANDIDATE_REPORT_ONLY"
    SIGNAL_CANDIDATE_LOCAL_ONLY = "SIGNAL_CANDIDATE_LOCAL_ONLY"
    SIGNAL_CANDIDATE_OFFLINE_ONLY = "SIGNAL_CANDIDATE_OFFLINE_ONLY"
    SIGNAL_CANDIDATE_NON_EXECUTABLE = "SIGNAL_CANDIDATE_NON_EXECUTABLE"
    SIGNAL_CANDIDATE_MISSING_INPUT = "SIGNAL_CANDIDATE_MISSING_INPUT"
    SIGNAL_CANDIDATE_MISSING_EXPERIMENT_REF = "SIGNAL_CANDIDATE_MISSING_EXPERIMENT_REF"
    SIGNAL_CANDIDATE_MISSING_MODEL_REF = "SIGNAL_CANDIDATE_MISSING_MODEL_REF"
    SIGNAL_CANDIDATE_MISSING_METRICS_REF = "SIGNAL_CANDIDATE_MISSING_METRICS_REF"
    SIGNAL_CANDIDATE_MISSING_ARTIFACT_REF = "SIGNAL_CANDIDATE_MISSING_ARTIFACT_REF"
    SIGNAL_CANDIDATE_MISSING_RISK_REVIEW_REF = "SIGNAL_CANDIDATE_MISSING_RISK_REVIEW_REF"
    SIGNAL_CANDIDATE_MISSING_PROMOTION_BLOCK_REF = "SIGNAL_CANDIDATE_MISSING_PROMOTION_BLOCK_REF"
    SIGNAL_CANDIDATE_MISSING_DATASET_LINEAGE = "SIGNAL_CANDIDATE_MISSING_DATASET_LINEAGE"
    SIGNAL_CANDIDATE_MISSING_SPLIT_LINEAGE = "SIGNAL_CANDIDATE_MISSING_SPLIT_LINEAGE"
    SIGNAL_CANDIDATE_INVALID_SCORE = "SIGNAL_CANDIDATE_INVALID_SCORE"
    SIGNAL_CANDIDATE_INVALID_CONFIDENCE_BUCKET = "SIGNAL_CANDIDATE_INVALID_CONFIDENCE_BUCKET"
    SIGNAL_CANDIDATE_INVALID_OUTCOME_LABEL = "SIGNAL_CANDIDATE_INVALID_OUTCOME_LABEL"
    SIGNAL_CANDIDATE_RUNTIME_SIGNAL_NOT_ALLOWED = "SIGNAL_CANDIDATE_RUNTIME_SIGNAL_NOT_ALLOWED"
    SIGNAL_CANDIDATE_ORDER_CANDIDATE_NOT_ALLOWED = "SIGNAL_CANDIDATE_ORDER_CANDIDATE_NOT_ALLOWED"
    SIGNAL_CANDIDATE_BUY_SELL_WORDING_NOT_ALLOWED = "SIGNAL_CANDIDATE_BUY_SELL_WORDING_NOT_ALLOWED"
    SIGNAL_CANDIDATE_ORDER_FIELD_NOT_ALLOWED = "SIGNAL_CANDIDATE_ORDER_FIELD_NOT_ALLOWED"
    SIGNAL_CANDIDATE_POSITION_FIELD_NOT_ALLOWED = "SIGNAL_CANDIDATE_POSITION_FIELD_NOT_ALLOWED"
    SIGNAL_CANDIDATE_PAPER_TRADING_NOT_ALLOWED = "SIGNAL_CANDIDATE_PAPER_TRADING_NOT_ALLOWED"
    SIGNAL_CANDIDATE_BROKER_PATH_NOT_ALLOWED = "SIGNAL_CANDIDATE_BROKER_PATH_NOT_ALLOWED"
    SIGNAL_CANDIDATE_LIVE_INFERENCE_NOT_ALLOWED = "SIGNAL_CANDIDATE_LIVE_INFERENCE_NOT_ALLOWED"
    SIGNAL_CANDIDATE_DEPLOYMENT_NOT_ALLOWED = "SIGNAL_CANDIDATE_DEPLOYMENT_NOT_ALLOWED"
    SIGNAL_CANDIDATE_NETWORK_NOT_ALLOWED = "SIGNAL_CANDIDATE_NETWORK_NOT_ALLOWED"
    SIGNAL_CANDIDATE_PROVIDER_API_NOT_ALLOWED = "SIGNAL_CANDIDATE_PROVIDER_API_NOT_ALLOWED"
    SIGNAL_CANDIDATE_CLOUD_LLM_NOT_ALLOWED = "SIGNAL_CANDIDATE_CLOUD_LLM_NOT_ALLOWED"
    SIGNAL_CANDIDATE_LOCAL_LLM_RUNTIME_NOT_ALLOWED = "SIGNAL_CANDIDATE_LOCAL_LLM_RUNTIME_NOT_ALLOWED"
    SIGNAL_CANDIDATE_LIVE_PROD_NOT_ALLOWED = "SIGNAL_CANDIDATE_LIVE_PROD_NOT_ALLOWED"
    SIGNAL_CANDIDATE_PARQUET_NOT_ALLOWED = "SIGNAL_CANDIDATE_PARQUET_NOT_ALLOWED"


class HistoricalSignalCandidateConfig(StrictModel):
    config_id: str = Field(..., min_length=1)
    strategy_track: StrategyTrack
    read_only: bool = True
    report_only: bool = True
    non_executable: bool = True
    local_file_only: bool = True
    offline_only: bool = True
    no_network: bool = True
    no_provider_api: bool = True
    no_order: bool = True
    no_broker_path: bool = True
    no_live_prod: bool = True
    no_cloud_llm: bool = True
    no_local_llm_runtime: bool = True
    no_runtime_trading_signal: bool = True
    no_order_candidate: bool = True
    no_live_inference: bool = True
    no_deployment: bool = True
    no_paper_trading: bool = True

    @field_validator("config_id", mode="before")
    @classmethod
    def normalize_config_id(cls, value):
        return _upper_required(value, "config_id")

    @model_validator(mode="after")
    def validate_config(self):
        if self.strategy_track != StrategyTrack.DOMESTIC_KR:
            raise ValueError("historical signal candidate config requires StrategyTrack DOMESTIC_KR")
        return _validate_safety_flags(self, "historical signal candidate config")


class HistoricalSignalCandidateSourceRef(StrictModel):
    source_ref_id: str = Field(..., min_length=1)
    symbol: str = Field(..., min_length=1)
    timestamp: datetime
    source_model_id: str = Field(..., min_length=1)
    source_experiment_id: str = Field(..., min_length=1)
    source_metrics_report_id: str = Field(..., min_length=1)
    source_artifact_manifest_id: str = Field(..., min_length=1)
    source_risk_review_id: str = Field(..., min_length=1)
    source_promotion_block_id: str = Field(..., min_length=1)
    dataset_lineage_id: str = Field(..., min_length=1)
    split_lineage_id: str = Field(..., min_length=1)
    score: float
    score_bucket: HistoricalSignalCandidateScoreBucket
    confidence_bucket: HistoricalSignalCandidateConfidenceBucket
    predicted_outcome_label: str = Field(..., min_length=1)
    horizon: str = Field(..., min_length=1)
    feature_schema_version: str = Field(..., min_length=1)
    label_schema_version: str = Field(..., min_length=1)
    explanation_summary: str = Field(..., min_length=1)
    source_manifest_ids: list[str] = Field(default_factory=list)
    source_audit_record_ids: list[str] = Field(default_factory=list)
    provider_provenance_ids: list[str] = Field(default_factory=list)
    metadata: dict[str, object] = Field(default_factory=dict)
    read_only: bool = True
    report_only: bool = True
    non_executable: bool = True
    local_file_only: bool = True
    offline_only: bool = True
    no_network: bool = True
    no_provider_api: bool = True
    no_order: bool = True
    no_broker_path: bool = True
    no_live_prod: bool = True
    no_cloud_llm: bool = True
    no_local_llm_runtime: bool = True
    no_runtime_trading_signal: bool = True
    no_order_candidate: bool = True
    no_live_inference: bool = True
    no_deployment: bool = True
    no_paper_trading: bool = True

    @field_validator(
        "source_ref_id",
        "source_model_id",
        "source_experiment_id",
        "source_metrics_report_id",
        "source_artifact_manifest_id",
        "source_risk_review_id",
        "source_promotion_block_id",
        "dataset_lineage_id",
        "split_lineage_id",
        "predicted_outcome_label",
        "horizon",
        "feature_schema_version",
        "label_schema_version",
        mode="before",
    )
    @classmethod
    def normalize_ids(cls, value, info):
        if info.field_name == "predicted_outcome_label":
            return _validate_outcome_label(value, info.field_name)
        return _upper_required(value, info.field_name)

    @field_validator("symbol", "explanation_summary", mode="before")
    @classmethod
    def normalize_strings(cls, value, info):
        return _string_required(value, info.field_name)

    @field_validator("timestamp")
    @classmethod
    def validate_timestamp(cls, value):
        return aware(value)

    @field_validator("source_manifest_ids", "source_audit_record_ids", "provider_provenance_ids", mode="before")
    @classmethod
    def normalize_lists(cls, value, info):
        return _normalize_id_list(value, info.field_name)

    @field_validator("metadata", mode="before")
    @classmethod
    def validate_metadata(cls, value):
        return validate_historical_signal_candidate_metadata_safety(value or {}, context="historical signal candidate")

    @model_validator(mode="after")
    def validate_source_ref(self):
        return _validate_safety_flags(self, "historical signal candidate source ref")


class HistoricalSignalCandidateScore(StrictModel):
    score: float = Field(..., ge=0.0, le=1.0)
    score_bucket: HistoricalSignalCandidateScoreBucket
    confidence_bucket: HistoricalSignalCandidateConfidenceBucket
    predicted_outcome_label: str = Field(..., min_length=1)
    horizon: str = Field(..., min_length=1)

    @field_validator("predicted_outcome_label", mode="before")
    @classmethod
    def validate_label(cls, value):
        return _validate_outcome_label(value, "predicted_outcome_label")

    @field_validator("horizon", mode="before")
    @classmethod
    def validate_horizon(cls, value):
        return _upper_required(value, "horizon")


class HistoricalSignalCandidate(StrictModel):
    candidate_id: str = Field(..., min_length=1)
    source_ref_id: str = Field(..., min_length=1)
    symbol: str = Field(..., min_length=1)
    timestamp: datetime
    source_model_id: str = Field(..., min_length=1)
    source_experiment_id: str = Field(..., min_length=1)
    source_metrics_report_id: str = Field(..., min_length=1)
    source_artifact_manifest_id: str = Field(..., min_length=1)
    source_risk_review_id: str = Field(..., min_length=1)
    source_promotion_block_id: str = Field(..., min_length=1)
    dataset_lineage_id: str = Field(..., min_length=1)
    split_lineage_id: str = Field(..., min_length=1)
    score: HistoricalSignalCandidateScore
    feature_schema_version: str = Field(..., min_length=1)
    label_schema_version: str = Field(..., min_length=1)
    explanation_summary: str = Field(..., min_length=1)
    source_manifest_ids: list[str] = Field(default_factory=list)
    source_audit_record_ids: list[str] = Field(default_factory=list)
    provider_provenance_ids: list[str] = Field(default_factory=list)
    read_only: bool = True
    report_only: bool = True
    non_executable: bool = True
    local_file_only: bool = True
    offline_only: bool = True
    no_network: bool = True
    no_provider_api: bool = True
    no_order: bool = True
    no_broker_path: bool = True
    no_live_prod: bool = True
    no_cloud_llm: bool = True
    no_local_llm_runtime: bool = True
    no_runtime_trading_signal: bool = True
    no_order_candidate: bool = True
    no_live_inference: bool = True
    no_deployment: bool = True
    no_paper_trading: bool = True

    @field_validator(
        "candidate_id",
        "source_ref_id",
        "source_model_id",
        "source_experiment_id",
        "source_metrics_report_id",
        "source_artifact_manifest_id",
        "source_risk_review_id",
        "source_promotion_block_id",
        "dataset_lineage_id",
        "split_lineage_id",
        "feature_schema_version",
        "label_schema_version",
        mode="before",
    )
    @classmethod
    def normalize_ids(cls, value, info):
        return _upper_required(value, info.field_name)

    @field_validator("symbol", "explanation_summary", mode="before")
    @classmethod
    def normalize_strings(cls, value, info):
        return _string_required(value, info.field_name)

    @field_validator("timestamp")
    @classmethod
    def validate_timestamp(cls, value):
        return aware(value)

    @field_validator("source_manifest_ids", "source_audit_record_ids", "provider_provenance_ids", mode="before")
    @classmethod
    def normalize_lists(cls, value, info):
        return _normalize_id_list(value, info.field_name)

    @model_validator(mode="after")
    def validate_candidate(self):
        return _validate_safety_flags(self, "historical signal candidate")


class HistoricalSignalCandidateBatch(StrictModel):
    candidate_batch_id: str = Field(..., min_length=1)
    signal_candidate_input_id: str = Field(..., min_length=1)
    candidates: list[HistoricalSignalCandidate] = Field(default_factory=list)
    accepted_candidate_count: int = Field(default=0, ge=0)
    rejected_candidate_count: int = Field(default=0, ge=0)
    read_only: bool = True
    report_only: bool = True
    non_executable: bool = True
    local_file_only: bool = True
    offline_only: bool = True
    no_network: bool = True
    no_provider_api: bool = True
    no_order: bool = True
    no_broker_path: bool = True
    no_live_prod: bool = True
    no_cloud_llm: bool = True
    no_local_llm_runtime: bool = True
    no_runtime_trading_signal: bool = True
    no_order_candidate: bool = True
    no_live_inference: bool = True
    no_deployment: bool = True
    no_paper_trading: bool = True

    @field_validator("candidate_batch_id", "signal_candidate_input_id", mode="before")
    @classmethod
    def normalize_ids(cls, value, info):
        return _upper_required(value, info.field_name)

    @model_validator(mode="after")
    def validate_batch(self):
        return _validate_safety_flags(self, "historical signal candidate batch")


class HistoricalSignalCandidateReport(StrictModel):
    candidate_report_id: str = Field(..., min_length=1)
    signal_candidate_input_id: str = Field(..., min_length=1)
    candidate_count: int = Field(default=0, ge=0)
    accepted_candidate_count: int = Field(default=0, ge=0)
    rejected_candidate_count: int = Field(default=0, ge=0)
    gap_counts: dict[str, int] = Field(default_factory=dict)
    safety_flag_summary: dict[str, bool] = Field(default_factory=dict)
    score_bucket_distribution: dict[str, int] = Field(default_factory=dict)
    confidence_bucket_distribution: dict[str, int] = Field(default_factory=dict)
    outcome_label_distribution: dict[str, int] = Field(default_factory=dict)
    lineage_coverage_summary: dict[str, int] = Field(default_factory=dict)
    blocked_execution_summary: dict[str, bool] = Field(default_factory=dict)
    read_only: bool = True
    report_only: bool = True
    non_executable: bool = True
    local_file_only: bool = True
    offline_only: bool = True
    no_network: bool = True
    no_provider_api: bool = True
    no_order: bool = True
    no_broker_path: bool = True
    no_live_prod: bool = True
    no_cloud_llm: bool = True
    no_local_llm_runtime: bool = True
    no_runtime_trading_signal: bool = True
    no_order_candidate: bool = True
    no_live_inference: bool = True
    no_deployment: bool = True
    no_paper_trading: bool = True

    @field_validator("candidate_report_id", "signal_candidate_input_id", mode="before")
    @classmethod
    def normalize_ids(cls, value, info):
        return _upper_required(value, info.field_name)

    @model_validator(mode="after")
    def validate_report(self):
        return _validate_safety_flags(self, "historical signal candidate report")


class HistoricalSignalCandidateSafetyReport(StrictModel):
    safety_report_id: str = Field(..., min_length=1)
    signal_candidate_input_id: str = Field(..., min_length=1)
    blocked_runtime_signal_count: int = Field(default=0, ge=0)
    blocked_order_candidate_count: int = Field(default=0, ge=0)
    blocked_paper_trading_count: int = Field(default=0, ge=0)
    blocked_live_inference_count: int = Field(default=0, ge=0)
    blocked_deployment_count: int = Field(default=0, ge=0)
    blocked_broker_path_count: int = Field(default=0, ge=0)
    read_only: bool = True
    report_only: bool = True
    non_executable: bool = True
    local_file_only: bool = True
    offline_only: bool = True
    no_network: bool = True
    no_provider_api: bool = True
    no_order: bool = True
    no_broker_path: bool = True
    no_live_prod: bool = True
    no_cloud_llm: bool = True
    no_local_llm_runtime: bool = True
    no_runtime_trading_signal: bool = True
    no_order_candidate: bool = True
    no_live_inference: bool = True
    no_deployment: bool = True
    no_paper_trading: bool = True

    @field_validator("safety_report_id", "signal_candidate_input_id", mode="before")
    @classmethod
    def normalize_ids(cls, value, info):
        return _upper_required(value, info.field_name)

    @model_validator(mode="after")
    def validate_safety_report(self):
        return _validate_safety_flags(self, "historical signal candidate safety report")


class HistoricalSignalCandidateGapReport(StrictModel):
    gap_report_id: str = Field(..., min_length=1)
    signal_candidate_input_id: str = Field(..., min_length=1)
    gap_status: str = Field(default="NO_GAPS", min_length=1)
    gap_categories: list[str] = Field(default_factory=list)
    blocking_gap_count: int = Field(default=0, ge=0)
    report_only_gap_count: int = Field(default=0, ge=0)
    gaps: list[dict[str, str]] = Field(default_factory=list)
    read_only: bool = True
    report_only: bool = True
    non_executable: bool = True
    local_file_only: bool = True
    offline_only: bool = True
    no_network: bool = True
    no_provider_api: bool = True
    no_order: bool = True
    no_broker_path: bool = True
    no_live_prod: bool = True
    no_cloud_llm: bool = True
    no_local_llm_runtime: bool = True
    no_runtime_trading_signal: bool = True
    no_order_candidate: bool = True
    no_live_inference: bool = True
    no_deployment: bool = True
    no_paper_trading: bool = True

    @field_validator("gap_report_id", "signal_candidate_input_id", "gap_status", mode="before")
    @classmethod
    def normalize_fields(cls, value, info):
        return _upper_required(value, info.field_name)

    @field_validator("gap_categories", mode="before")
    @classmethod
    def normalize_gap_categories(cls, value, info):
        return _normalize_id_list(value, info.field_name)

    @model_validator(mode="after")
    def validate_gap_report(self):
        return _validate_safety_flags(self, "historical signal candidate gap report")


class HistoricalSignalCandidateAuditRecord(StrictModel):
    audit_record_id: str = Field(..., min_length=1)
    signal_candidate_input_id: str = Field(..., min_length=1)
    created_at: datetime
    operator_context: str = Field(..., min_length=1)
    source_path: str = Field(..., min_length=1)
    source_manifest_ids: list[str] = Field(default_factory=list)
    source_audit_record_ids: list[str] = Field(default_factory=list)
    provider_provenance_ids: list[str] = Field(default_factory=list)

    @field_validator("audit_record_id", "signal_candidate_input_id", "operator_context", mode="before")
    @classmethod
    def normalize_ids(cls, value, info):
        return _upper_required(value, info.field_name)

    @field_validator("created_at")
    @classmethod
    def validate_created_at(cls, value):
        return aware(value)

    @field_validator("source_path", mode="before")
    @classmethod
    def validate_source_path(cls, value):
        return _validate_local_path(value, "source_path")

    @field_validator("source_manifest_ids", "source_audit_record_ids", "provider_provenance_ids", mode="before")
    @classmethod
    def normalize_lists(cls, value, info):
        return _normalize_id_list(value, info.field_name)


class HistoricalSignalCandidateInput(StrictModel):
    schema_version: str = Field(..., min_length=1)
    signal_candidate_input_id: str = Field(..., min_length=1)
    signal_candidate_config: HistoricalSignalCandidateConfig
    source_refs: list[HistoricalSignalCandidateSourceRef] = Field(default_factory=list)
    candidate_batch: HistoricalSignalCandidateBatch
    candidate_report: HistoricalSignalCandidateReport
    safety_report: HistoricalSignalCandidateSafetyReport
    gap_report: HistoricalSignalCandidateGapReport
    audit_records: list[HistoricalSignalCandidateAuditRecord] = Field(default_factory=list)

    @field_validator("schema_version", "signal_candidate_input_id", mode="before")
    @classmethod
    def normalize_ids(cls, value, info):
        return _upper_required(value, info.field_name)

