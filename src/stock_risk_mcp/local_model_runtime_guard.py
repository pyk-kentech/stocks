from __future__ import annotations

from stock_risk_mcp.local_llm_advisory_guard import detect_unsafe_output
from stock_risk_mcp.local_model_runtime_models import LocalModelRuntimeFixture


def validate_prompt_task_alignment(fixture: LocalModelRuntimeFixture) -> None:
    if fixture.request.task_type.value.startswith("SUMMARIZE_") and not fixture.backend.capabilities.supports_structured_json_output:
        raise ValueError("summary tasks require structured output support")


def detect_unsafe_runtime_output(text: str | None) -> str | None:
    return detect_unsafe_output(text)
