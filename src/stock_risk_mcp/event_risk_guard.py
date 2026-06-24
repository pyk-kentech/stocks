from __future__ import annotations

import json
import re


_UNSAFE_PATTERNS = (
    re.compile(r"authorization|bearer|secret|credential|api[_ -]?key|token", re.IGNORECASE),
    re.compile(r"account(_id|_number)?|broker_order|broker_id|real_order|order_intent|execution_approval", re.IGNORECASE),
    re.compile(r"kiwoom|broker api|provider api|httpx|requests|websocket|network transport|mockapi", re.IGNORECASE),
    re.compile(r"investing\.com|fed api|bls api|bea api|bok api", re.IGNORECASE),
    re.compile(r"live|prod|autonomous", re.IGNORECASE),
    re.compile(r"cloud[_ -]?llm|ollama|llama|transformers|gemini", re.IGNORECASE),
)


def validate_event_risk_metadata_safety(value, *, context: str) -> None:
    rendered = json.dumps(value, default=str).lower() if not isinstance(value, str) else value.lower()
    for pattern in _UNSAFE_PATTERNS:
        if pattern.search(rendered):
            raise ValueError(f"unsafe metadata detected for {context}: {pattern.pattern}")
