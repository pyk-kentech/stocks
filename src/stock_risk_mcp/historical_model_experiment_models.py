from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from pydantic import Field, field_validator, model_validator

from stock_risk_mcp.historical_dataset_readiness_models import HistoricalDatasetBaselineEvaluationReport
from stock_risk_mcp.historical_dataset_validation_models import (
    HistoricalDatasetLeakageAuditReport,
    HistoricalDatasetSplitManifest,
)
from stock_risk_mcp.historical_model_training_models import (
    HistoricalModelArtifactManifest,
    HistoricalModelEvaluationReport,
    HistoricalModelMetricsReport,
    HistoricalModelTrainingGapReport,
    HistoricalModelTrainingModelType,
    HistoricalModelTrainingRunReport,
    HistoricalModelTrainingSafetyReport,
)
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
    ):
        if not getattr(model, flag_name):
            raise ValueError(f"{context} must remain {flag_name}")
    return model


def _reject_unsafe_metadata(value, field_name: str):
    if value is None:
        return {}
    if not isinstance(value, dict):
        raise ValueError(f"{field_name} must be a dict")
    blocked_needles = (
        "deployment",
        "live_inference",
        "runtime_signal",
        "order_candidate",
        "order",
        "broker",
        "account",
        "credential",
        "token",
        "secret",
        "buy",
        "sell",
        "entry",
        "exit",
        "network",
        "api",
        "provider",
        "cloud_llm",
        "gemini",
        "openai",
        "local_llm",
        "ollama",
        "crawler",
        "live",
        "prod",
        "parquet",
    )
    for key, raw in value.items():
        haystack = f"{key} {raw}".lower()
        if any(needle in haystack for needle in blocked_needles):
            raise ValueError(f"{field_name} contains unsafe metadata")
    return value


class HistoricalModelExperimentGapCategory(StrEnum):
    EXPERIMENT_REGISTRY_REPORT_GENERATED = "EXPERIMENT_REGISTRY_REPORT_GENERATED"
    EXPERIMENT_REPORT_ONLY = "EXPERIMENT_REPORT_ONLY"
    EXPERIMENT_LOCAL_ONLY = "EXPERIMENT_LOCAL_ONLY"
    EXPERIMENT_OFFLINE_ONLY = "EXPERIMENT_OFFLINE_ONLY"
    EXPERIMENT_MISSING_INPUT = "EXPERIMENT_MISSING_INPUT"
    EXPERIMENT_MISSING_TRAINING_RUN_REPORT = "EXPERIMENT_MISSING_TRAINING_RUN_REPORT"
    EXPERIMENT_MISSING_EVALUATION_REPORT = "EXPERIMENT_MISSING_EVALUATION_REPORT"
    EXPERIMENT_MISSING_METRICS_REPORT = "EXPERIMENT_MISSING_METRICS_REPORT"
    EXPERIMENT_MISSING_ARTIFACT_MANIFEST = "EXPERIMENT_MISSING_ARTIFACT_MANIFEST"
    EXPERIMENT_MISSING_SAFETY_REPORT = "EXPERIMENT_MISSING_SAFETY_REPORT"
    EXPERIMENT_MISSING_DATASET_LINEAGE = "EXPERIMENT_MISSING_DATASET_LINEAGE"
    EXPERIMENT_MISSING_SPLIT_LINEAGE = "EXPERIMENT_MISSING_SPLIT_LINEAGE"
    EXPERIMENT_MISSING_LEAKAGE_AUDIT_LINEAGE = "EXPERIMENT_MISSING_LEAKAGE_AUDIT_LINEAGE"
    EXPERIMENT_UNSUPPORTED_MODEL_TYPE = "EXPERIMENT_UNSUPPORTED_MODEL_TYPE"
    EXPERIMENT_OVERFIT_RISK_DETECTED = "EXPERIMENT_OVERFIT_RISK_DETECTED"
    EXPERIMENT_LOW_LABEL_SUPPORT = "EXPERIMENT_LOW_LABEL_SUPPORT"
    EXPERIMENT_SEVERE_LABEL_IMBALANCE = "EXPERIMENT_SEVERE_LABEL_IMBALANCE"
    EXPERIMENT_TRAIN_TEST_METRIC_GAP = "EXPERIMENT_TRAIN_TEST_METRIC_GAP"
    EXPERIMENT_WEAK_BASELINE_IMPROVEMENT = "EXPERIMENT_WEAK_BASELINE_IMPROVEMENT"
    EXPERIMENT_OPTIONAL_SKLEARN_DEPENDENCY_RISK = "EXPERIMENT_OPTIONAL_SKLEARN_DEPENDENCY_RISK"
    EXPERIMENT_UNSAFE_ARTIFACT_METADATA = "EXPERIMENT_UNSAFE_ARTIFACT_METADATA"
    EXPERIMENT_MISSING_SAFETY_FLAGS = "EXPERIMENT_MISSING_SAFETY_FLAGS"
    EXPERIMENT_PROMOTION_BLOCK_GENERATED = "EXPERIMENT_PROMOTION_BLOCK_GENERATED"
    EXPERIMENT_PRODUCTION_USE_BLOCKED = "EXPERIMENT_PRODUCTION_USE_BLOCKED"
    EXPERIMENT_LIVE_INFERENCE_BLOCKED = "EXPERIMENT_LIVE_INFERENCE_BLOCKED"
    EXPERIMENT_RUNTIME_SIGNAL_BLOCKED = "EXPERIMENT_RUNTIME_SIGNAL_BLOCKED"
    EXPERIMENT_ORDER_CANDIDATE_BLOCKED = "EXPERIMENT_ORDER_CANDIDATE_BLOCKED"
    EXPERIMENT_PAPER_TRADING_BLOCKED = "EXPERIMENT_PAPER_TRADING_BLOCKED"
    EXPERIMENT_DEPLOYMENT_BLOCKED = "EXPERIMENT_DEPLOYMENT_BLOCKED"
    EXPERIMENT_PRODUCTION_DEPLOYMENT_NOT_ALLOWED = "EXPERIMENT_PRODUCTION_DEPLOYMENT_NOT_ALLOWED"
    EXPERIMENT_LIVE_INFERENCE_NOT_ALLOWED = "EXPERIMENT_LIVE_INFERENCE_NOT_ALLOWED"
    EXPERIMENT_RUNTIME_SIGNAL_DETECTED = "EXPERIMENT_RUNTIME_SIGNAL_DETECTED"
    EXPERIMENT_ORDER_CANDIDATE_DETECTED = "EXPERIMENT_ORDER_CANDIDATE_DETECTED"
    EXPERIMENT_ORDER_FIELD_DETECTED = "EXPERIMENT_ORDER_FIELD_DETECTED"
    EXPERIMENT_BUY_SELL_WORDING_DETECTED = "EXPERIMENT_BUY_SELL_WORDING_DETECTED"
    EXPERIMENT_BROKER_PATH_NOT_ALLOWED = "EXPERIMENT_BROKER_PATH_NOT_ALLOWED"
    EXPERIMENT_ACCOUNT_METADATA_NOT_ALLOWED = "EXPERIMENT_ACCOUNT_METADATA_NOT_ALLOWED"
    EXPERIMENT_CREDENTIALS_NOT_ALLOWED = "EXPERIMENT_CREDENTIALS_NOT_ALLOWED"
    EXPERIMENT_REMOTE_SOURCE_NOT_ALLOWED = "EXPERIMENT_REMOTE_SOURCE_NOT_ALLOWED"
    EXPERIMENT_API_SOURCE_NOT_ALLOWED = "EXPERIMENT_API_SOURCE_NOT_ALLOWED"
    EXPERIMENT_NETWORK_SOURCE_NOT_ALLOWED = "EXPERIMENT_NETWORK_SOURCE_NOT_ALLOWED"
    EXPERIMENT_PROVIDER_SOURCE_NOT_ALLOWED = "EXPERIMENT_PROVIDER_SOURCE_NOT_ALLOWED"
    EXPERIMENT_CLOUD_LLM_NOT_ALLOWED = "EXPERIMENT_CLOUD_LLM_NOT_ALLOWED"
    EXPERIMENT_LOCAL_LLM_RUNTIME_NOT_ALLOWED = "EXPERIMENT_LOCAL_LLM_RUNTIME_NOT_ALLOWED"
    EXPERIMENT_CRAWLER_TRIGGER_NOT_ALLOWED = "EXPERIMENT_CRAWLER_TRIGGER_NOT_ALLOWED"
    EXPERIMENT_LIVE_PROD_NOT_ALLOWED = "EXPERIMENT_LIVE_PROD_NOT_ALLOWED"
    EXPERIMENT_PARQUET_NOT_ALLOWED = "EXPERIMENT_PARQUET_NOT_ALLOWED"


class HistoricalModelExperimentRegistryConfig(StrictModel):
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

    @field_validator("config_id", mode="before")
    @classmethod
    def normalize_config_id(cls, value):
        return _upper_required(value, "config_id")

    @model_validator(mode="after")
    def validate_config(self):
        if self.strategy_track != StrategyTrack.DOMESTIC_KR:
            raise ValueError("historical model experiment registry config requires StrategyTrack DOMESTIC_KR")
        return _validate_safety_flags(self, "historical model experiment registry config")


class HistoricalModelExperimentRecord(StrictModel):
    experiment_id: str = Field(..., min_length=1)
    model_type: HistoricalModelTrainingModelType
    dataset_manifest_id: str = Field(..., min_length=1)
    split_manifest_id: str = Field(..., min_length=1)
    feature_schema_version: str = Field(..., min_length=1)
    label_schema_version: str = Field(..., min_length=1)
    metrics_report_id: str = Field(..., min_length=1)
    artifact_manifest_id: str = Field(..., min_length=1)
    safety_report_id: str = Field(..., min_length=1)
    training_timestamp: datetime
    model_metadata: dict[str, object] = Field(default_factory=dict)
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

    @field_validator(
        "experiment_id",
        "dataset_manifest_id",
        "split_manifest_id",
        "feature_schema_version",
        "label_schema_version",
        "metrics_report_id",
        "artifact_manifest_id",
        "safety_report_id",
        mode="before",
    )
    @classmethod
    def normalize_ids(cls, value, info):
        return _upper_required(value, info.field_name)

    @field_validator("training_timestamp", mode="after")
    @classmethod
    def validate_timestamp(cls, value):
        return aware(value)

    @field_validator("model_metadata", mode="before")
    @classmethod
    def validate_model_metadata(cls, value):
        return _reject_unsafe_metadata(value, "model_metadata")

    @field_validator("source_manifest_ids", "source_audit_record_ids", "provider_provenance_ids", mode="before")
    @classmethod
    def normalize_lists(cls, value, info):
        return _normalize_id_list(value, info.field_name)

    @model_validator(mode="after")
    def validate_record(self):
        return _validate_safety_flags(self, "historical model experiment record")


class HistoricalModelExperimentRegistryReport(StrictModel):
    registry_report_id: str = Field(..., min_length=1)
    registry_input_id: str = Field(..., min_length=1)
    experiment_count: int = Field(default=0, ge=0)
    blocked_experiment_count: int = Field(default=0, ge=0)
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

    @field_validator("registry_report_id", "registry_input_id", mode="before")
    @classmethod
    def normalize_ids(cls, value, info):
        return _upper_required(value, info.field_name)

    @field_validator("source_manifest_ids", "source_audit_record_ids", "provider_provenance_ids", mode="before")
    @classmethod
    def normalize_lists(cls, value, info):
        return _normalize_id_list(value, info.field_name)

    @model_validator(mode="after")
    def validate_report(self):
        return _validate_safety_flags(self, "historical model experiment registry report")


class HistoricalModelComparisonReport(StrictModel):
    comparison_report_id: str = Field(..., min_length=1)
    registry_input_id: str = Field(..., min_length=1)
    compared_experiment_ids: list[str] = Field(default_factory=list)
    compared_metric_names: list[str] = Field(default_factory=list)
    validation_accuracy_delta: float | None = None
    test_accuracy_delta: float | None = None
    balanced_accuracy_delta: float | None = None
    macro_f1_delta: float | None = None
    baseline_improvement_delta: float | None = None
    safety_blocked: bool = True
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

    @field_validator("comparison_report_id", "registry_input_id", mode="before")
    @classmethod
    def normalize_ids(cls, value, info):
        return _upper_required(value, info.field_name)

    @field_validator("compared_experiment_ids", "compared_metric_names", "source_manifest_ids", "source_audit_record_ids", "provider_provenance_ids", mode="before")
    @classmethod
    def normalize_lists(cls, value, info):
        return _normalize_id_list(value, info.field_name)

    @model_validator(mode="after")
    def validate_report(self):
        return _validate_safety_flags(self, "historical model comparison report")


class HistoricalModelRiskReviewReport(StrictModel):
    risk_review_report_id: str = Field(..., min_length=1)
    registry_input_id: str = Field(..., min_length=1)
    overfit_risk: bool = False
    low_label_support: bool = False
    severe_label_imbalance: bool = False
    train_test_metric_gap: bool = False
    weak_baseline_improvement: bool = False
    missing_leakage_audit_lineage: bool = False
    missing_validation_split_lineage: bool = False
    unsafe_artifact_metadata: bool = False
    optional_sklearn_dependency_risk: bool = False
    unsupported_model_type: bool = False
    missing_safety_flags: bool = False
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

    @field_validator("risk_review_report_id", "registry_input_id", mode="before")
    @classmethod
    def normalize_ids(cls, value, info):
        return _upper_required(value, info.field_name)

    @field_validator("source_manifest_ids", "source_audit_record_ids", "provider_provenance_ids", mode="before")
    @classmethod
    def normalize_lists(cls, value, info):
        return _normalize_id_list(value, info.field_name)

    @model_validator(mode="after")
    def validate_report(self):
        return _validate_safety_flags(self, "historical model risk review report")


class HistoricalModelPromotionBlockReport(StrictModel):
    promotion_block_report_id: str = Field(..., min_length=1)
    registry_input_id: str = Field(..., min_length=1)
    production_use_allowed: bool = False
    live_inference_allowed: bool = False
    runtime_trading_signal_allowed: bool = False
    order_candidate_allowed: bool = False
    paper_trading_allowed: bool = False
    broker_path_allowed: bool = False
    live_prod_allowed: bool = False
    deployment_allowed: bool = False
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

    @field_validator("promotion_block_report_id", "registry_input_id", mode="before")
    @classmethod
    def normalize_ids(cls, value, info):
        return _upper_required(value, info.field_name)

    @field_validator("source_manifest_ids", "source_audit_record_ids", "provider_provenance_ids", mode="before")
    @classmethod
    def normalize_lists(cls, value, info):
        return _normalize_id_list(value, info.field_name)

    @model_validator(mode="after")
    def validate_report(self):
        blocked_flags = (
            self.production_use_allowed,
            self.live_inference_allowed,
            self.runtime_trading_signal_allowed,
            self.order_candidate_allowed,
            self.paper_trading_allowed,
            self.broker_path_allowed,
            self.live_prod_allowed,
            self.deployment_allowed,
        )
        if any(blocked_flags):
            raise ValueError("historical model promotion block report must remain blocked-by-default")
        return _validate_safety_flags(self, "historical model promotion block report")


class HistoricalModelExperimentLineageReport(StrictModel):
    lineage_report_id: str = Field(..., min_length=1)
    registry_input_id: str = Field(..., min_length=1)
    leakage_audit_lineage_present: bool = True
    validation_split_lineage_present: bool = True
    artifact_manifest_lineage_present: bool = True
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

    @field_validator("lineage_report_id", "registry_input_id", mode="before")
    @classmethod
    def normalize_ids(cls, value, info):
        return _upper_required(value, info.field_name)

    @field_validator("source_manifest_ids", "source_audit_record_ids", "provider_provenance_ids", mode="before")
    @classmethod
    def normalize_lists(cls, value, info):
        return _normalize_id_list(value, info.field_name)

    @model_validator(mode="after")
    def validate_report(self):
        return _validate_safety_flags(self, "historical model experiment lineage report")


class HistoricalModelExperimentSafetyReport(StrictModel):
    safety_report_id: str = Field(..., min_length=1)
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

    @field_validator("safety_report_id", mode="before")
    @classmethod
    def normalize_id(cls, value):
        return _upper_required(value, "safety_report_id")

    @model_validator(mode="after")
    def validate_report(self):
        return _validate_safety_flags(self, "historical model experiment safety report")


class HistoricalModelExperimentGapReport(StrictModel):
    gap_report_id: str = Field(..., min_length=1)
    registry_input_id: str = Field(..., min_length=1)
    gap_status: str = Field(..., min_length=1)
    gap_categories: list[str] = Field(default_factory=list)
    blocking_gap_count: int = Field(default=0, ge=0)
    report_only_gap_count: int = Field(default=0, ge=0)
    gaps: list[dict] = Field(default_factory=list)
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

    @field_validator("gap_report_id", "registry_input_id", "gap_status", mode="before")
    @classmethod
    def normalize_ids(cls, value, info):
        return _upper_required(value, info.field_name)

    @field_validator("gap_categories", "source_manifest_ids", "source_audit_record_ids", "provider_provenance_ids", mode="before")
    @classmethod
    def normalize_lists(cls, value, info):
        return _normalize_id_list(value, info.field_name)

    @model_validator(mode="after")
    def validate_report(self):
        return _validate_safety_flags(self, "historical model experiment gap report")


class HistoricalModelExperimentAuditRecord(StrictModel):
    audit_record_id: str = Field(..., min_length=1)
    registry_input_id: str = Field(..., min_length=1)
    created_at: datetime
    operator_context: str = Field(..., min_length=1)
    source_path: str = Field(..., min_length=1)
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

    @field_validator("audit_record_id", "registry_input_id", mode="before")
    @classmethod
    def normalize_ids(cls, value, info):
        return _upper_required(value, info.field_name)

    @field_validator("operator_context", mode="before")
    @classmethod
    def normalize_context(cls, value):
        return _upper_required(value, "operator_context")

    @field_validator("source_path", mode="before")
    @classmethod
    def normalize_source_path(cls, value):
        return _validate_local_path(value, "source_path")

    @field_validator("created_at", mode="after")
    @classmethod
    def validate_timestamp(cls, value):
        return aware(value)

    @field_validator("source_manifest_ids", "source_audit_record_ids", "provider_provenance_ids", mode="before")
    @classmethod
    def normalize_lists(cls, value, info):
        return _normalize_id_list(value, info.field_name)

    @model_validator(mode="after")
    def validate_record(self):
        return _validate_safety_flags(self, "historical model experiment audit record")


class HistoricalModelExperimentRegistryInput(StrictModel):
    schema_version: str = Field(default="5.8-historical-model-experiment-registry-input", min_length=1)
    registry_input_id: str = Field(..., min_length=1)
    registry_config: HistoricalModelExperimentRegistryConfig
    experiment_records: list[HistoricalModelExperimentRecord] = Field(default_factory=list)
    training_run_report: HistoricalModelTrainingRunReport
    evaluation_report: HistoricalModelEvaluationReport
    metrics_report: HistoricalModelMetricsReport
    artifact_manifest: HistoricalModelArtifactManifest
    training_safety_report: HistoricalModelTrainingSafetyReport
    training_gap_report: HistoricalModelTrainingGapReport
    baseline_evaluation_report: HistoricalDatasetBaselineEvaluationReport | None = None
    split_manifest: HistoricalDatasetSplitManifest | None = None
    leakage_audit_report: HistoricalDatasetLeakageAuditReport | None = None
    registry_report: HistoricalModelExperimentRegistryReport
    comparison_report: HistoricalModelComparisonReport
    risk_review_report: HistoricalModelRiskReviewReport
    promotion_block_report: HistoricalModelPromotionBlockReport
    lineage_report: HistoricalModelExperimentLineageReport
    safety_report: HistoricalModelExperimentSafetyReport
    gap_report: HistoricalModelExperimentGapReport
    audit_records: list[HistoricalModelExperimentAuditRecord] = Field(default_factory=list)

    @field_validator("schema_version", mode="before")
    @classmethod
    def normalize_schema_version(cls, value):
        return _string_required(value, "schema_version")

    @field_validator("registry_input_id", mode="before")
    @classmethod
    def normalize_registry_input_id(cls, value):
        return _upper_required(value, "registry_input_id")

    @model_validator(mode="after")
    def validate_input(self):
        if self.registry_config.strategy_track != StrategyTrack.DOMESTIC_KR:
            raise ValueError("historical model experiment registry input requires StrategyTrack DOMESTIC_KR")
        if self.training_run_report.sandbox_mode != "RESEARCH_ONLY":
            raise ValueError("historical model experiment registry input must consume v5.7 sandbox artifacts only")
        if self.artifact_manifest.local_artifact_path.lower().endswith(".parquet"):
            raise ValueError("parquet remains unsupported")
        if self.training_run_report.no_live_prod is not True:
            raise ValueError("historical model experiment registry input must remain offline-only")
        return self
