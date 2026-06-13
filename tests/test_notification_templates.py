from datetime import date, datetime

from stock_risk_mcp.agent_brief import AgentBrief
from stock_risk_mcp.analysis_report import AnalysisReport, ReportType
from stock_risk_mcp.local_llm import LocalLLMBackend
from stock_risk_mcp.local_llm_response import LocalLLMResponse, LocalLLMResponseStatus
from stock_risk_mcp.notification_templates import (
    build_notifications_from_agent_brief,
    build_notifications_from_local_llm_response,
    build_notifications_from_pipeline,
    build_notifications_from_report,
)
from stock_risk_mcp.notifications import NotificationSeverity
from stock_risk_mcp.pipeline_run import AlertSeverity, AlertType, PipelineAlert, PipelineMode, PipelineRun, PipelineRunStatus
from stock_risk_mcp.repository import RiskRepository


def test_pipeline_notifications_filter_and_sort_critical_high_first(tmp_path) -> None:
    repository = RiskRepository(tmp_path / "risk.sqlite3")
    repository.save_pipeline_run(PipelineRun(
        pipeline_run_id="pipe-1", mode=PipelineMode.SCAN_ONLY, as_of_date=date(2026, 6, 13),
        status=PipelineRunStatus.COMPLETED, candidate_count=0, included_count=0, watch_count=0,
        basket_allocation_count=0, alert_count=3, created_at=datetime(2026, 6, 13),
    ))
    repository.save_pipeline_alerts([
        _alert("info", AlertSeverity.INFO), _alert("critical", AlertSeverity.CRITICAL),
        _alert("high", AlertSeverity.HIGH),
    ])

    messages = build_notifications_from_pipeline(repository, "pipe-1", NotificationSeverity.HIGH)

    assert [item.severity for item in messages] == [NotificationSeverity.CRITICAL, NotificationSeverity.HIGH]
    assert all("paper trading and research" in item.message for item in messages)


def test_report_and_brief_convert_warnings_and_risks(tmp_path) -> None:
    repository = RiskRepository(tmp_path / "risk.sqlite3")
    repository.save_analysis_report(AnalysisReport(
        report_id="report-1", report_type=ReportType.PIPELINE_SUMMARY, source_id="pipe-1",
        title="Report", summary="Summary", key_metrics={"count": 2}, warnings=["critical: blocked"],
        generated_at=datetime(2026, 6, 13),
    ))
    repository.save_agent_brief(AgentBrief(
        brief_id="brief-1", source_id="pipe-1", title="Brief", summary="Summary",
        key_points=["count: 2"], risks=["Missing data"], next_actions=["Review"],
        disclaimer="Research only.", generated_at=datetime(2026, 6, 13),
    ))

    report = build_notifications_from_report(repository, "report-1", NotificationSeverity.INFO)
    brief = build_notifications_from_agent_brief(repository, "brief-1", NotificationSeverity.INFO)

    assert report[0].severity == NotificationSeverity.CRITICAL
    assert brief[0].severity == NotificationSeverity.WARNING


def test_local_llm_response_mapping_and_preview_limit(tmp_path) -> None:
    repository = RiskRepository(tmp_path / "risk.sqlite3")
    completed = _response("completed", LocalLLMResponseStatus.COMPLETED, content="x" * 700)
    failed = _response("failed", LocalLLMResponseStatus.FAILED, error="offline")
    blocked = _response("blocked", LocalLLMResponseStatus.FAILED, error="non-local endpoint blocked")
    dry = _response("dry", LocalLLMResponseStatus.DRY_RUN)
    for item in (completed, failed, blocked, dry):
        repository.save_local_llm_response(item)

    completed_message = build_notifications_from_local_llm_response(repository, "completed", NotificationSeverity.INFO)[0]
    failed_message = build_notifications_from_local_llm_response(repository, "failed", NotificationSeverity.INFO)[0]
    blocked_message = build_notifications_from_local_llm_response(repository, "blocked", NotificationSeverity.INFO)[0]
    dry_message = build_notifications_from_local_llm_response(repository, "dry", NotificationSeverity.INFO)[0]

    assert completed_message.severity == NotificationSeverity.INFO
    assert len(completed_message.metadata["content_preview"]) <= 500
    assert "x" * 501 not in completed_message.message
    assert failed_message.severity == NotificationSeverity.WARNING
    assert blocked_message.severity == NotificationSeverity.HIGH
    assert dry_message.title == "Local LLM dry run completed"


def _alert(name, severity):
    return PipelineAlert(
        alert_id=name, pipeline_run_id="pipe-1", alert_type=AlertType.PIPELINE_ERROR,
        severity=severity, title=name, message=name, created_at=datetime(2026, 6, 13),
    )


def _response(response_id, status, content=None, error=None):
    return LocalLLMResponse(
        response_id=response_id, request_id=f"request-{response_id}", backend=LocalLLMBackend.DRY_RUN,
        model="local-model", status=status, content=content, error=error,
        warnings=[error] if error else [], created_at=datetime(2026, 6, 13),
    )
