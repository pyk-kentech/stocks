from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from pydantic import Field, field_validator, model_validator

from stock_risk_mcp.models import StrictModel


def _aware(value: datetime | str) -> datetime:
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


class ControlledMockReadinessDecision(StrEnum):
    BLOCKED = "BLOCKED"
    RESEARCH_ONLY = "RESEARCH_ONLY"
    MOCK_REVIEW_READY = "MOCK_REVIEW_READY"
    MOCK_DRY_RUN_READY = "MOCK_DRY_RUN_READY"
    GAP = "GAP"
    REJECTED = "REJECTED"


class ControlledMockReadinessGapCategory(StrEnum):
    READINESS_REPORT_GENERATED = "READINESS_REPORT_GENERATED"
    MISSING_V77_PAPER_EVAL = "MISSING_V77_PAPER_EVAL"
    INVALID_PAPER_EVAL_DECISION = "INVALID_PAPER_EVAL_DECISION"
    MISSING_V76_POLICY = "MISSING_V76_POLICY"
    INVALID_V76_POLICY_DECISION = "INVALID_V76_POLICY_DECISION"
    MISSING_ENSEMBLE_DEPENDENCY = "MISSING_ENSEMBLE_DEPENDENCY"
    MISSING_RISK_CONTROL = "MISSING_RISK_CONTROL"
    MISSING_OAUTH_READINESS = "MISSING_OAUTH_READINESS"
    MISSING_MARKET_DATA_READINESS = "MISSING_MARKET_DATA_READINESS"
    MISSING_BROKER_ADAPTER_BOUNDARY = "MISSING_BROKER_ADAPTER_BOUNDARY"
    MISSING_ORDER_GATE_BOUNDARY = "MISSING_ORDER_GATE_BOUNDARY"
    MISSING_KILL_SWITCH = "MISSING_KILL_SWITCH"
    MISSING_USER_OPT_IN_POLICY = "MISSING_USER_OPT_IN_POLICY"
    MISSING_AUDIT_POLICY = "MISSING_AUDIT_POLICY"
    MISSING_ROLLBACK_POLICY = "MISSING_ROLLBACK_POLICY"
    MISSING_COST_SLIPPAGE_EVIDENCE = "MISSING_COST_SLIPPAGE_EVIDENCE"
    CNN_FEATURE_GAP_NOTED = "CNN_FEATURE_GAP_NOTED"
    EXCESSIVE_DRAWDOWN = "EXCESSIVE_DRAWDOWN"
    EXCESSIVE_EXPOSURE = "EXCESSIVE_EXPOSURE"
    EXCESSIVE_TURNOVER = "EXCESSIVE_TURNOVER"
    LIVE_PROD_PATH_ATTEMPT = "LIVE_PROD_PATH_ATTEMPT"
    REAL_BROKER_DEPENDENCY = "REAL_BROKER_DEPENDENCY"
    REAL_ACCOUNT_DEPENDENCY = "REAL_ACCOUNT_DEPENDENCY"
    REAL_ORDER_DEPENDENCY = "REAL_ORDER_DEPENDENCY"
    WEBSOCKET_DEPENDENCY = "WEBSOCKET_DEPENDENCY"
    AUTONOMOUS_EXECUTION_PATH = "AUTONOMOUS_EXECUTION_PATH"
    REMOTE_SOURCE_NOT_ALLOWED = "REMOTE_SOURCE_NOT_ALLOWED"
    PARQUET_NOT_ALLOWED = "PARQUET_NOT_ALLOWED"


class ControlledMockReadinessGapEntry(StrictModel):
    gap_id: str = Field(..., min_length=1)
    gap_category: ControlledMockReadinessGapCategory
    severity: str = Field(default="REPORT_ONLY", min_length=1)
    message: str = Field(..., min_length=1)

    @field_validator("gap_id", "severity", mode="before")
    @classmethod
    def normalize_upper(cls, value):
        return _upper_required(value, "gap")

    @field_validator("message", mode="before")
    @classmethod
    def normalize_message(cls, value):
        return _string_required(value, "message")


class _BaseReview(StrictModel):
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


class ControlledMockSafetyPolicy(_BaseReview):
    policy_id: str = Field(..., min_length=1)
    explicit_user_opt_in_required: bool = True
    maximum_simulated_exposure: float = Field(..., ge=0)
    maximum_mock_exposure: float = Field(..., ge=0)
    maximum_inverse_hedge_exposure: float = Field(..., ge=0)
    daily_loss_limit: float = Field(..., ge=0)
    maximum_drawdown_limit: float = Field(..., ge=0)
    order_count_limit: int = Field(..., ge=0)
    cool_down_policy_present: bool = True
    kill_switch_policy_present: bool = True
    fail_closed_policy_present: bool = True
    audit_requirement_present: bool = True
    rollback_requirement_present: bool = True

    @field_validator("policy_id", mode="before")
    @classmethod
    def normalize_id(cls, value):
        return _upper_required(value, "policy_id")

    @model_validator(mode="after")
    def validate_model(self):
        return _validate_safety_flags(self, "controlled mock safety policy")


class ControlledMockReadinessSummaryReport(_BaseReview):
    report_id: str = Field(..., min_length=1)
    decision: ControlledMockReadinessDecision
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
    def validate_model(self):
        return _validate_safety_flags(self, "controlled mock readiness summary report")


class MockReadinessDependencyReport(_BaseReview):
    report_id: str = Field(..., min_length=1)
    paper_eval_decision: str = Field(..., min_length=1)
    policy_decision: str = Field(..., min_length=1)
    ensemble_dependency_present: bool = False
    point_in_time_evidence_present: bool = False
    walk_forward_evidence_present: bool = False
    costs_present: bool = False
    cnn_feature_gap_noted: bool = False

    @field_validator("report_id", "paper_eval_decision", "policy_decision", mode="before")
    @classmethod
    def normalize_upper(cls, value):
        return _upper_required(value, "field")

    @model_validator(mode="after")
    def validate_model(self):
        return _validate_safety_flags(self, "mock readiness dependency report")


class PaperPassEvidenceReport(_BaseReview):
    report_id: str = Field(..., min_length=1)
    paper_eval_passed: bool = False
    drawdown_limit_passed: bool = False
    exposure_limit_passed: bool = False
    turnover_limit_passed: bool = False
    costs_present: bool = False

    @field_validator("report_id", mode="before")
    @classmethod
    def normalize_id(cls, value):
        return _upper_required(value, "report_id")

    @model_validator(mode="after")
    def validate_model(self):
        return _validate_safety_flags(self, "paper pass evidence report")


class MockInfrastructureReadinessReport(_BaseReview):
    report_id: str = Field(..., min_length=1)
    mock_oauth_status: str = Field(..., min_length=1)
    mock_market_data_status: str = Field(..., min_length=1)
    broker_adapter_boundary_present: bool = False
    order_gate_boundary_present: bool = False

    @field_validator("report_id", "mock_oauth_status", "mock_market_data_status", mode="before")
    @classmethod
    def normalize_upper(cls, value):
        return _upper_required(value, "field")

    @model_validator(mode="after")
    def validate_model(self):
        return _validate_safety_flags(self, "mock infrastructure readiness report")


class MockSafetyPolicyReport(_BaseReview):
    report_id: str = Field(..., min_length=1)
    policy: ControlledMockSafetyPolicy

    @field_validator("report_id", mode="before")
    @classmethod
    def normalize_id(cls, value):
        return _upper_required(value, "report_id")

    @model_validator(mode="after")
    def validate_model(self):
        return _validate_safety_flags(self, "mock safety policy report")


class MockBoundaryViolationReport(_BaseReview):
    report_id: str = Field(..., min_length=1)
    live_prod_path_attempt: bool = False
    real_broker_dependency: bool = False
    real_account_dependency: bool = False
    real_order_dependency: bool = False
    websocket_dependency: bool = False
    autonomous_execution_path: bool = False
    missing_kill_switch: bool = False
    missing_opt_in_policy: bool = False
    missing_audit_trail: bool = False
    missing_rollback_policy: bool = False

    @field_validator("report_id", mode="before")
    @classmethod
    def normalize_id(cls, value):
        return _upper_required(value, "report_id")

    @model_validator(mode="after")
    def validate_model(self):
        return _validate_safety_flags(self, "mock boundary violation report")


class ControlledMockReadinessGapReport(_BaseReview):
    gap_report_id: str = Field(..., min_length=1)
    decision: ControlledMockReadinessDecision
    gap_entries: list[ControlledMockReadinessGapEntry] = Field(default_factory=list)
    blocking_gap_count: int = Field(..., ge=0)
    warning_gap_count: int = Field(..., ge=0)

    @field_validator("gap_report_id", mode="before")
    @classmethod
    def normalize_id(cls, value):
        return _upper_required(value, "gap_report_id")

    @model_validator(mode="after")
    def validate_model(self):
        return _validate_safety_flags(self, "controlled mock readiness gap report")


class ControlledMockReadinessAuditRecord(_BaseReview):
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

    @model_validator(mode="after")
    def validate_model(self):
        if not self.redaction_applied or self.contains_secret_material or self.contains_token_material or self.contains_account_material:
            raise ValueError("audit record must remain redacted and non-secret-bearing")
        return _validate_safety_flags(self, "controlled mock readiness audit record")


class ControlledMockReadinessInput(_BaseReview):
    readiness_review_id: str = Field(..., min_length=1)
    paper_evaluation_ref: str | None = None
    paper_evaluation_decision: str | None = None
    allocation_policy_ref: str | None = None
    allocation_policy_decision: str | None = None
    strategy_ensemble_ref: str | None = None
    risk_control_ref: str | None = None
    mock_oauth_readiness_ref: str | None = None
    mock_oauth_readiness_status: str | None = None
    mock_market_data_readiness_ref: str | None = None
    mock_market_data_readiness_status: str | None = None
    broker_adapter_boundary_ref: str | None = None
    order_gate_boundary_ref: str | None = None
    kill_switch_policy_ref: str | None = None
    user_opt_in_policy_ref: str | None = None
    audit_policy_ref: str | None = None
    rollback_policy_ref: str | None = None
    point_in_time_evidence_present: bool = False
    walk_forward_evidence_present: bool = False
    costs_present: bool = False
    cnn_feature_gap_noted: bool = False
    drawdown_limit_passed: bool = False
    exposure_limit_passed: bool = False
    turnover_limit_passed: bool = False
    live_prod_path_attempt: bool = False
    real_broker_dependency: bool = False
    real_account_dependency: bool = False
    real_order_dependency: bool = False
    websocket_dependency: bool = False
    autonomous_execution_path: bool = False
    safety_policy: ControlledMockSafetyPolicy
    audit_records: list[ControlledMockReadinessAuditRecord] = Field(default_factory=list)
    summary_report: ControlledMockReadinessSummaryReport | None = None
    dependency_report: MockReadinessDependencyReport | None = None
    paper_pass_evidence_report: PaperPassEvidenceReport | None = None
    infrastructure_readiness_report: MockInfrastructureReadinessReport | None = None
    safety_policy_report: MockSafetyPolicyReport | None = None
    boundary_violation_report: MockBoundaryViolationReport | None = None
    gap_report: ControlledMockReadinessGapReport | None = None

    @field_validator("readiness_review_id", mode="before")
    @classmethod
    def normalize_id(cls, value):
        return _upper_required(value, "readiness_review_id")

    @field_validator(
        "paper_evaluation_decision",
        "allocation_policy_decision",
        "mock_oauth_readiness_status",
        "mock_market_data_readiness_status",
        mode="before",
    )
    @classmethod
    def normalize_optional_upper(cls, value):
        if value is None:
            return None
        return _upper_required(value, "decision")

    @field_validator(
        "paper_evaluation_ref",
        "allocation_policy_ref",
        "strategy_ensemble_ref",
        "risk_control_ref",
        "mock_oauth_readiness_ref",
        "mock_market_data_readiness_ref",
        "broker_adapter_boundary_ref",
        "order_gate_boundary_ref",
        "kill_switch_policy_ref",
        "user_opt_in_policy_ref",
        "audit_policy_ref",
        "rollback_policy_ref",
        mode="before",
    )
    @classmethod
    def normalize_optional_ref(cls, value):
        if value is None:
            return None
        cleaned = str(value).strip()
        return cleaned or None

    @model_validator(mode="after")
    def validate_model(self):
        if not self.audit_records:
            raise ValueError("audit_records must not be empty")
        return _validate_safety_flags(self, "controlled mock readiness input")
