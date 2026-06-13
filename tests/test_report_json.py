from stock_risk_mcp.analysis_report import AnalysisReport, ReportType
from stock_risk_mcp.report_json import render_json


def test_json_context_contains_source_and_metrics() -> None:
    report = AnalysisReport(
        report_type=ReportType.PIPELINE_SUMMARY, source_id="pipe-1", title="Report", summary="Summary",
        key_metrics={"alert_count": 2}, context_json={"source_id": "pipe-1"},
    )

    payload = render_json(report)

    assert payload["source_id"] == "pipe-1"
    assert payload["key_metrics"]["alert_count"] == 2
