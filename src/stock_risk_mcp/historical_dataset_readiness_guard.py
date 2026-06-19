from __future__ import annotations

import re


_LEARNED_MODEL_PATTERNS = (re.compile(r"learned[_ -]?model|xgboost|lightgbm|random[_ -]?forest", re.IGNORECASE),)
_MODEL_WEIGHT_PATTERNS = (re.compile(r"weight|weights|trained[_ -]?artifact", re.IGNORECASE),)
_TRAINING_PATTERNS = (re.compile(r"training|fit", re.IGNORECASE),)
_TENSOR_PATTERNS = (re.compile(r"tensor|embedding|\.npy\b|tensor[_ -]?export", re.IGNORECASE),)
_TRADING_SIGNAL_PATTERNS = (re.compile(r"trading[_ -]?signal|runtime[_ -]?signal", re.IGNORECASE),)
_ORDER_PATTERNS = (re.compile(r"order", re.IGNORECASE),)
_EXECUTION_PATTERNS = (re.compile(r"execution|execute", re.IGNORECASE),)
_BUY_SELL_PATTERNS = (re.compile(r"buy|sell|entry|exit", re.IGNORECASE),)
_LIVE_PROD_PATTERNS = (re.compile(r"live|prod", re.IGNORECASE),)
_BROKER_PATTERNS = (re.compile(r"broker", re.IGNORECASE),)
_ACCOUNT_PATTERNS = (re.compile(r"account", re.IGNORECASE),)
_KIWOOM_PATTERNS = (re.compile(r"kiwoom", re.IGNORECASE),)
_LS_PATTERNS = (re.compile(r"\bls\b", re.IGNORECASE),)
_REMOTE_PATTERNS = (re.compile(r"https?://", re.IGNORECASE), re.compile(r"remote", re.IGNORECASE))
_API_PATTERNS = (re.compile(r"\bapi\b", re.IGNORECASE),)
_NETWORK_PATTERNS = (re.compile(r"tcp://", re.IGNORECASE), re.compile(r"network", re.IGNORECASE))
_PROVIDER_PATTERNS = (re.compile(r"provider", re.IGNORECASE),)
_GEMINI_PATTERNS = (re.compile(r"gemini", re.IGNORECASE),)
_LLM_PATTERNS = (re.compile(r"\bllm\b", re.IGNORECASE),)
_CLOUD_MODEL_PATTERNS = (re.compile(r"cloud[ _-]?model|model[_ -]?runtime|runtime", re.IGNORECASE),)
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


def validate_historical_dataset_readiness_metadata_safety(data, *, context: str):
    checks = (
        (_LEARNED_MODEL_PATTERNS, "learned"),
        (_MODEL_WEIGHT_PATTERNS, "weight"),
        (_TRAINING_PATTERNS, "training"),
        (_TENSOR_PATTERNS, "tensor"),
        (_TRADING_SIGNAL_PATTERNS, "trading signal"),
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


def validate_historical_dataset_readiness_split_integrity(data, *, context: str):
    if isinstance(data, dict) and data.get("random_shuffle_used") is True:
        raise ValueError(f"{context} rejected random shuffle marker")
    if isinstance(data, dict) and data.get("partition_overlap_detected") is True:
        raise ValueError(f"{context} rejected split overlap marker")
    if isinstance(data, dict) and data.get("duplicated_record_id_detected") is True:
        raise ValueError(f"{context} rejected duplicated split record marker")
    return data


def validate_historical_dataset_readiness_baseline_claims(data, *, context: str):
    if isinstance(data, dict):
        if data.get("deterministic_only") is False:
            raise ValueError(f"{context} rejected non-deterministic baseline claim")
        if data.get("non_learning_only") is False:
            raise ValueError(f"{context} rejected non-learning baseline claim")
        if data.get("trained_model_artifact_present") is True:
            raise ValueError(f"{context} rejected trained artifact claim")
        if data.get("model_weights_present") is True:
            raise ValueError(f"{context} rejected model weight claim")
    for key in _iter_dict_keys(data):
        _reject_patterns(_LEARNED_MODEL_PATTERNS, key, "learning")
        _reject_patterns(_TRAINING_PATTERNS, key, "training")
    for value in _iter_string_values(data):
        _reject_patterns(_LEARNED_MODEL_PATTERNS, value, "learning")
        _reject_patterns(_TRAINING_PATTERNS, value, "training")
    return data
