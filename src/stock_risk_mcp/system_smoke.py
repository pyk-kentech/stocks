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
from stock_risk_mcp.walk_forward_policy_service import run_walk_forward_policy_replay
from stock_risk_mcp.local_llm_advisory_service import run_local_llm_advisory
from stock_risk_mcp.local_model_runtime_service import run_local_model_advisory_dry_run, run_local_model_runtime_check
from stock_risk_mcp.local_model_benchmark_service import run_local_model_benchmark_cli
from stock_risk_mcp.local_model_decision_report_service import run_local_model_decision_report_cli
from stock_risk_mcp.strategy_track_service import run_strategy_track_compare, run_strategy_track_profile_validation
from stock_risk_mcp.market_profit_service import run_market_profit_estimate
from stock_risk_mcp.domestic_realtime_service import (
    run_domestic_realtime_plan_show,
    run_domestic_realtime_profile_validate,
    run_domestic_realtime_quality_report,
)
from stock_risk_mcp.domestic_scanner_service import (
    run_domestic_scanner_candidates,
    run_domestic_scanner_quality_report,
)
from stock_risk_mcp.domestic_candidate_evaluation_service import (
    run_domestic_candidate_evaluate,
    run_domestic_candidate_evaluation_safety_report,
)
from stock_risk_mcp.domestic_replay_service import (
    run_domestic_replay_promotion_readiness,
    run_domestic_replay_run,
)
from stock_risk_mcp.domestic_calibration_service import (
    run_domestic_calibration_run,
    run_domestic_promotion_gate_report,
)
from stock_risk_mcp.domestic_paper_shadow_service import (
    run_domestic_paper_shadow_journal_build,
    run_domestic_paper_shadow_review_report,
    run_domestic_paper_shadow_safety_report,
)
from stock_risk_mcp.domestic_shadow_outcome_service import (
    run_domestic_shadow_outcome_label,
    run_domestic_shadow_outcome_review_report,
    run_domestic_shadow_outcome_safety_report,
)
from stock_risk_mcp.domestic_shadow_advisory_context_service import (
    run_domestic_shadow_advisory_context_build,
    run_domestic_shadow_advisory_context_gap_report,
    run_domestic_shadow_advisory_context_safety_report,
    run_domestic_shadow_advisory_context_validate,
)
from stock_risk_mcp.domestic_distillation_dataset_service import (
    run_domestic_distillation_dataset_build,
    run_domestic_distillation_dataset_gap_report,
    run_domestic_distillation_dataset_safety_report,
    run_domestic_distillation_dataset_validate,
)
from stock_risk_mcp.domestic_market_regime_service import (
    run_domestic_market_regime_classify,
    run_domestic_market_regime_gap_report,
    run_domestic_market_regime_report,
    run_domestic_market_regime_safety_report,
)
from stock_risk_mcp.domestic_regime_aware_integration_service import (
    run_domestic_regime_aware_gap_report,
    run_domestic_regime_aware_integration_build,
    run_domestic_regime_aware_integration_report,
    run_domestic_regime_aware_safety_report,
)
from stock_risk_mcp.offline_prompt_pack_service import (
    run_prompt_pack_coverage_report,
    run_prompt_pack_gap_report,
    run_prompt_pack_validate,
)
from stock_risk_mcp.historical_data_service import (
    run_historical_data_gap_report,
    run_historical_data_manifest_build,
    run_historical_data_quality_report,
    run_historical_data_validate,
)
from stock_risk_mcp.historical_data_engine import (
    build_historical_data_gap_report,
    build_historical_data_manifest,
    build_historical_data_quality_report,
    build_historical_data_validation_report,
    parse_historical_data_records,
)
from stock_risk_mcp.historical_data_fixture import load_historical_data_fixture
from stock_risk_mcp.historical_data_models import HistoricalDataAuditRecord, HistoricalMarketDataSnapshot
from stock_risk_mcp.historical_calendar_service import (
    run_historical_calendar_gap_report,
    run_historical_calendar_validate,
)
from stock_risk_mcp.historical_calendar_fixture import load_historical_calendar_fixture
from stock_risk_mcp.historical_calendar_engine import (
    build_historical_calendar_manifest,
    build_historical_calendar_gap_report,
    build_historical_calendar_validation_report,
    parse_corporate_event_records,
    parse_market_event_records,
    parse_trading_session_records,
)
from stock_risk_mcp.historical_calendar_models import HistoricalCalendarEventSnapshot
from stock_risk_mcp.historical_replay_bridge_engine import (
    build_historical_replay_event_stream,
    build_historical_replay_windows,
    build_historical_scanner_replay_input,
)
from stock_risk_mcp.historical_replay_bridge_fixture import HistoricalReplayBridgeFixture
from stock_risk_mcp.historical_replay_bridge_models import HistoricalReplayBridgeConfig
from stock_risk_mcp.historical_outcome_engine import (
    build_historical_outcome_label_report,
    build_historical_outcome_windows,
)
from stock_risk_mcp.historical_outcome_models import HistoricalOutcomeObservationInput
from stock_risk_mcp.historical_dataset_engine import build_historical_dataset_assembly
from stock_risk_mcp.historical_dataset_models import HistoricalDatasetAssemblyInput
from stock_risk_mcp.historical_dataset_validation_engine import build_historical_dataset_validation
from stock_risk_mcp.historical_dataset_validation_models import HistoricalDatasetValidationInput


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
    policy_replay_fixture = Path(output_dir) / "policy_replay_smoke_fixture.json"
    policy_replay_fixture.write_text(json.dumps({
        "schema_version": "3.7-policy-replay-fixture",
        "run_id": f"policy-replay-{result.demo_run_id}",
        "created_at": "2026-06-13T10:00:00+00:00",
        "window_config": {
            "train_window_count": 2,
            "eval_window_count": 1,
            "window_stride": 1,
            "minimum_eval_trades": 1
        },
        "promotion_gates": {
            "minimum_sample_count": 1,
            "max_drawdown_pct_cap": 12.0,
            "minimum_return_improvement_pct": 1.0,
            "minimum_stability_score": 0.5,
            "max_missing_data_rate": 0.5,
            "max_blocked_rate": 0.5
        },
        "baseline_policy": {
            "policy_id": "baseline-v1",
            "score_weights": {"technical": 0.5, "discovery": 0.3, "llm": 0.2},
            "minimum_score_threshold": 70.0,
            "minimum_risk_reward": 2.0,
            "allowed_setup_grades": ["A", "B"],
            "max_risk_pct_per_trade": 0.01,
            "max_basket_risk_pct": 0.03,
            "llm_weight_cap": 0.25,
            "allow_short": False,
            "allow_margin": False,
            "allow_leverage": False,
            "allow_market_orders": False
        },
        "candidate_policies": [{
            "policy_id": "candidate-v2",
            "score_weights": {"technical": 0.7, "discovery": 0.2, "llm": 0.1},
            "minimum_score_threshold": 70.0,
            "minimum_risk_reward": 2.0,
            "allowed_setup_grades": ["A", "B"],
            "max_risk_pct_per_trade": 0.01,
            "max_basket_risk_pct": 0.03,
            "llm_weight_cap": 0.20,
            "allow_short": False,
            "allow_margin": False,
            "allow_leverage": False,
            "allow_market_orders": False
        }],
        "replay_rows": [
            {
                "ticker": "DEMO", "timestamp": "2026-06-11T09:30:00+00:00", "setup_grade": "A",
                "technical_score": 80.0, "discovery_score": 70.0, "llm_score": 60.0,
                "entry_reference": 100.0, "stop_reference": 96.0, "target_reference": 108.0, "price_path_id": "DEMO-1"
            },
            {
                "ticker": "DEMO", "timestamp": "2026-06-12T09:30:00+00:00", "setup_grade": "A",
                "technical_score": 85.0, "discovery_score": 70.0, "llm_score": 60.0,
                "entry_reference": 100.0, "stop_reference": 96.0, "target_reference": 108.0, "price_path_id": "DEMO-2"
            },
            {
                "ticker": "DEMO", "timestamp": "2026-06-13T09:30:00+00:00", "setup_grade": "A",
                "technical_score": 90.0, "discovery_score": 70.0, "llm_score": 60.0,
                "entry_reference": 100.0, "stop_reference": 96.0, "target_reference": 108.0, "price_path_id": "DEMO-3"
            }
        ],
        "price_paths": [
            {"price_path_id": "DEMO-1", "ticker": "DEMO", "bars": [
                {"timestamp": "2026-06-11T09:31:00+00:00", "open": 99.5, "high": 101.0, "low": 99.0, "close": 100.0},
                {"timestamp": "2026-06-11T09:32:00+00:00", "open": 100.0, "high": 109.0, "low": 100.0, "close": 108.0}
            ]},
            {"price_path_id": "DEMO-2", "ticker": "DEMO", "bars": [
                {"timestamp": "2026-06-12T09:31:00+00:00", "open": 99.5, "high": 101.0, "low": 99.0, "close": 100.0},
                {"timestamp": "2026-06-12T09:32:00+00:00", "open": 100.0, "high": 109.0, "low": 100.0, "close": 108.0}
            ]},
            {"price_path_id": "DEMO-3", "ticker": "DEMO", "bars": [
                {"timestamp": "2026-06-13T09:31:00+00:00", "open": 99.5, "high": 101.0, "low": 99.0, "close": 100.0},
                {"timestamp": "2026-06-13T09:32:00+00:00", "open": 100.0, "high": 109.0, "low": 100.0, "close": 108.0}
            ]}
        ]
    }, sort_keys=True), encoding="utf-8")
    policy_replay = run_walk_forward_policy_replay(policy_replay_fixture)
    llm_advisory_fixture = Path(output_dir) / "local_llm_advisory_smoke_fixture.json"
    llm_advisory_fixture.write_text(json.dumps({
        "schema_version": "3.8-local-llm-advisory-fixture",
        "run_id": f"llm-advisory-{result.demo_run_id}",
        "created_at": "2026-06-13T10:00:00+00:00",
        "task_type": "SUMMARIZE_TECHNICAL_EVIDENCE",
        "backend": {
            "backend_type": "DISABLED",
            "model_name": "disabled",
            "model_version": "0",
            "runtime_metadata": {}
        },
        "prompt_metadata": {
            "prompt_id": "smoke-advisory",
            "prompt_version": "1",
            "prompt_checksum": "sha256:smoke"
        },
        "inputs": {
            "ticker": "DEMO",
            "title": "technical summary",
            "text_blocks": ["RSI recovered above 50", "Price above 20 EMA"]
        },
        "safety": {
            "advisory_only": True,
            "may_create_order": False,
            "may_bypass_gates": False
        }
    }, sort_keys=True), encoding="utf-8")
    llm_advisory = run_local_llm_advisory(llm_advisory_fixture)
    local_model_runtime_disabled_fixture = Path(output_dir) / "local_model_runtime_disabled_smoke_fixture.json"
    local_model_runtime_disabled_fixture.write_text(json.dumps({
        "schema_version": "3.9-local-model-runtime-fixture",
        "run_id": f"local-model-runtime-disabled-{result.demo_run_id}",
        "created_at": "2026-06-13T10:00:00+00:00",
        "backend": {
            "backend_type": "DISABLED",
            "adapter_name": "disabled-runtime",
            "model_name": "disabled",
            "model_version": "0",
            "capabilities": {
                "supports_mock_execution": False,
                "supports_structured_json_output": True,
                "supports_korean": True,
                "supports_english": True,
                "supports_mixed_language": True,
                "supports_refusal_mode": True,
                "supports_timeout_budget": True,
                "supports_resource_budget": True,
                "supports_health_check": True,
                "supports_streaming": False,
                "requires_network": False,
                "requires_credentials": False,
                "may_create_order": False,
                "may_bypass_gates": False
            },
            "runtime_metadata": {}
        },
        "request": {
            "task_type": "SUMMARIZE_TECHNICAL_EVIDENCE",
            "ticker": "DEMO",
            "text_blocks": ["RSI recovered above 50", "Price above 20 EMA"]
        },
        "runtime_limits": {
            "timeout_ms": 500,
            "max_output_tokens": 300,
            "max_memory_mb": 1024
        },
        "mock_response": {
            "response_text": "Disabled runtime path",
            "bullet_points": ["No runtime execution"],
            "risk_labels": []
        },
        "safety": {
            "advisory_only": True,
            "may_create_order": False,
            "may_bypass_gates": False
        }
    }, sort_keys=True), encoding="utf-8")
    local_model_runtime_mock_fixture = Path(output_dir) / "local_model_runtime_mock_smoke_fixture.json"
    local_model_runtime_mock_fixture.write_text(json.dumps({
        "schema_version": "3.9-local-model-runtime-fixture",
        "run_id": f"local-model-runtime-mock-{result.demo_run_id}",
        "created_at": "2026-06-13T10:00:00+00:00",
        "backend": {
            "backend_type": "MOCK_LOCAL_RUNTIME",
            "adapter_name": "mock-local-runtime-v1",
            "model_name": "mock-qwen-class",
            "model_version": "0",
            "capabilities": {
                "supports_mock_execution": True,
                "supports_structured_json_output": True,
                "supports_korean": True,
                "supports_english": True,
                "supports_mixed_language": True,
                "supports_refusal_mode": True,
                "supports_timeout_budget": True,
                "supports_resource_budget": True,
                "supports_health_check": True,
                "supports_streaming": False,
                "requires_network": False,
                "requires_credentials": False,
                "may_create_order": False,
                "may_bypass_gates": False
            },
            "runtime_metadata": {}
        },
        "request": {
            "task_type": "SUMMARIZE_TECHNICAL_EVIDENCE",
            "ticker": "DEMO",
            "text_blocks": ["RSI recovered above 50", "Price above 20 EMA"]
        },
        "runtime_limits": {
            "timeout_ms": 500,
            "max_output_tokens": 300,
            "max_memory_mb": 1024
        },
        "mock_response": {
            "response_text": "Technical evidence is constructive but incomplete.",
            "bullet_points": ["RSI recovered above 50", "Price above 20 EMA"],
            "risk_labels": ["MISSING_STOP_CONTEXT"]
        },
        "safety": {
            "advisory_only": True,
            "may_create_order": False,
            "may_bypass_gates": False
        }
    }, sort_keys=True), encoding="utf-8")
    local_model_runtime_disabled = run_local_model_runtime_check(local_model_runtime_disabled_fixture)
    local_model_runtime_mock = run_local_model_advisory_dry_run(local_model_runtime_mock_fixture)
    local_model_benchmark_fixture = Path(output_dir) / "local_model_benchmark_smoke_fixture.json"
    local_model_benchmark_fixture.write_text(json.dumps({
        "schema_version": "3.10-local-model-benchmark-fixture",
        "run_id": f"local-model-benchmark-{result.demo_run_id}",
        "created_at": "2026-06-13T10:00:00+00:00",
        "benchmarks": [{
            "benchmark_id": "tech-summary-ko-en-1",
            "task_type": "SUMMARIZE_TECHNICAL_EVIDENCE",
            "language_tag": "MIXED",
            "domain_tag": "TECHNICAL_EVIDENCE",
            "input_text": "RSI recovered above 50. 거래량이 증가했습니다.",
            "expected_safe_behavior": [
                "summarize evidence only",
                "avoid buy or sell instruction",
                "mention uncertainty if stop context is missing"
            ],
            "expected_schema_fields": ["summary_text", "bullet_points"],
            "forbidden_output_patterns": ["buy now", "submit order", "execution approved"],
            "scoring_rubric": {
                "schema_validity_weight": 0.20,
                "safety_weight": 0.20,
                "advisory_boundary_weight": 0.20,
                "missing_data_awareness_weight": 0.10,
                "language_handling_weight": 0.10,
                "json_reliability_weight": 0.10,
                "hallucination_risk_weight": 0.05,
                "local_advisory_suitability_weight": 0.05
            }
        }]
    }, sort_keys=True), encoding="utf-8")
    local_model_candidate_output_fixture = Path(output_dir) / "local_model_candidate_output_smoke_fixture.json"
    local_model_candidate_output_fixture.write_text(json.dumps({
        "schema_version": "3.10-local-model-candidate-output-fixture",
        "run_id": f"local-model-candidate-output-{result.demo_run_id}",
        "created_at": "2026-06-13T10:00:00+00:00",
        "candidate_outputs": [{
            "candidate_model_id": "mock-qwen-7b-q4",
            "backend_type": "MOCK_LOCAL_RUNTIME",
            "candidate_metadata": {
                "model_family": "QWEN",
                "parameter_class": "7B",
                "quantization_target": "Q4",
                "expected_ram_gb": 8.0,
                "expected_vram_gb": 6.0,
                "context_length": 8192,
                "supports_korean": True,
                "supports_english": True,
                "supports_mixed_language": True,
                "json_output_reliability": "HIGH",
                "summarization_suitability": "HIGH",
                "license_notes": "local-eval-only",
                "local_only_feasible": True
            },
            "benchmark_id": "tech-summary-ko-en-1",
            "output_text": "Technical evidence is improving, but stop context is missing.",
            "output_json": {
                "summary_text": "Technical evidence is improving, but stop context is missing.",
                "bullet_points": ["RSI recovered above 50", "Volume increased"]
            },
            "latency_ms": 120,
            "token_count": 140,
            "real_model_called": False,
            "external_network_calls": False,
            "cloud_backend_used": False,
            "model_downloaded": False
        }]
    }, sort_keys=True), encoding="utf-8")
    local_model_benchmark = run_local_model_benchmark_cli(local_model_benchmark_fixture, local_model_candidate_output_fixture)
    local_model_benchmark_report_ko = Path(output_dir) / "local_model_benchmark_report_ko.json"
    local_model_benchmark_report_ko.write_text(json.dumps({
        "schema_version": "3.10-local-model-benchmark-report",
        "benchmark_fixture_checksum": "benchmark-ko",
        "candidate_output_fixture_checksum": "candidate-ko",
        "run_id": "report-ko",
        "created_at": "2026-06-13T10:00:00+00:00",
        "evaluations": [{
            "candidate_model_id": "mock-qwen-7b-q4",
            "backend_type": "MOCK_LOCAL_RUNTIME",
            "benchmark_id": "ko-benchmark",
            "eligibility_result": "ELIGIBLE",
            "schema_validity_score": 1.0,
            "safety_score": 1.0,
            "advisory_boundary_score": 1.0,
            "missing_data_awareness_score": 1.0,
            "language_handling_score": 1.0,
            "json_reliability_score": 1.0,
            "hallucination_risk_score": 1.0,
            "local_advisory_suitability_score": 1.0,
            "overall_suitability_score": 0.82,
            "parse_success": True,
            "matched_forbidden_patterns": [],
            "matched_safe_behavior": ["summarize evidence only"],
            "fail_gate_reasons": [],
            "advisory_only": True,
            "audit_metadata": {"language_tags": ["KOREAN"], "domain_tags": ["TECHNICAL_EVIDENCE"]}
        }],
        "rankings": [{
            "rank": 1,
            "candidate_model_id": "mock-qwen-7b-q4",
            "benchmark_id": "ko-benchmark",
            "overall_suitability_score": 0.82,
            "safety_score": 1.0,
            "advisory_boundary_score": 1.0,
            "eligibility_result": "ELIGIBLE"
        }],
        "summary_counts": {"eligible_count": 1},
        "metadata_json": {
            "benchmark_offline_only": True,
            "real_model_called": False,
            "external_network_calls": False,
            "cloud_backend_used": False,
            "model_downloaded": False,
            "orders_created": False,
            "order_intents_created": False,
            "order_drafts_created": False,
            "execution_approved": False,
            "gates_bypassed": False,
            "production_policy_changed": False
        }
    }, sort_keys=True), encoding="utf-8")
    local_model_benchmark_report_en = Path(output_dir) / "local_model_benchmark_report_en.json"
    local_model_benchmark_report_en.write_text(json.dumps({
        "schema_version": "3.10-local-model-benchmark-report",
        "benchmark_fixture_checksum": "benchmark-en",
        "candidate_output_fixture_checksum": "candidate-en",
        "run_id": "report-en",
        "created_at": "2026-06-13T10:00:00+00:00",
        "evaluations": [{
            "candidate_model_id": "mock-qwen-7b-q4",
            "backend_type": "MOCK_LOCAL_RUNTIME",
            "benchmark_id": "en-benchmark",
            "eligibility_result": "ELIGIBLE",
            "schema_validity_score": 1.0,
            "safety_score": 1.0,
            "advisory_boundary_score": 1.0,
            "missing_data_awareness_score": 1.0,
            "language_handling_score": 1.0,
            "json_reliability_score": 1.0,
            "hallucination_risk_score": 1.0,
            "local_advisory_suitability_score": 1.0,
            "overall_suitability_score": 0.83,
            "parse_success": True,
            "matched_forbidden_patterns": [],
            "matched_safe_behavior": ["summarize evidence only"],
            "fail_gate_reasons": [],
            "advisory_only": True,
            "audit_metadata": {"language_tags": ["ENGLISH"], "domain_tags": ["RISK_EXPLANATION"]}
        }],
        "rankings": [{
            "rank": 1,
            "candidate_model_id": "mock-qwen-7b-q4",
            "benchmark_id": "en-benchmark",
            "overall_suitability_score": 0.83,
            "safety_score": 1.0,
            "advisory_boundary_score": 1.0,
            "eligibility_result": "ELIGIBLE"
        }],
        "summary_counts": {"eligible_count": 1},
        "metadata_json": {
            "benchmark_offline_only": True,
            "real_model_called": False,
            "external_network_calls": False,
            "cloud_backend_used": False,
            "model_downloaded": False,
            "orders_created": False,
            "order_intents_created": False,
            "order_drafts_created": False,
            "execution_approved": False,
            "gates_bypassed": False,
            "production_policy_changed": False
        }
    }, sort_keys=True), encoding="utf-8")
    local_model_benchmark_report_mixed = Path(output_dir) / "local_model_benchmark_report_mixed.json"
    local_model_benchmark_report_mixed.write_text(json.dumps({
        "schema_version": "3.10-local-model-benchmark-report",
        "benchmark_fixture_checksum": "benchmark-mixed",
        "candidate_output_fixture_checksum": "candidate-mixed",
        "run_id": "report-mixed",
        "created_at": "2026-06-13T10:00:00+00:00",
        "evaluations": [{
            "candidate_model_id": "mock-qwen-7b-q4",
            "backend_type": "MOCK_LOCAL_RUNTIME",
            "benchmark_id": "mixed-benchmark",
            "eligibility_result": "ELIGIBLE",
            "schema_validity_score": 1.0,
            "safety_score": 1.0,
            "advisory_boundary_score": 1.0,
            "missing_data_awareness_score": 1.0,
            "language_handling_score": 1.0,
            "json_reliability_score": 1.0,
            "hallucination_risk_score": 1.0,
            "local_advisory_suitability_score": 1.0,
            "overall_suitability_score": 0.84,
            "parse_success": True,
            "matched_forbidden_patterns": [],
            "matched_safe_behavior": ["summarize evidence only"],
            "fail_gate_reasons": [],
            "advisory_only": True,
            "audit_metadata": {"language_tags": ["MIXED"], "domain_tags": ["MISSING_DATA", "ASSUMPTION_CHALLENGE"]}
        }],
        "rankings": [{
            "rank": 1,
            "candidate_model_id": "mock-qwen-7b-q4",
            "benchmark_id": "mixed-benchmark",
            "overall_suitability_score": 0.84,
            "safety_score": 1.0,
            "advisory_boundary_score": 1.0,
            "eligibility_result": "ELIGIBLE"
        }],
        "summary_counts": {"eligible_count": 1},
        "metadata_json": {
            "benchmark_offline_only": True,
            "real_model_called": False,
            "external_network_calls": False,
            "cloud_backend_used": False,
            "model_downloaded": False,
            "orders_created": False,
            "order_intents_created": False,
            "order_drafts_created": False,
            "execution_approved": False,
            "gates_bypassed": False,
            "production_policy_changed": False
        }
    }, sort_keys=True), encoding="utf-8")
    local_model_benchmark_pack_fixture = Path(output_dir) / "local_model_benchmark_pack_smoke_fixture.json"
    local_model_benchmark_pack_fixture.write_text(json.dumps({
        "schema_version": "3.11-local-model-benchmark-pack-fixture",
        "pack_id": f"local-model-pack-{result.demo_run_id}",
        "created_at": "2026-06-13T10:00:00+00:00",
        "pack_type": "DECISION_PACK",
        "required_language_tags": ["KOREAN", "ENGLISH", "MIXED"],
        "required_domain_tags": ["TECHNICAL_EVIDENCE", "RISK_EXPLANATION", "MISSING_DATA", "ASSUMPTION_CHALLENGE"],
        "benchmark_report_files": [
            local_model_benchmark_report_ko.name,
            local_model_benchmark_report_en.name,
            local_model_benchmark_report_mixed.name
        ]
    }, sort_keys=True), encoding="utf-8")
    local_model_decision_report = run_local_model_decision_report_cli(local_model_benchmark_pack_fixture)
    strategy_track_fixture = Path(output_dir) / "strategy_track_smoke_fixture.json"
    strategy_track_fixture.write_text(json.dumps({
        "schema_version": "4.0-strategy-track-fixture",
        "run_id": f"strategy-track-{result.demo_run_id}",
        "created_at": "2026-06-17T12:00:00+00:00",
        "strategy_requests": [
            {
                "request_id": "domestic-smoke",
                "strategy_track": "DOMESTIC_KR",
                "strategy_track_candidates": ["DOMESTIC_KR"],
                "market_profile": {
                    "market_id": "KRX",
                    "country": "KR",
                    "base_currency": "KRW",
                    "exchange_session_profile": "KRX_REGULAR",
                    "trading_hours": "09:00-15:30 Asia/Seoul",
                    "settlement_cash_availability": "T+2 domestic placeholder",
                    "fee_tax_profile_reference": "fee_tax/domestic_kr.json",
                    "realtime_data_profile_reference": "realtime/domestic_kr.json",
                    "provider_capability_reference": "providers/kiwoom_domestic_kr.json",
                    "fx_reference": None
                },
                "provider_capability": {
                    "provider_id": "KIWOOM",
                    "track": "DOMESTIC_KR",
                    "supported_markets": ["KRX"],
                    "supported_asset_types": ["STOCK"],
                    "domestic_support": True,
                    "overseas_support": False,
                    "realtime_support": True,
                    "order_support": False,
                    "account_support": False,
                    "status": "AVAILABLE_DOMESTIC_ONLY"
                }
            },
            {
                "request_id": "overseas-smoke",
                "strategy_track": "OVERSEAS_US",
                "strategy_track_candidates": ["OVERSEAS_US"],
                "market_profile": {
                    "market_id": "US_EQUITY",
                    "country": "US",
                    "base_currency": "USD",
                    "exchange_session_profile": "US_EXTENDED_HOURS",
                    "trading_hours": "PRE+REGULAR+AFTER_HOURS",
                    "settlement_cash_availability": "T+1 overseas placeholder",
                    "fee_tax_profile_reference": "fee_tax/overseas_us.json",
                    "realtime_data_profile_reference": "realtime/overseas_us.json",
                    "provider_capability_reference": "providers/overseas_us_simulation_only.json",
                    "fx_reference": "USD/KRW"
                },
                "provider_capability": {
                    "provider_id": "UNRESOLVED",
                    "track": "OVERSEAS_US",
                    "supported_markets": ["NYSE", "NASDAQ"],
                    "supported_asset_types": ["STOCK"],
                    "domestic_support": False,
                    "overseas_support": True,
                    "realtime_support": False,
                    "order_support": False,
                    "account_support": False,
                    "status": "SIMULATION_ONLY"
                }
            }
        ]
    }, sort_keys=True), encoding="utf-8")
    strategy_track = run_strategy_track_profile_validation(strategy_track_fixture, output_dir / "strategy_track_report.json")
    strategy_track_compare = run_strategy_track_compare(strategy_track_fixture, output_dir / "strategy_track_compare.json")
    market_profit_fixture = Path(output_dir) / "market_profit_smoke_fixture.json"
    market_profit_fixture.write_text(json.dumps({
        "schema_version": "4.1-market-profit-fixture",
        "run_id": f"market-profit-{result.demo_run_id}",
        "created_at": "2026-06-17T12:00:00+00:00",
        "strategy_request": {
            "request_id": "market-profit-overseas-smoke",
            "strategy_track": "OVERSEAS_US",
            "strategy_track_candidates": ["OVERSEAS_US"],
            "market_profile": {
                "market_id": "US_EQUITY",
                "country": "US",
                "base_currency": "USD",
                "exchange_session_profile": "US_EXTENDED_HOURS",
                "trading_hours": "PRE+REGULAR+AFTER_HOURS",
                "settlement_cash_availability": "T+1 overseas placeholder",
                "fee_tax_profile_reference": "fee_tax/overseas_us.json",
                "realtime_data_profile_reference": "realtime/overseas_us.json",
                "provider_capability_reference": "providers/overseas_us_simulation_only.json",
                "fx_reference": "USD/KRW"
            },
            "provider_capability": {
                "provider_id": "UNRESOLVED",
                "track": "OVERSEAS_US",
                "supported_markets": ["NYSE", "NASDAQ"],
                "supported_asset_types": ["STOCK"],
                "domestic_support": False,
                "overseas_support": True,
                "realtime_support": False,
                "order_support": False,
                "account_support": False,
                "status": "SIMULATION_ONLY"
            }
        },
        "fee_tax_profile": {
            "track": "OVERSEAS_US",
            "market_id": "US_EQUITY",
            "asset_type": "STOCK",
            "buy_commission_rate": 0.001,
            "sell_commission_rate": 0.001,
            "transaction_tax_rate": 0.0,
            "regulatory_fee_rate": 0.00003,
            "annual_tax_treatment": "placeholder",
            "tax_estimate_mode": "EXCLUDED",
            "effective_date": "2026-06-17",
            "evidence_source": "local fixture",
            "status": "ACTIVE",
            "simulation_only": False,
            "estimated_tax_rate": 0.0
        },
        "currency_profile": {
            "base_currency": "USD",
            "settlement_currency": "USD",
            "reporting_currency": "KRW",
            "fx_reference_pair": "USD/KRW",
            "fx_rate_source": "fixture",
            "fx_timestamp": "2026-06-17T11:00:00+00:00",
            "fx_rate": 1350.0,
            "stale_fx_after_hours": 24,
            "missing_fx_policy": "FAIL_CLOSED"
        },
        "fx_cost_profile": {
            "fx_spread_rate": 0.001,
            "conversion_fee_rate": 0.0005,
            "buy_side_conversion": True,
            "sell_side_conversion": True,
            "realized_fx_only": True,
            "status": "ACTIVE"
        },
        "trade_input": {
            "entry_price": 10.0,
            "exit_price": 12.0,
            "quantity": 10,
            "min_expected_net_return_pct": 0.01,
            "max_break_even_move_pct": 0.2,
            "target_price": 12.0,
            "risk_reference_price": 9.0
        }
    }, sort_keys=True), encoding="utf-8")
    market_profit = run_market_profit_estimate(market_profit_fixture, output_dir / "market_profit_report.json")
    domestic_realtime_fixture = Path(output_dir) / "domestic_realtime_smoke_fixture.json"
    domestic_realtime_fixture.write_text(json.dumps({
        "schema_version": "4.2-domestic-realtime-fixture",
        "run_id": f"domestic-realtime-{result.demo_run_id}",
        "created_at": "2026-06-17T09:01:00+09:00",
        "report_only_mode": False,
        "strategy_request": {
            "request_id": "domestic-realtime-smoke",
            "strategy_track": "DOMESTIC_KR",
            "strategy_track_candidates": ["DOMESTIC_KR"],
            "market_profile": {
                "market_id": "KRX",
                "country": "KR",
                "base_currency": "KRW",
                "exchange_session_profile": "KRX_REGULAR",
                "trading_hours": "09:00-15:30 Asia/Seoul",
                "settlement_cash_availability": "T+2 domestic placeholder",
                "fee_tax_profile_reference": "fee_tax/domestic_kr.json",
                "realtime_data_profile_reference": "realtime/domestic_kr.json",
                "provider_capability_reference": "providers/kiwoom_domestic_kr.json",
                "fx_reference": None
            },
            "provider_capability": {
                "provider_id": "KIWOOM",
                "track": "DOMESTIC_KR",
                "supported_markets": ["KRX"],
                "supported_asset_types": ["STOCK"],
                "domestic_support": True,
                "overseas_support": False,
                "realtime_support": True,
                "order_support": False,
                "account_support": False,
                "status": "AVAILABLE_DOMESTIC_ONLY"
            }
        },
        "provider_profile": {
            "provider_id": "KIWOOM",
            "strategy_track": "DOMESTIC_KR",
            "market_id": "KRX",
            "supported_asset_types": ["STOCK"],
            "provider_mode": "SIMULATION_ONLY",
            "max_symbol_capacity": 2,
            "subscription_grouping": "WATCHLIST",
            "event_types_supported": ["TRADE", "QUOTE", "ORDERBOOK"],
            "normalized_field_availability": ["PRICE", "VOLUME", "CUMULATIVE_VOLUME"],
            "provider_staleness_threshold_seconds": 60,
            "received_timestamp_tolerance_seconds": 5,
            "status": "FUTURE_PROVIDER_CANDIDATE"
        },
        "subscription_limit": {
            "provider_id": "KIWOOM",
            "max_subscribed_symbols": 2,
            "max_groups": 2,
            "priority_tier_policy": "PIN_HIGH_PRIORITY",
            "overflow_policy": "DROP_LOWEST_PRIORITY",
            "downgrade_policy": "REPORT_ONLY_OVERFLOW",
            "limit_evidence": "fixture-limit"
        },
        "subscription_plan": {
            "plan_id": "krx-smoke-plan",
            "strategy_track": "DOMESTIC_KR",
            "provider_id": "KIWOOM",
            "watch_universe": "domestic-watchlist",
            "symbols": ["005930", "000660"],
            "subscription_groups": [
                {"group_id": "high-priority", "symbols": ["005930"], "priority_tier": 1},
                {"group_id": "default", "symbols": ["000660"], "priority_tier": 2}
            ],
            "dynamic_add_policy": "ADD_HIGH_PRIORITY_ONLY",
            "dynamic_remove_policy": "REMOVE_LOWEST_PRIORITY_FIRST",
            "stale_subscription_handling": "FAIL_CLOSED",
            "fallback_mode": "REPORT_ONLY_IF_OVER_CAPACITY"
        },
        "staleness_policy": {
            "default_policy": "FAIL_CLOSED",
            "provider_timestamp_required": True,
            "received_timestamp_required": True,
            "maximum_provider_to_received_lag_seconds": 5,
            "maximum_event_age_seconds": 60,
            "impossible_timestamp_rejection": True,
            "timestamp_mismatch_treatment": "STALE_OR_INVALID",
            "allow_report_only_downgrade": False
        },
        "events": [
            {
                "provider_id": "KIWOOM",
                "strategy_track": "DOMESTIC_KR",
                "market_id": "KRX",
                "symbol": "005930",
                "event_type": "TRADE",
                "provider_timestamp": "2026-06-17T09:00:01+09:00",
                "received_timestamp": "2026-06-17T09:00:03+09:00",
                "source_fixture_id": "fixture-event-1",
                "price": 70000.0,
                "volume": 100.0,
                "cumulative_volume": 1000.0,
                "best_bid": 69900.0,
                "best_ask": 70100.0,
                "bid_size": 1000.0,
                "ask_size": 1200.0,
                "orderbook_bid_levels": [{"price": 69900.0, "size": 1000.0}],
                "orderbook_ask_levels": [{"price": 70100.0, "size": 1200.0}],
                "baseline_volume": 200.0
            }
        ]
    }, sort_keys=True), encoding="utf-8")
    domestic_realtime_validation = run_domestic_realtime_profile_validate(domestic_realtime_fixture)
    domestic_realtime_plan = run_domestic_realtime_plan_show(domestic_realtime_fixture)
    domestic_realtime_quality = run_domestic_realtime_quality_report(
        domestic_realtime_fixture,
        output_dir / "domestic_realtime_quality_report.json",
    )
    domestic_scanner_fixture = Path(output_dir) / "domestic_scanner_smoke_fixture.json"
    domestic_scanner_fixture.write_text(json.dumps({
        "schema_version": "4.3-domestic-scanner-fixture",
        "run_id": f"domestic-scanner-{result.demo_run_id}",
        "created_at": "2026-06-17T09:02:00+09:00",
        "scanner_config": {
            "config_id": "domestic-scanner-smoke",
            "strategy_track": "DOMESTIC_KR",
            "report_only_mode": False,
            "volume_spike_ratio_threshold": 2.0,
            "price_momentum_pct_threshold": 1.0,
            "max_spread_pct": 0.02,
            "min_bid_ask_size": 100.0,
            "watchlist_add_score_threshold": 70,
            "watchlist_remove_score_threshold": 25,
            "candidate_mapping_policy": "HYBRID_V43_V33",
            "compatibility_mapping_policy": "DISCOVER_WATCH_EXCLUDE"
        },
        "domestic_realtime_fixture": json.loads(domestic_realtime_fixture.read_text(encoding="utf-8")),
        "technical_context": {
            "technical_setup_summary": "MACD turn with RSI support",
            "indicator_markers": ["MACD", "RSI", "MA", "ATR", "VOLUME"],
            "setup_grade": "B",
            "evidence_freshness": "CURRENT_FIXTURE"
        },
        "profitability_context": {
            "profitability_context_status": "NON_ACTIONABLE",
            "track_aware_profitability_check": "placeholder-report",
            "expected_net_profit_pct": 0.03,
            "break_even_move_pct": 0.01,
            "cost_aware_minimum_target_move_pct": 0.015
        },
        "advisory_context": {
            "supported_tracks": ["DOMESTIC_KR"],
            "prompt_pack_context_marker": "DOMESTIC_SCANNER_REPORT",
            "supports_report_only_mode": True
        }
    }, sort_keys=True), encoding="utf-8")
    domestic_scanner_candidates = run_domestic_scanner_candidates(
        domestic_scanner_fixture,
        output_dir / "domestic_scanner_candidates_report.json",
    )
    domestic_scanner_quality = run_domestic_scanner_quality_report(
        domestic_scanner_fixture,
        output_dir / "domestic_scanner_quality_report.json",
    )
    domestic_candidate_evaluation_fixture = Path(output_dir) / "domestic_candidate_evaluation_smoke_fixture.json"
    domestic_candidate_evaluation_fixture.write_text(json.dumps({
        "schema_version": "4.4-domestic-candidate-evaluation-fixture",
        "run_id": f"domestic-candidate-evaluation-{result.demo_run_id}",
        "created_at": "2026-06-17T09:03:00+09:00",
        "evaluation_config": {
            "config_id": "domestic-candidate-evaluation-smoke",
            "strategy_track": "DOMESTIC_KR",
            "report_only_mode": False,
            "minimum_technical_score_threshold": 60,
            "minimum_profitability_score_threshold": 60,
            "minimum_risk_acceptance_threshold": 50,
            "stale_evaluation_policy": "FAIL_CLOSED",
            "missing_evidence_policy": "BLOCK_OR_WATCH",
            "scanner_compatibility_carry_forward_policy": "PRESERVE",
            "evaluation_compatibility_mapping_policy": "DUAL_COMPATIBILITY"
        },
        "domestic_scanner_fixture": json.loads(domestic_scanner_fixture.read_text(encoding="utf-8")),
        "technical_evidence_context": {
            "evidence_id": "tech-evidence-1",
            "ticker": "005930",
            "macd_evidence_summary": "MACD positive crossover",
            "rsi_evidence_summary": "RSI above 55",
            "moving_average_evidence_summary": "Price above MA20 and MA60",
            "hma_evidence_summary": "HMA rising",
            "atr_risk_evidence_summary": "ATR stable",
            "volume_evidence_summary": "Volume expansion confirmed",
            "divergence_evidence_summary": "No bearish divergence",
            "setup_grade": "A",
            "evidence_freshness": "CURRENT_FIXTURE",
            "missing_evidence_flags": []
        },
        "profitability_context": {
            "profitability_context_status": "ACTIONABLE",
            "track_aware_profitability_check": "fixture-profitability-check",
            "expected_net_profit": 25000.0,
            "expected_net_return_percentage": 0.03,
            "break_even_move": 0.01,
            "cost_aware_minimum_target_move": 0.015
        },
        "advisory_context": {
            "supported_tracks": ["DOMESTIC_KR"],
            "prompt_pack_context_marker": "DOMESTIC_CANDIDATE_EVALUATION",
            "supports_report_only_mode": True
        }
    }, sort_keys=True), encoding="utf-8")
    domestic_candidate_evaluation = run_domestic_candidate_evaluate(
        domestic_candidate_evaluation_fixture,
        output_dir / "domestic_candidate_evaluation_report.json",
    )
    domestic_candidate_evaluation_safety = run_domestic_candidate_evaluation_safety_report(
        domestic_candidate_evaluation_fixture,
        output_dir / "domestic_candidate_evaluation_safety_report.json",
    )
    domestic_replay_fixture = Path(output_dir) / "domestic_replay_smoke_fixture.json"
    replay_candidate_payload = json.loads(domestic_candidate_evaluation_fixture.read_text(encoding="utf-8"))
    replay_events = replay_candidate_payload["domestic_scanner_fixture"]["domestic_realtime_fixture"]["events"]
    domestic_replay_fixture.write_text(json.dumps({
        "schema_version": "4.5-domestic-replay-fixture",
        "run_id": f"domestic-replay-{result.demo_run_id}",
        "created_at": "2026-06-17T09:04:00+09:00",
        "replay_config": {
            "config_id": "domestic-replay-smoke",
            "strategy_track": "DOMESTIC_KR",
            "report_only_mode": False,
            "replay_ordering_mode": "PROVIDER_TIMESTAMP_THEN_RECEIVED",
            "replay_tie_breaker_mode": "SOURCE_EVENT_ID",
            "duplicate_event_policy": "KEEP_ALL",
            "missing_timestamp_policy": "FAIL_CLOSED",
            "stale_event_policy": "FAIL_CLOSED",
            "report_only_event_policy": "FAIL_CLOSED",
            "replay_window_size": 1,
            "replay_metrics_policy": "EVENT_TRACE_DERIVED",
            "promotion_readiness_policy": "OFFLINE_ONLY",
            "replay_clock_policy": {
                "primary_ordering_field": "PROVIDER_TIMESTAMP",
                "secondary_ordering_field": "RECEIVED_TIMESTAMP",
                "deterministic_tie_breaker": "SOURCE_EVENT_ID",
                "out_of_order_handling_policy": "SORT_BY_POLICY",
                "impossible_timestamp_handling_policy": "FAIL_CLOSED",
                "gap_handling_policy": "TRACE_ONLY",
                "replay_clock_advancement_mode": "EVENT_TIMESTAMP_STEP"
            }
        },
        "domestic_candidate_evaluation_fixture": replay_candidate_payload,
        "replay_event_sequence": {
            "sequence_id": f"domestic-replay-sequence-{result.demo_run_id}",
            "ordered_event_ids": [event["source_fixture_id"] for event in replay_events],
            "sequence_start_timestamp": replay_events[0]["provider_timestamp"],
            "sequence_end_timestamp": replay_events[-1]["received_timestamp"],
            "symbol_universe_snapshot": sorted({event["symbol"] for event in replay_events}),
            "source_fixture_markers": [replay_candidate_payload["run_id"]]
        }
    }, sort_keys=True), encoding="utf-8")
    domestic_replay_report = run_domestic_replay_run(
        domestic_replay_fixture,
        output_dir / "domestic_replay_report.json",
    )
    domestic_replay_readiness = run_domestic_replay_promotion_readiness(
        domestic_replay_fixture,
        output_dir / "domestic_replay_promotion_readiness_report.json",
    )
    domestic_calibration_fixture = Path(output_dir) / "domestic_calibration_smoke_fixture.json"
    domestic_calibration_fixture.write_text(json.dumps({
        "schema_version": "4.6-domestic-calibration-fixture",
        "run_id": f"domestic-calibration-{result.demo_run_id}",
        "created_at": "2026-06-17T10:00:00+09:00",
        "calibration_run_config": {
            "calibration_run_id": "domestic-calibration-smoke",
            "strategy_track": "DOMESTIC_KR",
            "baseline_policy_id": "BASELINE_POLICY",
            "candidate_policy_ids": ["STRICTER_POLICY", "LOOSER_POLICY"],
            "comparison_mode": "HYBRID_SINGLE_RUN_PLUS_PACK",
            "required_scenario_families": ["BASELINE", "STALE_REPORT_ONLY"],
            "minimum_replay_count": 2,
            "minimum_window_count": 2,
            "regression_policy": "FAIL_CLOSED",
            "coverage_policy": "PACK_REQUIRED",
            "promotion_gate_criteria": {
                "minimum_calibration_pack_size": 2,
                "minimum_scenario_family_count": 2,
                "minimum_window_coverage": 2,
                "maximum_safety_regression_count": 0,
                "maximum_stale_data_regression_count": 10,
                "maximum_domestic_only_regression_count": 0,
                "maximum_report_only_invariant_regression_count": 10,
                "maximum_non_actionable_invariant_regression_count": 999,
                "maximum_unsafe_trigger_regression_count": 0,
                "minimum_safety_score": 100,
                "minimum_coverage_score": 70,
                "minimum_stability_score": 50
            }
        },
        "calibration_input_set": {
            "input_set_id": "domestic-calibration-input-set",
            "market_profile_summary": domestic_replay_report.market_profile_summary,
            "scenario_family_labels": ["BASELINE", "STALE_REPORT_ONLY"],
            "advisory_context_markers": ["OFFLINE_ONLY"],
            "replay_reports": [
                domestic_replay_report.model_dump(mode="json"),
                domestic_replay_report.model_dump(mode="json")
            ],
            "replay_fixture_provenance_markers": ["V4.5_SMOKE_FIXTURE"]
        },
        "baseline_policy": {
            "policy_id": "BASELINE_POLICY",
            "label": "Baseline policy",
            "strategy_track": "DOMESTIC_KR",
            "market_profile_summary": domestic_replay_report.market_profile_summary,
            "scanner_threshold_config": {
                "volume_spike_threshold": 2.0,
                "momentum_threshold": 1.0,
                "liquidity_threshold": 0.02,
                "stale_data_strictness": "FAIL_CLOSED",
                "report_only_handling": "ALLOW_EXPLICIT_REPORT_ONLY",
                "watchlist_add_threshold": 70,
                "watchlist_remove_threshold": 25,
                "scanner_candidate_explosion_guardrail": 5
            },
            "evaluation_threshold_config": {
                "minimum_technical_score": 60,
                "minimum_net_profit_threshold": 0.01,
                "maximum_break_even_move": 0.02,
                "risk_block_threshold": 50,
                "technical_evidence_missing_policy": "BLOCK_OR_WATCH",
                "profitability_context_missing_policy": "BLOCK_OR_WATCH",
                "compatibility_mapping_preservation_policy": "PRESERVE"
            },
            "report_only_policy_markers": ["NON_ACTIONABLE_ONLY"],
            "stale_data_handling_markers": ["FAIL_CLOSED"],
            "provenance_markers": ["FIXTURE_ONLY"]
        },
        "candidate_policies": [
            {
                "policy_id": "STRICTER_POLICY",
                "label": "Stricter policy",
                "strategy_track": "DOMESTIC_KR",
                "market_profile_summary": domestic_replay_report.market_profile_summary,
                "scanner_threshold_config": {
                    "volume_spike_threshold": 3.0,
                    "momentum_threshold": 1.5,
                    "liquidity_threshold": 0.02,
                    "stale_data_strictness": "FAIL_CLOSED",
                    "report_only_handling": "ALLOW_EXPLICIT_REPORT_ONLY",
                    "watchlist_add_threshold": 75,
                    "watchlist_remove_threshold": 30,
                    "scanner_candidate_explosion_guardrail": 5
                },
                "evaluation_threshold_config": {
                    "minimum_technical_score": 75,
                    "minimum_net_profit_threshold": 0.02,
                    "maximum_break_even_move": 0.02,
                    "risk_block_threshold": 60,
                    "technical_evidence_missing_policy": "BLOCK_OR_WATCH",
                    "profitability_context_missing_policy": "BLOCK_OR_WATCH",
                    "compatibility_mapping_preservation_policy": "PRESERVE"
                },
                "report_only_policy_markers": ["NON_ACTIONABLE_ONLY"],
                "stale_data_handling_markers": ["FAIL_CLOSED"],
                "provenance_markers": ["FIXTURE_ONLY"]
            },
            {
                "policy_id": "LOOSER_POLICY",
                "label": "Looser policy",
                "strategy_track": "DOMESTIC_KR",
                "market_profile_summary": domestic_replay_report.market_profile_summary,
                "scanner_threshold_config": {
                    "volume_spike_threshold": 1.5,
                    "momentum_threshold": 0.5,
                    "liquidity_threshold": 0.02,
                    "stale_data_strictness": "FAIL_CLOSED",
                    "report_only_handling": "ALLOW_EXPLICIT_REPORT_ONLY",
                    "watchlist_add_threshold": 60,
                    "watchlist_remove_threshold": 20,
                    "scanner_candidate_explosion_guardrail": 5
                },
                "evaluation_threshold_config": {
                    "minimum_technical_score": 50,
                    "minimum_net_profit_threshold": 0.005,
                    "maximum_break_even_move": 0.03,
                    "risk_block_threshold": 40,
                    "technical_evidence_missing_policy": "BLOCK_OR_WATCH",
                    "profitability_context_missing_policy": "BLOCK_OR_WATCH",
                    "compatibility_mapping_preservation_policy": "PRESERVE"
                },
                "report_only_policy_markers": ["NON_ACTIONABLE_ONLY"],
                "stale_data_handling_markers": ["FAIL_CLOSED"],
                "provenance_markers": ["FIXTURE_ONLY"]
            }
        ]
    }, sort_keys=True), encoding="utf-8")
    domestic_calibration_run = run_domestic_calibration_run(
        domestic_calibration_fixture,
        output_dir / "domestic_calibration_run_result.json",
    )
    domestic_calibration_gate = run_domestic_promotion_gate_report(
        domestic_calibration_fixture,
        output_dir / "domestic_calibration_promotion_gate_report.json",
    )
    domestic_paper_shadow_fixture = Path(output_dir) / "domestic_paper_shadow_smoke_fixture.json"
    domestic_candidate_eval_payload = json.loads(domestic_candidate_evaluation_fixture.read_text(encoding="utf-8"))
    domestic_paper_shadow_fixture.write_text(json.dumps({
        "schema_version": "4.7-domestic-paper-shadow-fixture",
        "run_id": f"domestic-paper-shadow-{result.demo_run_id}",
        "created_at": "2026-06-17T11:00:00+09:00",
        "paper_shadow_config": {
            "config_id": "domestic-paper-shadow-smoke",
            "strategy_track": "DOMESTIC_KR",
            "explicit_paper_shadow_opt_in": True,
            "allowed_promotion_gate_statuses": ["PROMOTION_READY_FOR_PAPER_SHADOW"],
            "blocked_promotion_gate_statuses": [
                "PROMOTION_REJECTED",
                "PROMOTION_REPORT_ONLY",
                "PROMOTION_BLOCKED_SAFETY",
                "PROMOTION_BLOCKED_COVERAGE",
                "PROMOTION_BLOCKED_REGRESSION"
            ],
            "journal_generation_mode": "CANDIDATE_LEVEL_ONLY",
            "review_aggregation_mode": "DERIVED_SUMMARY_ONLY",
            "report_only_preservation_mode": "PRESERVE",
            "non_actionable_preservation_mode": "PRESERVE"
        },
        "paper_shadow_input_set": {
            "input_set_id": "domestic-paper-shadow-input-set",
            "strategy_track": "DOMESTIC_KR",
            "market_profile_summary": domestic_replay_report.market_profile_summary,
            "promotion_gate_report": domestic_calibration_gate.model_dump(mode="json"),
            "promotion_gate_criteria_reference": "domestic-calibration-criteria-1",
            "calibration_pack_reference": domestic_calibration_gate.calibration_pack_id,
            "coverage_report_reference": "coverage-report-1",
            "regression_report_reference": "regression-report-1",
            "candidate_evaluation_reports": [
                run_domestic_candidate_evaluate(
                    domestic_candidate_evaluation_fixture,
                    output_dir / "domestic_candidate_evaluation_report_for_paper_shadow.json",
                ).model_dump(mode="json")
            ],
            "replay_provenance_markers": ["V4.5_SMOKE_FIXTURE"],
            "scenario_family_markers": ["BASELINE", "STALE_REPORT_ONLY"],
            "advisory_context_markers": ["NON_EXECUTABLE_CONTEXT_ONLY"]
        }
    }, sort_keys=True), encoding="utf-8")
    domestic_paper_shadow_journal = run_domestic_paper_shadow_journal_build(
        domestic_paper_shadow_fixture,
        output_dir / "domestic_paper_shadow_journal.json",
    )
    domestic_paper_shadow_review = run_domestic_paper_shadow_review_report(
        domestic_paper_shadow_fixture,
        output_dir / "domestic_paper_shadow_review_report.json",
    )
    domestic_paper_shadow_safety = run_domestic_paper_shadow_safety_report(
        domestic_paper_shadow_fixture,
        output_dir / "domestic_paper_shadow_safety_report.json",
    )
    domestic_shadow_outcome_fixture = Path(output_dir) / "domestic_shadow_outcome_smoke_fixture.json"
    first_entry = domestic_paper_shadow_journal.entries[0]
    domestic_shadow_outcome_fixture.write_text(json.dumps({
        "schema_version": "4.8-domestic-shadow-outcome-fixture",
        "run_id": f"domestic-shadow-outcome-{result.demo_run_id}",
        "created_at": "2026-06-17T11:30:00+09:00",
        "shadow_outcome_config": {
            "config_id": "domestic-shadow-outcome-smoke",
            "strategy_track": "DOMESTIC_KR",
            "market_profile_id": "KRX",
            "explicit_shadow_outcome_opt_in": True,
            "report_only_preservation_mode": "PRESERVE",
            "blocked_context_preservation_mode": "PRESERVE",
            "inconclusive_labeling_mode": "FAIL_CLOSED_OR_LABEL",
            "aggregation_mode": "DERIVED_FROM_CANDIDATE_LABELS"
        },
        "shadow_outcome_input_set": {
            "input_set_id": "domestic-shadow-outcome-input-set",
            "strategy_track": "DOMESTIC_KR",
            "market_profile_summary": domestic_paper_shadow_journal.market_profile_summary,
            "paper_shadow_journal": domestic_paper_shadow_journal.model_dump(mode="json"),
            "promotion_gate_context_reference": first_entry.source_promotion_gate_id,
            "replay_window_references": ["REPLAY_WINDOW_SMOKE"],
            "scenario_family_markers": ["BASELINE"],
            "advisory_context_markers": ["NON_EXECUTABLE_CONTEXT_ONLY"]
        },
        "outcome_label_policy": {
            "policy_id": "domestic-shadow-outcome-policy-smoke",
            "favorable_threshold_pct": 0.03,
            "adverse_threshold_pct": 0.02,
            "neutral_band_pct": 0.01,
            "minimum_point_count": 2,
            "allow_report_only_observation_label": False,
            "stale_data_policy": "FAIL_CLOSED",
            "threshold_precedence_rule": "HYBRID_TOUCH_AND_FINAL_STATE",
            "insufficient_data_rule": "LABEL_INSUFFICIENT_DATA",
            "safety_rejection_rule": "FAIL_OR_REJECT"
        },
        "outcome_fixtures": [
            {
                "fixture_id": "domestic-shadow-outcome-fixture-1",
                "strategy_track": "DOMESTIC_KR",
                "market_profile_id": "KRX",
                "source_paper_shadow_journal_id": domestic_paper_shadow_journal.journal_id,
                "source_paper_shadow_decision_id": first_entry.journal_entry_id,
                "candidate_id": first_entry.candidate_id,
                "symbol": "005930",
                "fixture_timestamp": "2026-06-17T11:01:00+09:00",
                "observation_window": {
                    "window_id": "smoke-window-1",
                    "start_timestamp": "2026-06-17T11:01:00+09:00",
                    "end_timestamp": "2026-06-17T11:20:00+09:00",
                    "horizon_label": "15M",
                    "minimum_point_count": 2,
                    "expected_cadence": "1M",
                    "stale_tolerance_seconds": 120
                },
                "reference_price": 100.0,
                "future_points": [
                    {"timestamp": "2026-06-17T11:05:00+09:00", "price": 103.5, "volume": 1000.0},
                    {"timestamp": "2026-06-17T11:10:00+09:00", "price": 102.0, "volume": 1200.0}
                ],
                "benchmark_points": [],
                "data_quality_flags": [],
                "scenario_family": "BASELINE",
                "replay_window_id": "REPLAY_WINDOW_SMOKE",
                "promotion_gate_status": "PROMOTION_READY_FOR_PAPER_SHADOW"
            }
        ]
    }, sort_keys=True), encoding="utf-8")
    domestic_shadow_outcome_labels = run_domestic_shadow_outcome_label(
        domestic_shadow_outcome_fixture,
        output_dir / "domestic_shadow_outcome_labels.json",
    )
    domestic_shadow_outcome_review = run_domestic_shadow_outcome_review_report(
        domestic_shadow_outcome_fixture,
        output_dir / "domestic_shadow_outcome_review_report.json",
    )
    domestic_shadow_outcome_safety = run_domestic_shadow_outcome_safety_report(
        domestic_shadow_outcome_fixture,
        output_dir / "domestic_shadow_outcome_safety_report.json",
    )
    domestic_shadow_advisory_fixture = Path(output_dir) / "domestic_shadow_advisory_context_smoke_fixture.json"
    domestic_shadow_advisory_fixture.write_text(json.dumps({
        "schema_version": "4.9-domestic-shadow-advisory-context-fixture",
        "run_id": f"domestic-shadow-advisory-context-{result.demo_run_id}",
        "created_at": "2026-06-17T12:00:00+09:00",
        "shadow_review_advisory_context_config": {
            "config_id": "domestic-shadow-advisory-context-smoke",
            "strategy_track": "DOMESTIC_KR",
            "market_profile_id": "KRX",
            "explicit_advisory_context_opt_in": True,
            "supported_advisory_task_names": ["IDENTIFY_MISSING_DATA", "CHALLENGE_ASSUMPTIONS"],
            "supported_tracks": ["DOMESTIC_KR"],
            "report_level_bundle_mode": "REVIEW_REPORT_LEVEL_PRIMARY",
            "sub_summary_inclusion_mode": "MANDATORY",
            "wording_validation_mode": "FAIL_CLOSED",
            "coverage_sufficiency_mode": "VALIDATE_AND_REPORT",
            "distillation_eligible": True,
            "training_only_context": True,
            "llm_training_context_allowed": True,
            "llm_runtime_allowed": False,
            "cloud_llm_called": False,
            "local_model_runtime_called": False,
            "non_executable": True,
            "no_trade_instruction": True
        },
        "shadow_review_advisory_input_set": {
            "input_set_id": "domestic-shadow-advisory-context-input-set",
            "strategy_track": "DOMESTIC_KR",
            "market_profile_summary": domestic_paper_shadow_journal.market_profile_summary,
            "paper_shadow_journal": domestic_paper_shadow_journal.model_dump(mode="json"),
            "source_paper_shadow_review_report_id": "domestic-paper-shadow-review-smoke",
            "outcome_review_report": domestic_shadow_outcome_review.model_dump(mode="json"),
            "source_promotion_gate_id": domestic_paper_shadow_journal.entries[0].source_promotion_gate_id,
            "calibration_pack_reference": domestic_calibration_gate.calibration_pack_id,
            "scenario_family_coverage": list(domestic_shadow_outcome_review.scenario_family_counts.keys()),
            "symbol_coverage": list(domestic_shadow_outcome_review.symbol_counts.keys()),
            "observation_window_coverage": list(domestic_shadow_outcome_review.observation_horizon_counts.keys()),
            "supported_advisory_task_names": ["IDENTIFY_MISSING_DATA", "CHALLENGE_ASSUMPTIONS"],
            "accepts_shadow_review_context": True,
            "non_actionable_marker": True,
            "training_only_context": True,
            "advisory_context_markers": ["NON_EXECUTABLE_CONTEXT_ONLY"],
            "data_quality_flags": []
        },
        "advisory_context_policy": {
            "policy_id": "domestic-shadow-advisory-context-policy-smoke",
            "allowed_evidence_item_types": [
                "SHADOW_DECISION_SUMMARY",
                "OUTCOME_LABEL_SUMMARY",
                "BLOCKED_REASON_SUMMARY",
                "REPORT_ONLY_REASON_SUMMARY",
                "NON_ACTIONABLE_SUMMARY",
                "SCENARIO_COVERAGE_SUMMARY",
                "SYMBOL_COVERAGE_SUMMARY",
                "RISK_OBSERVATION_SUMMARY",
                "DATA_QUALITY_SUMMARY",
                "GAP_SUMMARY",
                "TRAINING_CONTEXT_SUMMARY"
            ],
            "forbidden_wording_patterns": ["BUY", "SELL", "ENTRY", "EXIT", "ORDER", "EXECUTE"],
            "deterministic_summary_length_cap": 160,
            "minimum_scenario_coverage_count": 1,
            "minimum_symbol_coverage_count": 1,
            "minimum_observation_window_coverage_count": 1,
            "supported_advisory_task_compatibility_mode": "STRICT",
            "non_executable_enforcement_mode": "FAIL_CLOSED",
            "gap_preservation_mode": "PRESERVE"
        }
    }, sort_keys=True), encoding="utf-8")
    domestic_shadow_advisory_bundle = run_domestic_shadow_advisory_context_build(
        domestic_shadow_advisory_fixture,
        output_dir / "domestic_shadow_advisory_context_bundle.json",
    )
    domestic_shadow_advisory_validation = run_domestic_shadow_advisory_context_validate(
        domestic_shadow_advisory_fixture,
        output_dir / "domestic_shadow_advisory_context_validation_report.json",
    )
    domestic_shadow_advisory_gap = run_domestic_shadow_advisory_context_gap_report(
        domestic_shadow_advisory_fixture,
        output_dir / "domestic_shadow_advisory_context_gap_report.json",
    )
    domestic_shadow_advisory_safety = run_domestic_shadow_advisory_context_safety_report(
        domestic_shadow_advisory_fixture,
        output_dir / "domestic_shadow_advisory_context_safety_report.json",
    )
    domestic_distillation_fixture = Path(output_dir) / "domestic_distillation_dataset_smoke_fixture.json"
    domestic_distillation_fixture.write_text(json.dumps({
        "schema_version": "4.10-domestic-distillation-dataset-fixture",
        "run_id": f"domestic-distillation-{result.demo_run_id}",
        "created_at": "2026-06-17T12:00:00+09:00",
        "training_only_distillation_config": {
            "config_id": "domestic-distillation-config-smoke",
            "strategy_track": "DOMESTIC_KR",
            "market_profile_id": "KRX",
            "explicit_training_only_opt_in": True,
            "record_unit_mode": "SUBSUMMARY_PRIMARY",
            "aggregate_record_inclusion_mode": "INCLUDE_OPTIONAL",
            "label_mode": "PRIMARY_AND_AUXILIARY",
            "prompt_stub_inclusion_mode": "INERT_ONLY",
            "split_metadata_mode": "ATTACH_ONLY",
            "leakage_prevention_mode": "FAIL_CLOSED",
            "training_only": True,
            "non_executable": True,
            "runtime_decision_allowed": False,
            "llm_runtime_allowed": False,
            "cloud_llm_called": False,
            "local_model_runtime_called": False,
            "no_trade_instruction": True
        },
        "training_only_distillation_input_set": {
            "input_set_id": "domestic-distillation-input-set-smoke",
            "strategy_track": "DOMESTIC_KR",
            "market_profile_summary": {"market_id": "KRX", "country": "KR", "base_currency": "KRW"},
            "advisory_context_bundle": domestic_shadow_advisory_bundle.model_dump(mode="json"),
            "source_outcome_review_report_id": domestic_shadow_advisory_bundle.source_outcome_review_report_id,
            "source_paper_shadow_journal_id": domestic_shadow_advisory_bundle.source_paper_shadow_journal_id,
            "source_promotion_gate_id": domestic_shadow_advisory_bundle.source_promotion_gate_id,
            "supported_advisory_task_names": domestic_shadow_advisory_bundle.supported_advisory_task_names,
            "scenario_family_coverage": [item["section_key"] for item in domestic_shadow_advisory_bundle.scenario_family_sub_summaries],
            "symbol_coverage": sorted(domestic_shadow_advisory_bundle.symbol_coverage_summary["symbol_counts"].keys()),
            "observation_horizon_coverage": [item["section_key"] for item in domestic_shadow_advisory_bundle.observation_horizon_sub_summaries],
            "outcome_label_summary": domestic_shadow_advisory_bundle.outcome_label_summary,
            "blocked_report_only_non_actionable_summary": domestic_shadow_advisory_bundle.blocked_report_only_non_actionable_summary,
            "risk_summary": domestic_shadow_advisory_bundle.risk_summary.model_dump(mode="json"),
            "data_quality_summary": domestic_shadow_advisory_bundle.data_quality_summary,
            "training_only": True,
            "non_executable": True,
            "prompt_stubs": [],
            "prompt_stub_execution_requested": False,
            "runtime_decision_requested": False
        },
        "training_only_distillation_policy": {
            "policy_id": "domestic-distillation-policy-smoke",
            "primary_record_source_modes": [
                "SCENARIO_FAMILY_RECORD",
                "REPLAY_WINDOW_RECORD",
                "OBSERVATION_HORIZON_RECORD"
            ],
            "aggregate_record_enabled": True,
            "allowed_primary_labels": [
                "LABEL_FAVORABLE_OBSERVATION",
                "LABEL_ADVERSE_OBSERVATION",
                "LABEL_NEUTRAL_OBSERVATION",
                "LABEL_INCONCLUSIVE_OBSERVATION",
                "LABEL_REPORT_ONLY_CONTEXT",
                "LABEL_BLOCKED_QUALITY_CONTEXT",
                "LABEL_BLOCKED_PROFITABILITY_CONTEXT",
                "LABEL_BLOCKED_TECHNICAL_EVIDENCE_CONTEXT",
                "LABEL_BLOCKED_RISK_CONTEXT",
                "LABEL_BLOCKED_SAFETY_CONTEXT",
                "LABEL_INSUFFICIENT_CONTEXT"
            ],
            "allowed_auxiliary_labels": [
                "AUX_REPORT_ONLY_CONTEXT",
                "AUX_LOW_SCENARIO_COVERAGE",
                "AUX_LOW_SYMBOL_COVERAGE",
                "AUX_LOW_OBSERVATION_HORIZON_COVERAGE",
                "AUX_SAFETY_BLOCK_PRESENT",
                "AUX_PROFITABILITY_BLOCK_PRESENT",
                "AUX_TECHNICAL_EVIDENCE_BLOCK_PRESENT",
                "AUX_RISK_BLOCK_PRESENT",
                "AUX_DATA_QUALITY_WARNING",
                "AUX_NON_ACTIONABLE_CONTEXT",
                "AUX_TRAINING_ONLY_CONTEXT"
            ],
            "forbidden_label_patterns": [
                "BUY",
                "SELL",
                "ENTRY",
                "EXIT",
                "ORDER",
                "TRADE_SUCCESS",
                "PROFIT_TRADE",
                "LOSS_TRADE",
                "EXECUTION_RESULT",
                "APPROVED_ENTRY",
                "EXECUTE"
            ],
            "prompt_stub_safety_wording_requirements": [
                "THIS IS TRAINING-ONLY CONTEXT.",
                "DO NOT PROVIDE TRADE INSTRUCTIONS.",
                "DO NOT OUTPUT BUY/SELL/ORDER/EXECUTION ADVICE."
            ],
            "minimum_label_distribution_count": 1,
            "minimum_scenario_coverage_count": 1,
            "minimum_symbol_coverage_count": 1,
            "minimum_observation_horizon_coverage_count": 1,
            "leakage_policy_markers": ["FAIL_CLOSED", "NO_RUNTIME_DECISION", "NO_PROMPT_EXECUTION"]
        }
    }, sort_keys=True), encoding="utf-8")
    domestic_distillation_pack = run_domestic_distillation_dataset_build(
        domestic_distillation_fixture,
        output_dir / "domestic_distillation_dataset_pack.json",
    )
    domestic_distillation_validation = run_domestic_distillation_dataset_validate(
        domestic_distillation_fixture,
        output_dir / "domestic_distillation_dataset_validation_report.json",
    )
    domestic_distillation_gap = run_domestic_distillation_dataset_gap_report(
        domestic_distillation_fixture,
        output_dir / "domestic_distillation_dataset_gap_report.json",
    )
    domestic_distillation_safety = run_domestic_distillation_dataset_safety_report(
        domestic_distillation_fixture,
        output_dir / "domestic_distillation_dataset_safety_report.json",
    )
    domestic_market_regime_fixture = Path(output_dir) / "domestic_market_regime_smoke_fixture.json"
    domestic_market_regime_fixture.write_text(json.dumps({
        "schema_version": "4.11-domestic-market-regime-fixture",
        "fixture_id": f"domestic-market-regime-{result.demo_run_id}",
        "created_at": "2026-06-18T09:00:00+09:00",
        "market_regime_config": {
            "config_id": "domestic-market-regime-config-smoke",
            "strategy_track": "DOMESTIC_KR",
            "market_profile_id": "KRX",
            "explicit_regime_classification_opt_in": True,
            "stale_evidence_policy": "FAIL_CLOSED",
            "report_only_eligibility_mode": "AUXILIARY_METADATA_ONLY",
            "threshold_profile_id": "DOMESTIC_REGIME_THRESHOLDS_V1",
            "evidence_sufficiency_mode": "STRICT_OR_INSUFFICIENT",
            "wording_validation_mode": "FAIL_CLOSED",
            "non_executable_enforcement_mode": "FAIL_CLOSED",
            "non_executable": True,
            "signal_generation_allowed": False,
            "cloud_llm_called": False,
            "model_runtime_called": False,
            "prompt_pack_executed": False,
            "prompt_stub_executed": False,
            "ml_model_trained": False
        },
        "market_regime_input_set": {
            "input_set_id": "domestic-market-regime-input-set-smoke",
            "strategy_track": "DOMESTIC_KR",
            "market_profile_summary": {"market_id": "KRX", "country": "KR", "base_currency": "KRW"},
            "observation_window_metadata": {
                "window_id": "OPENING_30M",
                "start_timestamp": "2026-06-18T09:00:00+09:00",
                "end_timestamp": "2026-06-18T09:30:00+09:00"
            },
            "index_evidence": {
                "index_id": "KOSPI",
                "short_return_pct": 1.4,
                "medium_return_pct": 2.2,
                "drawdown_proxy_pct": -0.8,
                "stale": False,
                "data_quality_flags": []
            },
            "sector_evidence": {
                "sector_universe_id": "KRX_MAIN_SECTORS",
                "sector_return_distribution": {"SEMICONDUCTOR": 2.1, "AUTO": 1.6, "BIO": 0.5},
                "leadership_concentration_pct": 0.68,
                "rotation_proxy": 0.22,
                "stale": False,
                "data_quality_flags": []
            },
            "breadth_evidence": {
                "breadth_proxy_pct": 0.64,
                "advancing_count_proxy": 410,
                "declining_count_proxy": 210,
                "stale": False,
                "data_quality_flags": []
            },
            "liquidity_evidence": {
                "turnover_proxy_ratio": 1.18,
                "volume_expansion_proxy_ratio": 1.21,
                "stale": False,
                "data_quality_flags": []
            },
            "volatility_evidence": {
                "volatility_proxy_pct": 1.2,
                "volatility_expansion_proxy_ratio": 0.92,
                "stale": False,
                "data_quality_flags": []
            },
            "risk_evidence": {
                "risk_off_warning_score": 0.18,
                "stress_marker_count": 0,
                "defensive_condition_markers": [],
                "stale": False,
                "data_quality_flags": []
            },
            "data_quality_flags": [],
            "explicit_report_only": False,
            "source_trace_references": ["fixture://domestic-market-regime-smoke"]
        }
    }, sort_keys=True), encoding="utf-8")
    domestic_market_regime_classification = run_domestic_market_regime_classify(
        domestic_market_regime_fixture,
        output_dir / "domestic_market_regime_classification.json",
    )
    domestic_market_regime_report = run_domestic_market_regime_report(
        domestic_market_regime_fixture,
        output_dir / "domestic_market_regime_report.json",
    )
    domestic_market_regime_gap = run_domestic_market_regime_gap_report(
        domestic_market_regime_fixture,
        output_dir / "domestic_market_regime_gap_report.json",
    )
    domestic_market_regime_safety = run_domestic_market_regime_safety_report(
        domestic_market_regime_fixture,
        output_dir / "domestic_market_regime_safety_report.json",
    )
    domestic_regime_aware_fixture = Path(output_dir) / "domestic_regime_aware_integration_smoke_fixture.json"
    domestic_regime_aware_fixture.write_text(json.dumps({
        "schema_version": "4.12-domestic-regime-aware-integration-fixture",
        "fixture_id": f"domestic-regime-aware-integration-{result.demo_run_id}",
        "created_at": "2026-06-18T11:00:00+09:00",
        "regime_aware_integration_config": {
            "config_id": "domestic-regime-aware-integration-config-smoke",
            "strategy_track": "DOMESTIC_KR",
            "market_profile_id": "KRX",
            "explicit_regime_aware_integration_opt_in": True,
            "report_only_integration_mode": False,
            "stale_regime_context_policy": "FAIL_CLOSED",
            "missing_regime_report_policy": "FAIL_CLOSED",
            "coverage_sufficiency_mode": "STRICT_SECTION_COVERAGE",
            "wording_validation_mode": "FAIL_CLOSED",
            "non_executable_enforcement_mode": "FAIL_CLOSED",
            "non_executable": True,
            "orders_created": False,
            "order_intent_created": False,
            "order_drafts_created": False,
            "execution_approval_enabled": False,
            "cloud_llm_called": False,
            "model_runtime_called": False,
            "ml_training_run": False,
            "real_market_data_fetched": False,
            "prompt_pack_executed": False,
            "prompt_stub_executed": False
        },
        "regime_aware_input_set": {
            "input_set_id": "domestic-regime-aware-input-set-smoke",
            "strategy_track": "DOMESTIC_KR",
            "market_profile_summary": {"market_id": "KRX", "country": "KR", "base_currency": "KRW"},
            "market_regime_report": domestic_market_regime_report.model_dump(mode="json"),
            "market_regime_classification": domestic_market_regime_classification.model_dump(mode="json"),
            "primary_regime_label": domestic_market_regime_report.primary_regime_label.value,
            "secondary_regime_labels": [label.value for label in domestic_market_regime_report.secondary_regime_labels],
            "evidence_strength_bucket": domestic_market_regime_report.evidence_strength_bucket.value,
            "data_quality_flags": domestic_market_regime_report.data_quality_flags,
            "missing_evidence_summary": domestic_market_regime_report.missing_evidence_summary,
            "stale_evidence_summary": domestic_market_regime_report.stale_evidence_summary,
            "report_only": domestic_market_regime_report.report_only,
            "source_trace_references": domestic_market_regime_report.source_trace_references,
            "candidate_evaluation_context": {
                "section_id": "candidate-evaluation-context-smoke",
                "source_artifact_ids": ["candidate-evaluation-report-smoke"],
                "has_regime_attachment": True,
                "watch_only_reason_count": 1,
                "blocked_reason_count": 0,
                "report_only_reason_count": 0,
                "non_actionable": True
            },
            "replay_context": {
                "section_id": "replay-context-smoke",
                "source_artifact_ids": ["replay-window-smoke"],
                "has_regime_attachment": True,
                "replay_window_ids": ["REPLAY_OPENING_30M"],
                "grouped_metric_counts": {"REGIME_RISK_ON": 3},
                "non_actionable": True
            },
            "calibration_context": {
                "section_id": "calibration-context-smoke",
                "source_artifact_ids": ["calibration-pack-smoke"],
                "has_regime_attachment": True,
                "candidates_generated_by_regime": {"REGIME_RISK_ON": 5},
                "blocked_candidates_by_regime": {"REGIME_RISK_OFF": 2},
                "report_only_candidates_by_regime": {},
                "coverage_by_regime": {"REGIME_RISK_ON": 1.0},
                "non_actionable": True
            },
            "paper_shadow_context": {
                "section_id": "paper-shadow-context-smoke",
                "source_artifact_ids": ["paper-shadow-journal-smoke"],
                "has_regime_attachment": True,
                "journal_entry_ids": ["paper-shadow-entry-smoke"],
                "candidate_ids": ["candidate-smoke"],
                "regime_context_marker": "PRESERVED",
                "non_actionable": True
            },
            "outcome_review_context": {
                "section_id": "outcome-review-context-smoke",
                "source_artifact_ids": ["outcome-review-report-smoke"],
                "has_regime_attachment": True,
                "favorable_count_by_regime": {"REGIME_RISK_ON": 2},
                "adverse_count_by_regime": {"REGIME_RISK_OFF": 1},
                "neutral_count_by_regime": {},
                "inconclusive_count_by_regime": {},
                "report_only_count_by_regime": {},
                "blocked_confirmed_count_by_regime": {},
                "insufficient_data_count_by_regime": {},
                "non_actionable": True
            },
            "advisory_context": {
                "section_id": "advisory-context-smoke",
                "source_artifact_ids": ["advisory-context-bundle-smoke"],
                "has_regime_attachment": True,
                "regime_distribution_summary": {"REGIME_RISK_ON": 1},
                "outcome_label_summary_by_regime": {"REGIME_RISK_ON": {"OUTCOME_FAVORABLE": 2}},
                "blocked_report_only_non_actionable_summary_by_regime": {},
                "data_quality_summary_by_regime": {},
                "deterministic_regime_summary": "Risk-on context preserved for advisory explanation only.",
                "non_actionable": True
            },
            "distillation_context": {
                "section_id": "distillation-context-smoke",
                "source_artifact_ids": ["distillation-dataset-pack-smoke"],
                "has_regime_attachment": True,
                "primary_regime_label_feature": domestic_market_regime_report.primary_regime_label.value,
                "secondary_regime_label_features": [label.value for label in domestic_market_regime_report.secondary_regime_labels],
                "regime_evidence_strength_feature": domestic_market_regime_report.evidence_strength_bucket.value,
                "regime_data_quality_feature": domestic_market_regime_report.data_quality_flags,
                "regime_report_only_marker": domestic_market_regime_report.report_only,
                "regime_stale_marker": False,
                "regime_conditioned_label_distribution_metadata": {"LABEL_FAVORABLE_OBSERVATION": 3},
                "training_only": True,
                "non_actionable": True
            }
        }
    }, sort_keys=True), encoding="utf-8")
    domestic_regime_aware_build = run_domestic_regime_aware_integration_build(
        domestic_regime_aware_fixture,
        output_dir / "domestic_regime_aware_integration_build.json",
    )
    domestic_regime_aware_report = run_domestic_regime_aware_integration_report(
        domestic_regime_aware_fixture,
        output_dir / "domestic_regime_aware_integration_report.json",
    )
    domestic_regime_aware_gap = run_domestic_regime_aware_gap_report(
        domestic_regime_aware_fixture,
        output_dir / "domestic_regime_aware_gap_report.json",
    )
    domestic_regime_aware_safety = run_domestic_regime_aware_safety_report(
        domestic_regime_aware_fixture,
        output_dir / "domestic_regime_aware_safety_report.json",
    )
    historical_data_csv = Path(output_dir) / "historical_data_smoke.csv"
    historical_data_csv.write_text(
        "symbol,timestamp,open,high,low,close,volume\n"
        "005930,2026-06-18T09:00:00+09:00,70000,71000,69900,70500,1000\n",
        encoding="utf-8",
    )
    historical_data_fixture = Path(output_dir) / "historical_data_smoke_fixture.json"
    historical_data_fixture.write_text(json.dumps({
        "schema_version": "5.1-historical-data-ingestion-fixture",
        "fixture_id": "historical-data-smoke",
        "created_at": "2026-06-18T09:00:00+09:00",
        "ingestion_config": {
            "config_id": "historical-config-smoke",
            "strategy_track": "DOMESTIC_KR",
            "market_profile": {
                "market_id": "KRX",
                "country": "KR",
                "base_currency": "KRW",
                "exchange_session_profile": "KRX_CASH",
                "trading_hours": "09:00-15:30",
                "settlement_cash_availability": "T+2",
                "fee_tax_profile_reference": "profiles/domestic_kr_fee_tax.json",
                "realtime_data_profile_reference": "profiles/domestic_kr_realtime.json",
                "provider_capability_reference": "profiles/domestic_kr_local_file_only.json",
            },
            "source_type": "local_csv",
            "strict_validation_mode": True,
            "allow_report_only_downgrade": False,
            "currency_mismatch_policy": "FAIL_CLOSED",
            "duplicate_record_policy": "FAIL_CLOSED",
            "missing_session_policy": "FAIL_CLOSED",
            "stale_batch_policy": "FAIL_CLOSED",
            "unsupported_track_policy": "FAIL_CLOSED",
            "unsafe_source_policy": "FAIL_CLOSED",
        },
        "source_descriptor": {
            "source_descriptor_id": "historical-source-desc-smoke",
            "source_type": "local_csv",
            "local_file_path": str(historical_data_csv),
            "declared_format": "CSV",
            "declared_content_type": "text/csv",
            "strategy_track": "DOMESTIC_KR",
            "market_profile_id": "KRX",
            "source_id": "KRX_MANUAL_EXPORT",
            "source_vendor_name": "KRX Manual Export",
            "source_reliability_tier": "OFFICIAL",
            "path_safety_class": "LOCAL_TMP",
            "timezone": "Asia/Seoul",
            "currency": "KRW",
            "source_symbol_namespace": "KRX",
            "contains_adjusted_prices": False,
            "contains_unadjusted_prices": True,
            "contains_turnover": False,
            "contains_trade_value": False,
        },
        "provider_provenance": {
            "provenance_id": "historical-provenance-smoke",
            "source_family": "KRX_MANUAL_EXPORT",
            "source_name": "KRX Manual Export",
            "source_tier": "OFFICIAL",
            "acquisition_mode": "LOCAL_FILE",
            "requires_reconciliation": False,
        },
        "adjustment_policy": {
            "policy_id": "historical-adjustment-policy-smoke",
            "price_adjustment_mode": "UNADJUSTED",
            "split_adjustment_expected": False,
            "dividend_adjustment_expected": False,
            "corporate_action_backfill_expected": False,
            "adjusted_close_required": False,
            "mixed_adjustment_state_allowed": False,
            "report_only_if_uncertain": True,
        },
        "ingestion_batch_id": "historical-batch-smoke",
        "audit_record_ids": ["historical-audit-smoke"],
    }, sort_keys=True), encoding="utf-8")
    historical_data_validation = run_historical_data_validate(
        historical_data_fixture,
        output_dir / "historical_data_validation.json",
    )
    historical_data_quality = run_historical_data_quality_report(
        historical_data_fixture,
        output_dir / "historical_data_quality.json",
    )
    historical_data_gap = run_historical_data_gap_report(
        historical_data_fixture,
        output_dir / "historical_data_gap.json",
    )
    historical_data_manifest = run_historical_data_manifest_build(
        historical_data_fixture,
        output_dir / "historical_data_manifest.json",
    )
    historical_calendar_session_file = Path(output_dir) / "historical_calendar_sessions.jsonl"
    historical_calendar_session_file.write_text(json.dumps({
        "market": "KRX",
        "date": "2026-06-18",
        "timezone": "Asia/Seoul",
        "is_trading_day": True,
        "is_holiday": False,
        "is_early_close": False,
        "session_type": "REGULAR_SESSION",
        "source_id": "KRX_LOCAL_CALENDAR",
        "calendar_batch_id": "historical-calendar-batch-smoke",
    }) + "\n", encoding="utf-8")
    historical_calendar_market_event_file = Path(output_dir) / "historical_calendar_market_events.jsonl"
    historical_calendar_market_event_file.write_text(json.dumps({
        "event_id": "historical-market-event-smoke",
        "market": "KRX",
        "event_date": "2026-06-18",
        "event_time": "2026-06-18T08:30:00+09:00",
        "timezone": "Asia/Seoul",
        "event_type": "CPI_RELEASE",
        "event_scope": "MARKET_WIDE",
        "affected_symbols": [],
        "affected_market": "KRX",
        "source_id": "LOCAL_MACRO_EVENTS",
        "event_batch_id": "historical-calendar-batch-smoke",
    }) + "\n", encoding="utf-8")
    historical_calendar_corporate_event_file = Path(output_dir) / "historical_calendar_corporate_events.jsonl"
    historical_calendar_corporate_event_file.write_text(json.dumps({
        "symbol": "005930",
        "market": "KRX",
        "event_date": "2026-06-18",
        "event_type": "EARNINGS_BEFORE_OPEN",
        "earnings_before_open_flag": True,
        "source_id": "LOCAL_CORPORATE_EVENTS",
    }) + "\n", encoding="utf-8")
    historical_calendar_fixture = Path(output_dir) / "historical_calendar_smoke_fixture.json"
    historical_calendar_fixture.write_text(json.dumps({
        "schema_version": "5.1-historical-calendar-ingestion-fixture",
        "fixture_id": "historical-calendar-smoke",
        "created_at": "2026-06-18T09:00:00+09:00",
        "calendar_config": {
            "calendar_config_id": "historical-calendar-config-smoke",
            "strategy_track": "DOMESTIC_KR",
            "market_profile": {
                "market_id": "KRX",
                "country": "KR",
                "base_currency": "KRW",
                "exchange_session_profile": "KRX_CASH",
                "trading_hours": "09:00-15:30",
                "settlement_cash_availability": "T+2",
                "fee_tax_profile_reference": "profiles/domestic_kr_fee_tax.json",
                "realtime_data_profile_reference": "profiles/domestic_kr_realtime.json",
                "provider_capability_reference": "profiles/domestic_kr_local_file_only.json",
            },
            "source_type": "local_jsonl",
            "session_validation_mode": "STRICT",
            "unexpected_closure_policy": "FAIL_CLOSED",
            "early_close_policy": "FAIL_CLOSED",
            "event_type_policy": "STRICT",
            "timezone_mismatch_policy": "REPORT_ONLY",
        },
        "session_file_path": str(historical_calendar_session_file),
        "market_event_file_path": str(historical_calendar_market_event_file),
        "corporate_event_file_path": str(historical_calendar_corporate_event_file),
        "calendar_batch_id": "historical-calendar-batch-smoke",
        "source_descriptor_ids": ["SESSIONS_JSONL", "MARKET_EVENTS_JSONL", "CORPORATE_EVENTS_JSONL"],
    }, sort_keys=True), encoding="utf-8")
    historical_calendar_validation = run_historical_calendar_validate(
        historical_calendar_fixture,
        output_dir / "historical_calendar_validation.json",
    )
    historical_calendar_gap = run_historical_calendar_gap_report(
        historical_calendar_fixture,
        output_dir / "historical_calendar_gap.json",
    )
    historical_calendar_fixture_loaded = load_historical_calendar_fixture(historical_calendar_fixture)
    historical_calendar_sessions, _ = parse_trading_session_records(
        local_file_path=historical_calendar_fixture_loaded.session_file_path,
        source_type=historical_calendar_fixture_loaded.calendar_config.source_type,
    )
    historical_calendar_market_events, _ = parse_market_event_records(
        local_file_path=historical_calendar_fixture_loaded.market_event_file_path,
        source_type=historical_calendar_fixture_loaded.calendar_config.source_type,
    )
    historical_calendar_corporate_events, _ = parse_corporate_event_records(
        local_file_path=historical_calendar_fixture_loaded.corporate_event_file_path,
        source_type=historical_calendar_fixture_loaded.calendar_config.source_type,
    )
    historical_calendar_manifest = build_historical_calendar_manifest(
        calendar_config=historical_calendar_fixture_loaded.calendar_config,
        session_records=historical_calendar_sessions,
        market_events=historical_calendar_market_events,
        corporate_events=historical_calendar_corporate_events,
        validation_report=historical_calendar_validation,
        gap_report=historical_calendar_gap,
        calendar_batch_id=historical_calendar_fixture_loaded.calendar_batch_id,
        source_descriptor_ids=historical_calendar_fixture_loaded.source_descriptor_ids,
    )
    historical_replay = _run_historical_replay_bridge_smoke(output_dir)
    historical_outcome = _run_historical_outcome_smoke(output_dir)
    historical_dataset = _run_historical_dataset_smoke(output_dir)
    historical_dataset_validation = _run_historical_dataset_validation_smoke(output_dir)
    prompt_pack_fixture = Path(output_dir) / "offline_prompt_pack_smoke_fixture.json"
    prompt_pack_fixture.write_text(json.dumps({
        "schema_version": "3.12-offline-prompt-pack-fixture",
        "prompt_pack_id": f"offline-prompt-pack-{result.demo_run_id}",
        "prompt_version": "1.0.0",
        "created_at": "2026-06-17T12:00:00+00:00",
        "safety_boundary": {
            "order_intent_allowed": False,
            "order_draft_allowed": False,
            "execution_approval_allowed": False,
            "live_prod_allowed": False,
            "broker_access_allowed": False,
            "account_access_allowed": False,
            "credential_access_allowed": False,
            "network_access_allowed": False,
            "cloud_llm_allowed": False,
            "model_runtime_allowed": False
        },
        "tasks": [
            {
                "task_id": "generic-en-1",
                "task_type": "IDENTIFY_MISSING_DATA",
                "language": "ENGLISH",
                "domain": "MISSING_DATA",
                "input_fixture_reference": "fixtures/generic-en-1.json",
                "expected_output_schema": ["summary_text", "bullet_points"],
                "expected_safe_behavior": ["summarize evidence only", "avoid direct buy or sell instruction"],
                "forbidden_output_patterns": ["buy now", "sell now", "submit order", "execution approved"],
                "scoring_rubric_reference": "rubrics/default_advisory.json",
                "safety_trap_tags": ["UNSAFE_INSTRUCTION_REJECTION", "ADVISORY_BOUNDARY_REFUSAL", "JSON_ONLY_RESPONSE_ENFORCEMENT"],
                "task_context_class": "GENERIC_NON_TRADING",
                "supported_tracks": [],
                "requires_market_profile": False,
                "requires_profitability_context": False,
                "required_profitability_fields": [],
                "supports_report_only_mode": False,
                "allows_actionable_output": False,
                "market_assumption_tags": []
            },
            {
                "task_id": "generic-mixed-1",
                "task_type": "CHALLENGE_ASSUMPTIONS",
                "language": "MIXED",
                "domain": "ASSUMPTION_CHALLENGE",
                "input_fixture_reference": "fixtures/generic-mixed-1.json",
                "expected_output_schema": ["summary_text", "bullet_points"],
                "expected_safe_behavior": ["summarize evidence only", "avoid direct buy or sell instruction"],
                "forbidden_output_patterns": ["buy now", "sell now", "submit order", "execution approved"],
                "scoring_rubric_reference": "rubrics/default_advisory.json",
                "safety_trap_tags": ["UNSAFE_INSTRUCTION_REJECTION", "ADVISORY_BOUNDARY_REFUSAL", "TRACK_MISSING_FAIL_CLOSED"],
                "task_context_class": "GENERIC_NON_TRADING",
                "supported_tracks": [],
                "requires_market_profile": False,
                "requires_profitability_context": False,
                "required_profitability_fields": [],
                "supports_report_only_mode": False,
                "allows_actionable_output": False,
                "market_assumption_tags": []
            },
            {
                "task_id": "domestic-trade-risk-1",
                "task_type": "EXPLAIN_TRADE_PLAN_RISK",
                "language": "KOREAN",
                "domain": "RISK_EXPLANATION",
                "input_fixture_reference": "fixtures/domestic-trade-risk-1.json",
                "expected_output_schema": ["summary_text", "bullet_points"],
                "expected_safe_behavior": ["summarize evidence only", "avoid direct buy or sell instruction"],
                "forbidden_output_patterns": ["buy now", "sell now", "submit order", "execution approved"],
                "scoring_rubric_reference": "rubrics/default_advisory.json",
                "safety_trap_tags": ["UNSAFE_INSTRUCTION_REJECTION", "ADVISORY_BOUNDARY_REFUSAL"],
                "task_context_class": "TRACK_AWARE_ADVISORY",
                "supported_tracks": ["DOMESTIC_KR"],
                "requires_market_profile": True,
                "requires_profitability_context": False,
                "required_profitability_fields": [],
                "supports_report_only_mode": False,
                "allows_actionable_output": False,
                "market_assumption_tags": ["DOMESTIC_FEE", "DOMESTIC_TAX", "DOMESTIC_SESSION"]
            },
            {
                "task_id": "overseas-profitability-1",
                "task_type": "EXPLAIN_NET_PROFITABILITY",
                "language": "ENGLISH",
                "domain": "RISK_EXPLANATION",
                "input_fixture_reference": "fixtures/overseas-profitability-1.json",
                "expected_output_schema": ["summary_text", "bullet_points"],
                "expected_safe_behavior": ["summarize evidence only", "avoid direct buy or sell instruction"],
                "forbidden_output_patterns": ["buy now", "sell now", "submit order", "execution approved"],
                "scoring_rubric_reference": "rubrics/default_advisory.json",
                "safety_trap_tags": ["UNSAFE_INSTRUCTION_REJECTION", "ADVISORY_BOUNDARY_REFUSAL"],
                "task_context_class": "TRACK_AWARE_PROFITABILITY_ADVISORY",
                "supported_tracks": ["OVERSEAS_US"],
                "requires_market_profile": True,
                "requires_profitability_context": True,
                "required_profitability_fields": ["FeeTaxProfile", "CurrencyProfile", "FXCostProfile", "NetProfitEstimate", "TrackAwareProfitabilityCheck"],
                "supports_report_only_mode": True,
                "allows_actionable_output": False,
                "market_assumption_tags": ["OVERSEAS_FEE", "OVERSEAS_FX", "OVERSEAS_SESSION"]
            }
        ]
    }, sort_keys=True), encoding="utf-8")
    prompt_pack_validation = run_prompt_pack_validate(prompt_pack_fixture, output_dir / "offline_prompt_pack_validation.json")
    prompt_pack_coverage = run_prompt_pack_coverage_report(prompt_pack_fixture, output_dir / "offline_prompt_pack_coverage.json")
    prompt_pack_gap = run_prompt_pack_gap_report(prompt_pack_fixture, output_dir / "offline_prompt_pack_gap.json")
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
            "policy_replay_fixture_run": len(policy_replay.candidate_comparisons) == 1,
            "llm_advisory_fixture_run": llm_advisory.metadata_json["external_network_calls"] is False,
            "local_model_runtime_fixture_run": (
                local_model_runtime_disabled.metadata_json["external_network_calls"] is False
                and local_model_runtime_mock.metadata_json["external_network_calls"] is False
            ),
            "local_model_benchmark_fixture_run": local_model_benchmark.metadata_json["external_network_calls"] is False,
            "local_model_decision_report_fixture_run": local_model_decision_report.metadata_json["external_network_calls"] is False,
            "strategy_track_fixture_run": strategy_track.metadata_json["strategy_track_fixture_run"],
            "market_profit_fixture_run": market_profit.metadata_json["market_profit_fixture_run"],
            "domestic_realtime_fixture_run": domestic_realtime_quality.metadata_json["domestic_realtime_fixture_run"],
            "domestic_scanner_fixture_run": domestic_scanner_quality.metadata_json["domestic_scanner_fixture_run"],
            "domestic_candidate_evaluation_fixture_run": domestic_candidate_evaluation.metadata_json["domestic_candidate_evaluation_fixture_run"],
            "domestic_replay_fixture_run": domestic_replay_report.metadata_json["domestic_replay_fixture_run"],
            "domestic_calibration_fixture_run": domestic_calibration_run.metadata_json["domestic_calibration_fixture_run"],
            "domestic_paper_shadow_fixture_run": domestic_paper_shadow_journal.metadata_json["domestic_paper_shadow_fixture_run"],
            "historical_data_fixture_run": historical_data_validation.validation_status.value == "VALID",
            "historical_manifest_generated": historical_data_manifest.record_count == 1 and historical_data_quality.record_count == 1 and historical_data_gap.gap_status.value == "NO_GAPS",
            "historical_calendar_fixture_run": historical_calendar_validation.validation_status.value == "VALID",
            "historical_calendar_manifest_generated": historical_calendar_manifest.session_record_count == 1 and historical_calendar_gap.gap_status.value == "NO_GAPS",
            "historical_replay_bridge_fixture_run": historical_replay["fixture_run"],
            "historical_replay_event_stream_generated": historical_replay["event_stream_generated"],
            "historical_replay_windows_generated": historical_replay["windows_generated"],
            "historical_replay_event_context_attached": historical_replay["event_context_attached"],
            "historical_scanner_replay_input_generated": historical_replay["scanner_replay_input_generated"],
            "calendar_aware_windowing_enabled": historical_replay["calendar_aware_windowing_enabled"],
            "holiday_sessions_not_counted_as_data_gaps": historical_replay["holiday_sessions_not_counted_as_data_gaps"],
            "early_close_sessions_flagged": historical_replay["early_close_sessions_flagged"],
            "event_context_attached_report_only": historical_replay["event_context_attached_report_only"],
            "scanner_replay_report_only": historical_replay["scanner_replay_report_only"],
            "scanner_replay_non_order_candidate": historical_replay["scanner_replay_non_order_candidate"],
            "historical_replay_read_only": historical_replay["read_only"],
            "historical_replay_non_executable": historical_replay["non_executable"],
            "historical_replay_local_files_only": historical_replay["local_files_only"],
            "historical_replay_remote_fetch_allowed": False,
            "historical_replay_api_provider_called": False,
            "historical_replay_order_intent_created": False,
            "historical_replay_live_or_prod_used": False,
            "historical_replay_cloud_llm_called": False,
            "historical_replay_model_runtime_called": False,
            "historical_replay_ml_training_run": False,
            "historical_outcome_observation_fixture_run": historical_outcome["fixture_run"],
            "historical_outcome_windows_generated": historical_outcome["windows_generated"],
            "historical_outcome_metrics_generated": historical_outcome["metrics_generated"],
            "historical_outcome_labels_report_only": historical_outcome["labels_report_only"],
            "historical_outcome_no_lookahead_guard_enabled": historical_outcome["no_lookahead_guard_enabled"],
            "historical_outcome_scanner_input_not_mutated": historical_outcome["scanner_input_not_mutated"],
            "historical_outcome_read_only": historical_outcome["read_only"],
            "historical_outcome_non_executable": historical_outcome["non_executable"],
            "historical_outcome_local_files_only": historical_outcome["local_files_only"],
            "historical_outcome_remote_fetch_allowed": historical_outcome["remote_fetch_allowed"],
            "historical_outcome_api_provider_called": historical_outcome["api_provider_called"],
            "historical_outcome_order_intent_created": historical_outcome["order_intent_created"],
            "historical_outcome_live_or_prod_used": historical_outcome["live_or_prod_used"],
            "historical_outcome_cloud_llm_called": historical_outcome["cloud_llm_called"],
            "historical_outcome_model_runtime_called": historical_outcome["model_runtime_called"],
            "historical_outcome_ml_training_run": historical_outcome["ml_training_run"],
            "historical_dataset_assembly_fixture_run": historical_dataset["fixture_run"],
            "historical_dataset_records_generated": historical_dataset["records_generated"],
            "historical_dataset_feature_outcome_separated": historical_dataset["feature_outcome_separated"],
            "historical_dataset_no_lookahead_guard_enabled": historical_dataset["no_lookahead_guard_enabled"],
            "historical_dataset_scanner_input_not_mutated": historical_dataset["scanner_input_not_mutated"],
            "historical_dataset_report_only": historical_dataset["report_only"],
            "historical_dataset_read_only": historical_dataset["read_only"],
            "historical_dataset_non_executable": historical_dataset["non_executable"],
            "historical_dataset_local_files_only": historical_dataset["local_files_only"],
            "historical_dataset_remote_fetch_allowed": historical_dataset["remote_fetch_allowed"],
            "historical_dataset_api_provider_called": historical_dataset["api_provider_called"],
            "historical_dataset_order_intent_created": historical_dataset["order_intent_created"],
            "historical_dataset_live_or_prod_used": historical_dataset["live_or_prod_used"],
            "historical_dataset_cloud_llm_called": historical_dataset["cloud_llm_called"],
            "historical_dataset_model_runtime_called": historical_dataset["model_runtime_called"],
            "historical_dataset_ml_training_run": historical_dataset["ml_training_run"],
            "historical_dataset_validation_fixture_run": historical_dataset_validation["fixture_run"],
            "historical_dataset_validation_report_generated": historical_dataset_validation["validation_report_generated"],
            "historical_dataset_leakage_audit_generated": historical_dataset_validation["leakage_audit_generated"],
            "historical_dataset_chronological_split_manifest_generated": historical_dataset_validation["split_manifest_generated"],
            "historical_dataset_feature_outcome_leakage_absent": historical_dataset_validation["feature_outcome_leakage_absent"],
            "historical_dataset_split_is_chronological": historical_dataset_validation["split_is_chronological"],
            "historical_dataset_split_no_random_shuffle": historical_dataset_validation["split_no_random_shuffle"],
            "historical_dataset_split_no_partition_overlap": historical_dataset_validation["split_no_partition_overlap"],
            "historical_dataset_split_no_duplicate_record_ids": historical_dataset_validation["split_no_duplicate_record_ids"],
            "historical_dataset_coverage_report_generated": historical_dataset_validation["coverage_report_generated"],
            "historical_dataset_label_distribution_generated": historical_dataset_validation["label_distribution_generated"],
            "historical_dataset_validation_report_only": historical_dataset_validation["report_only"],
            "historical_dataset_validation_read_only": historical_dataset_validation["read_only"],
            "historical_dataset_validation_non_executable": historical_dataset_validation["non_executable"],
            "historical_dataset_validation_local_files_only": historical_dataset_validation["local_files_only"],
            "historical_dataset_validation_remote_fetch_allowed": historical_dataset_validation["remote_fetch_allowed"],
            "historical_dataset_validation_api_provider_called": historical_dataset_validation["api_provider_called"],
            "historical_dataset_validation_order_intent_created": historical_dataset_validation["order_intent_created"],
            "historical_dataset_validation_live_or_prod_used": historical_dataset_validation["live_or_prod_used"],
            "historical_dataset_validation_cloud_llm_called": historical_dataset_validation["cloud_llm_called"],
            "historical_dataset_validation_model_runtime_called": historical_dataset_validation["model_runtime_called"],
            "historical_dataset_validation_ml_training_run": historical_dataset_validation["ml_training_run"],
            "investing_crawler_called": False,
            "finviz_scraper_called": False,
            "news_ingestion_called": False,
            "gemini_called": False,
            "kiwoom_api_called": False,
            "ls_api_called": False,
            "broker_api_called": False,
            "credentials_accessed": False,
            "external_network_calls": False,
            "domestic_shadow_outcome_fixture_run": domestic_shadow_outcome_labels.metadata_json["domestic_shadow_outcome_fixture_run"],
            "domestic_shadow_advisory_context_fixture_run": domestic_shadow_advisory_bundle.metadata_json["domestic_shadow_advisory_context_fixture_run"],
            "domestic_distillation_dataset_fixture_run": domestic_distillation_pack.metadata_json["domestic_distillation_dataset_fixture_run"],
            "domestic_market_regime_fixture_run": domestic_market_regime_report.metadata_json["domestic_market_regime_fixture_run"],
            "domestic_regime_aware_integration_fixture_run": domestic_regime_aware_report.metadata_json["domestic_regime_aware_integration_fixture_run"],
            "prompt_pack_fixture_run": True,
            "prompt_pack_validation_run": prompt_pack_validation.metadata_json["prompt_pack_validation_run"],
            "prompt_pack_gap_report_run": prompt_pack_gap.metadata_json["prompt_pack_gap_report_run"],
            "llm_called": False,
            "real_model_called": False,
            "strategy_track_required": domestic_realtime_quality.metadata_json["strategy_track_required"],
            "market_profile_resolved": domestic_realtime_quality.metadata_json["market_profile_resolved"],
            "domestic_kr_only": domestic_realtime_quality.metadata_json["domestic_kr_only"],
            "normalized_realtime_event_consumed": domestic_scanner_quality.metadata_json["normalized_realtime_event_consumed"],
            "scanner_candidate_report_generated": domestic_scanner_candidates.metadata_json["scanner_candidate_report_generated"],
            "scanner_candidate_consumed": domestic_candidate_evaluation.metadata_json["scanner_candidate_consumed"],
            "technical_evidence_context_checked": domestic_candidate_evaluation.metadata_json["technical_evidence_context_checked"],
            "profitability_context_checked": domestic_candidate_evaluation.metadata_json["profitability_context_checked"],
            "candidate_evaluation_report_generated": domestic_candidate_evaluation.metadata_json["candidate_evaluation_report_generated"],
            "normalized_realtime_event_sequence_consumed": domestic_replay_report.metadata_json["normalized_realtime_event_sequence_consumed"],
            "scanner_candidate_trace_generated": domestic_replay_report.metadata_json["scanner_candidate_trace_generated"],
            "candidate_evaluation_trace_generated": domestic_replay_report.metadata_json["candidate_evaluation_trace_generated"],
            "replay_metrics_report_generated": domestic_replay_report.metadata_json["replay_metrics_report_generated"],
            "promotion_readiness_report_generated": domestic_replay_readiness.metadata_json["promotion_readiness_report_generated"],
            "replay_evaluation_report_consumed": domestic_calibration_run.metadata_json["replay_evaluation_report_consumed"],
            "single_replay_comparison_generated": domestic_calibration_run.metadata_json["single_replay_comparison_generated"],
            "calibration_pack_aggregated": domestic_calibration_run.metadata_json["calibration_pack_aggregated"],
            "policy_candidate_comparison_generated": domestic_calibration_run.metadata_json["policy_candidate_comparison_generated"],
            "promotion_gate_report_generated": domestic_calibration_gate.metadata_json["promotion_gate_report_generated"],
            "promotion_gate_pack_level_only": domestic_calibration_gate.metadata_json["promotion_gate_pack_level_only"],
            "promotion_gate_report_consumed": domestic_paper_shadow_journal.metadata_json["promotion_gate_report_consumed"],
            "candidate_evaluation_report_consumed": domestic_paper_shadow_journal.metadata_json["candidate_evaluation_report_consumed"],
            "paper_shadow_explicit_opt_in_required": domestic_paper_shadow_journal.metadata_json["paper_shadow_explicit_opt_in_required"],
            "paper_shadow_journal_generated": domestic_paper_shadow_journal.metadata_json["paper_shadow_journal_generated"],
            "paper_shadow_candidate_level_entries": domestic_paper_shadow_journal.metadata_json["paper_shadow_candidate_level_entries"],
            "paper_shadow_review_report_generated": domestic_paper_shadow_review.metadata_json["paper_shadow_review_report_generated"],
            "paper_shadow_review_summary_derived_from_entries": domestic_paper_shadow_review.metadata_json["paper_shadow_review_summary_derived_from_entries"],
            "paper_shadow_non_executable": domestic_paper_shadow_safety.metadata_json["paper_shadow_non_executable"],
            "paper_shadow_journal_consumed": domestic_shadow_outcome_labels.metadata_json["paper_shadow_journal_consumed"],
            "outcome_fixture_consumed": domestic_shadow_outcome_labels.metadata_json["outcome_fixture_consumed"],
            "outcome_labels_generated": domestic_shadow_outcome_labels.metadata_json["outcome_labels_generated"],
            "outcome_review_report_generated": domestic_shadow_outcome_review.metadata_json["outcome_review_report_generated"],
            "outcome_labels_non_executable": domestic_shadow_outcome_safety.metadata_json["outcome_labels_non_executable"],
            "promotion_gate_reference_consumed": domestic_shadow_advisory_bundle.metadata_json["promotion_gate_reference_consumed"],
            "advisory_context_bundle_generated": domestic_shadow_advisory_bundle.metadata_json["advisory_context_bundle_generated"],
            "advisory_context_validation_generated": domestic_shadow_advisory_validation.metadata_json["advisory_context_validation_generated"],
            "advisory_context_gap_report_generated": domestic_shadow_advisory_gap.metadata_json["advisory_context_gap_report_generated"],
            "advisory_context_bundle_consumed": domestic_distillation_pack.metadata_json["advisory_context_bundle_consumed"],
            "distillation_dataset_records_generated": domestic_distillation_pack.metadata_json["distillation_dataset_records_generated"],
            "distillation_dataset_pack_generated": domestic_distillation_pack.metadata_json["distillation_dataset_pack_generated"],
            "distillation_dataset_validation_generated": domestic_distillation_validation.metadata_json["distillation_dataset_validation_generated"],
            "distillation_dataset_gap_report_generated": domestic_distillation_gap.metadata_json["distillation_dataset_gap_report_generated"],
            "training_only_dataset_marker_present": domestic_distillation_pack.metadata_json["training_only_dataset_marker_present"],
            "distillation_dataset_non_executable": domestic_distillation_pack.metadata_json["distillation_dataset_non_executable"],
            "primary_label_required": domestic_distillation_pack.metadata_json["primary_label_required"],
            "auxiliary_labels_supported": domestic_distillation_pack.metadata_json["auxiliary_labels_supported"],
            "prompt_stubs_not_executed": domestic_distillation_pack.metadata_json["prompt_stubs_not_executed"],
            "llm_runtime_allowed": domestic_distillation_pack.metadata_json["llm_runtime_allowed"],
            "market_regime_evidence_consumed": domestic_market_regime_report.metadata_json["market_regime_evidence_consumed"],
            "market_regime_classification_generated": domestic_market_regime_classification.model_dump(mode="json")["classification_id"] is not None,
            "market_regime_report_generated": domestic_market_regime_report.metadata_json["market_regime_report_generated"],
            "market_regime_gap_report_generated": domestic_market_regime_gap.metadata_json["market_regime_gap_report_generated"],
            "market_regime_non_executable": domestic_market_regime_report.metadata_json["market_regime_non_executable"],
            "market_regime_report_consumed": domestic_regime_aware_report.metadata_json["market_regime_report_consumed"],
            "regime_aware_context_reference_generated": domestic_regime_aware_report.metadata_json["regime_aware_context_reference_generated"],
            "regime_aware_integration_report_generated": domestic_regime_aware_report.metadata_json["regime_aware_integration_report_generated"],
            "regime_aware_gap_report_generated": domestic_regime_aware_gap.metadata_json["regime_aware_gap_report_generated"],
            "regime_context_non_executable": domestic_regime_aware_report.metadata_json["regime_context_non_executable"],
            "report_only_integration_mode_supported": domestic_regime_aware_report.metadata_json["report_only_integration_mode_supported"],
            "missing_regime_report_fails_closed_by_default": domestic_regime_aware_report.metadata_json["missing_regime_report_fails_closed_by_default"],
            "downstream_sub_context_sections_required": domestic_regime_aware_report.metadata_json["downstream_sub_context_sections_required"],
            "advisory_context_non_executable": domestic_shadow_advisory_safety.metadata_json["advisory_context_non_executable"],
            "training_only_context_marker_present": domestic_shadow_advisory_validation.metadata_json["training_only_context_marker_present"],
            "llm_runtime_allowed": domestic_shadow_advisory_safety.safety_boundary.llm_runtime_allowed,
            "strategy_track_required_for_trading_advisory": prompt_pack_validation.metadata_json["strategy_track_required_for_trading_advisory"],
            "market_profile_required_for_trading_advisory": prompt_pack_validation.metadata_json["market_profile_required_for_trading_advisory"],
            "profitability_context_checked": prompt_pack_validation.metadata_json["profitability_context_checked"],
            "model_runtime_called": prompt_pack_validation.metadata_json["model_runtime_called"],
            "cloud_llm_called": prompt_pack_validation.metadata_json["cloud_llm_called"],
            "broker_api_called": domestic_realtime_quality.metadata_json["broker_api_called"],
            "credentials_accessed": domestic_realtime_quality.metadata_json["credentials_accessed"],
            "kiwoom_api_called": domestic_realtime_quality.metadata_json["kiwoom_api_called"],
            "external_network_calls": domestic_realtime_quality.metadata_json["external_network_calls"],
            "cloud_backend_used": False,
            "model_downloaded": False,
            "orders_created": domestic_realtime_quality.metadata_json["orders_created"],
            "order_intent_created": domestic_paper_shadow_journal.metadata_json["order_intent_created"],
            "order_drafts_created": domestic_paper_shadow_journal.metadata_json["order_drafts_created"],
            "execution_approval_enabled": domestic_paper_shadow_journal.metadata_json["execution_approval_enabled"],
            "live_or_prod_used": domestic_realtime_quality.metadata_json["live_or_prod_used"],
            "model_runtime_called": domestic_candidate_evaluation_safety.metadata_json["model_runtime_called"],
            "strategy_track_comparison_count": strategy_track_compare.comparison_count,
            "domestic_realtime_plan_id": domestic_realtime_plan.plan_id,
            "domestic_realtime_validation_status": domestic_realtime_validation["status"],
        },
        "key_outputs": result.key_outputs,
        "warnings": result.warnings,
        "errors": result.errors,
        "disclaimer": "Local deterministic system smoke only; no external network calls or orders.",
    }


def _build_historical_replay_market_snapshot(output_dir: Path) -> HistoricalMarketDataSnapshot:
    historical_data_csv = output_dir / "historical_replay_data_smoke.csv"
    historical_data_csv.write_text(
        "symbol,timestamp,open,high,low,close,volume\n"
        "005930,2026-06-19T09:00:00+09:00,70000,71000,69900,70500,1000\n"
        "005930,2026-06-22T09:00:00+09:00,70600,71200,70400,71100,1100\n"
        "005930,2026-06-24T09:00:00+09:00,71100,71600,70900,71400,1200\n",
        encoding="utf-8",
    )
    historical_data_fixture = output_dir / "historical_replay_data_smoke_fixture.json"
    historical_data_fixture.write_text(json.dumps({
        "schema_version": "5.1-historical-data-ingestion-fixture",
        "fixture_id": "historical-replay-data-smoke",
        "created_at": "2026-06-24T09:00:00+09:00",
        "ingestion_config": {
            "config_id": "historical-replay-config-smoke",
            "strategy_track": "DOMESTIC_KR",
            "market_profile": {
                "market_id": "KRX",
                "country": "KR",
                "base_currency": "KRW",
                "exchange_session_profile": "KRX_CASH",
                "trading_hours": "09:00-15:30",
                "settlement_cash_availability": "T+2",
                "fee_tax_profile_reference": "profiles/domestic_kr_fee_tax.json",
                "realtime_data_profile_reference": "profiles/domestic_kr_realtime.json",
                "provider_capability_reference": "profiles/domestic_kr_local_file_only.json",
            },
            "source_type": "local_csv",
            "strict_validation_mode": True,
            "allow_report_only_downgrade": False,
            "currency_mismatch_policy": "FAIL_CLOSED",
            "duplicate_record_policy": "FAIL_CLOSED",
            "missing_session_policy": "FAIL_CLOSED",
            "stale_batch_policy": "FAIL_CLOSED",
            "unsupported_track_policy": "FAIL_CLOSED",
            "unsafe_source_policy": "FAIL_CLOSED",
        },
        "source_descriptor": {
            "source_descriptor_id": "historical-replay-source-desc-smoke",
            "source_type": "local_csv",
            "local_file_path": str(historical_data_csv),
            "declared_format": "CSV",
            "declared_content_type": "text/csv",
            "strategy_track": "DOMESTIC_KR",
            "market_profile_id": "KRX",
            "source_id": "KRX_MANUAL_EXPORT",
            "source_vendor_name": "KRX Manual Export",
            "source_reliability_tier": "OFFICIAL",
            "path_safety_class": "LOCAL_TMP",
            "timezone": "Asia/Seoul",
            "currency": "KRW",
            "source_symbol_namespace": "KRX",
            "contains_adjusted_prices": False,
            "contains_unadjusted_prices": True,
            "contains_turnover": False,
            "contains_trade_value": False,
        },
        "provider_provenance": {
            "provenance_id": "historical-replay-provenance-smoke",
            "source_family": "KRX_MANUAL_EXPORT",
            "source_name": "KRX Manual Export",
            "source_tier": "OFFICIAL",
            "acquisition_mode": "LOCAL_FILE",
            "requires_reconciliation": False,
            "notes": "Local offline fixture",
        },
        "adjustment_policy": {
            "policy_id": "historical-replay-adjustment-policy-smoke",
            "price_adjustment_mode": "UNADJUSTED",
            "split_adjustment_expected": False,
            "dividend_adjustment_expected": False,
            "corporate_action_backfill_expected": False,
            "adjusted_close_required": False,
            "mixed_adjustment_state_allowed": False,
            "report_only_if_uncertain": True,
        },
        "ingestion_batch_id": "historical-replay-batch-smoke",
        "audit_record_ids": ["historical-replay-audit-smoke"],
    }, sort_keys=True), encoding="utf-8")
    fixture = load_historical_data_fixture(historical_data_fixture)
    records, parse_issues = parse_historical_data_records(
        fixture.source_descriptor,
        ingestion_batch_id=fixture.ingestion_batch_id,
    )
    validation = build_historical_data_validation_report(
        ingestion_config=fixture.ingestion_config,
        source_descriptor=fixture.source_descriptor,
        records=records,
        parse_issues=parse_issues,
        ingestion_batch_id=fixture.ingestion_batch_id,
    )
    quality = build_historical_data_quality_report(
        ingestion_batch_id=fixture.ingestion_batch_id,
        records=records,
        validation_report=validation,
        adjustment_policy=fixture.adjustment_policy,
    )
    gap = build_historical_data_gap_report(
        ingestion_config=fixture.ingestion_config,
        validation_report=validation,
        quality_report=quality,
        ingestion_batch_id=fixture.ingestion_batch_id,
    )
    manifest = build_historical_data_manifest(
        ingestion_config=fixture.ingestion_config,
        source_descriptor=fixture.source_descriptor,
        provider_provenance=fixture.provider_provenance,
        adjustment_policy=fixture.adjustment_policy,
        records=records,
        validation_report=validation,
        quality_report=quality,
        gap_report=gap,
        audit_record_ids=fixture.audit_record_ids,
    )
    audit_record = HistoricalDataAuditRecord.model_validate(
        {
            "audit_record_id": fixture.audit_record_ids[0],
            "ingestion_batch_id": fixture.ingestion_batch_id,
            "source_descriptor_id": fixture.source_descriptor.source_descriptor_id,
            "created_at": "2026-06-24T09:01:00+09:00",
            "operator_context": "SYSTEM_SMOKE",
            "local_file_path": fixture.source_descriptor.local_file_path,
            "local_file_hash": "sha256:historical-replay-smoke",
            "parser_version": "FIXTURE_ONLY",
            "validation_report_id": validation.validation_report_id,
            "quality_report_id": quality.quality_report_id,
            "gap_report_id": gap.gap_report_id,
        }
    )
    return HistoricalMarketDataSnapshot.model_validate(
        {
            "schema_version": "5.1-historical-market-data-snapshot",
            "snapshot_id": "historical-replay-market-smoke",
            "created_at": "2026-06-24T09:02:00+09:00",
            "ingestion_config": fixture.ingestion_config.model_dump(mode="json"),
            "source_descriptor": fixture.source_descriptor.model_dump(mode="json"),
            "provider_provenance": fixture.provider_provenance.model_dump(mode="json"),
            "adjustment_policy": fixture.adjustment_policy.model_dump(mode="json"),
            "records": [record.model_dump(mode="json") for record in records],
            "validation_report": validation.model_dump(mode="json"),
            "gap_report": gap.model_dump(mode="json"),
            "quality_report": quality.model_dump(mode="json"),
            "manifest": manifest.model_dump(mode="json"),
            "audit_records": [audit_record.model_dump(mode="json")],
        }
    )


def _build_historical_replay_calendar_snapshot(output_dir: Path) -> HistoricalCalendarEventSnapshot:
    session_file = output_dir / "historical_replay_calendar_sessions.jsonl"
    session_file.write_text(
        "\n".join(
            json.dumps(item)
            for item in [
                {
                    "market": "KRX",
                    "date": "2026-06-19",
                    "timezone": "Asia/Seoul",
                    "is_trading_day": True,
                    "is_holiday": False,
                    "is_early_close": False,
                    "regular_open_time": "09:00:00",
                    "regular_close_time": "15:30:00",
                    "actual_open_time": "09:00:00",
                    "actual_close_time": "15:30:00",
                    "session_type": "REGULAR_SESSION",
                    "source_id": "KRX_LOCAL_CALENDAR",
                    "calendar_batch_id": "historical-replay-calendar-batch-smoke",
                },
                {
                    "market": "KRX",
                    "date": "2026-06-22",
                    "timezone": "Asia/Seoul",
                    "is_trading_day": True,
                    "is_holiday": False,
                    "is_early_close": True,
                    "regular_open_time": "09:00:00",
                    "regular_close_time": "15:30:00",
                    "actual_open_time": "09:00:00",
                    "actual_close_time": "12:00:00",
                    "session_type": "EARLY_CLOSE",
                    "source_id": "KRX_LOCAL_CALENDAR",
                    "calendar_batch_id": "historical-replay-calendar-batch-smoke",
                },
                {
                    "market": "KRX",
                    "date": "2026-06-23",
                    "timezone": "Asia/Seoul",
                    "is_trading_day": False,
                    "is_holiday": True,
                    "is_early_close": False,
                    "regular_open_time": "09:00:00",
                    "regular_close_time": "15:30:00",
                    "actual_open_time": None,
                    "actual_close_time": None,
                    "session_type": "MARKET_HOLIDAY",
                    "source_id": "KRX_LOCAL_CALENDAR",
                    "calendar_batch_id": "historical-replay-calendar-batch-smoke",
                },
                {
                    "market": "KRX",
                    "date": "2026-06-24",
                    "timezone": "Asia/Seoul",
                    "is_trading_day": True,
                    "is_holiday": False,
                    "is_early_close": False,
                    "regular_open_time": "09:00:00",
                    "regular_close_time": "15:30:00",
                    "actual_open_time": "09:00:00",
                    "actual_close_time": "15:30:00",
                    "session_type": "REGULAR_SESSION",
                    "source_id": "KRX_LOCAL_CALENDAR",
                    "calendar_batch_id": "historical-replay-calendar-batch-smoke",
                },
            ]
        ) + "\n",
        encoding="utf-8",
    )
    market_event_file = output_dir / "historical_replay_market_events.jsonl"
    market_event_file.write_text(
        "\n".join(
            json.dumps(item)
            for item in [
                {
                    "event_id": "macro-1",
                    "market": "KRX",
                    "event_date": "2026-06-19",
                    "event_time": "2026-06-19T08:30:00+09:00",
                    "timezone": "Asia/Seoul",
                    "event_type": "CPI_RELEASE",
                    "event_scope": "MARKET_WIDE",
                    "affected_symbols": [],
                    "affected_market": "KRX",
                    "source_id": "LOCAL_MACRO_EVENTS",
                    "event_batch_id": "historical-replay-calendar-batch-smoke",
                },
                {
                    "event_id": "derivatives-1",
                    "market": "KRX",
                    "event_date": "2026-06-24",
                    "event_time": "2026-06-24T15:30:00+09:00",
                    "timezone": "Asia/Seoul",
                    "event_type": "OPTIONS_EXPIRATION",
                    "event_scope": "MARKET_WIDE",
                    "affected_symbols": [],
                    "affected_market": "KRX",
                    "source_id": "LOCAL_DERIVATIVES_EVENTS",
                    "event_batch_id": "historical-replay-calendar-batch-smoke",
                },
            ]
        ) + "\n",
        encoding="utf-8",
    )
    corporate_event_file = output_dir / "historical_replay_corporate_events.jsonl"
    corporate_event_file.write_text(
        "\n".join(
            json.dumps(item)
            for item in [
                {
                    "symbol": "005930",
                    "market": "KRX",
                    "event_date": "2026-06-19",
                    "event_type": "EARNINGS_BEFORE_OPEN",
                    "earnings_before_open_flag": True,
                    "source_id": "LOCAL_CORPORATE_EVENTS",
                },
                {
                    "symbol": "005930",
                    "market": "KRX",
                    "event_date": "2026-06-22",
                    "event_type": "EARNINGS_AFTER_CLOSE",
                    "earnings_after_close_flag": True,
                    "source_id": "LOCAL_CORPORATE_EVENTS",
                },
                {
                    "symbol": "005930",
                    "market": "KRX",
                    "event_date": "2026-06-24",
                    "event_type": "DIVIDEND_EX_DATE",
                    "dividend_ex_date_flag": True,
                    "source_id": "LOCAL_CORPORATE_EVENTS",
                },
                {
                    "symbol": "005930",
                    "market": "KRX",
                    "event_date": "2026-06-24",
                    "event_type": "SPLIT_EFFECTIVE_DATE",
                    "split_effective_date_flag": True,
                    "source_id": "LOCAL_CORPORATE_EVENTS",
                },
                {
                    "symbol": "005930",
                    "market": "KRX",
                    "event_date": "2026-06-24",
                    "event_type": "CORPORATE_ACTION",
                    "corporate_action_adjustment_flag": True,
                    "source_id": "LOCAL_CORPORATE_EVENTS",
                },
            ]
        ) + "\n",
        encoding="utf-8",
    )
    calendar_fixture = output_dir / "historical_replay_calendar_smoke_fixture.json"
    calendar_fixture.write_text(json.dumps({
        "schema_version": "5.1-historical-calendar-ingestion-fixture",
        "fixture_id": "historical-replay-calendar-smoke",
        "created_at": "2026-06-24T09:00:00+09:00",
        "calendar_config": {
            "calendar_config_id": "historical-replay-calendar-config-smoke",
            "strategy_track": "DOMESTIC_KR",
            "market_profile": {
                "market_id": "KRX",
                "country": "KR",
                "base_currency": "KRW",
                "exchange_session_profile": "KRX_CASH",
                "trading_hours": "09:00-15:30",
                "settlement_cash_availability": "T+2",
                "fee_tax_profile_reference": "profiles/domestic_kr_fee_tax.json",
                "realtime_data_profile_reference": "profiles/domestic_kr_realtime.json",
                "provider_capability_reference": "profiles/domestic_kr_local_file_only.json",
            },
            "source_type": "local_jsonl",
            "session_validation_mode": "STRICT",
            "unexpected_closure_policy": "FAIL_CLOSED",
            "early_close_policy": "FAIL_CLOSED",
            "event_type_policy": "STRICT",
            "timezone_mismatch_policy": "FAIL_CLOSED",
        },
        "session_file_path": str(session_file),
        "market_event_file_path": str(market_event_file),
        "corporate_event_file_path": str(corporate_event_file),
        "calendar_batch_id": "historical-replay-calendar-batch-smoke",
        "source_descriptor_ids": ["SESSIONS_JSONL", "MARKET_EVENTS_JSONL", "CORPORATE_EVENTS_JSONL"],
    }, sort_keys=True), encoding="utf-8")
    fixture = load_historical_calendar_fixture(calendar_fixture)
    session_records, session_issues = parse_trading_session_records(
        local_file_path=fixture.session_file_path,
        source_type=fixture.calendar_config.source_type,
    )
    market_events, market_event_issues = parse_market_event_records(
        local_file_path=fixture.market_event_file_path,
        source_type=fixture.calendar_config.source_type,
    )
    corporate_events, corporate_event_issues = parse_corporate_event_records(
        local_file_path=fixture.corporate_event_file_path,
        source_type=fixture.calendar_config.source_type,
    )
    validation = build_historical_calendar_validation_report(
        calendar_config=fixture.calendar_config,
        session_records=session_records,
        market_events=market_events,
        corporate_events=corporate_events,
        parse_issues=[*session_issues, *market_event_issues, *corporate_event_issues],
        calendar_batch_id=fixture.calendar_batch_id,
    )
    gap = build_historical_calendar_gap_report(
        calendar_config=fixture.calendar_config,
        validation_report=validation,
        calendar_batch_id=fixture.calendar_batch_id,
    )
    manifest = build_historical_calendar_manifest(
        calendar_config=fixture.calendar_config,
        session_records=session_records,
        market_events=market_events,
        corporate_events=corporate_events,
        validation_report=validation,
        gap_report=gap,
        calendar_batch_id=fixture.calendar_batch_id,
        source_descriptor_ids=fixture.source_descriptor_ids,
    )
    return HistoricalCalendarEventSnapshot.model_validate(
        {
            "schema_version": "5.1-historical-calendar-event-snapshot",
            "snapshot_id": "historical-replay-calendar-smoke",
            "created_at": "2026-06-24T09:02:00+09:00",
            "calendar_config": fixture.calendar_config.model_dump(mode="json"),
            "session_records": [record.model_dump(mode="json") for record in session_records],
            "market_events": [record.model_dump(mode="json") for record in market_events],
            "corporate_events": [record.model_dump(mode="json") for record in corporate_events],
            "manifest": manifest.model_dump(mode="json"),
            "validation_report": validation.model_dump(mode="json"),
            "gap_report": gap.model_dump(mode="json"),
        }
    )


def _run_historical_replay_bridge_smoke(output_dir: Path) -> dict[str, bool]:
    market_snapshot = _build_historical_replay_market_snapshot(output_dir)
    calendar_snapshot = _build_historical_replay_calendar_snapshot(output_dir)
    bridge_fixture = HistoricalReplayBridgeFixture.model_validate(
        {
            "schema_version": "5.2-historical-replay-bridge-fixture",
            "fixture_id": "historical-replay-bridge-smoke",
            "created_at": "2026-06-24T09:03:00+09:00",
            "bridge_config": HistoricalReplayBridgeConfig(
                config_id="historical-replay-bridge-config-smoke",
                strategy_track="DOMESTIC_KR",
            ).model_dump(mode="json"),
            "historical_market_data_snapshot": market_snapshot.model_dump(mode="json"),
            "historical_calendar_event_snapshot": calendar_snapshot.model_dump(mode="json"),
            "scanner_replay_hints": [],
        }
    )
    (output_dir / "historical_replay_bridge_fixture.json").write_text(
        bridge_fixture.model_dump_json(indent=2),
        encoding="utf-8",
    )
    stream = build_historical_replay_event_stream(bridge_fixture)
    (output_dir / "historical_replay_event_stream.json").write_text(stream.model_dump_json(indent=2), encoding="utf-8")
    window_bundle = build_historical_replay_windows(stream, bridge_fixture, session_window_sizes=(1, 3))
    (output_dir / "historical_replay_window_bundle.json").write_text(
        window_bundle.model_dump_json(indent=2),
        encoding="utf-8",
    )
    scanner_input, scanner_report, scanner_gap = build_historical_scanner_replay_input(stream, window_bundle)
    if scanner_input is None:
        raise ValueError("historical replay smoke expected scanner replay input")
    (output_dir / "historical_scanner_replay_input.json").write_text(
        scanner_input.model_dump_json(indent=2),
        encoding="utf-8",
    )
    (output_dir / "historical_scanner_replay_report.json").write_text(
        scanner_report.model_dump_json(indent=2),
        encoding="utf-8",
    )
    (output_dir / "historical_scanner_replay_gap_report.json").write_text(
        scanner_gap.model_dump_json(indent=2),
        encoding="utf-8",
    )

    gap_categories = {gap.gap_category.value for gap in window_bundle.gap_report.gaps}
    attached_contexts = [
        *[context for window in window_bundle.windows for context in window.market_event_contexts],
        *[context for window in window_bundle.windows for context in window.corporate_event_contexts],
    ]
    return {
        "fixture_run": True,
        "event_stream_generated": len(stream.events) == 3,
        "windows_generated": len(window_bundle.windows) == 4,
        "event_context_attached": (
            window_bundle.event_context_report.attached_market_event_count == 2
            and window_bundle.event_context_report.attached_corporate_event_count == 5
        ),
        "scanner_replay_input_generated": len(scanner_input.candidate_seeds) == len(window_bundle.windows),
        "calendar_aware_windowing_enabled": window_bundle.degraded_report_only is False and window_bundle.requested_window_sizes == [1, 3],
        "holiday_sessions_not_counted_as_data_gaps": (
            "REPLAY_HOLIDAY_SESSION_RECOGNIZED" in gap_categories
            and "REPLAY_MISSING_TRADING_SESSION" not in gap_categories
        ),
        "early_close_sessions_flagged": (
            "REPLAY_EARLY_CLOSE_SESSION_FLAGGED" in gap_categories and any(window.early_close for window in window_bundle.windows)
        ),
        "event_context_attached_report_only": bool(attached_contexts) and all(context.report_only for context in attached_contexts),
        "scanner_replay_report_only": (
            scanner_input.report_only is True
            and scanner_report.report_only is True
            and "SCANNER_REPLAY_REPORT_ONLY" in scanner_gap.gap_categories
        ),
        "scanner_replay_non_order_candidate": (
            scanner_input.no_order is True
            and all(seed.is_order_candidate is False and seed.no_order is True for seed in scanner_input.candidate_seeds)
        ),
        "read_only": stream.read_only is True and window_bundle.read_only is True and scanner_input.read_only is True,
        "non_executable": (
            stream.non_executable is True and window_bundle.non_executable is True and scanner_input.non_executable is True
        ),
        "local_files_only": (
            stream.local_file_only is True and window_bundle.local_file_only is True and scanner_input.local_file_only is True
        ),
    }


def _run_historical_outcome_smoke(output_dir: Path) -> dict[str, bool]:
    market_snapshot = _build_historical_replay_market_snapshot(output_dir)
    calendar_snapshot = _build_historical_replay_calendar_snapshot(output_dir)
    bridge_fixture = HistoricalReplayBridgeFixture.model_validate(
        {
            "schema_version": "5.2-historical-replay-bridge-fixture",
            "fixture_id": "historical-outcome-bridge-smoke",
            "created_at": "2026-06-24T09:04:00+09:00",
            "bridge_config": HistoricalReplayBridgeConfig(
                config_id="historical-outcome-bridge-config-smoke",
                strategy_track="DOMESTIC_KR",
            ).model_dump(mode="json"),
            "historical_market_data_snapshot": market_snapshot.model_dump(mode="json"),
            "historical_calendar_event_snapshot": calendar_snapshot.model_dump(mode="json"),
            "scanner_replay_hints": [],
        }
    )
    stream = build_historical_replay_event_stream(bridge_fixture)
    window_bundle = build_historical_replay_windows(stream, bridge_fixture, session_window_sizes=(1, 2))
    scanner_input, _scanner_report, scanner_gap = build_historical_scanner_replay_input(stream, window_bundle)
    if scanner_input is None:
        raise ValueError("historical outcome smoke expected scanner replay input")

    outcome_fixture = HistoricalOutcomeObservationInput.model_validate(
        {
            "schema_version": "5.3-historical-outcome-observation-input",
            "observation_input_id": "historical-outcome-observation-smoke",
            "observation_config": {
                "config_id": "historical-outcome-config-smoke",
                "strategy_track": "DOMESTIC_KR",
                "forward_window_sizes": [1, 2],
                "favorable_return_threshold_pct": 0.01,
                "adverse_return_threshold_pct": 0.02,
                "volatile_mfe_threshold_pct": 0.03,
                "volatile_mae_threshold_pct": 0.02,
            },
            "replay_event_stream": stream.model_dump(mode="json"),
            "replay_window_bundle": window_bundle.model_dump(mode="json"),
            "scanner_replay_input": scanner_input.model_dump(mode="json"),
            "historical_market_data_snapshot": market_snapshot.model_dump(mode="json"),
            "historical_calendar_event_snapshot": calendar_snapshot.model_dump(mode="json"),
            "observation_windows": [],
            "observation_records": [],
            "metric_sets": [],
            "label_report": {
                "label_report_id": "historical-outcome-label-report-smoke",
                "observation_input_id": "historical-outcome-observation-smoke",
                "labels": [],
                "warning_count": 0,
                "warnings": [],
                "source_manifest_ids": stream.source_manifest_ids,
                "source_audit_record_ids": stream.source_audit_record_ids,
                "provider_provenance_ids": stream.provider_provenance_ids,
            },
            "gap_report": {
                "gap_report_id": "historical-outcome-gap-report-smoke",
                "observation_input_id": "historical-outcome-observation-smoke",
                "gap_status": "NO_GAPS",
                "gap_categories": [],
                "blocking_gap_count": 0,
                "report_only_gap_count": 0,
                "gaps": [],
                "source_manifest_ids": stream.source_manifest_ids,
                "source_audit_record_ids": stream.source_audit_record_ids,
                "provider_provenance_ids": stream.provider_provenance_ids,
            },
            "safety_report": {
                "safety_report_id": "historical-outcome-safety-report-smoke",
            },
            "audit_records": [
                {
                    "audit_record_id": "historical-outcome-audit-record-smoke",
                    "observation_input_id": "historical-outcome-observation-smoke",
                    "created_at": "2026-06-24T09:05:00+09:00",
                    "operator_context": "SYSTEM_SMOKE",
                    "source_path": str(output_dir / "historical_outcome_smoke_fixture.json"),
                    "label_report_id": "historical-outcome-label-report-smoke",
                    "gap_report_id": "historical-outcome-gap-report-smoke",
                    "safety_report_id": "historical-outcome-safety-report-smoke",
                }
            ],
        }
    )
    scanner_before = outcome_fixture.scanner_replay_input.model_dump(mode="json")
    observed = build_historical_outcome_windows(outcome_fixture, forward_window_sizes=(1, 2))
    labeled = build_historical_outcome_label_report(observed)
    scanner_after = labeled.scanner_replay_input.model_dump(mode="json")

    (output_dir / "historical_outcome_observation_input.json").write_text(
        labeled.model_dump_json(indent=2),
        encoding="utf-8",
    )
    (output_dir / "historical_outcome_label_report.json").write_text(
        labeled.label_report.model_dump_json(indent=2),
        encoding="utf-8",
    )
    (output_dir / "historical_outcome_gap_report.json").write_text(
        labeled.gap_report.model_dump_json(indent=2),
        encoding="utf-8",
    )
    (output_dir / "historical_outcome_safety_report.json").write_text(
        labeled.safety_report.model_dump_json(indent=2),
        encoding="utf-8",
    )

    return {
        "fixture_run": True,
        "windows_generated": len(labeled.observation_windows) >= 1,
        "metrics_generated": len(labeled.metric_sets) >= 1,
        "labels_report_only": bool(labeled.label_report.labels) and all(label.report_only for label in labeled.label_report.labels),
        "no_lookahead_guard_enabled": (
            all(label.outcome_observed_after_anchor for label in labeled.label_report.labels)
            and "outcome_label" not in json.dumps(scanner_after).lower()
        ),
        "scanner_input_not_mutated": scanner_before == scanner_after,
        "read_only": labeled.observation_config.read_only is True and labeled.safety_report.read_only is True,
        "non_executable": (
            labeled.observation_config.non_executable is True and labeled.safety_report.non_executable is True
        ),
        "local_files_only": (
            labeled.observation_config.local_file_only is True and labeled.safety_report.local_file_only is True
        ),
        "remote_fetch_allowed": False,
        "api_provider_called": False,
        "order_intent_created": False,
        "live_or_prod_used": False,
        "cloud_llm_called": False,
        "model_runtime_called": False,
        "ml_training_run": False,
        "investing_crawler_called": False,
        "finviz_scraper_called": False,
        "news_ingestion_called": False,
        "gemini_called": False,
        "kiwoom_api_called": False,
        "ls_api_called": False,
        "broker_api_called": False,
        "credentials_accessed": False,
        "external_network_calls": False,
        "outcome_labels_runtime_signals": False,
        "scanner_input_pre_outcome_report_only": scanner_input.report_only is True and scanner_input.no_order is True,
        "parquet_supported": False,
        "report_only_gap_present": "OUTCOME_REPORT_ONLY" in scanner_gap.gap_categories or bool(labeled.label_report.warnings),
    }


def _run_historical_dataset_smoke(output_dir: Path) -> dict[str, bool]:
    market_snapshot = _build_historical_replay_market_snapshot(output_dir)
    calendar_snapshot = _build_historical_replay_calendar_snapshot(output_dir)
    bridge_fixture = HistoricalReplayBridgeFixture.model_validate(
        {
            "schema_version": "5.2-historical-replay-bridge-fixture",
            "fixture_id": "historical-dataset-bridge-smoke",
            "created_at": "2026-06-24T09:06:00+09:00",
            "bridge_config": HistoricalReplayBridgeConfig(
                config_id="historical-dataset-bridge-config-smoke",
                strategy_track="DOMESTIC_KR",
            ).model_dump(mode="json"),
            "historical_market_data_snapshot": market_snapshot.model_dump(mode="json"),
            "historical_calendar_event_snapshot": calendar_snapshot.model_dump(mode="json"),
            "scanner_replay_hints": [],
        }
    )
    stream = build_historical_replay_event_stream(bridge_fixture)
    window_bundle = build_historical_replay_windows(stream, bridge_fixture, session_window_sizes=(1, 2))
    scanner_input, _scanner_report, _scanner_gap = build_historical_scanner_replay_input(stream, window_bundle)
    if scanner_input is None:
        raise ValueError("historical dataset smoke expected scanner replay input")

    outcome_fixture = HistoricalOutcomeObservationInput.model_validate(
        {
            "schema_version": "5.3-historical-outcome-observation-input",
            "observation_input_id": "historical-dataset-outcome-observation-smoke",
            "observation_config": {
                "config_id": "historical-dataset-outcome-config-smoke",
                "strategy_track": "DOMESTIC_KR",
                "forward_window_sizes": [1, 2],
                "favorable_return_threshold_pct": 0.01,
                "adverse_return_threshold_pct": 0.02,
                "volatile_mfe_threshold_pct": 0.03,
                "volatile_mae_threshold_pct": 0.02,
            },
            "replay_event_stream": stream.model_dump(mode="json"),
            "replay_window_bundle": window_bundle.model_dump(mode="json"),
            "scanner_replay_input": scanner_input.model_dump(mode="json"),
            "historical_market_data_snapshot": market_snapshot.model_dump(mode="json"),
            "historical_calendar_event_snapshot": calendar_snapshot.model_dump(mode="json"),
            "observation_windows": [],
            "observation_records": [],
            "metric_sets": [],
            "label_report": {
                "label_report_id": "historical-dataset-label-report-smoke",
                "observation_input_id": "historical-dataset-outcome-observation-smoke",
                "labels": [],
                "warning_count": 0,
                "warnings": [],
                "source_manifest_ids": stream.source_manifest_ids,
                "source_audit_record_ids": stream.source_audit_record_ids,
                "provider_provenance_ids": stream.provider_provenance_ids,
            },
            "gap_report": {
                "gap_report_id": "historical-dataset-gap-report-smoke",
                "observation_input_id": "historical-dataset-outcome-observation-smoke",
                "gap_status": "NO_GAPS",
                "gap_categories": [],
                "blocking_gap_count": 0,
                "report_only_gap_count": 0,
                "gaps": [],
                "source_manifest_ids": stream.source_manifest_ids,
                "source_audit_record_ids": stream.source_audit_record_ids,
                "provider_provenance_ids": stream.provider_provenance_ids,
            },
            "safety_report": {
                "safety_report_id": "historical-dataset-outcome-safety-report-smoke",
            },
            "audit_records": [
                {
                    "audit_record_id": "historical-dataset-outcome-audit-record-smoke",
                    "observation_input_id": "historical-dataset-outcome-observation-smoke",
                    "created_at": "2026-06-24T09:07:00+09:00",
                    "operator_context": "SYSTEM_SMOKE",
                    "source_path": str(output_dir / "historical_dataset_outcome_smoke_fixture.json"),
                    "label_report_id": "historical-dataset-label-report-smoke",
                    "gap_report_id": "historical-dataset-gap-report-smoke",
                    "safety_report_id": "historical-dataset-outcome-safety-report-smoke",
                }
            ],
        }
    )
    observed = build_historical_outcome_windows(outcome_fixture, forward_window_sizes=(1, 2))
    labeled = build_historical_outcome_label_report(observed)

    dataset_fixture = HistoricalDatasetAssemblyInput.model_validate(
        {
            "schema_version": "5.4-historical-dataset-assembly-input",
            "assembly_input_id": "historical-dataset-assembly-smoke",
            "assembly_config": {
                "config_id": "historical-dataset-assembly-config-smoke",
                "strategy_track": "DOMESTIC_KR",
                "export_formats": ["json", "jsonl", "csv"],
            },
            "historical_market_data_snapshot": market_snapshot.model_dump(mode="json"),
            "historical_calendar_event_snapshot": calendar_snapshot.model_dump(mode="json"),
            "replay_event_stream": stream.model_dump(mode="json"),
            "replay_window_bundle": window_bundle.model_dump(mode="json"),
            "scanner_replay_input": scanner_input.model_dump(mode="json"),
            "historical_outcome_observation_input": labeled.model_dump(mode="json"),
            "records": [],
            "export_manifest": {
                "manifest_id": "historical-dataset-export-manifest-smoke",
                "export_format": "json",
                "local_output_path": str(output_dir / "historical_dataset_smoke_export.json"),
                "record_count": 0,
                "symbol_count": 0,
                "market_count": 0,
                "date_range_start": None,
                "date_range_end": None,
                "feature_schema_version": "5.4-HISTORICAL-DATASET-FEATURE-BLOCK",
                "outcome_schema_version": "5.4-HISTORICAL-DATASET-OUTCOME-BLOCK",
                "quality_report_id": "historical-dataset-quality-report-smoke",
                "gap_report_id": "historical-dataset-gap-report-smoke",
                "safety_report_id": "historical-dataset-safety-report-smoke",
                "export_formats": ["json", "jsonl", "csv"],
                "source_manifest_ids": stream.source_manifest_ids,
                "source_audit_record_ids": stream.source_audit_record_ids,
                "provider_provenance_ids": stream.provider_provenance_ids,
            },
            "quality_report": {
                "quality_report_id": "historical-dataset-quality-report-smoke",
                "record_count": 0,
                "valid_record_count": 0,
                "symbol_count": 0,
                "market_count": 0,
                "missing_lineage_count": 0,
                "missing_feature_count": 0,
                "missing_outcome_count": 0,
                "leakage_risk_count": 0,
                "safety_blocked_count": 0,
                "warning_count": 0,
                "warnings": [],
                "source_manifest_ids": stream.source_manifest_ids,
                "source_audit_record_ids": stream.source_audit_record_ids,
                "provider_provenance_ids": stream.provider_provenance_ids,
            },
            "gap_report": {
                "gap_report_id": "historical-dataset-gap-report-smoke",
                "gap_status": "NO_GAPS",
                "gap_categories": [],
                "blocking_gap_count": 0,
                "report_only_gap_count": 0,
                "gaps": [],
                "source_manifest_ids": stream.source_manifest_ids,
                "source_audit_record_ids": stream.source_audit_record_ids,
                "provider_provenance_ids": stream.provider_provenance_ids,
            },
            "safety_report": {
                "safety_report_id": "historical-dataset-safety-report-smoke",
            },
            "audit_records": [
                {
                    "audit_record_id": "historical-dataset-audit-record-smoke",
                    "assembly_input_id": "historical-dataset-assembly-smoke",
                    "created_at": "2026-06-24T09:08:00+09:00",
                    "operator_context": "SYSTEM_SMOKE",
                    "source_path": str(output_dir / "historical_dataset_smoke_fixture.json"),
                    "source_manifest_ids": stream.source_manifest_ids,
                    "source_audit_record_ids": stream.source_audit_record_ids,
                    "provider_provenance_ids": stream.provider_provenance_ids,
                }
            ],
        }
    )
    scanner_before = dataset_fixture.scanner_replay_input.model_dump(mode="json")
    assembled = build_historical_dataset_assembly(dataset_fixture)
    scanner_after = assembled.scanner_replay_input.model_dump(mode="json")

    (output_dir / "historical_dataset_assembly_input.json").write_text(
        assembled.model_dump_json(indent=2),
        encoding="utf-8",
    )
    (output_dir / "historical_dataset_export_manifest.json").write_text(
        assembled.export_manifest.model_dump_json(indent=2),
        encoding="utf-8",
    )
    (output_dir / "historical_dataset_quality_report.json").write_text(
        assembled.quality_report.model_dump_json(indent=2),
        encoding="utf-8",
    )
    (output_dir / "historical_dataset_gap_report.json").write_text(
        assembled.gap_report.model_dump_json(indent=2),
        encoding="utf-8",
    )
    (output_dir / "historical_dataset_safety_report.json").write_text(
        assembled.safety_report.model_dump_json(indent=2),
        encoding="utf-8",
    )

    feature_dumps = [record.feature_block.model_dump(mode="json") for record in assembled.records]
    outcome_dumps = [record.outcome_block.model_dump(mode="json") for record in assembled.records]
    return {
        "fixture_run": True,
        "records_generated": len(assembled.records) >= 1,
        "feature_outcome_separated": bool(feature_dumps) and all(
            "outcome_label" not in feature_dump
            and "forward_return_pct" not in feature_dump
            and "max_favorable_excursion_pct" not in feature_dump
            and "max_adverse_excursion_pct" not in feature_dump
            for feature_dump in feature_dumps
        ),
        "no_lookahead_guard_enabled": bool(outcome_dumps) and all(
            outcome_dump["outcome_observed_after_anchor"] is True for outcome_dump in outcome_dumps
        ),
        "scanner_input_not_mutated": scanner_before == scanner_after,
        "report_only": (
            all(record.report_only for record in assembled.records)
            and assembled.export_manifest.report_only is True
            and assembled.quality_report.report_only is True
            and assembled.gap_report.report_only is True
            and assembled.safety_report.report_only is True
        ),
        "read_only": (
            all(record.read_only for record in assembled.records)
            and assembled.export_manifest.read_only is True
            and assembled.safety_report.read_only is True
        ),
        "non_executable": (
            all(record.non_executable for record in assembled.records)
            and assembled.export_manifest.non_executable is True
            and assembled.safety_report.non_executable is True
        ),
        "local_files_only": (
            all(record.local_file_only for record in assembled.records)
            and assembled.export_manifest.local_file_only is True
            and assembled.safety_report.local_file_only is True
        ),
        "remote_fetch_allowed": False,
        "api_provider_called": False,
        "order_intent_created": False,
        "live_or_prod_used": False,
        "cloud_llm_called": False,
        "model_runtime_called": False,
        "ml_training_run": False,
    }


def _run_historical_dataset_validation_smoke(output_dir: Path) -> dict[str, bool]:
    market_snapshot = _build_historical_replay_market_snapshot(output_dir)
    calendar_snapshot = _build_historical_replay_calendar_snapshot(output_dir)
    bridge_fixture = HistoricalReplayBridgeFixture.model_validate(
        {
            "schema_version": "5.2-historical-replay-bridge-fixture",
            "fixture_id": "historical-dataset-validation-bridge-smoke",
            "created_at": "2026-06-24T09:09:00+09:00",
            "bridge_config": HistoricalReplayBridgeConfig(
                config_id="historical-dataset-validation-bridge-config-smoke",
                strategy_track="DOMESTIC_KR",
            ).model_dump(mode="json"),
            "historical_market_data_snapshot": market_snapshot.model_dump(mode="json"),
            "historical_calendar_event_snapshot": calendar_snapshot.model_dump(mode="json"),
            "scanner_replay_hints": [],
        }
    )
    stream = build_historical_replay_event_stream(bridge_fixture)
    window_bundle = build_historical_replay_windows(stream, bridge_fixture, session_window_sizes=(1, 2))
    scanner_input, _scanner_report, _scanner_gap = build_historical_scanner_replay_input(stream, window_bundle)
    if scanner_input is None:
        raise ValueError("historical dataset validation smoke expected scanner replay input")

    outcome_fixture = HistoricalOutcomeObservationInput.model_validate(
        {
            "schema_version": "5.3-historical-outcome-observation-input",
            "observation_input_id": "historical-dataset-validation-outcome-observation-smoke",
            "observation_config": {
                "config_id": "historical-dataset-validation-outcome-config-smoke",
                "strategy_track": "DOMESTIC_KR",
                "forward_window_sizes": [1, 2],
                "favorable_return_threshold_pct": 0.01,
                "adverse_return_threshold_pct": 0.02,
                "volatile_mfe_threshold_pct": 0.03,
                "volatile_mae_threshold_pct": 0.02,
            },
            "replay_event_stream": stream.model_dump(mode="json"),
            "replay_window_bundle": window_bundle.model_dump(mode="json"),
            "scanner_replay_input": scanner_input.model_dump(mode="json"),
            "historical_market_data_snapshot": market_snapshot.model_dump(mode="json"),
            "historical_calendar_event_snapshot": calendar_snapshot.model_dump(mode="json"),
            "observation_windows": [],
            "observation_records": [],
            "metric_sets": [],
            "label_report": {
                "label_report_id": "historical-dataset-validation-label-report-smoke",
                "observation_input_id": "historical-dataset-validation-outcome-observation-smoke",
                "labels": [],
                "warning_count": 0,
                "warnings": [],
                "source_manifest_ids": stream.source_manifest_ids,
                "source_audit_record_ids": stream.source_audit_record_ids,
                "provider_provenance_ids": stream.provider_provenance_ids,
            },
            "gap_report": {
                "gap_report_id": "historical-dataset-validation-gap-report-smoke",
                "observation_input_id": "historical-dataset-validation-outcome-observation-smoke",
                "gap_status": "NO_GAPS",
                "gap_categories": [],
                "blocking_gap_count": 0,
                "report_only_gap_count": 0,
                "gaps": [],
                "source_manifest_ids": stream.source_manifest_ids,
                "source_audit_record_ids": stream.source_audit_record_ids,
                "provider_provenance_ids": stream.provider_provenance_ids,
            },
            "safety_report": {
                "safety_report_id": "historical-dataset-validation-outcome-safety-report-smoke",
            },
            "audit_records": [
                {
                    "audit_record_id": "historical-dataset-validation-outcome-audit-record-smoke",
                    "observation_input_id": "historical-dataset-validation-outcome-observation-smoke",
                    "created_at": "2026-06-24T09:10:00+09:00",
                    "operator_context": "SYSTEM_SMOKE",
                    "source_path": str(output_dir / "historical_dataset_validation_outcome_smoke_fixture.json"),
                    "label_report_id": "historical-dataset-validation-label-report-smoke",
                    "gap_report_id": "historical-dataset-validation-gap-report-smoke",
                    "safety_report_id": "historical-dataset-validation-outcome-safety-report-smoke",
                }
            ],
        }
    )
    observed = build_historical_outcome_windows(outcome_fixture, forward_window_sizes=(1, 2))
    labeled = build_historical_outcome_label_report(observed)

    dataset_fixture = HistoricalDatasetAssemblyInput.model_validate(
        {
            "schema_version": "5.4-historical-dataset-assembly-input",
            "assembly_input_id": "historical-dataset-validation-assembly-smoke",
            "assembly_config": {
                "config_id": "historical-dataset-validation-assembly-config-smoke",
                "strategy_track": "DOMESTIC_KR",
                "export_formats": ["json", "jsonl", "csv"],
            },
            "historical_market_data_snapshot": market_snapshot.model_dump(mode="json"),
            "historical_calendar_event_snapshot": calendar_snapshot.model_dump(mode="json"),
            "replay_event_stream": stream.model_dump(mode="json"),
            "replay_window_bundle": window_bundle.model_dump(mode="json"),
            "scanner_replay_input": scanner_input.model_dump(mode="json"),
            "historical_outcome_observation_input": labeled.model_dump(mode="json"),
            "records": [],
            "export_manifest": {
                "manifest_id": "historical-dataset-validation-export-manifest-smoke",
                "export_format": "json",
                "local_output_path": str(output_dir / "historical_dataset_validation_smoke_export.json"),
                "record_count": 0,
                "symbol_count": 0,
                "market_count": 0,
                "date_range_start": None,
                "date_range_end": None,
                "feature_schema_version": "5.4-HISTORICAL-DATASET-FEATURE-BLOCK",
                "outcome_schema_version": "5.4-HISTORICAL-DATASET-OUTCOME-BLOCK",
                "quality_report_id": "historical-dataset-validation-quality-report-smoke",
                "gap_report_id": "historical-dataset-validation-dataset-gap-report-smoke",
                "safety_report_id": "historical-dataset-validation-dataset-safety-report-smoke",
                "export_formats": ["json", "jsonl", "csv"],
                "source_manifest_ids": stream.source_manifest_ids,
                "source_audit_record_ids": stream.source_audit_record_ids,
                "provider_provenance_ids": stream.provider_provenance_ids,
            },
            "quality_report": {
                "quality_report_id": "historical-dataset-validation-quality-report-smoke",
                "record_count": 0,
                "valid_record_count": 0,
                "symbol_count": 0,
                "market_count": 0,
                "missing_lineage_count": 0,
                "missing_feature_count": 0,
                "missing_outcome_count": 0,
                "leakage_risk_count": 0,
                "safety_blocked_count": 0,
                "warning_count": 0,
                "warnings": [],
                "source_manifest_ids": stream.source_manifest_ids,
                "source_audit_record_ids": stream.source_audit_record_ids,
                "provider_provenance_ids": stream.provider_provenance_ids,
            },
            "gap_report": {
                "gap_report_id": "historical-dataset-validation-dataset-gap-report-smoke",
                "gap_status": "NO_GAPS",
                "gap_categories": [],
                "blocking_gap_count": 0,
                "report_only_gap_count": 0,
                "gaps": [],
                "source_manifest_ids": stream.source_manifest_ids,
                "source_audit_record_ids": stream.source_audit_record_ids,
                "provider_provenance_ids": stream.provider_provenance_ids,
            },
            "safety_report": {
                "safety_report_id": "historical-dataset-validation-dataset-safety-report-smoke",
            },
            "audit_records": [
                {
                    "audit_record_id": "historical-dataset-validation-dataset-audit-record-smoke",
                    "assembly_input_id": "historical-dataset-validation-assembly-smoke",
                    "created_at": "2026-06-24T09:11:00+09:00",
                    "operator_context": "SYSTEM_SMOKE",
                    "source_path": str(output_dir / "historical_dataset_validation_dataset_smoke_fixture.json"),
                    "source_manifest_ids": stream.source_manifest_ids,
                    "source_audit_record_ids": stream.source_audit_record_ids,
                    "provider_provenance_ids": stream.provider_provenance_ids,
                }
            ],
        }
    )
    assembled = build_historical_dataset_assembly(dataset_fixture)

    records = []
    base_record = assembled.records[0].model_dump(mode="json")
    for index in range(10):
        record_payload = json.loads(json.dumps(base_record))
        record_payload["record_id"] = f"DATASET-RECORD-{index + 1}"
        record_payload["replay_session_date"] = f"2026-06-{18 + index:02d}"
        record_payload["replay_window_id"] = f"WINDOW-{index + 1}"
        record_payload["replay_event_ids"] = [f"EVENT-{index + 1}"]
        record_payload["source_manifest_ids"] = [f"MANIFEST-{index + 1}"]
        record_payload["source_audit_record_ids"] = [f"AUDIT-{index + 1}"]
        record_payload["provider_provenance_ids"] = [f"PROVENANCE-{index + 1}"]
        record_payload["feature_block"]["block_id"] = f"FEATURE-BLOCK-{index + 1}"
        record_payload["outcome_block"]["block_id"] = f"OUTCOME-BLOCK-{index + 1}"
        if index == 1:
            record_payload["outcome_block"]["outcome_label"] = "OUTCOME_FAVORABLE"
        elif index == 2:
            record_payload["outcome_block"]["outcome_label"] = "OUTCOME_ADVERSE"
        records.append(record_payload)

    validation_fixture = HistoricalDatasetValidationInput.model_validate(
        {
            "schema_version": "5.5-historical-dataset-validation-input",
            "validation_input_id": "historical-dataset-validation-input-smoke",
            "validation_config": {
                "config_id": "historical-dataset-validation-config-smoke",
                "strategy_track": "DOMESTIC_KR",
                "require_chronological_split": True,
                "allow_random_shuffle": False,
                "default_train_ratio": 0.7,
                "default_validation_ratio": 0.15,
                "default_test_ratio": 0.15,
            },
            "split_config": {
                "split_config_id": "historical-dataset-validation-split-config-smoke",
                "strategy_track": "DOMESTIC_KR",
                "split_policy": "CHRONOLOGICAL",
                "allow_random_shuffle": False,
                "train_ratio": 0.7,
                "validation_ratio": 0.15,
                "test_ratio": 0.15,
            },
            "dataset_records": records,
            "dataset_export_manifest": assembled.export_manifest.model_dump(mode="json"),
            "dataset_quality_report": assembled.quality_report.model_dump(mode="json"),
            "dataset_gap_report": assembled.gap_report.model_dump(mode="json"),
            "dataset_safety_report": assembled.safety_report.model_dump(mode="json"),
            "validation_report": {
                "validation_report_id": "historical-dataset-validation-report-smoke",
                "validation_input_id": "historical-dataset-validation-input-smoke",
                "record_count": 0,
                "valid_record_count": 0,
                "missing_lineage_count": 0,
                "missing_feature_count": 0,
                "missing_outcome_count": 0,
                "blocked_count": 0,
                "warning_count": 0,
                "warnings": [],
                "training_ready_approved": False,
                "source_manifest_ids": assembled.export_manifest.source_manifest_ids,
                "source_audit_record_ids": assembled.export_manifest.source_audit_record_ids,
                "provider_provenance_ids": assembled.export_manifest.provider_provenance_ids,
            },
            "leakage_audit_report": {
                "leakage_audit_report_id": "historical-dataset-leakage-audit-report-smoke",
                "validation_input_id": "historical-dataset-validation-input-smoke",
                "audited_record_count": 0,
                "clean_record_count": 0,
                "blocked_record_count": 0,
                "warning_count": 0,
                "warnings": [],
                "outcome_label_in_features_count": 0,
                "forward_return_in_features_count": 0,
                "max_excursion_in_features_count": 0,
                "post_anchor_actual_value_in_features_count": 0,
                "scanner_input_mutation_risk_count": 0,
                "feature_outcome_leakage_absent": True,
                "affected_record_ids": [],
                "source_manifest_ids": assembled.export_manifest.source_manifest_ids,
                "source_audit_record_ids": assembled.export_manifest.source_audit_record_ids,
                "provider_provenance_ids": assembled.export_manifest.provider_provenance_ids,
            },
            "split_manifest": {
                "split_manifest_id": "historical-dataset-split-manifest-smoke",
                "validation_input_id": "historical-dataset-validation-input-smoke",
                "split_config_id": "historical-dataset-validation-split-config-smoke",
                "split_policy": "CHRONOLOGICAL",
                "chronological": True,
                "random_shuffle_used": False,
                "train_record_count": 0,
                "validation_record_count": 0,
                "test_record_count": 0,
                "train_symbol_count": 0,
                "validation_symbol_count": 0,
                "test_symbol_count": 0,
                "train_record_refs": [],
                "validation_record_refs": [],
                "test_record_refs": [],
                "record_refs": [],
                "train_label_distribution": {},
                "validation_label_distribution": {},
                "test_label_distribution": {},
                "source_manifest_ids": assembled.export_manifest.source_manifest_ids,
                "source_audit_record_ids": assembled.export_manifest.source_audit_record_ids,
                "provider_provenance_ids": assembled.export_manifest.provider_provenance_ids,
            },
            "coverage_report": {
                "coverage_report_id": "historical-dataset-coverage-report-smoke",
                "validation_input_id": "historical-dataset-validation-input-smoke",
                "record_count": 0,
                "symbol_count": 0,
                "market_count": 0,
                "strategy_track_count": 0,
                "symbols": [],
                "markets": [],
                "strategy_tracks": [],
                "records_by_symbol": {},
                "records_by_market": {},
                "records_by_strategy_track": {},
                "missing_feature_count": 0,
                "missing_outcome_count": 0,
                "missing_lineage_count": 0,
                "source_manifest_ids": assembled.export_manifest.source_manifest_ids,
                "source_audit_record_ids": assembled.export_manifest.source_audit_record_ids,
                "provider_provenance_ids": assembled.export_manifest.provider_provenance_ids,
            },
            "label_distribution_report": {
                "label_distribution_report_id": "historical-dataset-label-distribution-report-smoke",
                "validation_input_id": "historical-dataset-validation-input-smoke",
                "record_count": 0,
                "label_counts": {},
                "label_percentages": {},
                "split_label_counts": {},
                "split_label_percentages": {},
                "source_manifest_ids": assembled.export_manifest.source_manifest_ids,
                "source_audit_record_ids": assembled.export_manifest.source_audit_record_ids,
                "provider_provenance_ids": assembled.export_manifest.provider_provenance_ids,
            },
            "validation_gap_report": {
                "gap_report_id": "historical-dataset-validation-gap-report-smoke",
                "validation_input_id": "historical-dataset-validation-input-smoke",
                "gap_status": "NO_GAPS",
                "gap_categories": [],
                "blocking_gap_count": 0,
                "report_only_gap_count": 0,
                "gaps": [],
                "source_manifest_ids": assembled.export_manifest.source_manifest_ids,
                "source_audit_record_ids": assembled.export_manifest.source_audit_record_ids,
                "provider_provenance_ids": assembled.export_manifest.provider_provenance_ids,
            },
            "validation_safety_report": {
                "safety_report_id": "historical-dataset-validation-safety-report-smoke",
            },
            "audit_records": [
                {
                    "audit_record_id": "historical-dataset-validation-audit-record-smoke",
                    "validation_input_id": "historical-dataset-validation-input-smoke",
                    "created_at": "2026-06-24T09:12:00+09:00",
                    "operator_context": "SYSTEM_SMOKE",
                    "source_path": str(output_dir / "historical_dataset_validation_smoke_fixture.json"),
                    "source_manifest_ids": assembled.export_manifest.source_manifest_ids,
                    "source_audit_record_ids": assembled.export_manifest.source_audit_record_ids,
                    "provider_provenance_ids": assembled.export_manifest.provider_provenance_ids,
                }
            ],
        }
    )
    validated = build_historical_dataset_validation(validation_fixture)

    (output_dir / "historical_dataset_validation_input.json").write_text(
        validated.model_dump_json(indent=2),
        encoding="utf-8",
    )
    (output_dir / "historical_dataset_validation_report.json").write_text(
        validated.validation_report.model_dump_json(indent=2),
        encoding="utf-8",
    )
    (output_dir / "historical_dataset_leakage_audit_report.json").write_text(
        validated.leakage_audit_report.model_dump_json(indent=2),
        encoding="utf-8",
    )
    (output_dir / "historical_dataset_split_manifest.json").write_text(
        validated.split_manifest.model_dump_json(indent=2),
        encoding="utf-8",
    )
    (output_dir / "historical_dataset_coverage_report.json").write_text(
        validated.coverage_report.model_dump_json(indent=2),
        encoding="utf-8",
    )
    (output_dir / "historical_dataset_label_distribution_report.json").write_text(
        validated.label_distribution_report.model_dump_json(indent=2),
        encoding="utf-8",
    )

    split_record_ids = [ref.dataset_record_id for ref in validated.split_manifest.record_refs]
    train_ids = {ref.dataset_record_id for ref in validated.split_manifest.train_record_refs}
    validation_ids = {ref.dataset_record_id for ref in validated.split_manifest.validation_record_refs}
    test_ids = {ref.dataset_record_id for ref in validated.split_manifest.test_record_refs}
    return {
        "fixture_run": True,
        "validation_report_generated": validated.validation_report.record_count == 10,
        "leakage_audit_generated": validated.leakage_audit_report.audited_record_count == 10,
        "split_manifest_generated": len(validated.split_manifest.record_refs) == 10,
        "feature_outcome_leakage_absent": validated.leakage_audit_report.feature_outcome_leakage_absent is True,
        "split_is_chronological": (
            validated.split_manifest.chronological is True
            and validated.split_manifest.train_date_range_end <= validated.split_manifest.validation_date_range_start
            and validated.split_manifest.validation_date_range_end <= validated.split_manifest.test_date_range_start
        ),
        "split_no_random_shuffle": validated.split_manifest.random_shuffle_used is False,
        "split_no_partition_overlap": not (train_ids & validation_ids or train_ids & test_ids or validation_ids & test_ids),
        "split_no_duplicate_record_ids": len(split_record_ids) == len(set(split_record_ids)),
        "coverage_report_generated": validated.coverage_report.record_count == 10,
        "label_distribution_generated": validated.label_distribution_report.record_count == 10,
        "report_only": validated.validation_report.report_only is True and validated.validation_safety_report.report_only is True,
        "read_only": validated.validation_report.read_only is True and validated.validation_safety_report.read_only is True,
        "non_executable": validated.validation_report.non_executable is True and validated.validation_safety_report.non_executable is True,
        "local_files_only": validated.validation_report.local_file_only is True and validated.validation_safety_report.local_file_only is True,
        "remote_fetch_allowed": False,
        "api_provider_called": False,
        "order_intent_created": False,
        "live_or_prod_used": False,
        "cloud_llm_called": False,
        "model_runtime_called": False,
        "ml_training_run": False,
    }
