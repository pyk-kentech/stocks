import json
import yaml

from stock_risk_mcp.kiwoom_official_sell_schema_evidence import (
    OfficialSellSchemaEvidenceReviewStatus,
)
from stock_risk_mcp.kiwoom_official_sell_schema_evidence_service import (
    KiwoomOfficialSellSchemaEvidenceService,
)


def _payload():
    return {
        "evidence_id": "official-sell-1",
        "source_kind": "OFFICIAL_KIWOOM_DOCUMENTATION",
        "source_title": "Official stock order documentation",
        "source_url": "https://openapi.kiwoom.com/m/guide/apiguide?jobTpCode=13",
        "captured_at": "2026-06-15T00:00:00",
        "endpoint_id": "kt10000",
        "endpoint_path": "/api/dostk/ordr",
        "method": "POST",
        "endpoint_classification": "ORDER",
        "environment_support": ["MOCK"],
        "request_fields": {
            "side_field": "documented_side",
            "buy_side_value": "documented_buy",
            "sell_side_value": "documented_sell",
            "order_type_field": "documented_order_type",
            "limit_order_type_value": "documented_limit",
            "symbol_field": "documented_symbol",
            "quantity_field": "documented_quantity",
            "limit_price_field": "documented_limit_price",
            "account_field": "redacted_account_reference",
        },
        "idempotency_notes": "client order id is locally deduplicated before transport",
        "redaction_policy": "account values and credentials are never persisted",
        "notes": "manually captured official schema metadata",
    }


def _write(path, payload):
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def test_validate_explicit_official_evidence_file_is_offline_and_has_checksum(tmp_path):
    path = _write(tmp_path / "evidence.json", _payload())

    result = KiwoomOfficialSellSchemaEvidenceService().validate(path)

    assert result.valid is True
    assert result.review_status == OfficialSellSchemaEvidenceReviewStatus.NEEDS_MANUAL_REVIEW
    assert len(result.checksum) == 64
    assert result.metadata_json["network_called"] is False
    assert result.metadata_json["credentials_read"] is False
    assert result.metadata_json["token_requested"] is False


def test_missing_mapping_and_non_order_endpoint_are_rejected(tmp_path):
    missing = _payload()
    missing["request_fields"].pop("sell_side_value")
    non_order = _payload()
    non_order["endpoint_id"] = "ka10001"
    non_order["endpoint_path"] = "/api/dostk/stkinfo"
    non_order["endpoint_classification"] = "READ_ONLY"

    missing_result = KiwoomOfficialSellSchemaEvidenceService().validate(_write(tmp_path / "missing.json", missing))
    non_order_result = KiwoomOfficialSellSchemaEvidenceService().validate(_write(tmp_path / "readonly.json", non_order))

    assert "sell_side_value" in missing_result.missing_fields
    assert "OFFICIAL_ORDER_ENDPOINT_REQUIRED" in non_order_result.errors


def test_unofficial_guessed_and_sensitive_evidence_are_rejected(tmp_path):
    unofficial = _payload()
    unofficial["source_kind"] = "UNOFFICIAL_WRAPPER"
    guessed = _payload()
    guessed["request_fields"]["sell_side_value"] = "guessed:01"
    sensitive = _payload()
    sensitive["notes"] = "authorization: Bearer real-token account_number=12345678"

    service = KiwoomOfficialSellSchemaEvidenceService()
    unofficial_result = service.validate(_write(tmp_path / "unofficial.json", unofficial))
    guessed_result = service.validate(_write(tmp_path / "guessed.json", guessed))
    sensitive_result = service.validate(_write(tmp_path / "sensitive.json", sensitive))

    assert "OFFICIAL_SOURCE_REQUIRED" in unofficial_result.errors
    assert "GUESSED_OR_AMBIGUOUS_VALUE_BLOCKED" in guessed_result.errors
    assert "SENSITIVE_CONTENT_BLOCKED" in sensitive_result.errors


def test_missing_evidence_file_returns_safe_validation_error(tmp_path):
    result = KiwoomOfficialSellSchemaEvidenceService().validate(tmp_path / "missing.json")
    assert result.valid is False
    assert result.errors == ["EVIDENCE_FILE_NOT_FOUND"]


def test_explicit_yaml_evidence_file_is_supported(tmp_path):
    path = tmp_path / "evidence.yaml"
    path.write_text(yaml.safe_dump(_payload()), encoding="utf-8")
    assert KiwoomOfficialSellSchemaEvidenceService().validate(path).valid is True
