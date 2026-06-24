from __future__ import annotations

import re


_FORBIDDEN_PATTERNS = (
    re.compile(r"authorization", re.IGNORECASE),
    re.compile(r"bearer\s+[a-z0-9._-]+", re.IGNORECASE),
    re.compile(r"token|secret|credential", re.IGNORECASE),
    re.compile(r"account", re.IGNORECASE),
    re.compile(r"broker|kiwoom", re.IGNORECASE),
    re.compile(r"order[_ -]?intent|real[_ -]?order|mock[_ -]?order", re.IGNORECASE),
    re.compile(r"websocket|network|requests|httpx", re.IGNORECASE),
    re.compile(r"live|prod", re.IGNORECASE),
    re.compile(r"autonomous", re.IGNORECASE),
)


def _walk(value):
    if isinstance(value, dict):
        for key, nested in value.items():
            yield str(key)
            yield from _walk(nested)
    elif isinstance(value, list):
        for nested in value:
            yield from _walk(nested)
    elif value is not None:
        yield str(value)


def validate_controlled_mock_readiness_metadata_safety(value, *, context: str):
    for item in _walk(value):
        for pattern in _FORBIDDEN_PATTERNS:
            if pattern.search(item):
                raise ValueError(f"{context} contains forbidden marker: {item}")
    return True
