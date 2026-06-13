from __future__ import annotations

from datetime import date
from pathlib import Path

from stock_risk_mcp.dashboard_html import render_dashboard_html
from stock_risk_mcp.dashboard_models import DashboardBuildResult, DashboardBuildStatus, DashboardType
from stock_risk_mcp.dashboard_sections import daily_sections, overview_sections, pipeline_sections, policy_sections


def build_overview_dashboard(repository, output_file, as_of_date: date | None = None, limit: int = 20, save: bool = False):
    return _build(repository, DashboardType.OVERVIEW, "Local Research Overview", output_file, overview_sections(repository, as_of_date, limit), as_of_date=as_of_date, save=save)


def build_pipeline_dashboard(repository, pipeline_run_id: str, output_file, save: bool = False):
    return _build(repository, DashboardType.PIPELINE_RUN, f"Pipeline Dashboard: {pipeline_run_id}", output_file, pipeline_sections(repository, pipeline_run_id), source_id=pipeline_run_id, save=save)


def build_daily_dashboard(repository, as_of_date: date, output_file, save: bool = False):
    return _build(repository, DashboardType.DAILY, f"Daily Dashboard: {as_of_date.isoformat()}", output_file, daily_sections(repository, as_of_date), as_of_date=as_of_date, save=save)


def build_policy_dashboard(repository, output_file, limit: int = 20, save: bool = False):
    return _build(repository, DashboardType.POLICY, "Policy Research Dashboard", output_file, policy_sections(repository, limit), save=save)


def _build(repository, dashboard_type, title, output_file, sections, as_of_date=None, source_id=None, save=False):
    output = Path(output_file)
    warnings: list[str] = []
    errors: list[str] = []
    status = DashboardBuildStatus.COMPLETED
    try:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(render_dashboard_html(title, dashboard_type, sections), encoding="utf-8")
        if all(item.summary.startswith("No ") or item.title == "Disclaimer" for item in sections):
            status = DashboardBuildStatus.NO_DATA
    except Exception as error:
        status = DashboardBuildStatus.FAILED
        errors.append(f"failed to write dashboard output: {error}")
    result = DashboardBuildResult(
        dashboard_type=dashboard_type, as_of_date=as_of_date, source_id=source_id, status=status,
        output_path=str(output), section_count=len(sections), warnings=warnings, errors=errors,
    )
    if save:
        repository.save_dashboard_build(result)
    return result
