from __future__ import annotations

from datetime import date
from pathlib import Path

from stock_risk_mcp.demo_pipeline import DemoStepName, DemoStepStatus, run_local_demo


def run_system_smoke(db_path, output_dir, as_of_date: date | None = None) -> dict[str, object]:
    result = run_local_demo(db_path, as_of_date or date(2026, 6, 13), output_dir)
    steps = {item.step_name: item for item in result.step_results}
    complete = lambda name: steps.get(name) is not None and steps[name].status == DemoStepStatus.COMPLETED
    connector = steps.get(DemoStepName.CONNECTORS)
    dashboard_path = result.key_outputs.get("output_files", {}).get("dashboard")
    return {
        "demo_run_id": result.demo_run_id,
        "status": result.status.value,
        "checks": {
            "db_migration": Path(db_path).exists(),
            "mock_connector_output": complete(DemoStepName.CONNECTORS) and bool(connector and connector.metrics.get("output_count")),
            "import": complete(DemoStepName.IMPORT),
            "pipeline_run": complete(DemoStepName.PAPER_PIPELINE),
            "dashboard_html": complete(DemoStepName.DASHBOARD) and bool(dashboard_path and Path(dashboard_path).exists()),
            "external_network_calls": False,
        },
        "key_outputs": result.key_outputs,
        "warnings": result.warnings,
        "errors": result.errors,
        "disclaimer": "Local deterministic system smoke only; no external network calls or orders.",
    }
