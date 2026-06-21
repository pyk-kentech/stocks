from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from pydantic import Field, field_validator, model_validator

from stock_risk_mcp.historical_dataset_models import HistoricalDatasetExportManifest, HistoricalDatasetRecord
from stock_risk_mcp.historical_dataset_readiness_models import (
    HistoricalDatasetBaselineEvaluationReport,
    HistoricalDatasetImbalanceReport,
    HistoricalDatasetReadinessReport,
    HistoricalDatasetSplitQualityReport,
)
from stock_risk_mcp.historical_dataset_validation_models import (
    HistoricalDatasetCoverageReport,
    HistoricalDatasetLabelDistributionReport,
    HistoricalDatasetLeakageAuditReport,
    HistoricalDatasetSplitManifest,
    HistoricalDatasetValidationReport,
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
    ):
        if not getattr(model, flag_name):
            raise ValueError(f"{context} must remain {flag_name}")
    return model


def _validate_local_path(value: str, field_name: str) -> str:
    cleaned = _string_required(value, field_name)
    lowered = cleaned.lower()
    if "://" in lowered or lowered.startswith("//"):
        raise ValueError(f"{field_name} must be a local file path")
    if lowered.endswith(".parquet"):
        raise ValueError("parquet remains unsupported")
    return cleaned


class HistoricalModelTrainingModelType(StrEnum):
    DUMMY_MAJORITY = "DUMMY_MAJORITY"
    DUMMY_PRIOR = "DUMMY_PRIOR"
    LOGISTIC_REGRESSION_OPTIONAL_SKLEARN = "LOGISTIC_REGRESSION_OPTIONAL_SKLEARN"
    DECISION_TREE_OPTIONAL_SKLEARN = "DECISION_TREE_OPTIONAL_SKLEARN"
    RANDOM_FOREST_OPTIONAL_SKLEARN = "RANDOM_FOREST_OPTIONAL_SKLEARN"


class HistoricalModelTrainingGapCategory(StrEnum):
    TRAINING_PLAN_CHECK_GENERATED = "TRAINING_PLAN_CHECK_GENERATED"
    TRAINING_MISSING_PLAN_CHECK = "TRAINING_MISSING_PLAN_CHECK"
    TRAINING_PLAN_CHECK_FAILED = "TRAINING_PLAN_CHECK_FAILED"
    TRAINING_REPORT_ONLY = "TRAINING_REPORT_ONLY"
    TRAINING_LOCAL_ONLY = "TRAINING_LOCAL_ONLY"
    TRAINING_OFFLINE_ONLY = "TRAINING_OFFLINE_ONLY"
    TRAINING_MISSING_INPUT = "TRAINING_MISSING_INPUT"
    TRAINING_MISSING_DATASET_REF = "TRAINING_MISSING_DATASET_REF"
    TRAINING_MISSING_SPLIT_REF = "TRAINING_MISSING_SPLIT_REF"
    TRAINING_MISSING_READINESS_REPORT = "TRAINING_MISSING_READINESS_REPORT"
    TRAINING_MISSING_VALIDATION_REPORT = "TRAINING_MISSING_VALIDATION_REPORT"
    TRAINING_MISSING_LEAKAGE_AUDIT = "TRAINING_MISSING_LEAKAGE_AUDIT"
    TRAINING_READINESS_NOT_CLEAN = "TRAINING_READINESS_NOT_CLEAN"
    TRAINING_VALIDATION_NOT_CLEAN = "TRAINING_VALIDATION_NOT_CLEAN"
    TRAINING_LEAKAGE_AUDIT_NOT_CLEAN = "TRAINING_LEAKAGE_AUDIT_NOT_CLEAN"
    TRAINING_SPLIT_NOT_CHRONOLOGICAL = "TRAINING_SPLIT_NOT_CHRONOLOGICAL"
    TRAINING_RANDOM_SHUFFLE_DETECTED = "TRAINING_RANDOM_SHUFFLE_DETECTED"
    TRAINING_FEATURE_SCHEMA_MISSING = "TRAINING_FEATURE_SCHEMA_MISSING"
    TRAINING_LABEL_SCHEMA_MISSING = "TRAINING_LABEL_SCHEMA_MISSING"
    TRAINING_FEATURE_LEAKAGE_DETECTED = "TRAINING_FEATURE_LEAKAGE_DETECTED"
    TRAINING_OUTCOME_LABEL_IN_FEATURES_DETECTED = "TRAINING_OUTCOME_LABEL_IN_FEATURES_DETECTED"
    TRAINING_FORWARD_RETURN_IN_FEATURES_DETECTED = "TRAINING_FORWARD_RETURN_IN_FEATURES_DETECTED"
    TRAINING_POST_ANCHOR_ACTUAL_IN_FEATURES_DETECTED = "TRAINING_POST_ANCHOR_ACTUAL_IN_FEATURES_DETECTED"
    TRAINING_MISSING_FEATURE_MATRIX = "TRAINING_MISSING_FEATURE_MATRIX"
    TRAINING_MISSING_LABELS = "TRAINING_MISSING_LABELS"
    TRAINING_LABEL_NOT_OUTCOME_SIDE = "TRAINING_LABEL_NOT_OUTCOME_SIDE"
    TRAINING_UNSUPPORTED_MODEL_TYPE = "TRAINING_UNSUPPORTED_MODEL_TYPE"
    TRAINING_SKLEARN_UNAVAILABLE = "TRAINING_SKLEARN_UNAVAILABLE"
    TRAINING_MISSING_TRAIN_SPLIT = "TRAINING_MISSING_TRAIN_SPLIT"
    TRAINING_MISSING_VALIDATION_SPLIT = "TRAINING_MISSING_VALIDATION_SPLIT"
    TRAINING_MISSING_TEST_SPLIT = "TRAINING_MISSING_TEST_SPLIT"
    TRAINING_MODEL_ARTIFACT_GENERATED = "TRAINING_MODEL_ARTIFACT_GENERATED"
    TRAINING_ARTIFACT_REPORT_ONLY = "TRAINING_ARTIFACT_REPORT_ONLY"
    TRAINING_MODEL_ARTIFACT_UNSAFE = "TRAINING_MODEL_ARTIFACT_UNSAFE"
    TRAINING_MODEL_WEIGHT_DETECTED_UNSAFE = "TRAINING_MODEL_WEIGHT_DETECTED_UNSAFE"
    TRAINING_RUNTIME_SIGNAL_DETECTED = "TRAINING_RUNTIME_SIGNAL_DETECTED"
    TRAINING_ORDER_CANDIDATE_DETECTED = "TRAINING_ORDER_CANDIDATE_DETECTED"
    TRAINING_ORDER_FIELD_DETECTED = "TRAINING_ORDER_FIELD_DETECTED"
    TRAINING_BUY_SELL_WORDING_DETECTED = "TRAINING_BUY_SELL_WORDING_DETECTED"
    TRAINING_REMOTE_SOURCE_NOT_ALLOWED = "TRAINING_REMOTE_SOURCE_NOT_ALLOWED"
    TRAINING_API_SOURCE_NOT_ALLOWED = "TRAINING_API_SOURCE_NOT_ALLOWED"
    TRAINING_NETWORK_SOURCE_NOT_ALLOWED = "TRAINING_NETWORK_SOURCE_NOT_ALLOWED"
    TRAINING_PROVIDER_SOURCE_NOT_ALLOWED = "TRAINING_PROVIDER_SOURCE_NOT_ALLOWED"
    TRAINING_CLOUD_LLM_NOT_ALLOWED = "TRAINING_CLOUD_LLM_NOT_ALLOWED"
    TRAINING_LOCAL_LLM_RUNTIME_NOT_ALLOWED = "TRAINING_LOCAL_LLM_RUNTIME_NOT_ALLOWED"
    TRAINING_CRAWLER_TRIGGER_NOT_ALLOWED = "TRAINING_CRAWLER_TRIGGER_NOT_ALLOWED"
    TRAINING_LIVE_PROD_NOT_ALLOWED = "TRAINING_LIVE_PROD_NOT_ALLOWED"
    TRAINING_BROKER_PATH_NOT_ALLOWED = "TRAINING_BROKER_PATH_NOT_ALLOWED"
    TRAINING_CREDENTIALS_NOT_ALLOWED = "TRAINING_CREDENTIALS_NOT_ALLOWED"
    TRAINING_PARQUET_NOT_ALLOWED = "TRAINING_PARQUET_NOT_ALLOWED"


class HistoricalModelTrainingConfig(StrictModel):
    config_id: str = Field(..., min_length=1)
    strategy_track: StrategyTrack
    sandbox_mode: str = Field(default="RESEARCH_ONLY", min_length=1)
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

    @field_validator("config_id", "sandbox_mode", mode="before")
    @classmethod
    def normalize_config_fields(cls, value, info):
        return _upper_required(value, info.field_name)

    @model_validator(mode="after")
    def validate_config(self):
        if self.strategy_track != StrategyTrack.DOMESTIC_KR:
            raise ValueError("historical model training config requires StrategyTrack DOMESTIC_KR")
        if self.sandbox_mode != "RESEARCH_ONLY":
            raise ValueError("historical model training config must remain RESEARCH_ONLY")
        return _validate_safety_flags(self, "historical model training config")


class HistoricalModelTrainingDatasetRef(StrictModel):
    dataset_ref_id: str = Field(..., min_length=1)
    dataset_manifest_id: str = Field(..., min_length=1)
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

    @field_validator("dataset_ref_id", "dataset_manifest_id", mode="before")
    @classmethod
    def normalize_ids(cls, value, info):
        return _upper_required(value, info.field_name)

    @field_validator("source_manifest_ids", "source_audit_record_ids", "provider_provenance_ids", mode="before")
    @classmethod
    def normalize_lists(cls, value, info):
        return _normalize_id_list(value, info.field_name)

    @model_validator(mode="after")
    def validate_dataset_ref(self):
        return _validate_safety_flags(self, "historical model training dataset ref")


class HistoricalModelTrainingSplitRef(StrictModel):
    split_ref_id: str = Field(..., min_length=1)
    split_manifest_id: str = Field(..., min_length=1)
    split_policy: str = Field(default="CHRONOLOGICAL", min_length=1)
    chronological: bool = True
    random_shuffle_used: bool = False
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

    @field_validator("split_ref_id", "split_manifest_id", "split_policy", mode="before")
    @classmethod
    def normalize_fields(cls, value, info):
        return _upper_required(value, info.field_name)

    @field_validator("source_manifest_ids", "source_audit_record_ids", "provider_provenance_ids", mode="before")
    @classmethod
    def normalize_lists(cls, value, info):
        return _normalize_id_list(value, info.field_name)

    @model_validator(mode="after")
    def validate_split_ref(self):
        if self.split_policy != "CHRONOLOGICAL" or not self.chronological:
            raise ValueError("historical model training split ref requires chronological split metadata")
        if self.random_shuffle_used:
            raise ValueError("historical model training split ref must not allow random shuffle")
        return _validate_safety_flags(self, "historical model training split ref")


class HistoricalModelTrainingFeatureSchema(StrictModel):
    feature_schema_id: str = Field(..., min_length=1)
    feature_schema_version: str = Field(..., min_length=1)
    feature_fields: list[str] = Field(default_factory=list)
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

    @field_validator("feature_schema_id", "feature_schema_version", mode="before")
    @classmethod
    def normalize_ids(cls, value, info):
        return _upper_required(value, info.field_name)

    @field_validator("feature_fields", mode="before")
    @classmethod
    def normalize_feature_fields(cls, value):
        return _normalize_id_list(value, "feature_fields")

    @model_validator(mode="after")
    def validate_feature_schema(self):
        blocked = {
            "OUTCOME_LABEL",
            "FORWARD_RETURN_PCT",
            "MAX_FAVORABLE_EXCURSION_PCT",
            "MAX_ADVERSE_EXCURSION_PCT",
            "ACTUAL_FORWARD_VALUE",
            "FORWARD_CLOSE_PRICE",
        }
        if any(field in blocked for field in self.feature_fields):
            raise ValueError("historical model training feature schema must reject outcome leakage fields")
        return _validate_safety_flags(self, "historical model training feature schema")


class HistoricalModelTrainingLabelSchema(StrictModel):
    label_schema_id: str = Field(..., min_length=1)
    label_schema_version: str = Field(..., min_length=1)
    label_source: str = Field(default="OUTCOME_BLOCK_ONLY", min_length=1)
    label_field: str = Field(default="OUTCOME_LABEL", min_length=1)
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

    @field_validator("label_schema_id", "label_schema_version", "label_source", "label_field", mode="before")
    @classmethod
    def normalize_fields(cls, value, info):
        return _upper_required(value, info.field_name)

    @model_validator(mode="after")
    def validate_label_schema(self):
        if self.label_source != "OUTCOME_BLOCK_ONLY" or self.label_field != "OUTCOME_LABEL":
            raise ValueError("historical model training label schema must reference outcome-side labels only")
        return _validate_safety_flags(self, "historical model training label schema")


class HistoricalModelTrainingRunConfig(StrictModel):
    run_config_id: str = Field(..., min_length=1)
    requested_model_type: HistoricalModelTrainingModelType
    random_shuffle_enabled: bool = False
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

    @field_validator("run_config_id", mode="before")
    @classmethod
    def normalize_id(cls, value):
        return _upper_required(value, "run_config_id")

    @model_validator(mode="after")
    def validate_run_config(self):
        if self.random_shuffle_enabled:
            raise ValueError("historical model training run config must disable random shuffle by default")
        return _validate_safety_flags(self, "historical model training run config")


class HistoricalModelTrainingPlanCheckReport(StrictModel):
    plan_check_report_id: str = Field(..., min_length=1)
    training_input_id: str = Field(..., min_length=1)
    eligible_for_sandbox_training: bool = False
    warning_count: int = Field(default=0, ge=0)
    warnings: list[str] = Field(default_factory=list)
    blocking_issue_count: int = Field(default=0, ge=0)
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

    @field_validator("plan_check_report_id", "training_input_id", mode="before")
    @classmethod
    def normalize_ids(cls, value, info):
        return _upper_required(value, info.field_name)

    @field_validator("warnings", mode="before")
    @classmethod
    def normalize_warnings(cls, value):
        if value is None:
            return []
        if isinstance(value, (str, bytes)) or not isinstance(value, list):
            raise ValueError("warnings must be a list")
        return [_string_required(item, "warnings") for item in value]

    @field_validator("source_manifest_ids", "source_audit_record_ids", "provider_provenance_ids", mode="before")
    @classmethod
    def normalize_lists(cls, value, info):
        return _normalize_id_list(value, info.field_name)

    @model_validator(mode="after")
    def validate_report(self):
        if self.warning_count != len(self.warnings):
            raise ValueError("warning_count must match warnings length")
        return _validate_safety_flags(self, "historical model training plan check report")


class HistoricalModelTrainingRunReport(StrictModel):
    run_report_id: str = Field(..., min_length=1)
    training_input_id: str = Field(..., min_length=1)
    model_type: HistoricalModelTrainingModelType
    sandbox_mode: str = Field(default="RESEARCH_ONLY", min_length=1)
    report_only_prediction_count: int = Field(default=0, ge=0)
    training_executed: bool = False
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

    @field_validator("run_report_id", "training_input_id", "sandbox_mode", mode="before")
    @classmethod
    def normalize_fields(cls, value, info):
        return _upper_required(value, info.field_name)

    @field_validator("source_manifest_ids", "source_audit_record_ids", "provider_provenance_ids", mode="before")
    @classmethod
    def normalize_lists(cls, value, info):
        return _normalize_id_list(value, info.field_name)

    @model_validator(mode="after")
    def validate_run_report(self):
        if self.sandbox_mode != "RESEARCH_ONLY":
            raise ValueError("historical model training run report must remain RESEARCH_ONLY")
        return _validate_safety_flags(self, "historical model training run report")


class HistoricalModelEvaluationReport(StrictModel):
    evaluation_report_id: str = Field(..., min_length=1)
    training_input_id: str = Field(..., min_length=1)
    model_type: HistoricalModelTrainingModelType
    report_only_prediction_count: int = Field(default=0, ge=0)
    runtime_trading_signal_present: bool = False
    order_candidate_present: bool = False
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

    @field_validator("evaluation_report_id", "training_input_id", mode="before")
    @classmethod
    def normalize_ids(cls, value, info):
        return _upper_required(value, info.field_name)

    @field_validator("source_manifest_ids", "source_audit_record_ids", "provider_provenance_ids", mode="before")
    @classmethod
    def normalize_lists(cls, value, info):
        return _normalize_id_list(value, info.field_name)

    @model_validator(mode="after")
    def validate_evaluation_report(self):
        if self.runtime_trading_signal_present or self.order_candidate_present:
            raise ValueError("historical model evaluation report must remain report-only research predictions")
        return _validate_safety_flags(self, "historical model evaluation report")


class HistoricalModelMetricsReport(StrictModel):
    metrics_report_id: str = Field(..., min_length=1)
    training_input_id: str = Field(..., min_length=1)
    model_type: HistoricalModelTrainingModelType
    train_accuracy: float | None = Field(default=None, ge=0, le=1)
    validation_accuracy: float | None = Field(default=None, ge=0, le=1)
    test_accuracy: float | None = Field(default=None, ge=0, le=1)
    train_balanced_accuracy: float | None = Field(default=None, ge=0, le=1)
    validation_balanced_accuracy: float | None = Field(default=None, ge=0, le=1)
    test_balanced_accuracy: float | None = Field(default=None, ge=0, le=1)
    train_macro_precision: float | None = Field(default=None, ge=0, le=1)
    validation_macro_precision: float | None = Field(default=None, ge=0, le=1)
    test_macro_precision: float | None = Field(default=None, ge=0, le=1)
    train_macro_recall: float | None = Field(default=None, ge=0, le=1)
    validation_macro_recall: float | None = Field(default=None, ge=0, le=1)
    test_macro_recall: float | None = Field(default=None, ge=0, le=1)
    train_macro_f1: float | None = Field(default=None, ge=0, le=1)
    validation_macro_f1: float | None = Field(default=None, ge=0, le=1)
    test_macro_f1: float | None = Field(default=None, ge=0, le=1)
    confusion_matrix_counts: dict[str, int] = Field(default_factory=dict)
    per_label_support: dict[str, int] = Field(default_factory=dict)
    baseline_comparison: dict[str, float] = Field(default_factory=dict)
    warnings: list[str] = Field(default_factory=list)
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

    @field_validator("metrics_report_id", "training_input_id", mode="before")
    @classmethod
    def normalize_ids(cls, value, info):
        return _upper_required(value, info.field_name)

    @field_validator("source_manifest_ids", "source_audit_record_ids", "provider_provenance_ids", mode="before")
    @classmethod
    def normalize_lists(cls, value, info):
        return _normalize_id_list(value, info.field_name)

    @field_validator("warnings", mode="before")
    @classmethod
    def normalize_warnings(cls, value):
        if value is None:
            return []
        if isinstance(value, (str, bytes)) or not isinstance(value, list):
            raise ValueError("warnings must be a list")
        return [_upper_required(item, "warnings") for item in value]

    @model_validator(mode="after")
    def validate_metrics_report(self):
        return _validate_safety_flags(self, "historical model metrics report")


class HistoricalModelArtifactManifest(StrictModel):
    artifact_manifest_id: str = Field(..., min_length=1)
    model_id: str = Field(..., min_length=1)
    model_type: HistoricalModelTrainingModelType
    training_dataset_manifest_id: str = Field(..., min_length=1)
    split_manifest_id: str = Field(..., min_length=1)
    feature_schema_version: str = Field(..., min_length=1)
    label_schema_version: str = Field(..., min_length=1)
    training_timestamp: datetime
    metrics_report_id: str = Field(..., min_length=1)
    local_artifact_path: str = Field(..., min_length=1)
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

    @model_validator(mode="before")
    @classmethod
    def reject_unsafe_metadata(cls, data):
        if isinstance(data, dict):
            forbidden = {"credential_ref", "broker_metadata", "account_id", "order_id", "live_mode"}
            for field_name in forbidden:
                if field_name in data:
                    raise ValueError(f"{field_name} is not allowed in historical model artifact manifest")
        return data

    @field_validator(
        "artifact_manifest_id",
        "model_id",
        "training_dataset_manifest_id",
        "split_manifest_id",
        "feature_schema_version",
        "label_schema_version",
        "metrics_report_id",
        mode="before",
    )
    @classmethod
    def normalize_ids(cls, value, info):
        return _upper_required(value, info.field_name)

    @field_validator("local_artifact_path", mode="before")
    @classmethod
    def normalize_path(cls, value):
        return _validate_local_path(value, "local_artifact_path")

    @field_validator("training_timestamp", mode="after")
    @classmethod
    def validate_timestamp(cls, value):
        return aware(value)

    @model_validator(mode="after")
    def validate_artifact_manifest(self):
        return _validate_safety_flags(self, "historical model artifact manifest")


class HistoricalModelTrainingSafetyReport(StrictModel):
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

    @field_validator("safety_report_id", mode="before")
    @classmethod
    def normalize_id(cls, value):
        return _upper_required(value, "safety_report_id")

    @model_validator(mode="after")
    def validate_report(self):
        return _validate_safety_flags(self, "historical model training safety report")


class HistoricalModelTrainingGapReport(StrictModel):
    gap_report_id: str = Field(..., min_length=1)
    training_input_id: str = Field(..., min_length=1)
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

    @field_validator("gap_report_id", "training_input_id", "gap_status", mode="before")
    @classmethod
    def normalize_ids(cls, value, info):
        return _upper_required(value, info.field_name)

    @field_validator("gap_categories", mode="before")
    @classmethod
    def normalize_gap_categories(cls, value):
        return _normalize_id_list(value, "gap_categories")

    @field_validator("source_manifest_ids", "source_audit_record_ids", "provider_provenance_ids", mode="before")
    @classmethod
    def normalize_lists(cls, value, info):
        return _normalize_id_list(value, info.field_name)

    @model_validator(mode="after")
    def validate_report(self):
        return _validate_safety_flags(self, "historical model training gap report")


class HistoricalModelTrainingAuditRecord(StrictModel):
    audit_record_id: str = Field(..., min_length=1)
    training_input_id: str = Field(..., min_length=1)
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

    @field_validator("audit_record_id", "training_input_id", mode="before")
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
        return _validate_safety_flags(self, "historical model training audit record")


class HistoricalModelTrainingInput(StrictModel):
    schema_version: str = Field(default="5.7-historical-model-training-input", min_length=1)
    training_input_id: str = Field(..., min_length=1)
    training_config: HistoricalModelTrainingConfig
    dataset_ref: HistoricalModelTrainingDatasetRef
    split_ref: HistoricalModelTrainingSplitRef
    feature_schema: HistoricalModelTrainingFeatureSchema
    label_schema: HistoricalModelTrainingLabelSchema
    run_config: HistoricalModelTrainingRunConfig
    dataset_records: list[HistoricalDatasetRecord] = Field(default_factory=list)
    dataset_export_manifest: HistoricalDatasetExportManifest
    validation_report: HistoricalDatasetValidationReport
    leakage_audit_report: HistoricalDatasetLeakageAuditReport
    split_manifest: HistoricalDatasetSplitManifest
    coverage_report: HistoricalDatasetCoverageReport
    label_distribution_report: HistoricalDatasetLabelDistributionReport
    readiness_report: HistoricalDatasetReadinessReport
    split_quality_report: HistoricalDatasetSplitQualityReport
    imbalance_report: HistoricalDatasetImbalanceReport
    baseline_evaluation_report: HistoricalDatasetBaselineEvaluationReport
    plan_check_report: HistoricalModelTrainingPlanCheckReport
    run_report: HistoricalModelTrainingRunReport
    evaluation_report: HistoricalModelEvaluationReport
    metrics_report: HistoricalModelMetricsReport
    artifact_manifest: HistoricalModelArtifactManifest
    safety_report: HistoricalModelTrainingSafetyReport
    gap_report: HistoricalModelTrainingGapReport
    audit_records: list[HistoricalModelTrainingAuditRecord] = Field(default_factory=list)

    @field_validator("schema_version", "training_input_id", mode="before")
    @classmethod
    def normalize_fields(cls, value, info):
        return _upper_required(value, info.field_name)

    @model_validator(mode="after")
    def validate_training_input(self):
        if self.training_config.strategy_track != StrategyTrack.DOMESTIC_KR:
            raise ValueError("historical model training input requires StrategyTrack DOMESTIC_KR")
        if self.run_config.random_shuffle_enabled:
            raise ValueError("historical model training input must keep random shuffle disabled")
        if self.split_ref.split_policy != "CHRONOLOGICAL" or self.split_manifest.split_policy != "CHRONOLOGICAL":
            raise ValueError("historical model training input requires chronological split artifacts")
        if self.split_manifest.random_shuffle_used:
            raise ValueError("historical model training input must not consume random shuffle split artifacts")
        if self.label_schema.label_source != "OUTCOME_BLOCK_ONLY":
            raise ValueError("historical model training input must consume outcome-side labels only")
        if self.artifact_manifest.local_artifact_path.lower().endswith(".parquet"):
            raise ValueError("parquet remains unsupported")
        return self
