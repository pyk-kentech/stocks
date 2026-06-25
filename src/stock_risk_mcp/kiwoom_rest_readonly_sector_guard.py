from __future__ import annotations

import json
import re


_UNSAFE_PATTERNS = (
    re.compile(r"authorization:\s*bearer\s+(?!<token_ref_only>)", re.IGNORECASE),
    re.compile(r"api[_ -]?key|app[_ -]?key|secret|credential|password|token(?!_ref_only)", re.IGNORECASE),
    re.compile(r"os\.environ|env[_ -]?var|dotenv|credential file", re.IGNORECASE),
    re.compile(r"account(_id|_number|_no)?|order(_id)?|execution|broker[_ -]?order", re.IGNORECASE),
    re.compile(r"kt\d{5}|credit order|gold order|websocket|network", re.IGNORECASE),
    re.compile(r"live|prod|autonomous", re.IGNORECASE),
    re.compile(r"gemini|cloud[_ -]?llm|ollama|llama|transformers", re.IGNORECASE),
)


def validate_kiwoom_rest_sector_metadata_safety(value, *, context: str) -> None:
    rendered = json.dumps(value, default=str).lower() if not isinstance(value, str) else value.lower()
    for pattern in _UNSAFE_PATTERNS:
        if pattern.search(rendered):
            raise ValueError(f"unsafe metadata detected for {context}: {pattern.pattern}")
