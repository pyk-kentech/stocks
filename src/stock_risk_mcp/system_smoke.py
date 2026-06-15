from __future__ import annotations

import json
from datetime import date
from pathlib import Path

from stock_risk_mcp.demo_pipeline import DemoStepName, DemoStepStatus, run_local_demo
from stock_risk_mcp.repository import RiskRepository
from stock_risk_mcp.strategy_service import StrategyService


def run_system_smoke(db_path, output_dir, as_of_date: date | None = None) -> dict[str, object]:
    result = run_local_demo(db_path, as_of_date or date(2026, 6, 13), output_dir)
    strategy_fixture = Path(output_dir) / "strategy_smoke_fixture.json"
    snapshot_id = f"smoke-snapshot-{result.demo_run_id}"
    candidate_id = f"smoke-candidate-{result.demo_run_id}"
    strategy_fixture.parent.mkdir(parents=True, exist_ok=True)
    strategy_fixture.write_text(json.dumps({
        "schema_version": "3.0", "config": {},
        "snapshots": [{
            "snapshot_id": snapshot_id, "ticker": "DEMO", "region": "US",
            "observed_at": "2026-06-13T00:00:00",
            "features": {"signal_score": 0.8, "risk_score": 0.2, "hard_block": False},
        }],
        "candidates": [{
            "candidate_id": candidate_id, "snapshot_id": snapshot_id,
            "side": "BUY", "order_type": "LIMIT", "quantity": 1,
            "limit_price": 10, "rationale": "local deterministic smoke fixture",
        }],
    }, sort_keys=True), encoding="utf-8")
    strategy = StrategyService(RiskRepository(db_path)).run_fixture(strategy_fixture)
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
            "strategy_fixture_run": strategy["run"].status.value == "COMPLETED" and len(strategy["decisions"]) == 1,
            "external_network_calls": False,
        },
        "key_outputs": result.key_outputs,
        "warnings": result.warnings,
        "errors": result.errors,
        "disclaimer": "Local deterministic system smoke only; no external network calls or orders.",
    }
