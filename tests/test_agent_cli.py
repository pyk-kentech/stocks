import json

from stock_risk_mcp.analysis_report import AnalysisReport, ReportType
from stock_risk_mcp.cli import main
from stock_risk_mcp.repository import RiskRepository


def test_agent_cli_builds_context_prompt_brief_and_dry_run(tmp_path, capsys) -> None:
    db = tmp_path / "risk.sqlite3"
    repository = RiskRepository(db)
    repository.save_analysis_report(AnalysisReport(
        report_id="report-1", report_type=ReportType.PIPELINE_SUMMARY, source_id="pipe-1",
        title="Pipeline", summary="Summary", key_metrics={"candidate_count": 1},
    ))

    context = _run(capsys, ["agent-context-from-report", "--db", str(db), "--report-id", "report-1", "--save"])
    prompt = _run(capsys, ["agent-prompt", "--db", str(db), "--context-id", context["context_id"], "--save"])
    brief = _run(capsys, ["agent-brief", "--db", str(db), "--context-id", context["context_id"], "--save"])
    response = _run(capsys, ["agent-run-local", "--db", str(db), "--prompt-id", prompt["prompt_id"], "--backend", "dry-run", "--save"])

    assert context["permission_level"] == "READ_ONLY"
    assert brief["brief_id"]
    assert response["status"] == "DRY_RUN"
    assert response["request_saved"] is True
    assert response["response_saved"] is True
    assert len(_run(capsys, ["agent-contexts", "--db", str(db)])) == 1
    assert len(_run(capsys, ["agent-prompts", "--db", str(db)])) == 1
    assert len(_run(capsys, ["agent-briefs", "--db", str(db)])) == 1
    assert len(_run(capsys, ["local-llm-responses", "--db", str(db)])) == 1


def test_agent_cli_blocks_non_local_endpoint_and_persists_audit(tmp_path, capsys) -> None:
    db = tmp_path / "risk.sqlite3"
    repository = RiskRepository(db)
    repository.save_analysis_report(AnalysisReport(
        report_id="report-1", report_type=ReportType.PIPELINE_SUMMARY, source_id="pipe-1",
        title="Pipeline", summary="Summary",
    ))
    context = _run(capsys, ["agent-context-from-report", "--db", str(db), "--report-id", "report-1", "--save"])
    prompt = _run(capsys, ["agent-prompt", "--db", str(db), "--context-id", context["context_id"], "--save"])

    result = _run(capsys, [
        "agent-run-local", "--db", str(db), "--prompt-id", prompt["prompt_id"],
        "--backend", "openai-compat-local", "--endpoint-url", "https://api.openai.com/v1", "--save",
    ])

    assert result["backend"] == "OPENAI_COMPAT_LOCAL"
    assert result["endpoint_url"] == "https://api.openai.com/v1"
    assert result["status"] == "FAILED"
    assert result["error"] == "non-local endpoint blocked"
    assert result["request_saved"] is True
    assert result["response_saved"] is True


def test_agent_cli_without_save_does_not_persist_and_lists_read_only_tools(tmp_path, capsys) -> None:
    db = tmp_path / "risk.sqlite3"
    repository = RiskRepository(db)
    repository.save_analysis_report(AnalysisReport(
        report_id="report-1", report_type=ReportType.PIPELINE_SUMMARY, source_id="pipe-1",
        title="Pipeline", summary="Summary",
    ))

    context = _run(capsys, ["agent-context-from-report", "--db", str(db), "--report-id", "report-1"])
    tools = _run(capsys, ["agent-tools"])

    assert context["saved"] is False
    assert repository.count_rows("agent_contexts") == 0
    assert all(item["read_only"] for item in tools["tools"])


def _run(capsys, args):
    main(args)
    return json.loads(capsys.readouterr().out)
