from __future__ import annotations

import re


_REMOTE_PATTERNS = (re.compile(r"https?://", re.IGNORECASE), re.compile(r"remote", re.IGNORECASE))
_API_PATTERNS = (re.compile(r"\bapi\b", re.IGNORECASE),)
_NETWORK_PATTERNS = (re.compile(r"tcp://", re.IGNORECASE), re.compile(r"network", re.IGNORECASE))
_PROVIDER_PATTERNS = (re.compile(r"provider", re.IGNORECASE),)
_CLOUD_LLM_PATTERNS = (re.compile(r"cloud[_ -]?llm|openai|gemini|claude", re.IGNORECASE),)
_LOCAL_LLM_PATTERNS = (re.compile(r"local[_ -]?llm|ollama|vllm|llama", re.IGNORECASE),)
_CRAWLER_PATTERNS = (re.compile(r"crawler|crawl", re.IGNORECASE),)
_LIVE_PROD_PATTERNS = (re.compile(r"live|prod", re.IGNORECASE),)
_BROKER_PATTERNS = (re.compile(r"broker", re.IGNORECASE),)
_ACCOUNT_PATTERNS = (re.compile(r"account", re.IGNORECASE),)
_ORDER_PATTERNS = (re.compile(r"order", re.IGNORECASE),)
_CREDENTIAL_PATTERNS = (re.compile(r"credential|token|secret|password|key", re.IGNORECASE),)
_BUY_SELL_PATTERNS = (re.compile(r"buy|sell|entry|exit", re.IGNORECASE),)
_RUNTIME_SIGNAL_PATTERNS = (re.compile(r"runtime[_ -]?signal|trading[_ -]?signal", re.IGNORECASE),)
_ORDER_CANDIDATE_PATTERNS = (re.compile(r"order[_ -]?candidate|candidate", re.IGNORECASE),)
_PARQUET_PATTERNS = (re.compile(r"parquet", re.IGNORECASE),)
_RUNTIME_DEPLOYMENT_PATTERNS = (re.compile(r"runtime[_ -]?deployment|live[_ -]?use|trading[_ -]?use", re.IGNORECASE),)


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


def validate_historical_model_training_metadata_safety(data, *, context: str):
    key_checks = (
        (_REMOTE_PATTERNS, "remote"),
        (_API_PATTERNS, "api"),
        (_NETWORK_PATTERNS, "network"),
        (_CLOUD_LLM_PATTERNS, "cloud_llm"),
        (_LOCAL_LLM_PATTERNS, "local_llm"),
        (_CRAWLER_PATTERNS, "crawler"),
        (_LIVE_PROD_PATTERNS, "live_prod"),
        (_BROKER_PATTERNS, "broker"),
        (_ACCOUNT_PATTERNS, "account"),
        (_ORDER_CANDIDATE_PATTERNS, "order_candidate"),
        (_ORDER_PATTERNS, "order"),
        (_CREDENTIAL_PATTERNS, "credential"),
        (_BUY_SELL_PATTERNS, "buy_sell"),
        (_RUNTIME_SIGNAL_PATTERNS, "runtime_signal"),
        (_PARQUET_PATTERNS, "parquet"),
    )
    value_checks = key_checks + ((_PROVIDER_PATTERNS, "provider"),)
    for key in _iter_dict_keys(data):
        for patterns, label in key_checks:
            _reject_patterns(patterns, key, label)
    for value in _iter_string_values(data):
        for patterns, label in value_checks:
            _reject_patterns(patterns, value, label)
    return data


def validate_historical_model_training_split_safety(data, *, context: str):
    if isinstance(data, dict) and data.get("random_shuffle_used") is True:
        raise ValueError(f"{context} rejected random shuffle marker")
    split_policy = str(data.get("split_policy", "")).upper() if isinstance(data, dict) else ""
    if isinstance(data, dict) and (split_policy and split_policy != "CHRONOLOGICAL" or data.get("chronological") is False):
        raise ValueError(f"{context} requires chronological split metadata")
    return data


def validate_historical_model_training_feature_boundary(data, *, context: str):
    blocked = {
        "OUTCOME_LABEL": "outcome label",
        "FORWARD_RETURN_PCT": "forward return",
        "MAX_FAVORABLE_EXCURSION_PCT": "post-anchor",
        "MAX_ADVERSE_EXCURSION_PCT": "post-anchor",
        "ACTUAL_FORWARD_VALUE": "post-anchor",
        "FORWARD_CLOSE_PRICE": "post-anchor",
    }
    fields = []
    if isinstance(data, dict):
        fields = [str(item).upper() for item in data.get("feature_fields", [])]
    for field in fields:
        for blocked_field, label in blocked.items():
            if field == blocked_field:
                raise ValueError(label)
    return data


def validate_historical_model_training_label_schema_safety(data, *, context: str):
    if not isinstance(data, dict):
        return data
    label_source = str(data.get("label_source", "")).upper()
    label_field = str(data.get("label_field", "")).upper()
    if label_source != "OUTCOME_BLOCK_ONLY" or label_field != "OUTCOME_LABEL":
        raise ValueError(f"{context} requires outcome-side labels only")
    return data


def validate_historical_model_training_model_type_safety(data, *, context: str):
    if not isinstance(data, dict):
        return data
    requested = str(data.get("requested_model_type", "")).upper()
    allowed = {
        "DUMMY_MAJORITY",
        "DUMMY_PRIOR",
        "LOGISTIC_REGRESSION_OPTIONAL_SKLEARN",
        "DECISION_TREE_OPTIONAL_SKLEARN",
        "RANDOM_FOREST_OPTIONAL_SKLEARN",
    }
    if requested not in allowed:
        raise ValueError(f"{context} rejected unsupported model type")
    return data


def validate_historical_model_training_artifact_safety(data, *, context: str):
    checks = (
        (_BROKER_PATTERNS, "broker"),
        (_ACCOUNT_PATTERNS, "account"),
        (_PROVIDER_PATTERNS, "provider"),
        (_ORDER_PATTERNS, "order"),
        (_LIVE_PROD_PATTERNS, "live"),
        (_RUNTIME_DEPLOYMENT_PATTERNS, "runtime deployment"),
        (_CREDENTIAL_PATTERNS, "credential"),
        (_PARQUET_PATTERNS, "parquet"),
    )
    allowed_safety_keys = {
        "read_only",
        "report_only",
        "non_executable",
        "local_file_only",
        "offline_only",
        "no_network",
        "no_provider_api",
        "no_order",
        "no_broker_path",
        "no_live_prod",
        "no_cloud_llm",
        "no_local_llm_runtime",
        "no_runtime_trading_signal",
        "no_order_candidate",
    }
    for key in _iter_dict_keys(data):
        if key in allowed_safety_keys:
            continue
        for patterns, label in checks:
            _reject_patterns(patterns, key, label)
    for value in _iter_string_values(data):
        for patterns, label in checks:
            _reject_patterns(patterns, value, label)
    if isinstance(data, dict) and data.get("runtime_deployment") is True:
        raise ValueError("runtime deployment")
    return data
