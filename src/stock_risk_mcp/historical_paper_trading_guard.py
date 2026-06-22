from __future__ import annotations

import re


_REAL_ACTION_PATTERNS = (re.compile(r"\bbuy\b|\bsell\b|\bhold\b|\bentry\b|\bexit\b|\blong\b|\bshort\b", re.IGNORECASE),)
_ORDER_PATTERNS = (re.compile(r"real[_ -]?order|order[_ -]?intent|executable[_ -]?order|execution", re.IGNORECASE),)
_BROKER_PATTERNS = (re.compile(r"broker", re.IGNORECASE),)
_ACCOUNT_PATTERNS = (re.compile(r"account", re.IGNORECASE),)
_KIWOOM_PATTERNS = (re.compile(r"kiwoom", re.IGNORECASE),)
_LS_PATTERNS = (re.compile(r"\bls\b|ls[_ -]?", re.IGNORECASE),)
_ORDER_API_PATTERNS = (re.compile(r"order[_ -]?api", re.IGNORECASE),)
_ACCOUNT_API_PATTERNS = (re.compile(r"account[_ -]?api", re.IGNORECASE),)
_BROKER_API_PATTERNS = (re.compile(r"broker[_ -]?api", re.IGNORECASE),)
_PROVIDER_PATTERNS = (re.compile(r"provider", re.IGNORECASE),)
_API_PATTERNS = (re.compile(r"\bapi\b|api[_ -]?", re.IGNORECASE),)
_NETWORK_PATTERNS = (re.compile(r"https?://|tcp://|network|remote", re.IGNORECASE),)
_LIVE_TRADING_PATTERNS = (re.compile(r"live[_ -]?trading", re.IGNORECASE),)
_LIVE_PROD_PATTERNS = (re.compile(r"\blive\b|\bprod\b", re.IGNORECASE),)
_DEPLOYMENT_PATTERNS = (re.compile(r"deploy|deployment", re.IGNORECASE),)
_CLOUD_LLM_PATTERNS = (re.compile(r"cloud[_ -]?llm|gemini|openai|claude", re.IGNORECASE),)
_LOCAL_LLM_PATTERNS = (re.compile(r"local[_ -]?llm|ollama|vllm|llama", re.IGNORECASE),)
_NEWS_PATTERNS = (re.compile(r"investing|finviz|news[_ -]?ingestion|crawler|crawl", re.IGNORECASE),)
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


def validate_historical_paper_trading_metadata_safety(data, *, context: str):
    del context
    key_checks = (
        (_ORDER_PATTERNS, "order"),
        (_BROKER_API_PATTERNS, "broker"),
        (_BROKER_PATTERNS, "broker"),
        (_ACCOUNT_API_PATTERNS, "account"),
        (_ACCOUNT_PATTERNS, "account"),
        (_KIWOOM_PATTERNS, "kiwoom"),
        (_LS_PATTERNS, "ls"),
        (_ORDER_API_PATTERNS, "order"),
        (_CREDENTIAL_PATTERNS, "credential"),
        (_PROVIDER_PATTERNS, "provider"),
        (_API_PATTERNS, "api"),
        (_NETWORK_PATTERNS, "network"),
        (_LIVE_TRADING_PATTERNS, "live_trading"),
        (_LIVE_PROD_PATTERNS, "live_prod"),
        (_DEPLOYMENT_PATTERNS, "deployment"),
        (_CLOUD_LLM_PATTERNS, "cloud_llm"),
        (_LOCAL_LLM_PATTERNS, "local_llm"),
        (_NEWS_PATTERNS, "news"),
        (_PARQUET_PATTERNS, "parquet"),
        (_REAL_ACTION_PATTERNS, "real_action"),
    )
    for key in _iter_dict_keys(data):
        for patterns, label in key_checks:
            _reject_patterns(patterns, key, label)
    for value in _iter_string_values(data):
        for patterns, label in key_checks:
            _reject_patterns(patterns, value, label)
    return data
