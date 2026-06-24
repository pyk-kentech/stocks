from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from pydantic import Field, field_validator, model_validator

from stock_risk_mcp.models import StrictModel


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


def _validate_local_path(value: str, field_name: str) -> str:
    cleaned = _string_required(value, field_name)
    lowered = cleaned.lower()
    if "://" in lowered or lowered.startswith("//"):
        raise ValueError(f"{field_name} must be a local file path")
    if lowered.endswith(".parquet"):
        raise ValueError("parquet remains unsupported")
    return cleaned


def _normalize_list(value, field_name: str, *, upper: bool = False, local_paths: bool = False) -> list[str]:
    if value is None:
        return []
    if isinstance(value, (str, bytes)) or not isinstance(value, list):
        raise ValueError(f"{field_name} must be a list")
    if local_paths:
        return [_validate_local_path(item, field_name) for item in value]
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
        "no_websocket",
        "no_cloud_llm",
        "no_local_llm_runtime",
        "no_mock_order_execution",
    ):
        if not getattr(model, flag_name):
            raise ValueError(f"{context} must remain {flag_name}")
    return model


class ControlledMockDryRunDecision(StrEnum):
    BLOCKED = "BLOCKED"
    RESEARCH_ONLY = "RESEARCH_ONLY"
    DRY_RUN_REHEARSED = "DRY_RUN_REHEARSED"
    MOCK_EXECUTION_REVIEW_READY = "MOCK_EXECUTION_REVIEW_READY"
    WATCH_ONLY = "WATCH_ONLY"
    GAP = "GAP"
    REJECTED = "REJECTED"


class MockIntentRouteType(StrEnum):
    CORE_STRATEGY = "CORE_STRATEGY"
    LEADERSHIP_ONLY = "LEADERSHIP_ONLY"
    SECTOR_ONLY = "SECTOR_ONLY"
    LARGE_CAP_ONLY = "LARGE_CAP_ONLY"
    OUTLIER_MOMENTUM_SLEEVE = "OUTLIER_MOMENTUM_SLEEVE"
    HEDGE_INVERSE_SLEEVE = "HEDGE_INVERSE_SLEEVE"
    WATCH_ONLY = "WATCH_ONLY"
    BLOCKED = "BLOCKED"


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
    no_websocket: bool = True
    no_cloud_llm: bool = True
    no_local_llm_runtime: bool = True
    no_mock_order_execution: bool = True


class ControlledMockDryRunSafetyReport(_BaseReport):
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
        return _normalize_list(value, info.field_name, upper=True)

    @model_validator(mode="after")
    def validate_model(self):
        return _validate_safety_flags(self, "controlled mock dry-run safety report")


class ControlledMockDryRunAuditRecord(StrictModel):
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
    def normalize_dt(cls, value):
        return _aware(value)

    @field_validator("source_path", mode="before")
    @classmethod
    def normalize_path(cls, value):
        return _validate_local_path(value, "source_path")

    @field_validator("operator_context", mode="before")
    @classmethod
    def normalize_context(cls, value):
        return _string_required(value, "operator_context")


class MockOrderIntentPreview(_BaseReport):
    intent_id: str = Field(..., min_length=1)
    symbol: str = Field(..., min_length=1)
    market: str = Field(..., min_length=1)
    side: str = Field(..., min_length=1)
    candidate_action_type: str = Field(..., min_length=1)
    route_type: MockIntentRouteType
    quantity_preview: int = Field(default=0, ge=0)
    notional_preview: float = Field(default=0, ge=0)
    stop_discipline_ref: str | None = None
    event_restriction_ref: str | None = None
    market_regime_constraint_ref: str | None = None
    breadth_outlier_constraint_ref: str | None = None
    decision_timestamp: datetime
    available_at: datetime | None = None
    no_execution_flag: bool = True

    @field_validator("intent_id", "symbol", "market", "side", "candidate_action_type", mode="before")
    @classmethod
    def normalize_upper(cls, value):
        return _upper_required(value, "field")

    @field_validator(
        "stop_discipline_ref",
        "event_restriction_ref",
        "market_regime_constraint_ref",
        "breadth_outlier_constraint_ref",
        mode="before",
    )
    @classmethod
    def normalize_optional_ref(cls, value):
        if value is None:
            return None
        return _validate_local_path(value, "ref")

    @field_validator("decision_timestamp", "available_at", mode="before")
    @classmethod
    def normalize_dt(cls, value):
        return _aware(value)

    @model_validator(mode="after")
    def validate_model(self):
        return _validate_safety_flags(self, "mock order intent preview")


class ControlledMockDryRunSummaryReport(_BaseReport):
    report_id: str = Field(..., min_length=1)
    decision: ControlledMockDryRunDecision
    decision_reason: str = Field(..., min_length=1)
    route_type: MockIntentRouteType
    expected_state_transition: str = Field(..., min_length=1)

    @field_validator("report_id", "decision_reason", "expected_state_transition", mode="before")
    @classmethod
    def normalize_fields(cls, value, info):
        if info.field_name == "decision_reason":
            return _string_required(value, info.field_name)
        return _upper_required(value, info.field_name)

    @model_validator(mode="after")
    def validate_model(self):
        return _validate_safety_flags(self, "controlled mock dry-run summary report")


class SimpleStatusReport(_BaseReport):
    report_id: str = Field(..., min_length=1)
    status: str = Field(..., min_length=1)
    passed: bool = False
    details: list[str] = Field(default_factory=list)

    @field_validator("report_id", "status", mode="before")
    @classmethod
    def normalize_upper(cls, value):
        return _upper_required(value, "field")

    @field_validator("details", mode="before")
    @classmethod
    def normalize_details(cls, value):
        return _normalize_list(value, "details", upper=True)

    @model_validator(mode="after")
    def validate_model(self):
        return _validate_safety_flags(self, "simple status report")


class MockBoundaryViolationReport(_BaseReport):
    report_id: str = Field(..., min_length=1)
    real_broker_call_attempt: bool = False
    kiwoom_api_call_attempt: bool = False
    kiwoom_mock_order_execution_attempt: bool = False
    provider_network_execution_path: bool = False
    production_domain: bool = False
    websocket_dependency: bool = False
    autonomous_execution_path: bool = False
    executable_order_object_present: bool = False
    real_order_id_present: bool = False
    raw_account_output_present: bool = False
    credential_token_output_present: bool = False
    missing_fail_closed_behavior: bool = False
    findings: list[str] = Field(default_factory=list)

    @field_validator("report_id", mode="before")
    @classmethod
    def normalize_id(cls, value):
        return _upper_required(value, "report_id")

    @field_validator("findings", mode="before")
    @classmethod
    def normalize_findings(cls, value):
        return _normalize_list(value, "findings", upper=True)

    @model_validator(mode="after")
    def validate_model(self):
        return _validate_safety_flags(self, "mock boundary violation report")


class ControlledMockDryRunGapEntry(StrictModel):
    gap_id: str = Field(..., min_length=1)
    gap_category: str = Field(..., min_length=1)
    severity: str = Field(default="REPORT_ONLY", min_length=1)
    message: str = Field(..., min_length=1)

    @field_validator("gap_id", "gap_category", "severity", mode="before")
    @classmethod
    def normalize_upper(cls, value):
        return _upper_required(value, "field")

    @field_validator("message", mode="before")
    @classmethod
    def normalize_message(cls, value):
        return _string_required(value, "message")


class ControlledMockDryRunGapReport(_BaseReport):
    gap_report_id: str = Field(..., min_length=1)
    decision: ControlledMockDryRunDecision
    gap_entries: list[ControlledMockDryRunGapEntry] = Field(default_factory=list)
    blocking_gap_count: int = Field(default=0, ge=0)
    warning_gap_count: int = Field(default=0, ge=0)

    @field_validator("gap_report_id", mode="before")
    @classmethod
    def normalize_id(cls, value):
        return _upper_required(value, "gap_report_id")

    @model_validator(mode="after")
    def validate_model(self):
        return _validate_safety_flags(self, "controlled mock dry-run gap report")


class ControlledMockDryRunInput(StrictModel):
    dry_run_id: str = Field(..., min_length=1)
    candidate_symbol: str = Field(..., min_length=1)
    candidate_market: str = Field(..., min_length=1)
    candidate_side: str = Field(..., min_length=1)
    candidate_action_type: str = Field(..., min_length=1)
    candidate_is_leadership: bool = False
    candidate_is_outlier: bool = False
    candidate_is_exposure_reducing: bool = False
    candidate_is_inverse_or_hedge: bool = False
    route_hint: str | None = None
    paper_evaluation_ref: str | None = None
    paper_evaluation_decision: str | None = None
    mock_readiness_ref: str | None = None
    mock_readiness_decision: str | None = None
    market_regime_ref: str | None = None
    market_regime_decision: str | None = None
    market_regime_label: str | None = None
    provider_registry_ref: str | None = None
    provider_registry_decision: str | None = None
    position_sizing_ref: str | None = None
    position_sizing_decision: str | None = None
    quantity_preview: int = Field(default=0, ge=0)
    notional_preview: float = Field(default=0, ge=0)
    event_risk_ref: str | None = None
    event_risk_decision: str | None = None
    breadth_routing_ref: str | None = None
    breadth_routing_decision: str | None = None
    breadth_constraints: list[str] = Field(default_factory=list)
    strategy_ensemble_ref: str | None = None
    risk_policy_ref: str | None = None
    mock_market_data_readiness_ref: str | None = None
    mock_market_data_readiness_status: str | None = None
    mock_oauth_readiness_ref: str | None = None
    mock_oauth_readiness_status: str | None = None
    order_gate_boundary_ref: str | None = None
    kill_switch_policy_ref: str | None = None
    opt_in_policy_ref: str | None = None
    audit_policy_ref: str | None = None
    rollback_policy_ref: str | None = None
    stop_discipline_ref: str | None = None
    liquidity_evidence_ref: str | None = None
    slippage_risk_note: str | None = None
    outlier_max_sleeve_allocation: float | None = Field(default=None, ge=0)
    outlier_max_per_name_risk: float | None = Field(default=None, ge=0)
    candidate_requested_sleeve_allocation: float = Field(default=0, ge=0)
    candidate_requested_per_name_risk: float = Field(default=0, ge=0)
    current_order_count: int = Field(default=0, ge=0)
    max_order_count_limit: int = Field(default=0, ge=0)
    projected_total_exposure: float = Field(default=0, ge=0)
    max_total_exposure: float = Field(default=0, ge=0)
    projected_inverse_hedge_exposure: float = Field(default=0, ge=0)
    max_inverse_hedge_exposure: float = Field(default=0, ge=0)
    available_at: datetime | None = None
    source_refs: list[str] = Field(default_factory=list)
    live_prod_path_attempt: bool = False
    real_broker_dependency: bool = False
    kiwoom_dependency: bool = False
    kiwoom_mock_order_execution_dependency: bool = False
    provider_network_dependency: bool = False
    websocket_dependency: bool = False
    autonomous_execution_path: bool = False
    executable_order_object_present: bool = False
    real_order_id_present: bool = False
    raw_account_output_present: bool = False
    credential_token_output_present: bool = False
    missing_fail_closed_behavior: bool = False
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
    no_websocket: bool = True
    no_cloud_llm: bool = True
    no_local_llm_runtime: bool = True
    no_mock_order_execution: bool = True
    safety_report: ControlledMockDryRunSafetyReport
    audit_records: list[ControlledMockDryRunAuditRecord] = Field(default_factory=list)
    summary_report: ControlledMockDryRunSummaryReport | None = None
    mock_order_intent_preview: MockOrderIntentPreview | None = None
    preflight_rehearsal_report: SimpleStatusReport | None = None
    provider_readiness_rehearsal_report: SimpleStatusReport | None = None
    market_regime_rehearsal_report: SimpleStatusReport | None = None
    position_sizing_rehearsal_report: SimpleStatusReport | None = None
    event_risk_rehearsal_report: SimpleStatusReport | None = None
    breadth_outlier_routing_rehearsal_report: SimpleStatusReport | None = None
    order_gate_rehearsal_report: SimpleStatusReport | None = None
    risk_budget_rehearsal_report: SimpleStatusReport | None = None
    kill_switch_rehearsal_report: SimpleStatusReport | None = None
    rollback_rehearsal_report: SimpleStatusReport | None = None
    audit_trail_rehearsal_report: SimpleStatusReport | None = None
    boundary_violation_report: MockBoundaryViolationReport | None = None
    gap_report: ControlledMockDryRunGapReport | None = None

    @field_validator(
        "dry_run_id",
        "candidate_symbol",
        "candidate_market",
        "candidate_side",
        "candidate_action_type",
        "route_hint",
        "paper_evaluation_decision",
        "mock_readiness_decision",
        "market_regime_decision",
        "market_regime_label",
        "provider_registry_decision",
        "position_sizing_decision",
        "event_risk_decision",
        "breadth_routing_decision",
        "mock_market_data_readiness_status",
        "mock_oauth_readiness_status",
        "slippage_risk_note",
        mode="before",
    )
    @classmethod
    def normalize_upper(cls, value):
        if value is None:
            return None
        return _upper_required(value, "field")

    @field_validator(
        "paper_evaluation_ref",
        "mock_readiness_ref",
        "market_regime_ref",
        "provider_registry_ref",
        "position_sizing_ref",
        "event_risk_ref",
        "breadth_routing_ref",
        "strategy_ensemble_ref",
        "risk_policy_ref",
        "mock_market_data_readiness_ref",
        "mock_oauth_readiness_ref",
        "order_gate_boundary_ref",
        "kill_switch_policy_ref",
        "opt_in_policy_ref",
        "audit_policy_ref",
        "rollback_policy_ref",
        "stop_discipline_ref",
        "liquidity_evidence_ref",
        mode="before",
    )
    @classmethod
    def normalize_optional_ref(cls, value):
        if value is None:
            return None
        return _validate_local_path(value, "ref")

    @field_validator("available_at", mode="before")
    @classmethod
    def normalize_dt(cls, value):
        return _aware(value)

    @field_validator("source_refs", mode="before")
    @classmethod
    def normalize_refs(cls, value):
        return _normalize_list(value, "source_refs", local_paths=True)

    @field_validator("breadth_constraints", mode="before")
    @classmethod
    def normalize_constraints(cls, value):
        return _normalize_list(value, "breadth_constraints", upper=True)

    @model_validator(mode="after")
    def validate_model(self):
        return _validate_safety_flags(self, "controlled mock dry-run input")
