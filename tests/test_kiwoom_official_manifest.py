from pathlib import Path

from stock_risk_mcp.kiwoom_official_manifest import (
    KiwoomOfficialEndpointClass,
    load_kiwoom_official_manifest,
)


def test_curated_official_manifest_schema_and_scope() -> None:
    manifest = load_kiwoom_official_manifest()
    assert 12 <= len(manifest.endpoints) <= 20
    assert manifest.scope == "CURATED_REPRESENTATIVE_ENDPOINTS"
    assert all(item.source.startswith("https://openapi.kiwoom.com/") for item in manifest.endpoints)
    assert all(item.runtime_allowed_in_current_version is False for item in manifest.endpoints)
    assert {item.read_write_class for item in manifest.endpoints} >= {
        KiwoomOfficialEndpointClass.AUTH,
        KiwoomOfficialEndpointClass.READ_ONLY,
        KiwoomOfficialEndpointClass.ORDER,
        KiwoomOfficialEndpointClass.ACCOUNT_READ,
    }


def test_manifest_file_is_committed_config() -> None:
    root = Path(__file__).resolve().parents[1]
    assert (root / "configs" / "kiwoom_official_endpoint_manifest.json").exists()
