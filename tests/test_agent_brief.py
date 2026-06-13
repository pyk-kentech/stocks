from stock_risk_mcp.agent_brief import build_agent_brief
from stock_risk_mcp.agent_context import build_agent_context_from_report
from stock_risk_mcp.analysis_report import AnalysisReport, ReportType


def test_agent_brief_is_deterministic_without_llm() -> None:
    context = build_agent_context_from_report(AnalysisReport(
        report_type=ReportType.PIPELINE_SUMMARY, source_id="pipe-1", title="Pipeline", summary="Summary",
        key_metrics={"candidate_count": 2}, warnings=["Missing paper result"],
        context_json={"suggested_questions_for_llm": ["Explain risks."]},
    ))

    brief = build_agent_brief(context)

    assert "candidate_count: 2" in brief.key_points
    assert brief.risks == ["Missing paper result"]
    assert "not financial advice" in brief.disclaimer
