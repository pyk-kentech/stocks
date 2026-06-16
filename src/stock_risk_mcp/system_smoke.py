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
from stock_risk_mcp.llm_feature_service import run_feature_store, run_signal_evaluation
from stock_risk_mcp.trade_plan_service import run_trade_plan
from stock_risk_mcp.paper_eval_service import run_paper_eval


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
    llm_signal_fixture = Path(output_dir) / "llm_signal_smoke_fixture.json"
    llm_signal_fixture.write_text(json.dumps({
        "schema_version": "3.4-signals", "run_id": f"llm-{result.demo_run_id}",
        "created_at": "2026-06-13T10:00:00+00:00",
        "prompt_version": {"prompt_version_id": "smoke-prompt", "name": "smoke", "version": "1", "prompt_checksum": "sha256:smoke", "created_at": "2026-06-13T08:00:00+00:00"},
        "model_version": {"model_version_id": "smoke-model", "backend": "LOCAL_FIXTURE", "model_name": "fixture", "model_version": "1", "runtime_metadata": {}},
        "signals": [{"ticker": "DEMO", "as_of_time": "2026-06-13T09:00:00+00:00", "source_ids": [], "event_type": "SMOKE", "theme_tags": [], "direction": "POSITIVE", "catalyst_strength_score": .8, "risk_language_score": .2, "uncertainty_score": .2, "related_tickers": [], "summary": "smoke", "evidence_refs": [], "may_create_order": False, "may_bypass_gates": False}],
    }, sort_keys=True), encoding="utf-8")
    llm_outcome_fixture = Path(output_dir) / "llm_outcome_smoke_fixture.json"
    llm_outcome_fixture.write_text(json.dumps({
        "schema_version": "3.4-outcomes", "created_at": "2026-06-14T16:00:00+00:00",
        "snapshots": [{"ticker": "DEMO", "as_of_time": "2026-06-13T09:00:00+00:00", "reference_price": 100, "horizons": [{"horizon": "1D", "outcome_time": "2026-06-14T09:00:00+00:00", "future_price": 105, "return_pct": 5, "max_drawdown_pct": 2}]}],
    }, sort_keys=True), encoding="utf-8")
    llm_features = run_feature_store(llm_signal_fixture)
    llm_evaluation = run_signal_evaluation(llm_signal_fixture, llm_outcome_fixture)
    trade_plan_fixture = Path(output_dir) / "trade_plan_smoke_fixture.json"
    trade_plan_fixture.write_text(json.dumps({
        "schema_version": "3.5-trade-plan-fixture",
        "run_id": f"trade-plan-{result.demo_run_id}",
        "created_at": "2026-06-13T10:00:00+00:00",
        "config": {
            "portfolio_equity": 100000.0,
            "risk_pct_per_trade": 0.01,
            "max_basket_risk_pct": 0.03,
            "fixed_min_risk_reward": 2.0,
        },
        "candidates": [{
            "ticker": "DEMO",
            "side": "BUY",
            "setup_type": "SMOKE_BREAKOUT",
            "setup_grade": "A",
            "entry_reference": 100.0,
            "stop_reference": 96.0,
            "target_reference": 108.0,
            "technical_evidence_summary": "local deterministic smoke fixture",
            "llm_signal_summary": "advisory only",
            "warnings": [],
        }],
    }, sort_keys=True), encoding="utf-8")
    trade_plan = run_trade_plan(trade_plan_fixture)
    paper_eval_fixture = Path(output_dir) / "paper_eval_smoke_fixture.json"
    paper_eval_fixture.write_text(json.dumps({
        "schema_version": "3.6-paper-eval-fixture",
        "run_id": f"paper-eval-{result.demo_run_id}",
        "created_at": "2026-06-13T10:00:00+00:00",
        "config": {
            "initial_cash": 100000.0,
            "allow_limit_entry_only": True,
            "fee_per_trade": 0.0,
            "slippage_per_share": 0.0,
            "same_bar_exit_policy": "STOP_FIRST",
            "max_open_positions": 10,
        },
        "inputs": [{
            "ticker": "DEMO",
            "source_type": "TRADE_PLAN",
            "decision_time": "2026-06-13T09:30:00+00:00",
            "side": "BUY",
            "setup_grade": "A",
            "entry_reference": 100.0,
            "stop_reference": 96.0,
            "target_reference": 108.0,
            "suggested_quantity": 10,
            "plan_status": "TRADE_PLAN_READY",
            "technical_evidence_summary": "local deterministic smoke fixture",
            "market_discovery_summary": "volume spike",
            "llm_signal_summary": "advisory only"
        }],
        "price_paths": [{
            "ticker": "DEMO",
            "bars": [
                {"timestamp": "2026-06-13T09:31:00+00:00", "open": 99.0, "high": 101.0, "low": 98.0, "close": 100.0},
                {"timestamp": "2026-06-13T09:32:00+00:00", "open": 100.0, "high": 109.0, "low": 100.0, "close": 108.0}
            ]
        }]
    }, sort_keys=True), encoding="utf-8")
    paper_eval = run_paper_eval(paper_eval_fixture)
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
            "llm_feature_store_fixture_run": llm_features.signal_count == 1,
            "llm_signal_evaluation_fixture_run": len(llm_evaluation.evaluations) == 3,
            "trade_plan_fixture_run": len(trade_plan.plans) == 1 and trade_plan.summary_counts["ready_count"] == 1,
            "paper_eval_fixture_run": len(paper_eval.paper_trades) == 1 and paper_eval.metrics.trade_count == 1,
            "llm_called": False,
            "external_network_calls": False,
        },
        "key_outputs": result.key_outputs,
        "warnings": result.warnings,
        "errors": result.errors,
        "disclaimer": "Local deterministic system smoke only; no external network calls or orders.",
    }
