from datetime import datetime
from enum import StrEnum
from uuid import uuid4

from pydantic import Field

from stock_risk_mcp.models import StrictModel


class SandboxSellSchemaVerificationStatus(StrEnum):
    VERIFIED = "VERIFIED"
    UNVERIFIED = "UNVERIFIED"
    AMBIGUOUS = "AMBIGUOUS"
    MISSING_REQUIRED_FIELD = "MISSING_REQUIRED_FIELD"
    BLOCKED_UNOFFICIAL_ASSUMPTION = "BLOCKED_UNOFFICIAL_ASSUMPTION"


class SandboxSellSchemaFieldEvidence(StrictModel):
    field_evidence_id: str = Field(default_factory=lambda: f"sell_schema_field_{uuid4().hex}")
    report_id: str
    field_name: str
    status: SandboxSellSchemaVerificationStatus
    source_reference: str | None = None
    notes: str | None = None
    observed_at: datetime = Field(default_factory=datetime.now)
    metadata_json: dict = Field(default_factory=lambda: {"redacted": True, "network_called": False})


class SandboxSellSchemaVerificationReport(StrictModel):
    report_id: str = Field(default_factory=lambda: f"sell_schema_report_{uuid4().hex}")
    status: SandboxSellSchemaVerificationStatus
    endpoint_id: str
    endpoint_path: str | None = None
    endpoint_classification: str = "UNKNOWN_REVIEW_REQUIRED"
    verified_fields: list[str] = Field(default_factory=list)
    missing_fields: list[str] = Field(default_factory=list)
    ambiguous_fields: list[str] = Field(default_factory=list)
    blocked_reason: str | None = None
    source_references: list[str] = Field(default_factory=list)
    fields: list[SandboxSellSchemaFieldEvidence] = Field(default_factory=list)
    observed_at: datetime = Field(default_factory=datetime.now)
    metadata_json: dict = Field(default_factory=lambda: {
        "redacted": True, "network_called": False, "credentials_read": False,
        "token_requested": False, "orders_submitted": False,
    })


class SandboxSellDryRunStatus(StrEnum):
    APPROVED_FOR_DRY_RUN = "APPROVED_FOR_DRY_RUN"
    BLOCKED = "BLOCKED"


class SandboxSellDryRunDecision(StrictModel):
    dry_run_id: str = Field(default_factory=lambda: f"sell_dry_run_{uuid4().hex}")
    order_intent_id: str
    status: SandboxSellDryRunStatus
    schema_report_id: str | None = None
    reasons_json: list[str] = Field(default_factory=list)
    planned_order_metadata_json: dict = Field(default_factory=dict)
    observed_at: datetime = Field(default_factory=datetime.now)
    metadata_json: dict = Field(default_factory=lambda: {
        "redacted": True, "network_called": False, "credentials_read": False,
        "token_requested": False, "orders_submitted": False,
    })
