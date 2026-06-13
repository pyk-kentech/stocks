from stock_risk_mcp.agent_context import build_agent_context_from_report
from stock_risk_mcp.agent_prompt import build_agent_prompt
from stock_risk_mcp.analysis_report import AnalysisReport, ReportType


def test_agent_prompt_contains_read_only_guardrails_and_korean_option() -> None:
    context = build_agent_context_from_report(AnalysisReport(
        report_type=ReportType.CANDIDATE_SCAN, source_id="scan-1", title="Scan", summary="Summary",
    ))

    prompt = build_agent_prompt(context, language="ko")

    assert "read-only" in prompt.system_instructions
    assert "Never execute orders" in prompt.system_instructions
    assert "투자 조언" in prompt.user_prompt
    assert "activate_policy" in prompt.guardrails
