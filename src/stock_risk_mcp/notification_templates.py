from __future__ import annotations

from stock_risk_mcp.local_llm_response import LocalLLMResponseStatus
from stock_risk_mcp.notifications import (
    NotificationMessage,
    NotificationSeverity,
    meets_minimum,
    sort_notifications,
)


DISCLAIMER = "This is a paper trading and research alert. It is not financial advice."


def build_notifications_from_pipeline(repository, pipeline_run_id: str, min_severity: NotificationSeverity) -> list[NotificationMessage]:
    repository.get_pipeline_run(pipeline_run_id)
    messages = [
        NotificationMessage(
            source_type="pipeline_alert", source_id=pipeline_run_id, severity=NotificationSeverity(alert.severity.value),
            title=alert.title, message=f"{alert.message}\n\n{DISCLAIMER}", metadata=alert.metadata,
            dedupe_key="|".join([pipeline_run_id, alert.alert_type.value, alert.ticker or "", alert.title]),
            created_at=alert.created_at,
        )
        for alert in repository.list_pipeline_alerts(pipeline_run_id)
    ]
    return _filtered(messages, min_severity)


def build_notifications_from_report(repository, report_id: str, min_severity: NotificationSeverity) -> list[NotificationMessage]:
    report = repository.get_analysis_report(report_id)
    severity = _text_severity(report.warnings)
    message = NotificationMessage(
        source_type="analysis_report", source_id=report_id, severity=severity, title=report.title,
        message=f"{report.summary}\n\nMetrics: {report.key_metrics}\nWarnings: {report.warnings}\n\n{DISCLAIMER}",
        metadata={"key_metrics": report.key_metrics, "warnings": report.warnings},
        dedupe_key=f"{report_id}|{severity.value}|{report.title}", created_at=report.generated_at,
    )
    return _filtered([message], min_severity)


def build_notifications_from_agent_brief(repository, brief_id: str, min_severity: NotificationSeverity) -> list[NotificationMessage]:
    brief = repository.get_agent_brief(brief_id)
    severity = NotificationSeverity.WARNING if brief.risks else NotificationSeverity.INFO
    message = NotificationMessage(
        source_type="agent_brief", source_id=brief_id, severity=severity, title=brief.title,
        message=f"{brief.summary}\n\nKey points: {brief.key_points}\nRisks: {brief.risks}\nNext actions: {brief.next_actions}\n\n{DISCLAIMER}",
        metadata={"key_points": brief.key_points, "risks": brief.risks, "next_actions": brief.next_actions},
        dedupe_key=f"{brief_id}|{severity.value}|{brief.title}", created_at=brief.generated_at,
    )
    return _filtered([message], min_severity)


def build_notifications_from_local_llm_response(repository, response_id: str, min_severity: NotificationSeverity) -> list[NotificationMessage]:
    response = repository.get_local_llm_response(response_id)
    if response.status == LocalLLMResponseStatus.COMPLETED:
        severity, title = NotificationSeverity.INFO, "Local LLM response completed"
        preview = (response.content or "")[:500]
        body = f"Backend: {response.backend.value}; model: {response.model}; response preview: {preview}"
    elif response.status == LocalLLMResponseStatus.DRY_RUN:
        severity, title = NotificationSeverity.INFO, "Local LLM dry run completed"
        preview = ""
        body = "The prompt was generated but was not sent to a model."
    else:
        severity = NotificationSeverity.HIGH if response.error == "non-local endpoint blocked" else NotificationSeverity.WARNING
        title, preview = "Local LLM response failed", ""
        body = f"Error: {response.error}; warnings: {response.warnings}"
    message = NotificationMessage(
        source_type="local_llm_response", source_id=response_id, severity=severity, title=title,
        message=f"{body}\n\n{DISCLAIMER}", metadata={"content_preview": preview, "error": response.error, "warnings": response.warnings},
        dedupe_key="|".join([response_id, response.status.value, response.backend.value, response.model or ""]),
        created_at=response.created_at,
    )
    return _filtered([message], min_severity)


def _text_severity(warnings: list[str]) -> NotificationSeverity:
    text = " ".join(warnings).lower()
    if "critical" in text:
        return NotificationSeverity.CRITICAL
    return NotificationSeverity.WARNING if warnings else NotificationSeverity.INFO


def _filtered(messages: list[NotificationMessage], minimum: NotificationSeverity) -> list[NotificationMessage]:
    return sort_notifications([item for item in messages if meets_minimum(item.severity, minimum)])
