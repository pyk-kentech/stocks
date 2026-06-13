from datetime import date, datetime

from stock_risk_mcp.pipeline_report import build_pipeline_summary
from stock_risk_mcp.pipeline_run import AlertSeverity, AlertType, PipelineAlert, PipelineMode, PipelineRun, PipelineRunStatus


def test_pipeline_summary_keeps_highest_severity_alerts() -> None:
    run = PipelineRun(
        pipeline_run_id="pipe", mode=PipelineMode.PAPER_BASKET, as_of_date=date(2026, 1, 1),
        status=PipelineRunStatus.COMPLETED, candidate_count=10, included_count=2, watch_count=3,
        basket_allocation_count=2, alert_count=2, notes=["fixture"], created_at=datetime(2026, 1, 1),
    )
    alerts = [
        _alert("info", AlertSeverity.INFO),
        _alert("critical", AlertSeverity.CRITICAL),
    ]

    summary = build_pipeline_summary(run, alerts, basket_decision="PROPOSE", paper_outcome="WIN", realized_return_pct=4)

    assert summary.top_alerts[0].severity == AlertSeverity.CRITICAL
    assert summary.paper_outcome == "WIN"


def _alert(name, severity):
    return PipelineAlert(
        alert_id=name, pipeline_run_id="pipe", alert_type=AlertType.PIPELINE_ERROR,
        severity=severity, title=name, message=name, created_at=datetime(2026, 1, 1),
    )
