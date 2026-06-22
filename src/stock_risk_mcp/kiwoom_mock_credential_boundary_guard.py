from __future__ import annotations

import re


_RAW_SECRET_PATTERNS = (
    re.compile(r"\bappkey\b", re.IGNORECASE),
    re.compile(r"\bapp_key_value\b", re.IGNORECASE),
    re.compile(r"\bsecret_key_value\b", re.IGNORECASE),
    re.compile(r"\baccess_token\b", re.IGNORECASE),
    re.compile(r"\bauthorization\b", re.IGNORECASE),
    re.compile(r"\bbearer\b", re.IGNORECASE),
    re.compile(r"\baccount_number\b", re.IGNORECASE),
    re.compile(r"\bacct_no\b", re.IGNORECASE),
    re.compile(r"\bpassword\b", re.IGNORECASE),
    re.compile(r"\bcert\b", re.IGNORECASE),
    re.compile(r"\bprivate_key\b", re.IGNORECASE),
)
_ENVIRONMENT_READ_PATTERNS = (re.compile(r"environment[_ -]?read", re.IGNORECASE),)
_CREDENTIAL_FILE_READ_PATTERNS = (re.compile(r"credential[_ -]?file[_ -]?read", re.IGNORECASE),)
_TOKEN_ISSUE_PATTERNS = (re.compile(r"token[_ -]?issue", re.IGNORECASE),)
_TOKEN_REVOKE_PATTERNS = (re.compile(r"token[_ -]?revoke", re.IGNORECASE),)
_API_CALL_PATTERNS = (re.compile(r"api[_ -]?call", re.IGNORECASE),)
_MOCKAPI_CALL_PATTERNS = (re.compile(r"mockapi[_ -]?call", re.IGNORECASE),)
_WEBSOCKET_PATTERNS = (re.compile(r"websocket|socket|wss?://", re.IGNORECASE),)
_NETWORK_PATTERNS = (
    re.compile(r"network[_ -]?call", re.IGNORECASE),
    re.compile(r"https?://", re.IGNORECASE),
    re.compile(r"transport", re.IGNORECASE),
    re.compile(r"client", re.IGNORECASE),
)
_PRODUCTION_DOMAIN_PATTERNS = (
    re.compile(r"production[_ -]?domain[_ -]?execution", re.IGNORECASE),
    re.compile(r"https://api\.kiwoom\.com", re.IGNORECASE),
)
_LIVE_PROD_PATTERNS = (
    re.compile(r"\blive\b|\bprod\b", re.IGNORECASE),
    re.compile(r"live[_ -]?", re.IGNORECASE),
    re.compile(r"prod[_ -]?", re.IGNORECASE),
)
_REAL_ORDER_PATTERNS = (re.compile(r"real[_ -]?order", re.IGNORECASE),)
_LIVE_TRADING_PATTERNS = (re.compile(r"live[_ -]?trading", re.IGNORECASE),)
_ACCOUNT_MUTATION_PATTERNS = (re.compile(r"account[_ -]?mutation", re.IGNORECASE),)
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


def validate_kiwoom_mock_credential_boundary_metadata_safety(data, *, context: str):
    del context
    checks = (
        (_RAW_SECRET_PATTERNS, "raw credential value"),
        (_ENVIRONMENT_READ_PATTERNS, "environment read"),
        (_CREDENTIAL_FILE_READ_PATTERNS, "credential file read"),
        (_TOKEN_ISSUE_PATTERNS, "token issue"),
        (_TOKEN_REVOKE_PATTERNS, "token revoke"),
        (_MOCKAPI_CALL_PATTERNS, "mockapi call"),
        (_API_CALL_PATTERNS, "api call"),
        (_WEBSOCKET_PATTERNS, "websocket"),
        (_NETWORK_PATTERNS, "network"),
        (_PRODUCTION_DOMAIN_PATTERNS, "production domain execution"),
        (_REAL_ORDER_PATTERNS, "real order"),
        (_LIVE_TRADING_PATTERNS, "live trading"),
        (_ACCOUNT_MUTATION_PATTERNS, "account mutation"),
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
