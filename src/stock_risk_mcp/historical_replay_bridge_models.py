from __future__ import annotations

from datetime import date, datetime
from enum import StrEnum

from pydantic import Field, field_validator, model_validator

from stock_risk_mcp.historical_calendar_models import CalendarEventType, HistoricalCalendarEventSnapshot
from stock_risk_mcp.historical_data_models import HistoricalMarketDataSnapshot
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


def _strip(value: str) -> str:
    return value.strip()


def _upper(value: str) -> str:
    return value.strip().upper()


def _upper_required(value, field_name: str) -> str:
    if value is None:
        raise ValueError(f"{field_name} must not be null")
    cleaned = _upper(str(value))
    if not cleaned:
        raise ValueError(f"{field_name} must not be blank")
    return cleaned


def _string_required(value, field_name: str) -> str:
    if value is None:
        raise ValueError(f"{field_name} must not be null")
    cleaned = _strip(str(value))
    if not cleaned:
        raise ValueError(f"{field_name} must not be blank")
    return cleaned


def _normalize_id_list(value, field_name: str) -> list[str]:
    if value is None:
        return []
    if isinstance(value, (str, bytes)) or not isinstance(value, list):
        raise ValueError(f"{field_name} must be a list")
    return [_upper_required(item, field_name) for item in value]


class HistoricalReplayBridgeGapCategory(StrEnum):
    MISSING_HISTORICAL_MARKET_SNAPSHOT = "MISSING_HISTORICAL_MARKET_SNAPSHOT"
    MISSING_HISTORICAL_CALENDAR_EVENT_SNAPSHOT = "MISSING_HISTORICAL_CALENDAR_EVENT_SNAPSHOT"
    MISSING_SOURCE_MANIFEST = "MISSING_SOURCE_MANIFEST"
    MISSING_SOURCE_AUDIT_RECORD = "MISSING_SOURCE_AUDIT_RECORD"
    MISSING_PROVIDER_PROVENANCE = "MISSING_PROVIDER_PROVENANCE"
    MISSING_STRATEGY_TRACK = "MISSING_STRATEGY_TRACK"
    MISSING_MARKET_PROFILE = "MISSING_MARKET_PROFILE"
    UNSUPPORTED_REPLAY_TRACK = "UNSUPPORTED_REPLAY_TRACK"
    UNSUPPORTED_REPLAY_MARKET = "UNSUPPORTED_REPLAY_MARKET"
    REPLAY_CURRENCY_MISMATCH = "REPLAY_CURRENCY_MISMATCH"
    REPLAY_TIMEZONE_MISMATCH = "REPLAY_TIMEZONE_MISMATCH"
    REPLAY_EVENT_OUT_OF_ORDER = "REPLAY_EVENT_OUT_OF_ORDER"
    REPLAY_EVENT_DUPLICATE = "REPLAY_EVENT_DUPLICATE"
    REPLAY_MISSING_TRADING_CALENDAR = "REPLAY_MISSING_TRADING_CALENDAR"
    REPLAY_MISSING_TRADING_SESSION = "REPLAY_MISSING_TRADING_SESSION"
    REPLAY_HOLIDAY_SESSION_RECOGNIZED = "REPLAY_HOLIDAY_SESSION_RECOGNIZED"
    REPLAY_EARLY_CLOSE_SESSION_FLAGGED = "REPLAY_EARLY_CLOSE_SESSION_FLAGGED"
    REPLAY_CALENDAR_TIMEZONE_MISMATCH = "REPLAY_CALENDAR_TIMEZONE_MISMATCH"
    REPLAY_MARKET_PROFILE_MISMATCH = "REPLAY_MARKET_PROFILE_MISMATCH"
    REPLAY_WINDOW_DEGRADED_REPORT_ONLY = "REPLAY_WINDOW_DEGRADED_REPORT_ONLY"
    REPLAY_WINDOW_OUT_OF_ORDER = "REPLAY_WINDOW_OUT_OF_ORDER"
    REPLAY_WINDOW_SOURCE_LINEAGE_MISSING = "REPLAY_WINDOW_SOURCE_LINEAGE_MISSING"
    REPLAY_UNSUPPORTED_EVENT_CONTEXT = "REPLAY_UNSUPPORTED_EVENT_CONTEXT"
    REPLAY_SOURCE_PROVENANCE_MISSING = "REPLAY_SOURCE_PROVENANCE_MISSING"
    REPLAY_EVENT_KNOWN_TIME_INCOMPLETE = "REPLAY_EVENT_KNOWN_TIME_INCOMPLETE"
    REPLAY_EVENT_CONTEXT_LEAKAGE_BLOCKED = "REPLAY_EVENT_CONTEXT_LEAKAGE_BLOCKED"
    REPLAY_EXECUTABLE_WORDING_DETECTED = "REPLAY_EXECUTABLE_WORDING_DETECTED"
    REPLAY_ORDER_FIELD_DETECTED = "REPLAY_ORDER_FIELD_DETECTED"
    REPLAY_REMOTE_SOURCE_NOT_ALLOWED = "REPLAY_REMOTE_SOURCE_NOT_ALLOWED"
    REPLAY_API_SOURCE_NOT_ALLOWED = "REPLAY_API_SOURCE_NOT_ALLOWED"
    REPLAY_NETWORK_SOURCE_NOT_ALLOWED = "REPLAY_NETWORK_SOURCE_NOT_ALLOWED"


class HistoricalReplayBridgeGapEntry(StrictModel):
    gap_id: str = Field(..., min_length=1)
    gap_category: HistoricalReplayBridgeGapCategory
    severity: str = Field(..., min_length=1)
    message: str = Field(..., min_length=1)
    source_manifest_id: str | None = None
    source_audit_record_id: str | None = None
    provider_provenance_id: str | None = None

    @field_validator(
        "gap_id",
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


class HistoricalReplayBridgeConfig(StrictModel):
    config_id: str = Field(..., min_length=1)
    strategy_track: StrategyTrack
    calendar_required: bool = True
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

    @model_validator(mode="after")
    def enforce_safe_domestic_mode(self):
        if self.strategy_track != StrategyTrack.DOMESTIC_KR:
            raise ValueError("historical replay bridge config requires StrategyTrack DOMESTIC_KR")
        if not self.read_only:
            raise ValueError("historical replay bridge config must remain read_only")
        if not self.non_executable:
            raise ValueError("historical replay bridge config must remain non_executable")
        if not self.local_file_only:
            raise ValueError("historical replay bridge config must remain local_file_only")
        if not self.no_network:
            raise ValueError("historical replay bridge config must remain no_network")
        if not self.no_provider_api:
            raise ValueError("historical replay bridge config must remain no_provider_api")
        if not self.no_order:
            raise ValueError("historical replay bridge config must remain no_order")
        if not self.no_llm_runtime:
            raise ValueError("historical replay bridge config must remain no_llm_runtime")
        if not self.no_ml_training:
            raise ValueError("historical replay bridge config must remain no_ml_training")
        return self


class HistoricalReplayBridgeInput(StrictModel):
    bridge_input_id: str = Field(..., min_length=1)
    historical_market_data_snapshot: HistoricalMarketDataSnapshot
    historical_calendar_event_snapshot: HistoricalCalendarEventSnapshot | None = None
    source_manifest_ids: list[str] = Field(default_factory=list)
    source_audit_record_ids: list[str] = Field(default_factory=list)
    provider_provenance_ids: list[str] = Field(default_factory=list)

    @field_validator("bridge_input_id", mode="before")
    @classmethod
    def normalize_bridge_input_id(cls, value):
        return _upper_required(value, "bridge_input_id")

    @field_validator("source_manifest_ids", "source_audit_record_ids", "provider_provenance_ids", mode="before")
    @classmethod
    def normalize_id_lists(cls, values):
        return _normalize_id_list(values, "bridge_reference_ids")

    @model_validator(mode="after")
    def validate_snapshot_consistency(self):
        market_snapshot = self.historical_market_data_snapshot
        calendar_snapshot = self.historical_calendar_event_snapshot
        if market_snapshot.ingestion_config.strategy_track != StrategyTrack.DOMESTIC_KR:
            raise ValueError("historical replay bridge input requires DOMESTIC_KR market snapshot")
        if calendar_snapshot is not None:
            if calendar_snapshot.calendar_config.strategy_track != market_snapshot.ingestion_config.strategy_track:
                raise ValueError("calendar snapshot strategy_track must match market snapshot strategy_track")
            if calendar_snapshot.manifest.market_profile_id != market_snapshot.source_descriptor.market_profile_id:
                raise ValueError("calendar snapshot market_profile_id must match market snapshot market_profile_id")
            if calendar_snapshot.manifest.calendar_batch_id != calendar_snapshot.validation_report.calendar_batch_id:
                raise ValueError("calendar snapshot validation batch must match calendar manifest batch")
        return self


class HistoricalReplayEvent(StrictModel):
    replay_event_id: str = Field(..., min_length=1)
    bridge_input_id: str = Field(..., min_length=1)
    symbol: str = Field(..., min_length=1)
    market: str = Field(..., min_length=1)
    session_date: date
    replay_timestamp: datetime
    source_record_id: str | None = None
    source_source_id: str | None = None
    currency: str = Field(..., min_length=3)
    timezone: str = Field(..., min_length=1)
    source_manifest_ids: list[str] = Field(default_factory=list)
    source_audit_record_ids: list[str] = Field(default_factory=list)
    provider_provenance_ids: list[str] = Field(default_factory=list)
    historical_market_snapshot_id: str = Field(..., min_length=1)
    historical_calendar_snapshot_id: str | None = None
    report_only: bool = True
    read_only: bool = True
    non_executable: bool = True
    local_file_only: bool = True
    no_order: bool = True
    no_network: bool = True
    no_provider_api: bool = True
    no_llm_runtime: bool = True
    no_ml_training: bool = True

    _timestamp = field_validator("replay_timestamp")(aware)

    @field_validator(
        "replay_event_id",
        "bridge_input_id",
        "symbol",
        "market",
        "source_record_id",
        "source_source_id",
        "currency",
        "historical_market_snapshot_id",
        "historical_calendar_snapshot_id",
        mode="before",
    )
    @classmethod
    def normalize_text_fields(cls, value, info):
        if value is None:
            return None
        if info.field_name == "bridge_input_id":
            return _upper_required(value, info.field_name)
        return _upper_required(value, info.field_name)

    @field_validator("timezone", mode="before")
    @classmethod
    def normalize_timezone(cls, value):
        return _string_required(value, "timezone")

    @field_validator("source_manifest_ids", "source_audit_record_ids", "provider_provenance_ids", mode="before")
    @classmethod
    def normalize_reference_lists(cls, values):
        return _normalize_id_list(values, "replay_reference_ids")

    @model_validator(mode="after")
    def enforce_safe_mode(self):
        if not self.read_only:
            raise ValueError("historical replay event must remain read_only")
        if not self.non_executable:
            raise ValueError("historical replay event must remain non_executable")
        if not self.local_file_only:
            raise ValueError("historical replay event must remain local_file_only")
        if not self.no_order:
            raise ValueError("historical replay event must remain no_order")
        if not self.no_network:
            raise ValueError("historical replay event must remain no_network")
        if not self.no_provider_api:
            raise ValueError("historical replay event must remain no_provider_api")
        if not self.no_llm_runtime:
            raise ValueError("historical replay event must remain no_llm_runtime")
        if not self.no_ml_training:
            raise ValueError("historical replay event must remain no_ml_training")
        return self


class HistoricalReplayEventStream(StrictModel):
    stream_id: str = Field(..., min_length=1)
    bridge_input_id: str = Field(..., min_length=1)
    strategy_track: StrategyTrack
    market_profile_id: str = Field(..., min_length=1)
    source_type: str = Field(..., min_length=1)
    source_file_path: str = Field(..., min_length=1)
    source_currency: str = Field(..., min_length=3)
    source_timezone: str = Field(..., min_length=1)
    source_vendor_name: str | None = None
    source_notes: str | None = None
    historical_market_snapshot_id: str = Field(..., min_length=1)
    historical_calendar_snapshot_id: str | None = None
    source_manifest_ids: list[str] = Field(default_factory=list)
    source_audit_record_ids: list[str] = Field(default_factory=list)
    provider_provenance_ids: list[str] = Field(default_factory=list)
    events: list[HistoricalReplayEvent] = Field(default_factory=list)
    read_only: bool = True
    non_executable: bool = True
    local_file_only: bool = True
    no_network: bool = True
    no_provider_api: bool = True
    no_order: bool = True
    no_llm_runtime: bool = True
    no_ml_training: bool = True

    @field_validator(
        "stream_id",
        "market_profile_id",
        "source_type",
        "source_currency",
        "historical_market_snapshot_id",
        "historical_calendar_snapshot_id",
        mode="before",
    )
    @classmethod
    def normalize_upper_fields(cls, value, info):
        if value is None:
            return None
        return _upper_required(value, info.field_name)

    @field_validator("bridge_input_id", mode="before")
    @classmethod
    def normalize_bridge_id(cls, value):
        return _upper_required(value, "bridge_input_id")

    @field_validator("source_file_path", "source_timezone", "source_vendor_name", "source_notes", mode="before")
    @classmethod
    def normalize_stream_text_fields(cls, value, info):
        if value is None:
            return None
        return _string_required(value, info.field_name)

    @field_validator("source_manifest_ids", "source_audit_record_ids", "provider_provenance_ids", mode="before")
    @classmethod
    def normalize_stream_lineage_ids(cls, values):
        return _normalize_id_list(values, "stream_lineage_ids")

    @model_validator(mode="after")
    def enforce_safe_mode(self):
        if not self.read_only:
            raise ValueError("historical replay event stream must remain read_only")
        if not self.non_executable:
            raise ValueError("historical replay event stream must remain non_executable")
        if not self.local_file_only:
            raise ValueError("historical replay event stream must remain local_file_only")
        if not self.no_network:
            raise ValueError("historical replay event stream must remain no_network")
        if not self.no_provider_api:
            raise ValueError("historical replay event stream must remain no_provider_api")
        if not self.no_order:
            raise ValueError("historical replay event stream must remain no_order")
        if not self.no_llm_runtime:
            raise ValueError("historical replay event stream must remain no_llm_runtime")
        if not self.no_ml_training:
            raise ValueError("historical replay event stream must remain no_ml_training")
        return self


class HistoricalReplayEventContext(StrictModel):
    context_id: str = Field(..., min_length=1)
    replay_window_id: str = Field(..., min_length=1)
    replay_event_stream_id: str = Field(..., min_length=1)
    bridge_input_id: str = Field(..., min_length=1)
    context_scope: str = Field(..., min_length=1)
    event_source_record_id: str = Field(..., min_length=1)
    event_source_id: str = Field(..., min_length=1)
    event_batch_id: str | None = None
    market: str = Field(..., min_length=1)
    symbol: str | None = None
    event_type: CalendarEventType
    event_date: date
    event_time: datetime | None = None
    known_at: datetime | None = None
    known_time_complete: bool = False
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

    _event_time = field_validator("event_time", "known_at")(aware_optional)

    @field_validator(
        "context_id",
        "replay_window_id",
        "replay_event_stream_id",
        "bridge_input_id",
        "context_scope",
        "event_source_record_id",
        "event_source_id",
        "event_batch_id",
        "market",
        "symbol",
        "historical_market_snapshot_id",
        "historical_calendar_snapshot_id",
        mode="before",
    )
    @classmethod
    def normalize_context_fields(cls, value, info):
        if value is None:
            return None
        if info.field_name in {"bridge_input_id", "context_scope"}:
            return _upper_required(value, info.field_name)
        if info.field_name in {"event_source_record_id", "event_source_id", "event_batch_id"}:
            return _upper_required(value, info.field_name)
        if info.field_name == "symbol":
            return _upper_required(value, info.field_name)
        if info.field_name == "market":
            return _upper_required(value, info.field_name)
        return _upper_required(value, info.field_name)

    @field_validator("source_manifest_ids", "source_audit_record_ids", "provider_provenance_ids", mode="before")
    @classmethod
    def normalize_context_lineage_ids(cls, values):
        return _normalize_id_list(values, "event_context_lineage_ids")

    @model_validator(mode="after")
    def enforce_safe_mode(self):
        if not self.report_only:
            raise ValueError("historical replay event context must remain report_only")
        if not self.read_only:
            raise ValueError("historical replay event context must remain read_only")
        if not self.non_executable:
            raise ValueError("historical replay event context must remain non_executable")
        if not self.local_file_only:
            raise ValueError("historical replay event context must remain local_file_only")
        if not self.no_network:
            raise ValueError("historical replay event context must remain no_network")
        if not self.no_provider_api:
            raise ValueError("historical replay event context must remain no_provider_api")
        if not self.no_order:
            raise ValueError("historical replay event context must remain no_order")
        if not self.no_llm_runtime:
            raise ValueError("historical replay event context must remain no_llm_runtime")
        if not self.no_ml_training:
            raise ValueError("historical replay event context must remain no_ml_training")
        return self


class HistoricalReplayWindow(StrictModel):
    window_id: str = Field(..., min_length=1)
    replay_event_stream_id: str | None = None
    bridge_input_id: str = Field(..., min_length=1)
    strategy_track: StrategyTrack
    market_profile_id: str = Field(..., min_length=1)
    session_date: date
    window_size_sessions: int = Field(default=1, ge=1)
    window_session_dates: list[date] = Field(default_factory=list)
    event_ids: list[str] = Field(default_factory=list)
    market_event_contexts: list[HistoricalReplayEventContext] = Field(default_factory=list)
    corporate_event_contexts: list[HistoricalReplayEventContext] = Field(default_factory=list)
    early_close: bool = False
    gap_categories: list[HistoricalReplayBridgeGapCategory] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
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

    @field_validator(
        "window_id",
        "replay_event_stream_id",
        "market_profile_id",
        "historical_market_snapshot_id",
        "historical_calendar_snapshot_id",
        mode="before",
    )
    @classmethod
    def normalize_window_fields(cls, value, info):
        if value is None:
            return None
        return _upper_required(value, info.field_name)

    @field_validator("bridge_input_id", mode="before")
    @classmethod
    def normalize_window_bridge_id(cls, value):
        return _upper_required(value, "bridge_input_id")

    @field_validator("event_ids", mode="before")
    @classmethod
    def normalize_event_ids(cls, values):
        return _normalize_id_list(values, "event_ids")

    @field_validator("market_event_contexts", "corporate_event_contexts", mode="before")
    @classmethod
    def normalize_event_contexts(cls, values):
        if values is None:
            return []
        if isinstance(values, (str, bytes)) or not isinstance(values, list):
            raise ValueError("event contexts must be a list")
        return values

    @field_validator("window_session_dates", mode="before")
    @classmethod
    def normalize_window_session_dates(cls, values):
        if values is None:
            return []
        if not isinstance(values, list):
            raise ValueError("window_session_dates must be a list")
        return values

    @field_validator("source_manifest_ids", "source_audit_record_ids", "provider_provenance_ids", mode="before")
    @classmethod
    def normalize_lineage_ids(cls, values):
        return _normalize_id_list(values, "window_lineage_ids")

    @field_validator("warnings", mode="before")
    @classmethod
    def normalize_warnings(cls, values):
        if values is None:
            return []
        if isinstance(values, (str, bytes)) or not isinstance(values, list):
            raise ValueError("warnings must be a list")
        return [_string_required(value, "warnings") for value in values]

    @model_validator(mode="after")
    def enforce_safe_mode(self):
        if not self.read_only:
            raise ValueError("historical replay window must remain read_only")
        if not self.non_executable:
            raise ValueError("historical replay window must remain non_executable")
        if not self.local_file_only:
            raise ValueError("historical replay window must remain local_file_only")
        if not self.no_network:
            raise ValueError("historical replay window must remain no_network")
        if not self.no_provider_api:
            raise ValueError("historical replay window must remain no_provider_api")
        if not self.no_order:
            raise ValueError("historical replay window must remain no_order")
        if not self.no_llm_runtime:
            raise ValueError("historical replay window must remain no_llm_runtime")
        if not self.no_ml_training:
            raise ValueError("historical replay window must remain no_ml_training")
        return self


class HistoricalReplayBridgeGapReport(StrictModel):
    schema_version: str = "5.2-historical-replay-bridge-gap-report"
    gap_report_id: str = Field(..., min_length=1)
    bridge_input_id: str = Field(..., min_length=1)
    source_manifest_ids: list[str] = Field(default_factory=list)
    source_audit_record_ids: list[str] = Field(default_factory=list)
    provider_provenance_ids: list[str] = Field(default_factory=list)
    historical_market_snapshot_id: str = Field(..., min_length=1)
    historical_calendar_snapshot_id: str | None = None
    gap_categories: list[HistoricalReplayBridgeGapCategory] = Field(default_factory=list)
    blocking_gap_count: int = Field(default=0, ge=0)
    report_only_gap_count: int = Field(default=0, ge=0)
    gaps: list[HistoricalReplayBridgeGapEntry] = Field(default_factory=list)
    read_only: bool = True
    non_executable: bool = True
    local_file_only: bool = True
    no_network: bool = True
    no_provider_api: bool = True
    no_order: bool = True
    no_llm_runtime: bool = True
    no_ml_training: bool = True

    @field_validator(
        "gap_report_id",
        "historical_market_snapshot_id",
        "historical_calendar_snapshot_id",
        mode="before",
    )
    @classmethod
    def normalize_gap_report_id(cls, value, info):
        if value is None:
            return None
        return _upper_required(value, info.field_name)

    @field_validator("bridge_input_id", mode="before")
    @classmethod
    def normalize_gap_bridge_input_id(cls, value):
        return _upper_required(value, "bridge_input_id")

    @field_validator("source_manifest_ids", "source_audit_record_ids", "provider_provenance_ids", mode="before")
    @classmethod
    def normalize_gap_lineage_ids(cls, values):
        return _normalize_id_list(values, "gap_lineage_ids")

    @model_validator(mode="after")
    def enforce_safe_mode(self):
        if not self.read_only:
            raise ValueError("historical replay bridge gap report must remain read_only")
        if not self.non_executable:
            raise ValueError("historical replay bridge gap report must remain non_executable")
        if not self.local_file_only:
            raise ValueError("historical replay bridge gap report must remain local_file_only")
        if not self.no_network:
            raise ValueError("historical replay bridge gap report must remain no_network")
        if not self.no_provider_api:
            raise ValueError("historical replay bridge gap report must remain no_provider_api")
        if not self.no_order:
            raise ValueError("historical replay bridge gap report must remain no_order")
        if not self.no_llm_runtime:
            raise ValueError("historical replay bridge gap report must remain no_llm_runtime")
        if not self.no_ml_training:
            raise ValueError("historical replay bridge gap report must remain no_ml_training")
        return self


class HistoricalReplayEventContextAttachmentReport(StrictModel):
    attachment_report_id: str = Field(..., min_length=1)
    replay_event_stream_id: str = Field(..., min_length=1)
    bridge_input_id: str = Field(..., min_length=1)
    historical_market_snapshot_id: str = Field(..., min_length=1)
    historical_calendar_snapshot_id: str | None = None
    source_manifest_ids: list[str] = Field(default_factory=list)
    source_audit_record_ids: list[str] = Field(default_factory=list)
    provider_provenance_ids: list[str] = Field(default_factory=list)
    attached_market_event_count: int = Field(default=0, ge=0)
    attached_corporate_event_count: int = Field(default=0, ge=0)
    event_source_ids: list[str] = Field(default_factory=list)
    event_batch_ids: list[str] = Field(default_factory=list)
    read_only: bool = True
    non_executable: bool = True
    local_file_only: bool = True
    no_network: bool = True
    no_provider_api: bool = True
    no_order: bool = True
    no_llm_runtime: bool = True
    no_ml_training: bool = True

    @field_validator(
        "attachment_report_id",
        "replay_event_stream_id",
        "bridge_input_id",
        "historical_market_snapshot_id",
        "historical_calendar_snapshot_id",
        mode="before",
    )
    @classmethod
    def normalize_attachment_report_fields(cls, value, info):
        if value is None:
            return None
        return _upper_required(value, info.field_name)

    @field_validator("source_manifest_ids", "source_audit_record_ids", "provider_provenance_ids", mode="before")
    @classmethod
    def normalize_attachment_report_lineage_ids(cls, values):
        return _normalize_id_list(values, "attachment_report_lineage_ids")

    @field_validator("event_source_ids", "event_batch_ids", mode="before")
    @classmethod
    def normalize_attachment_report_event_ids(cls, values):
        return _normalize_id_list(values, "attachment_report_event_ids")

    @model_validator(mode="after")
    def enforce_safe_mode(self):
        if not self.read_only:
            raise ValueError("historical replay event context attachment report must remain read_only")
        if not self.non_executable:
            raise ValueError("historical replay event context attachment report must remain non_executable")
        if not self.local_file_only:
            raise ValueError("historical replay event context attachment report must remain local_file_only")
        if not self.no_network:
            raise ValueError("historical replay event context attachment report must remain no_network")
        if not self.no_provider_api:
            raise ValueError("historical replay event context attachment report must remain no_provider_api")
        if not self.no_order:
            raise ValueError("historical replay event context attachment report must remain no_order")
        if not self.no_llm_runtime:
            raise ValueError("historical replay event context attachment report must remain no_llm_runtime")
        if not self.no_ml_training:
            raise ValueError("historical replay event context attachment report must remain no_ml_training")
        return self


class HistoricalReplayWindowBundle(StrictModel):
    schema_version: str = "5.2-historical-replay-window-bundle"
    window_bundle_id: str = Field(..., min_length=1)
    replay_event_stream_id: str = Field(..., min_length=1)
    bridge_input_id: str = Field(..., min_length=1)
    strategy_track: StrategyTrack
    market_profile_id: str = Field(..., min_length=1)
    requested_window_sizes: list[int] = Field(default_factory=list)
    historical_market_snapshot_id: str = Field(..., min_length=1)
    historical_calendar_snapshot_id: str | None = None
    source_manifest_ids: list[str] = Field(default_factory=list)
    source_audit_record_ids: list[str] = Field(default_factory=list)
    provider_provenance_ids: list[str] = Field(default_factory=list)
    windows: list[HistoricalReplayWindow] = Field(default_factory=list)
    event_context_report: HistoricalReplayEventContextAttachmentReport
    gap_report: HistoricalReplayBridgeGapReport
    degraded_report_only: bool = False
    read_only: bool = True
    non_executable: bool = True
    local_file_only: bool = True
    no_network: bool = True
    no_provider_api: bool = True
    no_order: bool = True
    no_llm_runtime: bool = True
    no_ml_training: bool = True

    @field_validator(
        "window_bundle_id",
        "replay_event_stream_id",
        "market_profile_id",
        "historical_market_snapshot_id",
        "historical_calendar_snapshot_id",
        mode="before",
    )
    @classmethod
    def normalize_bundle_fields(cls, value, info):
        if value is None:
            return None
        return _upper_required(value, info.field_name)

    @field_validator("bridge_input_id", mode="before")
    @classmethod
    def normalize_bundle_bridge_input_id(cls, value):
        return _upper_required(value, "bridge_input_id")

    @field_validator("source_manifest_ids", "source_audit_record_ids", "provider_provenance_ids", mode="before")
    @classmethod
    def normalize_bundle_lineage_ids(cls, values):
        return _normalize_id_list(values, "window_bundle_lineage_ids")

    @field_validator("requested_window_sizes", mode="before")
    @classmethod
    def normalize_requested_window_sizes(cls, values):
        if values is None:
            return []
        if not isinstance(values, list):
            raise ValueError("requested_window_sizes must be a list")
        normalized: list[int] = []
        for value in values:
            size = int(value)
            if size <= 0:
                raise ValueError("requested_window_sizes must contain positive integers")
            normalized.append(size)
        return sorted(set(normalized))

    @model_validator(mode="after")
    def enforce_safe_mode(self):
        if not self.read_only:
            raise ValueError("historical replay window bundle must remain read_only")
        if not self.non_executable:
            raise ValueError("historical replay window bundle must remain non_executable")
        if not self.local_file_only:
            raise ValueError("historical replay window bundle must remain local_file_only")
        if not self.no_network:
            raise ValueError("historical replay window bundle must remain no_network")
        if not self.no_provider_api:
            raise ValueError("historical replay window bundle must remain no_provider_api")
        if not self.no_order:
            raise ValueError("historical replay window bundle must remain no_order")
        if not self.no_llm_runtime:
            raise ValueError("historical replay window bundle must remain no_llm_runtime")
        if not self.no_ml_training:
            raise ValueError("historical replay window bundle must remain no_ml_training")
        return self


class HistoricalReplayBridgeSafetyReport(StrictModel):
    safety_report_id: str = Field(default="historical-replay-bridge-safety-report", min_length=1)
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
    def enforce_safe_defaults(self):
        if not self.read_only:
            raise ValueError("historical replay bridge safety report must remain read_only")
        if not self.non_executable:
            raise ValueError("historical replay bridge safety report must remain non_executable")
        if not self.local_file_only:
            raise ValueError("historical replay bridge safety report must remain local_file_only")
        if not self.no_network:
            raise ValueError("historical replay bridge safety report must remain no_network")
        if not self.no_provider_api:
            raise ValueError("historical replay bridge safety report must remain no_provider_api")
        if not self.no_order:
            raise ValueError("historical replay bridge safety report must remain no_order")
        if not self.no_llm_runtime:
            raise ValueError("historical replay bridge safety report must remain no_llm_runtime")
        if not self.no_ml_training:
            raise ValueError("historical replay bridge safety report must remain no_ml_training")
        return self


class HistoricalReplayBridgeReport(StrictModel):
    schema_version: str = "5.2-historical-replay-bridge-report"
    report_id: str = Field(..., min_length=1)
    bridge_input_id: str = Field(..., min_length=1)
    strategy_track: StrategyTrack
    market_profile_id: str = Field(..., min_length=1)
    historical_market_snapshot_id: str = Field(..., min_length=1)
    historical_calendar_snapshot_id: str | None = None
    source_manifest_ids: list[str] = Field(default_factory=list)
    source_audit_record_ids: list[str] = Field(default_factory=list)
    provider_provenance_ids: list[str] = Field(default_factory=list)
    event_count: int = Field(default=0, ge=0)
    window_count: int = Field(default=0, ge=0)
    safety_report: HistoricalReplayBridgeSafetyReport = Field(default_factory=HistoricalReplayBridgeSafetyReport)
    warnings: list[str] = Field(default_factory=list)
    read_only: bool = True
    non_executable: bool = True
    local_file_only: bool = True
    no_network: bool = True
    no_provider_api: bool = True
    no_order: bool = True
    no_llm_runtime: bool = True
    no_ml_training: bool = True

    @field_validator("report_id", "market_profile_id", "historical_market_snapshot_id", "historical_calendar_snapshot_id", mode="before")
    @classmethod
    def normalize_report_fields(cls, value, info):
        if value is None:
            return None
        return _upper_required(value, info.field_name)

    @field_validator("bridge_input_id", mode="before")
    @classmethod
    def normalize_report_bridge_input_id(cls, value):
        return _upper_required(value, "bridge_input_id")

    @field_validator("source_manifest_ids", "source_audit_record_ids", "provider_provenance_ids", mode="before")
    @classmethod
    def normalize_report_lineage_ids(cls, values):
        return _normalize_id_list(values, "report_lineage_ids")

    @model_validator(mode="after")
    def enforce_safe_mode(self):
        if not self.read_only:
            raise ValueError("historical replay bridge report must remain read_only")
        if not self.non_executable:
            raise ValueError("historical replay bridge report must remain non_executable")
        if not self.local_file_only:
            raise ValueError("historical replay bridge report must remain local_file_only")
        if not self.no_network:
            raise ValueError("historical replay bridge report must remain no_network")
        if not self.no_provider_api:
            raise ValueError("historical replay bridge report must remain no_provider_api")
        if not self.no_order:
            raise ValueError("historical replay bridge report must remain no_order")
        if not self.no_llm_runtime:
            raise ValueError("historical replay bridge report must remain no_llm_runtime")
        if not self.no_ml_training:
            raise ValueError("historical replay bridge report must remain no_ml_training")
        return self


class HistoricalReplayBridgeAuditRecord(StrictModel):
    audit_record_id: str = Field(..., min_length=1)
    bridge_input_id: str = Field(..., min_length=1)
    created_at: datetime
    source_manifest_ids: list[str] = Field(default_factory=list)
    source_audit_record_ids: list[str] = Field(default_factory=list)
    provider_provenance_ids: list[str] = Field(default_factory=list)
    historical_market_snapshot_id: str = Field(..., min_length=1)
    historical_calendar_snapshot_id: str | None = None
    notes: str | None = None
    read_only: bool = True
    non_executable: bool = True
    local_file_only: bool = True
    no_network: bool = True
    no_provider_api: bool = True
    no_order: bool = True
    no_llm_runtime: bool = True
    no_ml_training: bool = True

    _created = field_validator("created_at")(aware)

    @field_validator(
        "audit_record_id",
        "historical_market_snapshot_id",
        "historical_calendar_snapshot_id",
        mode="before",
    )
    @classmethod
    def normalize_audit_fields(cls, value, info):
        if value is None:
            return None
        return _upper_required(value, info.field_name)

    @field_validator("bridge_input_id", mode="before")
    @classmethod
    def normalize_audit_bridge_input_id(cls, value):
        return _upper_required(value, "bridge_input_id")

    @field_validator("source_manifest_ids", "source_audit_record_ids", "provider_provenance_ids", mode="before")
    @classmethod
    def normalize_audit_reference_lists(cls, values):
        return _normalize_id_list(values, "audit_reference_ids")

    @field_validator("notes", mode="before")
    @classmethod
    def normalize_notes(cls, value):
        if value is None:
            return None
        return _strip(str(value))

    @model_validator(mode="after")
    def enforce_safe_mode(self):
        if not self.read_only:
            raise ValueError("historical replay bridge audit record must remain read_only")
        if not self.non_executable:
            raise ValueError("historical replay bridge audit record must remain non_executable")
        if not self.local_file_only:
            raise ValueError("historical replay bridge audit record must remain local_file_only")
        if not self.no_network:
            raise ValueError("historical replay bridge audit record must remain no_network")
        if not self.no_provider_api:
            raise ValueError("historical replay bridge audit record must remain no_provider_api")
        if not self.no_order:
            raise ValueError("historical replay bridge audit record must remain no_order")
        if not self.no_llm_runtime:
            raise ValueError("historical replay bridge audit record must remain no_llm_runtime")
        if not self.no_ml_training:
            raise ValueError("historical replay bridge audit record must remain no_ml_training")
        return self
