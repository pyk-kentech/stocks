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


class KiwoomRestSectorApiId(StrEnum):
    KA20001 = "KA20001"
    KA20002 = "KA20002"
    KA20003 = "KA20003"
    KA20004 = "KA20004"
    KA20005 = "KA20005"
    KA20006 = "KA20006"
    KA20007 = "KA20007"
    KA20008 = "KA20008"
    KA20009 = "KA20009"
    KA20019 = "KA20019"
    KA40001 = "KA40001"
    KA40002 = "KA40002"
    KA40003 = "KA40003"
    KA40004 = "KA40004"
    KA40006 = "KA40006"
    KA40007 = "KA40007"
    KA40008 = "KA40008"
    KA40009 = "KA40009"
    KA40010 = "KA40010"
    KA90001 = "KA90001"
    KA90002 = "KA90002"


class KiwoomRestSectorReadiness(StrEnum):
    MOCKED_TRANSPORT_READY = "MOCKED_TRANSPORT_READY"
    THEME_LEADERSHIP_READY = "THEME_LEADERSHIP_READY"
    THEME_MEMBERSHIP_READY = "THEME_MEMBERSHIP_READY"
    ETF_TREND_READY = "ETF_TREND_READY"
    SECTOR_CAPABILITY_MAPPED = "SECTOR_CAPABILITY_MAPPED"
    READONLY_ADAPTER_READY = "READONLY_ADAPTER_READY"
    DATA_GAP = "DATA_GAP"
    SCHEMA_GAP = "SCHEMA_GAP"
    FUTURE_SUPPORTED = "FUTURE_SUPPORTED"
    BLOCKED = "BLOCKED"
    REJECTED = "REJECTED"


class KiwoomRestSectorMode(StrEnum):
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


class KiwoomRestSectorContinuation(StrictModel):
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


class KiwoomRestThemeGroupItem(StrictModel):
    theme_group_code: str = Field(..., min_length=1)
    theme_name: str = Field(..., min_length=1)
    stock_count: int | None = Field(default=None, ge=0)
    change_sign: str | None = None
    change_rate: float | None = None
    rising_stock_count: int | None = Field(default=None, ge=0)
    falling_stock_count: int | None = Field(default=None, ge=0)
    period_return: float | None = None
    main_stock: str | None = None

    @field_validator("theme_group_code", mode="before")
    @classmethod
    def normalize_code(cls, value):
        return _upper_required(value, "theme_group_code")

    @field_validator("theme_name", "change_sign", "main_stock", mode="before")
    @classmethod
    def normalize_optional_text(cls, value, info):
        if value in (None, "") and info.field_name in {"change_sign", "main_stock"}:
            return None
        return _string_required(value, info.field_name) if value not in (None, "") else None

    @field_validator("stock_count", "rising_stock_count", "falling_stock_count", mode="before")
    @classmethod
    def normalize_ints(cls, value, info):
        if value in (None, ""):
            return None
        return int(_normalize_number(value, info.field_name))

    @field_validator("change_rate", "period_return", mode="before")
    @classmethod
    def normalize_numbers(cls, value, info):
        return _normalize_optional_number(value, info.field_name)


class KiwoomRestThemeComponentItem(StrictModel):
    theme_group_code: str = Field(..., min_length=1)
    theme_name: str | None = None
    component_stock_code: str | None = None
    component_stock_name: str | None = None
    component_change_rate: float | None = None
    component_return: float | None = None
    membership_evidence_flag: bool = False

    @field_validator("theme_group_code", mode="before")
    @classmethod
    def normalize_code(cls, value):
        return _upper_required(value, "theme_group_code")

    @field_validator("theme_name", "component_stock_code", "component_stock_name", mode="before")
    @classmethod
    def normalize_optional_text(cls, value):
        if value in (None, ""):
            return None
        return _string_required(value, "field")

    @field_validator("component_change_rate", "component_return", mode="before")
    @classmethod
    def normalize_numbers(cls, value, info):
        return _normalize_optional_number(value, info.field_name)


class KiwoomRestEtfTrendItem(StrictModel):
    etf_stock_code: str = Field(..., min_length=1)
    observed_at: datetime
    price: float | None = None
    previous_close_diff: float | None = None
    percent_change: float | None = None

    @field_validator("etf_stock_code", mode="before")
    @classmethod
    def normalize_code(cls, value):
        return _upper_required(value, "etf_stock_code")

    @field_validator("observed_at", mode="before")
    @classmethod
    def normalize_observed_at(cls, value):
        parsed = _aware(value)
        if parsed is None:
            raise ValueError("observed_at must not be null")
        return parsed

    @field_validator("price", "previous_close_diff", "percent_change", mode="before")
    @classmethod
    def normalize_numbers(cls, value, info):
        return _normalize_optional_number(value, info.field_name)


class KiwoomRestSectorCapabilityItem(StrictModel):
    api_id: KiwoomRestSectorApiId
    capability_group: str = Field(..., min_length=1)
    request_builder_ready: bool = False
    readiness: KiwoomRestSectorReadiness

    @field_validator("capability_group", mode="before")
    @classmethod
    def normalize_group(cls, value):
        return _upper_required(value, "capability_group")


class KiwoomRestSectorRequest(_BaseReport):
    request_id: str = Field(..., min_length=1)
    provider: str = "KIWOOM_REST"
    mode: KiwoomRestSectorMode = KiwoomRestSectorMode.MOCKED_TRANSPORT_ONLY
    domain_ref: str = "https://api.kiwoom.com"
    mock_domain_ref: str = "https://mockapi.kiwoom.com"
    method: str = "POST"
    path: str | None = None
    api_id: KiwoomRestSectorApiId
    token_ref: str = "TOKEN_REF_ONLY"
    continuation: KiwoomRestSectorContinuation = Field(default_factory=KiwoomRestSectorContinuation)
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
        _validate_safety_flags(self, "kiwoom rest sector request")
        if self.request_headers and self.request_headers.get("authorization") != "Bearer <TOKEN_REF_ONLY>":
            raise ValueError("authorization header must remain token-ref-only")
        return self


class KiwoomRestSectorResponse(_BaseReport):
    response_id: str = Field(..., min_length=1)
    api_id: KiwoomRestSectorApiId
    return_code: int
    return_msg: str = Field(..., min_length=1)
    theme_groups: list[KiwoomRestThemeGroupItem] = Field(default_factory=list)
    theme_components: list[KiwoomRestThemeComponentItem] = Field(default_factory=list)
    etf_trends: list[KiwoomRestEtfTrendItem] = Field(default_factory=list)
    continuation: KiwoomRestSectorContinuation = Field(default_factory=KiwoomRestSectorContinuation)
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
        return _validate_safety_flags(self, "kiwoom rest sector response")


class KiwoomRestSectorSafetyReport(_BaseReport):
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
        return _validate_safety_flags(self, "kiwoom rest sector safety report")


class KiwoomRestSectorGapEntry(StrictModel):
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


class KiwoomRestSectorGapReport(_BaseReport):
    gap_report_id: str = Field(..., min_length=1)
    readiness: KiwoomRestSectorReadiness
    gap_entries: list[KiwoomRestSectorGapEntry] = Field(default_factory=list)

    @field_validator("gap_report_id", mode="before")
    @classmethod
    def normalize_id(cls, value):
        return _upper_required(value, "gap_report_id")

    @model_validator(mode="after")
    def validate_report(self):
        return _validate_safety_flags(self, "kiwoom rest sector gap report")


class KiwoomRestSectorAuditRecord(StrictModel):
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


class CanonicalThemeLeadershipSignal(_BaseReport):
    provider: str = "KIWOOM_REST"
    provider_api_id: str = Field(..., min_length=1)
    theme_group_code: str = Field(..., min_length=1)
    theme_name: str = Field(..., min_length=1)
    stock_count: int | None = Field(default=None, ge=0)
    rising_stock_count: int | None = Field(default=None, ge=0)
    falling_stock_count: int | None = Field(default=None, ge=0)
    theme_change_rate: float | None = None
    period_return: float | None = None
    main_stock: str | None = None
    participation_hint: float | None = None
    concentration_hint: float | None = None
    observed_at: datetime
    available_at: datetime | None = None
    source_ref: str = Field(..., min_length=1)
    quality_flags: list[str] = Field(default_factory=list)
    stale_flag: bool = False
    gap_reason: str | None = None

    @field_validator("provider_api_id", "theme_group_code", "gap_reason", mode="before")
    @classmethod
    def normalize_upper_optional(cls, value, info):
        if value is None and info.field_name == "gap_reason":
            return None
        return _upper_required(value, info.field_name)

    @field_validator("theme_name", "main_stock", mode="before")
    @classmethod
    def normalize_optional_text(cls, value, info):
        if value in (None, "") and info.field_name == "main_stock":
            return None
        return _string_required(value, info.field_name) if value not in (None, "") else None

    @field_validator("stock_count", "rising_stock_count", "falling_stock_count", mode="before")
    @classmethod
    def normalize_ints(cls, value, info):
        if value in (None, ""):
            return None
        return int(_normalize_number(value, info.field_name))

    @field_validator("theme_change_rate", "period_return", "participation_hint", "concentration_hint", mode="before")
    @classmethod
    def normalize_numbers(cls, value, info):
        return _normalize_optional_number(value, info.field_name)

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

    @model_validator(mode="after")
    def validate_record(self):
        return _validate_safety_flags(self, "canonical theme leadership signal")


class CanonicalThemeMembershipSignal(_BaseReport):
    provider: str = "KIWOOM_REST"
    provider_api_id: str = Field(..., min_length=1)
    theme_group_code: str = Field(..., min_length=1)
    theme_name: str | None = None
    component_stock_code: str | None = None
    component_stock_name: str | None = None
    component_change_rate: float | None = None
    component_return: float | None = None
    membership_evidence_flag: bool = False
    observed_at: datetime
    available_at: datetime | None = None
    source_ref: str = Field(..., min_length=1)
    gap_reason: str | None = None

    @field_validator("provider_api_id", "theme_group_code", "component_stock_code", "gap_reason", mode="before")
    @classmethod
    def normalize_upper_optional(cls, value, info):
        if value is None and info.field_name in {"component_stock_code", "gap_reason"}:
            return None
        return _upper_required(value, info.field_name)

    @field_validator("theme_name", "component_stock_name", mode="before")
    @classmethod
    def normalize_optional_text(cls, value):
        if value in (None, ""):
            return None
        return _string_required(value, "field")

    @field_validator("component_change_rate", "component_return", mode="before")
    @classmethod
    def normalize_numbers(cls, value, info):
        return _normalize_optional_number(value, info.field_name)

    @field_validator("observed_at", "available_at", mode="before")
    @classmethod
    def normalize_datetimes(cls, value):
        return _aware(value)

    @field_validator("source_ref", mode="before")
    @classmethod
    def normalize_source_ref(cls, value):
        return _validate_local_path(value, "source_ref")

    @model_validator(mode="after")
    def validate_record(self):
        return _validate_safety_flags(self, "canonical theme membership signal")


class CanonicalEtfTrendSignal(_BaseReport):
    provider: str = "KIWOOM_REST"
    provider_api_id: str = Field(..., min_length=1)
    etf_stock_code: str = Field(..., min_length=1)
    date: str = Field(..., min_length=8, max_length=8)
    price: float | None = None
    previous_close_difference: float | None = None
    percent_change: float | None = None
    trend_direction: str | None = None
    observed_at: datetime
    available_at: datetime | None = None
    source_ref: str = Field(..., min_length=1)
    quality_flags: list[str] = Field(default_factory=list)
    stale_flag: bool = False
    gap_reason: str | None = None

    @field_validator("provider_api_id", "etf_stock_code", "date", "trend_direction", "gap_reason", mode="before")
    @classmethod
    def normalize_upper_optional(cls, value, info):
        if value is None and info.field_name in {"trend_direction", "gap_reason"}:
            return None
        return _upper_required(value, info.field_name)

    @field_validator("price", "previous_close_difference", "percent_change", mode="before")
    @classmethod
    def normalize_numbers(cls, value, info):
        return _normalize_optional_number(value, info.field_name)

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

    @model_validator(mode="after")
    def validate_record(self):
        return _validate_safety_flags(self, "canonical etf trend signal")


class CanonicalSectorCapabilitySignal(_BaseReport):
    provider: str = "KIWOOM_REST"
    api_id: KiwoomRestSectorApiId
    capability_group: str = Field(..., min_length=1)
    request_builder_ready: bool = False
    readiness: KiwoomRestSectorReadiness

    @field_validator("capability_group", mode="before")
    @classmethod
    def normalize_group(cls, value):
        return _upper_required(value, "capability_group")

    @model_validator(mode="after")
    def validate_record(self):
        return _validate_safety_flags(self, "canonical sector capability signal")


class KiwoomRestSectorRequestReport(_BaseReport):
    report_id: str = Field(..., min_length=1)
    request: KiwoomRestSectorRequest

    @field_validator("report_id", mode="before")
    @classmethod
    def normalize_id(cls, value):
        return _upper_required(value, "report_id")

    @model_validator(mode="after")
    def validate_report(self):
        return _validate_safety_flags(self, "kiwoom rest sector request report")


class KiwoomRestSectorMockedResponseReport(_BaseReport):
    report_id: str = Field(..., min_length=1)
    response: KiwoomRestSectorResponse

    @field_validator("report_id", mode="before")
    @classmethod
    def normalize_id(cls, value):
        return _upper_required(value, "report_id")

    @model_validator(mode="after")
    def validate_report(self):
        return _validate_safety_flags(self, "kiwoom rest sector mocked response report")


class KiwoomRestCanonicalThemeLeadershipReport(_BaseReport):
    report_id: str = Field(..., min_length=1)
    signals: list[CanonicalThemeLeadershipSignal] = Field(default_factory=list)

    @field_validator("report_id", mode="before")
    @classmethod
    def normalize_id(cls, value):
        return _upper_required(value, "report_id")

    @model_validator(mode="after")
    def validate_report(self):
        return _validate_safety_flags(self, "kiwoom rest canonical theme leadership report")


class KiwoomRestCanonicalThemeMembershipReport(_BaseReport):
    report_id: str = Field(..., min_length=1)
    signals: list[CanonicalThemeMembershipSignal] = Field(default_factory=list)

    @field_validator("report_id", mode="before")
    @classmethod
    def normalize_id(cls, value):
        return _upper_required(value, "report_id")

    @model_validator(mode="after")
    def validate_report(self):
        return _validate_safety_flags(self, "kiwoom rest canonical theme membership report")


class KiwoomRestCanonicalEtfTrendReport(_BaseReport):
    report_id: str = Field(..., min_length=1)
    signals: list[CanonicalEtfTrendSignal] = Field(default_factory=list)

    @field_validator("report_id", mode="before")
    @classmethod
    def normalize_id(cls, value):
        return _upper_required(value, "report_id")

    @model_validator(mode="after")
    def validate_report(self):
        return _validate_safety_flags(self, "kiwoom rest canonical etf trend report")


class KiwoomRestSectorEtfCapabilityMatrixReport(_BaseReport):
    report_id: str = Field(..., min_length=1)
    entries: list[CanonicalSectorCapabilitySignal] = Field(default_factory=list)

    @field_validator("report_id", mode="before")
    @classmethod
    def normalize_id(cls, value):
        return _upper_required(value, "report_id")

    @model_validator(mode="after")
    def validate_report(self):
        return _validate_safety_flags(self, "kiwoom rest sector etf capability matrix report")


class KiwoomRestSectorContinuationReport(_BaseReport):
    report_id: str = Field(..., min_length=1)
    continuation: KiwoomRestSectorContinuation
    has_more: bool = False

    @field_validator("report_id", mode="before")
    @classmethod
    def normalize_id(cls, value):
        return _upper_required(value, "report_id")

    @model_validator(mode="after")
    def validate_report(self):
        return _validate_safety_flags(self, "kiwoom rest sector continuation report")


class KiwoomRestSectorV7IntegrationReport(_BaseReport):
    report_id: str = Field(..., min_length=1)
    v712_leadership_membership_etf_ready: bool = False
    v710_etf_liquidity_risk_context_ready: bool = False
    canonical_fields_present: bool = False

    @field_validator("report_id", mode="before")
    @classmethod
    def normalize_id(cls, value):
        return _upper_required(value, "report_id")

    @model_validator(mode="after")
    def validate_report(self):
        return _validate_safety_flags(self, "kiwoom rest sector v7 integration report")


class KiwoomRestSectorSummaryReport(_BaseReport):
    report_id: str = Field(..., min_length=1)
    readiness: KiwoomRestSectorReadiness
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
        return _validate_safety_flags(self, "kiwoom rest sector summary report")


class KiwoomRestSectorConfig(_BaseReport):
    config_id: str = Field(..., min_length=1)
    provider: str = "KIWOOM_REST"
    mode: KiwoomRestSectorMode = KiwoomRestSectorMode.MOCKED_TRANSPORT_ONLY
    api_id: KiwoomRestSectorApiId
    available_at: datetime | None = None
    source_ref: str = Field(..., min_length=1)
    token_ref: str = "TOKEN_REF_ONLY"
    continuation: KiwoomRestSectorContinuation = Field(default_factory=KiwoomRestSectorContinuation)
    max_pages: int = Field(default=1, ge=1)
    timeout_policy: str = "MOCKED_TRANSPORT_ONLY"
    retry_policy: str = "NO_RETRY"
    qry_tp: str | None = None
    provider_symbol: str | None = None
    date_tp: str | None = None
    theme_name: str | None = None
    flu_pl_amt_tp: str | None = None
    stex_tp: str | None = None
    theme_group_code: str | None = None
    mocked_response_payload: dict[str, object] | None = None
    safety_report: KiwoomRestSectorSafetyReport
    audit_records: list[KiwoomRestSectorAuditRecord] = Field(default_factory=list)

    @field_validator(
        "config_id",
        "qry_tp",
        "provider_symbol",
        "date_tp",
        "theme_name",
        "flu_pl_amt_tp",
        "stex_tp",
        "theme_group_code",
        mode="before",
    )
    @classmethod
    def normalize_optionals(cls, value, info):
        if value is None and info.field_name != "config_id":
            return None
        if info.field_name in {"provider_symbol", "theme_name"} and value is not None:
            return str(value).strip().upper()
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
        _validate_safety_flags(self, "kiwoom rest sector config")
        if self.api_id == KiwoomRestSectorApiId.KA90001:
            for field_name in ("qry_tp", "date_tp", "flu_pl_amt_tp", "stex_tp"):
                if getattr(self, field_name) is None:
                    raise ValueError(f"ka90001 requires {field_name}")
        if self.api_id == KiwoomRestSectorApiId.KA90002:
            for field_name in ("date_tp", "theme_group_code", "stex_tp"):
                if getattr(self, field_name) is None:
                    raise ValueError(f"ka90002 requires {field_name}")
        if self.api_id == KiwoomRestSectorApiId.KA40003 and self.provider_symbol is None:
            raise ValueError("ka40003 requires provider_symbol")
        return self


class KiwoomRestSectorAdapterResult(_BaseReport):
    adapter_result_id: str = Field(..., min_length=1)
    request: KiwoomRestSectorRequest
    summary_report: KiwoomRestSectorSummaryReport
    request_report: KiwoomRestSectorRequestReport
    mocked_response_report: KiwoomRestSectorMockedResponseReport
    canonical_theme_leadership_report: KiwoomRestCanonicalThemeLeadershipReport
    canonical_theme_membership_report: KiwoomRestCanonicalThemeMembershipReport
    canonical_etf_trend_report: KiwoomRestCanonicalEtfTrendReport
    sector_etf_capability_matrix_report: KiwoomRestSectorEtfCapabilityMatrixReport
    continuation_report: KiwoomRestSectorContinuationReport
    safety_report: KiwoomRestSectorSafetyReport
    v7_integration_report: KiwoomRestSectorV7IntegrationReport
    gap_report: KiwoomRestSectorGapReport
    audit_records: list[KiwoomRestSectorAuditRecord] = Field(default_factory=list)

    @field_validator("adapter_result_id", mode="before")
    @classmethod
    def normalize_id(cls, value):
        return _upper_required(value, "adapter_result_id")

    @model_validator(mode="after")
    def validate_result(self):
        return _validate_safety_flags(self, "kiwoom rest sector adapter result")
