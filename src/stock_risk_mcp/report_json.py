from stock_risk_mcp.analysis_report import AnalysisReport


def render_json(report: AnalysisReport) -> dict[str, object]:
    return report.model_dump(mode="json")
