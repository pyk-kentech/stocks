from datetime import datetime
from enum import StrEnum
from uuid import uuid4

from pydantic import Field

from stock_risk_mcp.models import StrictModel


class OfficialSellSchemaEvidenceReviewStatus(StrEnum):
    IMPORTED = "IMPORTED"
    VALIDATED = "VALIDATED"
    REJECTED = "REJECTED"
    NEEDS_MANUAL_REVIEW = "NEEDS_MANUAL_REVIEW"
    SUPERSEDED = "SUPERSEDED"


class OfficialSellSchemaEvidenceField(StrictModel):
    evidence_field_id: str = Field(default_factory=lambda: f"official_sell_field_{uuid4().hex}")
    evidence_id: str
    field_name: str
    documented_value: str
    observed_at: datetime = Field(default_factory=datetime.now)
    metadata_json: dict = Field(default_factory=lambda: {"redacted": True, "network_called": False})


class OfficialSellSchemaEvidence(StrictModel):
    evidence_id: str
    source_kind: str
    source_title: str
    source_url: str | None = None
    captured_at: datetime
    endpoint_id: str
    endpoint_path: str
    method: str
    endpoint_classification: str
    environment_support: list[str] = Field(default_factory=list)
    request_fields: dict[str, str] = Field(default_factory=dict)
    idempotency_notes: str
    redaction_policy: str
    checksum: str
    notes: str | None = None
    observed_at: datetime = Field(default_factory=datetime.now)
    metadata_json: dict = Field(default_factory=lambda: {"redacted": True, "network_called": False})


class OfficialSellSchemaEvidenceValidationResult(StrictModel):
    valid: bool
    review_status: OfficialSellSchemaEvidenceReviewStatus
    checksum: str
    evidence: OfficialSellSchemaEvidence | None = None
    missing_fields: list[str] = Field(default_factory=list)
    ambiguous_fields: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)
    metadata_json: dict = Field(default_factory=lambda: {
        "redacted": True, "network_called": False, "credentials_read": False,
        "token_requested": False,
    })


class OfficialSellSchemaEvidenceImportReport(StrictModel):
    import_id: str = Field(default_factory=lambda: f"official_sell_import_{uuid4().hex}")
    evidence_id: str | None = None
    checksum: str
    status: OfficialSellSchemaEvidenceReviewStatus
    errors: list[str] = Field(default_factory=list)
    observed_at: datetime = Field(default_factory=datetime.now)
    metadata_json: dict = Field(default_factory=lambda: {"redacted": True, "network_called": False})


class OfficialSellSchemaEvidenceReview(StrictModel):
    review_id: str = Field(default_factory=lambda: f"official_sell_review_{uuid4().hex}")
    evidence_id: str
    status: OfficialSellSchemaEvidenceReviewStatus
    reviewed_by: str | None = None
    notes: str | None = None
    observed_at: datetime = Field(default_factory=datetime.now)
    metadata_json: dict = Field(default_factory=lambda: {"redacted": True, "network_called": False})
