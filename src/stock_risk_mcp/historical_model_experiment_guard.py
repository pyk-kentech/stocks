from __future__ import annotations

import re


_REMOTE_PATTERNS = (re.compile(r"https?://", re.IGNORECASE), re.compile(r"remote", re.IGNORECASE))
_API_PATTERNS = (re.compile(r"\bapi\b|api[_ -]?", re.IGNORECASE),)
_NETWORK_PATTERNS = (re.compile(r"tcp://", re.IGNORECASE), re.compile(r"network", re.IGNORECASE))
_PROVIDER_PATTERNS = (re.compile(r"provider", re.IGNORECASE),)
_CLOUD_LLM_PATTERNS = (re.compile(r"cloud[_ -]?llm|openai|gemini|claude", re.IGNORECASE),)
_LOCAL_LLM_PATTERNS = (re.compile(r"local[_ -]?llm|ollama|vllm|llama", re.IGNORECASE),)
_CRAWLER_PATTERNS = (re.compile(r"crawler|crawl", re.IGNORECASE),)
_LIVE_PROD_PATTERNS = (re.compile(r"live|prod", re.IGNORECASE),)
_DEPLOYMENT_PATTERNS = (re.compile(r"deploy|deployment", re.IGNORECASE),)
_LIVE_INFERENCE_PATTERNS = (re.compile(r"live[_ -]?inference|online[_ -]?inference", re.IGNORECASE),)
_BROKER_PATTERNS = (re.compile(r"broker", re.IGNORECASE),)
_ACCOUNT_PATTERNS = (re.compile(r"account", re.IGNORECASE),)
_ORDER_PATTERNS = (re.compile(r"order", re.IGNORECASE),)
_CREDENTIAL_PATTERNS = (re.compile(r"credential|token|secret|password|key", re.IGNORECASE),)
_BUY_SELL_PATTERNS = (re.compile(r"buy|sell|entry|exit", re.IGNORECASE),)
_RUNTIME_SIGNAL_PATTERNS = (re.compile(r"runtime[_ -]?signal|trading[_ -]?signal", re.IGNORECASE),)
_ORDER_CANDIDATE_PATTERNS = (re.compile(r"order[_ -]?candidate|candidate", re.IGNORECASE),)
_PAPER_TRADING_PATTERNS = (re.compile(r"paper[_ -]?trading", re.IGNORECASE),)
_LIVE_RANKING_PATTERNS = (re.compile(r"live[_ -]?rank|rank.*live", re.IGNORECASE),)
_PRODUCTION_READINESS_PATTERNS = (re.compile(r"production[_ -]?readiness|prod[_ -]?ready", re.IGNORECASE),)
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


def validate_historical_model_experiment_metadata_safety(data, *, context: str):
    key_checks = (
        (_PRODUCTION_READINESS_PATTERNS, "deployment"),
        (_DEPLOYMENT_PATTERNS, "deployment"),
        (_LIVE_INFERENCE_PATTERNS, "live_inference"),
        (_LIVE_RANKING_PATTERNS, "live_ranking"),
        (_RUNTIME_SIGNAL_PATTERNS, "runtime_signal"),
        (_ORDER_CANDIDATE_PATTERNS, "order_candidate"),
        (_BUY_SELL_PATTERNS, "buy_sell"),
        (_BROKER_PATTERNS, "broker"),
        (_ACCOUNT_PATTERNS, "account"),
        (_ORDER_PATTERNS, "order"),
        (_CREDENTIAL_PATTERNS, "credential"),
        (_REMOTE_PATTERNS, "remote"),
        (_PROVIDER_PATTERNS, "provider"),
        (_API_PATTERNS, "api"),
        (_NETWORK_PATTERNS, "network"),
        (_CLOUD_LLM_PATTERNS, "cloud_llm"),
        (_LOCAL_LLM_PATTERNS, "local_llm"),
        (_CRAWLER_PATTERNS, "crawler"),
        (_LIVE_PROD_PATTERNS, "live_prod"),
        (_PARQUET_PATTERNS, "parquet"),
        (_PAPER_TRADING_PATTERNS, "paper_trading"),
    )
    value_checks = key_checks + ((_PROVIDER_PATTERNS, "provider"),)
    for key in _iter_dict_keys(data):
        for patterns, label in key_checks:
            _reject_patterns(patterns, key, label)
    for value in _iter_string_values(data):
        for patterns, label in value_checks:
            _reject_patterns(patterns, value, label)
    return data


def validate_historical_model_experiment_artifact_safety(data, *, context: str):
    checks = (
        (_DEPLOYMENT_PATTERNS, "deployment"),
        (_LIVE_INFERENCE_PATTERNS, "live_inference"),
        (_RUNTIME_SIGNAL_PATTERNS, "runtime_signal"),
        (_ORDER_CANDIDATE_PATTERNS, "order_candidate"),
        (_BROKER_PATTERNS, "broker"),
        (_ACCOUNT_PATTERNS, "account"),
        (_ORDER_PATTERNS, "order"),
        (_CREDENTIAL_PATTERNS, "credential"),
        (_REMOTE_PATTERNS, "remote"),
        (_API_PATTERNS, "api"),
        (_NETWORK_PATTERNS, "network"),
        (_PROVIDER_PATTERNS, "provider"),
        (_CLOUD_LLM_PATTERNS, "cloud_llm"),
        (_LOCAL_LLM_PATTERNS, "local_llm"),
        (_CRAWLER_PATTERNS, "crawler"),
        (_LIVE_PROD_PATTERNS, "live_prod"),
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
        "no_live_inference",
        "no_deployment",
    }
    for key in _iter_dict_keys(data):
        if key in allowed_safety_keys:
            continue
        for patterns, label in checks:
            _reject_patterns(patterns, key, label)
    for value in _iter_string_values(data):
        for patterns, label in checks:
            _reject_patterns(patterns, value, label)
    return data


def validate_historical_model_experiment_promotion_block(data, *, context: str):
    if not isinstance(data, dict):
        return data
    blocked_flags = (
        "production_use_allowed",
        "live_inference_allowed",
        "runtime_trading_signal_allowed",
        "order_candidate_allowed",
        "paper_trading_allowed",
        "broker_path_allowed",
        "live_prod_allowed",
        "deployment_allowed",
    )
    if any(data.get(flag) is True for flag in blocked_flags):
        raise ValueError(f"{context} must remain blocked-by-default")
    return data


def validate_historical_model_experiment_comparison_safety(data, *, context: str):
    validate_historical_model_experiment_metadata_safety(data, context=context)
    if isinstance(data, dict):
        for key in _iter_dict_keys(data):
            _reject_patterns(_LIVE_RANKING_PATTERNS, key, "live_ranking")
        for value in _iter_string_values(data):
            _reject_patterns(_LIVE_RANKING_PATTERNS, value, "live_ranking")
    return data
