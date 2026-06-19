from __future__ import annotations

from datetime import date, datetime
from enum import StrEnum

from pydantic import Field, field_validator, model_validator

from stock_risk_mcp.historical_dataset_models import (
    HistoricalDatasetExportManifest,
    HistoricalDatasetGapReport,
    HistoricalDatasetQualityReport,
    HistoricalDatasetRecord,
    HistoricalDatasetSafetyReport,
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
    ):
        if not getattr(model, flag_name):
            raise ValueError(f"{context} must remain {flag_name}")
    return model


class HistoricalDatasetValidationGapCategory(StrEnum):
    VALIDATION_REPORT_GENERATED = "VALIDATION_REPORT_GENERATED"
    VALIDATION_REPORT_ONLY = "VALIDATION_REPORT_ONLY"
    VALIDATION_MISSING_INPUT = "VALIDATION_MISSING_INPUT"
    VALIDATION_MISSING_DATASET_RECORD = "VALIDATION_MISSING_DATASET_RECORD"
    VALIDATION_MISSING_FEATURE_BLOCK = "VALIDATION_MISSING_FEATURE_BLOCK"
    VALIDATION_MISSING_OUTCOME_BLOCK = "VALIDATION_MISSING_OUTCOME_BLOCK"
    VALIDATION_MISSING_LINEAGE = "VALIDATION_MISSING_LINEAGE"
    VALIDATION_MISSING_REPLAY_WINDOW_ID = "VALIDATION_MISSING_REPLAY_WINDOW_ID"
    VALIDATION_MISSING_SOURCE_MANIFEST_ID = "VALIDATION_MISSING_SOURCE_MANIFEST_ID"
    VALIDATION_FEATURE_OUTCOME_LEAKAGE_DETECTED = "VALIDATION_FEATURE_OUTCOME_LEAKAGE_DETECTED"
    VALIDATION_OUTCOME_LABEL_IN_FEATURES_DETECTED = "VALIDATION_OUTCOME_LABEL_IN_FEATURES_DETECTED"
    VALIDATION_FORWARD_RETURN_IN_FEATURES_DETECTED = "VALIDATION_FORWARD_RETURN_IN_FEATURES_DETECTED"
    VALIDATION_MFE_MAE_IN_FEATURES_DETECTED = "VALIDATION_MFE_MAE_IN_FEATURES_DETECTED"
    VALIDATION_POST_ANCHOR_ACTUAL_IN_FEATURES_DETECTED = "VALIDATION_POST_ANCHOR_ACTUAL_IN_FEATURES_DETECTED"
    VALIDATION_SCANNER_INPUT_MUTATION_DETECTED = "VALIDATION_SCANNER_INPUT_MUTATION_DETECTED"
    VALIDATION_SPLIT_NOT_CHRONOLOGICAL = "VALIDATION_SPLIT_NOT_CHRONOLOGICAL"
    VALIDATION_SPLIT_RECORD_DUPLICATED = "VALIDATION_SPLIT_RECORD_DUPLICATED"
    VALIDATION_SPLIT_PARTITION_OVERLAP = "VALIDATION_SPLIT_PARTITION_OVERLAP"
    VALIDATION_UNSUPPORTED_MARKET = "VALIDATION_UNSUPPORTED_MARKET"
    VALIDATION_UNSUPPORTED_TRACK = "VALIDATION_UNSUPPORTED_TRACK"
    VALIDATION_ORDER_FIELD_DETECTED = "VALIDATION_ORDER_FIELD_DETECTED"
    VALIDATION_BUY_SELL_WORDING_DETECTED = "VALIDATION_BUY_SELL_WORDING_DETECTED"
    VALIDATION_REMOTE_SOURCE_NOT_ALLOWED = "VALIDATION_REMOTE_SOURCE_NOT_ALLOWED"
    VALIDATION_API_SOURCE_NOT_ALLOWED = "VALIDATION_API_SOURCE_NOT_ALLOWED"
    VALIDATION_NETWORK_SOURCE_NOT_ALLOWED = "VALIDATION_NETWORK_SOURCE_NOT_ALLOWED"
    VALIDATION_PROVIDER_SOURCE_NOT_ALLOWED = "VALIDATION_PROVIDER_SOURCE_NOT_ALLOWED"
    VALIDATION_LLM_METADATA_NOT_ALLOWED = "VALIDATION_LLM_METADATA_NOT_ALLOWED"
    VALIDATION_ML_TRAINING_TRIGGER_NOT_ALLOWED = "VALIDATION_ML_TRAINING_TRIGGER_NOT_ALLOWED"
    VALIDATION_CRAWLER_TRIGGER_NOT_ALLOWED = "VALIDATION_CRAWLER_TRIGGER_NOT_ALLOWED"
    VALIDATION_LIVE_PROD_NOT_ALLOWED = "VALIDATION_LIVE_PROD_NOT_ALLOWED"
    VALIDATION_PARQUET_NOT_ALLOWED = "VALIDATION_PARQUET_NOT_ALLOWED"


class HistoricalDatasetValidationGapEntry(StrictModel):
    gap_id: str = Field(..., min_length=1)
    gap_category: HistoricalDatasetValidationGapCategory | None = None
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


class HistoricalDatasetValidationConfig(StrictModel):
    config_id: str = Field(..., min_length=1)
    strategy_track: StrategyTrack
    require_chronological_split: bool = True
    allow_random_shuffle: bool = False
    default_train_ratio: float = Field(default=0.7, ge=0, le=1)
    default_validation_ratio: float = Field(default=0.15, ge=0, le=1)
    default_test_ratio: float = Field(default=0.15, ge=0, le=1)
    read_only: bool = True
    report_only: bool = True
    non_executable: bool = True
    local_file_only: bool = True
    no_network: bool = True
    no_provider_api: bool = True
    no_order: bool = True
    no_llm_runtime: bool = True
    no_ml_training: bool = True

    @field_validator("config_id", mode="before")
    @classmethod
    def normalize_config_id(cls, value):
        return _upper_required(value, "config_id")

    @model_validator(mode="after")
    def validate_config(self):
        if self.strategy_track != StrategyTrack.DOMESTIC_KR:
            raise ValueError("historical dataset validation config requires StrategyTrack DOMESTIC_KR")
        if self.allow_random_shuffle:
            raise ValueError("historical dataset validation config must not allow random shuffle by default")
        ratio_sum = self.default_train_ratio + self.default_validation_ratio + self.default_test_ratio
        if abs(ratio_sum - 1.0) > 1e-9:
            raise ValueError("validation split ratios must sum to 1.0")
        return _validate_safety_flags(self, "historical dataset validation config")


class HistoricalDatasetSplitConfig(StrictModel):
    split_config_id: str = Field(..., min_length=1)
    strategy_track: StrategyTrack
    split_policy: str = Field(default="CHRONOLOGICAL", min_length=1)
    allow_random_shuffle: bool = False
    train_ratio: float = Field(default=0.7, ge=0, le=1)
    validation_ratio: float = Field(default=0.15, ge=0, le=1)
    test_ratio: float = Field(default=0.15, ge=0, le=1)
    read_only: bool = True
    report_only: bool = True
    non_executable: bool = True
    local_file_only: bool = True
    no_network: bool = True
    no_provider_api: bool = True
    no_order: bool = True
    no_llm_runtime: bool = True
    no_ml_training: bool = True

    @field_validator("split_config_id", "split_policy", mode="before")
    @classmethod
    def normalize_split_fields(cls, value, info):
        return _upper_required(value, info.field_name)

    @model_validator(mode="after")
    def validate_split_config(self):
        if self.strategy_track != StrategyTrack.DOMESTIC_KR:
            raise ValueError("historical dataset split config requires StrategyTrack DOMESTIC_KR")
        if self.split_policy != "CHRONOLOGICAL":
            raise ValueError("historical dataset split config requires CHRONOLOGICAL split policy")
        if self.allow_random_shuffle:
            raise ValueError("historical dataset split config must not allow random shuffle")
        ratio_sum = self.train_ratio + self.validation_ratio + self.test_ratio
        if abs(ratio_sum - 1.0) > 1e-9:
            raise ValueError("split ratios must sum to 1.0")
        return _validate_safety_flags(self, "historical dataset split config")


class HistoricalDatasetValidationReport(StrictModel):
    validation_report_id: str = Field(..., min_length=1)
    validation_input_id: str = Field(..., min_length=1)
    record_count: int = Field(default=0, ge=0)
    valid_record_count: int = Field(default=0, ge=0)
    missing_lineage_count: int = Field(default=0, ge=0)
    missing_feature_count: int = Field(default=0, ge=0)
    missing_outcome_count: int = Field(default=0, ge=0)
    blocked_count: int = Field(default=0, ge=0)
    warning_count: int = Field(default=0, ge=0)
    warnings: list[str] = Field(default_factory=list)
    training_ready_approved: bool = False
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

    @field_validator("validation_report_id", "validation_input_id", mode="before")
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
        if self.training_ready_approved:
            raise ValueError("validation report must not approve training readiness")
        if self.warning_count != len(self.warnings):
            raise ValueError("warning_count must match warnings length")
        return _validate_safety_flags(self, "historical dataset validation report")


class HistoricalDatasetLeakageAuditReport(StrictModel):
    leakage_audit_report_id: str = Field(..., min_length=1)
    validation_input_id: str = Field(..., min_length=1)
    audited_record_count: int = Field(default=0, ge=0)
    clean_record_count: int = Field(default=0, ge=0)
    blocked_record_count: int = Field(default=0, ge=0)
    warning_count: int = Field(default=0, ge=0)
    warnings: list[str] = Field(default_factory=list)
    outcome_label_in_features_count: int = Field(default=0, ge=0)
    forward_return_in_features_count: int = Field(default=0, ge=0)
    max_excursion_in_features_count: int = Field(default=0, ge=0)
    post_anchor_actual_value_in_features_count: int = Field(default=0, ge=0)
    scanner_input_mutation_risk_count: int = Field(default=0, ge=0)
    feature_outcome_leakage_absent: bool = True
    affected_record_ids: list[str] = Field(default_factory=list)
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

    @field_validator("leakage_audit_report_id", "validation_input_id", mode="before")
    @classmethod
    def normalize_audit_ids(cls, value, info):
        return _upper_required(value, info.field_name)

    @field_validator("warnings", mode="before")
    @classmethod
    def normalize_audit_warnings(cls, value):
        if value is None:
            return []
        if isinstance(value, (str, bytes)) or not isinstance(value, list):
            raise ValueError("warnings must be a list")
        return [_string_required(item, "warnings") for item in value]

    @field_validator("affected_record_ids", "source_manifest_ids", "source_audit_record_ids", "provider_provenance_ids", mode="before")
    @classmethod
    def normalize_audit_lists(cls, value, info):
        return _normalize_id_list(value, info.field_name)

    @model_validator(mode="after")
    def validate_audit_report(self):
        if self.warning_count != len(self.warnings):
            raise ValueError("warning_count must match warnings length")
        return _validate_safety_flags(self, "historical dataset leakage audit report")


class HistoricalDatasetSplitRecordRef(StrictModel):
    record_ref_id: str = Field(..., min_length=1)
    dataset_record_id: str = Field(..., min_length=1)
    split_partition: str = Field(..., min_length=1)
    replay_anchor_date: date
    symbol: str = Field(..., min_length=1)
    market: str = Field(..., min_length=1)
    read_only: bool = True
    report_only: bool = True
    non_executable: bool = True
    local_file_only: bool = True
    no_network: bool = True
    no_provider_api: bool = True
    no_order: bool = True
    no_llm_runtime: bool = True
    no_ml_training: bool = True

    @field_validator("record_ref_id", "dataset_record_id", "split_partition", mode="before")
    @classmethod
    def normalize_ref_ids(cls, value, info):
        return _upper_required(value, info.field_name)

    @field_validator("symbol", "market", mode="before")
    @classmethod
    def normalize_ref_strings(cls, value, info):
        return _string_required(value, info.field_name)

    @model_validator(mode="after")
    def validate_record_ref(self):
        if self.split_partition not in {"TRAIN", "VALIDATION", "TEST"}:
            raise ValueError("split_partition must be TRAIN, VALIDATION, or TEST")
        return _validate_safety_flags(self, "historical dataset split record ref")


class HistoricalDatasetSplitManifest(StrictModel):
    split_manifest_id: str = Field(..., min_length=1)
    validation_input_id: str = Field(..., min_length=1)
    split_config_id: str = Field(..., min_length=1)
    split_policy: str = Field(default="CHRONOLOGICAL", min_length=1)
    chronological: bool = True
    random_shuffle_used: bool = False
    train_record_count: int = Field(default=0, ge=0)
    validation_record_count: int = Field(default=0, ge=0)
    test_record_count: int = Field(default=0, ge=0)
    train_symbol_count: int = Field(default=0, ge=0)
    validation_symbol_count: int = Field(default=0, ge=0)
    test_symbol_count: int = Field(default=0, ge=0)
    train_date_range_start: date | None = None
    train_date_range_end: date | None = None
    validation_date_range_start: date | None = None
    validation_date_range_end: date | None = None
    test_date_range_start: date | None = None
    test_date_range_end: date | None = None
    train_label_distribution: dict[str, int] = Field(default_factory=dict)
    validation_label_distribution: dict[str, int] = Field(default_factory=dict)
    test_label_distribution: dict[str, int] = Field(default_factory=dict)
    train_record_refs: list[HistoricalDatasetSplitRecordRef] = Field(default_factory=list)
    validation_record_refs: list[HistoricalDatasetSplitRecordRef] = Field(default_factory=list)
    test_record_refs: list[HistoricalDatasetSplitRecordRef] = Field(default_factory=list)
    record_refs: list[HistoricalDatasetSplitRecordRef] = Field(default_factory=list)
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

    @field_validator("split_manifest_id", "validation_input_id", "split_config_id", "split_policy", mode="before")
    @classmethod
    def normalize_manifest_fields(cls, value, info):
        return _upper_required(value, info.field_name)

    @field_validator("source_manifest_ids", "source_audit_record_ids", "provider_provenance_ids", mode="before")
    @classmethod
    def normalize_manifest_lists(cls, value, info):
        return _normalize_id_list(value, info.field_name)

    @model_validator(mode="after")
    def validate_manifest(self):
        if self.split_policy != "CHRONOLOGICAL" or not self.chronological:
            raise ValueError("split manifest must remain chronological")
        if self.random_shuffle_used:
            raise ValueError("split manifest must remain deterministic without random shuffle")
        total_count = self.train_record_count + self.validation_record_count + self.test_record_count
        if total_count != len(self.record_refs):
            raise ValueError("split manifest record counts must match record_refs length")
        if self.train_record_count != len(self.train_record_refs):
            raise ValueError("train_record_count must match train_record_refs length")
        if self.validation_record_count != len(self.validation_record_refs):
            raise ValueError("validation_record_count must match validation_record_refs length")
        if self.test_record_count != len(self.test_record_refs):
            raise ValueError("test_record_count must match test_record_refs length")
        return _validate_safety_flags(self, "historical dataset split manifest")


class HistoricalDatasetCoverageReport(StrictModel):
    coverage_report_id: str = Field(..., min_length=1)
    validation_input_id: str = Field(..., min_length=1)
    record_count: int = Field(default=0, ge=0)
    symbol_count: int = Field(default=0, ge=0)
    market_count: int = Field(default=0, ge=0)
    strategy_track_count: int = Field(default=0, ge=0)
    earliest_replay_anchor_date: date | None = None
    latest_replay_anchor_date: date | None = None
    symbols: list[str] = Field(default_factory=list)
    markets: list[str] = Field(default_factory=list)
    strategy_tracks: list[str] = Field(default_factory=list)
    records_by_symbol: dict[str, int] = Field(default_factory=dict)
    records_by_market: dict[str, int] = Field(default_factory=dict)
    records_by_strategy_track: dict[str, int] = Field(default_factory=dict)
    missing_feature_count: int = Field(default=0, ge=0)
    missing_outcome_count: int = Field(default=0, ge=0)
    missing_lineage_count: int = Field(default=0, ge=0)
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

    @field_validator("coverage_report_id", "validation_input_id", mode="before")
    @classmethod
    def normalize_coverage_ids(cls, value, info):
        return _upper_required(value, info.field_name)

    @field_validator("symbols", "markets", "strategy_tracks", mode="before")
    @classmethod
    def normalize_coverage_lists(cls, value, info):
        return _normalize_id_list(value, info.field_name)

    @field_validator("source_manifest_ids", "source_audit_record_ids", "provider_provenance_ids", mode="before")
    @classmethod
    def normalize_coverage_lineage(cls, value, info):
        return _normalize_id_list(value, info.field_name)

    @model_validator(mode="after")
    def validate_coverage_report(self):
        return _validate_safety_flags(self, "historical dataset coverage report")


class HistoricalDatasetLabelDistributionReport(StrictModel):
    label_distribution_report_id: str = Field(..., min_length=1)
    validation_input_id: str = Field(..., min_length=1)
    record_count: int = Field(default=0, ge=0)
    label_counts: dict[str, int] = Field(default_factory=dict)
    label_percentages: dict[str, float] = Field(default_factory=dict)
    split_label_counts: dict[str, dict[str, int]] = Field(default_factory=dict)
    split_label_percentages: dict[str, dict[str, float]] = Field(default_factory=dict)
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

    @field_validator("label_distribution_report_id", "validation_input_id", mode="before")
    @classmethod
    def normalize_distribution_ids(cls, value, info):
        return _upper_required(value, info.field_name)

    @field_validator("source_manifest_ids", "source_audit_record_ids", "provider_provenance_ids", mode="before")
    @classmethod
    def normalize_distribution_lists(cls, value, info):
        return _normalize_id_list(value, info.field_name)

    @model_validator(mode="after")
    def validate_distribution_report(self):
        return _validate_safety_flags(self, "historical dataset label distribution report")


class HistoricalDatasetValidationGapReport(StrictModel):
    gap_report_id: str = Field(..., min_length=1)
    validation_input_id: str = Field(..., min_length=1)
    gap_status: str = Field(..., min_length=1)
    gap_categories: list[HistoricalDatasetValidationGapCategory] = Field(default_factory=list)
    blocking_gap_count: int = Field(default=0, ge=0)
    report_only_gap_count: int = Field(default=0, ge=0)
    gaps: list[HistoricalDatasetValidationGapEntry] = Field(default_factory=list)
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

    @field_validator("gap_report_id", "validation_input_id", "gap_status", mode="before")
    @classmethod
    def normalize_gap_report_fields(cls, value, info):
        return _upper_required(value, info.field_name)

    @field_validator("source_manifest_ids", "source_audit_record_ids", "provider_provenance_ids", mode="before")
    @classmethod
    def normalize_gap_report_lists(cls, value, info):
        return _normalize_id_list(value, info.field_name)

    @model_validator(mode="after")
    def validate_gap_report(self):
        return _validate_safety_flags(self, "historical dataset validation gap report")


class HistoricalDatasetValidationSafetyReport(StrictModel):
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

    @field_validator("safety_report_id", mode="before")
    @classmethod
    def normalize_safety_id(cls, value):
        return _upper_required(value, "safety_report_id")

    @model_validator(mode="after")
    def validate_safety_report(self):
        return _validate_safety_flags(self, "historical dataset validation safety report")


class HistoricalDatasetValidationAuditRecord(StrictModel):
    audit_record_id: str = Field(..., min_length=1)
    validation_input_id: str = Field(..., min_length=1)
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

    @field_validator("audit_record_id", "validation_input_id", mode="before")
    @classmethod
    def normalize_audit_record_ids(cls, value, info):
        return _upper_required(value, info.field_name)

    @field_validator("operator_context", "source_path", mode="before")
    @classmethod
    def normalize_audit_record_strings(cls, value, info):
        return _string_required(value, info.field_name)

    @field_validator("created_at", mode="after")
    @classmethod
    def validate_created_at(cls, value):
        return aware(value)

    @field_validator("source_manifest_ids", "source_audit_record_ids", "provider_provenance_ids", mode="before")
    @classmethod
    def normalize_audit_record_lists(cls, value, info):
        return _normalize_id_list(value, info.field_name)

    @model_validator(mode="after")
    def validate_audit_record(self):
        return _validate_safety_flags(self, "historical dataset validation audit record")


class HistoricalDatasetValidationInput(StrictModel):
    schema_version: str = Field(default="5.5-historical-dataset-validation-input", min_length=1)
    validation_input_id: str = Field(..., min_length=1)
    validation_config: HistoricalDatasetValidationConfig
    split_config: HistoricalDatasetSplitConfig
    dataset_records: list[HistoricalDatasetRecord] = Field(default_factory=list)
    dataset_export_manifest: HistoricalDatasetExportManifest
    dataset_quality_report: HistoricalDatasetQualityReport
    dataset_gap_report: HistoricalDatasetGapReport
    dataset_safety_report: HistoricalDatasetSafetyReport
    validation_report: HistoricalDatasetValidationReport
    leakage_audit_report: HistoricalDatasetLeakageAuditReport
    split_manifest: HistoricalDatasetSplitManifest
    coverage_report: HistoricalDatasetCoverageReport
    label_distribution_report: HistoricalDatasetLabelDistributionReport
    validation_gap_report: HistoricalDatasetValidationGapReport
    validation_safety_report: HistoricalDatasetValidationSafetyReport
    audit_records: list[HistoricalDatasetValidationAuditRecord] = Field(default_factory=list)

    @field_validator("schema_version", mode="before")
    @classmethod
    def normalize_schema_version(cls, value):
        return _string_required(value, "schema_version")

    @field_validator("validation_input_id", mode="before")
    @classmethod
    def normalize_validation_input_id(cls, value):
        return _upper_required(value, "validation_input_id")

    @model_validator(mode="after")
    def validate_input(self):
        if self.validation_config.strategy_track != StrategyTrack.DOMESTIC_KR:
            raise ValueError("historical dataset validation input requires StrategyTrack DOMESTIC_KR")
        if self.split_config.strategy_track != self.validation_config.strategy_track:
            raise ValueError("split config strategy_track must match validation config strategy_track")
        if self.split_config.allow_random_shuffle:
            raise ValueError("validation input must not allow random shuffle")
        if self.dataset_export_manifest.export_format == "PARQUET" or "PARQUET" in self.dataset_export_manifest.export_formats:
            raise ValueError("parquet remains unsupported")
        return self
