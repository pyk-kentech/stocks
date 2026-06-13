from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from uuid import uuid4

from pydantic import Field

from stock_risk_mcp.agent_guardrails import FORBIDDEN_ACTIONS
from stock_risk_mcp.models import StrictModel
from stock_risk_mcp.report_context import pipeline_context


class AgentContextType(StrEnum):
    PIPELINE_RUN = "PIPELINE_RUN"
    ANALYSIS_REPORT = "ANALYSIS_REPORT"
    SCAN_RUN = "SCAN_RUN"
    BASKET_PLAN = "BASKET_PLAN"
    POLICY_EVALUATION = "POLICY_EVALUATION"
    DAILY_BRIEF = "DAILY_BRIEF"


class AgentPermissionLevel(StrEnum):
    READ_ONLY = "READ_ONLY"
    PROPOSE_ONLY = "PROPOSE_ONLY"
    DISABLED = "DISABLED"


class AgentContext(StrictModel):
    context_id: str = Field(default_factory=lambda: f"context_{uuid4().hex}")
    context_type: AgentContextType
    source_id: str
    generated_at: datetime = Field(default_factory=datetime.now)
    permission_level: AgentPermissionLevel = AgentPermissionLevel.READ_ONLY
    summary: str
    context_json: dict
    warnings: list[str] = Field(default_factory=list)
    forbidden_actions: list[str] = Field(default_factory=lambda: list(FORBIDDEN_ACTIONS))


def build_agent_context_from_report(report) -> AgentContext:
    return AgentContext(
        context_type=AgentContextType.ANALYSIS_REPORT, source_id=report.report_id, summary=report.summary,
        context_json={"report_id": report.report_id, "source_id": report.source_id, "report": report.model_dump(mode="json")},
        warnings=report.warnings,
    )


def build_agent_context_from_pipeline(repository, pipeline_run_id: str) -> AgentContext:
    context = pipeline_context(repository, pipeline_run_id)
    return AgentContext(
        context_type=AgentContextType.PIPELINE_RUN, source_id=pipeline_run_id,
        summary=f"Read-only pipeline research context for {pipeline_run_id}.",
        context_json=context, warnings=context.get("warnings", []),
    )
