from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from pydantic import Field, field_validator, model_validator

from stock_risk_mcp.historical_dataset_models import HistoricalDatasetRecord
from stock_risk_mcp.historical_dataset_validation_models import (
    HistoricalDatasetCoverageReport,
    HistoricalDatasetLabelDistributionReport,
    HistoricalDatasetLeakageAuditReport,
    HistoricalDatasetSplitManifest,
    HistoricalDatasetValidationGapReport,
    HistoricalDatasetValidationReport,
    HistoricalDatasetValidationSafetyReport,
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
        "no_network",
        "no_provider_api",
        "no_order",
        "no_llm_runtime",
        "no_ml_training",
        "no_learned_model_evaluation",
    ):
        if not getattr(model, flag_name):
            raise ValueError(f"{context} must remain {flag_name}")
    return model


class HistoricalDatasetReadinessGapCategory(StrEnum):
    READINESS_REPORT_GENERATED = "READINESS_REPORT_GENERATED"
    READINESS_REPORT_ONLY = "READINESS_REPORT_ONLY"
    READINESS_MISSING_INPUT = "READINESS_MISSING_INPUT"
    READINESS_MISSING_VALIDATION_REPORT = "READINESS_MISSING_VALIDATION_REPORT"
    READINESS_MISSING_LEAKAGE_AUDIT = "READINESS_MISSING_LEAKAGE_AUDIT"
    READINESS_MISSING_SPLIT_MANIFEST = "READINESS_MISSING_SPLIT_MANIFEST"
    READINESS_MISSING_COVERAGE_REPORT = "READINESS_MISSING_COVERAGE_REPORT"
    READINESS_MISSING_LABEL_DISTRIBUTION = "READINESS_MISSING_LABEL_DISTRIBUTION"
    READINESS_VALIDATION_NOT_CLEAN = "READINESS_VALIDATION_NOT_CLEAN"
    READINESS_LEAKAGE_AUDIT_NOT_CLEAN = "READINESS_LEAKAGE_AUDIT_NOT_CLEAN"
    READINESS_SPLIT_NOT_CHRONOLOGICAL = "READINESS_SPLIT_NOT_CHRONOLOGICAL"
    READINESS_SPLIT_RANDOM_SHUFFLE_DETECTED = "READINESS_SPLIT_RANDOM_SHUFFLE_DETECTED"
    READINESS_SPLIT_PARTITION_OVERLAP = "READINESS_SPLIT_PARTITION_OVERLAP"
    READINESS_SPLIT_DUPLICATED_RECORD_ID = "READINESS_SPLIT_DUPLICATED_RECORD_ID"
    READINESS_TRAIN_COUNT_TOO_SMALL = "READINESS_TRAIN_COUNT_TOO_SMALL"
    READINESS_VALIDATION_COUNT_TOO_SMALL = "READINESS_VALIDATION_COUNT_TOO_SMALL"
    READINESS_TEST_COUNT_TOO_SMALL = "READINESS_TEST_COUNT_TOO_SMALL"
    READINESS_LABEL_COVERAGE_TOO_LOW = "READINESS_LABEL_COVERAGE_TOO_LOW"
    READINESS_LABEL_IMBALANCE_WARNING = "READINESS_LABEL_IMBALANCE_WARNING"
    READINESS_MISSINGNESS_WARNING = "READINESS_MISSINGNESS_WARNING"
    READINESS_LINEAGE_INCOMPLETE = "READINESS_LINEAGE_INCOMPLETE"
    READINESS_BASELINE_REPORT_GENERATED = "READINESS_BASELINE_REPORT_GENERATED"
    READINESS_BASELINE_NON_LEARNING = "READINESS_BASELINE_NON_LEARNING"
    READINESS_LEARNED_MODEL_DETECTED = "READINESS_LEARNED_MODEL_DETECTED"
    READINESS_MODEL_WEIGHT_DETECTED = "READINESS_MODEL_WEIGHT_DETECTED"
    READINESS_ML_TRAINING_TRIGGER_NOT_ALLOWED = "READINESS_ML_TRAINING_TRIGGER_NOT_ALLOWED"
    READINESS_ML_READY_TENSOR_EXPORT_NOT_ALLOWED = "READINESS_ML_READY_TENSOR_EXPORT_NOT_ALLOWED"
    READINESS_ORDER_FIELD_DETECTED = "READINESS_ORDER_FIELD_DETECTED"
    READINESS_BUY_SELL_WORDING_DETECTED = "READINESS_BUY_SELL_WORDING_DETECTED"
    READINESS_REMOTE_SOURCE_NOT_ALLOWED = "READINESS_REMOTE_SOURCE_NOT_ALLOWED"
    READINESS_API_SOURCE_NOT_ALLOWED = "READINESS_API_SOURCE_NOT_ALLOWED"
    READINESS_NETWORK_SOURCE_NOT_ALLOWED = "READINESS_NETWORK_SOURCE_NOT_ALLOWED"
    READINESS_PROVIDER_SOURCE_NOT_ALLOWED = "READINESS_PROVIDER_SOURCE_NOT_ALLOWED"
    READINESS_LLM_METADATA_NOT_ALLOWED = "READINESS_LLM_METADATA_NOT_ALLOWED"
    READINESS_CRAWLER_TRIGGER_NOT_ALLOWED = "READINESS_CRAWLER_TRIGGER_NOT_ALLOWED"
    READINESS_LIVE_PROD_NOT_ALLOWED = "READINESS_LIVE_PROD_NOT_ALLOWED"
    READINESS_PARQUET_NOT_ALLOWED = "READINESS_PARQUET_NOT_ALLOWED"


class HistoricalDatasetReadinessGapEntry(StrictModel):
    gap_id: str = Field(..., min_length=1)
    gap_category: HistoricalDatasetReadinessGapCategory | None = None
    severity: str = Field(default="REPORT_ONLY", min_length=1)
    message: str = Field(..., min_length=1)

    @field_validator("gap_id", "gap_category", "severity", mode="before")
    @classmethod
    def normalize_gap_fields(cls, value, info):
        if value is None:
            return None
        return _upper_required(value, info.field_name)

    @field_validator("message", mode="before")
    @classmethod
    def normalize_gap_message(cls, value):
        return _string_required(value, "message")


class HistoricalDatasetReadinessConfig(StrictModel):
    config_id: str = Field(..., min_length=1)
    strategy_track: StrategyTrack
    minimum_record_count: int = Field(default=1, ge=0)
    minimum_train_count: int = Field(default=1, ge=0)
    minimum_validation_count: int = Field(default=0, ge=0)
    minimum_test_count: int = Field(default=0, ge=0)
    minimum_label_coverage: int = Field(default=1, ge=0)
    read_only: bool = True
    report_only: bool = True
    non_executable: bool = True
    local_file_only: bool = True
    no_network: bool = True
    no_provider_api: bool = True
    no_order: bool = True
    no_llm_runtime: bool = True
    no_ml_training: bool = True
    no_learned_model_evaluation: bool = True

    @field_validator("config_id", mode="before")
    @classmethod
    def normalize_config_id(cls, value):
        return _upper_required(value, "config_id")

    @model_validator(mode="after")
    def validate_config(self):
        if self.strategy_track != StrategyTrack.DOMESTIC_KR:
            raise ValueError("historical dataset readiness config requires StrategyTrack DOMESTIC_KR")
        return _validate_safety_flags(self, "historical dataset readiness config")


class HistoricalDatasetBaselineConfig(StrictModel):
    baseline_config_id: str = Field(..., min_length=1)
    strategy_track: StrategyTrack
    enabled_baselines: list[str] = Field(default_factory=list)
    deterministic_only: bool = True
    non_learning_only: bool = True
    read_only: bool = True
    report_only: bool = True
    non_executable: bool = True
    local_file_only: bool = True
    no_network: bool = True
    no_provider_api: bool = True
    no_order: bool = True
    no_llm_runtime: bool = True
    no_ml_training: bool = True
    no_learned_model_evaluation: bool = True

    @field_validator("baseline_config_id", mode="before")
    @classmethod
    def normalize_baseline_config_id(cls, value):
        return _upper_required(value, "baseline_config_id")

    @field_validator("enabled_baselines", mode="before")
    @classmethod
    def normalize_enabled_baselines(cls, value):
        return _normalize_id_list(value, "enabled_baselines")

    @model_validator(mode="after")
    def validate_baseline_config(self):
        allowed = {
            "MAJORITY_LABEL_BASELINE",
            "PER_SYMBOL_MAJORITY_LABEL_BASELINE",
            "PER_MARKET_MAJORITY_LABEL_BASELINE",
            "PER_TRACK_MAJORITY_LABEL_BASELINE",
            "PRIOR_DISTRIBUTION_BASELINE",
            "NO_SKILL_BASELINE",
        }
        if self.strategy_track != StrategyTrack.DOMESTIC_KR:
            raise ValueError("historical dataset baseline config requires StrategyTrack DOMESTIC_KR")
        if not self.deterministic_only or not self.non_learning_only:
            raise ValueError("baseline config must remain deterministic and non-learning only")
        if any(name not in allowed for name in self.enabled_baselines):
            raise ValueError("baseline config contains unsupported baseline")
        return _validate_safety_flags(self, "historical dataset baseline config")


class HistoricalDatasetReadinessReport(StrictModel):
    readiness_report_id: str = Field(..., min_length=1)
    readiness_input_id: str = Field(..., min_length=1)
    record_count: int = Field(default=0, ge=0)
    blocking_gate_count: int = Field(default=0, ge=0)
    warning_count: int = Field(default=0, ge=0)
    warnings: list[str] = Field(default_factory=list)
    trade_approval: bool = False
    training_approval: bool = False
    source_manifest_ids: list[str] = Field(default_factory=list)
    source_audit_record_ids: list[str] = Field(default_factory=list)
    provider_provenance_ids: list[str] = Field(default_factory=list)
    read_only: bool = True
    report_only: bool = True
    non_executable: bool = True
    local_file_only: bool = True
    no_network: bool = True
    no_provider_api: bool = True
    no_order: bool = True
    no_llm_runtime: bool = True
    no_ml_training: bool = True
    no_learned_model_evaluation: bool = True

    @field_validator("readiness_report_id", "readiness_input_id", mode="before")
    @classmethod
    def normalize_report_ids(cls, value, info):
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
    def normalize_report_lists(cls, value, info):
        return _normalize_id_list(value, info.field_name)

    @model_validator(mode="after")
    def validate_report(self):
        if self.trade_approval or self.training_approval:
            raise ValueError("readiness report must not approve trade or training")
        if self.warning_count != len(self.warnings):
            raise ValueError("warning_count must match warnings length")
        return _validate_safety_flags(self, "historical dataset readiness report")


class HistoricalDatasetSplitQualityReport(StrictModel):
    split_quality_report_id: str = Field(..., min_length=1)
    readiness_input_id: str = Field(..., min_length=1)
    chronological_split: bool = True
    random_shuffle_used: bool = False
    partition_overlap_detected: bool = False
    duplicated_record_id_detected: bool = False
    train_record_count: int = Field(default=0, ge=0)
    validation_record_count: int = Field(default=0, ge=0)
    test_record_count: int = Field(default=0, ge=0)
    train_symbol_count: int = Field(default=0, ge=0)
    validation_symbol_count: int = Field(default=0, ge=0)
    test_symbol_count: int = Field(default=0, ge=0)
    train_date_range_start: str | None = None
    train_date_range_end: str | None = None
    validation_date_range_start: str | None = None
    validation_date_range_end: str | None = None
    test_date_range_start: str | None = None
    test_date_range_end: str | None = None
    train_label_distribution: dict[str, int] = Field(default_factory=dict)
    validation_label_distribution: dict[str, int] = Field(default_factory=dict)
    test_label_distribution: dict[str, int] = Field(default_factory=dict)
    source_manifest_ids: list[str] = Field(default_factory=list)
    source_audit_record_ids: list[str] = Field(default_factory=list)
    provider_provenance_ids: list[str] = Field(default_factory=list)
    read_only: bool = True
    report_only: bool = True
    non_executable: bool = True
    local_file_only: bool = True
    no_network: bool = True
    no_provider_api: bool = True
    no_order: bool = True
    no_llm_runtime: bool = True
    no_ml_training: bool = True
    no_learned_model_evaluation: bool = True

    @field_validator("split_quality_report_id", "readiness_input_id", mode="before")
    @classmethod
    def normalize_split_quality_ids(cls, value, info):
        return _upper_required(value, info.field_name)

    @field_validator(
        "train_date_range_start",
        "train_date_range_end",
        "validation_date_range_start",
        "validation_date_range_end",
        "test_date_range_start",
        "test_date_range_end",
        mode="before",
    )
    @classmethod
    def normalize_range_values(cls, value, info):
        if value is None:
            return None
        return _string_required(value, info.field_name)

    @field_validator("source_manifest_ids", "source_audit_record_ids", "provider_provenance_ids", mode="before")
    @classmethod
    def normalize_split_quality_lists(cls, value, info):
        return _normalize_id_list(value, info.field_name)

    @model_validator(mode="after")
    def validate_split_quality_report(self):
        return _validate_safety_flags(self, "historical dataset split quality report")


class HistoricalDatasetImbalanceReport(StrictModel):
    imbalance_report_id: str = Field(..., min_length=1)
    readiness_input_id: str = Field(..., min_length=1)
    label_counts: dict[str, int] = Field(default_factory=dict)
    label_percentages: dict[str, float] = Field(default_factory=dict)
    split_label_counts: dict[str, dict[str, int]] = Field(default_factory=dict)
    split_label_percentages: dict[str, dict[str, float]] = Field(default_factory=dict)
    severe_imbalance_warning: bool = False
    missing_label_warning: bool = False
    low_label_coverage_warning: bool = False
    warning_count: int = Field(default=0, ge=0)
    warnings: list[str] = Field(default_factory=list)
    source_manifest_ids: list[str] = Field(default_factory=list)
    source_audit_record_ids: list[str] = Field(default_factory=list)
    provider_provenance_ids: list[str] = Field(default_factory=list)
    read_only: bool = True
    report_only: bool = True
    non_executable: bool = True
    local_file_only: bool = True
    no_network: bool = True
    no_provider_api: bool = True
    no_order: bool = True
    no_llm_runtime: bool = True
    no_ml_training: bool = True
    no_learned_model_evaluation: bool = True

    @field_validator("imbalance_report_id", "readiness_input_id", mode="before")
    @classmethod
    def normalize_imbalance_ids(cls, value, info):
        return _upper_required(value, info.field_name)

    @field_validator("warnings", mode="before")
    @classmethod
    def normalize_imbalance_warnings(cls, value):
        if value is None:
            return []
        if isinstance(value, (str, bytes)) or not isinstance(value, list):
            raise ValueError("warnings must be a list")
        return [_string_required(item, "warnings") for item in value]

    @field_validator("source_manifest_ids", "source_audit_record_ids", "provider_provenance_ids", mode="before")
    @classmethod
    def normalize_imbalance_lists(cls, value, info):
        return _normalize_id_list(value, info.field_name)

    @model_validator(mode="after")
    def validate_imbalance_report(self):
        if self.warning_count != len(self.warnings):
            raise ValueError("warning_count must match warnings length")
        return _validate_safety_flags(self, "historical dataset imbalance report")


class HistoricalDatasetBaselineEvaluationReport(StrictModel):
    baseline_evaluation_report_id: str = Field(..., min_length=1)
    readiness_input_id: str = Field(..., min_length=1)
    baseline_names: list[str] = Field(default_factory=list)
    deterministic_only: bool = True
    non_learning_only: bool = True
    accuracy: float | None = Field(default=None, ge=0, le=1)
    label_coverage: float | None = Field(default=None, ge=0, le=1)
    confusion_matrix_counts: dict[str, int] = Field(default_factory=dict)
    split_metric_summary: dict[str, dict[str, float]] = Field(default_factory=dict)
    trained_model_artifact_present: bool = False
    model_weights_present: bool = False
    runtime_trading_signal_present: bool = False
    source_manifest_ids: list[str] = Field(default_factory=list)
    source_audit_record_ids: list[str] = Field(default_factory=list)
    provider_provenance_ids: list[str] = Field(default_factory=list)
    read_only: bool = True
    report_only: bool = True
    non_executable: bool = True
    local_file_only: bool = True
    no_network: bool = True
    no_provider_api: bool = True
    no_order: bool = True
    no_llm_runtime: bool = True
    no_ml_training: bool = True
    no_learned_model_evaluation: bool = True

    @field_validator("baseline_evaluation_report_id", "readiness_input_id", mode="before")
    @classmethod
    def normalize_baseline_report_ids(cls, value, info):
        return _upper_required(value, info.field_name)

    @field_validator("baseline_names", mode="before")
    @classmethod
    def normalize_baseline_names(cls, value):
        return _normalize_id_list(value, "baseline_names")

    @field_validator("source_manifest_ids", "source_audit_record_ids", "provider_provenance_ids", mode="before")
    @classmethod
    def normalize_baseline_lists(cls, value, info):
        return _normalize_id_list(value, info.field_name)

    @model_validator(mode="after")
    def validate_baseline_report(self):
        if not self.deterministic_only or not self.non_learning_only:
            raise ValueError("baseline evaluation report must remain deterministic and non-learning only")
        if self.trained_model_artifact_present or self.model_weights_present:
            raise ValueError("baseline evaluation report must not include trained model artifacts or model weights")
        if self.runtime_trading_signal_present:
            raise ValueError("baseline evaluation report must not create runtime trading signals")
        return _validate_safety_flags(self, "historical dataset baseline evaluation report")


class HistoricalDatasetReadinessGapReport(StrictModel):
    gap_report_id: str = Field(..., min_length=1)
    readiness_input_id: str = Field(..., min_length=1)
    gap_status: str = Field(..., min_length=1)
    gap_categories: list[HistoricalDatasetReadinessGapCategory] = Field(default_factory=list)
    blocking_gap_count: int = Field(default=0, ge=0)
    report_only_gap_count: int = Field(default=0, ge=0)
    gaps: list[HistoricalDatasetReadinessGapEntry] = Field(default_factory=list)
    source_manifest_ids: list[str] = Field(default_factory=list)
    source_audit_record_ids: list[str] = Field(default_factory=list)
    provider_provenance_ids: list[str] = Field(default_factory=list)
    read_only: bool = True
    report_only: bool = True
    non_executable: bool = True
    local_file_only: bool = True
    no_network: bool = True
    no_provider_api: bool = True
    no_order: bool = True
    no_llm_runtime: bool = True
    no_ml_training: bool = True
    no_learned_model_evaluation: bool = True

    @field_validator("gap_report_id", "readiness_input_id", "gap_status", mode="before")
    @classmethod
    def normalize_gap_report_ids(cls, value, info):
        return _upper_required(value, info.field_name)

    @field_validator("source_manifest_ids", "source_audit_record_ids", "provider_provenance_ids", mode="before")
    @classmethod
    def normalize_gap_report_lists(cls, value, info):
        return _normalize_id_list(value, info.field_name)

    @model_validator(mode="after")
    def validate_gap_report(self):
        return _validate_safety_flags(self, "historical dataset readiness gap report")


class HistoricalDatasetReadinessSafetyReport(StrictModel):
    safety_report_id: str = Field(..., min_length=1)
    read_only: bool = True
    report_only: bool = True
    non_executable: bool = True
    local_file_only: bool = True
    no_network: bool = True
    no_provider_api: bool = True
    no_order: bool = True
    no_llm_runtime: bool = True
    no_ml_training: bool = True
    no_learned_model_evaluation: bool = True

    @field_validator("safety_report_id", mode="before")
    @classmethod
    def normalize_safety_id(cls, value):
        return _upper_required(value, "safety_report_id")

    @model_validator(mode="after")
    def validate_safety_report(self):
        return _validate_safety_flags(self, "historical dataset readiness safety report")


class HistoricalDatasetReadinessAuditRecord(StrictModel):
    audit_record_id: str = Field(..., min_length=1)
    readiness_input_id: str = Field(..., min_length=1)
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
    no_network: bool = True
    no_provider_api: bool = True
    no_order: bool = True
    no_llm_runtime: bool = True
    no_ml_training: bool = True
    no_learned_model_evaluation: bool = True

    @field_validator("audit_record_id", "readiness_input_id", mode="before")
    @classmethod
    def normalize_audit_ids(cls, value, info):
        return _upper_required(value, info.field_name)

    @field_validator("operator_context", "source_path", mode="before")
    @classmethod
    def normalize_audit_strings(cls, value, info):
        return _string_required(value, info.field_name)

    @field_validator("created_at", mode="after")
    @classmethod
    def validate_created_at(cls, value):
        return aware(value)

    @field_validator("source_manifest_ids", "source_audit_record_ids", "provider_provenance_ids", mode="before")
    @classmethod
    def normalize_audit_lists(cls, value, info):
        return _normalize_id_list(value, info.field_name)

    @model_validator(mode="after")
    def validate_audit_record(self):
        return _validate_safety_flags(self, "historical dataset readiness audit record")


class HistoricalDatasetReadinessInput(StrictModel):
    schema_version: str = Field(default="5.6-historical-dataset-readiness-input", min_length=1)
    readiness_input_id: str = Field(..., min_length=1)
    readiness_config: HistoricalDatasetReadinessConfig
    baseline_config: HistoricalDatasetBaselineConfig
    dataset_records: list[HistoricalDatasetRecord] = Field(default_factory=list)
    validation_report: HistoricalDatasetValidationReport
    leakage_audit_report: HistoricalDatasetLeakageAuditReport
    split_manifest: HistoricalDatasetSplitManifest
    coverage_report: HistoricalDatasetCoverageReport
    label_distribution_report: HistoricalDatasetLabelDistributionReport
    validation_gap_report: HistoricalDatasetValidationGapReport
    validation_safety_report: HistoricalDatasetValidationSafetyReport
    readiness_report: HistoricalDatasetReadinessReport
    split_quality_report: HistoricalDatasetSplitQualityReport
    imbalance_report: HistoricalDatasetImbalanceReport
    baseline_evaluation_report: HistoricalDatasetBaselineEvaluationReport
    readiness_gap_report: HistoricalDatasetReadinessGapReport
    readiness_safety_report: HistoricalDatasetReadinessSafetyReport
    audit_records: list[HistoricalDatasetReadinessAuditRecord] = Field(default_factory=list)

    @field_validator("schema_version", mode="before")
    @classmethod
    def normalize_schema_version(cls, value):
        return _string_required(value, "schema_version")

    @field_validator("readiness_input_id", mode="before")
    @classmethod
    def normalize_readiness_input_id(cls, value):
        return _upper_required(value, "readiness_input_id")

    @model_validator(mode="after")
    def validate_input(self):
        if self.readiness_config.strategy_track != StrategyTrack.DOMESTIC_KR:
            raise ValueError("historical dataset readiness input requires StrategyTrack DOMESTIC_KR")
        if self.baseline_config.strategy_track != self.readiness_config.strategy_track:
            raise ValueError("baseline config strategy_track must match readiness config strategy_track")
        if "PARQUET" in self.validation_report.source_manifest_ids:
            raise ValueError("parquet remains unsupported")
        return self
