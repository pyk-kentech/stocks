from __future__ import annotations

from datetime import date

from stock_risk_mcp.dashboard_html import render_json, render_table
from stock_risk_mcp.dashboard_models import DashboardSection
from stock_risk_mcp.notifications import NotificationSeverity
from stock_risk_mcp.strategy_policy import StrategyPolicyStatus


def overview_sections(repository, as_of_date: date | None = None, limit: int = 20) -> list[DashboardSection]:
    runs = _date_filter(repository.list_pipeline_runs(limit), as_of_date, "created_at")
    alerts = _date_filter(repository.list_pipeline_alerts(limit=limit), as_of_date, "created_at")
    return [
        _section("Latest pipeline runs", runs, ["pipeline_run_id", "status", "candidate_count", "created_at"]),
        _section("Latest alerts", alerts, ["severity", "title", "pipeline_run_id", "created_at"], _alert_severity(alerts)),
        _section("Latest notification runs", _date_filter(repository.list_notification_runs(limit), as_of_date, "created_at"), ["notification_run_id", "status", "channel_type", "created_at"]),
        _section("Latest analysis reports", _date_filter(repository.list_analysis_reports(limit), as_of_date, "generated_at"), ["report_id", "report_type", "title", "generated_at"]),
        _section("Latest agent briefs", _date_filter(repository.list_agent_briefs(limit), as_of_date, "generated_at"), ["brief_id", "source_id", "title", "generated_at"]),
        _section("Latest local LLM responses", _date_filter(repository.list_local_llm_responses(limit), as_of_date, "created_at"), ["response_id", "status", "backend", "model", "created_at"]),
        _section("Latest import runs", _date_filter(repository.list_import_runs(limit), as_of_date, "created_at"), ["import_run_id", "status", "total_saved_count", "created_at"]),
        _section("Latest connector runs", _date_filter(repository.list_connector_runs(limit), as_of_date, "created_at"), ["connector_run_id", "connector_name", "status", "created_at"]),
        _object_section("Active policy", repository.get_active_strategy_policy(), "No active policy is stored."),
        _disclaimer_section(),
    ]


def pipeline_sections(repository, pipeline_run_id: str) -> list[DashboardSection]:
    run = repository.get_pipeline_run(pipeline_run_id)
    alerts = repository.list_pipeline_alerts(pipeline_run_id)
    notifications = repository.list_notification_messages(pipeline_run_id)
    reports = [item for item in repository.list_analysis_reports(1000) if item.source_id == pipeline_run_id]
    report_ids = {item.report_id for item in reports}
    briefs = [item for item in repository.list_agent_briefs(1000) if item.source_id == pipeline_run_id or item.source_id in report_ids]
    sections = [
        _object_section("Pipeline summary", run),
        _section("Candidate count", [{"candidate_count": run.candidate_count, "included_count": run.included_count, "watch_count": run.watch_count}]),
    ]
    if run.basket_id:
        try:
            sections.append(_object_section("Basket summary", repository.get_basket_plan(run.basket_id)))
        except LookupError:
            sections.append(DashboardSection(title="Basket summary", summary="Linked basket was not found.", html="<p>No stored record.</p>", severity=NotificationSeverity.WARNING))
        paper = repository.get_basket_backtest_result(run.basket_id)
        sections.append(_object_section("Paper result summary", paper, "No stored paper result."))
    else:
        sections.extend([_object_section("Basket summary", None, "No linked basket."), _object_section("Paper result summary", None, "No stored paper result.")])
    sections.extend([
        _section("Alerts", alerts, ["severity", "title", "message", "created_at"], _alert_severity(alerts)),
        _section("Notifications", notifications, ["severity", "title", "delivery_status", "created_at"]),
        _section("Linked reports", reports, ["report_id", "report_type", "title", "generated_at"]),
        _section("Agent briefs", briefs, ["brief_id", "title", "generated_at"]),
        DashboardSection(title="Warnings / errors", summary=f"{len(run.notes)} notes", html=render_json({"notes": run.notes, "error": run.error}), severity=NotificationSeverity.WARNING if run.notes or run.error else NotificationSeverity.INFO),
        _disclaimer_section(),
    ])
    return sections


def daily_sections(repository, as_of_date: date) -> list[DashboardSection]:
    runs = _date_filter(repository.list_pipeline_runs(1000), as_of_date, "as_of_date")
    alerts = _date_filter(repository.list_pipeline_alerts(limit=1000), as_of_date, "created_at")
    critical_count = sum(str(item.severity) == "CRITICAL" or getattr(item.severity, "value", "") == "CRITICAL" for item in alerts)
    return [
        _section("Daily pipeline runs", runs, ["pipeline_run_id", "status", "candidate_count", "created_at"]),
        _section("Daily alerts", alerts, ["severity", "title", "pipeline_run_id", "created_at"], _alert_severity(alerts)),
        _section("Daily notification digest", _date_filter(repository.list_notification_runs(1000), as_of_date, "created_at"), ["notification_run_id", "status", "delivered_count", "created_at"]),
        _section("Daily reports", _date_filter(repository.list_analysis_reports(1000), as_of_date, "generated_at"), ["report_id", "title", "generated_at"]),
        _section("Daily local LLM responses", _date_filter(repository.list_local_llm_responses(1000), as_of_date, "created_at"), ["response_id", "status", "backend", "created_at"]),
        _section("Daily import / connector runs", [*_date_filter(repository.list_import_runs(1000), as_of_date, "as_of_date"), *_date_filter(repository.list_connector_runs(1000), as_of_date, "as_of_date")]),
        DashboardSection(title="No critical alerts summary", summary="No critical alerts" if critical_count == 0 else f"{critical_count} critical alerts", html=render_json({"critical_alert_count": critical_count}), severity=NotificationSeverity.INFO if critical_count == 0 else NotificationSeverity.CRITICAL),
        _disclaimer_section(),
    ]


def policy_sections(repository, limit: int = 20) -> list[DashboardSection]:
    policies = repository.list_strategy_policies(limit)
    return [
        _object_section("Active policy", repository.get_active_strategy_policy(), "No active policy is stored."),
        _section("Draft policies", [item for item in policies if item.status == StrategyPolicyStatus.DRAFT]),
        _section("Approved policies", [item for item in policies if item.status == StrategyPolicyStatus.APPROVED]),
        _section("Recent policy evaluation suites", repository.list_policy_evaluation_suites(limit)),
        _section("Recent promotion proposals", repository.list_policy_promotion_proposals(limit)),
        DashboardSection(title="Policy safety warning", summary="This dashboard cannot approve or activate policy.", html="<p>Policy state changes require explicit CLI commands.</p>", severity=NotificationSeverity.WARNING),
        _disclaimer_section(),
    ]


def _section(title, items, columns=None, severity=NotificationSeverity.INFO):
    rows = [_dump(item) for item in items]
    return DashboardSection(title=title, summary=f"{len(rows)} stored records" if rows else "No stored records.", html=render_table(rows, columns), severity=severity)


def _object_section(title, item, empty="No stored record."):
    return DashboardSection(title=title, summary=empty if item is None else "Stored record summary.", html="<p>No stored record.</p>" if item is None else render_json(_dump(item)))


def _dump(item):
    return item.model_dump(mode="json") if hasattr(item, "model_dump") else dict(item)


def _date_filter(items, as_of_date, field):
    if as_of_date is None:
        return items
    matches = []
    for item in items:
        value = getattr(item, field, None)
        value_date = value.date() if hasattr(value, "date") else value
        if value_date == as_of_date:
            matches.append(item)
    return matches


def _alert_severity(alerts):
    values = {getattr(item.severity, "value", str(item.severity)) for item in alerts}
    for severity in (NotificationSeverity.CRITICAL, NotificationSeverity.HIGH, NotificationSeverity.WARNING):
        if severity.value in values:
            return severity
    return NotificationSeverity.INFO


def _disclaimer_section():
    return DashboardSection(title="Disclaimer", summary="Paper trading and research monitoring only.", html="<p>No investment advice or performance guarantee is provided.</p>", severity=NotificationSeverity.WARNING)
