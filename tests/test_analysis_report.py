from stock_risk_mcp.analysis_report import AnalysisReport, ReportSection, ReportSeverity, ReportType
from stock_risk_mcp.repository import RiskRepository


def test_analysis_report_repository_round_trip(tmp_path) -> None:
    repository = RiskRepository(tmp_path / "risk.sqlite3")
    report = AnalysisReport(
        report_id="report-1", report_type=ReportType.PIPELINE_SUMMARY, source_id="pipe-1",
        title="Pipeline report", summary="Stored evidence summary.",
        sections=[ReportSection(title="Findings", summary="One finding.", bullets=["Evidence"], severity=ReportSeverity.INFO)],
        key_metrics={"candidate_count": 1}, context_json={"source_id": "pipe-1"},
    )

    repository.save_analysis_report(report)

    assert repository.get_analysis_report("report-1") == report
    assert repository.list_analysis_reports() == [report]
