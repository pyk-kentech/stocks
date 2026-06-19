from __future__ import annotations

import re


_REMOTE_PATTERNS = (re.compile(r"https?://", re.IGNORECASE), re.compile(r"remote", re.IGNORECASE))
_API_PATTERNS = (re.compile(r"\bapi\b", re.IGNORECASE),)
_NETWORK_PATTERNS = (re.compile(r"tcp://", re.IGNORECASE), re.compile(r"network", re.IGNORECASE))
_PROVIDER_PATTERNS = (re.compile(r"provider", re.IGNORECASE),)
_ORDER_PATTERNS = (re.compile(r"order", re.IGNORECASE),)
_EXECUTION_PATTERNS = (re.compile(r"execution|execute", re.IGNORECASE),)
_BUY_SELL_PATTERNS = (re.compile(r"buy|sell|entry|exit", re.IGNORECASE),)
_LIVE_PROD_PATTERNS = (re.compile(r"live|prod", re.IGNORECASE),)
_BROKER_PATTERNS = (re.compile(r"broker", re.IGNORECASE),)
_ACCOUNT_PATTERNS = (re.compile(r"account", re.IGNORECASE),)
_KIWOOM_PATTERNS = (re.compile(r"kiwoom", re.IGNORECASE),)
_LS_PATTERNS = (re.compile(r"\bls\b", re.IGNORECASE),)
_GEMINI_PATTERNS = (re.compile(r"gemini", re.IGNORECASE),)
_LLM_PATTERNS = (re.compile(r"\bllm\b", re.IGNORECASE),)
_CLOUD_MODEL_PATTERNS = (re.compile(r"cloud[ _-]?model|runtime_backend|model runtime", re.IGNORECASE),)
_TRAINING_PATTERNS = (re.compile(r"training|fit", re.IGNORECASE),)
_CRAWLER_PATTERNS = (re.compile(r"crawler|crawl", re.IGNORECASE),)
_PARQUET_PATTERNS = (re.compile(r"parquet", re.IGNORECASE),)


def _iter_dict_keys(value):
    if isinstance(value, dict):
        for key in value.keys():
            yield str(key)
        for nested in value.values():
            yield from _iter_dict_keys(nested)
    elif isinstance(value, list):
        for item in value:
            yield from _iter_dict_keys(item)


def _iter_string_values(value):
    if isinstance(value, dict):
        for nested in value.values():
            yield from _iter_string_values(nested)
    elif isinstance(value, list):
        for item in value:
            yield from _iter_string_values(item)
    elif isinstance(value, str):
        yield value


def _reject_patterns(patterns, value, label: str):
    if any(pattern.search(value) for pattern in patterns):
        raise ValueError(label)


def validate_historical_dataset_validation_feature_outcome_boundary(data, *, context: str):
    blocked_keys = {
        "outcome_label": "outcome label",
        "forward_return_pct": "forward return",
        "max_favorable_excursion_pct": "max favorable",
        "max_adverse_excursion_pct": "max adverse",
        "forward_close_price": "post-anchor",
        "actual_forward_value": "post-anchor",
    }
    if isinstance(data, dict) and "scanner_replay_input" in data:
        scanner_payload = data["scanner_replay_input"]
        for key in _iter_dict_keys(scanner_payload):
            if key.strip().lower() in blocked_keys:
                raise ValueError(f"{context} rejected scanner input mutation marker")
        for value in _iter_string_values(scanner_payload):
            if value.strip().lower().startswith("outcome_"):
                raise ValueError(f"{context} rejected scanner input mutation marker")
    for key in _iter_dict_keys(data):
        normalized = key.strip().lower()
        if normalized in blocked_keys:
            raise ValueError(f"{context} rejected {blocked_keys[normalized]} in feature block")
    for value in _iter_string_values(data):
        lowered = value.strip().lower()
        if lowered.startswith("outcome_"):
            raise ValueError(f"{context} rejected outcome label in feature block")
    return data


def validate_historical_dataset_validation_split_integrity(data, *, context: str):
    if isinstance(data, dict) and data.get("allow_random_shuffle") is True:
        raise ValueError(f"{context} rejected random shuffle marker")
    seen_record_ids: dict[str, str] = {}
    record_refs = data.get("record_refs", []) if isinstance(data, dict) else []
    for record_ref in record_refs:
        if not isinstance(record_ref, dict):
            continue
        dataset_record_id = str(record_ref.get("dataset_record_id", "")).strip().upper()
        split_partition = str(record_ref.get("split_partition", "")).strip().upper()
        if dataset_record_id and dataset_record_id in seen_record_ids:
            if seen_record_ids[dataset_record_id] != split_partition:
                raise ValueError(f"{context} rejected split partition overlap")
            raise ValueError(f"{context} rejected duplicated split record refs")
        if dataset_record_id:
            seen_record_ids[dataset_record_id] = split_partition
    if isinstance(data, dict) and data.get("partition_overlap") is True:
        raise ValueError(f"{context} rejected split partition overlap")
    return data


def validate_historical_dataset_validation_metadata_safety(data, *, context: str):
    checks = (
        (_ORDER_PATTERNS, "order"),
        (_EXECUTION_PATTERNS, "execution"),
        (_BUY_SELL_PATTERNS, "buy_sell"),
        (_LIVE_PROD_PATTERNS, "live_prod"),
        (_BROKER_PATTERNS, "broker"),
        (_ACCOUNT_PATTERNS, "account"),
        (_KIWOOM_PATTERNS, "kiwoom"),
        (_LS_PATTERNS, "ls"),
        (_REMOTE_PATTERNS, "remote"),
        (_API_PATTERNS, "api"),
        (_NETWORK_PATTERNS, "network"),
        (_PROVIDER_PATTERNS, "provider"),
        (_GEMINI_PATTERNS, "gemini"),
        (_LLM_PATTERNS, "llm"),
        (_CLOUD_MODEL_PATTERNS, "cloud_model"),
        (_TRAINING_PATTERNS, "training"),
        (_CRAWLER_PATTERNS, "crawler"),
        (_PARQUET_PATTERNS, "parquet"),
    )
    for key in _iter_dict_keys(data):
        for patterns, label in checks:
            _reject_patterns(patterns, key, label)
    for value in _iter_string_values(data):
        for patterns, label in checks:
            _reject_patterns(patterns, value, label)
    return data
