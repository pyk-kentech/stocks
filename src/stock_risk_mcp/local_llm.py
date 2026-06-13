from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from uuid import uuid4

from pydantic import Field

from stock_risk_mcp.models import StrictModel


class LocalLLMBackend(StrEnum):
    DRY_RUN = "DRY_RUN"
    OLLAMA_LOCAL = "OLLAMA_LOCAL"
    OPENAI_COMPAT_LOCAL = "OPENAI_COMPAT_LOCAL"
    DISABLED = "DISABLED"


class LocalLLMRequest(StrictModel):
    request_id: str = Field(default_factory=lambda: f"request_{uuid4().hex}")
    backend: LocalLLMBackend = LocalLLMBackend.DRY_RUN
    model: str | None = None
    endpoint_url: str | None = None
    prompt_id: str
    system_instructions: str
    user_prompt: str
    context_json: dict
    temperature: float = 0.2
    max_tokens: int | None = None
    created_at: datetime = Field(default_factory=datetime.now)
