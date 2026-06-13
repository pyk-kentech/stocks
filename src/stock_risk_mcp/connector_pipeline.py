from __future__ import annotations

from datetime import date, datetime
from pathlib import Path

from stock_risk_mcp.connector_registry import ConnectorRegistry
from stock_risk_mcp.connector_run import (
    ConnectorMode, ConnectorResult, ConnectorRun, ConnectorRunStatus, ConnectorType,
)
from stock_risk_mcp.data_import import run_unified_import
from stock_risk_mcp.repository import RiskRepository


def run_connectors(
    repository: RiskRepository,
    registry: ConnectorRegistry,
    as_of_date: date,
    output_dir: str | Path,
    connector_names: list[str],
    tickers: list[str],
) -> list[ConnectorResult]:
    results: list[ConnectorResult] = []
    for name in connector_names:
        connector = None
        try:
            connector = registry.get_connector(name)
            if connector.mode == ConnectorMode.DISABLED:
                result = ConnectorResult(connector_run=ConnectorRun(
                    as_of_date=as_of_date, connector_name=connector.name, connector_type=connector.connector_type,
                    mode=connector.mode, status=ConnectorRunStatus.DISABLED,
                    warnings=["Connector is disabled."], completed_at=datetime.now(),
                ))
            else:
                result = connector.fetch(as_of_date, str(output_dir), tickers=tickers)
        except Exception as error:
            connector_type = getattr(connector, "connector_type", ConnectorType.UNKNOWN)
            mode = getattr(connector, "mode", ConnectorMode.MOCK)
            result = ConnectorResult(connector_run=ConnectorRun(
                as_of_date=as_of_date, connector_name=name, connector_type=connector_type, mode=mode,
                status=ConnectorRunStatus.FAILED, errors=[str(error)], completed_at=datetime.now(),
            ))
        repository.save_connector_run(result.connector_run)
        results.append(result)
    return results


def run_connectors_and_import(
    repository: RiskRepository,
    registry: ConnectorRegistry,
    as_of_date: date,
    output_dir: str | Path,
    connector_names: list[str],
    tickers: list[str],
) -> dict[str, object]:
    results = run_connectors(repository, registry, as_of_date, output_dir, connector_names, tickers)
    outputs = [item.output for item in results if item.output is not None]
    import_args: dict[str, object] = {}
    mapping = {
        ConnectorType.MARKET_DATA: "price_history_file",
        ConnectorType.NEWS: "news_signal_file",
        ConnectorType.DILUTION: "dilution_signal_file",
        ConnectorType.TOSS_PORTFOLIO: "toss_signal_file",
        ConnectorType.FLOW: "flow_signal_file",
        ConnectorType.COMPLIANCE: "nasdaq_noncompliant_file",
    }
    for output in outputs:
        argument = mapping.get(output.connector_type)
        if argument:
            import_args[argument] = output.output_path
    import_run = run_unified_import(
        repository, as_of_date=as_of_date,
        empty_input_note="no connector output files available for import",
        **import_args,
    )
    connector_failed = any(
        item.connector_run.status in {ConnectorRunStatus.FAILED, ConnectorRunStatus.DISABLED, ConnectorRunStatus.PARTIAL}
        for item in results
    )
    if not outputs and import_run.status.value == "FAILED":
        overall_status = "FAILED"
    elif connector_failed or import_run.status.value != "COMPLETED":
        overall_status = "PARTIAL"
    else:
        overall_status = "COMPLETED"
    return {
        "as_of_date": as_of_date.isoformat(),
        "connector_runs": [item.connector_run.model_dump(mode="json") for item in results],
        "connector_error_summary": [
            {"connector_name": item.connector_run.connector_name, "status": item.connector_run.status.value, "errors": item.connector_run.errors}
            for item in results if item.connector_run.status in {ConnectorRunStatus.FAILED, ConnectorRunStatus.DISABLED}
        ],
        "output_file_count": len(outputs),
        "import_run_id": import_run.import_run_id,
        "import_status": import_run.status.value,
        "status": import_run.status.value,
        "overall_status": overall_status,
    }
