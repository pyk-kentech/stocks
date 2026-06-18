from __future__ import annotations

from datetime import date

from pydantic import Field, field_validator, model_validator

from stock_risk_mcp.models import StrictModel
from stock_risk_mcp.strategy_track_models import StrategyTrack


def _strip(value: str) -> str:
    return value.strip()


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


def _normalize_warning_list(value, field_name: str) -> list[str]:
    if value is None:
        return []
    if isinstance(value, (str, bytes)) or not isinstance(value, list):
        raise ValueError(f"{field_name} must be a list")
    return [_string_required(item, field_name) for item in value]


class HistoricalScannerReplayCandidateSeed(StrictModel):
    seed_id: str = Field(..., min_length=1)
    symbol: str = Field(..., min_length=1)
    market: str = Field(..., min_length=1)
    session_date: date
    reason_code: str = Field(..., min_length=1)
    source_event_id: str | None = None
    replay_event_stream_id: str | None = None
    source_window_id: str | None = None
    scanner_context_id: str | None = None
    event_source_ids: list[str] = Field(default_factory=list)
    source_manifest_ids: list[str] = Field(default_factory=list)
    source_audit_record_ids: list[str] = Field(default_factory=list)
    provider_provenance_ids: list[str] = Field(default_factory=list)
    is_order_candidate: bool = False
    report_only: bool = True
    read_only: bool = True
    non_executable: bool = True
    local_file_only: bool = True
    no_network: bool = True
    no_provider_api: bool = True
    no_order: bool = True
    no_llm_runtime: bool = True
    no_ml_training: bool = True

    @model_validator(mode="before")
    @classmethod
    def reject_null_required_text_fields(cls, data):
        if isinstance(data, dict):
            for field_name in ("seed_id", "symbol", "market", "reason_code"):
                if data.get(field_name) is None:
                    raise ValueError(f"{field_name} must not be null")
        return data

    @field_validator(
        "seed_id",
        "symbol",
        "market",
        "reason_code",
        "source_event_id",
        "replay_event_stream_id",
        "source_window_id",
        "scanner_context_id",
        mode="before",
    )
    @classmethod
    def normalize_seed_fields(cls, value, info):
        if value is None:
            return None
        return _upper_required(value, info.field_name)

    @field_validator(
        "event_source_ids",
        "source_manifest_ids",
        "source_audit_record_ids",
        "provider_provenance_ids",
        mode="before",
    )
    @classmethod
    def normalize_seed_lineage_ids(cls, values, info):
        return _normalize_id_list(values, info.field_name)

    @model_validator(mode="after")
    def enforce_safe_mode(self):
        if self.is_order_candidate:
            raise ValueError("historical scanner replay candidate seed must remain non-order-candidate")
        if not self.report_only:
            raise ValueError("historical scanner replay candidate seed must remain report_only")
        if not self.read_only:
            raise ValueError("historical scanner replay candidate seed must remain read_only")
        if not self.non_executable:
            raise ValueError("historical scanner replay candidate seed must remain non_executable")
        if not self.local_file_only:
            raise ValueError("historical scanner replay candidate seed must remain local_file_only")
        if not self.no_network:
            raise ValueError("historical scanner replay candidate seed must remain no_network")
        if not self.no_provider_api:
            raise ValueError("historical scanner replay candidate seed must remain no_provider_api")
        if not self.no_order:
            raise ValueError("historical scanner replay candidate seed must remain no_order")
        if not self.no_llm_runtime:
            raise ValueError("historical scanner replay candidate seed must remain no_llm_runtime")
        if not self.no_ml_training:
            raise ValueError("historical scanner replay candidate seed must remain no_ml_training")
        return self


class HistoricalScannerReplayContext(StrictModel):
    context_id: str = Field(..., min_length=1)
    strategy_track: StrategyTrack
    market_profile_id: str = Field(..., min_length=1)
    historical_market_snapshot_id: str = Field(..., min_length=1)
    historical_calendar_snapshot_id: str | None = None
    replay_event_stream_id: str | None = None
    source_window_bundle_id: str | None = None
    scanner_window_ids: list[str] = Field(default_factory=list)
    symbol: str | None = None
    market: str | None = None
    early_close: bool = False
    holiday_session_gap: bool = False
    attached_market_event_count: int = Field(default=0, ge=0)
    attached_corporate_event_count: int = Field(default=0, ge=0)
    attached_event_context_summary: str | None = None
    event_source_ids: list[str] = Field(default_factory=list)
    validation_gap_categories: list[str] = Field(default_factory=list)
    lineage_complete: bool = False
    report_only: bool = True
    read_only: bool = True
    non_executable: bool = True
    local_file_only: bool = True
    no_network: bool = True
    no_provider_api: bool = True
    no_order: bool = True
    no_llm_runtime: bool = True
    no_ml_training: bool = True
    source_manifest_ids: list[str] = Field(default_factory=list)
    source_audit_record_ids: list[str] = Field(default_factory=list)
    provider_provenance_ids: list[str] = Field(default_factory=list)

    @field_validator(
        "context_id",
        "market_profile_id",
        "historical_market_snapshot_id",
        "historical_calendar_snapshot_id",
        "replay_event_stream_id",
        "source_window_bundle_id",
        "symbol",
        "market",
        mode="before",
    )
    @classmethod
    def normalize_context_fields(cls, value, info):
        if value is None:
            return None
        return _upper_required(value, info.field_name)

    @field_validator("attached_event_context_summary", mode="before")
    @classmethod
    def normalize_context_summary(cls, value):
        if value is None:
            return None
        return _string_required(value, "attached_event_context_summary")

    @field_validator(
        "scanner_window_ids",
        "event_source_ids",
        "validation_gap_categories",
        "source_manifest_ids",
        "source_audit_record_ids",
        "provider_provenance_ids",
        mode="before",
    )
    @classmethod
    def normalize_context_lists(cls, values, info):
        return _normalize_id_list(values, info.field_name)

    @model_validator(mode="after")
    def enforce_safe_mode(self):
        if not self.report_only:
            raise ValueError("historical scanner replay context must remain report_only")
        if not self.read_only:
            raise ValueError("historical scanner replay context must remain read_only")
        if not self.non_executable:
            raise ValueError("historical scanner replay context must remain non_executable")
        if not self.local_file_only:
            raise ValueError("historical scanner replay context must remain local_file_only")
        if not self.no_network:
            raise ValueError("historical scanner replay context must remain no_network")
        if not self.no_provider_api:
            raise ValueError("historical scanner replay context must remain no_provider_api")
        if not self.no_order:
            raise ValueError("historical scanner replay context must remain no_order")
        if not self.no_llm_runtime:
            raise ValueError("historical scanner replay context must remain no_llm_runtime")
        if not self.no_ml_training:
            raise ValueError("historical scanner replay context must remain no_ml_training")
        return self


class HistoricalScannerReplayGapEntry(StrictModel):
    gap_id: str = Field(..., min_length=1)
    gap_category: str | None = None
    severity: str = Field(..., min_length=1)
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


class HistoricalScannerReplayInput(StrictModel):
    schema_version: str = "5.2-historical-scanner-replay-input"
    replay_input_id: str = Field(..., min_length=1)
    strategy_track: StrategyTrack
    replay_context: HistoricalScannerReplayContext
    replay_event_stream_id: str | None = None
    source_window_bundle_id: str | None = None
    historical_market_snapshot_id: str = Field(..., min_length=1)
    historical_calendar_snapshot_id: str | None = None
    scanner_window_ids: list[str] = Field(default_factory=list)
    event_source_ids: list[str] = Field(default_factory=list)
    source_manifest_ids: list[str] = Field(default_factory=list)
    source_audit_record_ids: list[str] = Field(default_factory=list)
    provider_provenance_ids: list[str] = Field(default_factory=list)
    candidate_seeds: list[HistoricalScannerReplayCandidateSeed] = Field(default_factory=list)
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
        "replay_input_id",
        "replay_event_stream_id",
        "source_window_bundle_id",
        "historical_market_snapshot_id",
        "historical_calendar_snapshot_id",
        mode="before",
    )
    @classmethod
    def normalize_input_fields(cls, value, info):
        if value is None:
            return None
        return _upper_required(value, info.field_name)

    @field_validator(
        "scanner_window_ids",
        "event_source_ids",
        "source_manifest_ids",
        "source_audit_record_ids",
        "provider_provenance_ids",
        mode="before",
    )
    @classmethod
    def normalize_input_lists(cls, values, info):
        return _normalize_id_list(values, info.field_name if info.field_name != "source_manifest_ids" else "bundle_lineage_ids")

    @model_validator(mode="after")
    def enforce_safe_mode(self):
        if not self.report_only:
            raise ValueError("historical scanner replay input must remain report_only")
        if not self.read_only:
            raise ValueError("historical scanner replay input must remain read_only")
        if not self.non_executable:
            raise ValueError("historical scanner replay input must remain non_executable")
        if not self.local_file_only:
            raise ValueError("historical scanner replay input must remain local_file_only")
        if not self.no_network:
            raise ValueError("historical scanner replay input must remain no_network")
        if not self.no_provider_api:
            raise ValueError("historical scanner replay input must remain no_provider_api")
        if not self.no_order:
            raise ValueError("historical scanner replay input must remain no_order")
        if not self.no_llm_runtime:
            raise ValueError("historical scanner replay input must remain no_llm_runtime")
        if not self.no_ml_training:
            raise ValueError("historical scanner replay input must remain no_ml_training")
        if self.strategy_track != self.replay_context.strategy_track:
            raise ValueError("historical scanner replay input strategy_track must match replay_context strategy_track")
        if self.historical_market_snapshot_id != self.replay_context.historical_market_snapshot_id:
            raise ValueError(
                "historical scanner replay input historical_market_snapshot_id must match replay_context historical_market_snapshot_id"
            )
        if self.historical_calendar_snapshot_id != self.replay_context.historical_calendar_snapshot_id:
            raise ValueError(
                "historical scanner replay input historical_calendar_snapshot_id must match replay_context historical_calendar_snapshot_id"
            )
        return self


class HistoricalScannerReplayGapReport(StrictModel):
    schema_version: str = "5.2-historical-scanner-replay-gap-report"
    gap_report_id: str = Field(..., min_length=1)
    replay_input_id: str = Field(..., min_length=1)
    historical_calendar_snapshot_id: str | None = None
    gap_categories: list[str] = Field(default_factory=list)
    source_manifest_ids: list[str] = Field(default_factory=list)
    source_audit_record_ids: list[str] = Field(default_factory=list)
    provider_provenance_ids: list[str] = Field(default_factory=list)
    blocking_gap_count: int = Field(default=0, ge=0)
    report_only_gap_count: int = Field(default=0, ge=0)
    gaps: list[HistoricalScannerReplayGapEntry] = Field(default_factory=list)
    report_only: bool = True
    read_only: bool = True
    non_executable: bool = True
    local_file_only: bool = True
    no_network: bool = True
    no_provider_api: bool = True
    no_order: bool = True
    no_llm_runtime: bool = True
    no_ml_training: bool = True

    @field_validator("gap_report_id", "replay_input_id", "historical_calendar_snapshot_id", mode="before")
    @classmethod
    def normalize_gap_report_fields(cls, value, info):
        if value is None:
            return None
        return _upper_required(value, info.field_name)

    @field_validator(
        "gap_categories",
        "source_manifest_ids",
        "source_audit_record_ids",
        "provider_provenance_ids",
        mode="before",
    )
    @classmethod
    def normalize_gap_lists(cls, values, info):
        field_name = "gap_lineage_ids" if info.field_name == "source_manifest_ids" else info.field_name
        return _normalize_id_list(values, field_name)

    @model_validator(mode="after")
    def enforce_safe_mode(self):
        if not self.report_only:
            raise ValueError("historical scanner replay gap report must remain report_only")
        if not self.read_only:
            raise ValueError("historical scanner replay gap report must remain read_only")
        if not self.non_executable:
            raise ValueError("historical scanner replay gap report must remain non_executable")
        if not self.local_file_only:
            raise ValueError("historical scanner replay gap report must remain local_file_only")
        if not self.no_network:
            raise ValueError("historical scanner replay gap report must remain no_network")
        if not self.no_provider_api:
            raise ValueError("historical scanner replay gap report must remain no_provider_api")
        if not self.no_order:
            raise ValueError("historical scanner replay gap report must remain no_order")
        if not self.no_llm_runtime:
            raise ValueError("historical scanner replay gap report must remain no_llm_runtime")
        if not self.no_ml_training:
            raise ValueError("historical scanner replay gap report must remain no_ml_training")
        return self


class HistoricalScannerReplayReport(StrictModel):
    schema_version: str = "5.2-historical-scanner-replay-report"
    report_id: str = Field(..., min_length=1)
    replay_input_id: str = Field(..., min_length=1)
    strategy_track: StrategyTrack
    historical_calendar_snapshot_id: str | None = None
    source_manifest_ids: list[str] = Field(default_factory=list)
    source_audit_record_ids: list[str] = Field(default_factory=list)
    provider_provenance_ids: list[str] = Field(default_factory=list)
    candidate_seed_count: int = Field(default=0, ge=0)
    scanner_window_count: int = Field(default=0, ge=0)
    warnings: list[str] = Field(default_factory=list)
    report_only: bool = True
    read_only: bool = True
    non_executable: bool = True
    local_file_only: bool = True
    no_network: bool = True
    no_provider_api: bool = True
    no_order: bool = True
    no_llm_runtime: bool = True
    no_ml_training: bool = True

    @field_validator("report_id", "replay_input_id", "historical_calendar_snapshot_id", mode="before")
    @classmethod
    def normalize_report_fields(cls, value, info):
        if value is None:
            return None
        return _upper_required(value, info.field_name)

    @field_validator(
        "source_manifest_ids",
        "source_audit_record_ids",
        "provider_provenance_ids",
        mode="before",
    )
    @classmethod
    def normalize_report_lineage_ids(cls, values, info):
        return _normalize_id_list(values, "scanner_report_lineage_ids" if info.field_name == "source_manifest_ids" else info.field_name)

    @field_validator("warnings", mode="before")
    @classmethod
    def normalize_warnings(cls, values):
        return _normalize_warning_list(values, "warnings")

    @model_validator(mode="after")
    def enforce_safe_mode(self):
        if not self.report_only:
            raise ValueError("historical scanner replay report must remain report_only")
        if not self.read_only:
            raise ValueError("historical scanner replay report must remain read_only")
        if not self.non_executable:
            raise ValueError("historical scanner replay report must remain non_executable")
        if not self.local_file_only:
            raise ValueError("historical scanner replay report must remain local_file_only")
        if not self.no_network:
            raise ValueError("historical scanner replay report must remain no_network")
        if not self.no_provider_api:
            raise ValueError("historical scanner replay report must remain no_provider_api")
        if not self.no_order:
            raise ValueError("historical scanner replay report must remain no_order")
        if not self.no_llm_runtime:
            raise ValueError("historical scanner replay report must remain no_llm_runtime")
        if not self.no_ml_training:
            raise ValueError("historical scanner replay report must remain no_ml_training")
        return self
