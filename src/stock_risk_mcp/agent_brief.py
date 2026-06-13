from __future__ import annotations

from datetime import datetime
from uuid import uuid4

from pydantic import Field

from stock_risk_mcp.models import StrictModel


class AgentBrief(StrictModel):
    brief_id: str = Field(default_factory=lambda: f"brief_{uuid4().hex}")
    source_id: str
    title: str
    summary: str
    key_points: list[str] = Field(default_factory=list)
    risks: list[str] = Field(default_factory=list)
    suggested_questions: list[str] = Field(default_factory=list)
    next_actions: list[str] = Field(default_factory=list)
    disclaimer: str
    generated_at: datetime = Field(default_factory=datetime.now)


def build_agent_brief(context) -> AgentBrief:
    report = context.context_json.get("report", {})
    metrics = report.get("key_metrics") or context.context_json.get("metrics", {})
    questions = report.get("context_json", {}).get("suggested_questions_for_llm") or context.context_json.get("suggested_questions_for_llm", [])
    return AgentBrief(
        source_id=context.source_id, title=f"Read-only research brief: {context.source_id}", summary=context.summary,
        key_points=[f"{key}: {value}" for key, value in metrics.items()], risks=context.warnings,
        suggested_questions=questions, next_actions=["Review risks and missing data before any paper-trading decision."],
        disclaimer="This brief is for paper trading and research support only. It is not financial advice.",
    )
