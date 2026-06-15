from stock_risk_mcp.kiwoom_official_manifest import (
    KiwoomOfficialEndpointClass,
    load_kiwoom_official_manifest,
)
from stock_risk_mcp.kiwoom_real_readonly_models import KiwoomRealNetworkEnvironment
from stock_risk_mcp.kiwoom_sandbox_sell_schema import (
    SandboxSellSchemaFieldEvidence,
    SandboxSellSchemaVerificationReport,
    SandboxSellSchemaVerificationStatus,
)
from stock_risk_mcp.kiwoom_official_sell_schema_evidence import OfficialSellSchemaEvidenceReviewStatus


REQUIRED_MAPPING_FIELDS = (
    "side_field", "buy_side_value", "sell_side_value", "order_type_field",
    "limit_order_type_value", "symbol_field", "quantity_field",
    "limit_price_field", "account_field",
)


class KiwoomSandboxSellSchemaVerifier:
    def __init__(self, repository=None) -> None:
        self.repository = repository

    def verify(
        self,
        endpoint_id: str = "kt10000",
        field_mapping: dict | None = None,
        evidence_source: str = "project-local-official-manifest",
        environment: KiwoomRealNetworkEnvironment = KiwoomRealNetworkEnvironment.MOCK,
    ) -> SandboxSellSchemaVerificationReport:
        endpoint = next(
            (item for item in load_kiwoom_official_manifest().endpoints if item.api_id == endpoint_id),
            None,
        )
        verified = []
        missing = []
        blocked_reason = None
        reviewed_evidence = None
        status = SandboxSellSchemaVerificationStatus.UNVERIFIED
        if environment != KiwoomRealNetworkEnvironment.MOCK:
            status = SandboxSellSchemaVerificationStatus.BLOCKED_UNOFFICIAL_ASSUMPTION
            blocked_reason = "PROD_SELL_SCHEMA_VERIFICATION_BLOCKED"
        elif endpoint is None:
            status = SandboxSellSchemaVerificationStatus.MISSING_REQUIRED_FIELD
            blocked_reason = "OFFICIAL_ORDER_ENDPOINT_NOT_FOUND"
        elif endpoint.read_write_class != KiwoomOfficialEndpointClass.ORDER or "websocket" in endpoint.path.lower():
            status = SandboxSellSchemaVerificationStatus.BLOCKED_UNOFFICIAL_ASSUMPTION
            blocked_reason = "NON_ORDER_SELL_SCHEMA_ENDPOINT_BLOCKED"
        elif evidence_source != "project-local-official-manifest" or field_mapping:
            status = SandboxSellSchemaVerificationStatus.BLOCKED_UNOFFICIAL_ASSUMPTION
            blocked_reason = "UNOFFICIAL_SELL_SCHEMA_ASSUMPTION_BLOCKED"
        else:
            verified = ["endpoint_id", "endpoint_path", "endpoint_method", "endpoint_classification"]
            missing = list(REQUIRED_MAPPING_FIELDS)
            reviewed_evidence = self._reviewed_evidence(endpoint_id)
            if reviewed_evidence:
                verified.extend(REQUIRED_MAPPING_FIELDS)
                missing = []
                status = SandboxSellSchemaVerificationStatus.VERIFIED
                blocked_reason = None
        report = SandboxSellSchemaVerificationReport(
            status=status,
            endpoint_id=endpoint_id,
            endpoint_path=endpoint.path if endpoint else None,
            endpoint_classification=endpoint.read_write_class.value if endpoint else "UNKNOWN_REVIEW_REQUIRED",
            verified_fields=verified,
            missing_fields=missing,
            blocked_reason=blocked_reason,
            source_references=list(dict.fromkeys([
                *([endpoint.source] if endpoint else []),
                *([reviewed_evidence.source_url] if reviewed_evidence and reviewed_evidence.source_url else []),
            ])),
            metadata_json={
                "redacted": True, "network_called": False, "credentials_read": False,
                "token_requested": False, "orders_submitted": False,
                "official_evidence_id": reviewed_evidence.evidence_id if reviewed_evidence else None,
            },
        )
        report.fields = [
            SandboxSellSchemaFieldEvidence(
                report_id=report.report_id,
                field_name=name,
                status=SandboxSellSchemaVerificationStatus.VERIFIED
                if name in verified else SandboxSellSchemaVerificationStatus.MISSING_REQUIRED_FIELD,
                source_reference=report.source_references[0] if report.source_references else None,
            )
            for name in [*verified, *missing]
        ]
        if self.repository:
            self.repository.save_kiwoom_sandbox_sell_schema_report(report)
        return report

    def _reviewed_evidence(self, endpoint_id: str):
        if not self.repository:
            return None
        for evidence in self.repository.list_official_sell_schema_evidence():
            review = self.repository.get_latest_official_sell_schema_evidence_review(evidence.evidence_id)
            if (
                evidence.endpoint_id == endpoint_id
                and review is not None
                and review.status == OfficialSellSchemaEvidenceReviewStatus.VALIDATED
                and all(evidence.request_fields.get(name) for name in REQUIRED_MAPPING_FIELDS)
            ):
                return evidence
        return None
