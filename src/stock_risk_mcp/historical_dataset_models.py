from __future__ import annotations

from datetime import date, datetime
from enum import StrEnum

from pydantic import Field, field_validator, model_validator

from stock_risk_mcp.historical_calendar_models import HistoricalCalendarEventSnapshot
from stock_risk_mcp.historical_data_models import HistoricalMarketDataSnapshot
from stock_risk_mcp.historical_outcome_models import HistoricalOutcomeObservationInput
from stock_risk_mcp.historical_replay_bridge_models import (
    HistoricalReplayEventStream,
    HistoricalReplayWindowBundle,
)
from stock_risk_mcp.historical_scanner_replay_models import HistoricalScannerReplayInput
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


def _normalize_string_list(value, field_name: str) -> list[str]:
    if value is None:
        return []
    if isinstance(value, (str, bytes)) or not isinstance(value, list):
        raise ValueError(f"{field_name} must be a list")
    return [_string_required(item, field_name) for item in value]


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


def _validate_export_formats(formats: list[str], field_name: str = "export_formats") -> list[str]:
    allowed = {"JSON", "JSONL", "CSV"}
    normalized = _normalize_id_list(formats, field_name)
    if "PARQUET" in normalized:
        raise ValueError("parquet remains unsupported")
    if any(fmt not in allowed for fmt in normalized):
        raise ValueError(f"{field_name} must contain only json, jsonl, or csv")
    if not normalized:
        raise ValueError(f"{field_name} must not be empty")
    return normalized


class HistoricalDatasetGapCategory(StrEnum):
    DATASET_RECORD_GENERATED = "DATASET_RECORD_GENERATED"
    DATASET_REPORT_ONLY = "DATASET_REPORT_ONLY"
    DATASET_MISSING_ASSEMBLY_INPUT = "DATASET_MISSING_ASSEMBLY_INPUT"
    DATASET_MISSING_REPLAY_WINDOW = "DATASET_MISSING_REPLAY_WINDOW"
    DATASET_MISSING_SCANNER_CONTEXT = "DATASET_MISSING_SCANNER_CONTEXT"
    DATASET_MISSING_OUTCOME_OBSERVATION = "DATASET_MISSING_OUTCOME_OBSERVATION"
    DATASET_MISSING_FEATURE_BLOCK = "DATASET_MISSING_FEATURE_BLOCK"
    DATASET_MISSING_OUTCOME_BLOCK = "DATASET_MISSING_OUTCOME_BLOCK"
    DATASET_SOURCE_LINEAGE_MISSING = "DATASET_SOURCE_LINEAGE_MISSING"
    DATASET_FEATURE_OUTCOME_LEAKAGE_DETECTED = "DATASET_FEATURE_OUTCOME_LEAKAGE_DETECTED"
    DATASET_OUTCOME_LABEL_IN_FEATURES_DETECTED = "DATASET_OUTCOME_LABEL_IN_FEATURES_DETECTED"
    DATASET_FORWARD_RETURN_IN_FEATURES_DETECTED = "DATASET_FORWARD_RETURN_IN_FEATURES_DETECTED"
    DATASET_SCANNER_INPUT_MUTATION_DETECTED = "DATASET_SCANNER_INPUT_MUTATION_DETECTED"
    DATASET_UNSUPPORTED_TRACK = "DATASET_UNSUPPORTED_TRACK"
    DATASET_UNSUPPORTED_MARKET = "DATASET_UNSUPPORTED_MARKET"
    DATASET_MARKET_PROFILE_MISMATCH = "DATASET_MARKET_PROFILE_MISMATCH"
    DATASET_CURRENCY_MISMATCH = "DATASET_CURRENCY_MISMATCH"
    DATASET_TIMEZONE_MISMATCH = "DATASET_TIMEZONE_MISMATCH"
    DATASET_ORDER_FIELD_DETECTED = "DATASET_ORDER_FIELD_DETECTED"
    DATASET_BUY_SELL_WORDING_DETECTED = "DATASET_BUY_SELL_WORDING_DETECTED"
    DATASET_REMOTE_SOURCE_NOT_ALLOWED = "DATASET_REMOTE_SOURCE_NOT_ALLOWED"
    DATASET_API_SOURCE_NOT_ALLOWED = "DATASET_API_SOURCE_NOT_ALLOWED"
    DATASET_NETWORK_SOURCE_NOT_ALLOWED = "DATASET_NETWORK_SOURCE_NOT_ALLOWED"
    DATASET_PROVIDER_SOURCE_NOT_ALLOWED = "DATASET_PROVIDER_SOURCE_NOT_ALLOWED"
    DATASET_LLM_METADATA_NOT_ALLOWED = "DATASET_LLM_METADATA_NOT_ALLOWED"
    DATASET_ML_TRAINING_TRIGGER_NOT_ALLOWED = "DATASET_ML_TRAINING_TRIGGER_NOT_ALLOWED"
    DATASET_CRAWLER_TRIGGER_NOT_ALLOWED = "DATASET_CRAWLER_TRIGGER_NOT_ALLOWED"
    DATASET_LIVE_PROD_NOT_ALLOWED = "DATASET_LIVE_PROD_NOT_ALLOWED"
    DATASET_PARQUET_NOT_ALLOWED = "DATASET_PARQUET_NOT_ALLOWED"


class HistoricalDatasetGapEntry(StrictModel):
    gap_id: str = Field(..., min_length=1)
    gap_category: HistoricalDatasetGapCategory | None = None
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


class HistoricalDatasetAssemblyConfig(StrictModel):
    config_id: str = Field(..., min_length=1)
    strategy_track: StrategyTrack
    export_formats: list[str] = Field(default_factory=list)
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

    @field_validator("export_formats", mode="before")
    @classmethod
    def normalize_export_formats(cls, value):
        return _validate_export_formats(value)

    @model_validator(mode="after")
    def validate_config(self):
        if self.strategy_track != StrategyTrack.DOMESTIC_KR:
            raise ValueError("historical dataset assembly config requires StrategyTrack DOMESTIC_KR")
        return _validate_safety_flags(self, "historical dataset assembly config")


class HistoricalDatasetFeatureBlock(StrictModel):
    block_id: str = Field(..., min_length=1)
    replay_context_id: str | None = None
    scanner_replay_input_id: str | None = None
    known_event_context_summary: str | None = None
    attached_market_event_count: int = Field(default=0, ge=0)
    attached_corporate_event_count: int = Field(default=0, ge=0)
    read_only: bool = True
    report_only: bool = True
    non_executable: bool = True
    local_file_only: bool = True
    no_network: bool = True
    no_provider_api: bool = True
    no_order: bool = True
    no_llm_runtime: bool = True
    no_ml_training: bool = True

    @model_validator(mode="before")
    @classmethod
    def reject_outcome_fields(cls, data):
        if isinstance(data, dict):
            blocked_messages = {
                "outcome_label": "feature block must reject outcome label fields",
                "forward_return_pct": "feature block must reject forward return fields",
                "max_favorable_excursion_pct": "feature block must reject post-anchor actual values",
                "max_adverse_excursion_pct": "feature block must reject post-anchor actual values",
                "forward_close_price": "feature block must reject post-anchor actual values",
                "actual_forward_value": "feature block must reject post-anchor actual values",
            }
            for key, message in blocked_messages.items():
                if key in data:
                    raise ValueError(message)
        return data

    @field_validator("block_id", "replay_context_id", "scanner_replay_input_id", mode="before")
    @classmethod
    def normalize_feature_ids(cls, value, info):
        if value is None:
            return None
        return _upper_required(value, info.field_name)

    @field_validator("known_event_context_summary", mode="before")
    @classmethod
    def normalize_feature_summary(cls, value):
        if value is None:
            return None
        return _string_required(value, "known_event_context_summary")

    @model_validator(mode="after")
    def validate_feature_block(self):
        return _validate_safety_flags(self, "historical dataset feature block")


class HistoricalDatasetOutcomeBlock(StrictModel):
    block_id: str = Field(..., min_length=1)
    outcome_observed_after_anchor: bool = True
    outcome_label: str | None = None
    forward_return_pct: float | None = None
    max_favorable_excursion_pct: float | None = None
    max_adverse_excursion_pct: float | None = None
    sessions_observed: int = Field(default=0, ge=0)
    missing_session_count: int = Field(default=0, ge=0)
    early_close_count: int = Field(default=0, ge=0)
    read_only: bool = True
    report_only: bool = True
    non_executable: bool = True
    local_file_only: bool = True
    no_network: bool = True
    no_provider_api: bool = True
    no_order: bool = True
    no_llm_runtime: bool = True
    no_ml_training: bool = True

    @field_validator("block_id", "outcome_label", mode="before")
    @classmethod
    def normalize_outcome_fields(cls, value, info):
        if value is None:
            return None
        return _upper_required(value, info.field_name)

    @model_validator(mode="after")
    def validate_outcome_block(self):
        if not self.outcome_observed_after_anchor:
            raise ValueError("outcome block must remain outcome_observed_after_anchor")
        return _validate_safety_flags(self, "historical dataset outcome block")


class HistoricalDatasetRecord(StrictModel):
    record_id: str = Field(..., min_length=1)
    strategy_track: StrategyTrack
    market_profile_id: str = Field(..., min_length=1)
    symbol: str = Field(..., min_length=1)
    market: str = Field(..., min_length=1)
    replay_session_date: date
    replay_event_ids: list[str] = Field(default_factory=list)
    replay_window_id: str = Field(..., min_length=1)
    scanner_replay_candidate_seed_id: str | None = None
    outcome_observation_id: str | None = None
    feature_block: HistoricalDatasetFeatureBlock
    outcome_block: HistoricalDatasetOutcomeBlock
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

    @field_validator(
        "record_id",
        "market_profile_id",
        "symbol",
        "market",
        "replay_window_id",
        "scanner_replay_candidate_seed_id",
        "outcome_observation_id",
        mode="before",
    )
    @classmethod
    def normalize_record_fields(cls, value, info):
        if value is None:
            return None
        return _upper_required(value, info.field_name)

    @field_validator("replay_event_ids", "source_manifest_ids", "source_audit_record_ids", "provider_provenance_ids", mode="before")
    @classmethod
    def normalize_record_lists(cls, value, info):
        return _normalize_id_list(value, info.field_name)

    @model_validator(mode="after")
    def validate_record(self):
        if self.strategy_track != StrategyTrack.DOMESTIC_KR:
            raise ValueError("historical dataset record requires StrategyTrack DOMESTIC_KR")
        return _validate_safety_flags(self, "historical dataset record")


class HistoricalDatasetExportManifest(StrictModel):
    manifest_id: str = Field(..., min_length=1)
    export_format: str | None = None
    local_output_path: str | None = None
    record_count: int = Field(default=0, ge=0)
    symbol_count: int = Field(default=0, ge=0)
    market_count: int = Field(default=0, ge=0)
    date_range_start: date | None = None
    date_range_end: date | None = None
    feature_schema_version: str | None = None
    outcome_schema_version: str | None = None
    quality_report_id: str | None = None
    gap_report_id: str | None = None
    safety_report_id: str | None = None
    export_formats: list[str] = Field(default_factory=list)
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

    @field_validator(
        "manifest_id",
        "export_format",
        "feature_schema_version",
        "outcome_schema_version",
        "quality_report_id",
        "gap_report_id",
        "safety_report_id",
        mode="before",
    )
    @classmethod
    def normalize_manifest_id(cls, value, info):
        if value is None:
            return None
        return _upper_required(value, info.field_name)

    @field_validator("local_output_path", mode="before")
    @classmethod
    def normalize_manifest_path(cls, value):
        if value is None:
            return None
        return _string_required(value, "local_output_path")

    @field_validator("export_formats", mode="before")
    @classmethod
    def normalize_manifest_formats(cls, value):
        return _validate_export_formats(value)

    @field_validator("source_manifest_ids", "source_audit_record_ids", "provider_provenance_ids", mode="before")
    @classmethod
    def normalize_manifest_lists(cls, value, info):
        return _normalize_id_list(value, info.field_name)

    @model_validator(mode="after")
    def validate_manifest(self):
        return _validate_safety_flags(self, "historical dataset export manifest")


class HistoricalDatasetQualityReport(StrictModel):
    quality_report_id: str = Field(..., min_length=1)
    record_count: int = Field(default=0, ge=0)
    valid_record_count: int = Field(default=0, ge=0)
    symbol_count: int = Field(default=0, ge=0)
    market_count: int = Field(default=0, ge=0)
    missing_lineage_count: int = Field(default=0, ge=0)
    missing_feature_count: int = Field(default=0, ge=0)
    missing_outcome_count: int = Field(default=0, ge=0)
    leakage_risk_count: int = Field(default=0, ge=0)
    safety_blocked_count: int = Field(default=0, ge=0)
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

    @field_validator("quality_report_id", mode="before")
    @classmethod
    def normalize_quality_id(cls, value):
        return _upper_required(value, "quality_report_id")

    @field_validator("warnings", mode="before")
    @classmethod
    def normalize_quality_warnings(cls, value):
        return _normalize_string_list(value, "warnings")

    @field_validator("source_manifest_ids", "source_audit_record_ids", "provider_provenance_ids", mode="before")
    @classmethod
    def normalize_quality_lists(cls, value, info):
        return _normalize_id_list(value, info.field_name)

    @model_validator(mode="after")
    def validate_quality_report(self):
        if self.warning_count != len(self.warnings):
            raise ValueError("warning_count must match warnings length")
        return _validate_safety_flags(self, "historical dataset quality report")


class HistoricalDatasetGapReport(StrictModel):
    gap_report_id: str = Field(..., min_length=1)
    gap_status: str = Field(..., min_length=1)
    gap_categories: list[HistoricalDatasetGapCategory] = Field(default_factory=list)
    blocking_gap_count: int = Field(default=0, ge=0)
    report_only_gap_count: int = Field(default=0, ge=0)
    gaps: list[HistoricalDatasetGapEntry] = Field(default_factory=list)
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

    @field_validator("gap_report_id", "gap_status", mode="before")
    @classmethod
    def normalize_gap_report_ids(cls, value, info):
        return _upper_required(value, info.field_name)

    @field_validator("gap_categories", mode="before")
    @classmethod
    def normalize_gap_categories(cls, value):
        return _normalize_id_list(value, "gap_categories")

    @field_validator("source_manifest_ids", "source_audit_record_ids", "provider_provenance_ids", mode="before")
    @classmethod
    def normalize_gap_report_lists(cls, value, info):
        return _normalize_id_list(value, info.field_name)

    @model_validator(mode="after")
    def validate_gap_report(self):
        return _validate_safety_flags(self, "historical dataset gap report")


class HistoricalDatasetSafetyReport(StrictModel):
    safety_report_id: str = Field(default="historical-dataset-safety-report", min_length=1)
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
        return _validate_safety_flags(self, "historical dataset safety report")


class HistoricalDatasetAuditRecord(StrictModel):
    audit_record_id: str = Field(..., min_length=1)
    assembly_input_id: str = Field(..., min_length=1)
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

    _created_at = field_validator("created_at")(aware)

    @field_validator("audit_record_id", "assembly_input_id", mode="before")
    @classmethod
    def normalize_audit_ids(cls, value, info):
        return _upper_required(value, info.field_name)

    @field_validator("operator_context", "source_path", mode="before")
    @classmethod
    def normalize_audit_text(cls, value, info):
        return _string_required(value, info.field_name)

    @field_validator("source_manifest_ids", "source_audit_record_ids", "provider_provenance_ids", mode="before")
    @classmethod
    def normalize_audit_lists(cls, value, info):
        return _normalize_id_list(value, info.field_name)

    @model_validator(mode="after")
    def validate_audit_record(self):
        return _validate_safety_flags(self, "historical dataset audit record")


class HistoricalDatasetAssemblyInput(StrictModel):
    schema_version: str = "5.4-historical-dataset-assembly-input"
    assembly_input_id: str = Field(..., min_length=1)
    assembly_config: HistoricalDatasetAssemblyConfig
    historical_market_data_snapshot: HistoricalMarketDataSnapshot
    historical_calendar_event_snapshot: HistoricalCalendarEventSnapshot | None = None
    replay_event_stream: HistoricalReplayEventStream
    replay_window_bundle: HistoricalReplayWindowBundle
    scanner_replay_input: HistoricalScannerReplayInput
    historical_outcome_observation_input: HistoricalOutcomeObservationInput
    records: list[HistoricalDatasetRecord] = Field(default_factory=list)
    export_manifest: HistoricalDatasetExportManifest
    quality_report: HistoricalDatasetQualityReport
    gap_report: HistoricalDatasetGapReport
    safety_report: HistoricalDatasetSafetyReport = Field(default_factory=HistoricalDatasetSafetyReport)
    audit_records: list[HistoricalDatasetAuditRecord] = Field(default_factory=list)

    @field_validator("schema_version")
    @classmethod
    def validate_schema_version(cls, value):
        if value != "5.4-historical-dataset-assembly-input":
            raise ValueError("schema_version must be exactly 5.4-historical-dataset-assembly-input")
        return value

    @field_validator("assembly_input_id", mode="before")
    @classmethod
    def normalize_assembly_input_id(cls, value):
        return _upper_required(value, "assembly_input_id")

    @model_validator(mode="after")
    def validate_input(self):
        if self.assembly_config.strategy_track != StrategyTrack.DOMESTIC_KR:
            raise ValueError("historical dataset assembly input requires StrategyTrack DOMESTIC_KR")
        if self.historical_outcome_observation_input.observation_config.strategy_track != self.assembly_config.strategy_track:
            raise ValueError("historical outcome observation input strategy_track must match assembly_config")
        if self.scanner_replay_input.model_dump(mode="json") != self.historical_outcome_observation_input.scanner_replay_input.model_dump(mode="json"):
            raise ValueError("scanner replay input must remain pre-outcome and not mutated")
        return self
