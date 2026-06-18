from __future__ import annotations

from collections import Counter
from datetime import datetime
from enum import StrEnum
import re

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


def _strip_required(value, field_name: str) -> str:
    if value is None:
        raise ValueError(f"{field_name} must not be null")
    return _strip(str(value))


def _local_path_required(value, field_name: str) -> str:
    cleaned = _strip_required(value, field_name)
    lowered = cleaned.lower()
    if lowered.startswith(("http://", "https://")) or "://" in lowered:
        raise ValueError(f"{field_name} must be a local path")
    if re.match(r"^[a-z][a-z0-9_+.-]*:", lowered) and not re.match(r"^[a-z]:[\\/]", cleaned, re.IGNORECASE):
        raise ValueError(f"{field_name} must be a local path")
    return cleaned


class HistoricalDataSourceType(StrEnum):
    LOCAL_CSV = "local_csv"
    LOCAL_JSONL = "local_jsonl"
    LOCAL_PARQUET = "local_parquet"
    REMOTE_URL = "remote_url"
    PROVIDER_API = "provider_api"


class HistoricalGapCategory(StrEnum):
    MISSING_HISTORICAL_DATA_FILE = "MISSING_HISTORICAL_DATA_FILE"
    UNSUPPORTED_SOURCE_TYPE = "UNSUPPORTED_SOURCE_TYPE"
    REMOTE_FETCH_NOT_ALLOWED = "REMOTE_FETCH_NOT_ALLOWED"
    PROVIDER_API_NOT_ALLOWED = "PROVIDER_API_NOT_ALLOWED"
    UNSAFE_SOURCE_PATH = "UNSAFE_SOURCE_PATH"
    TIMEZONE_MISMATCH = "TIMEZONE_MISMATCH"
    CURRENCY_MISMATCH = "CURRENCY_MISMATCH"
    MARKET_PROFILE_MISMATCH = "MARKET_PROFILE_MISMATCH"
    DUPLICATE_RECORD = "DUPLICATE_RECORD"
    OUT_OF_ORDER_RECORD = "OUT_OF_ORDER_RECORD"
    INVALID_OHLC = "INVALID_OHLC"
    INVALID_VOLUME = "INVALID_VOLUME"
    MISSING_SESSION = "MISSING_SESSION"
    STALE_BATCH = "STALE_BATCH"


class HistoricalValidationStatus(StrEnum):
    VALID = "VALID"
    VALID_WITH_WARNINGS = "VALID_WITH_WARNINGS"
    INVALID = "INVALID"


class HistoricalGapStatus(StrEnum):
    NO_GAPS = "NO_GAPS"
    REPORT_ONLY_GAPS = "REPORT_ONLY_GAPS"
    BLOCKING_GAPS = "BLOCKING_GAPS"


class HistoricalQualityBucket(StrEnum):
    READY = "READY"
    REPORT_ONLY = "REPORT_ONLY"
    BLOCKED = "BLOCKED"


class HistoricalDataIngestionConfig(StrictModel):
    config_id: str = Field(..., min_length=1)
    strategy_track: StrategyTrack
    market_profile: MarketProfile
    source_type: HistoricalDataSourceType
    strict_validation_mode: bool = True
    allow_report_only_downgrade: bool = False
    currency_mismatch_policy: str = Field(default="FAIL_CLOSED", min_length=1)
    duplicate_record_policy: str = Field(default="FAIL_CLOSED", min_length=1)
    missing_session_policy: str = Field(default="FAIL_CLOSED", min_length=1)
    stale_batch_policy: str = Field(default="FAIL_CLOSED", min_length=1)
    unsupported_track_policy: str = Field(default="FAIL_CLOSED", min_length=1)
    unsafe_source_policy: str = Field(default="FAIL_CLOSED", min_length=1)
    read_only: bool = True
    non_executable: bool = True
    network_access_allowed: bool = False
    provider_api_allowed: bool = False

    @field_validator(
        "config_id",
        "currency_mismatch_policy",
        "duplicate_record_policy",
        "missing_session_policy",
        "stale_batch_policy",
        "unsupported_track_policy",
        "unsafe_source_policy",
    )
    @classmethod
    def strip_fields(cls, value: str) -> str:
        return _upper(value)

    @field_validator("source_type")
    @classmethod
    def supported_source_type_only(cls, value: HistoricalDataSourceType) -> HistoricalDataSourceType:
        if value not in {HistoricalDataSourceType.LOCAL_CSV, HistoricalDataSourceType.LOCAL_JSONL}:
            raise ValueError("source_type must be one of local_csv or local_jsonl")
        return value

    @model_validator(mode="after")
    def enforce_safe_mode(self):
        if not self.read_only:
            raise ValueError("historical ingestion config must remain read_only")
        if not self.non_executable:
            raise ValueError("historical ingestion config must remain non_executable")
        if self.network_access_allowed:
            raise ValueError("network_access_allowed must remain false")
        if self.provider_api_allowed:
            raise ValueError("provider_api_allowed must remain false")
        return self


class HistoricalDataSourceDescriptor(StrictModel):
    source_descriptor_id: str = Field(..., min_length=1)
    source_type: HistoricalDataSourceType
    local_file_path: str = Field(..., min_length=1)
    declared_format: str | None = None
    declared_content_type: str | None = None
    strategy_track: StrategyTrack
    market_profile_id: str = Field(..., min_length=1)
    source_id: str = Field(..., min_length=1)
    source_vendor_name: str | None = None
    source_reliability_tier: str | None = None
    path_safety_class: str | None = None
    timezone: str = Field(..., min_length=1)
    currency: str = Field(..., min_length=3)
    source_symbol_namespace: str | None = None
    contains_adjusted_prices: bool = False
    contains_unadjusted_prices: bool = True
    contains_turnover: bool = False
    contains_trade_value: bool = False
    report_only: bool = False
    read_only: bool = True
    non_executable: bool = True

    @field_validator("source_descriptor_id", "market_profile_id", "source_id", "currency", mode="before")
    @classmethod
    def normalize_required_fields(cls, value, info):
        return _upper_required(value, info.field_name)

    @field_validator(
        "declared_format",
        "source_reliability_tier",
        "path_safety_class",
        "source_symbol_namespace",
        mode="before",
    )
    @classmethod
    def normalize_optional_upper_fields(cls, value):
        if value is None:
            return None
        return _upper(str(value))

    @field_validator("declared_content_type", "source_vendor_name", "timezone", mode="before")
    @classmethod
    def strip_fidelity_fields(cls, value):
        if value is None:
            return None
        return _strip(str(value))

    @field_validator("local_file_path")
    @classmethod
    def local_path_only(cls, value: str) -> str:
        return _local_path_required(value, "local_file_path")

    @field_validator("source_type")
    @classmethod
    def supported_source_type_only(cls, value: HistoricalDataSourceType) -> HistoricalDataSourceType:
        if value not in {HistoricalDataSourceType.LOCAL_CSV, HistoricalDataSourceType.LOCAL_JSONL}:
            raise ValueError("source_type must be one of local_csv or local_jsonl")
        return value

    @model_validator(mode="after")
    def validate_local_file_path_for_source_type(self):
        expected_extension = {
            HistoricalDataSourceType.LOCAL_CSV: ".csv",
            HistoricalDataSourceType.LOCAL_JSONL: ".jsonl",
        }[self.source_type]
        if not self.local_file_path.lower().endswith(expected_extension):
            raise ValueError(f"{self.source_type.value} sources must use a {expected_extension} local_file_path")
        return self

    @model_validator(mode="after")
    def enforce_safe_mode(self):
        if not self.read_only:
            raise ValueError("historical source descriptor must remain read_only")
        if not self.non_executable:
            raise ValueError("historical source descriptor must remain non_executable")
        return self


class HistoricalOHLCVRecord(StrictModel):
    symbol: str = Field(..., min_length=1)
    market: str = Field(..., min_length=1)
    timestamp: datetime
    timezone: str = Field(..., min_length=1)
    open: float = Field(..., gt=0)
    high: float = Field(..., gt=0)
    low: float = Field(..., gt=0)
    close: float = Field(..., gt=0)
    volume: float = Field(..., ge=0)
    currency: str = Field(..., min_length=3)
    source_id: str = Field(..., min_length=1)
    ingestion_batch_id: str = Field(..., min_length=1)
    adjusted_close: float | None = Field(default=None, gt=0)
    turnover: float | None = Field(default=None, ge=0)
    trade_value: float | None = Field(default=None, ge=0)
    listed_market_segment: str | None = None
    data_vendor_note: str | None = None
    corporate_action_adjustment_flag: bool = False
    split_adjustment_flag: bool = False
    dividend_adjustment_flag: bool = False
    source_symbol: str | None = None
    canonical_symbol: str | None = None

    _timestamp = field_validator("timestamp")(aware)

    @field_validator("symbol", "market", "currency", "source_id", "ingestion_batch_id", mode="before")
    @classmethod
    def normalize_required_fields(cls, value, info):
        return _upper_required(value, info.field_name)

    @field_validator("listed_market_segment", "source_symbol", "canonical_symbol", mode="before")
    @classmethod
    def normalize_optional_upper_fields(cls, value):
        if value is None:
            return None
        return _upper(str(value))

    @field_validator("timezone", mode="before")
    @classmethod
    def strip_timezone(cls, value):
        if value is None:
            return None
        return _strip(str(value))

    @field_validator("data_vendor_note", mode="before")
    @classmethod
    def strip_note(cls, value):
        if value is None:
            return None
        return _strip(str(value))

    @model_validator(mode="after")
    def validate_ohlc_bounds(self):
        if self.high < self.open or self.high < self.close or self.high < self.low:
            raise ValueError("high price must be greater than or equal to open, close, and low")
        if self.low > self.open or self.low > self.close or self.low > self.high:
            raise ValueError("low price must be less than or equal to open, close, and high")
        return self


class HistoricalDataAdjustmentPolicy(StrictModel):
    policy_id: str = Field(..., min_length=1)
    price_adjustment_mode: str = Field(..., min_length=1)
    split_adjustment_expected: bool = False
    dividend_adjustment_expected: bool = False
    corporate_action_backfill_expected: bool = False
    adjusted_close_required: bool = False
    mixed_adjustment_state_allowed: bool = False
    report_only_if_uncertain: bool = True

    @field_validator("policy_id", "price_adjustment_mode", mode="before")
    @classmethod
    def normalize_fields(cls, value, info) -> str:
        return _upper_required(value, info.field_name)


class HistoricalDataProviderProvenance(StrictModel):
    provenance_id: str = Field(..., min_length=1)
    source_family: str = Field(..., min_length=1)
    source_name: str = Field(..., min_length=1)
    source_tier: str = Field(..., min_length=1)
    acquisition_mode: str = Field(..., min_length=1)
    original_export_context: str | None = None
    local_export_timestamp: datetime | None = None
    manual_or_automated_origin: str | None = None
    requires_reconciliation: bool = False
    official_source_reference: str | None = None
    notes: str | None = None

    _local_export_timestamp = field_validator("local_export_timestamp")(aware_optional)

    @field_validator("provenance_id", "source_family", "source_tier", "acquisition_mode", mode="before")
    @classmethod
    def normalize_upper_fields(cls, value, info):
        return _upper_required(value, info.field_name)

    @field_validator(
        "source_name",
        "original_export_context",
        "manual_or_automated_origin",
        "official_source_reference",
        mode="before",
    )
    @classmethod
    def strip_provenance_fidelity_fields(cls, value):
        if value is None:
            return None
        return _strip(str(value))

    @field_validator("notes", mode="before")
    @classmethod
    def strip_notes(cls, value):
        if value is None:
            return None
        return _strip(str(value))


class HistoricalDataSafetyBoundary(StrictModel):
    read_only: bool = True
    non_executable: bool = True
    network_access_allowed: bool = False
    provider_api_allowed: bool = False
    account_access_allowed: bool = False
    credential_access_allowed: bool = False
    token_access_allowed: bool = False
    order_intent_allowed: bool = False
    order_draft_allowed: bool = False
    execution_approval_allowed: bool = False
    live_or_prod_allowed: bool = False
    cloud_llm_allowed: bool = False
    local_model_runtime_allowed: bool = False
    ml_training_allowed: bool = False

    @model_validator(mode="after")
    def enforce_boundary(self):
        if not self.read_only:
            raise ValueError("read_only must remain true")
        if not self.non_executable:
            raise ValueError("non_executable must remain true")
        for field_name in (
            "network_access_allowed",
            "provider_api_allowed",
            "account_access_allowed",
            "credential_access_allowed",
            "token_access_allowed",
            "order_intent_allowed",
            "order_draft_allowed",
            "execution_approval_allowed",
            "live_or_prod_allowed",
            "cloud_llm_allowed",
            "local_model_runtime_allowed",
            "ml_training_allowed",
        ):
            if getattr(self, field_name):
                raise ValueError(f"{field_name} must remain false")
        return self


class HistoricalDataAuditRecord(StrictModel):
    audit_record_id: str = Field(..., min_length=1)
    ingestion_batch_id: str = Field(..., min_length=1)
    source_descriptor_id: str = Field(..., min_length=1)
    created_at: datetime
    operator_context: str | None = None
    local_file_path: str = Field(..., min_length=1)
    local_file_hash: str = Field(..., min_length=1)
    parser_version: str = Field(..., min_length=1)
    validation_report_id: str = Field(..., min_length=1)
    quality_report_id: str = Field(..., min_length=1)
    gap_report_id: str = Field(..., min_length=1)
    read_only: bool = True
    non_executable: bool = True
    no_network: bool = True
    no_provider_api: bool = True

    _created = field_validator("created_at")(aware)

    @field_validator(
        "audit_record_id",
        "ingestion_batch_id",
        "source_descriptor_id",
        "local_file_hash",
        "parser_version",
        "validation_report_id",
        "quality_report_id",
        "gap_report_id",
        mode="before",
    )
    @classmethod
    def normalize_upper_fields(cls, value, info):
        return _upper_required(value, info.field_name)

    @field_validator("operator_context", mode="before")
    @classmethod
    def normalize_optional_operator_context(cls, value):
        if value is None:
            return None
        return _upper(str(value))

    @field_validator("local_file_path", mode="before")
    @classmethod
    def strip_local_file_path(cls, value: str) -> str:
        return _local_path_required(value, "local_file_path")

    @model_validator(mode="after")
    def enforce_safe_flags(self):
        if not self.read_only:
            raise ValueError("audit record must remain read_only")
        if not self.non_executable:
            raise ValueError("audit record must remain non_executable")
        if not self.no_network:
            raise ValueError("audit record must remain no_network")
        if not self.no_provider_api:
            raise ValueError("audit record must remain no_provider_api")
        return self


class HistoricalDataValidationReport(StrictModel):
    schema_version: str = "5.1-historical-data-validation-report"
    validation_report_id: str = Field(..., min_length=1)
    ingestion_batch_id: str = Field(..., min_length=1)
    strategy_track: StrategyTrack
    market_profile_id: str = Field(..., min_length=1)
    validation_status: HistoricalValidationStatus
    error_count: int = Field(..., ge=0)
    warning_count: int = Field(..., ge=0)
    validation_issues: list[dict] = Field(default_factory=list)
    report_only: bool = False
    read_only: bool = True
    non_executable: bool = True

    @field_validator("validation_report_id", "ingestion_batch_id", "market_profile_id", mode="before")
    @classmethod
    def normalize_upper_fields(cls, value, info):
        return _upper_required(value, info.field_name)

    @field_validator("schema_version")
    @classmethod
    def exact_schema(cls, value: str) -> str:
        if value != "5.1-historical-data-validation-report":
            raise ValueError("schema_version must be exactly 5.1-historical-data-validation-report")
        return value

    @model_validator(mode="after")
    def enforce_safe_flags(self):
        if not self.read_only:
            raise ValueError("validation report must remain read_only")
        if not self.non_executable:
            raise ValueError("validation report must remain non_executable")
        return self


class HistoricalDataGapReport(StrictModel):
    schema_version: str = "5.1-historical-data-gap-report"
    gap_report_id: str = Field(..., min_length=1)
    ingestion_batch_id: str = Field(..., min_length=1)
    gap_status: HistoricalGapStatus
    gap_categories: list[HistoricalGapCategory] = Field(default_factory=list)
    blocking_gap_count: int = Field(..., ge=0)
    report_only_gap_count: int = Field(..., ge=0)
    gaps: list[dict] = Field(default_factory=list)
    read_only: bool = True
    non_executable: bool = True

    @field_validator("gap_report_id", "ingestion_batch_id", mode="before")
    @classmethod
    def normalize_upper_fields(cls, value, info):
        return _upper_required(value, info.field_name)

    @field_validator("schema_version")
    @classmethod
    def exact_schema(cls, value: str) -> str:
        if value != "5.1-historical-data-gap-report":
            raise ValueError("schema_version must be exactly 5.1-historical-data-gap-report")
        return value

    @model_validator(mode="after")
    def enforce_safe_flags(self):
        if not self.read_only:
            raise ValueError("gap report must remain read_only")
        if not self.non_executable:
            raise ValueError("gap report must remain non_executable")
        return self


class HistoricalDataQualityReport(StrictModel):
    schema_version: str = "5.1-historical-data-quality-report"
    quality_report_id: str = Field(..., min_length=1)
    ingestion_batch_id: str = Field(..., min_length=1)
    record_count: int = Field(..., ge=0)
    symbol_count: int = Field(..., ge=0)
    market_count: int = Field(..., ge=0)
    date_range_start: datetime | None = None
    date_range_end: datetime | None = None
    timezone_distribution: dict = Field(default_factory=dict)
    currency_distribution: dict = Field(default_factory=dict)
    missing_value_count: int = Field(..., ge=0)
    duplicate_count: int = Field(..., ge=0)
    invalid_ohlc_count: int = Field(..., ge=0)
    invalid_volume_count: int = Field(..., ge=0)
    out_of_order_count: int = Field(..., ge=0)
    missing_session_count: int = Field(..., ge=0)
    stale_batch_marker: bool = False
    adjustment_policy_summary: dict = Field(default_factory=dict)
    quality_bucket: HistoricalQualityBucket
    report_only: bool = False
    read_only: bool = True
    non_executable: bool = True

    _date_range_start = field_validator("date_range_start")(aware_optional)
    _date_range_end = field_validator("date_range_end")(aware_optional)

    @field_validator("quality_report_id", "ingestion_batch_id", mode="before")
    @classmethod
    def normalize_upper_fields(cls, value, info):
        return _upper_required(value, info.field_name)

    @field_validator("schema_version")
    @classmethod
    def exact_schema(cls, value: str) -> str:
        if value != "5.1-historical-data-quality-report":
            raise ValueError("schema_version must be exactly 5.1-historical-data-quality-report")
        return value

    @model_validator(mode="after")
    def enforce_safe_flags(self):
        if not self.read_only:
            raise ValueError("quality report must remain read_only")
        if not self.non_executable:
            raise ValueError("quality report must remain non_executable")
        return self


class HistoricalMarketDataManifest(StrictModel):
    schema_version: str = "5.1-historical-market-data-manifest"
    manifest_id: str = Field(..., min_length=1)
    ingestion_batch_id: str = Field(..., min_length=1)
    source_descriptor_id: str = Field(..., min_length=1)
    source_file_path: str = Field(..., min_length=1)
    source_file_hash: str = Field(..., min_length=1)
    source_provenance: HistoricalDataProviderProvenance
    strategy_track: StrategyTrack
    market_profile_id: str = Field(..., min_length=1)
    symbol_count: int = Field(..., ge=0)
    record_count: int = Field(..., ge=0)
    date_range_start: datetime | None = None
    date_range_end: datetime | None = None
    timezone: str = Field(..., min_length=1)
    currency: str = Field(..., min_length=3)
    adjustment_policy: HistoricalDataAdjustmentPolicy
    validation_report_id: str = Field(..., min_length=1)
    quality_report_id: str = Field(..., min_length=1)
    gap_report_id: str = Field(..., min_length=1)
    audit_record_ids: list[str] = Field(default_factory=list)
    non_executable: bool = True
    read_only: bool = True
    no_network: bool = True
    no_provider_api: bool = True
    no_order: bool = True

    _date_range_start = field_validator("date_range_start")(aware_optional)
    _date_range_end = field_validator("date_range_end")(aware_optional)

    @field_validator(
        "manifest_id",
        "ingestion_batch_id",
        "source_descriptor_id",
        "source_file_hash",
        "market_profile_id",
        "currency",
        "validation_report_id",
        "quality_report_id",
        "gap_report_id",
        mode="before",
    )
    @classmethod
    def normalize_upper_fields(cls, value, info):
        return _upper_required(value, info.field_name)

    @field_validator("timezone", mode="before")
    @classmethod
    def strip_timezone(cls, value):
        return _strip_required(value, "timezone")

    @field_validator("source_file_path", mode="before")
    @classmethod
    def strip_source_file_path(cls, value: str) -> str:
        return _local_path_required(value, "source_file_path")

    @field_validator("audit_record_ids", mode="before")
    @classmethod
    def normalize_audit_record_ids(cls, values):
        cleaned = []
        for value in values:
            cleaned.append(_upper_required(value, "audit_record_ids"))
        return cleaned

    @field_validator("schema_version")
    @classmethod
    def exact_schema(cls, value: str) -> str:
        if value != "5.1-historical-market-data-manifest":
            raise ValueError("schema_version must be exactly 5.1-historical-market-data-manifest")
        return value

    @model_validator(mode="after")
    def enforce_safe_flags(self):
        if not self.read_only:
            raise ValueError("manifest must remain read_only")
        if not self.non_executable:
            raise ValueError("manifest must remain non_executable")
        if not self.no_network:
            raise ValueError("manifest must remain no_network")
        if not self.no_provider_api:
            raise ValueError("manifest must remain no_provider_api")
        if not self.no_order:
            raise ValueError("manifest must remain no_order")
        return self


class HistoricalMarketDataSnapshot(StrictModel):
    schema_version: str
    snapshot_id: str = Field(..., min_length=1)
    created_at: datetime
    ingestion_config: HistoricalDataIngestionConfig
    source_descriptor: HistoricalDataSourceDescriptor
    provider_provenance: HistoricalDataProviderProvenance
    adjustment_policy: HistoricalDataAdjustmentPolicy
    safety_boundary: HistoricalDataSafetyBoundary = Field(default_factory=HistoricalDataSafetyBoundary)
    records: list[HistoricalOHLCVRecord] = Field(default_factory=list)
    validation_report: HistoricalDataValidationReport
    gap_report: HistoricalDataGapReport
    quality_report: HistoricalDataQualityReport
    manifest: HistoricalMarketDataManifest
    audit_records: list[HistoricalDataAuditRecord] = Field(default_factory=list)

    _created = field_validator("created_at")(aware)

    @field_validator("schema_version")
    @classmethod
    def exact_schema(cls, value: str) -> str:
        if value != "5.1-historical-market-data-snapshot":
            raise ValueError("schema_version must be exactly 5.1-historical-market-data-snapshot")
        return value

    @field_validator("snapshot_id")
    @classmethod
    def strip_snapshot_id(cls, value: str) -> str:
        return _strip(value)

    @model_validator(mode="after")
    def validate_snapshot_consistency(self):
        batch_ids = [self.validation_report.ingestion_batch_id]
        batch_ids.append(self.gap_report.ingestion_batch_id)
        batch_ids.append(self.quality_report.ingestion_batch_id)
        batch_ids.append(self.manifest.ingestion_batch_id)
        batch_ids.extend(record.ingestion_batch_id for record in self.records)
        batch_ids.extend(audit_record.ingestion_batch_id for audit_record in self.audit_records)
        expected_ingestion_batch_id = Counter(batch_ids).most_common(1)[0][0]
        if self.ingestion_config.source_type != self.source_descriptor.source_type:
            raise ValueError("ingestion_config.source_type must match source_descriptor.source_type")
        if self.ingestion_config.strategy_track != self.source_descriptor.strategy_track:
            raise ValueError("strategy_track must match between ingestion_config and source_descriptor")
        if self.ingestion_config.market_profile.market_id != self.source_descriptor.market_profile_id:
            raise ValueError("market_profile_id must match the ingestion_config market profile")
        if self.ingestion_config.market_profile.base_currency != self.source_descriptor.currency:
            raise ValueError("source descriptor currency must match market profile base currency")
        if self.validation_report.strategy_track != self.ingestion_config.strategy_track:
            raise ValueError("validation_report strategy_track must match ingestion_config strategy_track")
        if self.validation_report.market_profile_id != self.source_descriptor.market_profile_id:
            raise ValueError("validation_report market_profile_id must match source_descriptor market_profile_id")
        if self.manifest.strategy_track != self.ingestion_config.strategy_track:
            raise ValueError("manifest strategy_track must match ingestion_config strategy_track")
        if self.manifest.market_profile_id != self.source_descriptor.market_profile_id:
            raise ValueError("manifest market_profile_id must match source_descriptor market_profile_id")
        if self.validation_report.ingestion_batch_id != expected_ingestion_batch_id:
            raise ValueError("validation_report ingestion_batch_id must match snapshot ingestion_batch_id")
        if self.gap_report.ingestion_batch_id != expected_ingestion_batch_id:
            raise ValueError("gap_report ingestion_batch_id must match snapshot ingestion_batch_id")
        if self.quality_report.ingestion_batch_id != expected_ingestion_batch_id:
            raise ValueError("quality_report ingestion_batch_id must match snapshot ingestion_batch_id")
        if self.manifest.ingestion_batch_id != expected_ingestion_batch_id:
            raise ValueError("manifest ingestion_batch_id must match snapshot ingestion_batch_id")
        if self.manifest.validation_report_id != self.validation_report.validation_report_id:
            raise ValueError("manifest validation_report_id must match embedded validation_report")
        if self.manifest.quality_report_id != self.quality_report.quality_report_id:
            raise ValueError("manifest quality_report_id must match embedded quality_report")
        if self.manifest.gap_report_id != self.gap_report.gap_report_id:
            raise ValueError("manifest gap_report_id must match embedded gap_report")
        embedded_audit_record_ids = [audit_record.audit_record_id for audit_record in self.audit_records]
        if self.manifest.audit_record_ids != embedded_audit_record_ids:
            raise ValueError("manifest audit_record_ids must match embedded audit_records")
        if self.manifest.source_file_path != self.source_descriptor.local_file_path:
            raise ValueError("manifest source_file_path must match source_descriptor local_file_path")
        for record in self.records:
            if record.market != self.source_descriptor.market_profile_id:
                raise ValueError("record market must match source_descriptor market_profile_id")
            if record.currency != self.source_descriptor.currency:
                raise ValueError("record currency must match source_descriptor currency")
            if record.ingestion_batch_id != expected_ingestion_batch_id:
                raise ValueError("record ingestion_batch_id must match snapshot ingestion_batch_id")
        for audit_record in self.audit_records:
            if audit_record.ingestion_batch_id != expected_ingestion_batch_id:
                raise ValueError("audit record ingestion_batch_id must match snapshot ingestion_batch_id")
            if audit_record.source_descriptor_id != self.source_descriptor.source_descriptor_id:
                raise ValueError("audit record source_descriptor_id must match source_descriptor source_descriptor_id")
            if audit_record.local_file_path != self.source_descriptor.local_file_path:
                raise ValueError("audit record local_file_path must match source_descriptor local_file_path")
        return self
