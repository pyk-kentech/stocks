import json
import pytest

from stock_risk_mcp.kiwoom_official_sell_schema_evidence import (
    OfficialSellSchemaEvidenceReviewStatus,
)
from stock_risk_mcp.kiwoom_official_sell_schema_evidence_service import (
    KiwoomOfficialSellSchemaEvidenceService,
)
from stock_risk_mcp.repository import RiskRepository
from tests.test_kiwoom_official_sell_schema_evidence import _payload, _write


def test_import_stores_normalized_evidence_fields_checksum_and_no_raw_file(tmp_path):
    repository = RiskRepository(tmp_path / "risk.sqlite3")
    service = KiwoomOfficialSellSchemaEvidenceService(repository)
    path = _write(tmp_path / "evidence.json", _payload())

    report = service.import_evidence(path)
    evidence = repository.get_official_sell_schema_evidence("official-sell-1")
    payload = json.dumps(evidence.model_dump(mode="json")).lower()

    assert report.status == OfficialSellSchemaEvidenceReviewStatus.IMPORTED
    assert len(evidence.checksum) == 64
    assert len(repository.list_official_sell_schema_evidence_fields(evidence.evidence_id)) == 9
    assert repository.list_official_sell_schema_evidence_imports()
    assert str(path).lower() not in payload
    assert "raw_payload" not in payload


def test_reviews_are_append_only_and_latest_status_is_used(tmp_path):
    repository = RiskRepository(tmp_path / "risk.sqlite3")
    service = KiwoomOfficialSellSchemaEvidenceService(repository)
    service.import_evidence(_write(tmp_path / "evidence.json", _payload()))

    first = service.review("official-sell-1", OfficialSellSchemaEvidenceReviewStatus.VALIDATED, "reviewer")
    second = service.review("official-sell-1", OfficialSellSchemaEvidenceReviewStatus.SUPERSEDED, "reviewer")
    reviews = repository.list_official_sell_schema_evidence_reviews("official-sell-1")

    assert first.review_id != second.review_id
    assert len(reviews) == 2
    assert repository.get_latest_official_sell_schema_evidence_review("official-sell-1").status == OfficialSellSchemaEvidenceReviewStatus.SUPERSEDED


def test_review_rejects_sensitive_notes(tmp_path):
    repository = RiskRepository(tmp_path / "risk.sqlite3")
    service = KiwoomOfficialSellSchemaEvidenceService(repository)
    service.import_evidence(_write(tmp_path / "evidence.json", _payload()))

    with pytest.raises(ValueError, match="sensitive"):
        service.review(
            "official-sell-1", OfficialSellSchemaEvidenceReviewStatus.VALIDATED,
            notes="authorization: Bearer real-token",
        )
