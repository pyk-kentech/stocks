from datetime import date, datetime

from stock_risk_mcp.dashboard_sections import daily_sections, overview_sections, pipeline_sections, policy_sections
from stock_risk_mcp.pipeline_run import AlertSeverity, AlertType, PipelineAlert, PipelineMode, PipelineRun, PipelineRunStatus
from stock_risk_mcp.repository import RiskRepository


def test_dashboard_sections_include_expected_sources(tmp_path) -> None:
    repository = RiskRepository(tmp_path / "risk.sqlite3")
    repository.save_pipeline_run(PipelineRun(
        pipeline_run_id="pipe-1", mode=PipelineMode.SCAN_ONLY, as_of_date=date(2026, 6, 13),
        status=PipelineRunStatus.COMPLETED, candidate_count=2, included_count=1, watch_count=1,
        basket_allocation_count=0, alert_count=1, created_at=datetime(2026, 6, 14),
    ))
    repository.save_pipeline_alerts([PipelineAlert(
        alert_id="alert-1", pipeline_run_id="pipe-1", alert_type=AlertType.SIGNAL_CRITICAL,
        severity=AlertSeverity.CRITICAL, title="Critical alert", message="Review",
        created_at=datetime(2026, 6, 13),
    )])

    overview = overview_sections(repository, limit=20)
    pipeline = pipeline_sections(repository, "pipe-1")
    daily = daily_sections(repository, date(2026, 6, 13))
    policy = policy_sections(repository, limit=20)

    assert "Latest pipeline runs" in [item.title for item in overview]
    assert "Pipeline summary" in [item.title for item in pipeline]
    assert "Daily alerts" in [item.title for item in daily]
    assert "pipe-1" in next(item.html for item in daily if item.title == "Daily pipeline runs")
    assert "Active policy" in [item.title for item in policy]
