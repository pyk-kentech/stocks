import json
from datetime import date, datetime

from stock_risk_mcp.agent_brief import AgentBrief
from stock_risk_mcp.analysis_report import AnalysisReport, ReportType
from stock_risk_mcp.cli import main
from stock_risk_mcp.local_llm import LocalLLMBackend
from stock_risk_mcp.local_llm_response import LocalLLMResponse, LocalLLMResponseStatus
from stock_risk_mcp.pipeline_run import AlertSeverity, AlertType, PipelineAlert, PipelineMode, PipelineRun, PipelineRunStatus
from stock_risk_mcp.repository import RiskRepository


def test_notification_cli_commands_and_local_response_digest(tmp_path, capsys) -> None:
    db = tmp_path / "risk.sqlite3"
    output = tmp_path / "pipeline.md"
    repository = RiskRepository(db)
    _save_sources(repository)

    pipeline = _run(capsys, [
        "notify-pipeline", "--db", str(db), "--pipeline-run-id", "pipe-1", "--channel", "local-file",
        "--output-file", str(output), "--min-severity", "warning", "--save",
    ])
    report = _run(capsys, ["notify-report", "--db", str(db), "--report-id", "report-1", "--channel", "mock", "--save"])
    brief = _run(capsys, ["notify-brief", "--db", str(db), "--brief-id", "brief-1", "--channel", "mock", "--save"])
    response = _run(capsys, [
        "notify-local-response", "--db", str(db), "--response-id", "response-1", "--channel", "mock", "--save",
    ])
    digest = _run(capsys, [
        "notify-digest", "--db", str(db), "--as-of-date", "2026-06-13", "--channel", "mock",
        "--include-local-llm-responses",
    ])
    runs = _run(capsys, ["notification-runs", "--db", str(db)])
    shown = _run(capsys, [
        "notification-show", "--db", str(db), "--notification-run-id", pipeline["notification_run_id"],
    ])
    messages = _run(capsys, ["notifications", "--db", str(db), "--source-id", "pipe-1"])

    assert output.exists()
    assert pipeline["status"] == "COMPLETED"
    assert report["notification_run_id"] and brief["notification_run_id"] and response["notification_run_id"]
    assert digest["status"] == "COMPLETED"
    assert runs["notification_runs"]
    assert shown["run"]["notification_run_id"] == pipeline["notification_run_id"]
    assert messages["notifications"]


def _save_sources(repository):
    repository.save_pipeline_run(PipelineRun(
        pipeline_run_id="pipe-1", mode=PipelineMode.SCAN_ONLY, as_of_date=date(2026, 6, 13),
        status=PipelineRunStatus.COMPLETED, candidate_count=1, included_count=1, watch_count=0,
        basket_allocation_count=0, alert_count=1, created_at=datetime(2026, 6, 13),
    ))
    repository.save_pipeline_alerts([PipelineAlert(
        alert_id="alert-1", pipeline_run_id="pipe-1", alert_type=AlertType.SIGNAL_CRITICAL,
        severity=AlertSeverity.CRITICAL, title="Critical", message="Review", created_at=datetime(2026, 6, 13),
    )])
    repository.save_analysis_report(AnalysisReport(
        report_id="report-1", report_type=ReportType.PIPELINE_SUMMARY, source_id="pipe-1",
        title="Report", summary="Summary", generated_at=datetime(2026, 6, 13),
    ))
    repository.save_agent_brief(AgentBrief(
        brief_id="brief-1", source_id="pipe-1", title="Brief", summary="Summary",
        disclaimer="Research only.", generated_at=datetime(2026, 6, 13),
    ))
    repository.save_local_llm_response(LocalLLMResponse(
        response_id="response-1", request_id="request-1", backend=LocalLLMBackend.OPENAI_COMPAT_LOCAL,
        status=LocalLLMResponseStatus.FAILED, error="non-local endpoint blocked",
        created_at=datetime(2026, 6, 13),
    ))


def _run(capsys, args):
    main(args)
    return json.loads(capsys.readouterr().out)
