from datetime import date, datetime

from stock_risk_mcp.dashboard import (
    build_daily_dashboard,
    build_overview_dashboard,
    build_pipeline_dashboard,
    build_policy_dashboard,
)
from stock_risk_mcp.dashboard_models import DashboardBuildStatus
from stock_risk_mcp.pipeline_run import PipelineMode, PipelineRun, PipelineRunStatus
from stock_risk_mcp.repository import RiskRepository


def test_dashboard_builders_create_static_html(tmp_path) -> None:
    repository = RiskRepository(tmp_path / "risk.sqlite3")
    repository.save_pipeline_run(PipelineRun(
        pipeline_run_id="pipe-1", mode=PipelineMode.SCAN_ONLY, as_of_date=date(2026, 6, 13),
        status=PipelineRunStatus.COMPLETED, candidate_count=1, included_count=1, watch_count=0,
        basket_allocation_count=0, alert_count=0, created_at=datetime(2026, 6, 13),
    ))

    results = [
        build_overview_dashboard(repository, tmp_path / "overview.html"),
        build_pipeline_dashboard(repository, "pipe-1", tmp_path / "pipeline.html"),
        build_daily_dashboard(repository, date(2026, 6, 13), tmp_path / "daily.html"),
        build_policy_dashboard(repository, tmp_path / "policy.html"),
    ]

    assert all(item.status in {DashboardBuildStatus.COMPLETED, DashboardBuildStatus.NO_DATA} for item in results)
    assert all("paper trading and research monitoring" in (tmp_path / f"{name}.html").read_text(encoding="utf-8") for name in ("overview", "pipeline", "daily", "policy"))


def test_dashboard_output_failure_returns_failed_result(tmp_path) -> None:
    repository = RiskRepository(tmp_path / "risk.sqlite3")
    bad_output = tmp_path / "directory"
    bad_output.mkdir()

    result = build_overview_dashboard(repository, bad_output)

    assert result.status == DashboardBuildStatus.FAILED
    assert result.errors
