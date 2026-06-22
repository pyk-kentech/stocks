from __future__ import annotations

import re


_RAW_SECRET_PATTERNS = (
    re.compile(r"\bsecretkey\b", re.IGNORECASE),
    re.compile(r"\bsecret[_ -]?key\b", re.IGNORECASE),
    re.compile(r"\bappkey\b", re.IGNORECASE),
    re.compile(r"\bapp[_ -]?key\b", re.IGNORECASE),
    re.compile(r"\braw[_ -]?secret\b", re.IGNORECASE),
)
_RAW_TOKEN_PATTERNS = (
    re.compile(r"\baccess[_ -]?token\b", re.IGNORECASE),
    re.compile(r"\brefresh[_ -]?token\b", re.IGNORECASE),
    re.compile(r"\bbearer\b", re.IGNORECASE),
)
_AUTH_PATTERNS = (
    re.compile(r"\bauthorization\b", re.IGNORECASE),
    re.compile(r"authorization[_ -]?header", re.IGNORECASE),
    re.compile(r"\bauth[_ -]?header\b", re.IGNORECASE),
)
_ACCOUNT_PATTERNS = (
    re.compile(r"\baccount[_ -]?number\b", re.IGNORECASE),
    re.compile(r"\bacct[_ -]?no\b", re.IGNORECASE),
    re.compile(r"\bacctno\b", re.IGNORECASE),
)
_ENV_PATTERNS = (re.compile(r"\benv(_var)?\b|environment[_ -]?read", re.IGNORECASE),)
_CREDENTIAL_FILE_PATTERNS = (re.compile(r"credential[_ -]?file|secret[_ -]?file", re.IGNORECASE),)
_OAUTH_EXEC_PATTERNS = (
    re.compile(r"token[_ -]?issue", re.IGNORECASE),
    re.compile(r"token[_ -]?revoke", re.IGNORECASE),
    re.compile(r"token[_ -]?refresh", re.IGNORECASE),
    re.compile(r"token[_ -]?storage", re.IGNORECASE),
)
_API_PATTERNS = (
    re.compile(r"api[_ -]?call", re.IGNORECASE),
    re.compile(r"mockapi[_ -]?call", re.IGNORECASE),
    re.compile(r"https?://", re.IGNORECASE),
    re.compile(r"websocket|wss?://", re.IGNORECASE),
    re.compile(r"network[_ -]?call|transport|httpx|requests", re.IGNORECASE),
)
_PRODUCTION_PATTERNS = (
    re.compile(r"https://api\.kiwoom\.com", re.IGNORECASE),
    re.compile(r"production[_ -]?domain", re.IGNORECASE),
    re.compile(r"\blive\b|\bprod\b", re.IGNORECASE),
)
_REAL_ORDER_PATTERNS = (
    re.compile(r"real[_ -]?order", re.IGNORECASE),
    re.compile(r"live[_ -]?trading", re.IGNORECASE),
    re.compile(r"account[_ -]?mutation|account[_ -]?read", re.IGNORECASE),
)
_LLM_PATTERNS = (
    re.compile(r"cloud[_ -]?llm|openai|gemini|claude", re.IGNORECASE),
    re.compile(r"local[_ -]?llm|ollama|vllm|llama", re.IGNORECASE),
)
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


def validate_kiwoom_mock_oauth_draft_metadata_safety(data, *, context: str):
    del context
    checks = (
        (_AUTH_PATTERNS, "authorization"),
        (_RAW_TOKEN_PATTERNS, "token"),
        (_RAW_SECRET_PATTERNS, "secret"),
        (_ACCOUNT_PATTERNS, "account"),
        (_ENV_PATTERNS, "environment read"),
        (_CREDENTIAL_FILE_PATTERNS, "credential file read"),
        (_OAUTH_EXEC_PATTERNS, "oauth execution"),
        (_API_PATTERNS, "api/mockapi/network execution"),
        (_PRODUCTION_PATTERNS, "production domain"),
        (_REAL_ORDER_PATTERNS, "real account/order/live trading"),
        (_LLM_PATTERNS, "llm runtime"),
        (_PARQUET_PATTERNS, "parquet"),
    )
    for key in _iter_dict_keys(data):
        for patterns, label in checks:
            _reject_patterns(patterns, key, label)
    for value in _iter_string_values(data):
        for patterns, label in checks:
            _reject_patterns(patterns, value, label)
    return data
