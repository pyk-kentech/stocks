from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from pydantic import Field, field_validator, model_validator

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


def _normalize_number(value, field_name: str) -> float:
    if value is None:
        raise ValueError(f"{field_name} must not be null")
    text = str(value).strip().replace(",", "")
    if not text:
        raise ValueError(f"{field_name} must not be blank")
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


class KiwoomRestChartApiId(StrEnum):
    KA10080 = "KA10080"
    KA10081 = "KA10081"


class KiwoomRestChartReadiness(StrEnum):
    MOCKED_TRANSPORT_READY = "MOCKED_TRANSPORT_READY"
    CANONICAL_OHLCV_READY = "CANONICAL_OHLCV_READY"
    READONLY_ADAPTER_READY = "READONLY_ADAPTER_READY"
    DATA_GAP = "DATA_GAP"
    SCHEMA_GAP = "SCHEMA_GAP"
    BLOCKED = "BLOCKED"
    REJECTED = "REJECTED"


class KiwoomRestChartMode(StrEnum):
    MOCKED_TRANSPORT_ONLY = "MOCKED_TRANSPORT_ONLY"


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


class KiwoomRestChartContinuation(StrictModel):
    cont_yn: str = "N"
    next_key: str = ""

    @field_validator("cont_yn", mode="before")
    @classmethod
    def normalize_cont_yn(cls, value):
        cleaned = _upper_required(value, "cont_yn")
        if cleaned not in {"Y", "N"}:
            raise ValueError("cont_yn must be Y or N")
        return cleaned

    @field_validator("next_key", mode="before")
    @classmethod
    def normalize_next_key(cls, value):
        if value is None:
            return ""
        return str(value).strip()


class KiwoomRestChartBar(StrictModel):
    provider_symbol: str = Field(..., min_length=1)
    observed_at: datetime
    open_price: float
    high_price: float
    low_price: float
    close_price: float
    volume: float = Field(..., ge=0)
    adjusted_flag: bool = True
    previous_close_diff: float | None = None
    previous_close_sign_code: str | None = None

    @field_validator("provider_symbol", "previous_close_sign_code", mode="before")
    @classmethod
    def normalize_symbol(cls, value, info):
        if value is None and info.field_name == "previous_close_sign_code":
            return None
        return _upper_required(value, info.field_name)

    @field_validator("observed_at", mode="before")
    @classmethod
    def normalize_observed_at(cls, value):
        parsed = _aware(value)
        if parsed is None:
            raise ValueError("observed_at must not be null")
        return parsed

    @field_validator(
        "open_price",
        "high_price",
        "low_price",
        "close_price",
        "volume",
        "previous_close_diff",
        mode="before",
    )
    @classmethod
    def normalize_prices(cls, value, info):
        if value is None and info.field_name == "previous_close_diff":
            return None
        return _normalize_number(value, info.field_name)


class KiwoomRestChartRequest(_BaseReport):
    request_id: str = Field(..., min_length=1)
    provider: str = "KIWOOM_REST"
    mode: KiwoomRestChartMode = KiwoomRestChartMode.MOCKED_TRANSPORT_ONLY
    domain_ref: str = "https://api.kiwoom.com"
    mock_domain_ref: str = "https://mockapi.kiwoom.com"
    method: str = "POST"
    path: str = "/api/dostk/chart"
    api_id: KiwoomRestChartApiId
    token_ref: str = "TOKEN_REF_ONLY"
    content_type: str = "application/json;charset=UTF-8"
    provider_symbol: str = Field(..., min_length=1)
    base_dt: str = Field(..., min_length=8, max_length=8)
    upd_stkpc_tp: str = Field(default="1", min_length=1, max_length=1)
    tic_scope: str | None = None
    continuation: KiwoomRestChartContinuation = Field(default_factory=KiwoomRestChartContinuation)
    request_headers: dict[str, str] = Field(default_factory=dict)
    request_body: dict[str, str] = Field(default_factory=dict)

    @field_validator("request_id", "provider_symbol", "base_dt", "upd_stkpc_tp", "tic_scope", mode="before")
    @classmethod
    def normalize_fields(cls, value, info):
        if value is None and info.field_name == "tic_scope":
            return None
        return _upper_required(value, info.field_name)

    @field_validator("token_ref", mode="before")
    @classmethod
    def normalize_token_ref(cls, value):
        cleaned = _upper_required(value, "token_ref")
        if cleaned != "TOKEN_REF_ONLY":
            raise ValueError("token ref must remain TOKEN_REF_ONLY")
        return cleaned

    @model_validator(mode="after")
    def validate_request(self):
        _validate_safety_flags(self, "kiwoom rest chart request")
        if self.request_headers and self.request_headers.get("authorization") != "Bearer <TOKEN_REF_ONLY>":
            raise ValueError("authorization header must remain token-ref-only")
        return self


class KiwoomRestChartResponse(_BaseReport):
    response_id: str = Field(..., min_length=1)
    api_id: KiwoomRestChartApiId
    provider_symbol: str = Field(..., min_length=1)
    return_code: int
    return_msg: str = Field(..., min_length=1)
    bars: list[KiwoomRestChartBar] = Field(default_factory=list)
    continuation: KiwoomRestChartContinuation = Field(default_factory=KiwoomRestChartContinuation)
    raw_payload_redacted: bool = True

    @field_validator("response_id", "provider_symbol", mode="before")
    @classmethod
    def normalize_fields(cls, value, info):
        return _upper_required(value, info.field_name)

    @field_validator("return_msg", mode="before")
    @classmethod
    def normalize_return_msg(cls, value):
        return _string_required(value, "return_msg")

    @model_validator(mode="after")
    def validate_response(self):
        return _validate_safety_flags(self, "kiwoom rest chart response")


class KiwoomRestChartSafetyReport(_BaseReport):
    safety_report_id: str = Field(..., min_length=1)
    blocked_capabilities: list[str] = Field(default_factory=list)
    findings: list[str] = Field(default_factory=list)

    @field_validator("safety_report_id", mode="before")
    @classmethod
    def normalize_id(cls, value):
        return _upper_required(value, "safety_report_id")

    @field_validator("blocked_capabilities", "findings", mode="before")
    @classmethod
    def normalize_lists(cls, value, info):
        return _normalize_list(value, info.field_name)

    @model_validator(mode="after")
    def validate_report(self):
        return _validate_safety_flags(self, "kiwoom rest chart safety report")


class KiwoomRestChartGapEntry(StrictModel):
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


class KiwoomRestChartGapReport(_BaseReport):
    gap_report_id: str = Field(..., min_length=1)
    readiness: KiwoomRestChartReadiness
    gap_entries: list[KiwoomRestChartGapEntry] = Field(default_factory=list)

    @field_validator("gap_report_id", mode="before")
    @classmethod
    def normalize_id(cls, value):
        return _upper_required(value, "gap_report_id")

    @model_validator(mode="after")
    def validate_report(self):
        return _validate_safety_flags(self, "kiwoom rest chart gap report")


class KiwoomRestChartAuditRecord(StrictModel):
    audit_record_id: str = Field(..., min_length=1)
    created_at: datetime
    source_path: str = Field(..., min_length=1)
    operator_context: str = Field(..., min_length=1)
    redaction_applied: bool = True
    contains_secret_material: bool = False
    contains_token_material: bool = False
    contains_account_material: bool = False

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
        return _validate_local_path(value, "source_path")

    @field_validator("operator_context", mode="before")
    @classmethod
    def normalize_operator_context(cls, value):
        return _string_required(value, "operator_context")


class CanonicalOHLCVRecord(_BaseReport):
    provider: str = "KIWOOM_REST"
    provider_api_id: str = Field(..., min_length=1)
    canonical_instrument_key: str = Field(..., min_length=1)
    provider_symbol: str = Field(..., min_length=1)
    market: str = "KR"
    currency: str = "KRW"
    timeframe: str = Field(..., min_length=1)
    observed_at: datetime
    available_at: datetime | None = None
    open: float
    high: float
    low: float
    close: float
    volume: float = Field(..., ge=0)
    source_ref: str = Field(..., min_length=1)
    quality_flags: list[str] = Field(default_factory=list)
    stale_flag: bool = False
    gap_reason: str | None = None
    adjusted_flag: bool = True

    @field_validator(
        "provider_api_id",
        "canonical_instrument_key",
        "provider_symbol",
        "timeframe",
        "gap_reason",
        mode="before",
    )
    @classmethod
    def normalize_fields(cls, value, info):
        if value is None and info.field_name == "gap_reason":
            return None
        return _upper_required(value, info.field_name)

    @field_validator("observed_at", "available_at", mode="before")
    @classmethod
    def normalize_datetimes(cls, value):
        return _aware(value)

    @field_validator("source_ref", mode="before")
    @classmethod
    def normalize_source_ref(cls, value):
        return _validate_local_path(value, "source_ref")

    @field_validator("quality_flags", mode="before")
    @classmethod
    def normalize_quality_flags(cls, value):
        return _normalize_list(value, "quality_flags")

    @field_validator("open", "high", "low", "close", "volume", mode="before")
    @classmethod
    def normalize_numbers(cls, value, info):
        return _normalize_number(value, info.field_name)

    @model_validator(mode="after")
    def validate_record(self):
        return _validate_safety_flags(self, "canonical ohlcv record")


class KiwoomRestChartRequestReport(_BaseReport):
    report_id: str = Field(..., min_length=1)
    request: KiwoomRestChartRequest

    @field_validator("report_id", mode="before")
    @classmethod
    def normalize_id(cls, value):
        return _upper_required(value, "report_id")

    @model_validator(mode="after")
    def validate_report(self):
        return _validate_safety_flags(self, "kiwoom rest chart request report")


class KiwoomRestChartMockedResponseReport(_BaseReport):
    report_id: str = Field(..., min_length=1)
    response: KiwoomRestChartResponse

    @field_validator("report_id", mode="before")
    @classmethod
    def normalize_id(cls, value):
        return _upper_required(value, "report_id")

    @model_validator(mode="after")
    def validate_report(self):
        return _validate_safety_flags(self, "kiwoom rest chart mocked response report")


class KiwoomRestChartCanonicalOhlcvReport(_BaseReport):
    report_id: str = Field(..., min_length=1)
    records: list[CanonicalOHLCVRecord] = Field(default_factory=list)

    @field_validator("report_id", mode="before")
    @classmethod
    def normalize_id(cls, value):
        return _upper_required(value, "report_id")

    @model_validator(mode="after")
    def validate_report(self):
        return _validate_safety_flags(self, "kiwoom rest chart canonical ohlcv report")


class KiwoomRestChartContinuationReport(_BaseReport):
    report_id: str = Field(..., min_length=1)
    continuation: KiwoomRestChartContinuation
    has_more: bool = False

    @field_validator("report_id", mode="before")
    @classmethod
    def normalize_id(cls, value):
        return _upper_required(value, "report_id")

    @model_validator(mode="after")
    def validate_report(self):
        return _validate_safety_flags(self, "kiwoom rest chart continuation report")


class KiwoomRestChartIntegrationCompatibilityReport(_BaseReport):
    report_id: str = Field(..., min_length=1)
    v79_market_data_ready: bool = False
    v710_price_data_ready: bool = False
    canonical_fields_present: bool = False
    timeframe_supported: bool = False

    @field_validator("report_id", mode="before")
    @classmethod
    def normalize_id(cls, value):
        return _upper_required(value, "report_id")

    @model_validator(mode="after")
    def validate_report(self):
        return _validate_safety_flags(self, "kiwoom rest chart integration compatibility report")


class KiwoomRestChartSummaryReport(_BaseReport):
    report_id: str = Field(..., min_length=1)
    readiness: KiwoomRestChartReadiness
    decision_reason: str = Field(..., min_length=1)

    @field_validator("report_id", mode="before")
    @classmethod
    def normalize_id(cls, value):
        return _upper_required(value, "report_id")

    @field_validator("decision_reason", mode="before")
    @classmethod
    def normalize_reason(cls, value):
        return _string_required(value, "decision_reason")

    @model_validator(mode="after")
    def validate_report(self):
        return _validate_safety_flags(self, "kiwoom rest chart summary report")


class KiwoomRestChartAdapterResult(_BaseReport):
    adapter_result_id: str = Field(..., min_length=1)
    provider: str = "KIWOOM_REST"
    mode: KiwoomRestChartMode = KiwoomRestChartMode.MOCKED_TRANSPORT_ONLY
    request: KiwoomRestChartRequest
    summary_report: KiwoomRestChartSummaryReport
    request_report: KiwoomRestChartRequestReport
    mocked_response_report: KiwoomRestChartMockedResponseReport
    canonical_ohlcv_report: KiwoomRestChartCanonicalOhlcvReport
    continuation_report: KiwoomRestChartContinuationReport
    safety_report: KiwoomRestChartSafetyReport
    integration_compatibility_report: KiwoomRestChartIntegrationCompatibilityReport
    gap_report: KiwoomRestChartGapReport
    audit_records: list[KiwoomRestChartAuditRecord] = Field(default_factory=list)

    @field_validator("adapter_result_id", mode="before")
    @classmethod
    def normalize_id(cls, value):
        return _upper_required(value, "adapter_result_id")

    @model_validator(mode="after")
    def validate_result(self):
        return _validate_safety_flags(self, "kiwoom rest chart adapter result")


class KiwoomRestChartConfig(_BaseReport):
    config_id: str = Field(..., min_length=1)
    provider: str = "KIWOOM_REST"
    mode: KiwoomRestChartMode = KiwoomRestChartMode.MOCKED_TRANSPORT_ONLY
    domain_ref: str = "https://api.kiwoom.com"
    mock_domain_ref: str = "https://mockapi.kiwoom.com"
    token_ref: str = "TOKEN_REF_ONLY"
    api_id: KiwoomRestChartApiId
    path: str = "/api/dostk/chart"
    provider_symbol: str = Field(..., min_length=1)
    canonical_instrument_key: str = Field(..., min_length=1)
    base_dt: str = Field(..., min_length=8, max_length=8)
    upd_stkpc_tp: str = Field(default="1", min_length=1, max_length=1)
    tic_scope: str | None = None
    continuation: KiwoomRestChartContinuation = Field(default_factory=KiwoomRestChartContinuation)
    max_pages: int = Field(default=1, ge=1, le=10)
    timeout_seconds: int = Field(default=5, ge=1, le=30)
    retry_count: int = Field(default=0, ge=0, le=2)
    available_at: datetime | None = None
    source_ref: str = Field(..., min_length=1)
    mocked_response_payload: dict[str, object] | None = None
    safety_report: KiwoomRestChartSafetyReport
    audit_records: list[KiwoomRestChartAuditRecord] = Field(default_factory=list)

    @field_validator(
        "config_id",
        "provider_symbol",
        "canonical_instrument_key",
        "base_dt",
        "upd_stkpc_tp",
        "tic_scope",
        mode="before",
    )
    @classmethod
    def normalize_fields(cls, value, info):
        if value is None and info.field_name == "tic_scope":
            return None
        return _upper_required(value, info.field_name)

    @field_validator("source_ref", mode="before")
    @classmethod
    def normalize_source_ref(cls, value):
        return _validate_local_path(value, "source_ref")

    @field_validator("available_at", mode="before")
    @classmethod
    def normalize_available_at(cls, value):
        return _aware(value)

    @field_validator("token_ref", mode="before")
    @classmethod
    def normalize_token_ref(cls, value):
        cleaned = _upper_required(value, "token_ref")
        if cleaned != "TOKEN_REF_ONLY":
            raise ValueError("token ref must remain TOKEN_REF_ONLY")
        return cleaned

    @model_validator(mode="after")
    def validate_config(self):
        _validate_safety_flags(self, "kiwoom rest chart config")
        if self.api_id == KiwoomRestChartApiId.KA10081 and self.tic_scope is not None:
            raise ValueError("daily chart request must not include tic_scope")
        if self.api_id == KiwoomRestChartApiId.KA10080 and self.tic_scope is None:
            raise ValueError("minute chart request requires tic_scope")
        if self.upd_stkpc_tp not in {"0", "1"}:
            raise ValueError("upd_stkpc_tp must be 0 or 1")
        return self
