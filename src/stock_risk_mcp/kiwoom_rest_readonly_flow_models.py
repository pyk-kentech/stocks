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


class KiwoomRestFlowApiId(StrEnum):
    KA10008 = "KA10008"
    KA10014 = "KA10014"
    KA10058 = "KA10058"
    KA10059 = "KA10059"
    KA10060 = "KA10060"
    KA10061 = "KA10061"
    KA10063 = "KA10063"
    KA10064 = "KA10064"
    KA10065 = "KA10065"
    KA10066 = "KA10066"
    KA10068 = "KA10068"
    KA10069 = "KA10069"
    KA90003 = "KA90003"
    KA90004 = "KA90004"
    KA90005 = "KA90005"
    KA90007 = "KA90007"
    KA90008 = "KA90008"
    KA90009 = "KA90009"
    KA90010 = "KA90010"
    KA90012 = "KA90012"
    KA90013 = "KA90013"


class KiwoomRestFlowReadiness(StrEnum):
    MOCKED_TRANSPORT_READY = "MOCKED_TRANSPORT_READY"
    CANONICAL_FLOW_READY = "CANONICAL_FLOW_READY"
    INVESTOR_FLOW_READY = "INVESTOR_FLOW_READY"
    PROGRAM_FLOW_READY = "PROGRAM_FLOW_READY"
    SHORT_LENDING_CAPABILITY_MAPPED = "SHORT_LENDING_CAPABILITY_MAPPED"
    READONLY_ADAPTER_READY = "READONLY_ADAPTER_READY"
    DATA_GAP = "DATA_GAP"
    SCHEMA_GAP = "SCHEMA_GAP"
    FUTURE_SUPPORTED = "FUTURE_SUPPORTED"
    BLOCKED = "BLOCKED"
    REJECTED = "REJECTED"


class KiwoomRestFlowMode(StrEnum):
    MOCKED_TRANSPORT_ONLY = "MOCKED_TRANSPORT_ONLY"


class CanonicalFlowCategory(StrEnum):
    FOREIGN = "FOREIGN"
    INSTITUTION = "INSTITUTION"
    RETAIL = "RETAIL"
    PROGRAM = "PROGRAM"
    SHORT_SELLING = "SHORT_SELLING"
    SECURITIES_LENDING = "SECURITIES_LENDING"
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


class KiwoomRestFlowContinuation(StrictModel):
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


class KiwoomRestInvestorFlowItem(StrictModel):
    observed_at: datetime
    provider_symbol: str = Field(..., min_length=1)
    stock_name: str | None = None
    current_price: float | None = None
    price_change: float | None = None
    foreign_net_amount: float | None = None
    institution_net_amount: float | None = None
    retail_net_amount: float | None = None
    foreign_net_quantity: float | None = None
    institution_net_quantity: float | None = None
    retail_net_quantity: float | None = None

    @field_validator("observed_at", mode="before")
    @classmethod
    def normalize_observed_at(cls, value):
        parsed = _aware(value)
        if parsed is None:
            raise ValueError("observed_at must not be null")
        return parsed

    @field_validator("provider_symbol", mode="before")
    @classmethod
    def normalize_symbol(cls, value):
        return _upper_required(value, "provider_symbol")

    @field_validator("stock_name", mode="before")
    @classmethod
    def normalize_stock_name(cls, value):
        if value in (None, ""):
            return None
        return _string_required(value, "stock_name")

    @field_validator(
        "current_price",
        "price_change",
        "foreign_net_amount",
        "institution_net_amount",
        "retail_net_amount",
        "foreign_net_quantity",
        "institution_net_quantity",
        "retail_net_quantity",
        mode="before",
    )
    @classmethod
    def normalize_numbers(cls, value, info):
        return _normalize_optional_number(value, info.field_name)


class KiwoomRestProgramFlowItem(StrictModel):
    observed_at: datetime | None = None
    provider_symbol: str | None = None
    stock_name: str | None = None
    accumulated_trade_quantity: float | None = Field(default=None, ge=0)
    program_sell_amount: float | None = None
    program_buy_amount: float | None = None
    program_net_amount: float | None = None

    @field_validator("observed_at", mode="before")
    @classmethod
    def normalize_observed_at(cls, value):
        return _aware(value)

    @field_validator("provider_symbol", mode="before")
    @classmethod
    def normalize_symbol(cls, value):
        if value in (None, ""):
            return None
        return _upper_required(value, "provider_symbol")

    @field_validator("stock_name", mode="before")
    @classmethod
    def normalize_stock_name(cls, value):
        if value in (None, ""):
            return None
        return _string_required(value, "stock_name")

    @field_validator(
        "accumulated_trade_quantity",
        "program_sell_amount",
        "program_buy_amount",
        "program_net_amount",
        mode="before",
    )
    @classmethod
    def normalize_numbers(cls, value, info):
        return _normalize_optional_number(value, info.field_name)


class KiwoomRestShortSellingItem(StrictModel):
    capability_id: str = Field(..., min_length=1)
    api_id: KiwoomRestFlowApiId
    request_builder_ready: bool = False
    schema_evidence_available: bool = False

    @field_validator("capability_id", mode="before")
    @classmethod
    def normalize_id(cls, value):
        return _upper_required(value, "capability_id")


class KiwoomRestLendingItem(StrictModel):
    capability_id: str = Field(..., min_length=1)
    api_id: KiwoomRestFlowApiId
    request_builder_ready: bool = False
    schema_evidence_available: bool = False

    @field_validator("capability_id", mode="before")
    @classmethod
    def normalize_id(cls, value):
        return _upper_required(value, "capability_id")


class KiwoomRestFlowRequest(_BaseReport):
    request_id: str = Field(..., min_length=1)
    provider: str = "KIWOOM_REST"
    mode: KiwoomRestFlowMode = KiwoomRestFlowMode.MOCKED_TRANSPORT_ONLY
    domain_ref: str = "https://api.kiwoom.com"
    mock_domain_ref: str = "https://mockapi.kiwoom.com"
    method: str = "POST"
    path: str | None = None
    api_id: KiwoomRestFlowApiId
    token_ref: str = "TOKEN_REF_ONLY"
    continuation: KiwoomRestFlowContinuation = Field(default_factory=KiwoomRestFlowContinuation)
    request_headers: dict[str, str] = Field(default_factory=dict)
    request_body: dict[str, str] = Field(default_factory=dict)

    @field_validator("request_id", mode="before")
    @classmethod
    def normalize_id(cls, value):
        return _upper_required(value, "request_id")

    @field_validator("path", mode="before")
    @classmethod
    def normalize_path(cls, value):
        if value in (None, ""):
            return None
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
        _validate_safety_flags(self, "kiwoom rest flow request")
        if self.request_headers and self.request_headers.get("authorization") != "Bearer <TOKEN_REF_ONLY>":
            raise ValueError("authorization header must remain token-ref-only")
        return self


class KiwoomRestFlowResponse(_BaseReport):
    response_id: str = Field(..., min_length=1)
    api_id: KiwoomRestFlowApiId
    return_code: int
    return_msg: str = Field(..., min_length=1)
    investor_items: list[KiwoomRestInvestorFlowItem] = Field(default_factory=list)
    program_items: list[KiwoomRestProgramFlowItem] = Field(default_factory=list)
    continuation: KiwoomRestFlowContinuation = Field(default_factory=KiwoomRestFlowContinuation)
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
        return _validate_safety_flags(self, "kiwoom rest flow response")


class KiwoomRestFlowSafetyReport(_BaseReport):
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
        return _validate_safety_flags(self, "kiwoom rest flow safety report")


class KiwoomRestFlowGapEntry(StrictModel):
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


class KiwoomRestFlowGapReport(_BaseReport):
    gap_report_id: str = Field(..., min_length=1)
    readiness: KiwoomRestFlowReadiness
    gap_entries: list[KiwoomRestFlowGapEntry] = Field(default_factory=list)

    @field_validator("gap_report_id", mode="before")
    @classmethod
    def normalize_id(cls, value):
        return _upper_required(value, "gap_report_id")

    @model_validator(mode="after")
    def validate_report(self):
        return _validate_safety_flags(self, "kiwoom rest flow gap report")


class KiwoomRestFlowAuditRecord(StrictModel):
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


class _CanonicalFlowBase(_BaseReport):
    provider: str = "KIWOOM_REST"
    provider_api_id: str = Field(..., min_length=1)
    canonical_instrument_key: str | None = None
    provider_symbol: str | None = None
    stock_name: str | None = None
    market: str = "KR"
    currency: str = "KRW"
    observed_at: datetime
    available_at: datetime | None = None
    flow_category: CanonicalFlowCategory = CanonicalFlowCategory.UNKNOWN
    buy_amount: float | None = None
    sell_amount: float | None = None
    net_buy_amount: float | None = None
    buy_quantity: float | None = None
    sell_quantity: float | None = None
    net_buy_quantity: float | None = None
    short_selling_amount: float | None = None
    short_selling_volume: float | None = None
    lending_balance: float | None = None
    lending_transaction: float | None = None
    program_buy_amount: float | None = None
    program_sell_amount: float | None = None
    program_net_amount: float | None = None
    confidence_flags: list[str] = Field(default_factory=list)
    source_ref: str = Field(..., min_length=1)
    quality_flags: list[str] = Field(default_factory=list)
    stale_flag: bool = False
    gap_reason: str | None = None

    @field_validator("provider_api_id", "canonical_instrument_key", "provider_symbol", "gap_reason", mode="before")
    @classmethod
    def normalize_upper_optional(cls, value, info):
        if value is None and info.field_name in {"canonical_instrument_key", "provider_symbol", "gap_reason"}:
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

    @field_validator("confidence_flags", "quality_flags", mode="before")
    @classmethod
    def normalize_lists(cls, value, info):
        return _normalize_list(value, info.field_name)

    @field_validator(
        "buy_amount",
        "sell_amount",
        "net_buy_amount",
        "buy_quantity",
        "sell_quantity",
        "net_buy_quantity",
        "short_selling_amount",
        "short_selling_volume",
        "lending_balance",
        "lending_transaction",
        "program_buy_amount",
        "program_sell_amount",
        "program_net_amount",
        mode="before",
    )
    @classmethod
    def normalize_numbers(cls, value, info):
        return _normalize_optional_number(value, info.field_name)

    @model_validator(mode="after")
    def validate_record(self):
        return _validate_safety_flags(self, "canonical flow signal")


class CanonicalFlowSignal(_CanonicalFlowBase):
    pass


class CanonicalInvestorFlowSignal(_CanonicalFlowBase):
    pass


class CanonicalShortSellingSignal(_CanonicalFlowBase):
    pass


class CanonicalLendingSignal(_CanonicalFlowBase):
    pass


class CanonicalProgramTradingSignal(_CanonicalFlowBase):
    pass


class KiwoomRestFlowRequestReport(_BaseReport):
    report_id: str = Field(..., min_length=1)
    request: KiwoomRestFlowRequest

    @field_validator("report_id", mode="before")
    @classmethod
    def normalize_id(cls, value):
        return _upper_required(value, "report_id")

    @model_validator(mode="after")
    def validate_report(self):
        return _validate_safety_flags(self, "kiwoom rest flow request report")


class KiwoomRestFlowMockedResponseReport(_BaseReport):
    report_id: str = Field(..., min_length=1)
    response: KiwoomRestFlowResponse

    @field_validator("report_id", mode="before")
    @classmethod
    def normalize_id(cls, value):
        return _upper_required(value, "report_id")

    @model_validator(mode="after")
    def validate_report(self):
        return _validate_safety_flags(self, "kiwoom rest flow mocked response report")


class KiwoomRestCanonicalInvestorFlowReport(_BaseReport):
    report_id: str = Field(..., min_length=1)
    signals: list[CanonicalInvestorFlowSignal] = Field(default_factory=list)

    @field_validator("report_id", mode="before")
    @classmethod
    def normalize_id(cls, value):
        return _upper_required(value, "report_id")

    @model_validator(mode="after")
    def validate_report(self):
        return _validate_safety_flags(self, "kiwoom rest canonical investor flow report")


class KiwoomRestCanonicalProgramFlowReport(_BaseReport):
    report_id: str = Field(..., min_length=1)
    signals: list[CanonicalProgramTradingSignal] = Field(default_factory=list)

    @field_validator("report_id", mode="before")
    @classmethod
    def normalize_id(cls, value):
        return _upper_required(value, "report_id")

    @model_validator(mode="after")
    def validate_report(self):
        return _validate_safety_flags(self, "kiwoom rest canonical program flow report")


class KiwoomRestShortLendingCapabilityReport(_BaseReport):
    report_id: str = Field(..., min_length=1)
    short_selling_capabilities: list[KiwoomRestShortSellingItem] = Field(default_factory=list)
    lending_capabilities: list[KiwoomRestLendingItem] = Field(default_factory=list)

    @field_validator("report_id", mode="before")
    @classmethod
    def normalize_id(cls, value):
        return _upper_required(value, "report_id")

    @model_validator(mode="after")
    def validate_report(self):
        return _validate_safety_flags(self, "kiwoom rest short lending capability report")


class KiwoomRestFlowCapabilityMatrixEntry(StrictModel):
    api_id: KiwoomRestFlowApiId
    capability_group: str = Field(..., min_length=1)
    request_builder_ready: bool = False
    readiness: KiwoomRestFlowReadiness

    @field_validator("capability_group", mode="before")
    @classmethod
    def normalize_group(cls, value):
        return _upper_required(value, "capability_group")


class KiwoomRestFlowCapabilityMatrixReport(_BaseReport):
    report_id: str = Field(..., min_length=1)
    entries: list[KiwoomRestFlowCapabilityMatrixEntry] = Field(default_factory=list)

    @field_validator("report_id", mode="before")
    @classmethod
    def normalize_id(cls, value):
        return _upper_required(value, "report_id")

    @model_validator(mode="after")
    def validate_report(self):
        return _validate_safety_flags(self, "kiwoom rest flow capability matrix report")


class KiwoomRestFlowContinuationReport(_BaseReport):
    report_id: str = Field(..., min_length=1)
    continuation: KiwoomRestFlowContinuation
    has_more: bool = False

    @field_validator("report_id", mode="before")
    @classmethod
    def normalize_id(cls, value):
        return _upper_required(value, "report_id")

    @model_validator(mode="after")
    def validate_report(self):
        return _validate_safety_flags(self, "kiwoom rest flow continuation report")


class KiwoomRestFlowV7IntegrationReport(_BaseReport):
    report_id: str = Field(..., min_length=1)
    v712_flow_program_ready: bool = False
    v710_risk_liquidity_hints_ready: bool = False
    canonical_fields_present: bool = False

    @field_validator("report_id", mode="before")
    @classmethod
    def normalize_id(cls, value):
        return _upper_required(value, "report_id")

    @model_validator(mode="after")
    def validate_report(self):
        return _validate_safety_flags(self, "kiwoom rest flow v7 integration report")


class KiwoomRestFlowSummaryReport(_BaseReport):
    report_id: str = Field(..., min_length=1)
    readiness: KiwoomRestFlowReadiness
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
        return _validate_safety_flags(self, "kiwoom rest flow summary report")


class KiwoomRestFlowConfig(_BaseReport):
    config_id: str = Field(..., min_length=1)
    provider: str = "KIWOOM_REST"
    mode: KiwoomRestFlowMode = KiwoomRestFlowMode.MOCKED_TRANSPORT_ONLY
    api_id: KiwoomRestFlowApiId
    path_hint: str | None = None
    provider_symbol: str | None = None
    request_date: str | None = None
    available_at: datetime | None = None
    source_ref: str = Field(..., min_length=1)
    token_ref: str = "TOKEN_REF_ONLY"
    continuation: KiwoomRestFlowContinuation = Field(default_factory=KiwoomRestFlowContinuation)
    max_pages: int = Field(default=1, ge=1)
    timeout_policy: str = "MOCKED_TRANSPORT_ONLY"
    retry_policy: str = "NO_RETRY"
    amt_qty_tp: str | None = None
    trde_tp: str | None = None
    unit_tp: str | None = None
    trde_upper_tp: str | None = None
    mrkt_tp: str | None = None
    stex_tp: str | None = None
    mocked_response_payload: dict[str, object] | None = None
    safety_report: KiwoomRestFlowSafetyReport
    audit_records: list[KiwoomRestFlowAuditRecord] = Field(default_factory=list)

    @field_validator(
        "config_id",
        "provider_symbol",
        "request_date",
        "amt_qty_tp",
        "trde_tp",
        "unit_tp",
        "trde_upper_tp",
        "mrkt_tp",
        "stex_tp",
        mode="before",
    )
    @classmethod
    def normalize_optionals(cls, value, info):
        if value is None and info.field_name != "config_id":
            return None
        return _upper_required(value, info.field_name)

    @field_validator("path_hint", mode="before")
    @classmethod
    def normalize_path_hint(cls, value):
        if value in (None, ""):
            return None
        return _string_required(value, "path_hint")

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
        _validate_safety_flags(self, "kiwoom rest flow config")
        if self.api_id == KiwoomRestFlowApiId.KA10059:
            for field_name in ("request_date", "provider_symbol", "amt_qty_tp", "trde_tp", "unit_tp"):
                if getattr(self, field_name) is None:
                    raise ValueError(f"ka10059 requires {field_name}")
        if self.api_id == KiwoomRestFlowApiId.KA90003:
            for field_name in ("trde_upper_tp", "amt_qty_tp", "mrkt_tp", "stex_tp"):
                if getattr(self, field_name) is None:
                    raise ValueError(f"ka90003 requires {field_name}")
        return self


class KiwoomRestFlowAdapterResult(_BaseReport):
    adapter_result_id: str = Field(..., min_length=1)
    request: KiwoomRestFlowRequest
    summary_report: KiwoomRestFlowSummaryReport
    request_report: KiwoomRestFlowRequestReport
    mocked_response_report: KiwoomRestFlowMockedResponseReport
    canonical_investor_flow_report: KiwoomRestCanonicalInvestorFlowReport
    canonical_program_flow_report: KiwoomRestCanonicalProgramFlowReport
    short_lending_capability_report: KiwoomRestShortLendingCapabilityReport
    flow_capability_matrix_report: KiwoomRestFlowCapabilityMatrixReport
    continuation_report: KiwoomRestFlowContinuationReport
    safety_report: KiwoomRestFlowSafetyReport
    v7_integration_report: KiwoomRestFlowV7IntegrationReport
    gap_report: KiwoomRestFlowGapReport
    audit_records: list[KiwoomRestFlowAuditRecord] = Field(default_factory=list)

    @field_validator("adapter_result_id", mode="before")
    @classmethod
    def normalize_id(cls, value):
        return _upper_required(value, "adapter_result_id")

    @model_validator(mode="after")
    def validate_result(self):
        return _validate_safety_flags(self, "kiwoom rest flow adapter result")
