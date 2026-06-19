from __future__ import annotations

from datetime import date, datetime
from enum import StrEnum

from pydantic import Field, field_validator, model_validator

from stock_risk_mcp.historical_calendar_models import HistoricalCalendarEventSnapshot
from stock_risk_mcp.historical_data_models import HistoricalMarketDataSnapshot
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


def aware_optional(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    return aware(value)


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


class HistoricalOutcomeLabelType(StrEnum):
    OUTCOME_FAVORABLE = "OUTCOME_FAVORABLE"
    OUTCOME_ADVERSE = "OUTCOME_ADVERSE"
    OUTCOME_NEUTRAL = "OUTCOME_NEUTRAL"
    OUTCOME_VOLATILE_MIXED = "OUTCOME_VOLATILE_MIXED"
    OUTCOME_INCONCLUSIVE = "OUTCOME_INCONCLUSIVE"
    OUTCOME_INSUFFICIENT_FORWARD_DATA = "OUTCOME_INSUFFICIENT_FORWARD_DATA"
    OUTCOME_BLOCKED_SAFETY = "OUTCOME_BLOCKED_SAFETY"
    OUTCOME_REPORT_ONLY = "OUTCOME_REPORT_ONLY"


class HistoricalOutcomeGapCategory(StrEnum):
    OUTCOME_OBSERVATION_GENERATED = "OUTCOME_OBSERVATION_GENERATED"
    OUTCOME_REPORT_ONLY = "OUTCOME_REPORT_ONLY"
    OUTCOME_MISSING_REPLAY_INPUT = "OUTCOME_MISSING_REPLAY_INPUT"
    OUTCOME_MISSING_CANDIDATE_SEED = "OUTCOME_MISSING_CANDIDATE_SEED"
    OUTCOME_MISSING_REPLAY_WINDOW = "OUTCOME_MISSING_REPLAY_WINDOW"
    OUTCOME_MISSING_HISTORICAL_MARKET_DATA = "OUTCOME_MISSING_HISTORICAL_MARKET_DATA"
    OUTCOME_MISSING_TRADING_CALENDAR = "OUTCOME_MISSING_TRADING_CALENDAR"
    OUTCOME_MISSING_FORWARD_SESSION = "OUTCOME_MISSING_FORWARD_SESSION"
    OUTCOME_INSUFFICIENT_FORWARD_DATA = "OUTCOME_INSUFFICIENT_FORWARD_DATA"
    OUTCOME_MISSING_ANCHOR_PRICE = "OUTCOME_MISSING_ANCHOR_PRICE"
    OUTCOME_MISSING_FORWARD_PRICE = "OUTCOME_MISSING_FORWARD_PRICE"
    OUTCOME_INVALID_PRICE_SERIES = "OUTCOME_INVALID_PRICE_SERIES"
    OUTCOME_UNSUPPORTED_TRACK = "OUTCOME_UNSUPPORTED_TRACK"
    OUTCOME_UNSUPPORTED_MARKET = "OUTCOME_UNSUPPORTED_MARKET"
    OUTCOME_MARKET_PROFILE_MISMATCH = "OUTCOME_MARKET_PROFILE_MISMATCH"
    OUTCOME_CURRENCY_MISMATCH = "OUTCOME_CURRENCY_MISMATCH"
    OUTCOME_TIMEZONE_MISMATCH = "OUTCOME_TIMEZONE_MISMATCH"
    OUTCOME_THRESHOLD_CONFIG_MISSING = "OUTCOME_THRESHOLD_CONFIG_MISSING"
    OUTCOME_LABEL_INCONCLUSIVE = "OUTCOME_LABEL_INCONCLUSIVE"
    OUTCOME_LEAKAGE_RISK_DETECTED = "OUTCOME_LEAKAGE_RISK_DETECTED"
    OUTCOME_ORDER_FIELD_DETECTED = "OUTCOME_ORDER_FIELD_DETECTED"
    OUTCOME_BUY_SELL_WORDING_DETECTED = "OUTCOME_BUY_SELL_WORDING_DETECTED"
    OUTCOME_REMOTE_SOURCE_NOT_ALLOWED = "OUTCOME_REMOTE_SOURCE_NOT_ALLOWED"
    OUTCOME_API_SOURCE_NOT_ALLOWED = "OUTCOME_API_SOURCE_NOT_ALLOWED"
    OUTCOME_NETWORK_SOURCE_NOT_ALLOWED = "OUTCOME_NETWORK_SOURCE_NOT_ALLOWED"
    OUTCOME_PROVIDER_SOURCE_NOT_ALLOWED = "OUTCOME_PROVIDER_SOURCE_NOT_ALLOWED"
    OUTCOME_LLM_METADATA_NOT_ALLOWED = "OUTCOME_LLM_METADATA_NOT_ALLOWED"
    OUTCOME_ML_TRAINING_TRIGGER_NOT_ALLOWED = "OUTCOME_ML_TRAINING_TRIGGER_NOT_ALLOWED"
    OUTCOME_CRAWLER_TRIGGER_NOT_ALLOWED = "OUTCOME_CRAWLER_TRIGGER_NOT_ALLOWED"
    OUTCOME_LIVE_PROD_NOT_ALLOWED = "OUTCOME_LIVE_PROD_NOT_ALLOWED"
    OUTCOME_PARQUET_NOT_ALLOWED = "OUTCOME_PARQUET_NOT_ALLOWED"


class HistoricalOutcomeGapEntry(StrictModel):
    gap_id: str = Field(..., min_length=1)
    gap_category: HistoricalOutcomeGapCategory | None = None
    severity: str = Field(default="REPORT_ONLY", min_length=1)
    message: str = Field(..., min_length=1)
    source_manifest_id: str | None = None
    source_audit_record_id: str | None = None
    provider_provenance_id: str | None = None

    @field_validator(
        "gap_id",
        "gap_category",
        "severity",
        "source_manifest_id",
        "source_audit_record_id",
        "provider_provenance_id",
        mode="before",
    )
    @classmethod
    def normalize_gap_fields(cls, value, info):
        if value is None:
            return None
        return _upper_required(value, info.field_name)

    @field_validator("message", mode="before")
    @classmethod
    def normalize_message(cls, value):
        return _string_required(value, "message")


class HistoricalOutcomeObservationConfig(StrictModel):
    config_id: str = Field(..., min_length=1)
    strategy_track: StrategyTrack
    forward_window_sizes: list[int] = Field(default_factory=list)
    favorable_return_threshold_pct: float | None = None
    adverse_return_threshold_pct: float | None = None
    volatile_mfe_threshold_pct: float | None = None
    volatile_mae_threshold_pct: float | None = None
    allow_report_only_degraded_calendar: bool = False
    read_only: bool = True
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

    @field_validator("forward_window_sizes", mode="before")
    @classmethod
    def normalize_forward_window_sizes(cls, values):
        if values is None:
            raise ValueError("forward_window_sizes must not be null")
        if not isinstance(values, list):
            raise ValueError("forward_window_sizes must be a list")
        normalized: list[int] = []
        for value in values:
            size = int(value)
            if size <= 0:
                raise ValueError("forward_window_sizes must contain positive integers")
            normalized.append(size)
        if not normalized:
            raise ValueError("forward_window_sizes must not be empty")
        return sorted(set(normalized))

    @model_validator(mode="after")
    def validate_config(self):
        if self.strategy_track != StrategyTrack.DOMESTIC_KR:
            raise ValueError("historical outcome observation config requires StrategyTrack DOMESTIC_KR")
        return _validate_safety_flags(self, "historical outcome observation config")


class HistoricalOutcomeObservationWindow(StrictModel):
    window_id: str = Field(..., min_length=1)
    replay_window_id: str | None = None
    symbol: str = Field(..., min_length=1)
    market: str = Field(..., min_length=1)
    window_size_sessions: int = Field(..., ge=1)
    reference_timestamp: datetime
    observation_start_timestamp: datetime
    observation_end_timestamp: datetime
    window_session_dates: list[date] = Field(default_factory=list)
    historical_market_snapshot_id: str = Field(..., min_length=1)
    historical_calendar_snapshot_id: str | None = None
    source_manifest_ids: list[str] = Field(default_factory=list)
    source_audit_record_ids: list[str] = Field(default_factory=list)
    provider_provenance_ids: list[str] = Field(default_factory=list)
    report_only: bool = True
    read_only: bool = True
    non_executable: bool = True
    local_file_only: bool = True
    no_network: bool = True
    no_provider_api: bool = True
    no_order: bool = True
    no_llm_runtime: bool = True
    no_ml_training: bool = True

    _reference_timestamp = field_validator("reference_timestamp")(aware)
    _observation_start_timestamp = field_validator("observation_start_timestamp")(aware)
    _observation_end_timestamp = field_validator("observation_end_timestamp")(aware)

    @field_validator(
        "window_id",
        "replay_window_id",
        "symbol",
        "market",
        "historical_market_snapshot_id",
        "historical_calendar_snapshot_id",
        mode="before",
    )
    @classmethod
    def normalize_window_fields(cls, value, info):
        if value is None:
            return None
        return _upper_required(value, info.field_name)

    @field_validator("window_session_dates", mode="before")
    @classmethod
    def normalize_window_session_dates(cls, value):
        if value is None:
            return []
        if not isinstance(value, list):
            raise ValueError("window_session_dates must be a list")
        return value

    @field_validator("source_manifest_ids", "source_audit_record_ids", "provider_provenance_ids", mode="before")
    @classmethod
    def normalize_window_lineage_ids(cls, value, info):
        return _normalize_id_list(value, info.field_name)

    @model_validator(mode="after")
    def validate_window(self):
        if self.observation_start_timestamp < self.reference_timestamp:
            raise ValueError("observation_start_timestamp must not be earlier than reference_timestamp")
        if self.observation_end_timestamp < self.observation_start_timestamp:
            raise ValueError("observation_end_timestamp must not be earlier than observation_start_timestamp")
        return _validate_safety_flags(self, "historical outcome observation window")


class HistoricalOutcomeObservationRecord(StrictModel):
    observation_record_id: str = Field(..., min_length=1)
    window_id: str = Field(..., min_length=1)
    symbol: str = Field(..., min_length=1)
    market: str = Field(..., min_length=1)
    observation_timestamp: datetime
    close_price: float = Field(..., gt=0)
    volume: float | None = Field(default=None, ge=0)
    return_from_reference_pct: float | None = None
    outcome_observed_after_anchor: bool = True
    source_manifest_ids: list[str] = Field(default_factory=list)
    source_audit_record_ids: list[str] = Field(default_factory=list)
    provider_provenance_ids: list[str] = Field(default_factory=list)
    report_only: bool = True
    read_only: bool = True
    non_executable: bool = True
    local_file_only: bool = True
    no_network: bool = True
    no_provider_api: bool = True
    no_order: bool = True
    no_llm_runtime: bool = True
    no_ml_training: bool = True

    _observation_timestamp = field_validator("observation_timestamp")(aware)

    @field_validator(
        "observation_record_id",
        "window_id",
        "symbol",
        "market",
        mode="before",
    )
    @classmethod
    def normalize_record_fields(cls, value, info):
        return _upper_required(value, info.field_name)

    @field_validator("source_manifest_ids", "source_audit_record_ids", "provider_provenance_ids", mode="before")
    @classmethod
    def normalize_record_lineage_ids(cls, value, info):
        return _normalize_id_list(value, info.field_name)

    @model_validator(mode="after")
    def validate_record(self):
        if not self.outcome_observed_after_anchor:
            raise ValueError("historical outcome observation record must remain outcome_observed_after_anchor")
        return _validate_safety_flags(self, "historical outcome observation record")


class HistoricalOutcomeMetricSet(StrictModel):
    metric_set_id: str = Field(..., min_length=1)
    window_id: str = Field(..., min_length=1)
    observation_record_ids: list[str] = Field(default_factory=list)
    reference_price: float = Field(..., gt=0)
    anchor_close_price: float = Field(..., gt=0)
    final_price: float | None = Field(default=None, gt=0)
    forward_close_price: float | None = Field(default=None, gt=0)
    forward_return_pct: float | None = None
    max_favorable_excursion_pct: float | None = None
    max_adverse_excursion_pct: float | None = None
    final_return_pct: float | None = None
    high_water_mark: float | None = Field(default=None, gt=0)
    low_water_mark: float | None = Field(default=None, gt=0)
    observed_volume_total: float = Field(default=0, ge=0)
    observed_volume_average: float = Field(default=0, ge=0)
    sessions_observed: int = Field(default=0, ge=0)
    missing_session_count: int = Field(default=0, ge=0)
    early_close_count: int = Field(default=0, ge=0)
    has_market_event_context: bool = False
    has_corporate_event_context: bool = False
    observed_point_count: int = Field(default=0, ge=0)
    report_only: bool = True
    read_only: bool = True
    non_executable: bool = True
    local_file_only: bool = True
    no_network: bool = True
    no_provider_api: bool = True
    no_order: bool = True
    no_llm_runtime: bool = True
    no_ml_training: bool = True

    @field_validator("metric_set_id", "window_id", mode="before")
    @classmethod
    def normalize_metric_fields(cls, value, info):
        return _upper_required(value, info.field_name)

    @field_validator("observation_record_ids", mode="before")
    @classmethod
    def normalize_observation_record_ids(cls, value):
        return _normalize_id_list(value, "observation_record_ids")

    @model_validator(mode="after")
    def validate_metric_set(self):
        if self.observation_record_ids and self.observed_point_count <= 0:
            raise ValueError("observed_point_count must be positive when observation_record_ids are present")
        if self.final_price is not None and self.forward_close_price is not None and self.final_price != self.forward_close_price:
            raise ValueError("final_price must match forward_close_price when both are present")
        return _validate_safety_flags(self, "historical outcome metric set")


class HistoricalOutcomeLabel(StrictModel):
    label_id: str = Field(..., min_length=1)
    window_id: str = Field(..., min_length=1)
    metric_set_id: str = Field(..., min_length=1)
    label_type: HistoricalOutcomeLabelType
    reason_code: str = Field(..., min_length=1)
    symbol: str = Field(..., min_length=1)
    market: str = Field(..., min_length=1)
    final_return_pct: float | None = None
    outcome_observed_after_anchor: bool = True
    report_only: bool = True
    read_only: bool = True
    non_executable: bool = True
    local_file_only: bool = True
    no_network: bool = True
    no_provider_api: bool = True
    no_order: bool = True
    no_llm_runtime: bool = True
    no_ml_training: bool = True

    @field_validator("label_id", "window_id", "metric_set_id", "reason_code", "symbol", "market", mode="before")
    @classmethod
    def normalize_label_fields(cls, value, info):
        return _upper_required(value, info.field_name)

    @model_validator(mode="after")
    def validate_label(self):
        if not self.outcome_observed_after_anchor:
            raise ValueError("historical outcome label must remain outcome_observed_after_anchor")
        return _validate_safety_flags(self, "historical outcome label")


class HistoricalOutcomeSafetyReport(StrictModel):
    safety_report_id: str = Field(default="historical-outcome-safety-report", min_length=1)
    read_only: bool = True
    non_executable: bool = True
    local_file_only: bool = True
    no_network: bool = True
    no_provider_api: bool = True
    no_order: bool = True
    no_llm_runtime: bool = True
    no_ml_training: bool = True

    @field_validator("safety_report_id", mode="before")
    @classmethod
    def normalize_safety_report_id(cls, value):
        return _upper_required(value, "safety_report_id")

    @model_validator(mode="after")
    def validate_safety_report(self):
        return _validate_safety_flags(self, "historical outcome safety report")


class HistoricalOutcomeLabelReport(StrictModel):
    label_report_id: str = Field(..., min_length=1)
    observation_input_id: str = Field(..., min_length=1)
    labels: list[HistoricalOutcomeLabel] = Field(default_factory=list)
    warning_count: int = Field(default=0, ge=0)
    warnings: list[str] = Field(default_factory=list)
    source_manifest_ids: list[str] = Field(default_factory=list)
    source_audit_record_ids: list[str] = Field(default_factory=list)
    provider_provenance_ids: list[str] = Field(default_factory=list)
    safety_report: HistoricalOutcomeSafetyReport = Field(default_factory=HistoricalOutcomeSafetyReport)
    read_only: bool = True
    non_executable: bool = True
    local_file_only: bool = True
    no_network: bool = True
    no_provider_api: bool = True
    no_order: bool = True
    no_llm_runtime: bool = True
    no_ml_training: bool = True

    @field_validator("label_report_id", "observation_input_id", mode="before")
    @classmethod
    def normalize_label_report_fields(cls, value, info):
        return _upper_required(value, info.field_name)

    @field_validator("warnings", mode="before")
    @classmethod
    def normalize_warnings(cls, value):
        return _normalize_string_list(value, "warnings")

    @field_validator("source_manifest_ids", "source_audit_record_ids", "provider_provenance_ids", mode="before")
    @classmethod
    def normalize_label_report_lineage_ids(cls, value, info):
        return _normalize_id_list(value, info.field_name)

    @model_validator(mode="after")
    def validate_label_report(self):
        if self.warning_count != len(self.warnings):
            raise ValueError("warning_count must match warnings length")
        return _validate_safety_flags(self, "historical outcome label report")


class HistoricalOutcomeGapReport(StrictModel):
    gap_report_id: str = Field(..., min_length=1)
    observation_input_id: str = Field(..., min_length=1)
    gap_status: str = Field(..., min_length=1)
    gap_categories: list[HistoricalOutcomeGapCategory] = Field(default_factory=list)
    blocking_gap_count: int = Field(default=0, ge=0)
    report_only_gap_count: int = Field(default=0, ge=0)
    gaps: list[HistoricalOutcomeGapEntry] = Field(default_factory=list)
    source_manifest_ids: list[str] = Field(default_factory=list)
    source_audit_record_ids: list[str] = Field(default_factory=list)
    provider_provenance_ids: list[str] = Field(default_factory=list)
    read_only: bool = True
    non_executable: bool = True
    local_file_only: bool = True
    no_network: bool = True
    no_provider_api: bool = True
    no_order: bool = True
    no_llm_runtime: bool = True
    no_ml_training: bool = True

    @field_validator("gap_report_id", "observation_input_id", "gap_status", mode="before")
    @classmethod
    def normalize_gap_report_fields(cls, value, info):
        return _upper_required(value, info.field_name)

    @field_validator("gap_categories", mode="before")
    @classmethod
    def normalize_gap_categories(cls, value):
        return _normalize_id_list(value, "gap_categories")

    @field_validator("source_manifest_ids", "source_audit_record_ids", "provider_provenance_ids", mode="before")
    @classmethod
    def normalize_gap_report_lineage_ids(cls, value, info):
        return _normalize_id_list(value, info.field_name)

    @model_validator(mode="after")
    def validate_gap_report(self):
        if self.blocking_gap_count + self.report_only_gap_count < len(self.gaps):
            raise ValueError("gap counts must cover every gap entry")
        return _validate_safety_flags(self, "historical outcome gap report")


class HistoricalOutcomeAuditRecord(StrictModel):
    audit_record_id: str = Field(..., min_length=1)
    observation_input_id: str = Field(..., min_length=1)
    created_at: datetime
    operator_context: str = Field(..., min_length=1)
    source_path: str = Field(..., min_length=1)
    source_hash: str | None = None
    label_report_id: str | None = None
    gap_report_id: str | None = None
    safety_report_id: str | None = None
    read_only: bool = True
    non_executable: bool = True
    local_file_only: bool = True
    no_network: bool = True
    no_provider_api: bool = True
    no_order: bool = True
    no_llm_runtime: bool = True
    no_ml_training: bool = True

    _created_at = field_validator("created_at")(aware)

    @field_validator(
        "audit_record_id",
        "observation_input_id",
        "source_hash",
        "label_report_id",
        "gap_report_id",
        "safety_report_id",
        mode="before",
    )
    @classmethod
    def normalize_audit_ids(cls, value, info):
        if value is None:
            return None
        return _upper_required(value, info.field_name)

    @field_validator("operator_context", "source_path", mode="before")
    @classmethod
    def normalize_audit_text(cls, value, info):
        return _string_required(value, info.field_name)

    @model_validator(mode="after")
    def validate_audit_record(self):
        return _validate_safety_flags(self, "historical outcome audit record")


class HistoricalOutcomeObservationInput(StrictModel):
    schema_version: str = "5.3-historical-outcome-observation-input"
    observation_input_id: str = Field(..., min_length=1)
    observation_config: HistoricalOutcomeObservationConfig
    replay_event_stream: HistoricalReplayEventStream
    replay_window_bundle: HistoricalReplayWindowBundle
    scanner_replay_input: HistoricalScannerReplayInput
    historical_market_data_snapshot: HistoricalMarketDataSnapshot
    historical_calendar_event_snapshot: HistoricalCalendarEventSnapshot | None = None
    observation_windows: list[HistoricalOutcomeObservationWindow] = Field(default_factory=list)
    observation_records: list[HistoricalOutcomeObservationRecord] = Field(default_factory=list)
    metric_sets: list[HistoricalOutcomeMetricSet] = Field(default_factory=list)
    label_report: HistoricalOutcomeLabelReport
    gap_report: HistoricalOutcomeGapReport
    safety_report: HistoricalOutcomeSafetyReport = Field(default_factory=HistoricalOutcomeSafetyReport)
    audit_records: list[HistoricalOutcomeAuditRecord] = Field(default_factory=list)

    @field_validator("schema_version")
    @classmethod
    def validate_schema_version(cls, value):
        if value != "5.3-historical-outcome-observation-input":
            raise ValueError("schema_version must be exactly 5.3-historical-outcome-observation-input")
        return value

    @field_validator("observation_input_id", mode="before")
    @classmethod
    def normalize_observation_input_id(cls, value):
        return _upper_required(value, "observation_input_id")

    @model_validator(mode="after")
    def validate_input(self):
        if self.observation_config.strategy_track != StrategyTrack.DOMESTIC_KR:
            raise ValueError("historical outcome observation input requires StrategyTrack DOMESTIC_KR")
        if self.replay_event_stream.strategy_track != self.observation_config.strategy_track:
            raise ValueError("replay_event_stream strategy_track must match observation_config")
        if self.replay_window_bundle.strategy_track != self.observation_config.strategy_track:
            raise ValueError("replay_window_bundle strategy_track must match observation_config")
        if self.scanner_replay_input.strategy_track != self.observation_config.strategy_track:
            raise ValueError("scanner_replay_input strategy_track must match observation_config")
        if self.historical_market_data_snapshot.ingestion_config.strategy_track != self.observation_config.strategy_track:
            raise ValueError("historical_market_data_snapshot strategy_track must match observation_config")
        if self.historical_calendar_event_snapshot is not None:
            if self.historical_calendar_event_snapshot.calendar_config.strategy_track != self.observation_config.strategy_track:
                raise ValueError("historical_calendar_event_snapshot strategy_track must match observation_config")
        expected_market_snapshot_id = _upper_required(
            self.historical_market_data_snapshot.snapshot_id,
            "historical_market_data_snapshot.snapshot_id",
        )
        if self.replay_event_stream.historical_market_snapshot_id != expected_market_snapshot_id:
            raise ValueError("replay_event_stream historical_market_snapshot_id must match historical_market_data_snapshot")
        if self.replay_window_bundle.historical_market_snapshot_id != expected_market_snapshot_id:
            raise ValueError("replay_window_bundle historical_market_snapshot_id must match historical_market_data_snapshot")
        if self.scanner_replay_input.historical_market_snapshot_id != expected_market_snapshot_id:
            raise ValueError("scanner_replay_input historical_market_snapshot_id must match historical_market_data_snapshot")
        expected_calendar_snapshot_id = None
        if self.historical_calendar_event_snapshot is not None:
            expected_calendar_snapshot_id = _upper_required(
                self.historical_calendar_event_snapshot.snapshot_id,
                "historical_calendar_event_snapshot.snapshot_id",
            )
        if expected_calendar_snapshot_id is not None:
            if self.replay_event_stream.historical_calendar_snapshot_id != expected_calendar_snapshot_id:
                raise ValueError("replay_event_stream historical_calendar_snapshot_id must match historical_calendar_event_snapshot")
            if self.replay_window_bundle.historical_calendar_snapshot_id != expected_calendar_snapshot_id:
                raise ValueError("replay_window_bundle historical_calendar_snapshot_id must match historical_calendar_event_snapshot")
            if self.scanner_replay_input.historical_calendar_snapshot_id != expected_calendar_snapshot_id:
                raise ValueError("scanner_replay_input historical_calendar_snapshot_id must match historical_calendar_event_snapshot")
        if self.label_report.observation_input_id != self.observation_input_id:
            raise ValueError("label_report observation_input_id must match observation_input_id")
        if self.gap_report.observation_input_id != self.observation_input_id:
            raise ValueError("gap_report observation_input_id must match observation_input_id")
        for audit_record in self.audit_records:
            if audit_record.observation_input_id != self.observation_input_id:
                raise ValueError("audit_record observation_input_id must match observation_input_id")
        return self
