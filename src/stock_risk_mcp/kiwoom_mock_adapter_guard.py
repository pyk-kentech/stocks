from __future__ import annotations

import re


_REAL_ORDER_PATTERNS = (
    re.compile(r"\breal[_ -]?order\b", re.IGNORECASE),
    re.compile(r"real[_ -]?order[_ -]?intent", re.IGNORECASE),
    re.compile(r"\borderintent\b", re.IGNORECASE),
    re.compile(r"\border[_ -]?intent\b", re.IGNORECASE),
    re.compile(r"\bexecutable[_ -]?order\b", re.IGNORECASE),
)
_REAL_ACCOUNT_MUTATION_PATTERNS = (
    re.compile(r"real[_ -]?account[_ -]?mutation", re.IGNORECASE),
    re.compile(r"account[_ -]?mutation", re.IGNORECASE),
    re.compile(r"real[_ -]?account[_ -]?number", re.IGNORECASE),
)
_LIVE_TRADING_PATTERNS = (re.compile(r"live[_ -]?trading", re.IGNORECASE),)
_LIVE_PROD_PATTERNS = (re.compile(r"\blive\b|\bprod\b", re.IGNORECASE),)
_CREDENTIAL_PATTERNS = (
    re.compile(r"credential", re.IGNORECASE),
    re.compile(r"token", re.IGNORECASE),
    re.compile(r"secret", re.IGNORECASE),
    re.compile(r"password", re.IGNORECASE),
    re.compile(r"app[_ -]?key", re.IGNORECASE),
    re.compile(r"secret[_ -]?key", re.IGNORECASE),
)
_OAUTH_PATTERNS = (re.compile(r"oauth", re.IGNORECASE),)
_AUTH_PATTERNS = (re.compile(r"authorization", re.IGNORECASE),)
_API_CALL_PATTERNS = (re.compile(r"api[_ -]?call", re.IGNORECASE),)
_MOCKAPI_CALL_PATTERNS = (re.compile(r"mockapi[_ -]?call", re.IGNORECASE),)
_NETWORK_PATTERNS = (
    re.compile(r"network", re.IGNORECASE),
    re.compile(r"https?://", re.IGNORECASE),
    re.compile(r"\bclient\b", re.IGNORECASE),
    re.compile(r"transport", re.IGNORECASE),
    re.compile(r"callback", re.IGNORECASE),
)
_WEBSOCKET_PATTERNS = (re.compile(r"websocket|wss?://|socket", re.IGNORECASE),)
_BROKER_API_PATTERNS = (re.compile(r"broker[_ -]?api", re.IGNORECASE),)
_ORDER_API_PATTERNS = (re.compile(r"order[_ -]?api", re.IGNORECASE),)
_ACCOUNT_API_PATTERNS = (re.compile(r"account[_ -]?api", re.IGNORECASE),)
_PROVIDER_API_PATTERNS = (re.compile(r"provider[_ -]?api", re.IGNORECASE),)
_CLOUD_LLM_PATTERNS = (re.compile(r"cloud[_ -]?llm|openai|gemini|claude", re.IGNORECASE),)
_LOCAL_LLM_PATTERNS = (re.compile(r"local[_ -]?llm|ollama|vllm|llama", re.IGNORECASE),)
_INVESTING_PATTERNS = (re.compile(r"investing\.com|investing", re.IGNORECASE),)
_FINVIZ_PATTERNS = (re.compile(r"finviz", re.IGNORECASE),)
_NEWS_PATTERNS = (re.compile(r"news[_ -]?ingest|news", re.IGNORECASE),)
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


def _reject_patterns(patterns, value: str, label: str):
    if any(pattern.search(value) for pattern in patterns):
        raise ValueError(label)


def validate_kiwoom_mock_adapter_metadata_safety(data, *, context: str):
    del context
    checks = (
        (_REAL_ORDER_PATTERNS, "real order"),
        (_REAL_ACCOUNT_MUTATION_PATTERNS, "real account mutation"),
        (_OAUTH_PATTERNS, "oauth token"),
        (_AUTH_PATTERNS, "authorization"),
        (_MOCKAPI_CALL_PATTERNS, "mockapi"),
        (_BROKER_API_PATTERNS, "broker api"),
        (_ORDER_API_PATTERNS, "order api"),
        (_ACCOUNT_API_PATTERNS, "account api"),
        (_PROVIDER_API_PATTERNS, "provider api"),
        (_API_CALL_PATTERNS, "api call"),
        (_CREDENTIAL_PATTERNS, "credentials"),
        (_WEBSOCKET_PATTERNS, "websocket"),
        (_NETWORK_PATTERNS, "network"),
        (_LIVE_TRADING_PATTERNS, "live trading"),
        (_LIVE_PROD_PATTERNS, "live/prod"),
        (_CLOUD_LLM_PATTERNS, "cloud llm"),
        (_LOCAL_LLM_PATTERNS, "local llm runtime"),
        (_INVESTING_PATTERNS, "investing.com"),
        (_FINVIZ_PATTERNS, "finviz"),
        (_NEWS_PATTERNS, "news ingestion"),
        (_PARQUET_PATTERNS, "parquet"),
    )
    for key in _iter_dict_keys(data):
        for patterns, label in checks:
            _reject_patterns(patterns, key, label)
    for value in _iter_string_values(data):
        for patterns, label in checks:
            _reject_patterns(patterns, value, label)
    return data
