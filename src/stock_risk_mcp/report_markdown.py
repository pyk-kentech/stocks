from stock_risk_mcp.analysis_report import AnalysisReport
from stock_risk_mcp.report_templates import DISCLAIMER_EN, disclaimer, labels


def render_markdown(report: AnalysisReport, language: str = "en") -> str:
    text = labels(language)
    metrics = "\n".join(f"* `{key}`: {value}" for key, value in report.key_metrics.items()) or "* None"
    findings = [bullet for section in report.sections for bullet in section.bullets]
    risks = report.warnings or ["None"]
    questions = report.context_json.get("suggested_questions_for_llm", [])
    return "\n\n".join([
        f"# {report.title}",
        report.summary,
        f"## {text['key_metrics']}\n\n{metrics}",
        f"## {text['main_findings']}\n\n" + "\n".join(f"* {item}" for item in findings or ["None"]),
        f"## {text['risks']}\n\n" + "\n".join(f"* {item}" for item in risks),
        f"## {text['next_actions']}\n\n" + "\n".join(f"* {item}" for item in questions or ["Review stored evidence."]),
        f"## {text['disclaimer']}\n\n{disclaimer(language) if language == 'ko' and report.disclaimer == DISCLAIMER_EN else report.disclaimer}",
    ])
