from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from uuid import uuid4

from pydantic import Field

from stock_risk_mcp.models import StrictModel
from stock_risk_mcp.report_templates import disclaimer, localized_report_text


class ReportType(StrEnum):
    PIPELINE_SUMMARY = "PIPELINE_SUMMARY"
    CANDIDATE_SCAN = "CANDIDATE_SCAN"
    BASKET_PLAN = "BASKET_PLAN"
    PAPER_RESULT = "PAPER_RESULT"
    POLICY_EVALUATION = "POLICY_EVALUATION"
    DAILY_WATCH = "DAILY_WATCH"


class ReportFormat(StrEnum):
    JSON = "JSON"
    MARKDOWN = "MARKDOWN"


class ReportSeverity(StrEnum):
    INFO = "INFO"
    WARNING = "WARNING"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class ReportSection(StrictModel):
    title: str
    summary: str
    bullets: list[str] = Field(default_factory=list)
    severity: ReportSeverity = ReportSeverity.INFO


class AnalysisReport(StrictModel):
    report_id: str = Field(default_factory=lambda: f"report_{uuid4().hex}")
    report_type: ReportType
    source_id: str
    generated_at: datetime = Field(default_factory=datetime.now)
    title: str
    summary: str
    sections: list[ReportSection] = Field(default_factory=list)
    key_metrics: dict = Field(default_factory=dict)
    warnings: list[str] = Field(default_factory=list)
    disclaimer: str = "This report is for paper trading and research support only. It is not financial advice."
    context_json: dict = Field(default_factory=dict)
    markdown: str | None = None


def build_pipeline_summary_report(repository, pipeline_run_id: str, language: str = "en") -> AnalysisReport:
    from stock_risk_mcp.report_context import pipeline_context
    return _build(ReportType.PIPELINE_SUMMARY, pipeline_run_id, "Pipeline Summary Report", pipeline_context(repository, pipeline_run_id, language), language)


def build_candidate_scan_report(repository, scan_run_id: str, language: str = "en") -> AnalysisReport:
    from stock_risk_mcp.report_context import scan_context
    return _build(ReportType.CANDIDATE_SCAN, scan_run_id, "Candidate Scan Report", scan_context(repository, scan_run_id, language), language)


def build_basket_plan_report(repository, basket_id: str, language: str = "en") -> AnalysisReport:
    from stock_risk_mcp.report_context import basket_context
    return _build(ReportType.BASKET_PLAN, basket_id, "Basket Plan Report", basket_context(repository, basket_id, language), language)


def build_policy_evaluation_report(repository, suite_id: str, language: str = "en") -> AnalysisReport:
    from stock_risk_mcp.report_context import policy_context
    return _build(ReportType.POLICY_EVALUATION, suite_id, "Policy Evaluation Report", policy_context(repository, suite_id, language), language)


def _build(report_type: ReportType, source_id: str, title: str, context: dict, language: str) -> AnalysisReport:
    metrics = context["metrics"]
    bullets = [f"{key}: {value}" for key, value in metrics.items()]
    report_title, summary, section_summary = localized_report_text(title, source_id, language)
    report = AnalysisReport(
        report_type=report_type, source_id=source_id, title=report_title, summary=summary,
        sections=[ReportSection(title="주요 분석" if language == "ko" else "Main Findings", summary=section_summary, bullets=bullets)],
        key_metrics=metrics, warnings=context.get("warnings", []), disclaimer=disclaimer(language), context_json=context,
    )
    from stock_risk_mcp.report_markdown import render_markdown
    return report.model_copy(update={"markdown": render_markdown(report, language)})
