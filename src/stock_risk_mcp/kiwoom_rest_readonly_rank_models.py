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


class KiwoomRestRankApiId(StrEnum):
    KA00198 = "KA00198"
    KA10023 = "KA10023"
    KA10030 = "KA10030"
    KA10032 = "KA10032"
    KA10019 = "KA10019"
    KA10027 = "KA10027"
    KA10098 = "KA10098"


class KiwoomRestRankReadiness(StrEnum):
    MOCKED_TRANSPORT_READY = "MOCKED_TRANSPORT_READY"
    CANONICAL_RANK_READY = "CANONICAL_RANK_READY"
    CANONICAL_OUTLIER_READY = "CANONICAL_OUTLIER_READY"
    READONLY_ADAPTER_READY = "READONLY_ADAPTER_READY"
    DATA_GAP = "DATA_GAP"
    SCHEMA_GAP = "SCHEMA_GAP"
    BLOCKED = "BLOCKED"
    REJECTED = "REJECTED"


class KiwoomRestRankMode(StrEnum):
    MOCKED_TRANSPORT_ONLY = "MOCKED_TRANSPORT_ONLY"


class CanonicalOutlierCategory(StrEnum):
    REALTIME_INQUIRY_RANK = "REALTIME_INQUIRY_RANK"
    VOLUME_SURGE = "VOLUME_SURGE"
    VOLUME_RANK = "VOLUME_RANK"
    TRADING_VALUE_RANK = "TRADING_VALUE_RANK"
    PRICE_SURGE = "PRICE_SURGE"
    AFTER_HOURS_SURGE = "AFTER_HOURS_SURGE"
    UNKNOWN = "UNKNOWN"


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


class KiwoomRestRankContinuation(StrictModel):
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


class KiwoomRestRankItem(StrictModel):
    provider_symbol: str = Field(..., min_length=1)
    stock_name: str = Field(..., min_length=1)
    observed_at: datetime
    rank: int = Field(..., ge=1)
    previous_rank: int | None = Field(default=None, ge=1)
    rank_change: int | None = None
    rank_change_sign: str | None = None
    price: float | None = None
    price_change: float | None = None
    percent_change: float | None = None
    volume: float | None = Field(default=None, ge=0)
    trading_value: float | None = Field(default=None, ge=0)
    relative_volume: float | None = Field(default=None, ge=0)
    liquidity_evidence_flag: bool = False
    outlier_category: CanonicalOutlierCategory = CanonicalOutlierCategory.UNKNOWN
    gap_reason: str | None = None

    @field_validator("provider_symbol", "rank_change_sign", "gap_reason", mode="before")
    @classmethod
    def normalize_upper_optional(cls, value, info):
        if value is None and info.field_name in {"rank_change_sign", "gap_reason"}:
            return None
        return _upper_required(value, info.field_name)

    @field_validator("stock_name", mode="before")
    @classmethod
    def normalize_stock_name(cls, value):
        return _string_required(value, "stock_name")

    @field_validator("observed_at", mode="before")
    @classmethod
    def normalize_observed_at(cls, value):
        parsed = _aware(value)
        if parsed is None:
            raise ValueError("observed_at must not be null")
        return parsed

    @field_validator("rank", "previous_rank", "rank_change", mode="before")
    @classmethod
    def normalize_ints(cls, value, info):
        if value is None and info.field_name in {"previous_rank", "rank_change"}:
            return None
        normalized = _normalize_number(value, info.field_name)
        return int(normalized)

    @field_validator("price", "price_change", "percent_change", "volume", "trading_value", "relative_volume", mode="before")
    @classmethod
    def normalize_numbers(cls, value, info):
        return _normalize_optional_number(value, info.field_name)


class KiwoomRestRankRequest(_BaseReport):
    request_id: str = Field(..., min_length=1)
    provider: str = "KIWOOM_REST"
    mode: KiwoomRestRankMode = KiwoomRestRankMode.MOCKED_TRANSPORT_ONLY
    domain_ref: str = "https://api.kiwoom.com"
    mock_domain_ref: str = "https://mockapi.kiwoom.com"
    method: str = "POST"
    path: str = Field(..., min_length=1)
    api_id: KiwoomRestRankApiId
    token_ref: str = "TOKEN_REF_ONLY"
    content_type: str = "application/json;charset=UTF-8"
    continuation: KiwoomRestRankContinuation = Field(default_factory=KiwoomRestRankContinuation)
    request_headers: dict[str, str] = Field(default_factory=dict)
    request_body: dict[str, str] = Field(default_factory=dict)

    @field_validator("request_id", "path", mode="before")
    @classmethod
    def normalize_fields(cls, value, info):
        if info.field_name == "path":
            return _string_required(value, info.field_name)
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
        _validate_safety_flags(self, "kiwoom rest rank request")
        if self.request_headers and self.request_headers.get("authorization") != "Bearer <TOKEN_REF_ONLY>":
            raise ValueError("authorization header must remain token-ref-only")
        return self


class KiwoomRestRankResponse(_BaseReport):
    response_id: str = Field(..., min_length=1)
    api_id: KiwoomRestRankApiId
    return_code: int
    return_msg: str = Field(..., min_length=1)
    items: list[KiwoomRestRankItem] = Field(default_factory=list)
    continuation: KiwoomRestRankContinuation = Field(default_factory=KiwoomRestRankContinuation)
    raw_payload_redacted: bool = True

    @field_validator("response_id", mode="before")
    @classmethod
    def normalize_id(cls, value):
        return _upper_required(value, "response_id")

    @field_validator("return_msg", mode="before")
    @classmethod
    def normalize_return_msg(cls, value):
        return _string_required(value, "return_msg")

    @model_validator(mode="after")
    def validate_response(self):
        return _validate_safety_flags(self, "kiwoom rest rank response")


class KiwoomRestRankSafetyReport(_BaseReport):
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
        return _validate_safety_flags(self, "kiwoom rest rank safety report")


class KiwoomRestRankGapEntry(StrictModel):
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


class KiwoomRestRankGapReport(_BaseReport):
    gap_report_id: str = Field(..., min_length=1)
    readiness: KiwoomRestRankReadiness
    gap_entries: list[KiwoomRestRankGapEntry] = Field(default_factory=list)

    @field_validator("gap_report_id", mode="before")
    @classmethod
    def normalize_id(cls, value):
        return _upper_required(value, "gap_report_id")

    @model_validator(mode="after")
    def validate_report(self):
        return _validate_safety_flags(self, "kiwoom rest rank gap report")


class KiwoomRestRankAuditRecord(StrictModel):
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


class _CanonicalSignalBase(_BaseReport):
    provider: str = "KIWOOM_REST"
    provider_api_id: str = Field(..., min_length=1)
    canonical_instrument_key: str = Field(..., min_length=1)
    provider_symbol: str = Field(..., min_length=1)
    stock_name: str = Field(..., min_length=1)
    market: str = "KR"
    currency: str = "KRW"
    observed_at: datetime
    available_at: datetime | None = None
    rank_type: str = Field(..., min_length=1)
    rank: int = Field(..., ge=1)
    previous_rank: int | None = Field(default=None, ge=1)
    rank_change: int | None = None
    price: float | None = None
    price_change: float | None = None
    percent_change: float | None = None
    volume: float | None = Field(default=None, ge=0)
    trading_value: float | None = Field(default=None, ge=0)
    relative_volume: float | None = Field(default=None, ge=0)
    liquidity_evidence_flag: bool = False
    outlier_category: CanonicalOutlierCategory = CanonicalOutlierCategory.UNKNOWN
    source_ref: str = Field(..., min_length=1)
    quality_flags: list[str] = Field(default_factory=list)
    stale_flag: bool = False
    gap_reason: str | None = None

    @field_validator(
        "provider_api_id",
        "canonical_instrument_key",
        "provider_symbol",
        "rank_type",
        "gap_reason",
        mode="before",
    )
    @classmethod
    def normalize_fields(cls, value, info):
        if value is None and info.field_name == "gap_reason":
            return None
        return _upper_required(value, info.field_name)

    @field_validator("stock_name", mode="before")
    @classmethod
    def normalize_stock_name(cls, value):
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

    @field_validator("rank", "previous_rank", "rank_change", mode="before")
    @classmethod
    def normalize_ints(cls, value, info):
        if value is None and info.field_name in {"previous_rank", "rank_change"}:
            return None
        return int(_normalize_number(value, info.field_name))

    @field_validator("price", "price_change", "percent_change", "volume", "trading_value", "relative_volume", mode="before")
    @classmethod
    def normalize_numbers(cls, value, info):
        return _normalize_optional_number(value, info.field_name)

    @model_validator(mode="after")
    def validate_record(self):
        return _validate_safety_flags(self, "canonical rank signal")


class CanonicalRankSignal(_CanonicalSignalBase):
    pass


class CanonicalOutlierMomentumSignal(_CanonicalSignalBase):
    pass


class KiwoomRestRankRequestReport(_BaseReport):
    report_id: str = Field(..., min_length=1)
    request: KiwoomRestRankRequest

    @field_validator("report_id", mode="before")
    @classmethod
    def normalize_id(cls, value):
        return _upper_required(value, "report_id")

    @model_validator(mode="after")
    def validate_report(self):
        return _validate_safety_flags(self, "kiwoom rest rank request report")


class KiwoomRestRankMockedResponseReport(_BaseReport):
    report_id: str = Field(..., min_length=1)
    response: KiwoomRestRankResponse

    @field_validator("report_id", mode="before")
    @classmethod
    def normalize_id(cls, value):
        return _upper_required(value, "report_id")

    @model_validator(mode="after")
    def validate_report(self):
        return _validate_safety_flags(self, "kiwoom rest rank mocked response report")


class KiwoomRestCanonicalRankSignalReport(_BaseReport):
    report_id: str = Field(..., min_length=1)
    signals: list[CanonicalRankSignal] = Field(default_factory=list)

    @field_validator("report_id", mode="before")
    @classmethod
    def normalize_id(cls, value):
        return _upper_required(value, "report_id")

    @model_validator(mode="after")
    def validate_report(self):
        return _validate_safety_flags(self, "kiwoom rest canonical rank signal report")


class KiwoomRestCanonicalOutlierSignalReport(_BaseReport):
    report_id: str = Field(..., min_length=1)
    signals: list[CanonicalOutlierMomentumSignal] = Field(default_factory=list)

    @field_validator("report_id", mode="before")
    @classmethod
    def normalize_id(cls, value):
        return _upper_required(value, "report_id")

    @model_validator(mode="after")
    def validate_report(self):
        return _validate_safety_flags(self, "kiwoom rest canonical outlier signal report")


class KiwoomRestRankContinuationReport(_BaseReport):
    report_id: str = Field(..., min_length=1)
    continuation: KiwoomRestRankContinuation
    has_more: bool = False

    @field_validator("report_id", mode="before")
    @classmethod
    def normalize_id(cls, value):
        return _upper_required(value, "report_id")

    @model_validator(mode="after")
    def validate_report(self):
        return _validate_safety_flags(self, "kiwoom rest rank continuation report")


class KiwoomRestRankV7IntegrationReport(_BaseReport):
    report_id: str = Field(..., min_length=1)
    v712_breadth_routing_ready: bool = False
    v710_price_liquidity_hints_ready: bool = False
    canonical_fields_present: bool = False
    future_supported_api_ids: list[str] = Field(default_factory=list)
    request_builder_ready_api_ids: list[str] = Field(default_factory=list)

    @field_validator("report_id", mode="before")
    @classmethod
    def normalize_id(cls, value):
        return _upper_required(value, "report_id")

    @field_validator("future_supported_api_ids", "request_builder_ready_api_ids", mode="before")
    @classmethod
    def normalize_lists(cls, value, info):
        return _normalize_list(value, info.field_name)

    @model_validator(mode="after")
    def validate_report(self):
        return _validate_safety_flags(self, "kiwoom rest rank v7 integration report")


class KiwoomRestRankSummaryReport(_BaseReport):
    report_id: str = Field(..., min_length=1)
    readiness: KiwoomRestRankReadiness
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
        return _validate_safety_flags(self, "kiwoom rest rank summary report")


class KiwoomRestRankConfig(_BaseReport):
    config_id: str = Field(..., min_length=1)
    provider: str = "KIWOOM_REST"
    mode: KiwoomRestRankMode = KiwoomRestRankMode.MOCKED_TRANSPORT_ONLY
    api_id: KiwoomRestRankApiId
    available_at: datetime | None = None
    source_ref: str = Field(..., min_length=1)
    token_ref: str = "TOKEN_REF_ONLY"
    continuation: KiwoomRestRankContinuation = Field(default_factory=KiwoomRestRankContinuation)
    max_pages: int = Field(default=1, ge=1)
    timeout_policy: str = "MOCKED_TRANSPORT_ONLY"
    retry_policy: str = "NO_RETRY"
    qry_tp: str | None = None
    mrkt_tp: str | None = None
    sort_tp: str | None = None
    tm_tp: str | None = None
    trde_qty_tp: str | None = None
    tm: str | None = None
    stk_cnd: str | None = None
    pric_tp: str | None = None
    stex_tp: str | None = None
    mang_stk_incls: str | None = None
    crd_tp: str | None = None
    mocked_response_payload: dict[str, object] | None = None
    safety_report: KiwoomRestRankSafetyReport
    audit_records: list[KiwoomRestRankAuditRecord] = Field(default_factory=list)

    @field_validator(
        "config_id",
        "qry_tp",
        "mrkt_tp",
        "sort_tp",
        "tm_tp",
        "trde_qty_tp",
        "tm",
        "stk_cnd",
        "pric_tp",
        "stex_tp",
        "mang_stk_incls",
        "crd_tp",
        mode="before",
    )
    @classmethod
    def normalize_optionals(cls, value, info):
        if value is None and info.field_name != "config_id":
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
        _validate_safety_flags(self, "kiwoom rest rank config")
        if self.api_id == KiwoomRestRankApiId.KA00198 and self.qry_tp is None:
            raise ValueError("ka00198 requires qry_tp")
        if self.api_id == KiwoomRestRankApiId.KA10023:
            for field_name in ("mrkt_tp", "sort_tp", "tm_tp", "trde_qty_tp", "tm", "stk_cnd", "pric_tp", "stex_tp"):
                if getattr(self, field_name) is None:
                    raise ValueError(f"ka10023 requires {field_name}")
        if self.api_id == KiwoomRestRankApiId.KA10030:
            for field_name in ("mrkt_tp", "sort_tp", "mang_stk_incls", "crd_tp", "trde_qty_tp", "pric_tp", "stex_tp"):
                if getattr(self, field_name) is None:
                    raise ValueError(f"ka10030 requires {field_name}")
        if self.api_id == KiwoomRestRankApiId.KA10032:
            for field_name in ("mrkt_tp", "mang_stk_incls", "stex_tp"):
                if getattr(self, field_name) is None:
                    raise ValueError(f"ka10032 requires {field_name}")
        return self


class KiwoomRestRankAdapterResult(_BaseReport):
    adapter_result_id: str = Field(..., min_length=1)
    request: KiwoomRestRankRequest
    summary_report: KiwoomRestRankSummaryReport
    request_report: KiwoomRestRankRequestReport
    mocked_response_report: KiwoomRestRankMockedResponseReport
    canonical_rank_report: KiwoomRestCanonicalRankSignalReport
    canonical_outlier_report: KiwoomRestCanonicalOutlierSignalReport
    continuation_report: KiwoomRestRankContinuationReport
    safety_report: KiwoomRestRankSafetyReport
    v7_integration_report: KiwoomRestRankV7IntegrationReport
    gap_report: KiwoomRestRankGapReport
    audit_records: list[KiwoomRestRankAuditRecord] = Field(default_factory=list)

    @field_validator("adapter_result_id", mode="before")
    @classmethod
    def normalize_id(cls, value):
        return _upper_required(value, "adapter_result_id")

    @model_validator(mode="after")
    def validate_result(self):
        return _validate_safety_flags(self, "kiwoom rest rank adapter result")
