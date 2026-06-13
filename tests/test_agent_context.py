from datetime import date, datetime

from stock_risk_mcp.agent_context import (
    AgentContextType,
    AgentPermissionLevel,
    build_agent_context_from_pipeline,
    build_agent_context_from_report,
)
from stock_risk_mcp.analysis_report import AnalysisReport, ReportType
from stock_risk_mcp.pipeline_run import PipelineMode, PipelineRun, PipelineRunStatus
from stock_risk_mcp.repository import RiskRepository


def test_report_builds_read_only_agent_context() -> None:
    report = AnalysisReport(
        report_id="report-1", report_type=ReportType.PIPELINE_SUMMARY, source_id="pipe-1",
        title="Pipeline Report", summary="Summary", context_json={"metrics": {"candidate_count": 2}},
    )

    context = build_agent_context_from_report(report)

    assert context.context_type == AgentContextType.ANALYSIS_REPORT
    assert context.permission_level == AgentPermissionLevel.READ_ONLY
    assert "execute_trade" in context.forbidden_actions
    assert context.context_json["report_id"] == "report-1"


def test_pipeline_builds_read_only_agent_context(tmp_path) -> None:
    repository = RiskRepository(tmp_path / "risk.sqlite3")
    repository.save_pipeline_run(PipelineRun(
        pipeline_run_id="pipe-1", mode=PipelineMode.SCAN_ONLY, as_of_date=date(2026, 6, 13),
        status=PipelineRunStatus.COMPLETED, candidate_count=2, included_count=1, watch_count=1,
        basket_allocation_count=0, alert_count=0, created_at=datetime(2026, 6, 13),
    ))

    context = build_agent_context_from_pipeline(repository, "pipe-1")

    assert context.context_type == AgentContextType.PIPELINE_RUN
    assert context.permission_level == AgentPermissionLevel.READ_ONLY
    assert context.context_json["metrics"]["candidate_count"] == 2
