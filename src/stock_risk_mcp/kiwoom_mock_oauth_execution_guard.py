from __future__ import annotations

import re


_KEY_PATTERNS = (
    (re.compile(r"authorization", re.IGNORECASE), "authorization"),
    (re.compile(r"access[_ -]?token|refresh[_ -]?token", re.IGNORECASE), "token"),
    (re.compile(r"secretkey|secret[_ -]?key|appkey|app[_ -]?key", re.IGNORECASE), "secret"),
    (re.compile(r"account[_ -]?number|acct[_ -]?no|acctno", re.IGNORECASE), "account"),
)

_VALUE_PATTERNS = (
    (re.compile(r"^Bearer\s+", re.IGNORECASE), "authorization"),
    (re.compile(r"authorization\s*:", re.IGNORECASE), "authorization"),
    (re.compile(r"access[_ -]?token|refresh[_ -]?token|raw-token", re.IGNORECASE), "token"),
    (re.compile(r"raw[_ -]?secret|secret-key|app-key", re.IGNORECASE), "secret"),
    (re.compile(r"https://api\.kiwoom\.com", re.IGNORECASE), "production domain"),
    (re.compile(r"\.parquet\b", re.IGNORECASE), "parquet"),
    (re.compile(r"account[_ -]?number|acct[_ -]?no|acctno", re.IGNORECASE), "account"),
    (re.compile(r"openai|gemini|claude|ollama|vllm|llama", re.IGNORECASE), "llm runtime"),
)


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


def validate_kiwoom_mock_oauth_execution_metadata_safety(data, *, context: str):
    del context
    for key in _iter_dict_keys(data):
        for pattern, label in _KEY_PATTERNS:
            if pattern.search(key):
                raise ValueError(label)
    for value in _iter_string_values(data):
        for pattern, label in _VALUE_PATTERNS:
            if pattern.search(value):
                raise ValueError(label)
    return data
