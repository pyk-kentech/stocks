from __future__ import annotations


_FORBIDDEN_KEY_FRAGMENTS = (
    "secret",
    "token",
    "authorization",
    "account",
    "password",
    "credential",
    "order",
    "broker",
)

_FORBIDDEN_VALUE_FRAGMENTS = (
    "api.kiwoom.com",
    "mockapi.kiwoom.com",
    "websocket",
    "ws://",
    "wss://",
    "http://",
    "https://",
    "broker",
    "order",
    "buy",
    "sell",
    "live",
    "prod",
    "autonomous",
    "gemini",
    "llm",
)


def validate_quant_strategy_robustness_metadata_safety(data, *, context: str) -> None:
    _walk(data, context=context)


def _walk(value, *, context: str) -> None:
    if isinstance(value, dict):
        for key, item in value.items():
            lowered_key = str(key).lower()
            if any(fragment in lowered_key for fragment in _FORBIDDEN_KEY_FRAGMENTS):
                raise ValueError(f"{context} contains forbidden field: {key}")
            _walk(item, context=context)
        return
    if isinstance(value, list):
        for item in value:
            _walk(item, context=context)
        return
    if isinstance(value, str):
        lowered = value.lower()
        if lowered.endswith(".parquet"):
            raise ValueError("parquet remains unsupported")
        if any(fragment in lowered for fragment in _FORBIDDEN_VALUE_FRAGMENTS):
            raise ValueError(f"{context} contains forbidden metadata")
