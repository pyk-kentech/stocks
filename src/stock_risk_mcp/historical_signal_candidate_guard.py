from __future__ import annotations

import re


_BUY_SELL_PATTERNS = (re.compile(r"buy|sell|entry|exit|long|short", re.IGNORECASE),)
_RUNTIME_SIGNAL_PATTERNS = (re.compile(r"runtime[_ -]?signal|trading[_ -]?signal", re.IGNORECASE),)
_ORDER_CANDIDATE_PATTERNS = (re.compile(r"order[_ -]?candidate", re.IGNORECASE),)
_ORDER_PATTERNS = (re.compile(r"order|execution", re.IGNORECASE),)
_POSITION_PATTERNS = (
    re.compile(r"position|position[_ -]?size|quantity|target[_ -]?price|stop[_ -]?loss|take[_ -]?profit", re.IGNORECASE),
)
_PAPER_TRADING_PATTERNS = (re.compile(r"paper[_ -]?trading|paper[_ -]?order", re.IGNORECASE),)
_BROKER_PATTERNS = (re.compile(r"broker|account", re.IGNORECASE),)
_KIWOOM_LS_PATTERNS = (re.compile(r"kiwoom|ls", re.IGNORECASE),)
_LIVE_INFERENCE_PATTERNS = (re.compile(r"live[_ -]?inference|online[_ -]?inference", re.IGNORECASE),)
_DEPLOYMENT_PATTERNS = (re.compile(r"deploy|deployment|production[_ -]?model", re.IGNORECASE),)
_PROVIDER_PATTERNS = (re.compile(r"provider", re.IGNORECASE),)
_API_PATTERNS = (re.compile(r"\bapi\b|api[_ -]?", re.IGNORECASE),)
_NETWORK_PATTERNS = (re.compile(r"https?://|tcp://|network|remote", re.IGNORECASE),)
_CLOUD_LLM_PATTERNS = (re.compile(r"cloud[_ -]?llm|gemini|openai|claude", re.IGNORECASE),)
_LOCAL_LLM_PATTERNS = (re.compile(r"local[_ -]?llm|ollama|vllm|llama", re.IGNORECASE),)
_NEWS_PATTERNS = (re.compile(r"investing|finviz|news[_ -]?ingestion|crawler|crawl", re.IGNORECASE),)
_LIVE_PROD_PATTERNS = (re.compile(r"\blive\b|\bprod\b", re.IGNORECASE),)
_PARQUET_PATTERNS = (re.compile(r"parquet", re.IGNORECASE),)
_CREDENTIAL_PATTERNS = (re.compile(r"credential|token|secret|password|api[_ -]?key|key", re.IGNORECASE),)


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


def validate_historical_signal_candidate_metadata_safety(data, *, context: str):
    del context
    key_checks = (
        (_RUNTIME_SIGNAL_PATTERNS, "runtime_signal"),
        (_ORDER_CANDIDATE_PATTERNS, "order_candidate"),
        (_BUY_SELL_PATTERNS, "buy_sell"),
        (_POSITION_PATTERNS, "position"),
        (_PAPER_TRADING_PATTERNS, "paper_trading"),
        (_BROKER_PATTERNS, "broker"),
        (_KIWOOM_LS_PATTERNS, "broker"),
        (_LIVE_INFERENCE_PATTERNS, "live_inference"),
        (_DEPLOYMENT_PATTERNS, "deployment"),
        (_CREDENTIAL_PATTERNS, "credential"),
        (_PROVIDER_PATTERNS, "provider"),
        (_API_PATTERNS, "api"),
        (_NETWORK_PATTERNS, "network"),
        (_CLOUD_LLM_PATTERNS, "cloud_llm"),
        (_LOCAL_LLM_PATTERNS, "local_llm"),
        (_NEWS_PATTERNS, "news"),
        (_LIVE_PROD_PATTERNS, "live_prod"),
        (_PARQUET_PATTERNS, "parquet"),
        (_ORDER_PATTERNS, "order"),
    )
    for key in _iter_dict_keys(data):
        for patterns, label in key_checks:
            _reject_patterns(patterns, key, label)
    for value in _iter_string_values(data):
        for patterns, label in key_checks:
            _reject_patterns(patterns, value, label)
    return data
