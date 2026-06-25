from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from pydantic import Field, field_validator, model_validator

from stock_risk_mcp.kiwoom_readonly_snapshot_models import KiwoomReadonlyDomesticStockSnapshotReport
from stock_risk_mcp.kiwoom_rest_readonly_chart_models import CanonicalOHLCVRecord
from stock_risk_mcp.kiwoom_rest_readonly_flow_models import CanonicalInvestorFlowSignal, CanonicalProgramTradingSignal
from stock_risk_mcp.kiwoom_rest_readonly_quote_models import (
    CanonicalBasicInstrumentInfo,
    CanonicalLiquidityHint,
    CanonicalOrderbookRecord,
    CanonicalQuoteRecord,
)
from stock_risk_mcp.kiwoom_rest_readonly_rank_models import CanonicalOutlierMomentumSignal, CanonicalRankSignal
from stock_risk_mcp.kiwoom_rest_readonly_sector_models import (
    CanonicalEtfTrendSignal,
    CanonicalThemeLeadershipSignal,
    CanonicalThemeMembershipSignal,
)
from stock_risk_mcp.models import StrictModel


def _aware(value: datetime | str | None) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        parsed = value
    else:
        text = str(value).strip()
        if len(text) == 8 and text.isdigit():
            parsed = datetime.fromisoformat(f"{text[:4]}-{text[4:6]}-{text[6:8]}T15:30:00+09:00")
        elif len(text) == 14 and text.isdigit():
            parsed = datetime.fromisoformat(
                f"{text[:4]}-{text[4:6]}-{text[6:8]}T{text[8:10]}:{text[10:12]}:{text[12:14]}+09:00"
            )
        else:
            parsed = datetime.fromisoformat(text)
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError("timestamp must include timezone")
    return parsed


def _string_required(value, field_name: str) -> str:
    if value is None:
        raise ValueError(f"{field_name} must not be null")
    cleaned = str(value).strip()
    if not cleaned:
        raise ValueError(f"{field_name} must not be blank")
    return cleaned


def _upper_required(value, field_name: str) -> str:
    return _string_required(value, field_name).upper()


def _validate_local_path(value: str, field_name: str) -> str:
    cleaned = _string_required(value, field_name)
    lowered = cleaned.lower()
    if "://" in lowered or lowered.startswith("//"):
        raise ValueError(f"{field_name} must be a local file path")
    if lowered.endswith(".parquet"):
        raise ValueError("parquet remains unsupported")
    return cleaned


def _normalize_list(value, field_name: str, *, upper: bool = True) -> list[str]:
    if value is None:
        return []
    if isinstance(value, (str, bytes)) or not isinstance(value, list):
        raise ValueError(f"{field_name} must be a list")
    if upper:
        return [_upper_required(item, field_name) for item in value]
    return [_string_required(item, field_name) for item in value]


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
        "no_account_mutation",
        "no_live_prod",
        "no_autonomous_trading",
        "no_broker_api",
        "no_kiwoom_api",
        "no_ls_api",
        "no_websocket",
        "no_cloud_llm",
        "no_local_llm_runtime",
        "no_env_read",
        "no_credential_read",
        "no_token_loading",
        "no_auth_header_generation",
    ):
        if not getattr(model, flag_name):
            raise ValueError(f"{context} must remain {flag_name}")
    return model


class KiwoomManualResponseImportReadiness(StrEnum):
    IMPORT_READY = "IMPORT_READY"
    PARSED_CANONICAL_READY = "PARSED_CANONICAL_READY"
    SNAPSHOT_COMPOSED = "SNAPSHOT_COMPOSED"
    READONLY_SCHEMA_GAP = "READONLY_SCHEMA_GAP"
    CAPABILITY_ONLY = "CAPABILITY_ONLY"
    DATA_GAP = "DATA_GAP"
    SCHEMA_GAP = "SCHEMA_GAP"
    BLOCKED_SENSITIVE_CONTENT = "BLOCKED_SENSITIVE_CONTENT"
    BLOCKED_ACCOUNT_API = "BLOCKED_ACCOUNT_API"
    BLOCKED_ORDER_API = "BLOCKED_ORDER_API"
    BLOCKED_NETWORK_PATH = "BLOCKED_NETWORK_PATH"
    BLOCKED_CREDENTIAL_PATH = "BLOCKED_CREDENTIAL_PATH"
    BLOCKED_UNSUPPORTED_FORMAT = "BLOCKED_UNSUPPORTED_FORMAT"
    REJECTED = "REJECTED"


class KiwoomManualResponseApiClassification(StrEnum):
    READONLY_IMPLEMENTED = "READONLY_IMPLEMENTED"
    READONLY_SCHEMA_GAP = "READONLY_SCHEMA_GAP"
    READONLY_CAPABILITY_ONLY = "READONLY_CAPABILITY_ONLY"
    ACCOUNT_BLOCKED = "ACCOUNT_BLOCKED"
    ORDER_BLOCKED = "ORDER_BLOCKED"
    UNKNOWN_BLOCKED = "UNKNOWN_BLOCKED"


class _BaseReport(StrictModel):
    read_only: bool = True
    report_only: bool = True
    non_executable: bool = True
    local_file_only: bool = True
    offline_only: bool = True
    no_network: bool = True
    no_provider_api: bool = True
    no_order: bool = True
    no_account_mutation: bool = True
    no_live_prod: bool = True
    no_autonomous_trading: bool = True
    no_broker_api: bool = True
    no_kiwoom_api: bool = True
    no_ls_api: bool = True
    no_websocket: bool = True
    no_cloud_llm: bool = True
    no_local_llm_runtime: bool = True
    no_env_read: bool = True
    no_credential_read: bool = True
    no_token_loading: bool = True
    no_auth_header_generation: bool = True


class KiwoomManualResponseImportFile(StrictModel):
    file_path: str = Field(..., min_length=1)
    declared_api_id: str = Field(..., min_length=1)
    provider_symbol: str | None = None
    canonical_instrument_key: str | None = None
    market: str = "KR"
    currency: str = "KRW"
    observed_at: datetime | None = None
    available_at: datetime | None = None
    source_ref: str | None = None

    @field_validator("file_path", mode="before")
    @classmethod
    def normalize_file_path(cls, value):
        return _string_required(value, "file_path")

    @field_validator("declared_api_id", "provider_symbol", "canonical_instrument_key", "market", "currency", mode="before")
    @classmethod
    def normalize_upper_fields(cls, value, info):
        if value in (None, "") and info.field_name in {"provider_symbol", "canonical_instrument_key"}:
            return None
        return _upper_required(value, info.field_name)

    @field_validator("observed_at", "available_at", mode="before")
    @classmethod
    def normalize_datetimes(cls, value):
        return _aware(value)

    @field_validator("source_ref", mode="before")
    @classmethod
    def normalize_source_ref(cls, value):
        if value in (None, ""):
            return None
        return _validate_local_path(value, "source_ref")


class KiwoomManualResponseImportRequest(_BaseReport):
    request_id: str = Field(..., min_length=1)
    files: list[KiwoomManualResponseImportFile] = Field(default_factory=list)
    compose_snapshot: bool = False
    strict_mode: bool = True

    @field_validator("request_id", mode="before")
    @classmethod
    def normalize_request_id(cls, value):
        return _upper_required(value, "request_id")

    @model_validator(mode="after")
    def validate_request(self):
        _validate_safety_flags(self, "manual response import request")
        if not self.files:
            raise ValueError("files must not be empty")
        return self


class KiwoomManualResponseFileClassification(StrictModel):
    file_path: str = Field(..., min_length=1)
    api_id: str = Field(..., min_length=1)
    classification: KiwoomManualResponseApiClassification
    blocked: bool = False
    parser_supported: bool = False

    @field_validator("file_path", mode="before")
    @classmethod
    def normalize_file_path(cls, value):
        return _string_required(value, "file_path")

    @field_validator("api_id", mode="before")
    @classmethod
    def normalize_api_id(cls, value):
        return _upper_required(value, "api_id")


class KiwoomManualResponseSensitiveScan(StrictModel):
    file_path: str = Field(..., min_length=1)
    blocked: bool = False
    sensitive_field_names: list[str] = Field(default_factory=list)
    redaction_applied: bool = True

    @field_validator("file_path", mode="before")
    @classmethod
    def normalize_file_path(cls, value):
        return _string_required(value, "file_path")

    @field_validator("sensitive_field_names", mode="before")
    @classmethod
    def normalize_sensitive_fields(cls, value):
        return _normalize_list(value, "sensitive_field_names")


class KiwoomManualResponseRoutingResult(StrictModel):
    file_path: str = Field(..., min_length=1)
    api_id: str = Field(..., min_length=1)
    route_target: str = Field(..., min_length=1)
    readiness: KiwoomManualResponseImportReadiness

    @field_validator("file_path", mode="before")
    @classmethod
    def normalize_file_path(cls, value):
        return _string_required(value, "file_path")

    @field_validator("api_id", "route_target", mode="before")
    @classmethod
    def normalize_fields(cls, value, info):
        return _upper_required(value, info.field_name)


class KiwoomManualResponseParserResult(StrictModel):
    file_path: str = Field(..., min_length=1)
    api_id: str = Field(..., min_length=1)
    readiness: KiwoomManualResponseImportReadiness
    canonical_record_count: int = Field(default=0, ge=0)
    canonical_output_kinds: list[str] = Field(default_factory=list)

    @field_validator("file_path", mode="before")
    @classmethod
    def normalize_file_path(cls, value):
        return _string_required(value, "file_path")

    @field_validator("api_id", mode="before")
    @classmethod
    def normalize_api_id(cls, value):
        return _upper_required(value, "api_id")

    @field_validator("canonical_output_kinds", mode="before")
    @classmethod
    def normalize_kinds(cls, value):
        return _normalize_list(value, "canonical_output_kinds")


class KiwoomManualResponseSnapshotCompositionResult(_BaseReport):
    report_id: str = Field(..., min_length=1)
    compose_requested: bool = False
    composed: bool = False
    readiness: KiwoomManualResponseImportReadiness
    snapshot_report: KiwoomReadonlyDomesticStockSnapshotReport | None = None

    @field_validator("report_id", mode="before")
    @classmethod
    def normalize_id(cls, value):
        return _upper_required(value, "report_id")

    @model_validator(mode="after")
    def validate_report(self):
        return _validate_safety_flags(self, "manual response snapshot composition result")


class KiwoomManualResponseSafetyReport(_BaseReport):
    safety_report_id: str = Field(..., min_length=1)
    blocked: bool = False
    findings: list[str] = Field(default_factory=list)

    @field_validator("safety_report_id", mode="before")
    @classmethod
    def normalize_id(cls, value):
        return _upper_required(value, "safety_report_id")

    @field_validator("findings", mode="before")
    @classmethod
    def normalize_findings(cls, value):
        return _normalize_list(value, "findings")

    @model_validator(mode="after")
    def validate_report(self):
        return _validate_safety_flags(self, "manual response safety report")


class KiwoomManualResponseGapEntry(StrictModel):
    gap_id: str = Field(..., min_length=1)
    gap_category: str = Field(..., min_length=1)
    severity: str = Field(..., min_length=1)
    message: str = Field(..., min_length=1)

    @field_validator("gap_id", "gap_category", "severity", mode="before")
    @classmethod
    def normalize_upper(cls, value, info):
        return _upper_required(value, info.field_name)

    @field_validator("message", mode="before")
    @classmethod
    def normalize_message(cls, value):
        return _string_required(value, "message")


class KiwoomManualResponseGapReport(_BaseReport):
    gap_report_id: str = Field(..., min_length=1)
    readiness: KiwoomManualResponseImportReadiness
    gap_entries: list[KiwoomManualResponseGapEntry] = Field(default_factory=list)

    @field_validator("gap_report_id", mode="before")
    @classmethod
    def normalize_id(cls, value):
        return _upper_required(value, "gap_report_id")

    @model_validator(mode="after")
    def validate_report(self):
        return _validate_safety_flags(self, "manual response gap report")


class KiwoomManualResponseAuditRecord(StrictModel):
    audit_record_id: str = Field(..., min_length=1)
    created_at: datetime
    source_path: str = Field(..., min_length=1)
    operator_context: str = Field(..., min_length=1)
    redaction_applied: bool = True
    contains_secret_material: bool = False
    contains_token_material: bool = False
    contains_account_material: bool = False
    sensitive_field_names: list[str] = Field(default_factory=list)

    @field_validator("audit_record_id", mode="before")
    @classmethod
    def normalize_id(cls, value):
        return _upper_required(value, "audit_record_id")

    @field_validator("created_at", mode="before")
    @classmethod
    def normalize_created_at(cls, value):
        parsed = _aware(value)
        if parsed is None:
            raise ValueError("created_at must not be null")
        return parsed

    @field_validator("source_path", mode="before")
    @classmethod
    def normalize_source_path(cls, value):
        return _string_required(value, "source_path")

    @field_validator("operator_context", mode="before")
    @classmethod
    def normalize_context(cls, value):
        return _string_required(value, "operator_context")

    @field_validator("sensitive_field_names", mode="before")
    @classmethod
    def normalize_sensitive_fields(cls, value):
        return _normalize_list(value, "sensitive_field_names")


class KiwoomManualResponseImportSummaryReport(_BaseReport):
    report_id: str = Field(..., min_length=1)
    readiness: KiwoomManualResponseImportReadiness
    imported_file_count: int = Field(default=0, ge=0)
    canonical_output_count: int = Field(default=0, ge=0)
    message: str = Field(..., min_length=1)

    @field_validator("report_id", mode="before")
    @classmethod
    def normalize_id(cls, value):
        return _upper_required(value, "report_id")

    @field_validator("message", mode="before")
    @classmethod
    def normalize_message(cls, value):
        return _string_required(value, "message")

    @model_validator(mode="after")
    def validate_report(self):
        return _validate_safety_flags(self, "manual response import summary report")


class KiwoomManualResponseFileClassificationReport(_BaseReport):
    report_id: str = Field(..., min_length=1)
    files: list[KiwoomManualResponseFileClassification] = Field(default_factory=list)

    @field_validator("report_id", mode="before")
    @classmethod
    def normalize_id(cls, value):
        return _upper_required(value, "report_id")

    @model_validator(mode="after")
    def validate_report(self):
        return _validate_safety_flags(self, "manual response file classification report")


class KiwoomManualResponseSensitiveScanReport(_BaseReport):
    report_id: str = Field(..., min_length=1)
    scans: list[KiwoomManualResponseSensitiveScan] = Field(default_factory=list)

    @field_validator("report_id", mode="before")
    @classmethod
    def normalize_id(cls, value):
        return _upper_required(value, "report_id")

    @model_validator(mode="after")
    def validate_report(self):
        return _validate_safety_flags(self, "manual response sensitive scan report")


class KiwoomManualResponseRoutingReport(_BaseReport):
    report_id: str = Field(..., min_length=1)
    routes: list[KiwoomManualResponseRoutingResult] = Field(default_factory=list)
    parser_results: list[KiwoomManualResponseParserResult] = Field(default_factory=list)

    @field_validator("report_id", mode="before")
    @classmethod
    def normalize_id(cls, value):
        return _upper_required(value, "report_id")

    @model_validator(mode="after")
    def validate_report(self):
        return _validate_safety_flags(self, "manual response routing report")


class KiwoomManualResponseCanonicalOutputReport(_BaseReport):
    report_id: str = Field(..., min_length=1)
    canonical_ohlcv_records: list[CanonicalOHLCVRecord] = Field(default_factory=list)
    canonical_rank_signals: list[CanonicalRankSignal] = Field(default_factory=list)
    canonical_outlier_signals: list[CanonicalOutlierMomentumSignal] = Field(default_factory=list)
    canonical_quote_records: list[CanonicalQuoteRecord] = Field(default_factory=list)
    canonical_orderbook_records: list[CanonicalOrderbookRecord] = Field(default_factory=list)
    canonical_liquidity_hints: list[CanonicalLiquidityHint] = Field(default_factory=list)
    canonical_basic_info_records: list[CanonicalBasicInstrumentInfo] = Field(default_factory=list)
    canonical_investor_flow_signals: list[CanonicalInvestorFlowSignal] = Field(default_factory=list)
    canonical_program_flow_signals: list[CanonicalProgramTradingSignal] = Field(default_factory=list)
    canonical_theme_leadership_signals: list[CanonicalThemeLeadershipSignal] = Field(default_factory=list)
    canonical_theme_membership_signals: list[CanonicalThemeMembershipSignal] = Field(default_factory=list)
    canonical_etf_trend_signals: list[CanonicalEtfTrendSignal] = Field(default_factory=list)

    @field_validator("report_id", mode="before")
    @classmethod
    def normalize_id(cls, value):
        return _upper_required(value, "report_id")

    @model_validator(mode="after")
    def validate_report(self):
        return _validate_safety_flags(self, "manual response canonical output report")


class KiwoomManualResponseImportResult(_BaseReport):
    adapter_result_id: str = Field(..., min_length=1)
    summary_report: KiwoomManualResponseImportSummaryReport
    file_classification_report: KiwoomManualResponseFileClassificationReport
    sensitive_scan_report: KiwoomManualResponseSensitiveScanReport
    routing_report: KiwoomManualResponseRoutingReport
    canonical_output_report: KiwoomManualResponseCanonicalOutputReport
    snapshot_composition_result: KiwoomManualResponseSnapshotCompositionResult
    safety_report: KiwoomManualResponseSafetyReport
    gap_report: KiwoomManualResponseGapReport
    audit_records: list[KiwoomManualResponseAuditRecord] = Field(default_factory=list)

    @field_validator("adapter_result_id", mode="before")
    @classmethod
    def normalize_id(cls, value):
        return _upper_required(value, "adapter_result_id")

    @model_validator(mode="after")
    def validate_report(self):
        return _validate_safety_flags(self, "manual response import result")
