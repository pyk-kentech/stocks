from datetime import date, datetime

from stock_risk_mcp.pipeline_run import AlertSeverity, AlertType, PipelineAlert, PipelineMode, PipelineRun, PipelineRunStatus
from stock_risk_mcp.repository import RiskRepository


def test_repository_round_trips_and_updates_pipeline_runs_and_alerts(tmp_path) -> None:
    repository = RiskRepository(tmp_path / "risk.sqlite3")
    run = _run(PipelineRunStatus.CREATED)
    alert = PipelineAlert(
        alert_id="alert-1", pipeline_run_id="pipe-1", alert_type=AlertType.CANDIDATE_FOUND,
        severity=AlertSeverity.INFO, title="Candidates", message="Found candidates.", created_at=datetime(2026, 1, 1),
    )

    repository.save_pipeline_run(run)
    repository.update_pipeline_run(run.model_copy(update={"status": PipelineRunStatus.COMPLETED}))
    repository.save_pipeline_alerts([alert])

    assert repository.get_pipeline_run("pipe-1").status == PipelineRunStatus.COMPLETED
    assert repository.list_pipeline_runs()[0].pipeline_run_id == "pipe-1"
    assert repository.list_pipeline_alerts("pipe-1") == [alert]


def _run(status):
    return PipelineRun(
        pipeline_run_id="pipe-1", mode=PipelineMode.SCAN_ONLY, as_of_date=date(2026, 1, 1),
        status=status, candidate_count=0, included_count=0, watch_count=0,
        basket_allocation_count=0, alert_count=0, created_at=datetime(2026, 1, 1),
    )
