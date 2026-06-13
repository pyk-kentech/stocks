from __future__ import annotations

from datetime import date

from stock_risk_mcp.local_llm_response import LocalLLMResponseStatus
from stock_risk_mcp.notification_templates import (
    DISCLAIMER,
    build_notifications_from_agent_brief,
    build_notifications_from_local_llm_response,
    build_notifications_from_pipeline,
    build_notifications_from_report,
)
from stock_risk_mcp.notifications import NotificationMessage, NotificationSeverity, SEVERITY_RANK, meets_minimum, sort_notifications


def build_daily_digest(
    repository,
    as_of_date: date,
    min_severity: NotificationSeverity,
    include_pipeline_runs: bool = True,
    include_reports: bool = True,
    include_agent_briefs: bool = True,
    include_local_llm_responses: bool = False,
) -> NotificationMessage:
    items: list[NotificationMessage] = []
    if include_pipeline_runs:
        run_ids = {item.pipeline_run_id for item in repository.list_pipeline_alerts(limit=1000) if item.created_at.date() == as_of_date}
        for run_id in run_ids:
            items.extend(build_notifications_from_pipeline(repository, run_id, min_severity))
    if include_reports:
        for report in repository.list_analysis_reports(1000):
            if report.generated_at.date() == as_of_date:
                items.extend(build_notifications_from_report(repository, report.report_id, min_severity))
    if include_agent_briefs:
        for brief in repository.list_agent_briefs(1000):
            if brief.generated_at.date() == as_of_date:
                items.extend(build_notifications_from_agent_brief(repository, brief.brief_id, min_severity))
    if include_local_llm_responses:
        for response in repository.list_local_llm_responses_by_date(as_of_date):
            if response.status == LocalLLMResponseStatus.FAILED:
                items.extend(build_notifications_from_local_llm_response(repository, response.response_id, min_severity))
    items = sort_notifications(items)
    critical = sum(item.severity == NotificationSeverity.CRITICAL for item in items)
    lines = [f"# Daily Research Notification Digest - {as_of_date.isoformat()}", "", f"No critical alerts: {'yes' if critical == 0 else 'no'}"]
    for item in items:
        lines.extend(["", f"## [{item.severity.value}] {item.title}", f"Source: {item.source_id}", item.message])
    severity = max((item.severity for item in items), key=lambda value: SEVERITY_RANK[value], default=NotificationSeverity.INFO)
    if not meets_minimum(severity, min_severity):
        severity = NotificationSeverity.INFO
    return NotificationMessage(
        source_type="daily_digest", source_id=as_of_date.isoformat(), severity=severity,
        title=f"Daily research notification digest - {as_of_date.isoformat()}",
        message="\n".join(lines) + f"\n\n{DISCLAIMER}", metadata={"item_count": len(items), "critical_count": critical},
        dedupe_key=f"daily_digest|{as_of_date.isoformat()}|{min_severity.value}|{include_local_llm_responses}",
    )
