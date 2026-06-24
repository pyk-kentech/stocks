from __future__ import annotations

import json
import re


_UNSAFE_PATTERNS = (
    re.compile(r"authorization:\s*bearer\s+(?!<token_ref_only>)", re.IGNORECASE),
    re.compile(r"api[_ -]?key|secret|password|credential|env|os\.environ", re.IGNORECASE),
    re.compile(r"account(_id|_number)?|order(_id)?|execution|broker[_ -]?call", re.IGNORECASE),
    re.compile(r"kiwoom api call|ls api call|httpx|requests|aiohttp|websocket|network", re.IGNORECASE),
    re.compile(r"live|prod|autonomous", re.IGNORECASE),
    re.compile(r"token(?!_ref_only)", re.IGNORECASE),
    re.compile(r"gemini|cloud[_ -]?llm|ollama|llama|transformers", re.IGNORECASE),
)


def validate_read_only_provider_adapter_metadata_safety(value, *, context: str) -> None:
    rendered = json.dumps(value, default=str).lower() if not isinstance(value, str) else value.lower()
    for pattern in _UNSAFE_PATTERNS:
        if pattern.search(rendered):
            raise ValueError(f"unsafe metadata detected for {context}: {pattern.pattern}")
