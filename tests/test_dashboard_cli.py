import json
from datetime import date, datetime

from stock_risk_mcp.cli import main
from stock_risk_mcp.pipeline_run import PipelineMode, PipelineRun, PipelineRunStatus
from stock_risk_mcp.repository import RiskRepository


def test_dashboard_cli_commands(tmp_path, capsys) -> None:
    db = tmp_path / "risk.sqlite3"
    repository = RiskRepository(db)
    repository.save_pipeline_run(PipelineRun(
        pipeline_run_id="pipe-1", mode=PipelineMode.SCAN_ONLY, as_of_date=date(2026, 6, 13),
        status=PipelineRunStatus.COMPLETED, candidate_count=1, included_count=1, watch_count=0,
        basket_allocation_count=0, alert_count=0, created_at=datetime(2026, 6, 13),
    ))

    overview = _run(capsys, ["dashboard-overview", "--db", str(db), "--output-file", str(tmp_path / "overview.html"), "--save"])
    pipeline = _run(capsys, ["dashboard-pipeline", "--db", str(db), "--pipeline-run-id", "pipe-1", "--output-file", str(tmp_path / "pipeline.html"), "--save"])
    daily = _run(capsys, ["dashboard-daily", "--db", str(db), "--as-of-date", "2026-06-13", "--output-file", str(tmp_path / "daily.html"), "--save"])
    policy = _run(capsys, ["dashboard-policy", "--db", str(db), "--output-file", str(tmp_path / "policy.html"), "--save"])
    builds = _run(capsys, ["dashboard-builds", "--db", str(db)])
    shown = _run(capsys, ["dashboard-show", "--db", str(db), "--dashboard-id", overview["dashboard_id"]])

    assert all(item["dashboard_id"] for item in (overview, pipeline, daily, policy))
    assert len(builds["dashboard_builds"]) == 4
    assert shown["dashboard_id"] == overview["dashboard_id"]


def _run(capsys, args):
    main(args)
    return json.loads(capsys.readouterr().out)
