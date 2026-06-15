from __future__ import annotations

import json
from datetime import date
from pathlib import Path

from stock_risk_mcp.demo_pipeline import DemoStepName, DemoStepStatus, run_local_demo
from stock_risk_mcp.repository import RiskRepository
from stock_risk_mcp.strategy_service import StrategyService
from stock_risk_mcp.strategy_backtest_service import StrategyBacktestService
from stock_risk_mcp.technical_evidence_service import run_technical_evidence
from stock_risk_mcp.market_discovery_service import run_market_discovery


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
    backtest_fixture = Path(output_dir) / "strategy_backtest_smoke_fixture.json"
    backtest_fixture.write_text(json.dumps({
        "schema_version": "3.1", "strategy_config": {},
        "backtest_config": {"initial_cash": 1000, "fixed_quantity": 1},
        "snapshots": [{
            "snapshot": {
                "snapshot_id": f"backtest-{snapshot_id}", "ticker": "DEMO", "region": "US",
                "observed_at": "2026-06-13T09:00:00+00:00",
                "features": {"signal_score": 0.8, "risk_score": 0.2, "hard_block": False},
            },
            "features_available_at": "2026-06-13T09:00:00+00:00",
        }],
        "candidate_events": [{
            "candidate": {
                "candidate_id": f"backtest-{candidate_id}", "snapshot_id": f"backtest-{snapshot_id}",
                "side": "BUY", "order_type": "LIMIT", "rationale": "local deterministic backtest smoke fixture",
            },
            "decision_timestamp": "2026-06-13T09:01:00+00:00",
        }],
        "price_paths": [{
            "ticker": "DEMO",
            "points": [
                {"timestamp": "2026-06-13T09:02:00+00:00", "price": 10},
                {"timestamp": "2026-06-13T09:03:00+00:00", "price": 11},
            ],
        }],
    }, sort_keys=True), encoding="utf-8")
    backtest = StrategyBacktestService(RiskRepository(db_path)).run_fixture(backtest_fixture)
    technical_fixture = Path(output_dir) / "technical_evidence_smoke_fixture.json"
    technical_points = [
        {"timestamp": f"2026-06-13T09:{index:02d}:00+00:00", "open": 100 + index, "high": 101 + index, "low": 99 + index, "close": 100 + index, "volume": 1000}
        for index in range(20)
    ]
    technical_fixture.write_text(json.dumps({
        "schema_version": "3.2", "as_of_timestamp": "2026-06-13T10:00:00+00:00",
        "config": {}, "series": [{"ticker": "DEMO", "points": technical_points}],
    }, sort_keys=True), encoding="utf-8")
    technical = run_technical_evidence(technical_fixture)
    discovery_fixture = Path(output_dir) / "market_discovery_smoke_fixture.json"
    discovery_fixture.write_text(json.dumps({
        "schema_version": "3.3",
        "as_of_timestamp": "2026-06-13T10:00:00+00:00",
        "scanner_config": {
            "min_price": 1,
            "max_price": 100,
            "min_price_change_pct": 2,
            "min_volume_spike_ratio": 1.5,
            "min_dollar_volume_spike_ratio": 1.5,
            "min_average_dollar_volume_20d": 10_000_000,
            "max_candidates": 10,
        },
        "rows": [{
            "ticker": "DEMO",
            "observed_at": "2026-06-13T09:59:00+00:00",
            "price": 12,
            "previous_close": 10,
            "volume": 3_000_000,
            "average_volume_20d": 1_000_000,
            "average_dollar_volume_20d": 20_000_000,
        }],
    }, sort_keys=True), encoding="utf-8")
    discovery = run_market_discovery(discovery_fixture)
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
            "strategy_backtest_fixture_run": backtest["run"].status == "COMPLETED" and backtest["report"].metric.trade_count == 1,
            "technical_evidence_fixture_run": len(technical.evidence) == 1,
            "market_discovery_fixture_run": len(discovery.candidates) == 1,
            "external_network_calls": False,
        },
        "key_outputs": result.key_outputs,
        "warnings": result.warnings,
        "errors": result.errors,
        "disclaimer": "Local deterministic system smoke only; no external network calls or orders.",
    }
