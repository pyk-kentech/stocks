from __future__ import annotations

from collections import Counter

from pydantic import Field

from stock_risk_mcp.kiwoom_mock_execution_transport import KIWOOM_MOCK_EXECUTION_ENDPOINTS
from stock_risk_mcp.kiwoom_official_manifest import (
    KiwoomOfficialEndpointClass,
    KiwoomOfficialEndpointManifest,
)
from stock_risk_mcp.kiwoom_readonly_allowlist import KiwoomReadOnlyAllowlist
from stock_risk_mcp.models import StrictModel


DANGEROUS_KEYWORDS = (
    "order", "buy", "sell", "cancel", "account", "balance", "position",
    "holding", "cash", "fill", "execution", "loan", "margin", "credit",
)


class KiwoomOfficialManifestValidationResult(StrictModel):
    valid: bool
    endpoint_count: int
    class_counts: dict[str, int] = Field(default_factory=dict)
    disabled_dangerous_endpoint_count: int
    duplicate_count: int
    errors: list[str] = Field(default_factory=list)


def validate_kiwoom_official_manifest(
    manifest: KiwoomOfficialEndpointManifest,
) -> KiwoomOfficialManifestValidationResult:
    errors: list[str] = []
    pairs = [(item.api_id, item.path) for item in manifest.endpoints]
    duplicate_count = len(pairs) - len(set(pairs))
    if duplicate_count:
        errors.append("duplicate api_id + path entries")
    runtime_paths = {
        *(item.path for item in KiwoomReadOnlyAllowlist().list_endpoints()),
        *KIWOOM_MOCK_EXECUTION_ENDPOINTS.values(),
    }
    forbidden_classes = {
        KiwoomOfficialEndpointClass.AUTH,
        KiwoomOfficialEndpointClass.ORDER,
        KiwoomOfficialEndpointClass.ACCOUNT_READ,
        KiwoomOfficialEndpointClass.UNKNOWN_REVIEW_REQUIRED,
    }
    disabled_dangerous = 0
    for item in manifest.endpoints:
        dangerous_path = any(keyword in item.path.lower() for keyword in DANGEROUS_KEYWORDS)
        dangerous_class = item.read_write_class in forbidden_classes
        if (dangerous_path or dangerous_class) and not item.runtime_allowed_in_current_version:
            disabled_dangerous += 1
        if item.runtime_allowed_in_current_version:
            errors.append(f"official endpoint must be runtime disabled: {item.api_id}")
        if dangerous_path and item.runtime_allowed_in_current_version:
            errors.append(f"dangerous path runtime enabled: {item.path}")
        if item.path in runtime_paths:
            errors.append(f"official endpoint overlaps runtime allowlist: {item.path}")
        if not item.source.startswith("https://openapi.kiwoom.com/"):
            errors.append(f"non-official source: {item.api_id}")
    return KiwoomOfficialManifestValidationResult(
        valid=not errors,
        endpoint_count=len(manifest.endpoints),
        class_counts=dict(Counter(item.read_write_class.value for item in manifest.endpoints)),
        disabled_dangerous_endpoint_count=disabled_dangerous,
        duplicate_count=duplicate_count,
        errors=errors,
    )
