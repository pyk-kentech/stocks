import json

import pytest

from stock_risk_mcp.kiwoom_manual_response_import_fixture import load_kiwoom_manual_response_import_fixture
from stock_risk_mcp.kiwoom_manual_response_import_guard import validate_kiwoom_manual_response_import_metadata_safety
from stock_risk_mcp.kiwoom_manual_response_import_models import (
    KiwoomManualResponseApiClassification,
    KiwoomManualResponseImportReadiness,
    KiwoomManualResponseImportRequest,
)


def kiwoom_manual_response_import_payload(response_file: str, **overrides):
    payload = {
        "request_id": "MANUAL-IMPORT-1",
        "files": [
            {
                "file_path": response_file,
                "declared_api_id": "KA10081",
                "provider_symbol": "005930",
                "canonical_instrument_key": "005930_KRX",
                "available_at": "2026-06-25T15:35:00+09:00",
                "source_ref": response_file,
            }
        ],
        "compose_snapshot": False,
        "strict_mode": True,
    }
    payload.update(overrides)
    return payload


def test_manual_response_import_request_defaults_to_local_offline_readonly(tmp_path):
    response_file = tmp_path / "ka10081_response.json"
    response_file.write_text("{}", encoding="utf-8")
    loaded = KiwoomManualResponseImportRequest.model_validate(kiwoom_manual_response_import_payload(str(response_file)))
    assert loaded.local_file_only is True
    assert loaded.offline_only is True
    assert loaded.report_only is True
    assert loaded.no_network is True


def test_manual_response_import_fixture_loader_reads_local_json_only(tmp_path):
    response_file = tmp_path / "ka10081_response.json"
    response_file.write_text("{}", encoding="utf-8")
    fixture_path = tmp_path / "manual_import_fixture.json"
    fixture_path.write_text(json.dumps(kiwoom_manual_response_import_payload(str(response_file))), encoding="utf-8")
    loaded = load_kiwoom_manual_response_import_fixture(fixture_path)
    assert loaded.files[0].declared_api_id == "KA10081"


def test_manual_response_import_fixture_rejects_remote_or_parquet(tmp_path):
    with pytest.raises(ValueError):
        load_kiwoom_manual_response_import_fixture("https://example.com/import.json")
    with pytest.raises(ValueError):
        load_kiwoom_manual_response_import_fixture(tmp_path / "fixture.parquet")


def test_manual_response_import_guard_rejects_remote_or_blank_context():
    validate_kiwoom_manual_response_import_metadata_safety(
        {"source_path": "fixtures/manual_response.json", "operator_context": "manual import"},
        context="manual import",
    )
    with pytest.raises(ValueError):
        validate_kiwoom_manual_response_import_metadata_safety(
            {"source_path": "https://example.com/manual_response.json", "operator_context": "manual import"},
            context="manual import",
        )
    with pytest.raises(ValueError):
        validate_kiwoom_manual_response_import_metadata_safety(
            {"source_path": "fixtures/manual_response.json", "operator_context": ""},
            context="manual import",
        )


def test_manual_response_import_enums_surface_expected_values():
    assert KiwoomManualResponseImportReadiness.SNAPSHOT_COMPOSED.value == "SNAPSHOT_COMPOSED"
    assert KiwoomManualResponseApiClassification.ORDER_BLOCKED.value == "ORDER_BLOCKED"
