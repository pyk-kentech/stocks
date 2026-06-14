from stock_risk_mcp.kiwoom_official_manifest import (
    KiwoomOfficialEndpointClass,
    load_kiwoom_official_manifest,
)
from stock_risk_mcp.kiwoom_official_manifest_validator import validate_kiwoom_official_manifest


def test_official_manifest_validation_passes_and_counts_classes() -> None:
    result = validate_kiwoom_official_manifest(load_kiwoom_official_manifest())
    assert result.valid
    assert result.duplicate_count == 0
    assert result.class_counts[KiwoomOfficialEndpointClass.ORDER.value] >= 2
    assert result.disabled_dangerous_endpoint_count >= 1


def test_duplicate_and_runtime_enabled_dangerous_endpoint_are_rejected() -> None:
    manifest = load_kiwoom_official_manifest()
    duplicate = manifest.model_copy(update={"endpoints": [*manifest.endpoints, manifest.endpoints[0]]})
    unsafe = manifest.model_copy(update={"endpoints": [
        manifest.endpoints[0].model_copy(update={
            "path": "/api/order", "read_write_class": KiwoomOfficialEndpointClass.ORDER,
            "runtime_allowed_in_current_version": True,
        })
    ]})

    assert validate_kiwoom_official_manifest(duplicate).duplicate_count == 1
    assert not validate_kiwoom_official_manifest(unsafe).valid
