from __future__ import annotations

import re
from typing import Any


_REMOTE_PATH_PATTERN = re.compile(r"(^[a-z][a-z0-9+.-]*://)|(^//)", re.IGNORECASE)
_NETWORK_PATTERN = re.compile(r"(^|[^a-z0-9])(network|socket|websocket|http|https|tcp|udp)($|[^a-z0-9])", re.IGNORECASE)
_BLOCKED_KEYWORDS = {
    "remote": re.compile(r"(^|[^a-z0-9])remote($|[^a-z0-9])", re.IGNORECASE),
    "provider": re.compile(r"(^|[^a-z0-9])provider($|[^a-z0-9])", re.IGNORECASE),
    "api": re.compile(r"(^|[^a-z0-9])api($|[^a-z0-9])", re.IGNORECASE),
    "order": re.compile(r"(^|[^a-z0-9])order($|[^a-z0-9])", re.IGNORECASE),
    "execution": re.compile(r"(^|[^a-z0-9])(execute|execution|executable)($|[^a-z0-9])", re.IGNORECASE),
    "buy_sell": re.compile(r"(^|[^a-z0-9])(buy|sell|entry|exit)($|[^a-z0-9])", re.IGNORECASE),
    "live_prod": re.compile(r"(^|[^a-z0-9])(live|prod)($|[^a-z0-9])", re.IGNORECASE),
    "broker": re.compile(r"(^|[^a-z0-9])broker($|[^a-z0-9])", re.IGNORECASE),
    "account": re.compile(r"(^|[^a-z0-9])account($|[^a-z0-9])", re.IGNORECASE),
    "kiwoom": re.compile(r"(^|[^a-z0-9])kiwoom($|[^a-z0-9])", re.IGNORECASE),
    "ls": re.compile(r"(^|[^a-z0-9])ls($|[^a-z0-9])", re.IGNORECASE),
    "gemini": re.compile(r"(^|[^a-z0-9])gemini($|[^a-z0-9])", re.IGNORECASE),
    "llm": re.compile(r"(^|[^a-z0-9])llm($|[^a-z0-9])", re.IGNORECASE),
    "cloud_model": re.compile(r"(^|[^a-z0-9])(cloud model|model runtime|local model|runtime)($|[^a-z0-9])", re.IGNORECASE),
    "training": re.compile(r"(^|[^a-z0-9])(ml|training)($|[^a-z0-9])", re.IGNORECASE),
    "crawler": re.compile(r"(^|[^a-z0-9])crawler($|[^a-z0-9])", re.IGNORECASE),
    "parquet": re.compile(r"(^|[^a-z0-9])parquet($|[^a-z0-9])", re.IGNORECASE),
    "runtime_signal": re.compile(r"(^|[^a-z0-9])(runtime signal|runtime_signal)($|[^a-z0-9])", re.IGNORECASE),
}
_REMOTE_SOURCE_TYPES = {"remote_url", "provider_api", "local_parquet"}


def validate_historical_outcome_source_type(source_type: str, *, context: str) -> None:
    normalized = _normalize_text(source_type)
    if normalized in _REMOTE_SOURCE_TYPES:
        raise ValueError(f"{context} rejected non-local source type: {normalized}")


def validate_historical_outcome_metadata_safety(data: Any, *, context: str) -> None:
    for path, key, item in _iter_dict_keys(data):
        lowered = key.strip().lower()
        if not lowered:
            continue
        if _REMOTE_PATH_PATTERN.search(lowered):
            raise ValueError(f"{context} rejected remote field name at {path}: {key}")
        if _NETWORK_PATTERN.search(lowered):
            raise ValueError(f"{context} rejected network field name at {path}: {key}")
        for label, pattern in _BLOCKED_KEYWORDS.items():
            if pattern.search(lowered):
                raise ValueError(f"{context} rejected {label} field name at {path}: {key}")
    for path, value in _iter_string_values(data):
        lowered = value.strip().lower()
        if not lowered:
            continue
        if _REMOTE_PATH_PATTERN.search(lowered):
            raise ValueError(f"{context} rejected remote path-like metadata at {path}: {value}")
        if _NETWORK_PATTERN.search(lowered):
            raise ValueError(f"{context} rejected network metadata at {path}: {value}")
        for label, pattern in _BLOCKED_KEYWORDS.items():
            if pattern.search(lowered):
                raise ValueError(f"{context} rejected {label} metadata at {path}: {value}")


def validate_historical_outcome_pre_outcome_boundary(data: Any, *, context: str) -> None:
    for path, value in _iter_string_values(data):
        lowered = value.strip().lower()
        if lowered.startswith("outcome_"):
            raise ValueError(f"{context} rejected outcome label attached to pre-outcome scanner input at {path}: {value}")
    for path, key, _item in _iter_dict_keys(data):
        lowered = key.strip().lower()
        if lowered in {"label_type", "outcome_label", "outcome_labels", "runtime_signal"}:
            raise ValueError(f"{context} rejected outcome label attached to pre-outcome scanner input at {path}: {key}")


def _normalize_text(value: Any) -> str:
    return str(value).strip().lower()


def _iter_string_values(value: Any, path: str = "fixture"):
    if isinstance(value, str):
        yield path, value
        return
    if isinstance(value, list):
        for index, item in enumerate(value):
            yield from _iter_string_values(item, f"{path}[{index}]")
        return
    if isinstance(value, dict):
        for key, item in value.items():
            yield from _iter_string_values(item, f"{path}.{key}")


def _iter_dict_keys(value: Any, path: str = "fixture"):
    if isinstance(value, list):
        for index, item in enumerate(value):
            yield from _iter_dict_keys(item, f"{path}[{index}]")
        return
    if isinstance(value, dict):
        for key, item in value.items():
            key_text = str(key)
            yield f"{path}.{key_text}", key_text, item
            yield from _iter_dict_keys(item, f"{path}.{key_text}")
