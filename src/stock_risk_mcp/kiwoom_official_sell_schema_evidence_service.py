import json
import re
from hashlib import sha256
from pathlib import Path

import yaml

from stock_risk_mcp.kiwoom_official_manifest import (
    KiwoomOfficialEndpointClass,
    load_kiwoom_official_manifest,
)
from stock_risk_mcp.kiwoom_official_sell_schema_evidence import (
    OfficialSellSchemaEvidence,
    OfficialSellSchemaEvidenceField,
    OfficialSellSchemaEvidenceImportReport,
    OfficialSellSchemaEvidenceReview,
    OfficialSellSchemaEvidenceReviewStatus,
    OfficialSellSchemaEvidenceValidationResult,
)


REQUIRED_REQUEST_FIELDS = (
    "side_field", "buy_side_value", "sell_side_value", "order_type_field",
    "limit_order_type_value", "symbol_field", "quantity_field",
    "limit_price_field", "account_field",
)
SENSITIVE_PATTERN = re.compile(
    r"(authorization\s*:|bearer\s+\S+|appkey|secretkey|access[_ -]?token|"
    r"refresh[_ -]?token|account[_ -]?number\s*[:=]\s*\d{6,})",
    re.IGNORECASE,
)


class KiwoomOfficialSellSchemaEvidenceService:
    def __init__(self, repository=None) -> None:
        self.repository = repository

    def validate(self, evidence_file: Path) -> OfficialSellSchemaEvidenceValidationResult:
        path = Path(evidence_file)
        if not path.is_file():
            return OfficialSellSchemaEvidenceValidationResult(
                valid=False, review_status=OfficialSellSchemaEvidenceReviewStatus.REJECTED,
                checksum="", errors=["EVIDENCE_FILE_NOT_FOUND"],
            )
        raw = path.read_bytes()
        checksum = sha256(raw).hexdigest()
        text = raw.decode("utf-8")
        if SENSITIVE_PATTERN.search(text):
            return self._invalid(checksum, ["SENSITIVE_CONTENT_BLOCKED"])
        try:
            payload = yaml.safe_load(text) if path.suffix.lower() in {".yaml", ".yml"} else json.loads(text)
        except (ValueError, yaml.YAMLError, UnicodeDecodeError):
            return self._invalid(checksum, ["INVALID_EVIDENCE_FILE"])
        errors = []
        if payload.get("source_kind") != "OFFICIAL_KIWOOM_DOCUMENTATION":
            errors.append("OFFICIAL_SOURCE_REQUIRED")
        endpoint = next(
            (item for item in load_kiwoom_official_manifest().endpoints if item.api_id == payload.get("endpoint_id")),
            None,
        )
        if endpoint is None or endpoint.read_write_class != KiwoomOfficialEndpointClass.ORDER:
            errors.append("OFFICIAL_ORDER_ENDPOINT_REQUIRED")
        elif (
            endpoint.path != payload.get("endpoint_path")
            or endpoint.method != payload.get("method")
            or payload.get("endpoint_classification") != KiwoomOfficialEndpointClass.ORDER.value
        ):
            errors.append("MANIFEST_ENDPOINT_MISMATCH")
        fields = payload.get("request_fields") if isinstance(payload.get("request_fields"), dict) else {}
        missing = [name for name in REQUIRED_REQUEST_FIELDS if not fields.get(name)]
        values = [str(value).lower() for value in fields.values()]
        if any("guess" in value or "ambiguous" in value or "infer" in value for value in values):
            errors.append("GUESSED_OR_AMBIGUOUS_VALUE_BLOCKED")
        for name in ("idempotency_notes", "redaction_policy"):
            if not payload.get(name):
                missing.append(name)
        try:
            evidence = OfficialSellSchemaEvidence(
                **payload, checksum=checksum,
            )
        except (TypeError, ValueError):
            evidence = None
            errors.append("INVALID_EVIDENCE_SCHEMA")
        valid = not errors and not missing and evidence is not None
        return OfficialSellSchemaEvidenceValidationResult(
            valid=valid,
            review_status=OfficialSellSchemaEvidenceReviewStatus.NEEDS_MANUAL_REVIEW
            if valid else OfficialSellSchemaEvidenceReviewStatus.REJECTED,
            checksum=checksum,
            evidence=evidence if valid else None,
            missing_fields=list(dict.fromkeys(missing)),
            errors=list(dict.fromkeys(errors)),
        )

    def import_evidence(self, evidence_file: Path) -> OfficialSellSchemaEvidenceImportReport:
        result = self.validate(evidence_file)
        report = OfficialSellSchemaEvidenceImportReport(
            evidence_id=result.evidence.evidence_id if result.evidence else None,
            checksum=result.checksum,
            status=OfficialSellSchemaEvidenceReviewStatus.IMPORTED
            if result.valid else OfficialSellSchemaEvidenceReviewStatus.REJECTED,
            errors=result.errors,
        )
        if self.repository:
            if result.valid and result.evidence:
                self.repository.save_official_sell_schema_evidence(result.evidence)
                for name, value in result.evidence.request_fields.items():
                    self.repository.save_official_sell_schema_evidence_field(
                        OfficialSellSchemaEvidenceField(
                            evidence_id=result.evidence.evidence_id,
                            field_name=name,
                            documented_value=value,
                        )
                    )
            self.repository.save_official_sell_schema_evidence_import(report)
        return report

    def review(
        self,
        evidence_id: str,
        status: OfficialSellSchemaEvidenceReviewStatus,
        reviewed_by: str | None = None,
        notes: str | None = None,
    ) -> OfficialSellSchemaEvidenceReview:
        if SENSITIVE_PATTERN.search(f"{reviewed_by or ''} {notes or ''}"):
            raise ValueError("sensitive review metadata blocked")
        if status not in {
            OfficialSellSchemaEvidenceReviewStatus.VALIDATED,
            OfficialSellSchemaEvidenceReviewStatus.REJECTED,
            OfficialSellSchemaEvidenceReviewStatus.SUPERSEDED,
            OfficialSellSchemaEvidenceReviewStatus.NEEDS_MANUAL_REVIEW,
        }:
            raise ValueError("review status is not allowed")
        if not self.repository:
            raise ValueError("repository required")
        self.repository.get_official_sell_schema_evidence(evidence_id)
        review = OfficialSellSchemaEvidenceReview(
            evidence_id=evidence_id, status=status, reviewed_by=reviewed_by, notes=notes,
        )
        self.repository.save_official_sell_schema_evidence_review(review)
        return review

    @staticmethod
    def _invalid(checksum: str, errors: list[str]) -> OfficialSellSchemaEvidenceValidationResult:
        return OfficialSellSchemaEvidenceValidationResult(
            valid=False, review_status=OfficialSellSchemaEvidenceReviewStatus.REJECTED,
            checksum=checksum, errors=errors,
        )
