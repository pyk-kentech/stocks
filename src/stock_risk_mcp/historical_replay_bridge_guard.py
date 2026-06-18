from __future__ import annotations

import re
from typing import Any

from stock_risk_mcp.historical_data_models import HistoricalDataSourceType
from stock_risk_mcp.historical_replay_bridge_fixture import HistoricalReplayBridgeFixture


_REMOTE_PATH_PATTERN = re.compile(r"(^[a-z][a-z0-9+.-]*://)|(^//)", re.IGNORECASE)
_REMOTE_NETWORK_PATTERN = re.compile(r"(^|[^a-z0-9])(network|socket|websocket|http|https|tcp|udp)($|[^a-z0-9])", re.IGNORECASE)
_REMOTE_SOURCE_TYPES = {
    HistoricalDataSourceType.REMOTE_URL.value,
    HistoricalDataSourceType.PROVIDER_API.value,
    HistoricalDataSourceType.LOCAL_PARQUET.value,
}
_BLOCKED_VALUE_PATTERNS = {
    "remote": re.compile(r"(^|[^a-z0-9])remote($|[^a-z0-9])", re.IGNORECASE),
    "parquet": re.compile(r"(^|[^a-z0-9])parquet($|[^a-z0-9])", re.IGNORECASE),
    "provider": re.compile(r"(^|[^a-z0-9])provider($|[^a-z0-9])", re.IGNORECASE),
    "api": re.compile(r"(^|[^a-z0-9])api($|[^a-z0-9])", re.IGNORECASE),
    "broker": re.compile(r"(^|[^a-z0-9])broker($|[^a-z0-9])", re.IGNORECASE),
    "order": re.compile(r"(^|[^a-z0-9])order($|[^a-z0-9])", re.IGNORECASE),
    "execution": re.compile(r"(^|[^a-z0-9])(execute|execution|executable)($|[^a-z0-9])", re.IGNORECASE),
    "account": re.compile(r"(^|[^a-z0-9])account($|[^a-z0-9])", re.IGNORECASE),
    "network": re.compile(r"(^|[^a-z0-9])network($|[^a-z0-9])", re.IGNORECASE),
    "live": re.compile(r"(^|[^a-z0-9])live($|[^a-z0-9])", re.IGNORECASE),
    "prod": re.compile(r"(^|[^a-z0-9])prod($|[^a-z0-9])", re.IGNORECASE),
    "llm": re.compile(r"(^|[^a-z0-9])llm($|[^a-z0-9])", re.IGNORECASE),
    "cloud": re.compile(r"(^|[^a-z0-9])cloud($|[^a-z0-9])", re.IGNORECASE),
    "model": re.compile(r"(^|[^a-z0-9])(cloud model|local model|model runtime|runtime)($|[^a-z0-9])", re.IGNORECASE),
    "ml": re.compile(r"(^|[^a-z0-9])ml($|[^a-z0-9])", re.IGNORECASE),
    "training": re.compile(r"(^|[^a-z0-9])training($|[^a-z0-9])", re.IGNORECASE),
    "crawler": re.compile(r"(^|[^a-z0-9])crawler($|[^a-z0-9])", re.IGNORECASE),
    "gemini": re.compile(r"(^|[^a-z0-9])gemini($|[^a-z0-9])", re.IGNORECASE),
    "kiwoom": re.compile(r"(^|[^a-z0-9])kiwoom($|[^a-z0-9])", re.IGNORECASE),
    "ls": re.compile(r"(^|[^a-z0-9])ls($|[^a-z0-9])", re.IGNORECASE),
}


def validate_historical_replay_bridge_fixture_safety(fixture: HistoricalReplayBridgeFixture) -> None:
    market_snapshot = fixture.historical_market_data_snapshot
    if market_snapshot is None:
        raise ValueError("missing market snapshot")

    source_descriptor = market_snapshot.source_descriptor
    ingestion_config = market_snapshot.ingestion_config
    if source_descriptor is None or ingestion_config is None:
        raise ValueError("missing market snapshot")
    source_type_values = {
        _source_type_value(ingestion_config.source_type),
        _source_type_value(source_descriptor.source_type),
    }
    for source_type in source_type_values:
        validate_historical_replay_source_type(source_type, context="historical replay bridge fixture")

    validate_historical_replay_metadata_safety(
        fixture.model_dump(mode="json"),
        context="historical replay bridge fixture",
    )


def validate_historical_replay_source_type(source_type: str, *, context: str) -> None:
    normalized_source_type = _source_type_value(source_type)
    if normalized_source_type in _REMOTE_SOURCE_TYPES:
        raise ValueError(f"{context} rejected non-local source type: {normalized_source_type}")


def validate_historical_replay_metadata_safety(data: Any, *, context: str) -> None:
    for path, key, item in _iter_dict_keys(data):
        lowered = key.strip().lower()
        if not lowered:
            continue
        if _is_allowed_safe_boundary_key(lowered, item):
            continue
        if _REMOTE_PATH_PATTERN.search(lowered):
            raise ValueError(f"{context} rejected remote field name at {path}: {key}")
        if _REMOTE_NETWORK_PATTERN.search(lowered):
            raise ValueError(f"{context} rejected network field name at {path}: {key}")
        for label, pattern in _BLOCKED_VALUE_PATTERNS.items():
            if pattern.search(lowered):
                raise ValueError(f"{context} rejected {label} field name at {path}: {key}")
    for path, value in _iter_string_values(data):
        lowered = value.strip().lower()
        if not lowered:
            continue
        if _REMOTE_PATH_PATTERN.search(lowered):
            raise ValueError(f"{context} rejected remote path-like metadata at {path}: {value}")
        if _REMOTE_NETWORK_PATTERN.search(lowered):
            raise ValueError(f"{context} rejected network metadata at {path}: {value}")
        for label, pattern in _BLOCKED_VALUE_PATTERNS.items():
            if pattern.search(lowered):
                raise ValueError(f"{context} rejected {label} metadata at {path}: {value}")


def _source_type_value(value: Any) -> str:
    if hasattr(value, "value"):
        return str(value.value).strip().lower()
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


def _is_allowed_safe_boundary_key(key: str, value: Any) -> bool:
    if key.startswith("no_") and value is True:
        return True
    if key.endswith("_allowed") and value is False:
        return True
    if key in {
        "non_executable",
        "local_file_only",
        "out_of_order_count",
        "provider_provenance",
        "provider_provenance_id",
        "provider_provenance_ids",
        "provenance_id",
        "provider_capability_reference",
    }:
        return True
    return False
