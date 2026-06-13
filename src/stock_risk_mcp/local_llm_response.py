from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from uuid import uuid4

from pydantic import Field

from stock_risk_mcp.local_llm import LocalLLMBackend
from stock_risk_mcp.models import StrictModel


class LocalLLMResponseStatus(StrEnum):
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    DRY_RUN = "DRY_RUN"


class LocalLLMResponse(StrictModel):
    response_id: str = Field(default_factory=lambda: f"response_{uuid4().hex}")
    request_id: str
    backend: LocalLLMBackend
    model: str | None = None
    status: LocalLLMResponseStatus
    content: str | None = None
    error: str | None = None
    warnings: list[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.now)
