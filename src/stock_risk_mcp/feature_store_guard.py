from __future__ import annotations

from pathlib import Path


_BLOCKED_MARKERS = (
    "authorization",
    "bearer ",
    "api_key",
    "secret",
    "token",
    "password",
    "account",
    "order",
    "broker",
    "buy",
    "sell",
)


def validate_feature_store_metadata_safety(metadata: dict[str, object], context: str) -> None:
    for key, value in metadata.items():
        lowered_key = str(key).lower()
        lowered_value = str(value).lower()
        if any(marker in lowered_key for marker in _BLOCKED_MARKERS):
            raise ValueError(f"{context} contains blocked metadata field: {key}")
        if any(marker in lowered_value for marker in _BLOCKED_MARKERS):
            raise ValueError(f"{context} contains blocked metadata value")


def validate_feature_store_root(path: str, *, repo_root: Path) -> tuple[bool, str]:
    raw = Path(path)
    candidate = raw if raw.is_absolute() else (repo_root / raw)
    normalized = candidate.resolve()
    safe_root = (repo_root / "local_data" / "feature_store").resolve()
    if safe_root == normalized or safe_root in normalized.parents:
        return True, "SAFE_LOCAL_ROOT_ONLY"
    if "/tmp/" in str(normalized) or "/var/folders/" in str(normalized):
        return True, "TEST_TEMP_ONLY"
    return False, "REJECTED_PATH"
