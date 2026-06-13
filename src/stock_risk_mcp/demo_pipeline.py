from __future__ import annotations

from datetime import date, datetime, timedelta
from enum import StrEnum
from pathlib import Path
from uuid import uuid4

from pydantic import Field

from stock_risk_mcp.agent_context import build_agent_context_from_report
from stock_risk_mcp.agent_prompt import build_agent_prompt
from stock_risk_mcp.analysis_report import build_pipeline_summary_report
from stock_risk_mcp.connector_pipeline import run_connectors
from stock_risk_mcp.connector_registry import default_connector_registry
from stock_risk_mcp.connector_run import ConnectorRunStatus, ConnectorType
from stock_risk_mcp.dashboard import build_pipeline_dashboard
from stock_risk_mcp.data_import import run_unified_import
from stock_risk_mcp.demo_report import write_demo_summary
from stock_risk_mcp.import_run import ImportRunStatus
from stock_risk_mcp.local_llm import LocalLLMBackend, LocalLLMRequest
from stock_risk_mcp.local_llm_client import LocalLLMClient
from stock_risk_mcp.models import StrictModel
from stock_risk_mcp.notification_outbox import deliver_notifications
from stock_risk_mcp.notification_templates import build_notifications_from_pipeline
from stock_risk_mcp.notifications import NotificationChannelType, NotificationSeverity
from stock_risk_mcp.operational_pipeline import OperationalPipeline
from stock_risk_mcp.pipeline_run import PipelineRunStatus
from stock_risk_mcp.repository import RiskRepository


class DemoStepStatus(StrEnum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    SKIPPED = "SKIPPED"
    FAILED = "FAILED"


class DemoStepName(StrEnum):
    CONNECTORS = "CONNECTORS"
    IMPORT = "IMPORT"
    PAPER_PIPELINE = "PAPER_PIPELINE"
    ANALYSIS_REPORT = "ANALYSIS_REPORT"
    AGENT_CONTEXT = "AGENT_CONTEXT"
    AGENT_PROMPT = "AGENT_PROMPT"
    LOCAL_LLM_DRY_RUN = "LOCAL_LLM_DRY_RUN"
    NOTIFICATION = "NOTIFICATION"
    DASHBOARD = "DASHBOARD"
    SUMMARY = "SUMMARY"


class DemoStepResult(StrictModel):
    step_name: DemoStepName
    status: DemoStepStatus = DemoStepStatus.PENDING
    source_id: str | None = None
    output_path: str | None = None
    metrics: dict = Field(default_factory=dict)
    warnings: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)


class DemoRunStatus(StrEnum):
    COMPLETED = "COMPLETED"
    PARTIAL = "PARTIAL"
    FAILED = "FAILED"


class DemoRunResult(StrictModel):
    demo_run_id: str = Field(default_factory=lambda: f"demo_{uuid4().hex}")
    status: DemoRunStatus
    as_of_date: date
    db_path: str
    output_dir: str
    step_results: list[DemoStepResult] = Field(default_factory=list)
    key_outputs: dict = Field(default_factory=dict)
    warnings: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.now)
    completed_at: datetime | None = None


DEFAULT_CONNECTORS = [
    "mock_market_data", "mock_news_signal", "mock_dilution_signal",
    "mock_toss_signal", "mock_flow_signal",
]
CORE_STEPS = {DemoStepName.CONNECTORS, DemoStepName.IMPORT, DemoStepName.PAPER_PIPELINE}


def run_local_demo(
    db_path,
    as_of_date: date,
    output_dir,
    tickers: list[str] | None = None,
    account_equity: float = 10_000,
    cash_available: float = 5_000,
    horizon_days: int = 10,
    save_intermediate: bool = True,
    connector_names: list[str] | None = None,
) -> DemoRunResult:
    created_at = datetime.now()
    output = Path(output_dir)
    tickers = tickers or ["AAPL", "TSLA", "NVDA"]
    connectors = DEFAULT_CONNECTORS if connector_names is None else connector_names
    steps: list[DemoStepResult] = []
    keys: dict[str, object] = {"output_files": {}}
    warnings: list[str] = []
    errors: list[str] = []
    try:
        repository = RiskRepository(db_path)
        output.mkdir(parents=True, exist_ok=True)
    except Exception as error:
        failed = _failed(DemoStepName.CONNECTORS, error)
        return DemoRunResult(
            status=DemoRunStatus.FAILED, as_of_date=as_of_date, db_path=str(db_path), output_dir=str(output),
            step_results=[failed], key_outputs=keys, errors=failed.errors, created_at=created_at,
            completed_at=datetime.now(),
        )

    connector_results = None
    try:
        connector_results = run_connectors(repository, default_connector_registry(), as_of_date, output / "connectors", connectors, tickers)
        failed = [item for item in connector_results if item.connector_run.status != ConnectorRunStatus.COMPLETED]
        step = DemoStepResult(
            step_name=DemoStepName.CONNECTORS, status=DemoStepStatus.FAILED if failed else DemoStepStatus.COMPLETED,
            metrics={"connector_count": len(connector_results), "output_count": sum(item.output is not None for item in connector_results), "network_access": False},
            warnings=[warning for item in connector_results for warning in item.connector_run.warnings],
            errors=[error for item in connector_results for error in item.connector_run.errors],
        )
        keys["connector_run_ids"] = [item.connector_run.connector_run_id for item in connector_results]
    except Exception as error:
        step = _failed(DemoStepName.CONNECTORS, error)
    steps.append(step)

    import_run = None
    if step.status == DemoStepStatus.COMPLETED:
        try:
            import_run = _import_connector_outputs(repository, connector_results, as_of_date)
            status = DemoStepStatus.COMPLETED if import_run.status == ImportRunStatus.COMPLETED else DemoStepStatus.FAILED
            step = DemoStepResult(
                step_name=DemoStepName.IMPORT, status=status, source_id=import_run.import_run_id,
                metrics={"status": import_run.status.value, "saved_count": import_run.total_saved_count, "error_count": import_run.total_error_count},
                warnings=import_run.notes, errors=[error for item in import_run.source_results for error in item.errors],
            )
            keys["import_run_id"] = import_run.import_run_id
        except Exception as error:
            step = _failed(DemoStepName.IMPORT, error)
    else:
        step = _skipped(DemoStepName.IMPORT, "Connector step did not complete.")
    steps.append(step)

    execution = None
    if step.status == DemoStepStatus.COMPLETED:
        try:
            pipeline_date = as_of_date - timedelta(days=horizon_days)
            execution = OperationalPipeline(repository).run_paper_basket_pipeline(
                pipeline_date, account_equity, cash_available, horizon_days,
                save_basket=save_intermediate, save_replay_snapshot=save_intermediate, paper_trade=True,
            )
            pipeline_ok = execution.run.status not in {PipelineRunStatus.FAILED, PipelineRunStatus.PARTIAL}
            step = DemoStepResult(
                step_name=DemoStepName.PAPER_PIPELINE, status=DemoStepStatus.COMPLETED if pipeline_ok else DemoStepStatus.FAILED,
                source_id=execution.run.pipeline_run_id,
                metrics={"pipeline_status": execution.run.status.value, "connector_as_of_date": as_of_date.isoformat(), "pipeline_as_of_date": pipeline_date.isoformat(), "candidate_count": execution.run.candidate_count},
                warnings=execution.run.notes, errors=[execution.run.error] if execution.run.error else [],
            )
            keys["pipeline_run_id"] = execution.run.pipeline_run_id
        except Exception as error:
            step = _failed(DemoStepName.PAPER_PIPELINE, error)
    else:
        step = _skipped(DemoStepName.PAPER_PIPELINE, "Import step did not complete.")
    steps.append(step)

    pipeline_ok = step.status == DemoStepStatus.COMPLETED and execution is not None
    report = context = prompt = response = None
    if pipeline_ok:
        try:
            report = build_pipeline_summary_report(repository, execution.run.pipeline_run_id)
            if save_intermediate:
                repository.save_analysis_report(report)
            report_path = output / "report.md"
            report_warnings: list[str] = []
            try:
                report_path.write_text(report.markdown or report.summary, encoding="utf-8")
                keys["output_files"]["report"] = str(report_path)
            except Exception as error:
                report_warnings.append(f"failed to write optional report.md: {error}")
            step = DemoStepResult(
                step_name=DemoStepName.ANALYSIS_REPORT, status=DemoStepStatus.COMPLETED,
                source_id=report.report_id, output_path=str(report_path), warnings=report_warnings,
            )
            keys["report_id"] = report.report_id
        except Exception as error:
            step = _failed(DemoStepName.ANALYSIS_REPORT, error)
    else:
        step = _skipped(DemoStepName.ANALYSIS_REPORT, "Paper pipeline did not complete.")
    steps.append(step)

    if step.status == DemoStepStatus.COMPLETED and report is not None:
        try:
            context = build_agent_context_from_report(report)
            if save_intermediate:
                repository.save_agent_context(context)
            step = DemoStepResult(step_name=DemoStepName.AGENT_CONTEXT, status=DemoStepStatus.COMPLETED, source_id=context.context_id)
            keys["context_id"] = context.context_id
        except Exception as error:
            step = _failed(DemoStepName.AGENT_CONTEXT, error)
    else:
        step = _skipped(DemoStepName.AGENT_CONTEXT, "Analysis report did not complete.")
    steps.append(step)

    if step.status == DemoStepStatus.COMPLETED and context is not None:
        try:
            prompt = build_agent_prompt(context)
            if save_intermediate:
                repository.save_agent_prompt(prompt)
            step = DemoStepResult(step_name=DemoStepName.AGENT_PROMPT, status=DemoStepStatus.COMPLETED, source_id=prompt.prompt_id)
            keys["prompt_id"] = prompt.prompt_id
        except Exception as error:
            step = _failed(DemoStepName.AGENT_PROMPT, error)
    else:
        step = _skipped(DemoStepName.AGENT_PROMPT, "Agent context did not complete.")
    steps.append(step)

    if step.status == DemoStepStatus.COMPLETED and prompt is not None:
        try:
            request = LocalLLMRequest(
                backend=LocalLLMBackend.DRY_RUN, prompt_id=prompt.prompt_id,
                system_instructions=prompt.system_instructions, user_prompt=prompt.user_prompt, context_json=prompt.context_json,
            )
            response = LocalLLMClient().run(request)
            if save_intermediate:
                repository.save_local_llm_request(request)
                repository.save_local_llm_response(response)
            step = DemoStepResult(step_name=DemoStepName.LOCAL_LLM_DRY_RUN, status=DemoStepStatus.COMPLETED, source_id=response.response_id, metrics={"status": response.status.value, "network_access": False})
            keys["local_llm_response_id"] = response.response_id
        except Exception as error:
            step = _failed(DemoStepName.LOCAL_LLM_DRY_RUN, error)
    else:
        step = _skipped(DemoStepName.LOCAL_LLM_DRY_RUN, "Agent prompt did not complete.")
    steps.append(step)

    if pipeline_ok:
        try:
            notification_path = output / "notification.md"
            messages = build_notifications_from_pipeline(repository, execution.run.pipeline_run_id, NotificationSeverity.INFO)
            notification = deliver_notifications(repository, messages, NotificationChannelType.LOCAL_FILE, output_path=notification_path, save=save_intermediate)
            if not notification_path.exists():
                notification_path.write_text("# No pipeline alerts\n\nLocal system demo produced no notification messages.\n", encoding="utf-8")
            status = DemoStepStatus.FAILED if notification.failed_count else DemoStepStatus.COMPLETED
            step = DemoStepResult(step_name=DemoStepName.NOTIFICATION, status=status, source_id=notification.notification_run_id, output_path=str(notification_path), metrics={"delivered_count": notification.delivered_count}, errors=notification.errors)
            keys["notification_run_id"], keys["output_files"]["notification"] = notification.notification_run_id, str(notification_path)
        except Exception as error:
            step = _failed(DemoStepName.NOTIFICATION, error)
    else:
        step = _skipped(DemoStepName.NOTIFICATION, "Paper pipeline did not complete.")
    steps.append(step)

    if pipeline_ok:
        try:
            dashboard_path = output / "dashboard.html"
            dashboard = build_pipeline_dashboard(repository, execution.run.pipeline_run_id, dashboard_path, save=save_intermediate)
            status = DemoStepStatus.FAILED if dashboard.status.value == "FAILED" else DemoStepStatus.COMPLETED
            step = DemoStepResult(step_name=DemoStepName.DASHBOARD, status=status, source_id=dashboard.dashboard_id, output_path=str(dashboard_path), errors=dashboard.errors)
            keys["dashboard_id"], keys["output_files"]["dashboard"] = dashboard.dashboard_id, str(dashboard_path)
        except Exception as error:
            step = _failed(DemoStepName.DASHBOARD, error)
    else:
        step = _skipped(DemoStepName.DASHBOARD, "Paper pipeline did not complete.")
    steps.append(step)

    summary_path = output / "demo_summary.json"
    summary = DemoStepResult(step_name=DemoStepName.SUMMARY, status=DemoStepStatus.COMPLETED, output_path=str(summary_path))
    keys["output_files"]["summary"] = str(summary_path)
    steps.append(summary)
    result = DemoRunResult(
        status=_overall_status(steps), as_of_date=as_of_date, db_path=str(db_path), output_dir=str(output),
        step_results=steps, key_outputs=keys,
        errors=[error for item in steps for error in item.errors],
        warnings=[warning for item in steps for warning in item.warnings],
        created_at=created_at, completed_at=datetime.now(),
    )
    try:
        write_demo_summary(result, summary_path)
    except Exception as error:
        steps[-1] = _failed(DemoStepName.SUMMARY, error)
        keys["output_files"].pop("summary", None)
        result = result.model_copy(update={
            "status": _overall_status(steps), "step_results": steps, "key_outputs": keys,
            "errors": [error for item in steps for error in item.errors],
        })
    return result


def _import_connector_outputs(repository, results, as_of_date):
    mapping = {
        ConnectorType.MARKET_DATA: "price_history_file", ConnectorType.NEWS: "news_signal_file",
        ConnectorType.DILUTION: "dilution_signal_file", ConnectorType.TOSS_PORTFOLIO: "toss_signal_file",
        ConnectorType.FLOW: "flow_signal_file", ConnectorType.COMPLIANCE: "nasdaq_noncompliant_file",
    }
    kwargs = {mapping[item.output.connector_type]: item.output.output_path for item in results if item.output and item.output.connector_type in mapping}
    return run_unified_import(repository, as_of_date=as_of_date, empty_input_note="no connector output files available for import", **kwargs)


def _failed(name, error):
    return DemoStepResult(step_name=name, status=DemoStepStatus.FAILED, errors=[str(error)])


def _skipped(name, reason):
    return DemoStepResult(step_name=name, status=DemoStepStatus.SKIPPED, warnings=[reason])


def _overall_status(steps):
    failed = {item.step_name for item in steps if item.status == DemoStepStatus.FAILED}
    if failed & CORE_STEPS:
        return DemoRunStatus.FAILED
    if failed or any(item.status == DemoStepStatus.SKIPPED for item in steps):
        return DemoRunStatus.PARTIAL
    return DemoRunStatus.COMPLETED
