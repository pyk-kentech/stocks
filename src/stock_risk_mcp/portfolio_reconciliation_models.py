from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from pydantic import Field, field_validator, model_validator

from stock_risk_mcp.account_read_models import AccountReadSnapshot, _aware, _normalize_list, _string_required, _upper_required, _validate_safety_flags
from stock_risk_mcp.feature_store_models import FeatureStoreAuditRecord
from stock_risk_mcp.models import StrictModel
from stock_risk_mcp.paper_evaluation_models import (
    PaperEvaluationPipelineResult,
    PaperEvaluationPortfolioSnapshot,
    PaperEvaluationPosition,
    PaperEvaluationTrade,
)


class PortfolioReconciliationReadinessStatus(StrEnum):
    RECONCILIATION_READY = "RECONCILIATION_READY"
    RECONCILIATION_REPORT_READY = "RECONCILIATION_REPORT_READY"
    ACCOUNT_DATA_GAP = "ACCOUNT_DATA_GAP"
    PAPER_DATA_GAP = "PAPER_DATA_GAP"
    TARGET_DATA_GAP = "TARGET_DATA_GAP"
    DATA_GAP = "DATA_GAP"
    STALE = "STALE"
    CONFLICT = "CONFLICT"
    RESEARCH_ONLY = "RESEARCH_ONLY"
    BLOCKED = "BLOCKED"


class PortfolioComparisonBasis(StrEnum):
    PAPER_VS_ACCOUNT = "PAPER_VS_ACCOUNT"
    TARGET_VS_ACCOUNT = "TARGET_VS_ACCOUNT"


class PortfolioMismatchStatus(StrEnum):
    MATCH = "MATCH"
    QUANTITY_MISMATCH = "QUANTITY_MISMATCH"
    PRICE_MISMATCH = "PRICE_MISMATCH"
    VALUE_MISMATCH = "VALUE_MISMATCH"
    ACCOUNT_ONLY = "ACCOUNT_ONLY"
    PAPER_ONLY = "PAPER_ONLY"
    TARGET_ONLY = "TARGET_ONLY"
    DATA_GAP = "DATA_GAP"


class V13ReadinessTier(StrEnum):
    NOT_READY = "NOT_READY"
    PARTIAL = "PARTIAL"
    READY_FOR_MANUAL_REVIEW = "READY_FOR_MANUAL_REVIEW"


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
    account_read_only: bool = True


class TargetPortfolioPosition(StrictModel):
    instrument_id: str = Field(..., min_length=1)
    market: str = Field(..., min_length=1)
    currency: str = Field(..., min_length=1)
    quantity: float
    target_weight: float | None = None
    average_cost: float | None = None

    @field_validator("instrument_id", "market", "currency", mode="before")
    @classmethod
    def normalize_upper(cls, value, info):
        return _upper_required(value, info.field_name)


class PortfolioReconciliationPlanReport(_BaseSafety):
    report_id: str = Field(..., min_length=1)
    dataset_id: str = Field(..., min_length=1)
    account_snapshot_id: str = Field(..., min_length=1)
    readiness_status: PortfolioReconciliationReadinessStatus
    comparison_bases: list[PortfolioComparisonBasis] = Field(default_factory=list)
    target_positions_supplied: bool = False
    v13_readiness_tier: V13ReadinessTier = V13ReadinessTier.NOT_READY

    @field_validator("report_id", "dataset_id", "account_snapshot_id", mode="before")
    @classmethod
    def normalize_upper(cls, value, info):
        return _upper_required(value, info.field_name)

    @model_validator(mode="after")
    def validate_model(self):
        return _validate_safety_flags(self, "portfolio reconciliation plan report")


class PortfolioMismatchEntry(StrictModel):
    mismatch_id: str = Field(..., min_length=1)
    comparison_basis: PortfolioComparisonBasis
    instrument_id: str = Field(..., min_length=1)
    mismatch_status: PortfolioMismatchStatus
    paper_quantity: float | None = None
    account_quantity: float | None = None
    target_quantity: float | None = None
    quantity_delta: float | None = None
    paper_average_cost: float | None = None
    account_average_cost: float | None = None
    average_cost_delta: float | None = None
    notes: list[str] = Field(default_factory=list)

    @field_validator("mismatch_id", "instrument_id", mode="before")
    @classmethod
    def normalize_upper(cls, value, info):
        return _upper_required(value, info.field_name)

    @field_validator("notes", mode="before")
    @classmethod
    def normalize_notes(cls, value):
        return _normalize_list(value, "notes")


class PortfolioReconciliationReport(_BaseSafety):
    report_id: str = Field(..., min_length=1)
    dataset_id: str = Field(..., min_length=1)
    account_snapshot_id: str = Field(..., min_length=1)
    readiness_status: PortfolioReconciliationReadinessStatus
    paper_vs_account_match_count: int = Field(default=0, ge=0)
    paper_vs_account_mismatch_count: int = Field(default=0, ge=0)
    target_vs_account_match_count: int = Field(default=0, ge=0)
    target_vs_account_mismatch_count: int = Field(default=0, ge=0)
    mismatch_entries: list[PortfolioMismatchEntry] = Field(default_factory=list)
    comparison_notes: list[str] = Field(default_factory=list)

    @field_validator("report_id", "dataset_id", "account_snapshot_id", mode="before")
    @classmethod
    def normalize_upper(cls, value, info):
        return _upper_required(value, info.field_name)

    @field_validator("comparison_notes", mode="before")
    @classmethod
    def normalize_comparison_notes(cls, value):
        return _normalize_list(value, "comparison_notes", upper=True)

    @model_validator(mode="after")
    def validate_model(self):
        return _validate_safety_flags(self, "portfolio reconciliation report")


class PortfolioMismatchReport(_BaseSafety):
    report_id: str = Field(..., min_length=1)
    dataset_id: str = Field(..., min_length=1)
    mismatch_entries: list[PortfolioMismatchEntry] = Field(default_factory=list)

    @field_validator("report_id", "dataset_id", mode="before")
    @classmethod
    def normalize_upper(cls, value, info):
        return _upper_required(value, info.field_name)

    @model_validator(mode="after")
    def validate_model(self):
        return _validate_safety_flags(self, "portfolio mismatch report")


class PortfolioReconciliationReadinessReport(_BaseSafety):
    report_id: str = Field(..., min_length=1)
    dataset_id: str = Field(..., min_length=1)
    readiness_status: PortfolioReconciliationReadinessStatus
    v13_readiness_tier: V13ReadinessTier
    findings: list[str] = Field(default_factory=list)

    @field_validator("report_id", "dataset_id", mode="before")
    @classmethod
    def normalize_upper(cls, value, info):
        return _upper_required(value, info.field_name)

    @field_validator("findings", mode="before")
    @classmethod
    def normalize_findings(cls, value):
        return _normalize_list(value, "findings", upper=True)

    @model_validator(mode="after")
    def validate_model(self):
        return _validate_safety_flags(self, "portfolio reconciliation readiness report")


class PortfolioReconciliationIntegrationReport(_BaseSafety):
    report_id: str = Field(..., min_length=1)
    dataset_id: str = Field(..., min_length=1)
    paper_portfolio_ready: bool = False
    paper_trade_ready: bool = False
    account_snapshot_ready: bool = False
    target_positions_ready: bool = False
    average_cost_comparison_ready: bool = False
    provider_gap_propagated: bool = False
    explicit_read_only_contract: bool = True

    @field_validator("report_id", "dataset_id", mode="before")
    @classmethod
    def normalize_upper(cls, value, info):
        return _upper_required(value, info.field_name)

    @model_validator(mode="after")
    def validate_model(self):
        return _validate_safety_flags(self, "portfolio reconciliation integration report")


class PortfolioReconciliationSafetyReport(_BaseSafety):
    report_id: str = Field(..., min_length=1)
    dataset_id: str = Field(..., min_length=1)
    findings: list[str] = Field(default_factory=list)

    @field_validator("report_id", "dataset_id", mode="before")
    @classmethod
    def normalize_upper(cls, value, info):
        return _upper_required(value, info.field_name)

    @field_validator("findings", mode="before")
    @classmethod
    def normalize_findings(cls, value):
        return _normalize_list(value, "findings", upper=True)

    @model_validator(mode="after")
    def validate_model(self):
        return _validate_safety_flags(self, "portfolio reconciliation safety report")


class PortfolioReconciliationGapEntry(StrictModel):
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


class PortfolioReconciliationGapReport(_BaseSafety):
    report_id: str = Field(..., min_length=1)
    dataset_id: str = Field(..., min_length=1)
    readiness_status: PortfolioReconciliationReadinessStatus
    gap_entries: list[PortfolioReconciliationGapEntry] = Field(default_factory=list)

    @field_validator("report_id", "dataset_id", mode="before")
    @classmethod
    def normalize_upper(cls, value, info):
        return _upper_required(value, info.field_name)

    @model_validator(mode="after")
    def validate_model(self):
        return _validate_safety_flags(self, "portfolio reconciliation gap report")


class PortfolioReconciliationPipelineInput(_BaseSafety):
    pipeline_id: str = Field(..., min_length=1)
    dataset_id: str = Field(..., min_length=1)
    paper_evaluation: PaperEvaluationPipelineResult
    account_snapshot: AccountReadSnapshot
    target_positions: list[TargetPortfolioPosition] = Field(default_factory=list)
    audit_records: list[FeatureStoreAuditRecord] = Field(default_factory=list)
    evaluated_at: datetime

    @field_validator("pipeline_id", "dataset_id", mode="before")
    @classmethod
    def normalize_upper(cls, value, info):
        return _upper_required(value, info.field_name)

    @field_validator("evaluated_at", mode="before")
    @classmethod
    def normalize_dt(cls, value):
        return _aware(value)

    @model_validator(mode="after")
    def validate_model(self):
        return _validate_safety_flags(self, "portfolio reconciliation pipeline input")


class PortfolioReconciliationPipelineResult(StrictModel):
    plan_report: PortfolioReconciliationPlanReport
    reconciliation_report: PortfolioReconciliationReport
    mismatch_report: PortfolioMismatchReport
    readiness_report: PortfolioReconciliationReadinessReport
    integration_report: PortfolioReconciliationIntegrationReport
    safety_report: PortfolioReconciliationSafetyReport
    gap_report: PortfolioReconciliationGapReport
