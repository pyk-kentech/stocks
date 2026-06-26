from __future__ import annotations

from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any

from pydantic import Field, field_validator, model_validator

from stock_risk_mcp.feature_store_models import FeatureStoreAuditRecord
from stock_risk_mcp.models import StrictModel


class StrEnum(str, Enum):
    pass


ScalarValue = int | float | str | bool | None


def _aware(value: datetime | str | None) -> datetime | None:
    if value is None:
        return None
    parsed = datetime.fromisoformat(value) if isinstance(value, str) else value
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


def _normalize_list(value, field_name: str, *, upper: bool = False) -> list[str]:
    if value is None:
        return []
    if isinstance(value, (str, bytes)) or not isinstance(value, list):
        raise ValueError(f"{field_name} must be a list")
    if upper:
        return [_upper_required(item, field_name) for item in value]
    return [_string_required(item, field_name) for item in value]


def _validate_relative_path(value: str | None, field_name: str) -> str | None:
    if value is None:
        return None
    cleaned = _string_required(value, field_name)
    lowered = cleaned.lower()
    if "://" in lowered or lowered.startswith("//"):
        raise ValueError(f"{field_name} must be a local path")
    path = Path(cleaned)
    if path.is_absolute():
        raise ValueError(f"{field_name} must be relative")
    if ".." in path.parts:
        raise ValueError(f"{field_name} must not contain path traversal")
    if cleaned.lower().endswith(".parquet"):
        raise ValueError(f"{field_name} parquet remains unsupported")
    return cleaned


def _validate_scalar_map(value: dict[str, Any], field_name: str) -> dict[str, ScalarValue]:
    if not isinstance(value, dict):
        raise ValueError(f"{field_name} must be a dict")
    blocked = ("credential", "token", "secret", "authorization", "api_key", "account_number")
    normalized: dict[str, ScalarValue] = {}
    for key, raw in value.items():
        name = _string_required(key, f"{field_name}.key")
        if any(marker in name.lower() for marker in blocked):
            raise ValueError(f"{field_name} contains blocked field name: {name}")
        if isinstance(raw, bool) or raw is None or isinstance(raw, (int, float, str)):
            normalized[name] = raw
            continue
        raise ValueError(f"{field_name} values must be scalar only")
    return normalized


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
        "no_broker_paper_api",
        "no_kiwoom_api",
        "no_ls_api",
        "no_websocket",
        "no_cloud_llm",
        "no_local_llm_runtime",
        "no_env_read",
        "no_credential_read",
        "no_token_loading",
        "no_auth_header_generation",
        "no_model_training",
        "execution_controlled_only",
    ):
        if not getattr(model, flag_name):
            raise ValueError(f"{context} must remain {flag_name}")
    return model


class ControlledExecutionMode(StrEnum):
    BLOCKED_DEFAULT = "BLOCKED_DEFAULT"
    READINESS_REPORT_ONLY = "READINESS_REPORT_ONLY"
    PREFLIGHT_ONLY = "PREFLIGHT_ONLY"
    MANUAL_APPROVAL_PACKET_ONLY = "MANUAL_APPROVAL_PACKET_ONLY"
    MOCK_EXECUTION_ONLY = "MOCK_EXECUTION_ONLY"
    DRY_RUN_NO_BROKER = "DRY_RUN_NO_BROKER"
    LIVE_EXECUTION_OPT_IN_BOUNDARY = "LIVE_EXECUTION_OPT_IN_BOUNDARY"
    REJECTED = "REJECTED"


class ControlledExecutionProvider(StrEnum):
    LOCAL_MOCK = "LOCAL_MOCK"
    DRY_RUN = "DRY_RUN"
    KIWOOM = "KIWOOM"
    LS = "LS"
    UNKNOWN = "UNKNOWN"


class ControlledExecutionAdapterStatus(StrEnum):
    MOCK_READY = "MOCK_READY"
    DRY_RUN_READY = "DRY_RUN_READY"
    LIVE_BOUNDARY_BLOCKED_DEFAULT = "LIVE_BOUNDARY_BLOCKED_DEFAULT"
    ADAPTER_SCHEMA_GAP = "ADAPTER_SCHEMA_GAP"
    PROVIDER_SETUP_REQUIRED = "PROVIDER_SETUP_REQUIRED"
    REJECTED = "REJECTED"


class ControlledExecutionCredentialPolicy(StrEnum):
    NOT_REQUIRED = "NOT_REQUIRED"
    MOCK_ONLY = "MOCK_ONLY"
    KEY_REF_ONLY = "KEY_REF_ONLY"
    TOKEN_PROVIDER_ONLY = "TOKEN_PROVIDER_ONLY"
    BLOCKED = "BLOCKED"


class ControlledExecutionPrerequisiteStatus(StrEnum):
    GREEN = "GREEN"
    MISSING = "MISSING"
    STALE = "STALE"
    AMBIGUOUS = "AMBIGUOUS"
    BLOCKED = "BLOCKED"
    REJECTED = "REJECTED"
    DATA_GAP = "DATA_GAP"


class ControlledExecutionIntentSide(StrEnum):
    BUY = "BUY"
    SELL = "SELL"
    HOLD = "HOLD"
    WATCH = "WATCH"
    CANCEL_BLOCKED = "CANCEL_BLOCKED"


class ControlledExecutionOrderType(StrEnum):
    LIMIT = "LIMIT"
    MARKET = "MARKET"
    STOP_LIMIT = "STOP_LIMIT"


class ControlledExecutionTimeInForce(StrEnum):
    DAY = "DAY"
    IOC = "IOC"
    FOK = "FOK"
    GTC = "GTC"


class ControlledExecutionKillSwitchStatus(StrEnum):
    CLEAR = "CLEAR"
    ACTIVE = "ACTIVE"
    TRIPPED_DAILY_LOSS = "TRIPPED_DAILY_LOSS"
    TRIPPED_MAX_ORDERS = "TRIPPED_MAX_ORDERS"
    TRIPPED_MAX_EXPOSURE = "TRIPPED_MAX_EXPOSURE"
    TRIPPED_EVENT_RISK = "TRIPPED_EVENT_RISK"
    TRIPPED_STALE_DATA = "TRIPPED_STALE_DATA"
    DATA_GAP = "DATA_GAP"
    REJECTED = "REJECTED"


class ControlledExecutionDuplicateStatus(StrEnum):
    NO_DUPLICATE = "NO_DUPLICATE"
    DUPLICATE_INTENT = "DUPLICATE_INTENT"
    DUPLICATE_DRAFT = "DUPLICATE_DRAFT"
    DUPLICATE_IDEMPOTENCY_KEY = "DUPLICATE_IDEMPOTENCY_KEY"
    PENDING_STATE_UNRESOLVED = "PENDING_STATE_UNRESOLVED"
    APPROVAL_REUSE_DETECTED = "APPROVAL_REUSE_DETECTED"
    DATA_GAP = "DATA_GAP"
    REJECTED = "REJECTED"


class ControlledExecutionReadinessStatus(StrEnum):
    BLOCKED_DEFAULT = "BLOCKED_DEFAULT"
    READINESS_REPORT_READY = "READINESS_REPORT_READY"
    PREFLIGHT_READY = "PREFLIGHT_READY"
    APPROVAL_PACKET_READY = "APPROVAL_PACKET_READY"
    MOCK_EXECUTION_READY = "MOCK_EXECUTION_READY"
    DRY_RUN_READY = "DRY_RUN_READY"
    LIVE_BOUNDARY_BLOCKED = "LIVE_BOUNDARY_BLOCKED"
    DATA_GAP = "DATA_GAP"
    STALE = "STALE"
    AMBIGUOUS = "AMBIGUOUS"
    BLOCKED = "BLOCKED"
    REJECTED = "REJECTED"


class ControlledExecutionOptIn(StrictModel):
    allow_live_boundary_preview: bool = False
    allow_mock_execution: bool = False
    allow_dry_run: bool = False
    acknowledge_readonly_only: bool = False
    acknowledge_no_account_mutation: bool = False
    acknowledge_manual_approval_required: bool = False
    acknowledge_user_initiated: bool = False


class _BaseSafety(StrictModel):
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
    no_broker_paper_api: bool = True
    no_kiwoom_api: bool = True
    no_ls_api: bool = True
    no_websocket: bool = True
    no_cloud_llm: bool = True
    no_local_llm_runtime: bool = True
    no_env_read: bool = True
    no_credential_read: bool = True
    no_token_loading: bool = True
    no_auth_header_generation: bool = True
    no_model_training: bool = True
    execution_controlled_only: bool = True


class ControlledExecutionGapEntry(StrictModel):
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


class ControlledExecutionPrerequisiteCheck(StrictModel):
    prerequisite_name: str = Field(..., min_length=1)
    prerequisite_status: ControlledExecutionPrerequisiteStatus
    reason_codes: list[str] = Field(default_factory=list)
    source_ref: str | None = None

    @field_validator("prerequisite_name", mode="before")
    @classmethod
    def normalize_name(cls, value):
        return _upper_required(value, "prerequisite_name")

    @field_validator("reason_codes", mode="before")
    @classmethod
    def normalize_reason_codes(cls, value):
        return _normalize_list(value, "reason_codes", upper=True)

    @field_validator("source_ref", mode="before")
    @classmethod
    def normalize_source_ref(cls, value):
        if value is None:
            return None
        return _validate_relative_path(value, "source_ref")


class ControlledExecutionReadinessReport(_BaseSafety):
    report_id: str = Field(..., min_length=1)
    pipeline_id: str = Field(..., min_length=1)
    mode: ControlledExecutionMode
    readiness_status: ControlledExecutionReadinessStatus
    prerequisite_checks: list[ControlledExecutionPrerequisiteCheck] = Field(default_factory=list)
    all_green: bool = False
    reason_codes: list[str] = Field(default_factory=list)

    @field_validator("report_id", "pipeline_id", mode="before")
    @classmethod
    def normalize_upper(cls, value, info):
        return _upper_required(value, info.field_name)

    @field_validator("reason_codes", mode="before")
    @classmethod
    def normalize_reason_codes(cls, value):
        return _normalize_list(value, "reason_codes", upper=True)

    @model_validator(mode="after")
    def validate_model(self):
        return _validate_safety_flags(self, "controlled execution readiness report")


class ControlledExecutionPreflightRequest(_BaseSafety):
    request_id: str = Field(..., min_length=1)
    pipeline_id: str = Field(..., min_length=1)
    mode: ControlledExecutionMode
    requested_at: datetime
    requested_by: str = Field(..., min_length=1)

    @field_validator("request_id", "pipeline_id", mode="before")
    @classmethod
    def normalize_upper(cls, value, info):
        return _upper_required(value, info.field_name)

    @field_validator("requested_by", mode="before")
    @classmethod
    def normalize_requested_by(cls, value):
        return _string_required(value, "requested_by")

    @field_validator("requested_at", mode="before")
    @classmethod
    def normalize_requested_at(cls, value):
        return _aware(value)

    @model_validator(mode="after")
    def validate_model(self):
        return _validate_safety_flags(self, "controlled execution preflight request")


class ControlledExecutionPreflightDecision(_BaseSafety):
    decision_id: str = Field(..., min_length=1)
    pipeline_id: str = Field(..., min_length=1)
    mode: ControlledExecutionMode
    readiness_status: ControlledExecutionReadinessStatus
    all_green: bool = False
    approved_for_draft: bool = False
    approved_for_live_boundary: bool = False
    reason_codes: list[str] = Field(default_factory=list)

    @field_validator("decision_id", "pipeline_id", mode="before")
    @classmethod
    def normalize_upper(cls, value, info):
        return _upper_required(value, info.field_name)

    @field_validator("reason_codes", mode="before")
    @classmethod
    def normalize_reason_codes(cls, value):
        return _normalize_list(value, "reason_codes", upper=True)

    @model_validator(mode="after")
    def validate_model(self):
        return _validate_safety_flags(self, "controlled execution preflight decision")


class ControlledExecutionRiskCheckResult(_BaseSafety):
    check_id: str = Field(..., min_length=1)
    risk_budget_ref: str | None = None
    prerequisite_status: ControlledExecutionPrerequisiteStatus
    bounded_position_size: bool = True
    daily_order_cap_checked: bool = True
    price_band_checked: bool = True
    reason_codes: list[str] = Field(default_factory=list)

    @field_validator("check_id", mode="before")
    @classmethod
    def normalize_id(cls, value):
        return _upper_required(value, "check_id")

    @field_validator("risk_budget_ref", mode="before")
    @classmethod
    def normalize_ref(cls, value):
        if value is None:
            return None
        return _string_required(value, "risk_budget_ref")

    @field_validator("reason_codes", mode="before")
    @classmethod
    def normalize_reason_codes(cls, value):
        return _normalize_list(value, "reason_codes", upper=True)

    @model_validator(mode="after")
    def validate_model(self):
        return _validate_safety_flags(self, "controlled execution risk check result")


class ControlledExecutionReconciliationCheckResult(_BaseSafety):
    check_id: str = Field(..., min_length=1)
    prerequisite_status: ControlledExecutionPrerequisiteStatus
    account_ref_redacted: bool = True
    account_read_only: bool = True
    instrument_mapping_unambiguous: bool = True
    cash_position_mismatch_classified: bool = True
    reason_codes: list[str] = Field(default_factory=list)

    @field_validator("check_id", mode="before")
    @classmethod
    def normalize_id(cls, value):
        return _upper_required(value, "check_id")

    @field_validator("reason_codes", mode="before")
    @classmethod
    def normalize_reason_codes(cls, value):
        return _normalize_list(value, "reason_codes", upper=True)

    @model_validator(mode="after")
    def validate_model(self):
        return _validate_safety_flags(self, "controlled execution reconciliation check result")


class ControlledExecutionIntent(_BaseSafety):
    intent_id: str = Field(..., min_length=1)
    instrument_id: str = Field(..., min_length=1)
    provider_symbol: str = Field(..., min_length=1)
    market: str = Field(..., min_length=1)
    side: ControlledExecutionIntentSide
    reference_price: float | None = Field(default=None, gt=0)
    quantity_proposal: float = Field(default=0.0, ge=0)
    notional_proposal: float = Field(default=0.0, ge=0)
    risk_budget_ref: str | None = None
    source_report_refs: list[str] = Field(default_factory=list)
    reason_codes: list[str] = Field(default_factory=list)
    preflight_status: ControlledExecutionReadinessStatus

    @field_validator("intent_id", "instrument_id", "provider_symbol", "market", mode="before")
    @classmethod
    def normalize_upper(cls, value, info):
        if info.field_name == "provider_symbol":
            return _string_required(value, info.field_name).upper()
        return _upper_required(value, info.field_name)

    @field_validator("risk_budget_ref", mode="before")
    @classmethod
    def normalize_ref(cls, value):
        if value is None:
            return None
        return _string_required(value, "risk_budget_ref")

    @field_validator("source_report_refs", mode="before")
    @classmethod
    def normalize_refs(cls, value):
        return _normalize_list(value, "source_report_refs")

    @field_validator("reason_codes", mode="before")
    @classmethod
    def normalize_reason_codes(cls, value):
        return _normalize_list(value, "reason_codes", upper=True)

    @model_validator(mode="after")
    def validate_model(self):
        return _validate_safety_flags(self, "controlled execution intent")


class ControlledExecutionOrderDraft(_BaseSafety):
    draft_id: str = Field(..., min_length=1)
    instrument_id: str = Field(..., min_length=1)
    side: ControlledExecutionIntentSide
    quantity: float = Field(default=0.0, ge=0)
    order_type: ControlledExecutionOrderType = ControlledExecutionOrderType.LIMIT
    limit_price: float | None = Field(default=None, gt=0)
    time_in_force: ControlledExecutionTimeInForce = ControlledExecutionTimeInForce.DAY
    idempotency_key: str = Field(..., min_length=1)
    draft_hash: str = Field(..., min_length=1)
    risk_checks: list[str] = Field(default_factory=list)
    reconciliation_checks: list[str] = Field(default_factory=list)
    approval_hash: str | None = None
    adapter_target: ControlledExecutionProvider = ControlledExecutionProvider.UNKNOWN
    status: ControlledExecutionReadinessStatus
    live_submit_preview_blocked: bool = True

    @field_validator("draft_id", "instrument_id", "idempotency_key", "draft_hash", mode="before")
    @classmethod
    def normalize_upper(cls, value, info):
        return _upper_required(value, info.field_name)

    @field_validator("risk_checks", "reconciliation_checks", mode="before")
    @classmethod
    def normalize_checks(cls, value, info):
        return _normalize_list(value, info.field_name, upper=True)

    @field_validator("approval_hash", mode="before")
    @classmethod
    def normalize_approval_hash(cls, value):
        if value is None:
            return None
        return _upper_required(value, "approval_hash")

    @model_validator(mode="after")
    def validate_model(self):
        if self.order_type == ControlledExecutionOrderType.MARKET:
            raise ValueError("market order remains blocked by default")
        return _validate_safety_flags(self, "controlled execution order draft")


class ControlledExecutionApprovalPacket(_BaseSafety):
    packet_id: str = Field(..., min_length=1)
    order_draft_hash: str = Field(..., min_length=1)
    packet_hash: str = Field(..., min_length=1)
    expiry_at: datetime
    single_use_approval_ref: str = Field(..., min_length=1)
    risk_summary: dict[str, ScalarValue] = Field(default_factory=dict)
    reconciliation_summary: dict[str, ScalarValue] = Field(default_factory=dict)
    kill_switch_summary: dict[str, ScalarValue] = Field(default_factory=dict)
    duplicate_guard_summary: dict[str, ScalarValue] = Field(default_factory=dict)
    adapter_summary: dict[str, ScalarValue] = Field(default_factory=dict)
    preview_summary: dict[str, ScalarValue] = Field(default_factory=dict)

    @field_validator("packet_id", "order_draft_hash", "packet_hash", mode="before")
    @classmethod
    def normalize_upper(cls, value, info):
        return _upper_required(value, info.field_name)

    @field_validator("single_use_approval_ref", mode="before")
    @classmethod
    def normalize_ref(cls, value):
        return _string_required(value, "single_use_approval_ref")

    @field_validator("expiry_at", mode="before")
    @classmethod
    def normalize_expiry(cls, value):
        return _aware(value)

    @field_validator(
        "risk_summary",
        "reconciliation_summary",
        "kill_switch_summary",
        "duplicate_guard_summary",
        "adapter_summary",
        "preview_summary",
        mode="before",
    )
    @classmethod
    def normalize_maps(cls, value, info):
        return _validate_scalar_map(value or {}, info.field_name)

    @model_validator(mode="after")
    def validate_model(self):
        return _validate_safety_flags(self, "controlled execution approval packet")


class ControlledExecutionManualApproval(_BaseSafety):
    approval_id: str = Field(..., min_length=1)
    approval_ref: str = Field(..., min_length=1)
    approval_ref_hash: str = Field(..., min_length=1)
    order_draft_hash: str = Field(..., min_length=1)
    packet_hash: str = Field(..., min_length=1)
    approved_at: datetime
    expiry_at: datetime
    single_use: bool = True
    already_used: bool = False
    valid: bool = False
    reason_codes: list[str] = Field(default_factory=list)

    @field_validator("approval_id", "approval_ref_hash", "order_draft_hash", "packet_hash", mode="before")
    @classmethod
    def normalize_upper(cls, value, info):
        return _upper_required(value, info.field_name)

    @field_validator("approval_ref", mode="before")
    @classmethod
    def normalize_ref(cls, value):
        return _string_required(value, "approval_ref")

    @field_validator("approved_at", "expiry_at", mode="before")
    @classmethod
    def normalize_dt(cls, value):
        return _aware(value)

    @field_validator("reason_codes", mode="before")
    @classmethod
    def normalize_reason_codes(cls, value):
        return _normalize_list(value, "reason_codes", upper=True)

    @model_validator(mode="after")
    def validate_model(self):
        return _validate_safety_flags(self, "controlled execution manual approval")


class ControlledExecutionKillSwitchState(_BaseSafety):
    state_id: str = Field(..., min_length=1)
    global_status: ControlledExecutionKillSwitchStatus
    market_status: ControlledExecutionKillSwitchStatus
    instrument_status: ControlledExecutionKillSwitchStatus
    daily_loss_status: ControlledExecutionKillSwitchStatus
    max_order_count_status: ControlledExecutionKillSwitchStatus
    max_exposure_status: ControlledExecutionKillSwitchStatus
    event_risk_status: ControlledExecutionKillSwitchStatus
    stale_data_status: ControlledExecutionKillSwitchStatus
    cooldown_status: ControlledExecutionKillSwitchStatus
    clear_for_preflight: bool = False
    reason_codes: list[str] = Field(default_factory=list)

    @field_validator("state_id", mode="before")
    @classmethod
    def normalize_id(cls, value):
        return _upper_required(value, "state_id")

    @field_validator("reason_codes", mode="before")
    @classmethod
    def normalize_reason_codes(cls, value):
        return _normalize_list(value, "reason_codes", upper=True)

    @model_validator(mode="after")
    def validate_model(self):
        return _validate_safety_flags(self, "controlled execution kill switch state")


class ControlledExecutionDuplicateGuardState(_BaseSafety):
    state_id: str = Field(..., min_length=1)
    duplicate_status: ControlledExecutionDuplicateStatus
    idempotency_key: str = Field(..., min_length=1)
    clear_for_preflight: bool = False
    reason_codes: list[str] = Field(default_factory=list)

    @field_validator("state_id", "idempotency_key", mode="before")
    @classmethod
    def normalize_upper(cls, value, info):
        return _upper_required(value, info.field_name)

    @field_validator("reason_codes", mode="before")
    @classmethod
    def normalize_reason_codes(cls, value):
        return _normalize_list(value, "reason_codes", upper=True)

    @model_validator(mode="after")
    def validate_model(self):
        return _validate_safety_flags(self, "controlled execution duplicate guard state")


class ControlledExecutionAdapterCapabilityRow(StrictModel):
    provider: ControlledExecutionProvider
    adapter_status: ControlledExecutionAdapterStatus
    credential_policy: ControlledExecutionCredentialPolicy
    exact_schema_evidence_present: bool = False
    allowlisted: bool = False
    notes: str = Field(..., min_length=1)

    @field_validator("notes", mode="before")
    @classmethod
    def normalize_notes(cls, value):
        return _string_required(value, "notes")


class ControlledExecutionAdapterCapabilityReport(_BaseSafety):
    report_id: str = Field(..., min_length=1)
    mode: ControlledExecutionMode
    adapter_rows: list[ControlledExecutionAdapterCapabilityRow] = Field(default_factory=list)
    blocked_submit_preview: dict[str, ScalarValue] = Field(default_factory=dict)

    @field_validator("report_id", mode="before")
    @classmethod
    def normalize_id(cls, value):
        return _upper_required(value, "report_id")

    @field_validator("blocked_submit_preview", mode="before")
    @classmethod
    def normalize_preview(cls, value):
        return _validate_scalar_map(value or {}, "blocked_submit_preview")

    @model_validator(mode="after")
    def validate_model(self):
        return _validate_safety_flags(self, "controlled execution adapter capability report")


class ControlledExecutionMockExecutionResult(_BaseSafety):
    result_id: str = Field(..., min_length=1)
    draft_id: str = Field(..., min_length=1)
    mode: ControlledExecutionMode = ControlledExecutionMode.MOCK_EXECUTION_ONLY
    simulated_status: str = Field(..., min_length=1)
    accepted: bool = False
    audit_ref: str = Field(..., min_length=1)
    reason_codes: list[str] = Field(default_factory=list)

    @field_validator("result_id", "draft_id", "simulated_status", "audit_ref", mode="before")
    @classmethod
    def normalize_fields(cls, value, info):
        if info.field_name == "audit_ref":
            return _string_required(value, info.field_name)
        return _upper_required(value, info.field_name)

    @field_validator("reason_codes", mode="before")
    @classmethod
    def normalize_reason_codes(cls, value):
        return _normalize_list(value, "reason_codes", upper=True)

    @model_validator(mode="after")
    def validate_model(self):
        return _validate_safety_flags(self, "controlled execution mock execution result")


class ControlledExecutionDryRunResult(_BaseSafety):
    result_id: str = Field(..., min_length=1)
    draft_id: str = Field(..., min_length=1)
    mode: ControlledExecutionMode = ControlledExecutionMode.DRY_RUN_NO_BROKER
    preview_status: str = Field(..., min_length=1)
    schema_evidence_present: bool = False
    blocked_redacted_preview: dict[str, ScalarValue] = Field(default_factory=dict)
    audit_ref: str = Field(..., min_length=1)
    reason_codes: list[str] = Field(default_factory=list)

    @field_validator("result_id", "draft_id", "preview_status", mode="before")
    @classmethod
    def normalize_upper(cls, value, info):
        return _upper_required(value, info.field_name)

    @field_validator("audit_ref", mode="before")
    @classmethod
    def normalize_audit_ref(cls, value):
        return _string_required(value, "audit_ref")

    @field_validator("blocked_redacted_preview", mode="before")
    @classmethod
    def normalize_preview(cls, value):
        return _validate_scalar_map(value or {}, "blocked_redacted_preview")

    @field_validator("reason_codes", mode="before")
    @classmethod
    def normalize_reason_codes(cls, value):
        return _normalize_list(value, "reason_codes", upper=True)

    @model_validator(mode="after")
    def validate_model(self):
        return _validate_safety_flags(self, "controlled execution dry-run result")


class ControlledExecutionAuditRecord(_BaseSafety):
    audit_id: str = Field(..., min_length=1)
    action_type: str = Field(..., min_length=1)
    created_at: datetime
    source_refs: list[str] = Field(default_factory=list)
    order_draft_hash: str | None = None
    approval_ref_hash: str | None = None
    idempotency_key: str | None = None
    mode: ControlledExecutionMode
    decision: str = Field(..., min_length=1)
    reason_codes: list[str] = Field(default_factory=list)
    redaction_applied: bool = True

    @field_validator("audit_id", "action_type", "decision", mode="before")
    @classmethod
    def normalize_fields(cls, value, info):
        if info.field_name == "action_type":
            return _string_required(value, info.field_name).upper()
        return _upper_required(value, info.field_name)

    @field_validator("created_at", mode="before")
    @classmethod
    def normalize_created_at(cls, value):
        return _aware(value)

    @field_validator("source_refs", mode="before")
    @classmethod
    def normalize_source_refs(cls, value):
        return _normalize_list(value, "source_refs")

    @field_validator("order_draft_hash", "approval_ref_hash", "idempotency_key", mode="before")
    @classmethod
    def normalize_optional_upper(cls, value, info):
        if value is None:
            return None
        return _upper_required(value, info.field_name)

    @field_validator("reason_codes", mode="before")
    @classmethod
    def normalize_reason_codes(cls, value):
        return _normalize_list(value, "reason_codes", upper=True)

    @model_validator(mode="after")
    def validate_model(self):
        return _validate_safety_flags(self, "controlled execution audit record")


class ControlledExecutionSafetyReport(_BaseSafety):
    report_id: str = Field(..., min_length=1)
    pipeline_id: str = Field(..., min_length=1)
    findings: list[str] = Field(default_factory=list)

    @field_validator("report_id", "pipeline_id", mode="before")
    @classmethod
    def normalize_upper(cls, value, info):
        return _upper_required(value, info.field_name)

    @field_validator("findings", mode="before")
    @classmethod
    def normalize_findings(cls, value):
        return _normalize_list(value, "findings", upper=True)

    @model_validator(mode="after")
    def validate_model(self):
        return _validate_safety_flags(self, "controlled execution safety report")


class ControlledExecutionGapReport(_BaseSafety):
    report_id: str = Field(..., min_length=1)
    pipeline_id: str = Field(..., min_length=1)
    readiness_status: ControlledExecutionReadinessStatus
    gap_entries: list[ControlledExecutionGapEntry] = Field(default_factory=list)

    @field_validator("report_id", "pipeline_id", mode="before")
    @classmethod
    def normalize_upper(cls, value, info):
        return _upper_required(value, info.field_name)

    @model_validator(mode="after")
    def validate_model(self):
        return _validate_safety_flags(self, "controlled execution gap report")


class ControlledExecutionPipelineInput(_BaseSafety):
    pipeline_id: str = Field(..., min_length=1)
    dataset_id: str = Field(..., min_length=1)
    mode: ControlledExecutionMode = ControlledExecutionMode.BLOCKED_DEFAULT
    provider: ControlledExecutionProvider = ControlledExecutionProvider.LOCAL_MOCK
    opt_in: ControlledExecutionOptIn = Field(default_factory=ControlledExecutionOptIn)
    requested_by: str = Field(default="LOCAL_OPERATOR", min_length=1)
    requested_at: datetime
    instrument_id: str = Field(..., min_length=1)
    provider_symbol: str = Field(..., min_length=1)
    market: str = Field(..., min_length=1)
    side: ControlledExecutionIntentSide
    reference_price: float = Field(..., gt=0)
    quantity_proposal: float = Field(..., gt=0)
    notional_proposal: float = Field(..., gt=0)
    risk_budget_ref: str | None = None
    feature_store_manifest: dict[str, ScalarValue] = Field(default_factory=dict)
    leakage_report: dict[str, ScalarValue] = Field(default_factory=dict)
    paper_evaluation_report: dict[str, ScalarValue] = Field(default_factory=dict)
    macro_regime_report: dict[str, ScalarValue] = Field(default_factory=dict)
    domestic_snapshot_report: dict[str, ScalarValue] = Field(default_factory=dict)
    position_sizing_report: dict[str, ScalarValue] = Field(default_factory=dict)
    event_risk_report: dict[str, ScalarValue] = Field(default_factory=dict)
    breadth_routing_report: dict[str, ScalarValue] = Field(default_factory=dict)
    controlled_mock_rehearsal_report: dict[str, ScalarValue] = Field(default_factory=dict)
    account_read_report: dict[str, ScalarValue] = Field(default_factory=dict)
    reconciliation_report: dict[str, ScalarValue] = Field(default_factory=dict)
    adapter_evidence: dict[str, ScalarValue] = Field(default_factory=dict)
    manual_approval_fixture: dict[str, ScalarValue] | None = None
    live_boundary_evidence_ref: str | None = None
    global_kill_switch_active: bool = False
    market_kill_switch_active: bool = False
    instrument_kill_switch_active: bool = False
    daily_loss_breached: bool = False
    max_order_count_breached: bool = False
    max_exposure_breached: bool = False
    stale_data_blocked: bool = False
    cooldown_active: bool = False
    prior_open_intent_exists: bool = False
    prior_pending_draft_exists: bool = False
    same_instrument_side_collision: bool = False
    prior_pending_audit_unresolved: bool = False
    approval_reuse_detected: bool = False
    idempotency_key: str = Field(..., min_length=1)
    prior_audit_records: list[ControlledExecutionAuditRecord] = Field(default_factory=list)
    audit_records: list[FeatureStoreAuditRecord] = Field(default_factory=list)

    @field_validator("pipeline_id", "dataset_id", "instrument_id", "market", "idempotency_key", mode="before")
    @classmethod
    def normalize_upper(cls, value, info):
        return _upper_required(value, info.field_name)

    @field_validator("provider_symbol", "requested_by", mode="before")
    @classmethod
    def normalize_string(cls, value, info):
        return _string_required(value, info.field_name)

    @field_validator("requested_at", mode="before")
    @classmethod
    def normalize_requested_at(cls, value):
        return _aware(value)

    @field_validator("risk_budget_ref", "live_boundary_evidence_ref", mode="before")
    @classmethod
    def normalize_optional_strings(cls, value, info):
        if value is None:
            return None
        if info.field_name == "live_boundary_evidence_ref":
            return _validate_relative_path(value, info.field_name)
        return _string_required(value, info.field_name)

    @field_validator(
        "feature_store_manifest",
        "leakage_report",
        "paper_evaluation_report",
        "macro_regime_report",
        "domestic_snapshot_report",
        "position_sizing_report",
        "event_risk_report",
        "breadth_routing_report",
        "controlled_mock_rehearsal_report",
        "account_read_report",
        "reconciliation_report",
        "adapter_evidence",
        mode="before",
    )
    @classmethod
    def normalize_maps(cls, value, info):
        return _validate_scalar_map(value or {}, info.field_name)

    @field_validator("manual_approval_fixture", mode="before")
    @classmethod
    def normalize_manual_fixture(cls, value):
        if value is None:
            return None
        return _validate_scalar_map(value, "manual_approval_fixture")

    @model_validator(mode="after")
    def validate_model(self):
        return _validate_safety_flags(self, "controlled execution pipeline input")


class ControlledExecutionPipelineResult(StrictModel):
    readiness_report: ControlledExecutionReadinessReport
    preflight_request: ControlledExecutionPreflightRequest
    preflight_decision: ControlledExecutionPreflightDecision
    risk_check_result: ControlledExecutionRiskCheckResult
    reconciliation_check_result: ControlledExecutionReconciliationCheckResult
    execution_intent: ControlledExecutionIntent
    order_draft: ControlledExecutionOrderDraft
    approval_packet: ControlledExecutionApprovalPacket
    manual_approval: ControlledExecutionManualApproval
    kill_switch_state: ControlledExecutionKillSwitchState
    duplicate_guard_state: ControlledExecutionDuplicateGuardState
    adapter_capability_report: ControlledExecutionAdapterCapabilityReport
    mock_execution_result: ControlledExecutionMockExecutionResult
    dry_run_result: ControlledExecutionDryRunResult
    audit_records: list[ControlledExecutionAuditRecord]
    safety_report: ControlledExecutionSafetyReport
    gap_report: ControlledExecutionGapReport
