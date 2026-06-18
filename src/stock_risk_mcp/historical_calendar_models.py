from __future__ import annotations

from datetime import date, datetime, time
from enum import StrEnum

from pydantic import Field, field_validator, model_validator

from stock_risk_mcp.models import StrictModel
from stock_risk_mcp.strategy_track_models import MarketProfile, StrategyTrack


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
    return _upper(str(value))


class HistoricalCalendarSourceType(StrEnum):
    LOCAL_CSV = "local_csv"
    LOCAL_JSONL = "local_jsonl"


class CalendarSessionType(StrEnum):
    MARKET_HOLIDAY = "MARKET_HOLIDAY"
    EARLY_CLOSE = "EARLY_CLOSE"
    REGULAR_SESSION = "REGULAR_SESSION"


class CalendarEventType(StrEnum):
    MARKET_HOLIDAY = "MARKET_HOLIDAY"
    EARLY_CLOSE = "EARLY_CLOSE"
    REGULAR_SESSION = "REGULAR_SESSION"
    OPTIONS_EXPIRATION = "OPTIONS_EXPIRATION"
    FUTURES_EXPIRATION = "FUTURES_EXPIRATION"
    QUADRUPLE_WITCHING = "QUADRUPLE_WITCHING"
    FOMC_DECISION = "FOMC_DECISION"
    CPI_RELEASE = "CPI_RELEASE"
    PPI_RELEASE = "PPI_RELEASE"
    JOBS_REPORT = "JOBS_REPORT"
    ELECTION_DAY = "ELECTION_DAY"
    EARNINGS_BEFORE_OPEN = "EARNINGS_BEFORE_OPEN"
    EARNINGS_AFTER_CLOSE = "EARNINGS_AFTER_CLOSE"
    DIVIDEND_EX_DATE = "DIVIDEND_EX_DATE"
    SPLIT_EFFECTIVE_DATE = "SPLIT_EFFECTIVE_DATE"
    CORPORATE_ACTION = "CORPORATE_ACTION"


class CalendarValidationStatus(StrEnum):
    VALID = "VALID"
    VALID_WITH_WARNINGS = "VALID_WITH_WARNINGS"
    INVALID = "INVALID"


class CalendarGapStatus(StrEnum):
    NO_GAPS = "NO_GAPS"
    REPORT_ONLY_GAPS = "REPORT_ONLY_GAPS"
    BLOCKING_GAPS = "BLOCKING_GAPS"


class CalendarGapCategory(StrEnum):
    MISSING_CALENDAR_FILE = "MISSING_CALENDAR_FILE"
    UNSUPPORTED_SOURCE_TYPE = "UNSUPPORTED_SOURCE_TYPE"
    REMOTE_FETCH_NOT_ALLOWED = "REMOTE_FETCH_NOT_ALLOWED"
    PROVIDER_API_NOT_ALLOWED = "PROVIDER_API_NOT_ALLOWED"
    UNSAFE_SOURCE_PATH = "UNSAFE_SOURCE_PATH"
    TIMEZONE_MISMATCH = "TIMEZONE_MISMATCH"
    MARKET_PROFILE_MISMATCH = "MARKET_PROFILE_MISMATCH"
    DUPLICATE_SESSION = "DUPLICATE_SESSION"
    DUPLICATE_EVENT = "DUPLICATE_EVENT"
    MISSING_SESSION = "MISSING_SESSION"
    UNSUPPORTED_TRACK = "UNSUPPORTED_TRACK"


class TradingCalendarConfig(StrictModel):
    calendar_config_id: str = Field(..., min_length=1)
    strategy_track: StrategyTrack
    market_profile: MarketProfile
    source_type: HistoricalCalendarSourceType
    session_validation_mode: str = Field(..., min_length=1)
    unexpected_closure_policy: str = Field(..., min_length=1)
    early_close_policy: str = Field(..., min_length=1)
    event_type_policy: str = Field(..., min_length=1)
    timezone_mismatch_policy: str = Field(..., min_length=1)
    read_only: bool = True
    non_executable: bool = True
    network_access_allowed: bool = False
    provider_api_allowed: bool = False

    @field_validator(
        "calendar_config_id",
        "session_validation_mode",
        "unexpected_closure_policy",
        "early_close_policy",
        "event_type_policy",
        "timezone_mismatch_policy",
    )
    @classmethod
    def normalize_fields(cls, value: str) -> str:
        return _upper(value)

    @model_validator(mode="after")
    def enforce_safe_domestic_mode(self):
        if self.strategy_track != StrategyTrack.DOMESTIC_KR:
            raise ValueError("trading calendar config requires StrategyTrack DOMESTIC_KR")
        profile = self.market_profile
        if profile.market_id != "KRX" or profile.country != "KR" or profile.base_currency != "KRW":
            raise ValueError("DOMESTIC_KR market profile is inconsistent")
        if not self.read_only:
            raise ValueError("trading calendar config must remain read_only")
        if not self.non_executable:
            raise ValueError("trading calendar config must remain non_executable")
        if self.network_access_allowed:
            raise ValueError("network_access_allowed must remain false")
        if self.provider_api_allowed:
            raise ValueError("provider_api_allowed must remain false")
        return self


class TradingSessionRecord(StrictModel):
    market: str = Field(..., min_length=1)
    date: date
    timezone: str = Field(..., min_length=1)
    is_trading_day: bool
    is_holiday: bool
    is_early_close: bool
    regular_open_time: time | None = None
    regular_close_time: time | None = None
    actual_open_time: time | None = None
    actual_close_time: time | None = None
    session_type: CalendarSessionType
    source_id: str = Field(..., min_length=1)
    calendar_batch_id: str = Field(..., min_length=1)

    @field_validator("market", "source_id", "calendar_batch_id", mode="before")
    @classmethod
    def normalize_required_fields(cls, value, info):
        return _upper_required(value, info.field_name)

    @field_validator("timezone", mode="before")
    @classmethod
    def strip_timezone(cls, value):
        return _strip(str(value))


class MarketEventRecord(StrictModel):
    event_id: str = Field(..., min_length=1)
    market: str = Field(..., min_length=1)
    event_date: date
    event_time: datetime | None = None
    timezone: str = Field(..., min_length=1)
    event_type: CalendarEventType
    event_scope: str = Field(..., min_length=1)
    affected_symbols: list[str] = Field(default_factory=list)
    affected_market: str | None = None
    source_id: str = Field(..., min_length=1)
    event_batch_id: str = Field(..., min_length=1)
    report_only: bool = False
    non_executable: bool = True

    _event_time = field_validator("event_time")(aware_optional)

    @field_validator(
        "event_id",
        "market",
        "event_scope",
        "affected_market",
        "source_id",
        "event_batch_id",
        mode="before",
    )
    @classmethod
    def normalize_optional_required_upper_fields(cls, value, info):
        if value is None:
            return None
        return _upper_required(value, info.field_name)

    @field_validator("timezone", mode="before")
    @classmethod
    def strip_timezone(cls, value):
        return _strip(str(value))

    @field_validator("affected_symbols", mode="before")
    @classmethod
    def normalize_affected_symbols(cls, values):
        cleaned = [_upper_required(value, "affected_symbols") for value in values]
        if any(not value for value in cleaned):
            raise ValueError("affected_symbols must not contain blank values")
        return cleaned

    @model_validator(mode="after")
    def enforce_safe_mode(self):
        if not self.affected_symbols and not self.affected_market:
            raise ValueError("market event record requires affected_symbols or affected_market")
        if not self.non_executable:
            raise ValueError("market event record must remain non_executable")
        return self


class CorporateEventRecord(StrictModel):
    symbol: str = Field(..., min_length=1)
    market: str = Field(..., min_length=1)
    event_date: date
    event_type: CalendarEventType
    earnings_before_open_flag: bool = False
    earnings_after_close_flag: bool = False
    dividend_ex_date_flag: bool = False
    split_effective_date_flag: bool = False
    corporate_action_adjustment_flag: bool = False
    source_id: str = Field(..., min_length=1)

    @field_validator("symbol", "market", "source_id", mode="before")
    @classmethod
    def normalize_required_fields(cls, value, info):
        return _upper_required(value, info.field_name)


class CalendarSafetyBoundary(StrictModel):
    read_only: bool = True
    non_executable: bool = True
    network_access_allowed: bool = False
    provider_api_allowed: bool = False
    exchange_api_allowed: bool = False
    broker_api_allowed: bool = False
    kiwoom_api_allowed: bool = False
    ls_api_allowed: bool = False
    account_access_allowed: bool = False
    credential_access_allowed: bool = False
    token_access_allowed: bool = False
    live_or_prod_allowed: bool = False
    cloud_llm_allowed: bool = False
    local_model_runtime_allowed: bool = False
    prompt_pack_execution_allowed: bool = False
    prompt_stub_execution_allowed: bool = False

    @model_validator(mode="after")
    def enforce_deny_defaults(self):
        if not self.read_only:
            raise ValueError("calendar safety boundary must remain read_only")
        if not self.non_executable:
            raise ValueError("calendar safety boundary must remain non_executable")
        denied_flags = (
            "network_access_allowed",
            "provider_api_allowed",
            "exchange_api_allowed",
            "broker_api_allowed",
            "kiwoom_api_allowed",
            "ls_api_allowed",
            "account_access_allowed",
            "credential_access_allowed",
            "token_access_allowed",
            "live_or_prod_allowed",
            "cloud_llm_allowed",
            "local_model_runtime_allowed",
            "prompt_pack_execution_allowed",
            "prompt_stub_execution_allowed",
        )
        for field_name in denied_flags:
            if getattr(self, field_name):
                raise ValueError(f"{field_name} must remain false")
        return self


class CalendarValidationReport(StrictModel):
    calendar_validation_report_id: str = Field(..., min_length=1)
    calendar_batch_id: str = Field(..., min_length=1)
    strategy_track: StrategyTrack
    market_profile_id: str = Field(..., min_length=1)
    validation_status: CalendarValidationStatus
    error_count: int = Field(..., ge=0)
    warning_count: int = Field(..., ge=0)
    validation_issues: list[dict] = Field(default_factory=list)
    read_only: bool = True
    non_executable: bool = True

    @field_validator("calendar_validation_report_id", "calendar_batch_id", "market_profile_id", mode="before")
    @classmethod
    def normalize_required_fields(cls, value, info):
        return _upper_required(value, info.field_name)


class CalendarGapReport(StrictModel):
    calendar_gap_report_id: str = Field(..., min_length=1)
    calendar_batch_id: str = Field(..., min_length=1)
    gap_status: CalendarGapStatus
    gap_categories: list[CalendarGapCategory] = Field(default_factory=list)
    blocking_gap_count: int = Field(..., ge=0)
    report_only_gap_count: int = Field(..., ge=0)
    gaps: list[dict] = Field(default_factory=list)
    read_only: bool = True
    non_executable: bool = True

    @field_validator("calendar_gap_report_id", "calendar_batch_id", mode="before")
    @classmethod
    def normalize_required_fields(cls, value, info):
        return _upper_required(value, info.field_name)


class HistoricalCalendarManifest(StrictModel):
    calendar_manifest_id: str = Field(..., min_length=1)
    calendar_batch_id: str = Field(..., min_length=1)
    source_descriptor_ids: list[str] = Field(..., min_length=1)
    strategy_track: StrategyTrack
    market_profile_id: str = Field(..., min_length=1)
    session_record_count: int = Field(..., ge=0)
    market_event_count: int = Field(..., ge=0)
    corporate_event_count: int = Field(..., ge=0)
    date_range_start: datetime
    date_range_end: datetime
    timezone: str = Field(..., min_length=1)
    validation_report_id: str = Field(..., min_length=1)
    gap_report_id: str = Field(..., min_length=1)
    safety_boundary: CalendarSafetyBoundary = Field(default_factory=CalendarSafetyBoundary)
    read_only: bool = True
    non_executable: bool = True
    no_network: bool = True
    no_provider_api: bool = True

    _start = field_validator("date_range_start")(aware)
    _end = field_validator("date_range_end")(aware)

    @field_validator(
        "calendar_manifest_id",
        "calendar_batch_id",
        "market_profile_id",
        "validation_report_id",
        "gap_report_id",
        mode="before",
    )
    @classmethod
    def normalize_required_fields(cls, value, info):
        return _upper_required(value, info.field_name)

    @field_validator("source_descriptor_ids", mode="before")
    @classmethod
    def normalize_source_descriptor_ids(cls, values):
        cleaned = [_upper_required(value, "source_descriptor_ids") for value in values]
        if any(not value for value in cleaned):
            raise ValueError("source_descriptor_ids must not contain blank values")
        return cleaned

    @field_validator("timezone", mode="before")
    @classmethod
    def strip_timezone(cls, value):
        return _strip(str(value))

    @model_validator(mode="after")
    def validate_range_and_safe_mode(self):
        if self.date_range_end < self.date_range_start:
            raise ValueError("date_range_end must be greater than or equal to date_range_start")
        if not self.read_only:
            raise ValueError("historical calendar manifest must remain read_only")
        if not self.non_executable:
            raise ValueError("historical calendar manifest must remain non_executable")
        if not self.no_network:
            raise ValueError("no_network must remain true")
        if not self.no_provider_api:
            raise ValueError("no_provider_api must remain true")
        return self


class HistoricalCalendarEventSnapshot(StrictModel):
    schema_version: str
    snapshot_id: str = Field(..., min_length=1)
    created_at: datetime
    calendar_config: TradingCalendarConfig
    session_records: list[TradingSessionRecord] = Field(default_factory=list)
    market_events: list[MarketEventRecord] = Field(default_factory=list)
    corporate_events: list[CorporateEventRecord] = Field(default_factory=list)
    manifest: HistoricalCalendarManifest
    validation_report: CalendarValidationReport
    gap_report: CalendarGapReport
    safety_boundary: CalendarSafetyBoundary = Field(default_factory=CalendarSafetyBoundary)

    _created = field_validator("created_at")(aware)

    @field_validator("schema_version")
    @classmethod
    def exact_schema(cls, value: str) -> str:
        if value != "5.1-historical-calendar-event-snapshot":
            raise ValueError("schema_version must be exactly 5.1-historical-calendar-event-snapshot")
        return value

    @field_validator("snapshot_id", mode="before")
    @classmethod
    def normalize_snapshot_id(cls, value):
        return _strip(str(value))

    @model_validator(mode="after")
    def validate_consistency(self):
        if self.calendar_config.strategy_track != StrategyTrack.DOMESTIC_KR:
            raise ValueError("historical calendar snapshot requires StrategyTrack DOMESTIC_KR")
        if self.manifest.strategy_track != self.calendar_config.strategy_track:
            raise ValueError("manifest strategy_track must match calendar_config strategy_track")
        if self.validation_report.strategy_track != self.calendar_config.strategy_track:
            raise ValueError("validation report strategy_track must match calendar_config strategy_track")
        if self.manifest.market_profile_id != self.calendar_config.market_profile.market_id:
            raise ValueError("manifest market_profile_id must match calendar_config market_profile")
        if self.validation_report.market_profile_id != self.calendar_config.market_profile.market_id:
            raise ValueError("validation report market_profile_id must match calendar_config market_profile")
        if self.manifest.calendar_batch_id != self.validation_report.calendar_batch_id:
            raise ValueError("manifest and validation report calendar_batch_id must match")
        if self.manifest.calendar_batch_id != self.gap_report.calendar_batch_id:
            raise ValueError("manifest and gap report calendar_batch_id must match")
        if self.manifest.validation_report_id != self.validation_report.calendar_validation_report_id:
            raise ValueError("manifest validation_report_id must match validation report id")
        if self.manifest.gap_report_id != self.gap_report.calendar_gap_report_id:
            raise ValueError("manifest gap_report_id must match gap report id")
        if self.manifest.session_record_count != len(self.session_records):
            raise ValueError("manifest session_record_count must match session_records")
        if self.manifest.market_event_count != len(self.market_events):
            raise ValueError("manifest market_event_count must match market_events")
        if self.manifest.corporate_event_count != len(self.corporate_events):
            raise ValueError("manifest corporate_event_count must match corporate_events")
        return self
