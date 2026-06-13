from stock_risk_mcp.analysis_report import AnalysisReport, ReportSection, ReportSeverity, ReportType
from stock_risk_mcp.report_markdown import render_markdown


def test_markdown_contains_required_sections_and_disclaimer() -> None:
    report = AnalysisReport(
        report_type=ReportType.CANDIDATE_SCAN, source_id="scan-1", title="Candidate Scan Report",
        summary="Research summary.", key_metrics={"included_count": 2},
        sections=[ReportSection(title="Main Findings", summary="Findings.", bullets=["AAA"], severity=ReportSeverity.INFO)],
        context_json={"source_id": "scan-1"},
    )

    markdown = render_markdown(report)

    assert "# Candidate Scan Report" in markdown
    assert "## Key Metrics" in markdown
    assert "## Disclaimer" in markdown
    assert "not financial advice" in markdown


def test_markdown_supports_korean_template() -> None:
    report = AnalysisReport(
        report_type=ReportType.CANDIDATE_SCAN, source_id="scan-1", title="후보 스캔 보고서",
        summary="연구 요약", context_json={},
    )

    markdown = render_markdown(report, "ko")

    assert "## 핵심 지표" in markdown
    assert "투자 조언이 아닙니다" in markdown
