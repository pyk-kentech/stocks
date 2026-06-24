from __future__ import annotations

import json
import re


_UNSAFE_PATTERNS = (
    re.compile(r"authorization|bearer|secret|credential", re.IGNORECASE),
    re.compile(r"account_number|account_id|order_intent|real_order|execution_approval", re.IGNORECASE),
    re.compile(r"websocket|httpx|requests|mockapi|api call|network requests", re.IGNORECASE),
    re.compile(r"live|prod|autonomous", re.IGNORECASE),
    re.compile(r"cloud[_ -]?llm|ollama|llama|transformers|gemini", re.IGNORECASE),
)


def validate_market_data_provider_registry_metadata_safety(value, *, context: str) -> None:
    rendered = json.dumps(value, default=str).lower() if not isinstance(value, str) else value.lower()
    for pattern in _UNSAFE_PATTERNS:
        if pattern.search(rendered):
            raise ValueError(f"unsafe metadata detected for {context}: {pattern.pattern}")
