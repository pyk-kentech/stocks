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


def _normalize_optional_number(value, field_name: str) -> float | None:
    if value in (None, ""):
        return None
    return _normalize_number(value, field_name)


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


class KiwoomRestQuoteApiId(StrEnum):
    KA10004 = "KA10004"
    KA10003 = "KA10003"
    KA10001 = "KA10001"


class KiwoomRestQuoteReadiness(StrEnum):
    MOCKED_TRANSPORT_READY = "MOCKED_TRANSPORT_READY"
    CANONICAL_QUOTE_READY = "CANONICAL_QUOTE_READY"
    CANONICAL_ORDERBOOK_READY = "CANONICAL_ORDERBOOK_READY"
    LIQUIDITY_HINT_READY = "LIQUIDITY_HINT_READY"
    READONLY_ADAPTER_READY = "READONLY_ADAPTER_READY"
    DATA_GAP = "DATA_GAP"
    SCHEMA_GAP = "SCHEMA_GAP"
    BLOCKED = "BLOCKED"
    REJECTED = "REJECTED"


class KiwoomRestQuoteMode(StrEnum):
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


class KiwoomRestQuoteContinuation(StrictModel):
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


class KiwoomRestOrderbookLevel(StrictModel):
    side: str = Field(..., min_length=1)
    level: int = Field(..., ge=1, le=10)
    price: float | None = None
    quantity: float | None = Field(default=None, ge=0)
    quantity_change: float | None = None

    @field_validator("side", mode="before")
    @classmethod
    def normalize_side(cls, value):
        cleaned = _upper_required(value, "side")
        if cleaned not in {"ASK", "BID"}:
            raise ValueError("side must be ASK or BID")
        return cleaned

    @field_validator("price", "quantity", "quantity_change", mode="before")
    @classmethod
    def normalize_numbers(cls, value, info):
        return _normalize_optional_number(value, info.field_name)


class KiwoomRestExecutionItem(StrictModel):
    observed_at: datetime
    last_price: float | None = None
    price_change: float | None = None
    percent_change: float | None = None
    priority_ask_price: float | None = None
    priority_bid_price: float | None = None
    last_trade_quantity: float | None = Field(default=None, ge=0)
    sign_code: str | None = None

    @field_validator("observed_at", mode="before")
    @classmethod
    def normalize_observed_at(cls, value):
        parsed = _aware(value)
        if parsed is None:
            raise ValueError("observed_at must not be null")
        return parsed

    @field_validator("sign_code", mode="before")
    @classmethod
    def normalize_sign_code(cls, value):
        if value is None:
            return None
        return _upper_required(value, "sign_code")

    @field_validator(
        "last_price",
        "price_change",
        "percent_change",
        "priority_ask_price",
        "priority_bid_price",
        "last_trade_quantity",
        mode="before",
    )
    @classmethod
    def normalize_numbers(cls, value, info):
        return _normalize_optional_number(value, info.field_name)


class KiwoomRestBasicInfo(StrictModel):
    provider_symbol: str = Field(..., min_length=1)
    stock_name: str | None = None
    settlement_month: str | None = None
    face_value: float | None = None
    capital: float | None = None
    listed_shares: float | None = Field(default=None, ge=0)
    credit_ratio: float | None = None
    yearly_high: float | None = None
    yearly_low: float | None = None
    market_cap: float | None = None
    market_cap_weight: float | None = None

    @field_validator("provider_symbol", mode="before")
    @classmethod
    def normalize_symbol(cls, value):
        return _upper_required(value, "provider_symbol")

    @field_validator("stock_name", "settlement_month", mode="before")
    @classmethod
    def normalize_optional_text(cls, value):
        if value in (None, ""):
            return None
        return _string_required(value, "field")

    @field_validator(
        "face_value",
        "capital",
        "listed_shares",
        "credit_ratio",
        "yearly_high",
        "yearly_low",
        "market_cap",
        "market_cap_weight",
        mode="before",
    )
    @classmethod
    def normalize_numbers(cls, value, info):
        return _normalize_optional_number(value, info.field_name)


class KiwoomRestQuoteRequest(_BaseReport):
    request_id: str = Field(..., min_length=1)
    provider: str = "KIWOOM_REST"
    mode: KiwoomRestQuoteMode = KiwoomRestQuoteMode.MOCKED_TRANSPORT_ONLY
    domain_ref: str = "https://api.kiwoom.com"
    mock_domain_ref: str = "https://mockapi.kiwoom.com"
    method: str = "POST"
    path: str = Field(..., min_length=1)
    api_id: KiwoomRestQuoteApiId
    token_ref: str = "TOKEN_REF_ONLY"
    provider_symbol: str = Field(..., min_length=1)
    content_type: str = "application/json;charset=UTF-8"
    continuation: KiwoomRestQuoteContinuation = Field(default_factory=KiwoomRestQuoteContinuation)
    request_headers: dict[str, str] = Field(default_factory=dict)
    request_body: dict[str, str] = Field(default_factory=dict)

    @field_validator("request_id", "provider_symbol", mode="before")
    @classmethod
    def normalize_upper_fields(cls, value, info):
        return _upper_required(value, info.field_name)

    @field_validator("path", mode="before")
    @classmethod
    def normalize_path(cls, value):
        return _string_required(value, "path")

    @field_validator("token_ref", mode="before")
    @classmethod
    def normalize_token_ref(cls, value):
        cleaned = _upper_required(value, "token_ref")
        if cleaned != "TOKEN_REF_ONLY":
            raise ValueError("token ref must remain TOKEN_REF_ONLY")
        return cleaned

    @model_validator(mode="after")
    def validate_request(self):
        _validate_safety_flags(self, "kiwoom rest quote request")
        if self.request_headers and self.request_headers.get("authorization") != "Bearer <TOKEN_REF_ONLY>":
            raise ValueError("authorization header must remain token-ref-only")
        return self


class KiwoomRestQuoteResponse(_BaseReport):
    response_id: str = Field(..., min_length=1)
    api_id: KiwoomRestQuoteApiId
    provider_symbol: str = Field(..., min_length=1)
    stock_name: str | None = None
    return_code: int
    return_msg: str = Field(..., min_length=1)
    orderbook_base_time: datetime | None = None
    orderbook_levels: list[KiwoomRestOrderbookLevel] = Field(default_factory=list)
    execution_items: list[KiwoomRestExecutionItem] = Field(default_factory=list)
    basic_info: KiwoomRestBasicInfo | None = None
    continuation: KiwoomRestQuoteContinuation = Field(default_factory=KiwoomRestQuoteContinuation)
    raw_payload_redacted: bool = True

    @field_validator("response_id", "provider_symbol", mode="before")
    @classmethod
    def normalize_upper_fields(cls, value, info):
        return _upper_required(value, info.field_name)

    @field_validator("stock_name", mode="before")
    @classmethod
    def normalize_stock_name(cls, value):
        if value in (None, ""):
            return None
        return _string_required(value, "stock_name")

    @field_validator("return_msg", mode="before")
    @classmethod
    def normalize_return_msg(cls, value):
        return _string_required(value, "return_msg")

    @field_validator("orderbook_base_time", mode="before")
    @classmethod
    def normalize_base_time(cls, value):
        return _aware(value)

    @model_validator(mode="after")
    def validate_response(self):
        return _validate_safety_flags(self, "kiwoom rest quote response")


class KiwoomRestQuoteSafetyReport(_BaseReport):
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
        return _validate_safety_flags(self, "kiwoom rest quote safety report")


class KiwoomRestQuoteGapEntry(StrictModel):
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


class KiwoomRestQuoteGapReport(_BaseReport):
    gap_report_id: str = Field(..., min_length=1)
    readiness: KiwoomRestQuoteReadiness
    gap_entries: list[KiwoomRestQuoteGapEntry] = Field(default_factory=list)

    @field_validator("gap_report_id", mode="before")
    @classmethod
    def normalize_id(cls, value):
        return _upper_required(value, "gap_report_id")

    @model_validator(mode="after")
    def validate_report(self):
        return _validate_safety_flags(self, "kiwoom rest quote gap report")


class KiwoomRestQuoteAuditRecord(StrictModel):
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


class CanonicalQuoteRecord(_BaseReport):
    provider: str = "KIWOOM_REST"
    provider_api_id: str = Field(..., min_length=1)
    canonical_instrument_key: str = Field(..., min_length=1)
    provider_symbol: str = Field(..., min_length=1)
    stock_name: str | None = None
    market: str = "KR"
    currency: str = "KRW"
    observed_at: datetime
    available_at: datetime | None = None
    last_price: float | None = None
    bid_price: float | None = None
    ask_price: float | None = None
    bid_quantity: float | None = Field(default=None, ge=0)
    ask_quantity: float | None = Field(default=None, ge=0)
    spread: float | None = None
    mid_price: float | None = None
    last_trade_quantity: float | None = Field(default=None, ge=0)
    percent_change: float | None = None
    price_change: float | None = None
    liquidity_evidence_flag: bool = False
    source_ref: str = Field(..., min_length=1)
    quality_flags: list[str] = Field(default_factory=list)
    stale_flag: bool = False
    gap_reason: str | None = None

    @field_validator("provider_api_id", "canonical_instrument_key", "provider_symbol", "gap_reason", mode="before")
    @classmethod
    def normalize_upper_optional(cls, value, info):
        if value is None and info.field_name == "gap_reason":
            return None
        return _upper_required(value, info.field_name)

    @field_validator("stock_name", mode="before")
    @classmethod
    def normalize_stock_name(cls, value):
        if value in (None, ""):
            return None
        return _string_required(value, "stock_name")

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

    @field_validator(
        "last_price",
        "bid_price",
        "ask_price",
        "bid_quantity",
        "ask_quantity",
        "spread",
        "mid_price",
        "last_trade_quantity",
        "percent_change",
        "price_change",
        mode="before",
    )
    @classmethod
    def normalize_numbers(cls, value, info):
        return _normalize_optional_number(value, info.field_name)

    @model_validator(mode="after")
    def validate_record(self):
        return _validate_safety_flags(self, "canonical quote record")


class CanonicalOrderbookRecord(_BaseReport):
    provider: str = "KIWOOM_REST"
    provider_api_id: str = Field(..., min_length=1)
    canonical_instrument_key: str = Field(..., min_length=1)
    provider_symbol: str = Field(..., min_length=1)
    stock_name: str | None = None
    market: str = "KR"
    currency: str = "KRW"
    observed_at: datetime
    available_at: datetime | None = None
    levels: list[KiwoomRestOrderbookLevel] = Field(default_factory=list)
    spread: float | None = None
    mid_price: float | None = None
    top_of_book_imbalance: float | None = None
    depth_summary_quantity: float | None = Field(default=None, ge=0)
    source_ref: str = Field(..., min_length=1)
    quality_flags: list[str] = Field(default_factory=list)
    stale_flag: bool = False
    gap_reason: str | None = None

    @field_validator("provider_api_id", "canonical_instrument_key", "provider_symbol", "gap_reason", mode="before")
    @classmethod
    def normalize_upper_optional(cls, value, info):
        if value is None and info.field_name == "gap_reason":
            return None
        return _upper_required(value, info.field_name)

    @field_validator("stock_name", mode="before")
    @classmethod
    def normalize_stock_name(cls, value):
        if value in (None, ""):
            return None
        return _string_required(value, "stock_name")

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

    @field_validator("spread", "mid_price", "top_of_book_imbalance", "depth_summary_quantity", mode="before")
    @classmethod
    def normalize_numbers(cls, value, info):
        return _normalize_optional_number(value, info.field_name)

    @model_validator(mode="after")
    def validate_record(self):
        return _validate_safety_flags(self, "canonical orderbook record")


class CanonicalLiquidityHint(_BaseReport):
    provider: str = "KIWOOM_REST"
    provider_api_id: str = Field(..., min_length=1)
    canonical_instrument_key: str = Field(..., min_length=1)
    provider_symbol: str = Field(..., min_length=1)
    stock_name: str | None = None
    observed_at: datetime
    available_at: datetime | None = None
    spread: float | None = None
    mid_price: float | None = None
    last_trade_quantity: float | None = Field(default=None, ge=0)
    top_of_book_imbalance: float | None = None
    price_liquidity_ready: bool = False
    outlier_routing_ready: bool = False
    mock_intent_preview_ready: bool = False
    source_ref: str = Field(..., min_length=1)
    quality_flags: list[str] = Field(default_factory=list)
    stale_flag: bool = False
    gap_reason: str | None = None

    @field_validator("provider_api_id", "canonical_instrument_key", "provider_symbol", "gap_reason", mode="before")
    @classmethod
    def normalize_upper_optional(cls, value, info):
        if value is None and info.field_name == "gap_reason":
            return None
        return _upper_required(value, info.field_name)

    @field_validator("stock_name", mode="before")
    @classmethod
    def normalize_stock_name(cls, value):
        if value in (None, ""):
            return None
        return _string_required(value, "stock_name")

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

    @field_validator("spread", "mid_price", "last_trade_quantity", "top_of_book_imbalance", mode="before")
    @classmethod
    def normalize_numbers(cls, value, info):
        return _normalize_optional_number(value, info.field_name)

    @model_validator(mode="after")
    def validate_record(self):
        return _validate_safety_flags(self, "canonical liquidity hint")


class CanonicalBasicInstrumentInfo(_BaseReport):
    provider: str = "KIWOOM_REST"
    provider_api_id: str = Field(..., min_length=1)
    canonical_instrument_key: str = Field(..., min_length=1)
    provider_symbol: str = Field(..., min_length=1)
    stock_name: str | None = None
    market: str = "KR"
    currency: str = "KRW"
    available_at: datetime | None = None
    settlement_month: str | None = None
    face_value: float | None = None
    capital: float | None = None
    listed_shares: float | None = Field(default=None, ge=0)
    credit_ratio: float | None = None
    yearly_high: float | None = None
    yearly_low: float | None = None
    market_cap: float | None = None
    market_cap_weight: float | None = None
    source_ref: str = Field(..., min_length=1)
    quality_flags: list[str] = Field(default_factory=list)
    stale_flag: bool = False
    gap_reason: str | None = None

    @field_validator("provider_api_id", "canonical_instrument_key", "provider_symbol", "gap_reason", mode="before")
    @classmethod
    def normalize_upper_optional(cls, value, info):
        if value is None and info.field_name == "gap_reason":
            return None
        return _upper_required(value, info.field_name)

    @field_validator("stock_name", "settlement_month", mode="before")
    @classmethod
    def normalize_optional_text(cls, value):
        if value in (None, ""):
            return None
        return _string_required(value, "field")

    @field_validator("available_at", mode="before")
    @classmethod
    def normalize_available_at(cls, value):
        return _aware(value)

    @field_validator("source_ref", mode="before")
    @classmethod
    def normalize_source_ref(cls, value):
        return _validate_local_path(value, "source_ref")

    @field_validator("quality_flags", mode="before")
    @classmethod
    def normalize_quality_flags(cls, value):
        return _normalize_list(value, "quality_flags")

    @field_validator(
        "face_value",
        "capital",
        "listed_shares",
        "credit_ratio",
        "yearly_high",
        "yearly_low",
        "market_cap",
        "market_cap_weight",
        mode="before",
    )
    @classmethod
    def normalize_numbers(cls, value, info):
        return _normalize_optional_number(value, info.field_name)

    @model_validator(mode="after")
    def validate_record(self):
        return _validate_safety_flags(self, "canonical basic instrument info")


class KiwoomRestQuoteRequestReport(_BaseReport):
    report_id: str = Field(..., min_length=1)
    request: KiwoomRestQuoteRequest

    @field_validator("report_id", mode="before")
    @classmethod
    def normalize_id(cls, value):
        return _upper_required(value, "report_id")

    @model_validator(mode="after")
    def validate_report(self):
        return _validate_safety_flags(self, "kiwoom rest quote request report")


class KiwoomRestQuoteMockedResponseReport(_BaseReport):
    report_id: str = Field(..., min_length=1)
    response: KiwoomRestQuoteResponse

    @field_validator("report_id", mode="before")
    @classmethod
    def normalize_id(cls, value):
        return _upper_required(value, "report_id")

    @model_validator(mode="after")
    def validate_report(self):
        return _validate_safety_flags(self, "kiwoom rest quote mocked response report")


class KiwoomRestCanonicalQuoteReport(_BaseReport):
    report_id: str = Field(..., min_length=1)
    records: list[CanonicalQuoteRecord] = Field(default_factory=list)

    @field_validator("report_id", mode="before")
    @classmethod
    def normalize_id(cls, value):
        return _upper_required(value, "report_id")

    @model_validator(mode="after")
    def validate_report(self):
        return _validate_safety_flags(self, "kiwoom rest canonical quote report")


class KiwoomRestCanonicalOrderbookReport(_BaseReport):
    report_id: str = Field(..., min_length=1)
    records: list[CanonicalOrderbookRecord] = Field(default_factory=list)

    @field_validator("report_id", mode="before")
    @classmethod
    def normalize_id(cls, value):
        return _upper_required(value, "report_id")

    @model_validator(mode="after")
    def validate_report(self):
        return _validate_safety_flags(self, "kiwoom rest canonical orderbook report")


class KiwoomRestLiquidityHintReport(_BaseReport):
    report_id: str = Field(..., min_length=1)
    records: list[CanonicalLiquidityHint] = Field(default_factory=list)

    @field_validator("report_id", mode="before")
    @classmethod
    def normalize_id(cls, value):
        return _upper_required(value, "report_id")

    @model_validator(mode="after")
    def validate_report(self):
        return _validate_safety_flags(self, "kiwoom rest liquidity hint report")


class KiwoomRestBasicInfoReport(_BaseReport):
    report_id: str = Field(..., min_length=1)
    records: list[CanonicalBasicInstrumentInfo] = Field(default_factory=list)

    @field_validator("report_id", mode="before")
    @classmethod
    def normalize_id(cls, value):
        return _upper_required(value, "report_id")

    @model_validator(mode="after")
    def validate_report(self):
        return _validate_safety_flags(self, "kiwoom rest basic info report")


class KiwoomRestQuoteContinuationReport(_BaseReport):
    report_id: str = Field(..., min_length=1)
    continuation: KiwoomRestQuoteContinuation
    has_more: bool = False

    @field_validator("report_id", mode="before")
    @classmethod
    def normalize_id(cls, value):
        return _upper_required(value, "report_id")

    @model_validator(mode="after")
    def validate_report(self):
        return _validate_safety_flags(self, "kiwoom rest quote continuation report")


class KiwoomRestQuoteV7IntegrationReport(_BaseReport):
    report_id: str = Field(..., min_length=1)
    v710_price_liquidity_ready: bool = False
    v712_liquidity_outlier_ready: bool = False
    v713_mock_intent_preview_ready: bool = False
    canonical_fields_present: bool = False

    @field_validator("report_id", mode="before")
    @classmethod
    def normalize_id(cls, value):
        return _upper_required(value, "report_id")

    @model_validator(mode="after")
    def validate_report(self):
        return _validate_safety_flags(self, "kiwoom rest quote v7 integration report")


class KiwoomRestQuoteSummaryReport(_BaseReport):
    report_id: str = Field(..., min_length=1)
    readiness: KiwoomRestQuoteReadiness
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
        return _validate_safety_flags(self, "kiwoom rest quote summary report")


class KiwoomRestQuoteConfig(_BaseReport):
    config_id: str = Field(..., min_length=1)
    provider: str = "KIWOOM_REST"
    mode: KiwoomRestQuoteMode = KiwoomRestQuoteMode.MOCKED_TRANSPORT_ONLY
    api_id: KiwoomRestQuoteApiId
    provider_symbol: str = Field(..., min_length=1)
    available_at: datetime | None = None
    request_date: str | None = None
    source_ref: str = Field(..., min_length=1)
    token_ref: str = "TOKEN_REF_ONLY"
    continuation: KiwoomRestQuoteContinuation = Field(default_factory=KiwoomRestQuoteContinuation)
    max_pages: int = Field(default=1, ge=1)
    timeout_policy: str = "MOCKED_TRANSPORT_ONLY"
    retry_policy: str = "NO_RETRY"
    mocked_response_payload: dict[str, object] | None = None
    safety_report: KiwoomRestQuoteSafetyReport
    audit_records: list[KiwoomRestQuoteAuditRecord] = Field(default_factory=list)

    @field_validator("config_id", "provider_symbol", "request_date", mode="before")
    @classmethod
    def normalize_optionals(cls, value, info):
        if value is None and info.field_name == "request_date":
            return None
        return _upper_required(value, info.field_name)

    @field_validator("available_at", mode="before")
    @classmethod
    def normalize_available_at(cls, value):
        return _aware(value)

    @field_validator("source_ref", mode="before")
    @classmethod
    def normalize_source_ref(cls, value):
        return _validate_local_path(value, "source_ref")

    @field_validator("token_ref", mode="before")
    @classmethod
    def normalize_token_ref(cls, value):
        cleaned = _upper_required(value, "token_ref")
        if cleaned != "TOKEN_REF_ONLY":
            raise ValueError("token ref must remain TOKEN_REF_ONLY")
        return cleaned

    @model_validator(mode="after")
    def validate_config(self):
        _validate_safety_flags(self, "kiwoom rest quote config")
        if self.api_id == KiwoomRestQuoteApiId.KA10003 and self.request_date is None:
            raise ValueError("ka10003 requires request_date")
        return self


class KiwoomRestQuoteAdapterResult(_BaseReport):
    adapter_result_id: str = Field(..., min_length=1)
    request: KiwoomRestQuoteRequest
    summary_report: KiwoomRestQuoteSummaryReport
    request_report: KiwoomRestQuoteRequestReport
    mocked_response_report: KiwoomRestQuoteMockedResponseReport
    canonical_quote_report: KiwoomRestCanonicalQuoteReport
    canonical_orderbook_report: KiwoomRestCanonicalOrderbookReport
    liquidity_hint_report: KiwoomRestLiquidityHintReport
    basic_info_report: KiwoomRestBasicInfoReport
    continuation_report: KiwoomRestQuoteContinuationReport
    safety_report: KiwoomRestQuoteSafetyReport
    v7_integration_report: KiwoomRestQuoteV7IntegrationReport
    gap_report: KiwoomRestQuoteGapReport
    audit_records: list[KiwoomRestQuoteAuditRecord] = Field(default_factory=list)

    @field_validator("adapter_result_id", mode="before")
    @classmethod
    def normalize_id(cls, value):
        return _upper_required(value, "adapter_result_id")

    @model_validator(mode="after")
    def validate_result(self):
        return _validate_safety_flags(self, "kiwoom rest quote adapter result")
