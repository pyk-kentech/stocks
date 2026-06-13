from __future__ import annotations

from datetime import datetime
from uuid import uuid4

from pydantic import Field

from stock_risk_mcp.agent_guardrails import FORBIDDEN_ACTIONS, READ_ONLY_SYSTEM_INSTRUCTIONS
from stock_risk_mcp.models import StrictModel


class AgentPrompt(StrictModel):
    prompt_id: str = Field(default_factory=lambda: f"prompt_{uuid4().hex}")
    context_id: str
    system_instructions: str
    user_prompt: str
    context_json: dict
    guardrails: list[str] = Field(default_factory=list)
    generated_at: datetime = Field(default_factory=datetime.now)


def build_agent_prompt(context, language: str = "en") -> AgentPrompt:
    user_prompt = (
        "저장된 근거를 바탕으로 위험, 가정, 오래되거나 누락된 데이터를 설명하세요. 투자 조언이나 즉시 매수를 권하지 마세요."
        if language == "ko"
        else "Explain the stored evidence, risks, assumptions, stale data, and missing data without investment advice."
    )
    return AgentPrompt(
        context_id=context.context_id, system_instructions=READ_ONLY_SYSTEM_INSTRUCTIONS,
        user_prompt=user_prompt, context_json=context.context_json, guardrails=list(FORBIDDEN_ACTIONS),
    )
