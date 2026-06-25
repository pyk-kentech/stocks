from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from pydantic import Field, field_validator, model_validator

from stock_risk_mcp.kiwoom_rest_readonly_chart_models import CanonicalOHLCVRecord, KiwoomRestChartAuditRecord
from stock_risk_mcp.kiwoom_rest_readonly_flow_models import (
    CanonicalInvestorFlowSignal,
    CanonicalProgramTradingSignal,
)
from stock_risk_mcp.kiwoom_rest_readonly_quote_models import (
    CanonicalBasicInstrumentInfo,
    CanonicalLiquidityHint,
    CanonicalOrderbookRecord,
    CanonicalQuoteRecord,
)
from stock_risk_mcp.kiwoom_rest_readonly_rank_models import CanonicalOutlierMomentumSignal, CanonicalRankSignal
from stock_risk_mcp.kiwoom_rest_readonly_sector_models import (
    CanonicalEtfTrendSignal,
    CanonicalSectorCapabilitySignal,
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


def _normalize_optional_number(value, field_name: str) -> float | None:
    if value in (None, ""):
        return None
    text = str(value).strip().replace(",", "")
    if not text:
        return None
    sign = -1 if text.startswith("-") else 1
    text = text.lstrip("+-")
    if not text or not any(ch.isdigit() for ch in text):
        raise ValueError(f"{field_name} must be numeric")
    return sign * float(text)


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


class KiwoomReadonlySnapshotReadiness(StrEnum):
    SNAPSHOT_READY = "SNAPSHOT_READY"
    PARTIAL = "PARTIAL"
    STALE = "STALE"
    CONFLICT = "CONFLICT"
    DATA_GAP = "DATA_GAP"
    BLOCKED = "BLOCKED"
    REJECTED = "REJECTED"


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


class KiwoomReadonlySnapshotSafetyReport(_BaseReport):
    safety_report_id: str = Field(..., min_length=1)

    @field_validator("safety_report_id", mode="before")
    @classmethod
    def normalize_id(cls, value):
        return _upper_required(value, "safety_report_id")

    @model_validator(mode="after")
    def validate_report(self):
        return _validate_safety_flags(self, "snapshot safety report")


class KiwoomReadonlySnapshotAuditRecord(KiwoomRestChartAuditRecord):
    pass


class KiwoomReadonlySnapshotConfig(_BaseReport):
    config_id: str = Field(..., min_length=1)
    available_at: datetime | None = None
    source_ref: str = Field(..., min_length=1)
    operator_context: str = Field(..., min_length=1)
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
    canonical_sector_capability_signals: list[CanonicalSectorCapabilitySignal] = Field(default_factory=list)
    safety_report: KiwoomReadonlySnapshotSafetyReport
    audit_records: list[KiwoomReadonlySnapshotAuditRecord] = Field(default_factory=list)

    @field_validator("config_id", mode="before")
    @classmethod
    def normalize_config_id(cls, value):
        return _upper_required(value, "config_id")

    @field_validator("available_at", mode="before")
    @classmethod
    def normalize_available_at(cls, value):
        return _aware(value)

    @field_validator("source_ref", mode="before")
    @classmethod
    def normalize_source_ref(cls, value):
        return _validate_local_path(value, "source_ref")

    @field_validator("operator_context", mode="before")
    @classmethod
    def normalize_context(cls, value):
        return _string_required(value, "operator_context")

    @model_validator(mode="after")
    def validate_report(self):
        return _validate_safety_flags(self, "snapshot config")


class CanonicalDomesticStockSnapshot(_BaseReport):
    provider: str = "KIWOOM_REST"
    canonical_instrument_key: str = Field(..., min_length=1)
    provider_symbol: str = Field(..., min_length=1)
    stock_name: str | None = None
    market: str = "KR"
    currency: str = "KRW"
    available_at: datetime | None = None
    quote_observed_at: datetime | None = None
    last_daily_bar_at: datetime | None = None
    reference_price: float | None = None
    latest_close_price: float | None = None
    percent_change: float | None = None
    price_change: float | None = None
    spread: float | None = None
    mid_price: float | None = None
    last_trade_quantity: float | None = None
    top_of_book_imbalance: float | None = None
    latest_volume: float | None = None
    liquidity_ready: bool = False
    rank_types: list[str] = Field(default_factory=list)
    best_rank: int | None = None
    outlier_categories: list[str] = Field(default_factory=list)
    investor_net_buy_amount: float | None = None
    investor_net_buy_quantity: float | None = None
    program_net_amount: float | None = None
    listed_shares: float | None = None
    market_cap: float | None = None
    market_cap_weight: float | None = None
    theme_names: list[str] = Field(default_factory=list)
    leading_theme_names: list[str] = Field(default_factory=list)
    theme_membership_count: int = Field(default=0, ge=0)
    related_etf_codes: list[str] = Field(default_factory=list)
    source_coverage_ratio: float = Field(default=0, ge=0, le=1)
    quality_flags: list[str] = Field(default_factory=list)
    stale_flag: bool = False
    conflict_flag: bool = False
    gap_reason: str | None = None

    @field_validator(
        "canonical_instrument_key",
        "provider_symbol",
        "gap_reason",
        mode="before",
    )
    @classmethod
    def normalize_upper_fields(cls, value, info):
        if value is None and info.field_name == "gap_reason":
            return None
        return _upper_required(value, info.field_name)

    @field_validator("stock_name", mode="before")
    @classmethod
    def normalize_optional_text(cls, value):
        if value in (None, ""):
            return None
        return _string_required(value, "stock_name")

    @field_validator("available_at", "quote_observed_at", "last_daily_bar_at", mode="before")
    @classmethod
    def normalize_datetimes(cls, value):
        return _aware(value)

    @field_validator("rank_types", "outlier_categories", "quality_flags", mode="before")
    @classmethod
    def normalize_upper_lists(cls, value, info):
        return _normalize_list(value, info.field_name)

    @field_validator("theme_names", "leading_theme_names", mode="before")
    @classmethod
    def normalize_text_lists(cls, value, info):
        return _normalize_list(value, info.field_name, upper=False)

    @field_validator("related_etf_codes", mode="before")
    @classmethod
    def normalize_etf_codes(cls, value):
        return _normalize_list(value, "related_etf_codes")

    @field_validator(
        "reference_price",
        "latest_close_price",
        "percent_change",
        "price_change",
        "spread",
        "mid_price",
        "last_trade_quantity",
        "top_of_book_imbalance",
        "latest_volume",
        "investor_net_buy_amount",
        "investor_net_buy_quantity",
        "program_net_amount",
        "listed_shares",
        "market_cap",
        "market_cap_weight",
        "source_coverage_ratio",
        mode="before",
    )
    @classmethod
    def normalize_numbers(cls, value, info):
        return _normalize_optional_number(value, info.field_name)

    @model_validator(mode="after")
    def validate_report(self):
        return _validate_safety_flags(self, "canonical domestic stock snapshot")


class KiwoomReadonlySnapshotSummaryReport(_BaseReport):
    report_id: str = Field(..., min_length=1)
    readiness: KiwoomReadonlySnapshotReadiness
    snapshot_count: int = Field(default=0, ge=0)
    covered_source_count: int = Field(default=0, ge=0)
    total_source_count: int = Field(default=0, ge=0)
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
        return _validate_safety_flags(self, "snapshot summary report")


class KiwoomReadonlySnapshotSourceCoverageEntry(StrictModel):
    source_name: str = Field(..., min_length=1)
    present: bool = False
    record_count: int = Field(default=0, ge=0)

    @field_validator("source_name", mode="before")
    @classmethod
    def normalize_source_name(cls, value):
        return _upper_required(value, "source_name")


class KiwoomReadonlySnapshotSourceCoverageReport(_BaseReport):
    report_id: str = Field(..., min_length=1)
    entries: list[KiwoomReadonlySnapshotSourceCoverageEntry] = Field(default_factory=list)
    coverage_ratio: float = Field(default=0, ge=0, le=1)

    @field_validator("report_id", mode="before")
    @classmethod
    def normalize_id(cls, value):
        return _upper_required(value, "report_id")

    @field_validator("coverage_ratio", mode="before")
    @classmethod
    def normalize_ratio(cls, value):
        normalized = _normalize_optional_number(value, "coverage_ratio")
        return 0.0 if normalized is None else normalized

    @model_validator(mode="after")
    def validate_report(self):
        return _validate_safety_flags(self, "snapshot source coverage report")


class KiwoomReadonlySnapshotFreshnessEntry(StrictModel):
    source_name: str = Field(..., min_length=1)
    latest_observed_at: datetime | None = None
    stale: bool = False
    reason: str | None = None

    @field_validator("source_name", "reason", mode="before")
    @classmethod
    def normalize_text(cls, value, info):
        if value is None and info.field_name == "reason":
            return None
        return _upper_required(value, info.field_name)

    @field_validator("latest_observed_at", mode="before")
    @classmethod
    def normalize_dt(cls, value):
        return _aware(value)


class KiwoomReadonlySnapshotFreshnessReport(_BaseReport):
    report_id: str = Field(..., min_length=1)
    entries: list[KiwoomReadonlySnapshotFreshnessEntry] = Field(default_factory=list)
    stale_source_count: int = Field(default=0, ge=0)

    @field_validator("report_id", mode="before")
    @classmethod
    def normalize_id(cls, value):
        return _upper_required(value, "report_id")

    @model_validator(mode="after")
    def validate_report(self):
        return _validate_safety_flags(self, "snapshot freshness report")


class KiwoomReadonlySnapshotCompletenessReport(_BaseReport):
    report_id: str = Field(..., min_length=1)
    snapshot_count: int = Field(default=0, ge=0)
    missing_fields: list[str] = Field(default_factory=list)

    @field_validator("report_id", mode="before")
    @classmethod
    def normalize_id(cls, value):
        return _upper_required(value, "report_id")

    @field_validator("missing_fields", mode="before")
    @classmethod
    def normalize_fields(cls, value):
        return _normalize_list(value, "missing_fields")

    @model_validator(mode="after")
    def validate_report(self):
        return _validate_safety_flags(self, "snapshot completeness report")


class KiwoomReadonlySnapshotConflictEntry(StrictModel):
    conflict_id: str = Field(..., min_length=1)
    canonical_instrument_key: str = Field(..., min_length=1)
    field_name: str = Field(..., min_length=1)
    left_value: str = Field(..., min_length=1)
    right_value: str = Field(..., min_length=1)

    @field_validator("conflict_id", "canonical_instrument_key", "field_name", mode="before")
    @classmethod
    def normalize_upper_fields(cls, value, info):
        return _upper_required(value, info.field_name)

    @field_validator("left_value", "right_value", mode="before")
    @classmethod
    def normalize_text(cls, value, info):
        return _string_required(value, info.field_name)


class KiwoomReadonlySnapshotConflictReport(_BaseReport):
    report_id: str = Field(..., min_length=1)
    entries: list[KiwoomReadonlySnapshotConflictEntry] = Field(default_factory=list)
    conflict_count: int = Field(default=0, ge=0)

    @field_validator("report_id", mode="before")
    @classmethod
    def normalize_id(cls, value):
        return _upper_required(value, "report_id")

    @model_validator(mode="after")
    def validate_report(self):
        return _validate_safety_flags(self, "snapshot conflict report")


class KiwoomReadonlyDomesticStockSnapshotReport(_BaseReport):
    report_id: str = Field(..., min_length=1)
    snapshots: list[CanonicalDomesticStockSnapshot] = Field(default_factory=list)

    @field_validator("report_id", mode="before")
    @classmethod
    def normalize_id(cls, value):
        return _upper_required(value, "report_id")

    @model_validator(mode="after")
    def validate_report(self):
        return _validate_safety_flags(self, "domestic stock snapshot report")


class KiwoomReadonlySnapshotV710IntegrationReport(_BaseReport):
    report_id: str = Field(..., min_length=1)
    v710_price_history_ready: bool = False
    v710_quote_liquidity_ready: bool = False

    @field_validator("report_id", mode="before")
    @classmethod
    def normalize_id(cls, value):
        return _upper_required(value, "report_id")

    @model_validator(mode="after")
    def validate_report(self):
        return _validate_safety_flags(self, "snapshot v710 integration report")


class KiwoomReadonlySnapshotV712IntegrationReport(_BaseReport):
    report_id: str = Field(..., min_length=1)
    v712_theme_context_ready: bool = False
    v712_market_context_ready: bool = False

    @field_validator("report_id", mode="before")
    @classmethod
    def normalize_id(cls, value):
        return _upper_required(value, "report_id")

    @model_validator(mode="after")
    def validate_report(self):
        return _validate_safety_flags(self, "snapshot v712 integration report")


class KiwoomReadonlySnapshotV713IntegrationReport(_BaseReport):
    report_id: str = Field(..., min_length=1)
    v713_snapshot_ready: bool = False
    v713_conflict_guard_enabled: bool = False

    @field_validator("report_id", mode="before")
    @classmethod
    def normalize_id(cls, value):
        return _upper_required(value, "report_id")

    @model_validator(mode="after")
    def validate_report(self):
        return _validate_safety_flags(self, "snapshot v713 integration report")


class KiwoomReadonlySnapshotGapEntry(StrictModel):
    gap_id: str = Field(..., min_length=1)
    gap_category: str = Field(..., min_length=1)
    severity: str = Field(..., min_length=1)
    message: str = Field(..., min_length=1)

    @field_validator("gap_id", "gap_category", "severity", mode="before")
    @classmethod
    def normalize_upper_text(cls, value, info):
        return _upper_required(value, info.field_name)

    @field_validator("message", mode="before")
    @classmethod
    def normalize_message(cls, value):
        return _string_required(value, "message")


class KiwoomReadonlySnapshotGapReport(_BaseReport):
    gap_report_id: str = Field(..., min_length=1)
    readiness: KiwoomReadonlySnapshotReadiness
    gap_entries: list[KiwoomReadonlySnapshotGapEntry] = Field(default_factory=list)

    @field_validator("gap_report_id", mode="before")
    @classmethod
    def normalize_id(cls, value):
        return _upper_required(value, "gap_report_id")

    @model_validator(mode="after")
    def validate_report(self):
        return _validate_safety_flags(self, "snapshot gap report")


class KiwoomReadonlySnapshotComposerResult(_BaseReport):
    adapter_result_id: str = Field(..., min_length=1)
    summary_report: KiwoomReadonlySnapshotSummaryReport
    source_coverage_report: KiwoomReadonlySnapshotSourceCoverageReport
    freshness_report: KiwoomReadonlySnapshotFreshnessReport
    completeness_report: KiwoomReadonlySnapshotCompletenessReport
    conflict_report: KiwoomReadonlySnapshotConflictReport
    domestic_stock_snapshot_report: KiwoomReadonlyDomesticStockSnapshotReport
    v710_integration_report: KiwoomReadonlySnapshotV710IntegrationReport
    v712_integration_report: KiwoomReadonlySnapshotV712IntegrationReport
    v713_integration_report: KiwoomReadonlySnapshotV713IntegrationReport
    safety_report: KiwoomReadonlySnapshotSafetyReport
    gap_report: KiwoomReadonlySnapshotGapReport
    audit_records: list[KiwoomReadonlySnapshotAuditRecord] = Field(default_factory=list)

    @field_validator("adapter_result_id", mode="before")
    @classmethod
    def normalize_id(cls, value):
        return _upper_required(value, "adapter_result_id")

    @model_validator(mode="after")
    def validate_report(self):
        return _validate_safety_flags(self, "snapshot composer result")
