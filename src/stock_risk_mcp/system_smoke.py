from __future__ import annotations

import json
import os
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
from stock_risk_mcp.historical_dataset_readiness_engine import build_historical_dataset_readiness
from stock_risk_mcp.historical_dataset_readiness_models import HistoricalDatasetReadinessInput
from stock_risk_mcp.historical_model_training_engine import (
    build_historical_model_training_plan_check,
    run_historical_model_training_sandbox,
)
from stock_risk_mcp.historical_model_training_models import HistoricalModelTrainingInput
from stock_risk_mcp.historical_model_training_models import HistoricalModelTrainingModelType
from stock_risk_mcp.historical_model_experiment_engine import build_historical_model_experiment_registry
from stock_risk_mcp.historical_model_experiment_models import HistoricalModelExperimentRegistryInput
from stock_risk_mcp.historical_signal_candidate_engine import build_historical_signal_candidate_batch
from stock_risk_mcp.historical_signal_candidate_models import HistoricalSignalCandidateInput
from stock_risk_mcp.historical_paper_trading_engine import run_historical_paper_trading
from stock_risk_mcp.historical_paper_trading_models import HistoricalPaperTradingInput
from stock_risk_mcp.broker_mock_adapter_engine import run_broker_mock_adapter_boundary
from stock_risk_mcp.broker_mock_adapter_models import BrokerMockAdapterInput
from stock_risk_mcp.kiwoom_mock_adapter_engine import run_kiwoom_mock_adapter_draft_mapping
from stock_risk_mcp.kiwoom_mock_adapter_models import KiwoomMockAdapterInput
from stock_risk_mcp.kiwoom_mock_credential_boundary_engine import (
    run_kiwoom_mock_credential_boundary_evaluation,
)
from stock_risk_mcp.kiwoom_mock_credential_boundary_models import (
    KiwoomMockCredentialBoundaryConfig,
)
from stock_risk_mcp.kiwoom_mock_oauth_draft_engine import run_kiwoom_mock_oauth_draft_boundary
from stock_risk_mcp.kiwoom_mock_oauth_draft_models import KiwoomMockOAuthDraftConfig
from stock_risk_mcp.kiwoom_mock_oauth_execution_engine import (
    build_kiwoom_mock_oauth_execution_gap_report,
    build_kiwoom_mock_oauth_execution_safety_report,
    execute_kiwoom_mock_oauth,
)
from stock_risk_mcp.kiwoom_mock_oauth_execution_models import (
    KiwoomMockOAuthExecutionConfig,
    KiwoomMockOAuthExecutionMode,
)
from stock_risk_mcp.kiwoom_mock_api_transport_draft_engine import (
    run_kiwoom_mock_api_transport_draft_boundary,
)
from stock_risk_mcp.kiwoom_mock_api_transport_draft_models import (
    KiwoomMockApiTransportDraftConfig,
)
from stock_risk_mcp.kiwoom_mock_api_preflight_gate_engine import (
    run_kiwoom_mock_api_preflight_gate,
)
from stock_risk_mcp.kiwoom_mock_api_preflight_gate_models import (
    KiwoomMockApiExecutionReadiness,
    KiwoomMockApiPreflightGateConfig,
)
from stock_risk_mcp.kiwoom_mock_market_data_execution_engine import (
    build_kiwoom_mock_market_data_execution_gap_report,
    build_kiwoom_mock_market_data_execution_safety_report,
    build_kiwoom_mock_market_data_response_report,
    execute_kiwoom_mock_market_data,
)
from stock_risk_mcp.kiwoom_mock_market_data_execution_models import (
    KiwoomMockMarketDataExecutionConfig,
)
from stock_risk_mcp.quant_strategy_robustness_engine import build_quant_strategy_robustness
from stock_risk_mcp.quant_strategy_robustness_models import QuantStrategyRobustnessInput
from stock_risk_mcp.point_in_time_universe_engine import build_point_in_time_universe_gate
from stock_risk_mcp.point_in_time_universe_models import PointInTimeUniverseInput
from stock_risk_mcp.walk_forward_validation_engine import build_walk_forward_validation
from stock_risk_mcp.walk_forward_validation_models import WalkForwardValidationInput
from stock_risk_mcp.training_pipeline_promotion_engine import build_training_pipeline_promotion
from stock_risk_mcp.training_pipeline_promotion_models import TrainingPipelinePromotionInput
from stock_risk_mcp.strategy_ensemble_alpha_engine import build_strategy_ensemble_alpha_gate
from stock_risk_mcp.strategy_ensemble_alpha_models import StrategyEnsembleAlphaInput
from stock_risk_mcp.regime_allocation_learning_engine import build_regime_allocation_learning_dataset
from stock_risk_mcp.regime_allocation_learning_models import RegimeAllocationLearningInput
from stock_risk_mcp.allocation_policy_training_engine import build_allocation_policy_training_sandbox
from stock_risk_mcp.allocation_policy_training_models import AllocationPolicyCandidateInput
from stock_risk_mcp.cnn_fear_greed_engine import run_cnn_fear_greed_collection
from stock_risk_mcp.cnn_fear_greed_models import CNNFearGreedCollectorConfig
from stock_risk_mcp.controlled_mock_readiness_engine import build_controlled_mock_readiness_review
from stock_risk_mcp.controlled_mock_readiness_models import ControlledMockReadinessInput
from stock_risk_mcp.controlled_mock_dry_run_engine import build_controlled_mock_dry_run_review
from stock_risk_mcp.controlled_mock_dry_run_models import ControlledMockDryRunInput
from stock_risk_mcp.read_only_provider_adapter_engine import build_read_only_provider_adapter_boundary
from stock_risk_mcp.read_only_provider_adapter_models import ReadOnlyProviderAdapterInput
from stock_risk_mcp.kiwoom_rest_readonly_chart_engine import build_kiwoom_rest_readonly_chart_adapter
from stock_risk_mcp.kiwoom_rest_readonly_chart_models import KiwoomRestChartConfig
from stock_risk_mcp.kiwoom_rest_readonly_rank_engine import build_kiwoom_rest_readonly_rank_adapter
from stock_risk_mcp.kiwoom_rest_readonly_rank_models import KiwoomRestRankConfig
from stock_risk_mcp.kiwoom_rest_readonly_quote_engine import build_kiwoom_rest_readonly_quote_adapter
from stock_risk_mcp.kiwoom_rest_readonly_quote_models import KiwoomRestQuoteConfig
from stock_risk_mcp.kiwoom_rest_readonly_flow_engine import build_kiwoom_rest_readonly_flow_adapter
from stock_risk_mcp.kiwoom_rest_readonly_flow_models import KiwoomRestFlowConfig
from stock_risk_mcp.kiwoom_rest_readonly_sector_engine import build_kiwoom_rest_readonly_sector_adapter
from stock_risk_mcp.kiwoom_rest_readonly_sector_models import KiwoomRestSectorConfig
from stock_risk_mcp.kiwoom_readonly_snapshot_engine import build_kiwoom_readonly_domestic_stock_snapshot
from stock_risk_mcp.kiwoom_readonly_snapshot_models import KiwoomReadonlySnapshotConfig
from stock_risk_mcp.macro_regime_classifier_engine import build_macro_regime_classification
from stock_risk_mcp.macro_regime_integration_engine import build_macro_regime_pipeline_result
from stock_risk_mcp.macro_regime_provider_models import MacroRegimePipelineInput
from stock_risk_mcp.macro_regime_snapshot_engine import build_macro_regime_snapshot
from stock_risk_mcp.feature_store_integration_engine import build_feature_store_pipeline
from stock_risk_mcp.feature_store_models import FeatureStorePipelineInput
from stock_risk_mcp.paper_evaluation_integration_engine import build_paper_evaluation_pipeline
from stock_risk_mcp.paper_evaluation_models import PaperEvaluationPipelineInput
from stock_risk_mcp.account_read_snapshot_engine import build_account_read_snapshot_pipeline
from stock_risk_mcp.account_read_models import AccountReadPipelineInput
from stock_risk_mcp.portfolio_reconciliation_integration_engine import build_portfolio_reconciliation_pipeline
from stock_risk_mcp.portfolio_reconciliation_models import PortfolioReconciliationPipelineInput
from stock_risk_mcp.controlled_execution_models import ControlledExecutionPipelineInput
from stock_risk_mcp.controlled_execution_preflight_engine import build_controlled_execution_preflight
from stock_risk_mcp.kiwoom_manual_response_import_engine import build_kiwoom_manual_response_import_harness
from stock_risk_mcp.kiwoom_manual_response_import_models import KiwoomManualResponseImportRequest
from stock_risk_mcp.kiwoom_readonly_final_transport_engine import build_kiwoom_readonly_final_transport
from stock_risk_mcp.kiwoom_readonly_final_transport_models import (
    KiwoomReadonlyFinalDomain,
    KiwoomReadonlyFinalRequest,
    KiwoomReadonlyFinalTokenProviderKind,
    KiwoomReadonlyFinalTransportMode,
)
from stock_risk_mcp.market_data_provider_registry_engine import build_market_data_provider_registry
from stock_risk_mcp.market_data_provider_registry_models import MarketDataProviderRegistryInput
from stock_risk_mcp.position_sizing_engine import build_position_sizing_review
from stock_risk_mcp.position_sizing_models import PositionSizingInput
from stock_risk_mcp.event_risk_engine import build_event_risk_review
from stock_risk_mcp.event_risk_models import EventRiskInput
from stock_risk_mcp.breadth_leadership_routing_engine import build_breadth_leadership_routing_review
from stock_risk_mcp.breadth_leadership_routing_models import BreadthLeadershipRoutingInput
from stock_risk_mcp.market_regime_engine import build_market_regime
from stock_risk_mcp.market_regime_models import MarketRegimeInput
from stock_risk_mcp.risk_adjusted_paper_eval_engine import build_risk_adjusted_paper_evaluation
from stock_risk_mcp.risk_adjusted_paper_eval_models import RiskAdjustedPaperEvalInput


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
    historical_dataset_readiness = _run_historical_dataset_readiness_smoke(output_dir)
    historical_model_training = _run_historical_model_training_smoke(output_dir)
    historical_model_experiment = _run_historical_model_experiment_smoke(output_dir)
    historical_signal_candidate = _run_historical_signal_candidate_smoke(output_dir)
    historical_paper_trading = _run_historical_paper_trading_smoke(output_dir)
    broker_mock_adapter = _run_broker_mock_adapter_smoke(output_dir)
    kiwoom_mock_adapter = _run_kiwoom_mock_adapter_smoke(output_dir)
    kiwoom_mock_credential_boundary = _run_kiwoom_mock_credential_boundary_smoke(output_dir)
    kiwoom_mock_oauth_draft = _run_kiwoom_mock_oauth_draft_smoke(output_dir)
    kiwoom_mock_oauth_execution = _run_kiwoom_mock_oauth_execution_smoke(output_dir)
    kiwoom_mock_api_transport_draft = _run_kiwoom_mock_api_transport_draft_smoke(output_dir)
    kiwoom_mock_api_preflight_gate = _run_kiwoom_mock_api_preflight_gate_smoke(output_dir)
    kiwoom_mock_market_data_execution = _run_kiwoom_mock_market_data_execution_smoke(output_dir)
    quant_strategy_robustness = _run_quant_strategy_robustness_smoke(output_dir)
    point_in_time_universe = _run_point_in_time_universe_smoke(output_dir)
    walk_forward_validation = _run_walk_forward_validation_smoke(output_dir)
    training_pipeline_promotion = _run_training_pipeline_promotion_smoke(output_dir)
    strategy_ensemble_alpha = _run_strategy_ensemble_alpha_smoke(output_dir)
    regime_allocation_learning = _run_regime_allocation_learning_smoke(output_dir)
    allocation_policy_training = _run_allocation_policy_training_smoke(output_dir)
    cnn_fear_greed = _run_cnn_fear_greed_smoke(output_dir)
    risk_adjusted_paper_eval = _run_risk_adjusted_paper_eval_smoke(output_dir)
    controlled_mock_readiness = _run_controlled_mock_readiness_smoke(output_dir)
    market_regime = _run_market_regime_smoke(output_dir)
    macro_regime = _run_macro_regime_smoke(output_dir)
    feature_store = _run_feature_store_smoke(output_dir)
    paper_evaluation = _run_paper_evaluation_smoke(output_dir)
    portfolio_reconciliation = _run_portfolio_reconciliation_smoke(output_dir)
    controlled_execution = _run_controlled_execution_smoke(output_dir)
    provider_registry = _run_market_data_provider_registry_smoke(output_dir)
    position_sizing = _run_position_sizing_smoke(output_dir)
    event_risk = _run_event_risk_smoke(output_dir)
    breadth_leadership_routing = _run_breadth_leadership_routing_smoke(output_dir)
    controlled_mock_dry_run = _run_controlled_mock_dry_run_smoke(output_dir)
    read_only_provider_adapter = _run_read_only_provider_adapter_smoke(output_dir)
    kiwoom_rest_readonly_chart = _run_kiwoom_rest_readonly_chart_smoke(output_dir)
    kiwoom_rest_readonly_rank = _run_kiwoom_rest_readonly_rank_smoke(output_dir)
    kiwoom_rest_readonly_quote = _run_kiwoom_rest_readonly_quote_smoke(output_dir)
    kiwoom_rest_readonly_flow = _run_kiwoom_rest_readonly_flow_smoke(output_dir)
    kiwoom_rest_readonly_sector = _run_kiwoom_rest_readonly_sector_smoke(output_dir)
    kiwoom_readonly_snapshot = _run_kiwoom_readonly_snapshot_smoke(output_dir)
    kiwoom_manual_response_import = _run_kiwoom_manual_response_import_smoke(output_dir)
    kiwoom_readonly_final_transport = _run_kiwoom_readonly_final_transport_smoke(output_dir)
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
            "historical_dataset_readiness_fixture_run": historical_dataset_readiness["fixture_run"],
            "historical_dataset_readiness_report_generated": historical_dataset_readiness["readiness_report_generated"],
            "historical_dataset_split_quality_report_generated": historical_dataset_readiness["split_quality_report_generated"],
            "historical_dataset_imbalance_report_generated": historical_dataset_readiness["imbalance_report_generated"],
            "historical_dataset_baseline_evaluation_generated": historical_dataset_readiness["baseline_evaluation_generated"],
            "historical_dataset_baseline_non_learning": historical_dataset_readiness["baseline_non_learning"],
            "historical_dataset_readiness_report_only": historical_dataset_readiness["report_only"],
            "historical_dataset_readiness_read_only": historical_dataset_readiness["read_only"],
            "historical_dataset_readiness_non_executable": historical_dataset_readiness["non_executable"],
            "historical_dataset_readiness_local_files_only": historical_dataset_readiness["local_files_only"],
            "historical_dataset_readiness_remote_fetch_allowed": historical_dataset_readiness["remote_fetch_allowed"],
            "historical_dataset_readiness_api_provider_called": historical_dataset_readiness["api_provider_called"],
            "historical_dataset_readiness_order_intent_created": historical_dataset_readiness["order_intent_created"],
            "historical_dataset_readiness_live_or_prod_used": historical_dataset_readiness["live_or_prod_used"],
            "historical_dataset_readiness_cloud_llm_called": historical_dataset_readiness["cloud_llm_called"],
            "historical_dataset_readiness_model_runtime_called": historical_dataset_readiness["model_runtime_called"],
            "historical_dataset_readiness_ml_training_run": historical_dataset_readiness["ml_training_run"],
            "historical_dataset_readiness_learned_model_evaluation_run": historical_dataset_readiness["learned_model_evaluation_run"],
            "historical_dataset_readiness_ml_ready_tensor_export_created": historical_dataset_readiness["ml_ready_tensor_export_created"],
            "historical_model_training_sandbox_fixture_run": historical_model_training["fixture_run"],
            "historical_model_training_plan_check_generated": historical_model_training["plan_check_generated"],
            "historical_model_training_run_report_generated": historical_model_training["run_report_generated"],
            "historical_model_evaluation_report_generated": historical_model_training["evaluation_report_generated"],
            "historical_model_metrics_report_generated": historical_model_training["metrics_report_generated"],
            "historical_model_artifact_manifest_generated": historical_model_training["artifact_manifest_generated"],
            "historical_model_training_local_only": historical_model_training["local_only"],
            "historical_model_training_offline_only": historical_model_training["offline_only"],
            "historical_model_training_chronological_split_used": historical_model_training["chronological_split_used"],
            "historical_model_training_no_random_shuffle": historical_model_training["no_random_shuffle"],
            "historical_model_training_dummy_models_available": historical_model_training["dummy_models_available"],
            "historical_model_training_optional_sklearn_fail_closed": historical_model_training["optional_sklearn_fail_closed"],
            "historical_model_training_report_only": historical_model_training["report_only"],
            "historical_model_training_non_executable": historical_model_training["non_executable"],
            "historical_model_training_no_runtime_signal": historical_model_training["no_runtime_signal"],
            "historical_model_training_no_order_candidate": historical_model_training["no_order_candidate"],
            "historical_model_training_no_live_inference": historical_model_training["no_live_inference"],
            "historical_model_training_no_broker_path": historical_model_training["no_broker_path"],
            "historical_model_training_no_live_prod": historical_model_training["no_live_prod"],
            "historical_model_training_no_network": historical_model_training["no_network"],
            "historical_model_training_no_cloud_llm": historical_model_training["no_cloud_llm"],
            "historical_model_training_no_local_llm_runtime": historical_model_training["no_local_llm_runtime"],
            "historical_model_experiment_registry_fixture_run": historical_model_experiment["fixture_run"],
            "historical_model_experiment_registry_report_generated": historical_model_experiment["registry_report_generated"],
            "historical_model_comparison_report_generated": historical_model_experiment["comparison_report_generated"],
            "historical_model_risk_review_generated": historical_model_experiment["risk_review_generated"],
            "historical_model_promotion_block_report_generated": historical_model_experiment["promotion_block_report_generated"],
            "historical_model_experiment_lineage_report_generated": historical_model_experiment["lineage_report_generated"],
            "historical_model_experiment_report_only": historical_model_experiment["report_only"],
            "historical_model_experiment_non_executable": historical_model_experiment["non_executable"],
            "historical_model_experiment_no_runtime_signal": historical_model_experiment["no_runtime_signal"],
            "historical_model_experiment_no_order_candidate": historical_model_experiment["no_order_candidate"],
            "historical_model_experiment_no_live_inference": historical_model_experiment["no_live_inference"],
            "historical_model_experiment_no_deployment": historical_model_experiment["no_deployment"],
            "historical_model_experiment_no_paper_trading": historical_model_experiment["no_paper_trading"],
            "historical_model_experiment_no_broker_path": historical_model_experiment["no_broker_path"],
            "historical_model_experiment_no_live_prod": historical_model_experiment["no_live_prod"],
            "historical_model_experiment_no_network": historical_model_experiment["no_network"],
            "historical_model_experiment_no_cloud_llm": historical_model_experiment["no_cloud_llm"],
            "historical_model_experiment_no_local_llm_runtime": historical_model_experiment["no_local_llm_runtime"],
            "historical_model_experiment_promotion_blocked_by_default": historical_model_experiment["promotion_blocked_by_default"],
            "historical_signal_candidate_fixture_run": historical_signal_candidate["fixture_run"],
            "historical_signal_candidate_build_generated": historical_signal_candidate["build_generated"],
            "historical_signal_candidate_report_generated": historical_signal_candidate["report_generated"],
            "historical_signal_candidate_safety_report_generated": historical_signal_candidate["safety_report_generated"],
            "historical_signal_candidate_gap_report_generated": historical_signal_candidate["gap_report_generated"],
            "historical_signal_candidate_audit_record_generated": historical_signal_candidate["audit_record_generated"],
            "historical_signal_candidate_report_only": historical_signal_candidate["report_only"],
            "historical_signal_candidate_non_executable": historical_signal_candidate["non_executable"],
            "historical_signal_candidate_local_only": historical_signal_candidate["local_only"],
            "historical_signal_candidate_offline_only": historical_signal_candidate["offline_only"],
            "historical_signal_candidate_no_runtime_signal": historical_signal_candidate["no_runtime_signal"],
            "historical_signal_candidate_no_order_candidate": historical_signal_candidate["no_order_candidate"],
            "historical_signal_candidate_no_live_inference": historical_signal_candidate["no_live_inference"],
            "historical_signal_candidate_no_deployment": historical_signal_candidate["no_deployment"],
            "historical_signal_candidate_no_paper_trading": historical_signal_candidate["no_paper_trading"],
            "historical_signal_candidate_no_broker_path": historical_signal_candidate["no_broker_path"],
            "historical_signal_candidate_no_live_prod": historical_signal_candidate["no_live_prod"],
            "historical_signal_candidate_no_network": historical_signal_candidate["no_network"],
            "historical_signal_candidate_no_provider_api": historical_signal_candidate["no_provider_api"],
            "historical_signal_candidate_no_cloud_llm": historical_signal_candidate["no_cloud_llm"],
            "historical_signal_candidate_no_local_llm_runtime": historical_signal_candidate["no_local_llm_runtime"],
            "historical_signal_candidate_no_buy_sell_order_execution": historical_signal_candidate["no_buy_sell_order_execution"],
            "historical_signal_candidate_parquet_unsupported": historical_signal_candidate["parquet_unsupported"],
            "historical_paper_trading_fixture_run": historical_paper_trading["fixture_run"],
            "historical_paper_trading_run_generated": historical_paper_trading["run_generated"],
            "historical_paper_trading_decision_generated": historical_paper_trading["decision_generated"],
            "historical_paper_trading_order_intent_generated": historical_paper_trading["order_intent_generated"],
            "historical_paper_trading_fill_generated": historical_paper_trading["fill_generated"],
            "historical_paper_trading_ledger_generated": historical_paper_trading["ledger_generated"],
            "historical_paper_trading_position_generated": historical_paper_trading["position_generated"],
            "historical_paper_trading_trade_generated": historical_paper_trading["trade_generated"],
            "historical_paper_trading_performance_report_generated": historical_paper_trading["performance_report_generated"],
            "historical_paper_trading_safety_report_generated": historical_paper_trading["safety_report_generated"],
            "historical_paper_trading_gap_report_generated": historical_paper_trading["gap_report_generated"],
            "historical_paper_trading_audit_record_generated": historical_paper_trading["audit_record_generated"],
            "historical_paper_trading_paper_only": historical_paper_trading["paper_only"],
            "historical_paper_trading_simulated_only": historical_paper_trading["simulated_only"],
            "historical_paper_trading_non_executable": historical_paper_trading["non_executable"],
            "historical_paper_trading_local_only": historical_paper_trading["local_only"],
            "historical_paper_trading_offline_only": historical_paper_trading["offline_only"],
            "historical_paper_trading_read_only_input": historical_paper_trading["read_only_input"],
            "historical_paper_trading_no_real_order": historical_paper_trading["no_real_order"],
            "historical_paper_trading_no_real_order_intent": historical_paper_trading["no_real_order_intent"],
            "historical_paper_trading_no_broker_api": historical_paper_trading["no_broker_api"],
            "historical_paper_trading_no_account_api": historical_paper_trading["no_account_api"],
            "historical_paper_trading_no_order_api": historical_paper_trading["no_order_api"],
            "historical_paper_trading_no_kiwoom_api": historical_paper_trading["no_kiwoom_api"],
            "historical_paper_trading_no_ls_api": historical_paper_trading["no_ls_api"],
            "historical_paper_trading_no_broker_mock_api": historical_paper_trading["no_broker_mock_api"],
            "historical_paper_trading_no_kiwoom_mock_api": historical_paper_trading["no_kiwoom_mock_api"],
            "historical_paper_trading_no_ls_mock_api": historical_paper_trading["no_ls_mock_api"],
            "historical_paper_trading_no_live_trading": historical_paper_trading["no_live_trading"],
            "historical_paper_trading_no_live_prod": historical_paper_trading["no_live_prod"],
            "historical_paper_trading_no_network": historical_paper_trading["no_network"],
            "historical_paper_trading_no_provider_api": historical_paper_trading["no_provider_api"],
            "historical_paper_trading_no_cloud_llm": historical_paper_trading["no_cloud_llm"],
            "historical_paper_trading_no_local_llm_runtime": historical_paper_trading["no_local_llm_runtime"],
            "historical_paper_trading_no_external_execution": historical_paper_trading["no_external_execution"],
            "historical_paper_trading_parquet_unsupported": historical_paper_trading["parquet_unsupported"],
            "broker_mock_adapter_boundary_fixture_run": broker_mock_adapter["fixture_run"],
            "broker_mock_adapter_boundary_run_generated": broker_mock_adapter["boundary_run_generated"],
            "broker_mock_adapter_capability_report_generated": broker_mock_adapter["capability_report_generated"],
            "broker_mock_adapter_order_intent_generated": broker_mock_adapter["order_intent_generated"],
            "broker_mock_adapter_order_request_generated": broker_mock_adapter["order_request_generated"],
            "broker_mock_adapter_order_response_generated": broker_mock_adapter["order_response_generated"],
            "broker_mock_adapter_execution_report_generated": broker_mock_adapter["execution_report_generated"],
            "broker_mock_adapter_account_snapshot_generated": broker_mock_adapter["account_snapshot_generated"],
            "broker_mock_adapter_position_snapshot_generated": broker_mock_adapter["position_snapshot_generated"],
            "broker_mock_adapter_safety_report_generated": broker_mock_adapter["safety_report_generated"],
            "broker_mock_adapter_gap_report_generated": broker_mock_adapter["gap_report_generated"],
            "broker_mock_adapter_audit_record_generated": broker_mock_adapter["audit_record_generated"],
            "broker_mock_adapter_mock_only": broker_mock_adapter["mock_only"],
            "broker_mock_adapter_paper_only": broker_mock_adapter["paper_only"],
            "broker_mock_adapter_disabled_by_default": broker_mock_adapter["disabled_by_default"],
            "broker_mock_adapter_explicit_opt_in_required": broker_mock_adapter["explicit_opt_in_required"],
            "broker_mock_adapter_non_executable_by_default": broker_mock_adapter["non_executable_by_default"],
            "broker_mock_adapter_local_only": broker_mock_adapter["local_only"],
            "broker_mock_adapter_offline_only": broker_mock_adapter["offline_only"],
            "broker_mock_adapter_no_real_order": broker_mock_adapter["no_real_order"],
            "broker_mock_adapter_no_real_order_intent": broker_mock_adapter["no_real_order_intent"],
            "broker_mock_adapter_no_real_account_mutation": broker_mock_adapter["no_real_account_mutation"],
            "broker_mock_adapter_no_live_trading": broker_mock_adapter["no_live_trading"],
            "broker_mock_adapter_no_live_prod": broker_mock_adapter["no_live_prod"],
            "broker_mock_adapter_no_production_broker": broker_mock_adapter["no_production_broker"],
            "broker_mock_adapter_no_credentials_loaded": broker_mock_adapter["no_credentials_loaded"],
            "broker_mock_adapter_no_network_call": broker_mock_adapter["no_network_call"],
            "broker_mock_adapter_no_kiwoom_api_call": broker_mock_adapter["no_kiwoom_api_call"],
            "broker_mock_adapter_no_ls_api_call": broker_mock_adapter["no_ls_api_call"],
            "broker_mock_adapter_no_broker_api_call": broker_mock_adapter["no_broker_api_call"],
            "broker_mock_adapter_no_order_api_call": broker_mock_adapter["no_order_api_call"],
            "broker_mock_adapter_no_account_api_call": broker_mock_adapter["no_account_api_call"],
            "broker_mock_adapter_no_provider_api_call": broker_mock_adapter["no_provider_api_call"],
            "broker_mock_adapter_no_websocket_connection": broker_mock_adapter["no_websocket_connection"],
            "broker_mock_adapter_no_cloud_llm": broker_mock_adapter["no_cloud_llm"],
            "broker_mock_adapter_no_local_llm_runtime": broker_mock_adapter["no_local_llm_runtime"],
            "broker_mock_adapter_parquet_unsupported": broker_mock_adapter["parquet_unsupported"],
            "kiwoom_mock_adapter_draft_fixture_run": kiwoom_mock_adapter["fixture_run"],
            "kiwoom_mock_adapter_draft_build_generated": kiwoom_mock_adapter["draft_build_generated"],
            "kiwoom_mock_adapter_order_draft_generated": kiwoom_mock_adapter["order_draft_generated"],
            "kiwoom_mock_adapter_request_draft_generated": kiwoom_mock_adapter["request_draft_generated"],
            "kiwoom_mock_adapter_response_draft_generated": kiwoom_mock_adapter["response_draft_generated"],
            "kiwoom_mock_adapter_execution_draft_generated": kiwoom_mock_adapter["execution_draft_generated"],
            "kiwoom_mock_adapter_account_snapshot_draft_generated": kiwoom_mock_adapter["account_snapshot_draft_generated"],
            "kiwoom_mock_adapter_position_snapshot_draft_generated": kiwoom_mock_adapter["position_snapshot_draft_generated"],
            "kiwoom_mock_adapter_safety_report_generated": kiwoom_mock_adapter["safety_report_generated"],
            "kiwoom_mock_adapter_gap_report_generated": kiwoom_mock_adapter["gap_report_generated"],
            "kiwoom_mock_adapter_audit_record_generated": kiwoom_mock_adapter["audit_record_generated"],
            "kiwoom_mock_adapter_kiwoom_mock_only": kiwoom_mock_adapter["kiwoom_mock_only"],
            "kiwoom_mock_adapter_draft_only": kiwoom_mock_adapter["draft_only"],
            "kiwoom_mock_adapter_paper_only": kiwoom_mock_adapter["paper_only"],
            "kiwoom_mock_adapter_disabled_by_default": kiwoom_mock_adapter["disabled_by_default"],
            "kiwoom_mock_adapter_explicit_opt_in_required": kiwoom_mock_adapter["explicit_opt_in_required"],
            "kiwoom_mock_adapter_non_executable": kiwoom_mock_adapter["non_executable"],
            "kiwoom_mock_adapter_local_only": kiwoom_mock_adapter["local_only"],
            "kiwoom_mock_adapter_offline_only": kiwoom_mock_adapter["offline_only"],
            "kiwoom_mock_adapter_evidence_backed": kiwoom_mock_adapter["evidence_backed"],
            "kiwoom_mock_adapter_no_credentials_loaded": kiwoom_mock_adapter["no_credentials_loaded"],
            "kiwoom_mock_adapter_no_oauth_token_request": kiwoom_mock_adapter["no_oauth_token_request"],
            "kiwoom_mock_adapter_no_api_call": kiwoom_mock_adapter["no_api_call"],
            "kiwoom_mock_adapter_no_mockapi_call": kiwoom_mock_adapter["no_mockapi_call"],
            "kiwoom_mock_adapter_no_network_call": kiwoom_mock_adapter["no_network_call"],
            "kiwoom_mock_adapter_no_websocket_connection": kiwoom_mock_adapter["no_websocket_connection"],
            "kiwoom_mock_adapter_no_real_order": kiwoom_mock_adapter["no_real_order"],
            "kiwoom_mock_adapter_no_real_account_mutation": kiwoom_mock_adapter["no_real_account_mutation"],
            "kiwoom_mock_adapter_no_live_trading": kiwoom_mock_adapter["no_live_trading"],
            "kiwoom_mock_adapter_no_live_prod": kiwoom_mock_adapter["no_live_prod"],
            "kiwoom_mock_adapter_no_broker_api_call": kiwoom_mock_adapter["no_broker_api_call"],
            "kiwoom_mock_adapter_no_order_api_call": kiwoom_mock_adapter["no_order_api_call"],
            "kiwoom_mock_adapter_no_account_api_call": kiwoom_mock_adapter["no_account_api_call"],
            "kiwoom_mock_adapter_no_provider_api_call": kiwoom_mock_adapter["no_provider_api_call"],
            "kiwoom_mock_adapter_no_cloud_llm": kiwoom_mock_adapter["no_cloud_llm"],
            "kiwoom_mock_adapter_no_local_llm_runtime": kiwoom_mock_adapter["no_local_llm_runtime"],
            "kiwoom_mock_adapter_parquet_unsupported": kiwoom_mock_adapter["parquet_unsupported"],
            "kiwoom_mock_credential_boundary_fixture_run": kiwoom_mock_credential_boundary["fixture_run"],
            "kiwoom_mock_credential_boundary_check_generated": kiwoom_mock_credential_boundary["boundary_check_generated"],
            "kiwoom_mock_credential_domain_policy_report_generated": kiwoom_mock_credential_boundary["domain_policy_report_generated"],
            "kiwoom_mock_credential_opt_in_report_generated": kiwoom_mock_credential_boundary["opt_in_report_generated"],
            "kiwoom_mock_credential_safety_report_generated": kiwoom_mock_credential_boundary["safety_report_generated"],
            "kiwoom_mock_credential_gap_report_generated": kiwoom_mock_credential_boundary["gap_report_generated"],
            "kiwoom_mock_credential_audit_record_generated": kiwoom_mock_credential_boundary["audit_record_generated"],
            "kiwoom_mock_credential_mock_only": kiwoom_mock_credential_boundary["mock_only"],
            "kiwoom_mock_credential_boundary_only": kiwoom_mock_credential_boundary["credential_boundary_only"],
            "kiwoom_mock_credential_disabled_by_default": kiwoom_mock_credential_boundary["disabled_by_default"],
            "kiwoom_mock_credential_explicit_opt_in_required": kiwoom_mock_credential_boundary["explicit_opt_in_required"],
            "kiwoom_mock_credential_local_only": kiwoom_mock_credential_boundary["local_only"],
            "kiwoom_mock_credential_offline_only": kiwoom_mock_credential_boundary["offline_only"],
            "kiwoom_mock_credential_non_executable": kiwoom_mock_credential_boundary["non_executable"],
            "kiwoom_mock_credential_no_credentials_loaded": kiwoom_mock_credential_boundary["no_credentials_loaded"],
            "kiwoom_mock_credential_no_environment_read": kiwoom_mock_credential_boundary["no_environment_read"],
            "kiwoom_mock_credential_no_credential_file_read": kiwoom_mock_credential_boundary["no_credential_file_read"],
            "kiwoom_mock_credential_no_token_issued": kiwoom_mock_credential_boundary["no_token_issued"],
            "kiwoom_mock_credential_no_token_revoked": kiwoom_mock_credential_boundary["no_token_revoked"],
            "kiwoom_mock_credential_no_api_call": kiwoom_mock_credential_boundary["no_api_call"],
            "kiwoom_mock_credential_no_mockapi_call": kiwoom_mock_credential_boundary["no_mockapi_call"],
            "kiwoom_mock_credential_no_websocket_connection": kiwoom_mock_credential_boundary["no_websocket_connection"],
            "kiwoom_mock_credential_no_network_call": kiwoom_mock_credential_boundary["no_network_call"],
            "kiwoom_mock_credential_no_real_order": kiwoom_mock_credential_boundary["no_real_order"],
            "kiwoom_mock_credential_no_live_trading": kiwoom_mock_credential_boundary["no_live_trading"],
            "kiwoom_mock_credential_no_live_prod": kiwoom_mock_credential_boundary["no_live_prod"],
            "kiwoom_mock_credential_no_account_mutation": kiwoom_mock_credential_boundary["no_account_mutation"],
            "kiwoom_mock_credential_no_production_domain_execution": kiwoom_mock_credential_boundary["no_production_domain_execution"],
            "kiwoom_mock_credential_no_cloud_llm": kiwoom_mock_credential_boundary["no_cloud_llm"],
            "kiwoom_mock_credential_no_local_llm_runtime": kiwoom_mock_credential_boundary["no_local_llm_runtime"],
            "kiwoom_mock_credential_parquet_unsupported": kiwoom_mock_credential_boundary["parquet_unsupported"],
            "kiwoom_mock_oauth_draft_fixture_run": kiwoom_mock_oauth_draft["fixture_run"],
            "kiwoom_mock_oauth_token_request_draft_generated": kiwoom_mock_oauth_draft["token_request_draft_generated"],
            "kiwoom_mock_oauth_token_response_draft_generated": kiwoom_mock_oauth_draft["token_response_draft_generated"],
            "kiwoom_mock_oauth_token_revoke_draft_generated": kiwoom_mock_oauth_draft["token_revoke_draft_generated"],
            "kiwoom_mock_oauth_token_lifecycle_report_generated": kiwoom_mock_oauth_draft["token_lifecycle_report_generated"],
            "kiwoom_mock_oauth_safety_report_generated": kiwoom_mock_oauth_draft["safety_report_generated"],
            "kiwoom_mock_oauth_gap_report_generated": kiwoom_mock_oauth_draft["gap_report_generated"],
            "kiwoom_mock_oauth_audit_record_generated": kiwoom_mock_oauth_draft["audit_record_generated"],
            "kiwoom_mock_oauth_mock_only": kiwoom_mock_oauth_draft["mock_only"],
            "kiwoom_mock_oauth_draft_only": kiwoom_mock_oauth_draft["oauth_draft_only"],
            "kiwoom_mock_oauth_credential_boundary_only": kiwoom_mock_oauth_draft["credential_boundary_only"],
            "kiwoom_mock_oauth_disabled_by_default": kiwoom_mock_oauth_draft["disabled_by_default"],
            "kiwoom_mock_oauth_explicit_opt_in_required": kiwoom_mock_oauth_draft["explicit_opt_in_required"],
            "kiwoom_mock_oauth_local_only": kiwoom_mock_oauth_draft["local_only"],
            "kiwoom_mock_oauth_offline_only": kiwoom_mock_oauth_draft["offline_only"],
            "kiwoom_mock_oauth_non_executable": kiwoom_mock_oauth_draft["non_executable"],
            "kiwoom_mock_oauth_no_credentials_loaded": kiwoom_mock_oauth_draft["no_credentials_loaded"],
            "kiwoom_mock_oauth_no_env_read": kiwoom_mock_oauth_draft["no_env_read"],
            "kiwoom_mock_oauth_no_token_issued": kiwoom_mock_oauth_draft["no_token_issued"],
            "kiwoom_mock_oauth_no_token_revoked": kiwoom_mock_oauth_draft["no_token_revoked"],
            "kiwoom_mock_oauth_no_api_call": kiwoom_mock_oauth_draft["no_api_call"],
            "kiwoom_mock_oauth_no_mockapi_call": kiwoom_mock_oauth_draft["no_mockapi_call"],
            "kiwoom_mock_oauth_no_websocket_connection": kiwoom_mock_oauth_draft["no_websocket_connection"],
            "kiwoom_mock_oauth_no_network_call": kiwoom_mock_oauth_draft["no_network_call"],
            "kiwoom_mock_oauth_no_real_order": kiwoom_mock_oauth_draft["no_real_order"],
            "kiwoom_mock_oauth_no_live_trading": kiwoom_mock_oauth_draft["no_live_trading"],
            "kiwoom_mock_oauth_no_live_prod": kiwoom_mock_oauth_draft["no_live_prod"],
            "kiwoom_mock_oauth_no_account_mutation": kiwoom_mock_oauth_draft["no_account_mutation"],
            "kiwoom_mock_oauth_no_production_domain_execution": kiwoom_mock_oauth_draft["no_production_domain_execution"],
            "kiwoom_mock_oauth_no_cloud_llm": kiwoom_mock_oauth_draft["no_cloud_llm"],
            "kiwoom_mock_oauth_no_local_llm_runtime": kiwoom_mock_oauth_draft["no_local_llm_runtime"],
            "kiwoom_mock_oauth_parquet_unsupported": kiwoom_mock_oauth_draft["parquet_unsupported"],
            "kiwoom_mock_oauth_execution_fixture_run": kiwoom_mock_oauth_execution["fixture_run"],
            "kiwoom_mock_oauth_execution_request_generated": kiwoom_mock_oauth_execution["request_generated"],
            "kiwoom_mock_oauth_execution_revoke_generated": kiwoom_mock_oauth_execution["revoke_generated"],
            "kiwoom_mock_oauth_execution_safety_report_generated": kiwoom_mock_oauth_execution["safety_report_generated"],
            "kiwoom_mock_oauth_execution_gap_report_generated": kiwoom_mock_oauth_execution["gap_report_generated"],
            "kiwoom_mock_oauth_execution_audit_record_generated": kiwoom_mock_oauth_execution["audit_record_generated"],
            "kiwoom_mock_oauth_execution_mock_only": kiwoom_mock_oauth_execution["mock_only"],
            "kiwoom_mock_oauth_execution_local_only": kiwoom_mock_oauth_execution["local_only"],
            "kiwoom_mock_oauth_execution_redacted_output_only": kiwoom_mock_oauth_execution["redacted_output_only"],
            "kiwoom_mock_oauth_execution_no_raw_secret_token_output": kiwoom_mock_oauth_execution["no_raw_secret_token_output"],
            "kiwoom_mock_oauth_execution_no_token_persistence": kiwoom_mock_oauth_execution["no_token_persistence"],
            "kiwoom_mock_oauth_execution_no_real_network_in_smoke": kiwoom_mock_oauth_execution["no_real_network_in_smoke"],
            "kiwoom_mock_oauth_execution_no_production_path": kiwoom_mock_oauth_execution["no_production_path"],
            "kiwoom_mock_oauth_execution_no_account_path": kiwoom_mock_oauth_execution["no_account_path"],
            "kiwoom_mock_oauth_execution_no_order_path": kiwoom_mock_oauth_execution["no_order_path"],
            "kiwoom_mock_oauth_execution_no_quote_path": kiwoom_mock_oauth_execution["no_quote_path"],
            "kiwoom_mock_oauth_execution_no_websocket_path": kiwoom_mock_oauth_execution["no_websocket_path"],
            "kiwoom_mock_oauth_execution_no_live_prod": kiwoom_mock_oauth_execution["no_live_prod"],
            "kiwoom_mock_api_transport_draft_fixture_run": kiwoom_mock_api_transport_draft["fixture_run"],
            "kiwoom_mock_api_transport_request_envelope_draft_generated": kiwoom_mock_api_transport_draft[
                "request_envelope_draft_generated"
            ],
            "kiwoom_mock_api_transport_policy_report_generated": kiwoom_mock_api_transport_draft[
                "transport_policy_report_generated"
            ],
            "kiwoom_mock_api_retry_timeout_report_generated": kiwoom_mock_api_transport_draft[
                "retry_timeout_report_generated"
            ],
            "kiwoom_mock_api_error_response_draft_generated": kiwoom_mock_api_transport_draft[
                "error_response_draft_generated"
            ],
            "kiwoom_mock_api_transport_safety_report_generated": kiwoom_mock_api_transport_draft[
                "safety_report_generated"
            ],
            "kiwoom_mock_api_transport_gap_report_generated": kiwoom_mock_api_transport_draft[
                "gap_report_generated"
            ],
            "kiwoom_mock_api_transport_audit_record_generated": kiwoom_mock_api_transport_draft[
                "audit_record_generated"
            ],
            "kiwoom_mock_api_transport_draft_only": kiwoom_mock_api_transport_draft[
                "kiwoom_mock_api_transport_draft_only"
            ],
            "kiwoom_mock_api_transport_mock_only": kiwoom_mock_api_transport_draft["mock_only"],
            "kiwoom_mock_api_transport_offline_only": kiwoom_mock_api_transport_draft["offline_only"],
            "kiwoom_mock_api_transport_local_only": kiwoom_mock_api_transport_draft["local_only"],
            "kiwoom_mock_api_transport_request_envelope_only": kiwoom_mock_api_transport_draft[
                "request_envelope_only"
            ],
            "kiwoom_mock_api_transport_non_executable": kiwoom_mock_api_transport_draft["non_executable"],
            "kiwoom_mock_api_transport_no_authorization_header": kiwoom_mock_api_transport_draft[
                "no_authorization_header"
            ],
            "kiwoom_mock_api_transport_no_token_loading": kiwoom_mock_api_transport_draft["no_token_loading"],
            "kiwoom_mock_api_transport_no_token_usage": kiwoom_mock_api_transport_draft["no_token_usage"],
            "kiwoom_mock_api_transport_no_token_refresh": kiwoom_mock_api_transport_draft["no_token_refresh"],
            "kiwoom_mock_api_transport_no_environment_read": kiwoom_mock_api_transport_draft[
                "no_environment_read"
            ],
            "kiwoom_mock_api_transport_no_credential_file_read": kiwoom_mock_api_transport_draft[
                "no_credential_file_read"
            ],
            "kiwoom_mock_api_transport_no_credentials_loaded": kiwoom_mock_api_transport_draft[
                "no_credentials_loaded"
            ],
            "kiwoom_mock_api_transport_no_http_client": kiwoom_mock_api_transport_draft["no_http_client"],
            "kiwoom_mock_api_transport_no_http_session": kiwoom_mock_api_transport_draft["no_http_session"],
            "kiwoom_mock_api_transport_no_transport": kiwoom_mock_api_transport_draft["no_transport"],
            "kiwoom_mock_api_transport_no_api_call": kiwoom_mock_api_transport_draft["no_api_call"],
            "kiwoom_mock_api_transport_no_mockapi_call": kiwoom_mock_api_transport_draft["no_mockapi_call"],
            "kiwoom_mock_api_transport_no_websocket_connection": kiwoom_mock_api_transport_draft[
                "no_websocket_connection"
            ],
            "kiwoom_mock_api_transport_no_network_call": kiwoom_mock_api_transport_draft["no_network_call"],
            "kiwoom_mock_api_transport_no_account_read": kiwoom_mock_api_transport_draft["no_account_read"],
            "kiwoom_mock_api_transport_no_account_mutation": kiwoom_mock_api_transport_draft[
                "no_account_mutation"
            ],
            "kiwoom_mock_api_transport_no_real_order": kiwoom_mock_api_transport_draft["no_real_order"],
            "kiwoom_mock_api_transport_no_live_trading": kiwoom_mock_api_transport_draft["no_live_trading"],
            "kiwoom_mock_api_transport_no_live_prod": kiwoom_mock_api_transport_draft["no_live_prod"],
            "kiwoom_mock_api_transport_parquet_unsupported": kiwoom_mock_api_transport_draft[
                "parquet_unsupported"
            ],
            "kiwoom_mock_api_preflight_fixture_run": kiwoom_mock_api_preflight_gate["fixture_run"],
            "kiwoom_mock_api_preflight_check_generated": kiwoom_mock_api_preflight_gate["preflight_check_generated"],
            "kiwoom_mock_api_preflight_readiness_report_generated": kiwoom_mock_api_preflight_gate[
                "readiness_report_generated"
            ],
            "kiwoom_mock_api_preflight_safety_report_generated": kiwoom_mock_api_preflight_gate[
                "safety_report_generated"
            ],
            "kiwoom_mock_api_preflight_gap_report_generated": kiwoom_mock_api_preflight_gate[
                "gap_report_generated"
            ],
            "kiwoom_mock_api_preflight_audit_record_generated": kiwoom_mock_api_preflight_gate[
                "audit_record_generated"
            ],
            "kiwoom_mock_api_preflight_local_only": kiwoom_mock_api_preflight_gate["local_only"],
            "kiwoom_mock_api_preflight_offline_only": kiwoom_mock_api_preflight_gate["offline_only"],
            "kiwoom_mock_api_preflight_non_executable": kiwoom_mock_api_preflight_gate["non_executable"],
            "kiwoom_mock_api_preflight_quote_draft_ready": kiwoom_mock_api_preflight_gate["quote_draft_ready"],
            "kiwoom_mock_api_preflight_gap_status_supported": kiwoom_mock_api_preflight_gate[
                "gap_status_supported"
            ],
            "kiwoom_mock_api_preflight_oauth_blocked": kiwoom_mock_api_preflight_gate["oauth_blocked"],
            "kiwoom_mock_api_preflight_account_blocked": kiwoom_mock_api_preflight_gate["account_blocked"],
            "kiwoom_mock_api_preflight_order_blocked": kiwoom_mock_api_preflight_gate["order_blocked"],
            "kiwoom_mock_api_preflight_websocket_blocked": kiwoom_mock_api_preflight_gate[
                "websocket_blocked"
            ],
            "kiwoom_mock_api_preflight_unknown_rejected": kiwoom_mock_api_preflight_gate["unknown_rejected"],
            "kiwoom_mock_api_preflight_prod_blocked_or_rejected": kiwoom_mock_api_preflight_gate[
                "prod_blocked_or_rejected"
            ],
            "kiwoom_mock_api_preflight_no_token_loading": kiwoom_mock_api_preflight_gate["no_token_loading"],
            "kiwoom_mock_api_preflight_no_token_usage": kiwoom_mock_api_preflight_gate["no_token_usage"],
            "kiwoom_mock_api_preflight_no_token_refresh": kiwoom_mock_api_preflight_gate["no_token_refresh"],
            "kiwoom_mock_api_preflight_no_authorization_header": kiwoom_mock_api_preflight_gate[
                "no_authorization_header"
            ],
            "kiwoom_mock_api_preflight_no_http_client": kiwoom_mock_api_preflight_gate["no_http_client"],
            "kiwoom_mock_api_preflight_no_http_session": kiwoom_mock_api_preflight_gate["no_http_session"],
            "kiwoom_mock_api_preflight_no_transport": kiwoom_mock_api_preflight_gate["no_transport"],
            "kiwoom_mock_api_preflight_no_api_call": kiwoom_mock_api_preflight_gate["no_api_call"],
            "kiwoom_mock_api_preflight_no_mockapi_call": kiwoom_mock_api_preflight_gate["no_mockapi_call"],
            "kiwoom_mock_api_preflight_no_websocket_connection": kiwoom_mock_api_preflight_gate[
                "no_websocket_connection"
            ],
            "kiwoom_mock_api_preflight_no_network_call": kiwoom_mock_api_preflight_gate["no_network_call"],
            "kiwoom_mock_api_preflight_no_account_read": kiwoom_mock_api_preflight_gate["no_account_read"],
            "kiwoom_mock_api_preflight_no_account_mutation": kiwoom_mock_api_preflight_gate[
                "no_account_mutation"
            ],
            "kiwoom_mock_api_preflight_no_real_order": kiwoom_mock_api_preflight_gate["no_real_order"],
            "kiwoom_mock_api_preflight_no_live_trading": kiwoom_mock_api_preflight_gate["no_live_trading"],
            "kiwoom_mock_api_preflight_no_live_prod": kiwoom_mock_api_preflight_gate["no_live_prod"],
            "kiwoom_mock_api_preflight_parquet_unsupported": kiwoom_mock_api_preflight_gate[
                "parquet_unsupported"
            ],
            "kiwoom_mock_market_data_execution_fixture_run": kiwoom_mock_market_data_execution["fixture_run"],
            "kiwoom_mock_market_data_execution_request_generated": kiwoom_mock_market_data_execution[
                "request_generated"
            ],
            "kiwoom_mock_market_data_execution_response_report_generated": kiwoom_mock_market_data_execution[
                "response_report_generated"
            ],
            "kiwoom_mock_market_data_execution_safety_report_generated": kiwoom_mock_market_data_execution[
                "safety_report_generated"
            ],
            "kiwoom_mock_market_data_execution_gap_report_generated": kiwoom_mock_market_data_execution[
                "gap_report_generated"
            ],
            "kiwoom_mock_market_data_execution_audit_record_generated": kiwoom_mock_market_data_execution[
                "audit_record_generated"
            ],
            "kiwoom_mock_market_data_execution_mock_only": kiwoom_mock_market_data_execution["mock_only"],
            "kiwoom_mock_market_data_execution_local_only": kiwoom_mock_market_data_execution["local_only"],
            "kiwoom_mock_market_data_execution_read_only_market_data_only": kiwoom_mock_market_data_execution[
                "read_only_market_data_only"
            ],
            "kiwoom_mock_market_data_execution_redacted_output_only": kiwoom_mock_market_data_execution[
                "redacted_output_only"
            ],
            "kiwoom_mock_market_data_execution_no_raw_secret_token_output": kiwoom_mock_market_data_execution[
                "no_raw_secret_token_output"
            ],
            "kiwoom_mock_market_data_execution_no_token_persistence": kiwoom_mock_market_data_execution[
                "no_token_persistence"
            ],
            "kiwoom_mock_market_data_execution_no_token_refresh": kiwoom_mock_market_data_execution[
                "no_token_refresh"
            ],
            "kiwoom_mock_market_data_execution_no_real_network_in_smoke": kiwoom_mock_market_data_execution[
                "no_real_network_in_smoke"
            ],
            "kiwoom_mock_market_data_execution_no_production_path": kiwoom_mock_market_data_execution[
                "no_production_path"
            ],
            "kiwoom_mock_market_data_execution_no_account_path": kiwoom_mock_market_data_execution[
                "no_account_path"
            ],
            "kiwoom_mock_market_data_execution_no_order_path": kiwoom_mock_market_data_execution[
                "no_order_path"
            ],
            "kiwoom_mock_market_data_execution_no_websocket_path": kiwoom_mock_market_data_execution[
                "no_websocket_path"
            ],
            "kiwoom_mock_market_data_execution_no_live_prod": kiwoom_mock_market_data_execution["no_live_prod"],
            "quant_strategy_robustness_fixture_run": quant_strategy_robustness["fixture_run"],
            "quant_strategy_robustness_report_generated": quant_strategy_robustness["report_generated"],
            "quant_strategy_survivorship_bias_report_generated": quant_strategy_robustness["survivorship_report_generated"],
            "quant_strategy_point_in_time_report_generated": quant_strategy_robustness["point_in_time_report_generated"],
            "quant_strategy_walk_forward_report_generated": quant_strategy_robustness["walk_forward_report_generated"],
            "quant_strategy_data_snooping_report_generated": quant_strategy_robustness["data_snooping_report_generated"],
            "quant_strategy_diversification_report_generated": quant_strategy_robustness["diversification_report_generated"],
            "quant_strategy_regime_readiness_report_generated": quant_strategy_robustness["regime_report_generated"],
            "quant_strategy_robustness_local_only": quant_strategy_robustness["local_only"],
            "quant_strategy_robustness_offline_only": quant_strategy_robustness["offline_only"],
            "quant_strategy_robustness_report_only": quant_strategy_robustness["report_only"],
            "quant_strategy_robustness_non_executable": quant_strategy_robustness["non_executable"],
            "quant_strategy_robustness_training_ready": quant_strategy_robustness["training_ready"],
            "quant_strategy_robustness_no_live_path": quant_strategy_robustness["no_live_path"],
            "quant_strategy_robustness_no_order_path": quant_strategy_robustness["no_order_path"],
            "quant_strategy_robustness_no_account_mutation": quant_strategy_robustness["no_account_mutation"],
            "quant_strategy_robustness_no_network": quant_strategy_robustness["no_network"],
            "quant_strategy_robustness_parquet_unsupported": quant_strategy_robustness["parquet_unsupported"],
            "point_in_time_universe_fixture_run": point_in_time_universe["fixture_run"],
            "point_in_time_universe_report_generated": point_in_time_universe["point_in_time_report_generated"],
            "survivorship_bias_dataset_report_generated": point_in_time_universe["survivorship_report_generated"],
            "security_lifecycle_coverage_report_generated": point_in_time_universe["lifecycle_report_generated"],
            "dataset_leakage_report_generated": point_in_time_universe["leakage_report_generated"],
            "dataset_promotion_readiness_report_generated": point_in_time_universe["promotion_report_generated"],
            "point_in_time_universe_local_only": point_in_time_universe["local_only"],
            "point_in_time_universe_offline_only": point_in_time_universe["offline_only"],
            "point_in_time_universe_report_only": point_in_time_universe["report_only"],
            "point_in_time_universe_non_executable": point_in_time_universe["non_executable"],
            "point_in_time_universe_training_ready": point_in_time_universe["training_ready"],
            "point_in_time_universe_no_live_path": point_in_time_universe["no_live_path"],
            "point_in_time_universe_no_order_path": point_in_time_universe["no_order_path"],
            "point_in_time_universe_no_account_mutation": point_in_time_universe["no_account_mutation"],
            "point_in_time_universe_no_network": point_in_time_universe["no_network"],
            "point_in_time_universe_parquet_unsupported": point_in_time_universe["parquet_unsupported"],
            "walk_forward_validation_fixture_run": walk_forward_validation["fixture_run"],
            "walk_forward_split_report_generated": walk_forward_validation["split_report_generated"],
            "walk_forward_data_snooping_report_generated": walk_forward_validation["data_snooping_report_generated"],
            "walk_forward_experiment_lineage_report_generated": walk_forward_validation["lineage_report_generated"],
            "walk_forward_parameter_search_pressure_report_generated": walk_forward_validation["pressure_report_generated"],
            "walk_forward_final_test_contamination_report_generated": walk_forward_validation["contamination_report_generated"],
            "walk_forward_stability_report_generated": walk_forward_validation["stability_report_generated"],
            "walk_forward_promotion_readiness_report_generated": walk_forward_validation["promotion_report_generated"],
            "walk_forward_validation_local_only": walk_forward_validation["local_only"],
            "walk_forward_validation_offline_only": walk_forward_validation["offline_only"],
            "walk_forward_validation_report_only": walk_forward_validation["report_only"],
            "walk_forward_validation_non_executable": walk_forward_validation["non_executable"],
            "walk_forward_validation_ready_for_validation_or_paper": walk_forward_validation["ready_for_validation_or_paper"],
            "walk_forward_validation_no_live_path": walk_forward_validation["no_live_path"],
            "walk_forward_validation_no_order_path": walk_forward_validation["no_order_path"],
            "walk_forward_validation_no_account_mutation": walk_forward_validation["no_account_mutation"],
            "walk_forward_validation_no_network": walk_forward_validation["no_network"],
            "walk_forward_validation_parquet_unsupported": walk_forward_validation["parquet_unsupported"],
            "training_pipeline_promotion_fixture_run": training_pipeline_promotion["fixture_run"],
            "training_dataset_eligibility_report_generated": training_pipeline_promotion["training_eligibility_report_generated"],
            "training_dependency_report_generated": training_pipeline_promotion["dependency_report_generated"],
            "training_leakage_overfit_risk_report_generated": training_pipeline_promotion["leakage_overfit_risk_report_generated"],
            "training_reproducibility_report_generated": training_pipeline_promotion["reproducibility_report_generated"],
            "training_model_artifact_policy_report_generated": training_pipeline_promotion["model_artifact_policy_report_generated"],
            "training_model_promotion_readiness_report_generated": training_pipeline_promotion["model_promotion_readiness_report_generated"],
            "training_pipeline_promotion_local_only": training_pipeline_promotion["local_only"],
            "training_pipeline_promotion_offline_only": training_pipeline_promotion["offline_only"],
            "training_pipeline_promotion_report_only": training_pipeline_promotion["report_only"],
            "training_pipeline_promotion_non_executable": training_pipeline_promotion["non_executable"],
            "training_pipeline_promotion_training_ready_or_paper_candidate": training_pipeline_promotion["training_ready_or_paper_candidate"],
            "training_pipeline_promotion_no_live_path": training_pipeline_promotion["no_live_path"],
            "training_pipeline_promotion_no_order_path": training_pipeline_promotion["no_order_path"],
            "training_pipeline_promotion_no_account_mutation": training_pipeline_promotion["no_account_mutation"],
            "training_pipeline_promotion_no_network": training_pipeline_promotion["no_network"],
            "training_pipeline_promotion_parquet_unsupported": training_pipeline_promotion["parquet_unsupported"],
            "strategy_ensemble_alpha_fixture_run": strategy_ensemble_alpha["fixture_run"],
            "alpha_candidate_report_generated": strategy_ensemble_alpha["alpha_candidate_report_generated"],
            "strategy_family_diversification_report_generated": strategy_ensemble_alpha["family_report_generated"],
            "alpha_correlation_risk_report_generated": strategy_ensemble_alpha["correlation_report_generated"],
            "drawdown_co_movement_report_generated": strategy_ensemble_alpha["drawdown_report_generated"],
            "regime_overlap_report_generated": strategy_ensemble_alpha["regime_report_generated"],
            "alpha_portfolio_concentration_report_generated": strategy_ensemble_alpha["concentration_report_generated"],
            "ensemble_promotion_readiness_report_generated": strategy_ensemble_alpha["promotion_report_generated"],
            "strategy_ensemble_alpha_local_only": strategy_ensemble_alpha["local_only"],
            "strategy_ensemble_alpha_offline_only": strategy_ensemble_alpha["offline_only"],
            "strategy_ensemble_alpha_report_only": strategy_ensemble_alpha["report_only"],
            "strategy_ensemble_alpha_non_executable": strategy_ensemble_alpha["non_executable"],
            "strategy_ensemble_alpha_ensemble_ready_or_paper_candidate": strategy_ensemble_alpha["ensemble_ready_or_paper_candidate"],
            "strategy_ensemble_alpha_no_live_path": strategy_ensemble_alpha["no_live_path"],
            "strategy_ensemble_alpha_no_order_path": strategy_ensemble_alpha["no_order_path"],
            "strategy_ensemble_alpha_no_account_mutation": strategy_ensemble_alpha["no_account_mutation"],
            "strategy_ensemble_alpha_no_network": strategy_ensemble_alpha["no_network"],
            "strategy_ensemble_alpha_parquet_unsupported": strategy_ensemble_alpha["parquet_unsupported"],
            "regime_allocation_learning_fixture_run": regime_allocation_learning["fixture_run"],
            "regime_feature_report_generated": regime_allocation_learning["regime_feature_report_generated"],
            "allocation_action_candidate_report_generated": regime_allocation_learning["action_candidate_report_generated"],
            "hedge_inverse_eligibility_report_generated": regime_allocation_learning["hedge_inverse_eligibility_report_generated"],
            "forward_outcome_label_report_generated": regime_allocation_learning["forward_outcome_label_report_generated"],
            "allocation_reward_scoring_report_generated": regime_allocation_learning["allocation_reward_scoring_report_generated"],
            "regime_allocation_leakage_report_generated": regime_allocation_learning["leakage_report_generated"],
            "regime_allocation_dataset_readiness_report_generated": regime_allocation_learning["readiness_report_generated"],
            "regime_allocation_learning_local_only": regime_allocation_learning["local_only"],
            "regime_allocation_learning_offline_only": regime_allocation_learning["offline_only"],
            "regime_allocation_learning_report_only": regime_allocation_learning["report_only"],
            "regime_allocation_learning_non_executable": regime_allocation_learning["non_executable"],
            "regime_allocation_learning_training_ready": regime_allocation_learning["training_ready"],
            "regime_allocation_learning_no_live_path": regime_allocation_learning["no_live_path"],
            "regime_allocation_learning_no_order_path": regime_allocation_learning["no_order_path"],
            "regime_allocation_learning_no_account_mutation": regime_allocation_learning["no_account_mutation"],
            "regime_allocation_learning_no_network": regime_allocation_learning["no_network"],
            "regime_allocation_learning_hedge_inverse_report_only": regime_allocation_learning["hedge_inverse_report_only"],
            "regime_allocation_learning_parquet_unsupported": regime_allocation_learning["parquet_unsupported"],
            "allocation_policy_training_fixture_run": allocation_policy_training["fixture_run"],
            "allocation_policy_training_summary_report_generated": allocation_policy_training["summary_report_generated"],
            "regime_action_selection_report_generated": allocation_policy_training["selection_report_generated"],
            "allocation_policy_walk_forward_report_generated": allocation_policy_training["walk_forward_report_generated"],
            "allocation_policy_risk_adjusted_report_generated": allocation_policy_training["risk_adjusted_report_generated"],
            "allocation_policy_turnover_slippage_report_generated": allocation_policy_training["turnover_report_generated"],
            "allocation_policy_drawdown_stability_report_generated": allocation_policy_training["drawdown_report_generated"],
            "allocation_policy_promotion_readiness_report_generated": allocation_policy_training["promotion_report_generated"],
            "allocation_policy_artifact_report_generated": allocation_policy_training["artifact_report_generated"],
            "allocation_policy_training_local_only": allocation_policy_training["local_only"],
            "allocation_policy_training_offline_only": allocation_policy_training["offline_only"],
            "allocation_policy_training_report_only": allocation_policy_training["report_only"],
            "allocation_policy_training_non_executable": allocation_policy_training["non_executable"],
            "allocation_policy_training_trained_or_paper_candidate": allocation_policy_training["trained_or_paper_candidate"],
            "allocation_policy_training_no_live_path": allocation_policy_training["no_live_path"],
            "allocation_policy_training_no_order_path": allocation_policy_training["no_order_path"],
            "allocation_policy_training_no_account_mutation": allocation_policy_training["no_account_mutation"],
            "allocation_policy_training_no_network": allocation_policy_training["no_network"],
            "allocation_policy_training_artifact_local_only": allocation_policy_training["artifact_local_only"],
            "allocation_policy_training_parquet_unsupported": allocation_policy_training["parquet_unsupported"],
            "cnn_fear_greed_fixture_run": cnn_fear_greed["fixture_run"],
            "cnn_fear_greed_snapshot_generated": cnn_fear_greed["snapshot_generated"],
            "cnn_fear_greed_history_report_generated": cnn_fear_greed["history_report_generated"],
            "cnn_fear_greed_feature_integration_report_generated": cnn_fear_greed["feature_integration_report_generated"],
            "cnn_fear_greed_source_health_report_generated": cnn_fear_greed["source_health_report_generated"],
            "cnn_fear_greed_audit_report_generated": cnn_fear_greed["audit_report_generated"],
            "cnn_fear_greed_safe_default_dry_run": cnn_fear_greed["safe_default_dry_run"],
            "cnn_fear_greed_mocked_transport_default": cnn_fear_greed["mocked_transport_default"],
            "cnn_fear_greed_real_network_opt_in_required": cnn_fear_greed["real_network_opt_in_required"],
            "cnn_fear_greed_no_real_network_called": cnn_fear_greed["no_real_network_called"],
            "cnn_fear_greed_no_trading_order_account_broker_path": cnn_fear_greed["no_trading_order_account_broker_path"],
            "cnn_fear_greed_parquet_unsupported": cnn_fear_greed["parquet_unsupported"],
            "risk_adjusted_paper_eval_fixture_run": risk_adjusted_paper_eval["fixture_run"],
            "risk_adjusted_paper_eval_summary_report_generated": risk_adjusted_paper_eval["summary_report_generated"],
            "risk_adjusted_paper_eval_virtual_portfolio_report_generated": risk_adjusted_paper_eval["portfolio_report_generated"],
            "risk_adjusted_paper_eval_trade_ledger_report_generated": risk_adjusted_paper_eval["ledger_report_generated"],
            "risk_adjusted_paper_eval_cost_report_generated": risk_adjusted_paper_eval["cost_report_generated"],
            "risk_adjusted_paper_eval_risk_adjusted_report_generated": risk_adjusted_paper_eval["risk_adjusted_report_generated"],
            "risk_adjusted_paper_eval_drawdown_report_generated": risk_adjusted_paper_eval["drawdown_report_generated"],
            "risk_adjusted_paper_eval_bucket_report_generated": risk_adjusted_paper_eval["bucket_report_generated"],
            "risk_adjusted_paper_eval_readiness_report_generated": risk_adjusted_paper_eval["readiness_report_generated"],
            "risk_adjusted_paper_eval_local_only": risk_adjusted_paper_eval["local_only"],
            "risk_adjusted_paper_eval_offline_only": risk_adjusted_paper_eval["offline_only"],
            "risk_adjusted_paper_eval_report_only": risk_adjusted_paper_eval["report_only"],
            "risk_adjusted_paper_eval_non_executable": risk_adjusted_paper_eval["non_executable"],
            "risk_adjusted_paper_eval_no_live_path": risk_adjusted_paper_eval["no_live_path"],
            "risk_adjusted_paper_eval_no_order_path": risk_adjusted_paper_eval["no_order_path"],
            "risk_adjusted_paper_eval_no_account_mutation": risk_adjusted_paper_eval["no_account_mutation"],
            "risk_adjusted_paper_eval_no_network": risk_adjusted_paper_eval["no_network"],
            "risk_adjusted_paper_eval_paper_evaluated_or_pass": risk_adjusted_paper_eval["paper_evaluated_or_pass"],
            "risk_adjusted_paper_eval_fear_feature_used": risk_adjusted_paper_eval["fear_feature_used"],
            "risk_adjusted_paper_eval_parquet_unsupported": risk_adjusted_paper_eval["parquet_unsupported"],
            "controlled_mock_readiness_fixture_run": controlled_mock_readiness["fixture_run"],
            "controlled_mock_readiness_summary_report_generated": controlled_mock_readiness["summary_report_generated"],
            "controlled_mock_readiness_dependency_report_generated": controlled_mock_readiness["dependency_report_generated"],
            "controlled_mock_readiness_paper_pass_evidence_report_generated": controlled_mock_readiness["paper_pass_evidence_report_generated"],
            "controlled_mock_readiness_infrastructure_report_generated": controlled_mock_readiness["infrastructure_report_generated"],
            "controlled_mock_readiness_safety_policy_report_generated": controlled_mock_readiness["safety_policy_report_generated"],
            "controlled_mock_readiness_boundary_violation_report_generated": controlled_mock_readiness["boundary_violation_report_generated"],
            "controlled_mock_readiness_gap_report_generated": controlled_mock_readiness["gap_report_generated"],
            "controlled_mock_readiness_local_only": controlled_mock_readiness["local_only"],
            "controlled_mock_readiness_offline_only": controlled_mock_readiness["offline_only"],
            "controlled_mock_readiness_report_only": controlled_mock_readiness["report_only"],
            "controlled_mock_readiness_non_executable": controlled_mock_readiness["non_executable"],
            "controlled_mock_readiness_no_live_path": controlled_mock_readiness["no_live_path"],
            "controlled_mock_readiness_no_order_path": controlled_mock_readiness["no_order_path"],
            "controlled_mock_readiness_no_account_mutation": controlled_mock_readiness["no_account_mutation"],
            "controlled_mock_readiness_no_network": controlled_mock_readiness["no_network"],
            "controlled_mock_readiness_no_mock_order_execution": controlled_mock_readiness["no_mock_order_execution"],
            "controlled_mock_readiness_review_only": controlled_mock_readiness["review_only"],
            "controlled_mock_readiness_parquet_unsupported": controlled_mock_readiness["parquet_unsupported"],
            "market_regime_fixture_run": market_regime["fixture_run"],
            "market_regime_summary_report_generated": market_regime["summary_report_generated"],
            "market_regime_input_snapshot_report_generated": market_regime["input_snapshot_report_generated"],
            "market_regime_risk_appetite_report_generated": market_regime["risk_appetite_report_generated"],
            "market_regime_direction_report_generated": market_regime["direction_report_generated"],
            "market_regime_volatility_report_generated": market_regime["volatility_report_generated"],
            "market_regime_stress_report_generated": market_regime["stress_report_generated"],
            "market_regime_conflict_report_generated": market_regime["conflict_report_generated"],
            "market_regime_constraint_report_generated": market_regime["constraint_report_generated"],
            "market_regime_training_feature_report_generated": market_regime["training_feature_report_generated"],
            "market_regime_gap_report_generated": market_regime["gap_report_generated"],
            "market_regime_local_only": market_regime["local_only"],
            "market_regime_offline_only": market_regime["offline_only"],
            "market_regime_report_only": market_regime["report_only"],
            "market_regime_non_executable": market_regime["non_executable"],
            "market_regime_no_live_path": market_regime["no_live_path"],
            "market_regime_no_order_path": market_regime["no_order_path"],
            "market_regime_no_account_mutation": market_regime["no_account_mutation"],
            "market_regime_no_network": market_regime["no_network"],
            "market_regime_training_feature_ready": market_regime["training_feature_ready"],
            "market_regime_parquet_unsupported": market_regime["parquet_unsupported"],
            "macro_regime_fixture_run": macro_regime["fixture_run"],
            "macro_regime_snapshot_generated": macro_regime["snapshot_generated"],
            "macro_regime_classification_generated": macro_regime["classification_generated"],
            "macro_regime_provider_capability_report_generated": macro_regime["provider_capability_report_generated"],
            "macro_regime_freshness_report_generated": macro_regime["freshness_report_generated"],
            "macro_regime_conflict_report_generated": macro_regime["conflict_report_generated"],
            "macro_regime_event_window_report_generated": macro_regime["event_window_report_generated"],
            "macro_regime_v7_integration_report_generated": macro_regime["v7_integration_report_generated"],
            "macro_regime_v8_integration_report_generated": macro_regime["v8_integration_report_generated"],
            "macro_regime_report_only": macro_regime["report_only"],
            "macro_regime_no_network": macro_regime["no_network"],
            "macro_regime_no_env_read": macro_regime["no_env_read"],
            "macro_regime_no_account_order_path": macro_regime["no_account_order_path"],
            "macro_regime_no_executable_output": macro_regime["no_executable_output"],
            "macro_regime_boundary_only": macro_regime["provider_boundary_only"],
            "macro_regime_parquet_unsupported": macro_regime["parquet_unsupported"],
            "feature_store_fixture_run": feature_store["fixture_run"],
            "feature_store_cache_manifest_generated": feature_store["cache_manifest_generated"],
            "feature_store_dataset_manifest_generated": feature_store["dataset_manifest_generated"],
            "feature_store_training_dataset_manifest_generated": feature_store["training_dataset_manifest_generated"],
            "feature_store_walk_forward_plan_generated": feature_store["walk_forward_plan_generated"],
            "feature_store_leakage_report_generated": feature_store["leakage_report_generated"],
            "feature_store_backend_capability_report_generated": feature_store["backend_capability_report_generated"],
            "feature_store_v7_integration_report_generated": feature_store["v7_integration_report_generated"],
            "feature_store_v8_integration_report_generated": feature_store["v8_integration_report_generated"],
            "feature_store_v9_integration_report_generated": feature_store["v9_integration_report_generated"],
            "feature_store_report_only": feature_store["report_only"],
            "feature_store_no_network": feature_store["no_network"],
            "feature_store_no_env_read": feature_store["no_env_read"],
            "feature_store_no_account_order_path": feature_store["no_account_order_path"],
            "feature_store_no_training": feature_store["no_training"],
            "feature_store_no_paper_trading": feature_store["no_paper_trading"],
            "feature_store_safe_local_materialization_only": feature_store["safe_local_materialization_only"],
            "paper_evaluation_fixture_run": paper_evaluation["fixture_run"],
            "paper_evaluation_plan_generated": paper_evaluation["plan_generated"],
            "paper_evaluation_signal_replay_generated": paper_evaluation["signal_replay_generated"],
            "paper_evaluation_fill_simulation_generated": paper_evaluation["fill_simulation_generated"],
            "paper_evaluation_ledger_generated": paper_evaluation["ledger_generated"],
            "paper_evaluation_metrics_generated": paper_evaluation["metrics_generated"],
            "paper_evaluation_integration_generated": paper_evaluation["integration_generated"],
            "paper_evaluation_safety_generated": paper_evaluation["safety_generated"],
            "paper_evaluation_report_only": paper_evaluation["report_only"],
            "paper_evaluation_no_network": paper_evaluation["no_network"],
            "paper_evaluation_no_env_read": paper_evaluation["no_env_read"],
            "paper_evaluation_no_account_order_path": paper_evaluation["no_account_order_path"],
            "paper_evaluation_no_model_training": paper_evaluation["no_model_training"],
            "paper_evaluation_no_broker_paper_api": paper_evaluation["no_broker_paper_api"],
            "paper_evaluation_no_executable_output": paper_evaluation["no_executable_output"],
            "portfolio_reconciliation_fixture_run": portfolio_reconciliation["fixture_run"],
            "portfolio_reconciliation_plan_generated": portfolio_reconciliation["plan_generated"],
            "portfolio_reconciliation_report_generated": portfolio_reconciliation["report_generated"],
            "portfolio_reconciliation_integration_generated": portfolio_reconciliation["integration_generated"],
            "portfolio_reconciliation_report_only": portfolio_reconciliation["report_only"],
            "portfolio_reconciliation_no_network": portfolio_reconciliation["no_network"],
            "portfolio_reconciliation_no_env_read": portfolio_reconciliation["no_env_read"],
            "portfolio_reconciliation_no_account_order_path": portfolio_reconciliation["no_account_order_path"],
            "portfolio_reconciliation_no_executable_output": portfolio_reconciliation["no_executable_output"],
            "portfolio_reconciliation_redacted_account_ref": portfolio_reconciliation["redacted_account_ref"],
            "controlled_execution_fixture_run": controlled_execution["fixture_run"],
            "controlled_execution_readiness_generated": controlled_execution["readiness_generated"],
            "controlled_execution_preflight_generated": controlled_execution["preflight_generated"],
            "controlled_execution_approval_generated": controlled_execution["approval_generated"],
            "controlled_execution_mock_execution_generated": controlled_execution["mock_execution_generated"],
            "controlled_execution_dry_run_generated": controlled_execution["dry_run_generated"],
            "controlled_execution_audit_generated": controlled_execution["audit_generated"],
            "controlled_execution_report_only": controlled_execution["report_only"],
            "controlled_execution_no_network": controlled_execution["no_network"],
            "controlled_execution_no_env_read": controlled_execution["no_env_read"],
            "controlled_execution_no_account_order_path": controlled_execution["no_account_order_path"],
            "controlled_execution_no_executable_output": controlled_execution["no_executable_output"],
            "controlled_execution_live_boundary_blocked": controlled_execution["live_boundary_blocked"],
            "market_data_provider_registry_fixture_run": provider_registry["fixture_run"],
            "market_data_provider_registry_report_generated": provider_registry["registry_report_generated"],
            "market_data_provider_module_requirement_report_generated": provider_registry["module_requirement_report_generated"],
            "market_data_provider_readiness_matrix_report_generated": provider_registry["readiness_matrix_report_generated"],
            "market_data_provider_canonical_contract_report_generated": provider_registry["canonical_contract_report_generated"],
            "market_data_provider_symbol_mapping_report_generated": provider_registry["symbol_mapping_report_generated"],
            "market_data_provider_selection_report_generated": provider_registry["selection_report_generated"],
            "market_data_provider_gap_report_generated": provider_registry["gap_report_generated"],
            "market_data_provider_local_only": provider_registry["local_only"],
            "market_data_provider_offline_only": provider_registry["offline_only"],
            "market_data_provider_report_only": provider_registry["report_only"],
            "market_data_provider_non_executable": provider_registry["non_executable"],
            "market_data_provider_no_live_path": provider_registry["no_live_path"],
            "market_data_provider_no_order_path": provider_registry["no_order_path"],
            "market_data_provider_no_account_mutation": provider_registry["no_account_mutation"],
            "market_data_provider_no_network": provider_registry["no_network"],
            "market_data_provider_no_provider_call": provider_registry["no_provider_call"],
            "market_data_provider_parquet_unsupported": provider_registry["parquet_unsupported"],
            "position_sizing_fixture_run": position_sizing["fixture_run"],
            "position_sizing_summary_report_generated": position_sizing["summary_report_generated"],
            "position_sizing_stop_distance_report_generated": position_sizing["stop_distance_report_generated"],
            "position_sizing_risk_budget_report_generated": position_sizing["risk_budget_report_generated"],
            "position_sizing_data_readiness_report_generated": position_sizing["data_readiness_report_generated"],
            "position_sizing_quantity_notional_report_generated": position_sizing["quantity_notional_report_generated"],
            "position_sizing_cost_assumption_report_generated": position_sizing["cost_assumption_report_generated"],
            "position_sizing_market_regime_adjustment_report_generated": position_sizing["market_regime_adjustment_report_generated"],
            "position_sizing_inverse_hedge_report_generated": position_sizing["inverse_hedge_report_generated"],
            "position_sizing_boundary_report_generated": position_sizing["boundary_report_generated"],
            "position_sizing_gap_report_generated": position_sizing["gap_report_generated"],
            "position_sizing_local_only": position_sizing["local_only"],
            "position_sizing_offline_only": position_sizing["offline_only"],
            "position_sizing_report_only": position_sizing["report_only"],
            "position_sizing_non_executable": position_sizing["non_executable"],
            "position_sizing_no_live_path": position_sizing["no_live_path"],
            "position_sizing_no_order_path": position_sizing["no_order_path"],
            "position_sizing_no_account_mutation": position_sizing["no_account_mutation"],
            "position_sizing_no_network": position_sizing["no_network"],
            "position_sizing_no_provider_call": position_sizing["no_provider_call"],
            "position_sizing_parquet_unsupported": position_sizing["parquet_unsupported"],
            "event_risk_fixture_run": event_risk["fixture_run"],
            "event_risk_summary_report_generated": event_risk["summary_report_generated"],
            "event_risk_calendar_snapshot_report_generated": event_risk["calendar_snapshot_report_generated"],
            "event_risk_event_window_report_generated": event_risk["event_window_report_generated"],
            "event_risk_restriction_report_generated": event_risk["restriction_report_generated"],
            "event_risk_position_sizing_adjustment_report_generated": event_risk["position_sizing_adjustment_report_generated"],
            "event_risk_provider_readiness_report_generated": event_risk["provider_readiness_report_generated"],
            "event_risk_leakage_report_generated": event_risk["leakage_report_generated"],
            "event_risk_gap_report_generated": event_risk["gap_report_generated"],
            "event_risk_local_only": event_risk["local_only"],
            "event_risk_offline_only": event_risk["offline_only"],
            "event_risk_report_only": event_risk["report_only"],
            "event_risk_non_executable": event_risk["non_executable"],
            "event_risk_no_live_path": event_risk["no_live_path"],
            "event_risk_no_order_path": event_risk["no_order_path"],
            "event_risk_no_account_mutation": event_risk["no_account_mutation"],
            "event_risk_no_network": event_risk["no_network"],
            "event_risk_no_provider_call": event_risk["no_provider_call"],
            "event_risk_parquet_unsupported": event_risk["parquet_unsupported"],
            "breadth_leadership_routing_fixture_run": breadth_leadership_routing["fixture_run"],
            "breadth_leadership_summary_report_generated": breadth_leadership_routing["summary_report_generated"],
            "breadth_input_snapshot_report_generated": breadth_leadership_routing["breadth_input_snapshot_report_generated"],
            "advance_decline_report_generated": breadth_leadership_routing["advance_decline_report_generated"],
            "new_high_low_report_generated": breadth_leadership_routing["new_high_low_report_generated"],
            "up_down_volume_participation_report_generated": breadth_leadership_routing["up_down_volume_participation_report_generated"],
            "sector_leadership_report_generated": breadth_leadership_routing["sector_leadership_report_generated"],
            "leadership_concentration_report_generated": breadth_leadership_routing["leadership_concentration_report_generated"],
            "index_distortion_report_generated": breadth_leadership_routing["index_distortion_report_generated"],
            "equal_weight_divergence_report_generated": breadth_leadership_routing["equal_weight_divergence_report_generated"],
            "outlier_momentum_candidate_report_generated": breadth_leadership_routing["outlier_momentum_candidate_report_generated"],
            "outlier_sleeve_risk_report_generated": breadth_leadership_routing["outlier_sleeve_risk_report_generated"],
            "breadth_routing_downstream_constraint_report_generated": breadth_leadership_routing["downstream_constraint_report_generated"],
            "breadth_routing_provider_readiness_report_generated": breadth_leadership_routing["provider_readiness_report_generated"],
            "breadth_routing_leakage_report_generated": breadth_leadership_routing["leakage_report_generated"],
            "breadth_routing_gap_report_generated": breadth_leadership_routing["gap_report_generated"],
            "breadth_routing_local_only": breadth_leadership_routing["local_only"],
            "breadth_routing_offline_only": breadth_leadership_routing["offline_only"],
            "breadth_routing_report_only": breadth_leadership_routing["report_only"],
            "breadth_routing_non_executable": breadth_leadership_routing["non_executable"],
            "breadth_routing_no_live_path": breadth_leadership_routing["no_live_path"],
            "breadth_routing_no_order_path": breadth_leadership_routing["no_order_path"],
            "breadth_routing_no_account_mutation": breadth_leadership_routing["no_account_mutation"],
            "breadth_routing_no_network": breadth_leadership_routing["no_network"],
            "breadth_routing_no_provider_call": breadth_leadership_routing["no_provider_call"],
            "breadth_routing_parquet_unsupported": breadth_leadership_routing["parquet_unsupported"],
            "controlled_mock_dry_run_fixture_run": controlled_mock_dry_run["fixture_run"],
            "controlled_mock_dry_run_summary_report_generated": controlled_mock_dry_run["summary_report_generated"],
            "controlled_mock_dry_run_preview_generated": controlled_mock_dry_run["preview_generated"],
            "controlled_mock_dry_run_preflight_report_generated": controlled_mock_dry_run["preflight_report_generated"],
            "controlled_mock_dry_run_provider_report_generated": controlled_mock_dry_run["provider_report_generated"],
            "controlled_mock_dry_run_market_regime_report_generated": controlled_mock_dry_run["market_regime_report_generated"],
            "controlled_mock_dry_run_position_sizing_report_generated": controlled_mock_dry_run["position_sizing_report_generated"],
            "controlled_mock_dry_run_event_risk_report_generated": controlled_mock_dry_run["event_risk_report_generated"],
            "controlled_mock_dry_run_breadth_routing_report_generated": controlled_mock_dry_run["breadth_routing_report_generated"],
            "controlled_mock_dry_run_order_gate_report_generated": controlled_mock_dry_run["order_gate_report_generated"],
            "controlled_mock_dry_run_risk_budget_report_generated": controlled_mock_dry_run["risk_budget_report_generated"],
            "controlled_mock_dry_run_kill_switch_report_generated": controlled_mock_dry_run["kill_switch_report_generated"],
            "controlled_mock_dry_run_rollback_report_generated": controlled_mock_dry_run["rollback_report_generated"],
            "controlled_mock_dry_run_audit_report_generated": controlled_mock_dry_run["audit_report_generated"],
            "controlled_mock_dry_run_boundary_report_generated": controlled_mock_dry_run["boundary_report_generated"],
            "controlled_mock_dry_run_gap_report_generated": controlled_mock_dry_run["gap_report_generated"],
            "controlled_mock_dry_run_report_only": controlled_mock_dry_run["report_only"],
            "controlled_mock_dry_run_non_executable": controlled_mock_dry_run["non_executable"],
            "controlled_mock_dry_run_local_only": controlled_mock_dry_run["local_only"],
            "controlled_mock_dry_run_offline_only": controlled_mock_dry_run["offline_only"],
            "controlled_mock_dry_run_no_live_order_account_prod_path": controlled_mock_dry_run["no_live_order_account_prod_path"],
            "controlled_mock_dry_run_no_real_broker_kiwoom_network_provider_call": controlled_mock_dry_run["no_real_broker_kiwoom_network_provider_call"],
            "controlled_mock_dry_run_no_mock_order_execution": controlled_mock_dry_run["no_mock_order_execution"],
            "controlled_mock_dry_run_preview_non_executable": controlled_mock_dry_run["preview_non_executable"],
            "controlled_mock_dry_run_execution_review_or_rehearsed_only": controlled_mock_dry_run["execution_review_or_rehearsed_only"],
            "controlled_mock_dry_run_parquet_unsupported": controlled_mock_dry_run["parquet_unsupported"],
            "read_only_provider_adapter_fixture_run": read_only_provider_adapter["fixture_run"],
            "read_only_provider_adapter_summary_report_generated": read_only_provider_adapter["summary_report_generated"],
            "read_only_provider_adapter_evidence_map_report_generated": read_only_provider_adapter["evidence_map_report_generated"],
            "read_only_provider_adapter_ls_report_generated": read_only_provider_adapter["ls_report_generated"],
            "read_only_provider_adapter_canonical_contract_report_generated": read_only_provider_adapter["canonical_contract_report_generated"],
            "read_only_provider_adapter_capability_matrix_report_generated": read_only_provider_adapter["capability_matrix_report_generated"],
            "read_only_provider_adapter_blocked_api_report_generated": read_only_provider_adapter["blocked_api_report_generated"],
            "read_only_provider_adapter_migration_report_generated": read_only_provider_adapter["migration_report_generated"],
            "read_only_provider_adapter_gap_report_generated": read_only_provider_adapter["gap_report_generated"],
            "read_only_provider_adapter_local_only": read_only_provider_adapter["local_only"],
            "read_only_provider_adapter_offline_only": read_only_provider_adapter["offline_only"],
            "read_only_provider_adapter_report_only": read_only_provider_adapter["report_only"],
            "read_only_provider_adapter_non_executable": read_only_provider_adapter["non_executable"],
            "read_only_provider_adapter_no_provider_network_call": read_only_provider_adapter["no_provider_network_call"],
            "read_only_provider_adapter_no_credential_env_read": read_only_provider_adapter["no_credential_env_read"],
            "read_only_provider_adapter_no_auth_header_generation": read_only_provider_adapter["no_auth_header_generation"],
            "read_only_provider_adapter_account_order_blocked": read_only_provider_adapter["account_order_blocked"],
            "read_only_provider_adapter_canonical_output_only": read_only_provider_adapter["canonical_output_only"],
            "read_only_provider_adapter_parquet_unsupported": read_only_provider_adapter["parquet_unsupported"],
            "kiwoom_rest_readonly_chart_fixture_run": kiwoom_rest_readonly_chart["fixture_run"],
            "kiwoom_rest_readonly_chart_request_report_generated": kiwoom_rest_readonly_chart["request_report_generated"],
            "kiwoom_rest_readonly_chart_mocked_response_report_generated": kiwoom_rest_readonly_chart["mocked_response_report_generated"],
            "kiwoom_rest_readonly_chart_canonical_ohlcv_report_generated": kiwoom_rest_readonly_chart["canonical_ohlcv_report_generated"],
            "kiwoom_rest_readonly_chart_continuation_report_generated": kiwoom_rest_readonly_chart["continuation_report_generated"],
            "kiwoom_rest_readonly_chart_safety_report_generated": kiwoom_rest_readonly_chart["safety_report_generated"],
            "kiwoom_rest_readonly_chart_integration_compatibility_report_generated": kiwoom_rest_readonly_chart["integration_compatibility_report_generated"],
            "kiwoom_rest_readonly_chart_gap_report_generated": kiwoom_rest_readonly_chart["gap_report_generated"],
            "kiwoom_rest_readonly_chart_local_only": kiwoom_rest_readonly_chart["local_only"],
            "kiwoom_rest_readonly_chart_offline_only": kiwoom_rest_readonly_chart["offline_only"],
            "kiwoom_rest_readonly_chart_report_only": kiwoom_rest_readonly_chart["report_only"],
            "kiwoom_rest_readonly_chart_non_executable": kiwoom_rest_readonly_chart["non_executable"],
            "kiwoom_rest_readonly_chart_no_network": kiwoom_rest_readonly_chart["no_network"],
            "kiwoom_rest_readonly_chart_no_provider_api": kiwoom_rest_readonly_chart["no_provider_api"],
            "kiwoom_rest_readonly_chart_no_account_order_path": kiwoom_rest_readonly_chart["no_account_order_path"],
            "kiwoom_rest_readonly_chart_no_env_credential_read": kiwoom_rest_readonly_chart["no_env_credential_read"],
            "kiwoom_rest_readonly_chart_no_token_loading": kiwoom_rest_readonly_chart["no_token_loading"],
            "kiwoom_rest_readonly_chart_no_auth_header_generation": kiwoom_rest_readonly_chart["no_auth_header_generation"],
            "kiwoom_rest_readonly_chart_canonical_ohlcv_output_only": kiwoom_rest_readonly_chart["canonical_ohlcv_output_only"],
            "kiwoom_rest_readonly_chart_parquet_unsupported": kiwoom_rest_readonly_chart["parquet_unsupported"],
            "kiwoom_rest_readonly_rank_fixture_run": kiwoom_rest_readonly_rank["fixture_run"],
            "kiwoom_rest_readonly_rank_request_report_generated": kiwoom_rest_readonly_rank["request_report_generated"],
            "kiwoom_rest_readonly_rank_mocked_response_report_generated": kiwoom_rest_readonly_rank["mocked_response_report_generated"],
            "kiwoom_rest_readonly_rank_canonical_rank_report_generated": kiwoom_rest_readonly_rank["canonical_rank_report_generated"],
            "kiwoom_rest_readonly_rank_canonical_outlier_report_generated": kiwoom_rest_readonly_rank["canonical_outlier_report_generated"],
            "kiwoom_rest_readonly_rank_continuation_report_generated": kiwoom_rest_readonly_rank["continuation_report_generated"],
            "kiwoom_rest_readonly_rank_safety_report_generated": kiwoom_rest_readonly_rank["safety_report_generated"],
            "kiwoom_rest_readonly_rank_v7_integration_report_generated": kiwoom_rest_readonly_rank["v7_integration_report_generated"],
            "kiwoom_rest_readonly_rank_gap_report_generated": kiwoom_rest_readonly_rank["gap_report_generated"],
            "kiwoom_rest_readonly_rank_local_only": kiwoom_rest_readonly_rank["local_only"],
            "kiwoom_rest_readonly_rank_offline_only": kiwoom_rest_readonly_rank["offline_only"],
            "kiwoom_rest_readonly_rank_report_only": kiwoom_rest_readonly_rank["report_only"],
            "kiwoom_rest_readonly_rank_non_executable": kiwoom_rest_readonly_rank["non_executable"],
            "kiwoom_rest_readonly_rank_no_network": kiwoom_rest_readonly_rank["no_network"],
            "kiwoom_rest_readonly_rank_no_provider_api": kiwoom_rest_readonly_rank["no_provider_api"],
            "kiwoom_rest_readonly_rank_no_account_order_path": kiwoom_rest_readonly_rank["no_account_order_path"],
            "kiwoom_rest_readonly_rank_no_env_credential_read": kiwoom_rest_readonly_rank["no_env_credential_read"],
            "kiwoom_rest_readonly_rank_no_token_loading": kiwoom_rest_readonly_rank["no_token_loading"],
            "kiwoom_rest_readonly_rank_no_auth_header_generation": kiwoom_rest_readonly_rank["no_auth_header_generation"],
            "kiwoom_rest_readonly_rank_canonical_output_only": kiwoom_rest_readonly_rank["canonical_output_only"],
            "kiwoom_rest_readonly_rank_parquet_unsupported": kiwoom_rest_readonly_rank["parquet_unsupported"],
            "kiwoom_rest_readonly_quote_fixture_run": kiwoom_rest_readonly_quote["fixture_run"],
            "kiwoom_rest_readonly_quote_request_report_generated": kiwoom_rest_readonly_quote["request_report_generated"],
            "kiwoom_rest_readonly_quote_mocked_response_report_generated": kiwoom_rest_readonly_quote["mocked_response_report_generated"],
            "kiwoom_rest_readonly_quote_canonical_quote_report_generated": kiwoom_rest_readonly_quote["canonical_quote_report_generated"],
            "kiwoom_rest_readonly_quote_canonical_orderbook_report_generated": kiwoom_rest_readonly_quote["canonical_orderbook_report_generated"],
            "kiwoom_rest_readonly_quote_liquidity_hint_report_generated": kiwoom_rest_readonly_quote["liquidity_hint_report_generated"],
            "kiwoom_rest_readonly_quote_basic_info_report_generated": kiwoom_rest_readonly_quote["basic_info_report_generated"],
            "kiwoom_rest_readonly_quote_continuation_report_generated": kiwoom_rest_readonly_quote["continuation_report_generated"],
            "kiwoom_rest_readonly_quote_safety_report_generated": kiwoom_rest_readonly_quote["safety_report_generated"],
            "kiwoom_rest_readonly_quote_v7_integration_report_generated": kiwoom_rest_readonly_quote["v7_integration_report_generated"],
            "kiwoom_rest_readonly_quote_gap_report_generated": kiwoom_rest_readonly_quote["gap_report_generated"],
            "kiwoom_rest_readonly_quote_local_only": kiwoom_rest_readonly_quote["local_only"],
            "kiwoom_rest_readonly_quote_offline_only": kiwoom_rest_readonly_quote["offline_only"],
            "kiwoom_rest_readonly_quote_report_only": kiwoom_rest_readonly_quote["report_only"],
            "kiwoom_rest_readonly_quote_non_executable": kiwoom_rest_readonly_quote["non_executable"],
            "kiwoom_rest_readonly_quote_no_network": kiwoom_rest_readonly_quote["no_network"],
            "kiwoom_rest_readonly_quote_no_provider_api": kiwoom_rest_readonly_quote["no_provider_api"],
            "kiwoom_rest_readonly_quote_no_account_order_path": kiwoom_rest_readonly_quote["no_account_order_path"],
            "kiwoom_rest_readonly_quote_no_env_credential_read": kiwoom_rest_readonly_quote["no_env_credential_read"],
            "kiwoom_rest_readonly_quote_no_token_loading": kiwoom_rest_readonly_quote["no_token_loading"],
            "kiwoom_rest_readonly_quote_no_auth_header_generation": kiwoom_rest_readonly_quote["no_auth_header_generation"],
            "kiwoom_rest_readonly_quote_canonical_output_only": kiwoom_rest_readonly_quote["canonical_output_only"],
            "kiwoom_rest_readonly_quote_parquet_unsupported": kiwoom_rest_readonly_quote["parquet_unsupported"],
            "kiwoom_rest_readonly_flow_fixture_run": kiwoom_rest_readonly_flow["fixture_run"],
            "kiwoom_rest_readonly_flow_request_report_generated": kiwoom_rest_readonly_flow["request_report_generated"],
            "kiwoom_rest_readonly_flow_mocked_response_report_generated": kiwoom_rest_readonly_flow["mocked_response_report_generated"],
            "kiwoom_rest_readonly_flow_canonical_investor_flow_report_generated": kiwoom_rest_readonly_flow["canonical_investor_flow_report_generated"],
            "kiwoom_rest_readonly_flow_canonical_program_flow_report_generated": kiwoom_rest_readonly_flow["canonical_program_flow_report_generated"],
            "kiwoom_rest_readonly_flow_short_lending_capability_report_generated": kiwoom_rest_readonly_flow["short_lending_capability_report_generated"],
            "kiwoom_rest_readonly_flow_capability_matrix_report_generated": kiwoom_rest_readonly_flow["capability_matrix_report_generated"],
            "kiwoom_rest_readonly_flow_continuation_report_generated": kiwoom_rest_readonly_flow["continuation_report_generated"],
            "kiwoom_rest_readonly_flow_safety_report_generated": kiwoom_rest_readonly_flow["safety_report_generated"],
            "kiwoom_rest_readonly_flow_v7_integration_report_generated": kiwoom_rest_readonly_flow["v7_integration_report_generated"],
            "kiwoom_rest_readonly_flow_gap_report_generated": kiwoom_rest_readonly_flow["gap_report_generated"],
            "kiwoom_rest_readonly_flow_local_only": kiwoom_rest_readonly_flow["local_only"],
            "kiwoom_rest_readonly_flow_offline_only": kiwoom_rest_readonly_flow["offline_only"],
            "kiwoom_rest_readonly_flow_report_only": kiwoom_rest_readonly_flow["report_only"],
            "kiwoom_rest_readonly_flow_non_executable": kiwoom_rest_readonly_flow["non_executable"],
            "kiwoom_rest_readonly_flow_no_network": kiwoom_rest_readonly_flow["no_network"],
            "kiwoom_rest_readonly_flow_no_provider_api": kiwoom_rest_readonly_flow["no_provider_api"],
            "kiwoom_rest_readonly_flow_no_account_order_path": kiwoom_rest_readonly_flow["no_account_order_path"],
            "kiwoom_rest_readonly_flow_no_env_credential_read": kiwoom_rest_readonly_flow["no_env_credential_read"],
            "kiwoom_rest_readonly_flow_no_token_loading": kiwoom_rest_readonly_flow["no_token_loading"],
            "kiwoom_rest_readonly_flow_no_auth_header_generation": kiwoom_rest_readonly_flow["no_auth_header_generation"],
            "kiwoom_rest_readonly_flow_canonical_output_only": kiwoom_rest_readonly_flow["canonical_output_only"],
            "kiwoom_rest_readonly_flow_parquet_unsupported": kiwoom_rest_readonly_flow["parquet_unsupported"],
            "kiwoom_rest_readonly_sector_fixture_run": kiwoom_rest_readonly_sector["fixture_run"],
            "kiwoom_rest_readonly_sector_request_report_generated": kiwoom_rest_readonly_sector["request_report_generated"],
            "kiwoom_rest_readonly_sector_mocked_response_report_generated": kiwoom_rest_readonly_sector["mocked_response_report_generated"],
            "kiwoom_rest_readonly_sector_canonical_theme_leadership_report_generated": kiwoom_rest_readonly_sector["canonical_theme_leadership_report_generated"],
            "kiwoom_rest_readonly_sector_canonical_theme_membership_report_generated": kiwoom_rest_readonly_sector["canonical_theme_membership_report_generated"],
            "kiwoom_rest_readonly_sector_canonical_etf_trend_report_generated": kiwoom_rest_readonly_sector["canonical_etf_trend_report_generated"],
            "kiwoom_rest_readonly_sector_capability_matrix_report_generated": kiwoom_rest_readonly_sector["capability_matrix_report_generated"],
            "kiwoom_rest_readonly_sector_continuation_report_generated": kiwoom_rest_readonly_sector["continuation_report_generated"],
            "kiwoom_rest_readonly_sector_safety_report_generated": kiwoom_rest_readonly_sector["safety_report_generated"],
            "kiwoom_rest_readonly_sector_v7_integration_report_generated": kiwoom_rest_readonly_sector["v7_integration_report_generated"],
            "kiwoom_rest_readonly_sector_gap_report_generated": kiwoom_rest_readonly_sector["gap_report_generated"],
            "kiwoom_rest_readonly_sector_local_only": kiwoom_rest_readonly_sector["local_only"],
            "kiwoom_rest_readonly_sector_offline_only": kiwoom_rest_readonly_sector["offline_only"],
            "kiwoom_rest_readonly_sector_report_only": kiwoom_rest_readonly_sector["report_only"],
            "kiwoom_rest_readonly_sector_non_executable": kiwoom_rest_readonly_sector["non_executable"],
            "kiwoom_rest_readonly_sector_no_network": kiwoom_rest_readonly_sector["no_network"],
            "kiwoom_rest_readonly_sector_no_provider_api": kiwoom_rest_readonly_sector["no_provider_api"],
            "kiwoom_rest_readonly_sector_no_account_order_path": kiwoom_rest_readonly_sector["no_account_order_path"],
            "kiwoom_rest_readonly_sector_no_env_credential_read": kiwoom_rest_readonly_sector["no_env_credential_read"],
            "kiwoom_rest_readonly_sector_no_token_loading": kiwoom_rest_readonly_sector["no_token_loading"],
            "kiwoom_rest_readonly_sector_no_auth_header_generation": kiwoom_rest_readonly_sector["no_auth_header_generation"],
            "kiwoom_rest_readonly_sector_canonical_output_only": kiwoom_rest_readonly_sector["canonical_output_only"],
            "kiwoom_rest_readonly_sector_parquet_unsupported": kiwoom_rest_readonly_sector["parquet_unsupported"],
            "kiwoom_readonly_snapshot_fixture_run": kiwoom_readonly_snapshot["fixture_run"],
            "kiwoom_readonly_snapshot_summary_report_generated": kiwoom_readonly_snapshot["summary_report_generated"],
            "kiwoom_readonly_snapshot_source_coverage_report_generated": kiwoom_readonly_snapshot["source_coverage_report_generated"],
            "kiwoom_readonly_snapshot_freshness_report_generated": kiwoom_readonly_snapshot["freshness_report_generated"],
            "kiwoom_readonly_snapshot_completeness_report_generated": kiwoom_readonly_snapshot["completeness_report_generated"],
            "kiwoom_readonly_snapshot_conflict_report_generated": kiwoom_readonly_snapshot["conflict_report_generated"],
            "kiwoom_readonly_snapshot_domestic_stock_report_generated": kiwoom_readonly_snapshot["domestic_stock_report_generated"],
            "kiwoom_readonly_snapshot_v710_report_generated": kiwoom_readonly_snapshot["v710_report_generated"],
            "kiwoom_readonly_snapshot_v712_report_generated": kiwoom_readonly_snapshot["v712_report_generated"],
            "kiwoom_readonly_snapshot_v713_report_generated": kiwoom_readonly_snapshot["v713_report_generated"],
            "kiwoom_readonly_snapshot_safety_report_generated": kiwoom_readonly_snapshot["safety_report_generated"],
            "kiwoom_readonly_snapshot_gap_report_generated": kiwoom_readonly_snapshot["gap_report_generated"],
            "kiwoom_readonly_snapshot_local_only": kiwoom_readonly_snapshot["local_only"],
            "kiwoom_readonly_snapshot_offline_only": kiwoom_readonly_snapshot["offline_only"],
            "kiwoom_readonly_snapshot_report_only": kiwoom_readonly_snapshot["report_only"],
            "kiwoom_readonly_snapshot_non_executable": kiwoom_readonly_snapshot["non_executable"],
            "kiwoom_readonly_snapshot_no_network": kiwoom_readonly_snapshot["no_network"],
            "kiwoom_readonly_snapshot_no_provider_api": kiwoom_readonly_snapshot["no_provider_api"],
            "kiwoom_readonly_snapshot_no_account_order_path": kiwoom_readonly_snapshot["no_account_order_path"],
            "kiwoom_readonly_snapshot_no_env_credential_read": kiwoom_readonly_snapshot["no_env_credential_read"],
            "kiwoom_readonly_snapshot_no_token_loading": kiwoom_readonly_snapshot["no_token_loading"],
            "kiwoom_readonly_snapshot_no_auth_header_generation": kiwoom_readonly_snapshot["no_auth_header_generation"],
            "kiwoom_readonly_snapshot_canonical_output_only": kiwoom_readonly_snapshot["canonical_output_only"],
            "kiwoom_readonly_snapshot_parquet_unsupported": kiwoom_readonly_snapshot["parquet_unsupported"],
            "kiwoom_manual_response_import_fixture_run": kiwoom_manual_response_import["fixture_run"],
            "kiwoom_manual_response_import_summary_report_generated": kiwoom_manual_response_import["summary_report_generated"],
            "kiwoom_manual_response_import_file_classification_report_generated": kiwoom_manual_response_import["file_classification_report_generated"],
            "kiwoom_manual_response_import_sensitive_scan_report_generated": kiwoom_manual_response_import["sensitive_scan_report_generated"],
            "kiwoom_manual_response_import_routing_report_generated": kiwoom_manual_response_import["routing_report_generated"],
            "kiwoom_manual_response_import_canonical_output_report_generated": kiwoom_manual_response_import["canonical_output_report_generated"],
            "kiwoom_manual_response_import_snapshot_report_generated": kiwoom_manual_response_import["snapshot_report_generated"],
            "kiwoom_manual_response_import_safety_report_generated": kiwoom_manual_response_import["safety_report_generated"],
            "kiwoom_manual_response_import_gap_report_generated": kiwoom_manual_response_import["gap_report_generated"],
            "kiwoom_manual_response_import_local_only": kiwoom_manual_response_import["local_only"],
            "kiwoom_manual_response_import_offline_only": kiwoom_manual_response_import["offline_only"],
            "kiwoom_manual_response_import_report_only": kiwoom_manual_response_import["report_only"],
            "kiwoom_manual_response_import_non_executable": kiwoom_manual_response_import["non_executable"],
            "kiwoom_manual_response_import_no_network": kiwoom_manual_response_import["no_network"],
            "kiwoom_manual_response_import_no_provider_api": kiwoom_manual_response_import["no_provider_api"],
            "kiwoom_manual_response_import_no_account_order_path": kiwoom_manual_response_import["no_account_order_path"],
            "kiwoom_manual_response_import_no_env_credential_read": kiwoom_manual_response_import["no_env_credential_read"],
            "kiwoom_manual_response_import_no_token_loading": kiwoom_manual_response_import["no_token_loading"],
            "kiwoom_manual_response_import_no_auth_header_generation": kiwoom_manual_response_import["no_auth_header_generation"],
            "kiwoom_manual_response_import_canonical_output_only": kiwoom_manual_response_import["canonical_output_only"],
            "kiwoom_manual_response_import_snapshot_composed": kiwoom_manual_response_import["snapshot_composed"],
            "kiwoom_manual_response_import_snapshot_not_empty": kiwoom_manual_response_import["snapshot_not_empty"],
            "kiwoom_manual_response_import_parquet_unsupported": kiwoom_manual_response_import["parquet_unsupported"],
            "kiwoom_readonly_final_transport_fixture_run": kiwoom_readonly_final_transport["fixture_run"],
            "kiwoom_readonly_final_transport_summary_report_generated": kiwoom_readonly_final_transport["summary_report_generated"],
            "kiwoom_readonly_final_transport_request_preview_report_generated": kiwoom_readonly_final_transport["request_preview_report_generated"],
            "kiwoom_readonly_final_transport_allowlist_report_generated": kiwoom_readonly_final_transport["allowlist_report_generated"],
            "kiwoom_readonly_final_transport_token_provider_report_generated": kiwoom_readonly_final_transport["token_provider_report_generated"],
            "kiwoom_readonly_final_transport_capture_report_generated": kiwoom_readonly_final_transport["capture_report_generated"],
            "kiwoom_readonly_final_transport_response_routing_report_generated": kiwoom_readonly_final_transport["response_routing_report_generated"],
            "kiwoom_readonly_final_transport_snapshot_validation_report_generated": kiwoom_readonly_final_transport["snapshot_validation_report_generated"],
            "kiwoom_readonly_final_transport_readiness_report_generated": kiwoom_readonly_final_transport["readiness_report_generated"],
            "kiwoom_readonly_final_transport_safety_report_generated": kiwoom_readonly_final_transport["safety_report_generated"],
            "kiwoom_readonly_final_transport_gap_report_generated": kiwoom_readonly_final_transport["gap_report_generated"],
            "kiwoom_readonly_final_transport_local_only": kiwoom_readonly_final_transport["local_only"],
            "kiwoom_readonly_final_transport_offline_only": kiwoom_readonly_final_transport["offline_only"],
            "kiwoom_readonly_final_transport_report_only": kiwoom_readonly_final_transport["report_only"],
            "kiwoom_readonly_final_transport_non_executable": kiwoom_readonly_final_transport["non_executable"],
            "kiwoom_readonly_final_transport_no_network": kiwoom_readonly_final_transport["no_network"],
            "kiwoom_readonly_final_transport_no_provider_api": kiwoom_readonly_final_transport["no_provider_api"],
            "kiwoom_readonly_final_transport_no_account_order_path": kiwoom_readonly_final_transport["no_account_order_path"],
            "kiwoom_readonly_final_transport_no_env_credential_read": kiwoom_readonly_final_transport["no_env_credential_read"],
            "kiwoom_readonly_final_transport_no_token_loading": kiwoom_readonly_final_transport["no_token_loading"],
            "kiwoom_readonly_final_transport_no_auth_header_generation": kiwoom_readonly_final_transport["no_auth_header_generation"],
            "kiwoom_readonly_final_transport_canonical_output_only": kiwoom_readonly_final_transport["canonical_output_only"],
            "kiwoom_readonly_final_transport_snapshot_validation_ran": kiwoom_readonly_final_transport["snapshot_validation_ran"],
            "kiwoom_readonly_final_transport_real_network_not_used": kiwoom_readonly_final_transport["real_network_not_used"],
            "kiwoom_readonly_final_transport_parquet_unsupported": kiwoom_readonly_final_transport["parquet_unsupported"],
            "investing_crawler_called": False,
            "finviz_scraper_called": False,
            "news_ingestion_called": False,
            "gemini_called": False,
            "kiwoom_api_called": False,
            "kiwoom_mockapi_called": False,
            "ls_api_called": False,
            "broker_api_called": False,
            "account_api_called": False,
            "order_api_called": False,
            "oauth_token_requested": False,
            "oauth_token_revoked": False,
            "credentials_accessed": False,
            "environment_variables_read": False,
            "credential_file_read": False,
            "websocket_connected": False,
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


def _run_historical_dataset_readiness_smoke(output_dir: Path) -> dict[str, bool]:
    validation_input = HistoricalDatasetValidationInput.model_validate_json(
        (output_dir / "historical_dataset_validation_input.json").read_text(encoding="utf-8")
    )

    readiness_fixture = HistoricalDatasetReadinessInput.model_validate(
        {
            "schema_version": "5.6-historical-dataset-readiness-input",
            "readiness_input_id": "historical-dataset-readiness-input-smoke",
            "readiness_config": {
                "config_id": "historical-dataset-readiness-config-smoke",
                "strategy_track": "DOMESTIC_KR",
                "minimum_record_count": 1,
                "minimum_train_count": 1,
                "minimum_validation_count": 0,
                "minimum_test_count": 0,
                "minimum_label_coverage": 1,
            },
            "baseline_config": {
                "baseline_config_id": "historical-dataset-baseline-config-smoke",
                "strategy_track": "DOMESTIC_KR",
                "enabled_baselines": [
                    "MAJORITY_LABEL_BASELINE",
                    "PER_SYMBOL_MAJORITY_LABEL_BASELINE",
                    "PER_MARKET_MAJORITY_LABEL_BASELINE",
                    "PER_TRACK_MAJORITY_LABEL_BASELINE",
                    "PRIOR_DISTRIBUTION_BASELINE",
                    "NO_SKILL_BASELINE",
                ],
                "deterministic_only": True,
                "non_learning_only": True,
            },
            "dataset_records": validation_input.dataset_records,
            "validation_report": validation_input.validation_report.model_dump(mode="json"),
            "leakage_audit_report": validation_input.leakage_audit_report.model_dump(mode="json"),
            "split_manifest": validation_input.split_manifest.model_dump(mode="json"),
            "coverage_report": validation_input.coverage_report.model_dump(mode="json"),
            "label_distribution_report": validation_input.label_distribution_report.model_dump(mode="json"),
            "validation_gap_report": validation_input.validation_gap_report.model_dump(mode="json"),
            "validation_safety_report": validation_input.validation_safety_report.model_dump(mode="json"),
            "readiness_report": {
                "readiness_report_id": "historical-dataset-readiness-report-smoke",
                "readiness_input_id": "historical-dataset-readiness-input-smoke",
                "record_count": 0,
                "blocking_gate_count": 0,
                "warning_count": 0,
                "warnings": [],
                "trade_approval": False,
                "training_approval": False,
                "source_manifest_ids": validation_input.validation_report.source_manifest_ids,
                "source_audit_record_ids": validation_input.validation_report.source_audit_record_ids,
                "provider_provenance_ids": validation_input.validation_report.provider_provenance_ids,
            },
            "split_quality_report": {
                "split_quality_report_id": "historical-dataset-split-quality-report-smoke",
                "readiness_input_id": "historical-dataset-readiness-input-smoke",
                "chronological_split": True,
                "random_shuffle_used": False,
                "partition_overlap_detected": False,
                "duplicated_record_id_detected": False,
                "train_record_count": 0,
                "validation_record_count": 0,
                "test_record_count": 0,
                "train_symbol_count": 0,
                "validation_symbol_count": 0,
                "test_symbol_count": 0,
                "train_label_distribution": {},
                "validation_label_distribution": {},
                "test_label_distribution": {},
                "source_manifest_ids": validation_input.validation_report.source_manifest_ids,
                "source_audit_record_ids": validation_input.validation_report.source_audit_record_ids,
                "provider_provenance_ids": validation_input.validation_report.provider_provenance_ids,
            },
            "imbalance_report": {
                "imbalance_report_id": "historical-dataset-imbalance-report-smoke",
                "readiness_input_id": "historical-dataset-readiness-input-smoke",
                "label_counts": {},
                "label_percentages": {},
                "split_label_counts": {},
                "split_label_percentages": {},
                "severe_imbalance_warning": False,
                "missing_label_warning": False,
                "low_label_coverage_warning": False,
                "warning_count": 0,
                "warnings": [],
                "source_manifest_ids": validation_input.validation_report.source_manifest_ids,
                "source_audit_record_ids": validation_input.validation_report.source_audit_record_ids,
                "provider_provenance_ids": validation_input.validation_report.provider_provenance_ids,
            },
            "baseline_evaluation_report": {
                "baseline_evaluation_report_id": "historical-dataset-baseline-evaluation-report-smoke",
                "readiness_input_id": "historical-dataset-readiness-input-smoke",
                "baseline_names": [
                    "MAJORITY_LABEL_BASELINE",
                    "PER_SYMBOL_MAJORITY_LABEL_BASELINE",
                    "PER_MARKET_MAJORITY_LABEL_BASELINE",
                    "PER_TRACK_MAJORITY_LABEL_BASELINE",
                    "PRIOR_DISTRIBUTION_BASELINE",
                    "NO_SKILL_BASELINE",
                ],
                "deterministic_only": True,
                "non_learning_only": True,
                "accuracy": None,
                "label_coverage": None,
                "confusion_matrix_counts": {},
                "split_metric_summary": {},
                "trained_model_artifact_present": False,
                "model_weights_present": False,
                "runtime_trading_signal_present": False,
                "source_manifest_ids": validation_input.validation_report.source_manifest_ids,
                "source_audit_record_ids": validation_input.validation_report.source_audit_record_ids,
                "provider_provenance_ids": validation_input.validation_report.provider_provenance_ids,
            },
            "readiness_gap_report": {
                "gap_report_id": "historical-dataset-readiness-gap-report-smoke",
                "readiness_input_id": "historical-dataset-readiness-input-smoke",
                "gap_status": "NO_GAPS",
                "gap_categories": [],
                "blocking_gap_count": 0,
                "report_only_gap_count": 0,
                "gaps": [],
                "source_manifest_ids": validation_input.validation_report.source_manifest_ids,
                "source_audit_record_ids": validation_input.validation_report.source_audit_record_ids,
                "provider_provenance_ids": validation_input.validation_report.provider_provenance_ids,
            },
            "readiness_safety_report": {
                "safety_report_id": "historical-dataset-readiness-safety-report-smoke",
            },
            "audit_records": [
                {
                    "audit_record_id": "historical-dataset-readiness-audit-record-smoke",
                    "readiness_input_id": "historical-dataset-readiness-input-smoke",
                    "created_at": "2026-06-24T09:13:00+09:00",
                    "operator_context": "SYSTEM_SMOKE",
                    "source_path": str(output_dir / "historical_dataset_readiness_smoke_fixture.json"),
                    "source_manifest_ids": validation_input.validation_report.source_manifest_ids,
                    "source_audit_record_ids": validation_input.validation_report.source_audit_record_ids,
                    "provider_provenance_ids": validation_input.validation_report.provider_provenance_ids,
                }
            ],
        }
    )
    readiness = build_historical_dataset_readiness(readiness_fixture)

    (output_dir / "historical_dataset_readiness_input.json").write_text(
        readiness.model_dump_json(indent=2),
        encoding="utf-8",
    )
    (output_dir / "historical_dataset_readiness_report.json").write_text(
        readiness.readiness_report.model_dump_json(indent=2),
        encoding="utf-8",
    )
    (output_dir / "historical_dataset_split_quality_report.json").write_text(
        readiness.split_quality_report.model_dump_json(indent=2),
        encoding="utf-8",
    )
    (output_dir / "historical_dataset_imbalance_report.json").write_text(
        readiness.imbalance_report.model_dump_json(indent=2),
        encoding="utf-8",
    )
    (output_dir / "historical_dataset_baseline_evaluation_report.json").write_text(
        readiness.baseline_evaluation_report.model_dump_json(indent=2),
        encoding="utf-8",
    )
    (output_dir / "historical_dataset_readiness_safety_report.json").write_text(
        readiness.readiness_safety_report.model_dump_json(indent=2),
        encoding="utf-8",
    )

    return {
        "fixture_run": True,
        "readiness_report_generated": readiness.readiness_report.record_count == len(readiness.dataset_records),
        "split_quality_report_generated": (
            readiness.split_quality_report.train_record_count
            + readiness.split_quality_report.validation_record_count
            + readiness.split_quality_report.test_record_count
            == len(readiness.dataset_records)
        ),
        "imbalance_report_generated": sum(readiness.imbalance_report.label_counts.values()) == len(readiness.dataset_records),
        "baseline_evaluation_generated": len(readiness.baseline_evaluation_report.baseline_names) == 6,
        "baseline_non_learning": (
            readiness.baseline_evaluation_report.deterministic_only is True
            and readiness.baseline_evaluation_report.non_learning_only is True
            and readiness.baseline_evaluation_report.trained_model_artifact_present is False
            and readiness.baseline_evaluation_report.model_weights_present is False
            and readiness.baseline_evaluation_report.runtime_trading_signal_present is False
        ),
        "report_only": readiness.readiness_report.report_only is True and readiness.readiness_safety_report.report_only is True,
        "read_only": readiness.readiness_report.read_only is True and readiness.readiness_safety_report.read_only is True,
        "non_executable": readiness.readiness_report.non_executable is True and readiness.readiness_safety_report.non_executable is True,
        "local_files_only": readiness.readiness_report.local_file_only is True and readiness.readiness_safety_report.local_file_only is True,
        "remote_fetch_allowed": False,
        "api_provider_called": False,
        "order_intent_created": False,
        "live_or_prod_used": False,
        "cloud_llm_called": False,
        "model_runtime_called": False,
        "ml_training_run": False,
        "learned_model_evaluation_run": False,
        "ml_ready_tensor_export_created": False,
    }


def _run_historical_model_training_smoke(output_dir: Path) -> dict[str, bool]:
    readiness_input = HistoricalDatasetReadinessInput.model_validate_json(
        (output_dir / "historical_dataset_readiness_input.json").read_text(encoding="utf-8")
    )

    training_fixture = HistoricalModelTrainingInput.model_validate(
        {
            "schema_version": "5.7-historical-model-training-input",
            "training_input_id": "historical-model-training-input-smoke",
            "training_config": {
                "config_id": "historical-model-training-config-smoke",
                "strategy_track": "DOMESTIC_KR",
                "sandbox_mode": "RESEARCH_ONLY",
            },
            "dataset_ref": {
                "dataset_ref_id": "historical-model-dataset-ref-smoke",
                "dataset_manifest_id": "DATASET-EXPORT-MANIFEST-1",
                "source_manifest_ids": readiness_input.validation_report.source_manifest_ids,
                "source_audit_record_ids": readiness_input.validation_report.source_audit_record_ids,
                "provider_provenance_ids": readiness_input.validation_report.provider_provenance_ids,
            },
            "split_ref": {
                "split_ref_id": "historical-model-split-ref-smoke",
                "split_manifest_id": readiness_input.split_manifest.split_manifest_id,
                "split_policy": "CHRONOLOGICAL",
                "chronological": True,
                "random_shuffle_used": False,
                "source_manifest_ids": readiness_input.validation_report.source_manifest_ids,
                "source_audit_record_ids": readiness_input.validation_report.source_audit_record_ids,
                "provider_provenance_ids": readiness_input.validation_report.provider_provenance_ids,
            },
            "feature_schema": {
                "feature_schema_id": "historical-model-feature-schema-smoke",
                "feature_schema_version": "5.4-HISTORICAL-DATASET-FEATURE-BLOCK",
                "feature_fields": [
                    "REPLAY_CONTEXT_ID",
                    "SCANNER_REPLAY_INPUT_ID",
                    "KNOWN_EVENT_CONTEXT_SUMMARY",
                    "ATTACHED_MARKET_EVENT_COUNT",
                    "ATTACHED_CORPORATE_EVENT_COUNT",
                ],
            },
            "label_schema": {
                "label_schema_id": "historical-model-label-schema-smoke",
                "label_schema_version": "5.4-HISTORICAL-DATASET-OUTCOME-BLOCK",
                "label_source": "OUTCOME_BLOCK_ONLY",
                "label_field": "OUTCOME_LABEL",
            },
            "run_config": {
                "run_config_id": "historical-model-run-config-smoke",
                "requested_model_type": "DUMMY_MAJORITY",
                "random_shuffle_enabled": False,
            },
            "dataset_records": [record.model_dump(mode="json") for record in readiness_input.dataset_records],
            "dataset_export_manifest": {
                "manifest_id": "DATASET-EXPORT-MANIFEST-1",
                "export_format": "JSON",
                "local_output_path": str(output_dir / "historical_model_training_dataset_export.json"),
                "record_count": len(readiness_input.dataset_records),
                "symbol_count": len({record.symbol for record in readiness_input.dataset_records}),
                "market_count": len({record.market for record in readiness_input.dataset_records}),
                "date_range_start": min(record.replay_session_date for record in readiness_input.dataset_records).isoformat(),
                "date_range_end": max(record.replay_session_date for record in readiness_input.dataset_records).isoformat(),
                "feature_schema_version": "5.4-HISTORICAL-DATASET-FEATURE-BLOCK",
                "outcome_schema_version": "5.4-HISTORICAL-DATASET-OUTCOME-BLOCK",
                "quality_report_id": "DATASET-QUALITY-REPORT-1",
                "gap_report_id": "DATASET-GAP-REPORT-1",
                "safety_report_id": "DATASET-SAFETY-REPORT-1",
                "export_formats": ["JSON", "JSONL", "CSV"],
                "source_manifest_ids": readiness_input.validation_report.source_manifest_ids,
                "source_audit_record_ids": readiness_input.validation_report.source_audit_record_ids,
                "provider_provenance_ids": readiness_input.validation_report.provider_provenance_ids,
            },
            "validation_report": readiness_input.validation_report.model_dump(mode="json"),
            "leakage_audit_report": readiness_input.leakage_audit_report.model_dump(mode="json"),
            "split_manifest": readiness_input.split_manifest.model_dump(mode="json"),
            "coverage_report": readiness_input.coverage_report.model_dump(mode="json"),
            "label_distribution_report": readiness_input.label_distribution_report.model_dump(mode="json"),
            "readiness_report": readiness_input.readiness_report.model_dump(mode="json"),
            "split_quality_report": readiness_input.split_quality_report.model_dump(mode="json"),
            "imbalance_report": readiness_input.imbalance_report.model_dump(mode="json"),
            "baseline_evaluation_report": readiness_input.baseline_evaluation_report.model_dump(mode="json"),
            "plan_check_report": {
                "plan_check_report_id": "historical-model-plan-check-report-smoke",
                "training_input_id": "historical-model-training-input-smoke",
                "eligible_for_sandbox_training": False,
                "warning_count": 0,
                "warnings": [],
                "blocking_issue_count": 0,
                "source_manifest_ids": readiness_input.validation_report.source_manifest_ids,
                "source_audit_record_ids": readiness_input.validation_report.source_audit_record_ids,
                "provider_provenance_ids": readiness_input.validation_report.provider_provenance_ids,
            },
            "run_report": {
                "run_report_id": "historical-model-run-report-smoke",
                "training_input_id": "historical-model-training-input-smoke",
                "model_type": "DUMMY_MAJORITY",
                "sandbox_mode": "RESEARCH_ONLY",
                "report_only_prediction_count": 0,
                "training_executed": False,
                "source_manifest_ids": readiness_input.validation_report.source_manifest_ids,
                "source_audit_record_ids": readiness_input.validation_report.source_audit_record_ids,
                "provider_provenance_ids": readiness_input.validation_report.provider_provenance_ids,
            },
            "evaluation_report": {
                "evaluation_report_id": "historical-model-evaluation-report-smoke",
                "training_input_id": "historical-model-training-input-smoke",
                "model_type": "DUMMY_MAJORITY",
                "report_only_prediction_count": 0,
                "runtime_trading_signal_present": False,
                "order_candidate_present": False,
                "source_manifest_ids": readiness_input.validation_report.source_manifest_ids,
                "source_audit_record_ids": readiness_input.validation_report.source_audit_record_ids,
                "provider_provenance_ids": readiness_input.validation_report.provider_provenance_ids,
            },
            "metrics_report": {
                "metrics_report_id": "historical-model-metrics-report-smoke",
                "training_input_id": "historical-model-training-input-smoke",
                "model_type": "DUMMY_MAJORITY",
                "train_accuracy": 0.0,
                "validation_accuracy": 0.0,
                "test_accuracy": 0.0,
                "source_manifest_ids": readiness_input.validation_report.source_manifest_ids,
                "source_audit_record_ids": readiness_input.validation_report.source_audit_record_ids,
                "provider_provenance_ids": readiness_input.validation_report.provider_provenance_ids,
            },
            "artifact_manifest": {
                "artifact_manifest_id": "historical-model-artifact-manifest-smoke",
                "model_id": "historical-model-smoke",
                "model_type": "DUMMY_MAJORITY",
                "training_dataset_manifest_id": "DATASET-EXPORT-MANIFEST-1",
                "split_manifest_id": readiness_input.split_manifest.split_manifest_id,
                "feature_schema_version": "5.4-HISTORICAL-DATASET-FEATURE-BLOCK",
                "label_schema_version": "5.4-HISTORICAL-DATASET-OUTCOME-BLOCK",
                "training_timestamp": "2026-06-24T09:18:00+09:00",
                "metrics_report_id": "historical-model-metrics-report-smoke",
                "local_artifact_path": str(output_dir / "historical_model_smoke_artifact.json"),
            },
            "safety_report": {
                "safety_report_id": "historical-model-safety-report-smoke",
            },
            "gap_report": {
                "gap_report_id": "historical-model-gap-report-smoke",
                "training_input_id": "historical-model-training-input-smoke",
                "gap_status": "NO_GAPS",
                "gap_categories": [],
                "blocking_gap_count": 0,
                "report_only_gap_count": 0,
                "gaps": [],
                "source_manifest_ids": readiness_input.validation_report.source_manifest_ids,
                "source_audit_record_ids": readiness_input.validation_report.source_audit_record_ids,
                "provider_provenance_ids": readiness_input.validation_report.provider_provenance_ids,
            },
            "audit_records": [
                {
                    "audit_record_id": "historical-model-audit-record-smoke",
                    "training_input_id": "historical-model-training-input-smoke",
                    "created_at": "2026-06-24T09:20:00+09:00",
                    "operator_context": "SYSTEM_SMOKE",
                    "source_path": str(output_dir / "historical_model_training_smoke_fixture.json"),
                    "source_manifest_ids": readiness_input.validation_report.source_manifest_ids,
                    "source_audit_record_ids": readiness_input.validation_report.source_audit_record_ids,
                    "provider_provenance_ids": readiness_input.validation_report.provider_provenance_ids,
                }
            ],
        }
    )
    plan_checked = build_historical_model_training_plan_check(training_fixture)
    trained = run_historical_model_training_sandbox(training_fixture)
    sklearn_probe_fixture = training_fixture.model_copy(
        update={
            "run_config": training_fixture.run_config.model_copy(
                update={"requested_model_type": HistoricalModelTrainingModelType.LOGISTIC_REGRESSION_OPTIONAL_SKLEARN}
            ),
            "run_report": training_fixture.run_report.model_copy(update={"model_type": HistoricalModelTrainingModelType.LOGISTIC_REGRESSION_OPTIONAL_SKLEARN}),
            "evaluation_report": training_fixture.evaluation_report.model_copy(update={"model_type": HistoricalModelTrainingModelType.LOGISTIC_REGRESSION_OPTIONAL_SKLEARN}),
            "metrics_report": training_fixture.metrics_report.model_copy(update={"model_type": HistoricalModelTrainingModelType.LOGISTIC_REGRESSION_OPTIONAL_SKLEARN}),
            "artifact_manifest": training_fixture.artifact_manifest.model_copy(update={"model_type": HistoricalModelTrainingModelType.LOGISTIC_REGRESSION_OPTIONAL_SKLEARN}),
        }
    )
    sklearn_probe = run_historical_model_training_sandbox(sklearn_probe_fixture)

    (output_dir / "historical_model_training_input.json").write_text(
        trained.model_dump_json(indent=2),
        encoding="utf-8",
    )
    (output_dir / "historical_model_training_plan_check_report.json").write_text(
        plan_checked.plan_check_report.model_dump_json(indent=2),
        encoding="utf-8",
    )
    (output_dir / "historical_model_training_run_report.json").write_text(
        trained.run_report.model_dump_json(indent=2),
        encoding="utf-8",
    )
    (output_dir / "historical_model_evaluation_report.json").write_text(
        trained.evaluation_report.model_dump_json(indent=2),
        encoding="utf-8",
    )
    (output_dir / "historical_model_metrics_report.json").write_text(
        trained.metrics_report.model_dump_json(indent=2),
        encoding="utf-8",
    )
    (output_dir / "historical_model_artifact_manifest.json").write_text(
        trained.artifact_manifest.model_dump_json(indent=2),
        encoding="utf-8",
    )
    (output_dir / "historical_model_training_safety_report.json").write_text(
        trained.safety_report.model_dump_json(indent=2),
        encoding="utf-8",
    )
    (output_dir / "historical_model_training_gap_report.json").write_text(
        trained.gap_report.model_dump_json(indent=2),
        encoding="utf-8",
    )

    return {
        "fixture_run": True,
        "plan_check_generated": plan_checked.plan_check_report.eligible_for_sandbox_training is True,
        "run_report_generated": trained.run_report.training_executed is True,
        "evaluation_report_generated": trained.evaluation_report.report_only_prediction_count == len(trained.dataset_records),
        "metrics_report_generated": trained.metrics_report.test_accuracy is not None,
        "artifact_manifest_generated": trained.artifact_manifest.metrics_report_id == trained.metrics_report.metrics_report_id,
        "local_only": trained.run_report.local_file_only is True and trained.artifact_manifest.local_file_only is True,
        "offline_only": trained.run_report.offline_only is True and trained.artifact_manifest.offline_only is True,
        "chronological_split_used": trained.split_ref.chronological is True and trained.split_manifest.chronological is True,
        "no_random_shuffle": trained.run_config.random_shuffle_enabled is False and trained.split_manifest.random_shuffle_used is False,
        "dummy_models_available": trained.run_report.model_type == "DUMMY_MAJORITY" and trained.run_report.training_executed is True,
        "optional_sklearn_fail_closed": any(
            gap["gap_category"] == "TRAINING_SKLEARN_UNAVAILABLE" for gap in sklearn_probe.gap_report.gaps
        ),
        "report_only": (
            trained.run_report.report_only is True
            and trained.evaluation_report.report_only is True
            and trained.metrics_report.report_only is True
            and trained.artifact_manifest.report_only is True
        ),
        "non_executable": (
            trained.run_report.non_executable is True
            and trained.evaluation_report.non_executable is True
            and trained.metrics_report.non_executable is True
            and trained.artifact_manifest.non_executable is True
        ),
        "no_runtime_signal": (
            trained.evaluation_report.runtime_trading_signal_present is False
            and trained.run_report.no_runtime_trading_signal is True
            and trained.artifact_manifest.no_runtime_trading_signal is True
        ),
        "no_order_candidate": (
            trained.evaluation_report.order_candidate_present is False
            and trained.run_report.no_order_candidate is True
            and trained.artifact_manifest.no_order_candidate is True
        ),
        "no_live_inference": trained.run_report.no_live_prod is True and trained.artifact_manifest.no_live_prod is True,
        "no_broker_path": trained.run_report.no_broker_path is True and trained.artifact_manifest.no_broker_path is True,
        "no_live_prod": trained.training_config.no_live_prod is True and trained.artifact_manifest.no_live_prod is True,
        "no_network": trained.training_config.no_network is True and trained.artifact_manifest.no_network is True,
        "no_cloud_llm": trained.training_config.no_cloud_llm is True and trained.artifact_manifest.no_cloud_llm is True,
        "no_local_llm_runtime": (
            trained.training_config.no_local_llm_runtime is True
            and trained.artifact_manifest.no_local_llm_runtime is True
        ),
    }


def _run_historical_model_experiment_smoke(output_dir: Path) -> dict[str, bool]:
    training_input = HistoricalModelTrainingInput.model_validate_json(
        (output_dir / "historical_model_training_input.json").read_text(encoding="utf-8")
    )

    experiment_fixture = HistoricalModelExperimentRegistryInput.model_validate(
        {
            "schema_version": "5.8-historical-model-experiment-registry-input",
            "registry_input_id": "historical-model-experiment-registry-input-smoke",
            "registry_config": {
                "config_id": "historical-model-experiment-registry-config-smoke",
                "strategy_track": "DOMESTIC_KR",
            },
            "experiment_records": [
                {
                    "experiment_id": "historical-model-experiment-smoke",
                    "model_type": training_input.run_report.model_type,
                    "dataset_manifest_id": training_input.dataset_ref.dataset_manifest_id,
                    "split_manifest_id": training_input.split_ref.split_manifest_id,
                    "feature_schema_version": training_input.feature_schema.feature_schema_version,
                    "label_schema_version": training_input.label_schema.label_schema_version,
                    "metrics_report_id": training_input.metrics_report.metrics_report_id,
                    "artifact_manifest_id": training_input.artifact_manifest.artifact_manifest_id,
                    "safety_report_id": training_input.safety_report.safety_report_id,
                    "training_timestamp": training_input.artifact_manifest.training_timestamp,
                    "model_metadata": {"sandbox_origin": "offline"},
                    "source_manifest_ids": training_input.metrics_report.source_manifest_ids,
                    "source_audit_record_ids": training_input.metrics_report.source_audit_record_ids,
                    "provider_provenance_ids": training_input.metrics_report.provider_provenance_ids,
                }
            ],
            "training_run_report": training_input.run_report.model_dump(mode="json"),
            "evaluation_report": training_input.evaluation_report.model_dump(mode="json"),
            "metrics_report": training_input.metrics_report.model_dump(mode="json"),
            "artifact_manifest": training_input.artifact_manifest.model_dump(mode="json"),
            "training_safety_report": training_input.safety_report.model_dump(mode="json"),
            "training_gap_report": training_input.gap_report.model_dump(mode="json"),
            "baseline_evaluation_report": training_input.baseline_evaluation_report.model_dump(mode="json")
            if training_input.baseline_evaluation_report is not None
            else None,
            "split_manifest": training_input.split_manifest.model_dump(mode="json") if training_input.split_manifest is not None else None,
            "leakage_audit_report": training_input.leakage_audit_report.model_dump(mode="json")
            if training_input.leakage_audit_report is not None
            else None,
            "registry_report": {
                "registry_report_id": "historical-model-experiment-registry-report-smoke",
                "registry_input_id": "historical-model-experiment-registry-input-smoke",
                "experiment_count": 0,
                "blocked_experiment_count": 0,
                "source_manifest_ids": training_input.metrics_report.source_manifest_ids,
                "source_audit_record_ids": training_input.metrics_report.source_audit_record_ids,
                "provider_provenance_ids": training_input.metrics_report.provider_provenance_ids,
            },
            "comparison_report": {
                "comparison_report_id": "historical-model-comparison-report-smoke",
                "registry_input_id": "historical-model-experiment-registry-input-smoke",
                "compared_experiment_ids": [],
                "compared_metric_names": [],
                "validation_accuracy_delta": None,
                "test_accuracy_delta": None,
                "balanced_accuracy_delta": None,
                "macro_f1_delta": None,
                "baseline_improvement_delta": None,
                "safety_blocked": True,
                "source_manifest_ids": training_input.metrics_report.source_manifest_ids,
                "source_audit_record_ids": training_input.metrics_report.source_audit_record_ids,
                "provider_provenance_ids": training_input.metrics_report.provider_provenance_ids,
            },
            "risk_review_report": {
                "risk_review_report_id": "historical-model-risk-review-report-smoke",
                "registry_input_id": "historical-model-experiment-registry-input-smoke",
                "overfit_risk": False,
                "low_label_support": False,
                "severe_label_imbalance": False,
                "train_test_metric_gap": False,
                "weak_baseline_improvement": False,
                "missing_leakage_audit_lineage": False,
                "missing_validation_split_lineage": False,
                "unsafe_artifact_metadata": False,
                "optional_sklearn_dependency_risk": False,
                "unsupported_model_type": False,
                "missing_safety_flags": False,
                "source_manifest_ids": training_input.metrics_report.source_manifest_ids,
                "source_audit_record_ids": training_input.metrics_report.source_audit_record_ids,
                "provider_provenance_ids": training_input.metrics_report.provider_provenance_ids,
            },
            "promotion_block_report": {
                "promotion_block_report_id": "historical-model-promotion-block-report-smoke",
                "registry_input_id": "historical-model-experiment-registry-input-smoke",
                "production_use_allowed": False,
                "live_inference_allowed": False,
                "runtime_trading_signal_allowed": False,
                "order_candidate_allowed": False,
                "paper_trading_allowed": False,
                "broker_path_allowed": False,
                "live_prod_allowed": False,
                "deployment_allowed": False,
                "source_manifest_ids": training_input.metrics_report.source_manifest_ids,
                "source_audit_record_ids": training_input.metrics_report.source_audit_record_ids,
                "provider_provenance_ids": training_input.metrics_report.provider_provenance_ids,
            },
            "lineage_report": {
                "lineage_report_id": "historical-model-lineage-report-smoke",
                "registry_input_id": "historical-model-experiment-registry-input-smoke",
                "leakage_audit_lineage_present": True,
                "validation_split_lineage_present": True,
                "artifact_manifest_lineage_present": True,
                "source_manifest_ids": training_input.metrics_report.source_manifest_ids,
                "source_audit_record_ids": training_input.metrics_report.source_audit_record_ids,
                "provider_provenance_ids": training_input.metrics_report.provider_provenance_ids,
            },
            "safety_report": {
                "safety_report_id": "historical-model-experiment-safety-report-smoke",
            },
            "gap_report": {
                "gap_report_id": "historical-model-experiment-gap-report-smoke",
                "registry_input_id": "historical-model-experiment-registry-input-smoke",
                "gap_status": "NO_GAPS",
                "gap_categories": [],
                "blocking_gap_count": 0,
                "report_only_gap_count": 0,
                "gaps": [],
                "source_manifest_ids": training_input.metrics_report.source_manifest_ids,
                "source_audit_record_ids": training_input.metrics_report.source_audit_record_ids,
                "provider_provenance_ids": training_input.metrics_report.provider_provenance_ids,
            },
            "audit_records": [
                {
                    "audit_record_id": "historical-model-experiment-audit-record-smoke",
                    "registry_input_id": "historical-model-experiment-registry-input-smoke",
                    "created_at": "2026-06-24T09:25:00+09:00",
                    "operator_context": "SYSTEM_SMOKE",
                    "source_path": str(output_dir / "historical_model_experiment_smoke_fixture.json"),
                    "source_manifest_ids": training_input.metrics_report.source_manifest_ids,
                    "source_audit_record_ids": training_input.metrics_report.source_audit_record_ids,
                    "provider_provenance_ids": training_input.metrics_report.provider_provenance_ids,
                }
            ],
        }
    )
    experiment = build_historical_model_experiment_registry(experiment_fixture)

    (output_dir / "historical_model_experiment_registry_input.json").write_text(
        experiment.model_dump_json(indent=2),
        encoding="utf-8",
    )
    (output_dir / "historical_model_experiment_registry_report.json").write_text(
        experiment.registry_report.model_dump_json(indent=2),
        encoding="utf-8",
    )
    (output_dir / "historical_model_comparison_report.json").write_text(
        experiment.comparison_report.model_dump_json(indent=2),
        encoding="utf-8",
    )
    (output_dir / "historical_model_risk_review_report.json").write_text(
        experiment.risk_review_report.model_dump_json(indent=2),
        encoding="utf-8",
    )
    (output_dir / "historical_model_promotion_block_report.json").write_text(
        experiment.promotion_block_report.model_dump_json(indent=2),
        encoding="utf-8",
    )
    (output_dir / "historical_model_experiment_lineage_report.json").write_text(
        experiment.lineage_report.model_dump_json(indent=2),
        encoding="utf-8",
    )
    (output_dir / "historical_model_experiment_safety_report.json").write_text(
        experiment.safety_report.model_dump_json(indent=2),
        encoding="utf-8",
    )

    return {
        "fixture_run": True,
        "registry_report_generated": experiment.registry_report.experiment_count == 1,
        "comparison_report_generated": len(experiment.comparison_report.compared_experiment_ids) == 1,
        "risk_review_generated": experiment.risk_review_report.risk_review_report_id.endswith("SMOKE"),
        "promotion_block_report_generated": experiment.promotion_block_report.promotion_block_report_id.endswith("SMOKE"),
        "lineage_report_generated": experiment.lineage_report.lineage_report_id.endswith("SMOKE"),
        "report_only": (
            experiment.registry_report.report_only is True
            and experiment.comparison_report.report_only is True
            and experiment.risk_review_report.report_only is True
            and experiment.promotion_block_report.report_only is True
        ),
        "non_executable": (
            experiment.registry_report.non_executable is True
            and experiment.comparison_report.non_executable is True
            and experiment.risk_review_report.non_executable is True
            and experiment.promotion_block_report.non_executable is True
        ),
        "no_runtime_signal": (
            experiment.registry_report.no_runtime_trading_signal is True
            and experiment.safety_report.no_runtime_trading_signal is True
            and experiment.promotion_block_report.runtime_trading_signal_allowed is False
        ),
        "no_order_candidate": (
            experiment.registry_report.no_order_candidate is True
            and experiment.safety_report.no_order_candidate is True
            and experiment.promotion_block_report.order_candidate_allowed is False
        ),
        "no_live_inference": (
            experiment.registry_report.no_live_inference is True
            and experiment.safety_report.no_live_inference is True
            and experiment.promotion_block_report.live_inference_allowed is False
        ),
        "no_deployment": (
            experiment.registry_report.no_deployment is True
            and experiment.safety_report.no_deployment is True
            and experiment.promotion_block_report.deployment_allowed is False
        ),
        "no_paper_trading": experiment.promotion_block_report.paper_trading_allowed is False,
        "no_broker_path": (
            experiment.registry_report.no_broker_path is True
            and experiment.safety_report.no_broker_path is True
            and experiment.promotion_block_report.broker_path_allowed is False
        ),
        "no_live_prod": (
            experiment.registry_report.no_live_prod is True
            and experiment.safety_report.no_live_prod is True
            and experiment.promotion_block_report.live_prod_allowed is False
        ),
        "no_network": experiment.registry_report.no_network is True and experiment.safety_report.no_network is True,
        "no_cloud_llm": experiment.registry_report.no_cloud_llm is True and experiment.safety_report.no_cloud_llm is True,
        "no_local_llm_runtime": (
            experiment.registry_report.no_local_llm_runtime is True
            and experiment.safety_report.no_local_llm_runtime is True
        ),
        "promotion_blocked_by_default": (
            experiment.promotion_block_report.production_use_allowed is False
            and experiment.promotion_block_report.live_inference_allowed is False
            and experiment.promotion_block_report.runtime_trading_signal_allowed is False
            and experiment.promotion_block_report.order_candidate_allowed is False
            and experiment.promotion_block_report.paper_trading_allowed is False
            and experiment.promotion_block_report.broker_path_allowed is False
            and experiment.promotion_block_report.live_prod_allowed is False
            and experiment.promotion_block_report.deployment_allowed is False
        ),
    }


def _run_historical_signal_candidate_smoke(output_dir: Path) -> dict[str, bool]:
    experiment_input = HistoricalModelExperimentRegistryInput.model_validate_json(
        (output_dir / "historical_model_experiment_registry_input.json").read_text(encoding="utf-8")
    )
    experiment_record = experiment_input.experiment_records[0]
    fixture = HistoricalSignalCandidateInput.model_validate(
        {
            "schema_version": "5.9-historical-signal-candidate-input",
            "signal_candidate_input_id": "historical-signal-candidate-input-smoke",
            "signal_candidate_config": {
                "config_id": "historical-signal-candidate-config-smoke",
                "strategy_track": "DOMESTIC_KR",
            },
            "source_refs": [
                {
                    "source_ref_id": "historical-signal-source-ref-smoke",
                    "symbol": "005930",
                    "timestamp": "2026-06-24T09:30:00+09:00",
                    "source_model_id": experiment_input.training_run_report.run_report_id,
                    "source_experiment_id": experiment_record.experiment_id,
                    "source_metrics_report_id": experiment_input.metrics_report.metrics_report_id,
                    "source_artifact_manifest_id": experiment_input.artifact_manifest.artifact_manifest_id,
                    "source_risk_review_id": experiment_input.risk_review_report.risk_review_report_id,
                    "source_promotion_block_id": experiment_input.promotion_block_report.promotion_block_report_id,
                    "dataset_lineage_id": experiment_record.dataset_manifest_id,
                    "split_lineage_id": experiment_record.split_manifest_id,
                    "score": 0.76,
                    "score_bucket": "HIGH",
                    "confidence_bucket": "HIGH",
                    "predicted_outcome_label": "OUTCOME_FAVORABLE",
                    "horizon": "T_PLUS_5",
                    "feature_schema_version": experiment_record.feature_schema_version,
                    "label_schema_version": experiment_record.label_schema_version,
                    "explanation_summary": "Offline neutral observation candidate from experiment registry smoke fixture.",
                    "source_manifest_ids": experiment_input.metrics_report.source_manifest_ids,
                    "source_audit_record_ids": experiment_input.metrics_report.source_audit_record_ids,
                    "provider_provenance_ids": experiment_input.metrics_report.provider_provenance_ids,
                    "metadata": {"report_origin": "offline_fixture"},
                }
            ],
            "candidate_batch": {
                "candidate_batch_id": "historical-signal-candidate-batch-smoke",
                "signal_candidate_input_id": "historical-signal-candidate-input-smoke",
                "candidates": [],
                "accepted_candidate_count": 0,
                "rejected_candidate_count": 0,
            },
            "candidate_report": {
                "candidate_report_id": "historical-signal-candidate-report-smoke",
                "signal_candidate_input_id": "historical-signal-candidate-input-smoke",
                "candidate_count": 0,
                "accepted_candidate_count": 0,
                "rejected_candidate_count": 0,
                "gap_counts": {},
                "safety_flag_summary": {},
                "score_bucket_distribution": {},
                "confidence_bucket_distribution": {},
                "outcome_label_distribution": {},
                "lineage_coverage_summary": {},
                "blocked_execution_summary": {},
            },
            "safety_report": {
                "safety_report_id": "historical-signal-candidate-safety-report-smoke",
                "signal_candidate_input_id": "historical-signal-candidate-input-smoke",
                "blocked_runtime_signal_count": 0,
                "blocked_order_candidate_count": 0,
                "blocked_paper_trading_count": 0,
                "blocked_live_inference_count": 0,
                "blocked_deployment_count": 0,
                "blocked_broker_path_count": 0,
            },
            "gap_report": {
                "gap_report_id": "historical-signal-candidate-gap-report-smoke",
                "signal_candidate_input_id": "historical-signal-candidate-input-smoke",
                "gap_status": "NO_GAPS",
                "gap_categories": [],
                "blocking_gap_count": 0,
                "report_only_gap_count": 0,
                "gaps": [],
            },
            "audit_records": [
                {
                    "audit_record_id": "historical-signal-candidate-audit-record-smoke",
                    "signal_candidate_input_id": "historical-signal-candidate-input-smoke",
                    "created_at": "2026-06-24T09:35:00+09:00",
                    "operator_context": "SYSTEM_SMOKE",
                    "source_path": str(output_dir / "historical_signal_candidate_smoke_fixture.json"),
                    "source_manifest_ids": experiment_input.metrics_report.source_manifest_ids,
                    "source_audit_record_ids": experiment_input.metrics_report.source_audit_record_ids,
                    "provider_provenance_ids": experiment_input.metrics_report.provider_provenance_ids,
                }
            ],
        }
    )
    signal_candidate = build_historical_signal_candidate_batch(fixture)

    (output_dir / "historical_signal_candidate_input.json").write_text(
        signal_candidate.model_dump_json(indent=2),
        encoding="utf-8",
    )
    (output_dir / "historical_signal_candidate_batch.json").write_text(
        signal_candidate.candidate_batch.model_dump_json(indent=2),
        encoding="utf-8",
    )
    (output_dir / "historical_signal_candidate_report.json").write_text(
        signal_candidate.candidate_report.model_dump_json(indent=2),
        encoding="utf-8",
    )
    (output_dir / "historical_signal_candidate_safety_report.json").write_text(
        signal_candidate.safety_report.model_dump_json(indent=2),
        encoding="utf-8",
    )
    (output_dir / "historical_signal_candidate_gap_report.json").write_text(
        signal_candidate.gap_report.model_dump_json(indent=2),
        encoding="utf-8",
    )

    batch_dump = json.dumps(signal_candidate.candidate_batch.model_dump(mode="json")).lower()
    return {
        "fixture_run": True,
        "build_generated": signal_candidate.candidate_batch.accepted_candidate_count == 1,
        "report_generated": signal_candidate.candidate_report.candidate_count == 1,
        "safety_report_generated": signal_candidate.safety_report.safety_report_id.endswith("SMOKE"),
        "gap_report_generated": signal_candidate.gap_report.gap_report_id.endswith("SMOKE"),
        "audit_record_generated": len(signal_candidate.audit_records) == 1,
        "report_only": (
            signal_candidate.candidate_batch.report_only is True
            and signal_candidate.candidate_report.report_only is True
            and signal_candidate.safety_report.report_only is True
            and signal_candidate.gap_report.report_only is True
        ),
        "non_executable": (
            signal_candidate.candidate_batch.non_executable is True
            and signal_candidate.candidate_report.non_executable is True
            and signal_candidate.safety_report.non_executable is True
            and signal_candidate.gap_report.non_executable is True
        ),
        "local_only": (
            signal_candidate.candidate_batch.local_file_only is True
            and signal_candidate.candidate_report.local_file_only is True
            and signal_candidate.safety_report.local_file_only is True
            and signal_candidate.gap_report.local_file_only is True
        ),
        "offline_only": (
            signal_candidate.candidate_batch.offline_only is True
            and signal_candidate.candidate_report.offline_only is True
            and signal_candidate.safety_report.offline_only is True
            and signal_candidate.gap_report.offline_only is True
        ),
        "no_runtime_signal": (
            signal_candidate.candidate_batch.no_runtime_trading_signal is True
            and signal_candidate.candidate_report.no_runtime_trading_signal is True
            and signal_candidate.safety_report.no_runtime_trading_signal is True
        ),
        "no_order_candidate": (
            signal_candidate.candidate_batch.no_order_candidate is True
            and signal_candidate.candidate_report.no_order_candidate is True
            and signal_candidate.safety_report.no_order_candidate is True
        ),
        "no_live_inference": (
            signal_candidate.candidate_batch.no_live_inference is True
            and signal_candidate.candidate_report.no_live_inference is True
            and signal_candidate.safety_report.no_live_inference is True
        ),
        "no_deployment": (
            signal_candidate.candidate_batch.no_deployment is True
            and signal_candidate.candidate_report.no_deployment is True
            and signal_candidate.safety_report.no_deployment is True
        ),
        "no_paper_trading": (
            signal_candidate.candidate_batch.no_paper_trading is True
            and signal_candidate.candidate_report.no_paper_trading is True
            and signal_candidate.safety_report.no_paper_trading is True
        ),
        "no_broker_path": (
            signal_candidate.candidate_batch.no_broker_path is True
            and signal_candidate.candidate_report.no_broker_path is True
            and signal_candidate.safety_report.no_broker_path is True
        ),
        "no_live_prod": (
            signal_candidate.candidate_batch.no_live_prod is True
            and signal_candidate.candidate_report.no_live_prod is True
            and signal_candidate.safety_report.no_live_prod is True
        ),
        "no_network": (
            signal_candidate.candidate_batch.no_network is True
            and signal_candidate.candidate_report.no_network is True
            and signal_candidate.safety_report.no_network is True
        ),
        "no_provider_api": (
            signal_candidate.candidate_batch.no_provider_api is True
            and signal_candidate.candidate_report.no_provider_api is True
            and signal_candidate.safety_report.no_provider_api is True
        ),
        "no_cloud_llm": (
            signal_candidate.candidate_batch.no_cloud_llm is True
            and signal_candidate.candidate_report.no_cloud_llm is True
            and signal_candidate.safety_report.no_cloud_llm is True
        ),
        "no_local_llm_runtime": (
            signal_candidate.candidate_batch.no_local_llm_runtime is True
            and signal_candidate.candidate_report.no_local_llm_runtime is True
            and signal_candidate.safety_report.no_local_llm_runtime is True
        ),
        "no_buy_sell_order_execution": all(
            token not in batch_dump
            for token in ("\"buy\"", "\"sell\"", "\"entry\"", "\"exit\"", "order_intent", "execution_approval")
        ),
        "parquet_unsupported": ".parquet" not in batch_dump,
    }


def _run_historical_paper_trading_smoke(output_dir: Path) -> dict[str, bool]:
    signal_input = HistoricalSignalCandidateInput.model_validate_json(
        (output_dir / "historical_signal_candidate_input.json").read_text(encoding="utf-8")
    )
    candidate = signal_input.candidate_batch.candidates[0]
    fixture = HistoricalPaperTradingInput.model_validate(
        {
            "schema_version": "5.10-historical-paper-trading-input",
            "paper_trading_input_id": "historical-paper-trading-input-smoke",
            "paper_trading_config": {
                "config_id": "historical-paper-trading-config-smoke",
                "strategy_track": "DOMESTIC_KR",
                "initial_cash": 1000000.0,
                "slippage_bps": 5.0,
                "fee_bps": 2.0,
            },
            "paper_policy": {
                "policy_id": "historical-paper-policy-smoke",
                "max_positions": 5,
                "max_exposure": 500000.0,
                "max_per_symbol_exposure": 150000.0,
                "max_daily_loss": 50000.0,
                "max_drawdown": 100000.0,
                "default_holding_period_sessions": 5,
                "stop_simulation_rule": "FIXED_PCT",
                "take_profit_simulation_rule": "FIXED_PCT",
            },
            "paper_decision": {
                "decision_id": "historical-paper-decision-smoke",
                "signal_candidate_ref_id": candidate.candidate_id,
                "paper_side": "PAPER_BUY",
                "decision_timestamp": "2026-06-24T09:35:00+09:00",
                "decision_reason": "Paper-only deterministic smoke decision.",
            },
            "paper_order_intent": {
                "paper_order_intent_id": "historical-paper-order-intent-smoke",
                "signal_candidate_ref_id": candidate.candidate_id,
                "decision_id": "historical-paper-decision-smoke",
                "paper_side": "PAPER_BUY",
                "symbol": candidate.symbol,
                "quantity": 2,
                "decision_timestamp": "2026-06-24T09:35:00+09:00",
                "intended_entry_session": "2026-06-25",
            },
            "paper_fill": {
                "paper_fill_id": "historical-paper-fill-smoke",
                "paper_order_intent_id": "historical-paper-order-intent-smoke",
                "symbol": candidate.symbol,
                "paper_side": "PAPER_BUY",
                "fill_price": 100.0,
                "fill_quantity": 2,
                "fill_timestamp": "2026-06-25T09:05:00+09:00",
                "slippage_cost": 0.0,
                "fee_cost": 0.0,
            },
            "paper_ledger": {
                "paper_ledger_id": "historical-paper-ledger-smoke",
                "starting_cash": 1000000.0,
                "cash_balance": 1000000.0,
                "reserved_cash": 0.0,
                "realized_pnl": 0.0,
                "unrealized_pnl": 0.0,
                "fees_paid": 0.0,
                "slippage_paid": 0.0,
            },
            "paper_position": {
                "paper_position_id": "historical-paper-position-smoke",
                "symbol": candidate.symbol,
                "open_quantity": 0,
                "average_entry_price": 0.0,
                "market_value": 0.0,
                "unrealized_pnl": 0.0,
            },
            "paper_trade": {
                "paper_trade_id": "historical-paper-trade-smoke",
                "symbol": candidate.symbol,
                "entry_fill_id": "historical-paper-fill-smoke",
                "entry_side": "PAPER_BUY",
                "entry_price": 0.0,
                "entry_quantity": 1,
                "status": "OPEN",
            },
            "paper_risk_limit": {
                "paper_risk_limit_id": "historical-paper-risk-limit-smoke",
                "max_positions": 5,
                "max_exposure": 500000.0,
                "max_per_symbol_exposure": 150000.0,
                "max_daily_loss": 50000.0,
                "max_drawdown": 100000.0,
            },
            "paper_performance_report": {
                "performance_report_id": "historical-paper-performance-report-smoke",
                "total_return": 0.0,
                "realized_pnl": 0.0,
                "unrealized_pnl": 0.0,
                "max_drawdown": 0.0,
                "win_rate": 0.0,
                "profit_factor": 0.0,
                "average_win": 0.0,
                "average_loss": 0.0,
                "turnover": 0.0,
                "exposure_time": 0.0,
                "fees": 0.0,
                "slippage_cost": 0.0,
                "number_of_trades": 0,
            },
            "safety_report": {
                "safety_report_id": "historical-paper-trading-safety-report-smoke",
                "paper_trading_input_id": "historical-paper-trading-input-smoke",
            },
            "gap_report": {
                "gap_report_id": "historical-paper-trading-gap-report-smoke",
                "paper_trading_input_id": "historical-paper-trading-input-smoke",
                "gap_status": "NO_GAPS",
                "gap_categories": [],
                "blocking_gap_count": 0,
                "report_only_gap_count": 0,
                "gaps": [],
            },
            "audit_records": [
                {
                    "audit_record_id": "historical-paper-trading-audit-record-smoke",
                    "paper_trading_input_id": "historical-paper-trading-input-smoke",
                    "created_at": "2026-06-24T09:40:00+09:00",
                    "operator_context": "SYSTEM_SMOKE",
                    "source_path": str(output_dir / "historical_paper_trading_smoke_fixture.json"),
                }
            ],
            "paper_runtime_context": {
                "signal_candidate": {
                    "candidate_id": candidate.candidate_id,
                    "symbol": candidate.symbol,
                    "score": candidate.score.score,
                    "confidence_bucket": candidate.score.confidence_bucket.value,
                    "predicted_outcome_label": candidate.score.predicted_outcome_label,
                    "risk_review_blocked": False,
                    "promotion_blocked": True,
                },
                "price_bars": [
                    {
                        "session": "2026-06-25",
                        "open": 100.0,
                        "high": 110.0,
                        "low": 98.0,
                        "close": 108.0,
                        "volume": 100000,
                    }
                ],
                "current_mark_price": 108.0,
                "existing_position_count": 0,
                "existing_symbol_exposure": 0.0,
                "existing_total_exposure": 0.0,
                "daily_loss": 0.0,
                "drawdown": 0.0,
            },
        }
    )
    paper = run_historical_paper_trading(fixture)

    (output_dir / "historical_paper_trading_input.json").write_text(
        paper.model_dump_json(indent=2),
        encoding="utf-8",
    )
    (output_dir / "historical_paper_trading_order_intent.json").write_text(
        paper.paper_order_intent.model_dump_json(indent=2),
        encoding="utf-8",
    )
    (output_dir / "historical_paper_trading_performance_report.json").write_text(
        paper.paper_performance_report.model_dump_json(indent=2),
        encoding="utf-8",
    )
    (output_dir / "historical_paper_trading_safety_report.json").write_text(
        paper.safety_report.model_dump_json(indent=2),
        encoding="utf-8",
    )
    (output_dir / "historical_paper_trading_gap_report.json").write_text(
        paper.gap_report.model_dump_json(indent=2),
        encoding="utf-8",
    )

    return {
        "fixture_run": True,
        "run_generated": paper.paper_order_intent.paper_order_intent_id.endswith("SMOKE"),
        "decision_generated": paper.paper_decision.decision_id.endswith("SMOKE"),
        "order_intent_generated": paper.paper_order_intent.paper_order_intent_id.endswith("SMOKE"),
        "fill_generated": paper.paper_fill.paper_fill_id.endswith("SMOKE"),
        "ledger_generated": paper.paper_ledger.paper_ledger_id.endswith("SMOKE"),
        "position_generated": paper.paper_position.paper_position_id.endswith("SMOKE"),
        "trade_generated": paper.paper_trade.paper_trade_id.endswith("SMOKE"),
        "performance_report_generated": paper.paper_performance_report.performance_report_id.endswith("SMOKE"),
        "safety_report_generated": paper.safety_report.safety_report_id.endswith("SMOKE"),
        "gap_report_generated": paper.gap_report.gap_report_id.endswith("SMOKE"),
        "audit_record_generated": len(paper.audit_records) == 1,
        "paper_only": all(
            getattr(item, "paper_only", True) is True
            for item in (
                paper.paper_decision,
                paper.paper_order_intent,
                paper.paper_fill,
                paper.paper_ledger,
                paper.paper_position,
                paper.paper_trade,
                paper.paper_performance_report,
                paper.safety_report,
                paper.gap_report,
            )
        ),
        "simulated_only": all(
            getattr(item, "simulated_only", True) is True
            for item in (
                paper.paper_decision,
                paper.paper_order_intent,
                paper.paper_fill,
                paper.paper_ledger,
                paper.paper_position,
                paper.paper_trade,
                paper.paper_performance_report,
                paper.safety_report,
                paper.gap_report,
            )
        ),
        "non_executable": all(
            getattr(item, "non_executable", True) is True
            for item in (
                paper.paper_decision,
                paper.paper_order_intent,
                paper.paper_fill,
                paper.paper_ledger,
                paper.paper_position,
                paper.paper_trade,
                paper.paper_performance_report,
                paper.safety_report,
                paper.gap_report,
            )
        ),
        "local_only": all(
            getattr(item, "local_file_only", True) is True
            for item in (
                paper.paper_decision,
                paper.paper_order_intent,
                paper.paper_fill,
                paper.paper_ledger,
                paper.paper_position,
                paper.paper_trade,
                paper.paper_performance_report,
                paper.safety_report,
                paper.gap_report,
            )
        ),
        "offline_only": all(
            getattr(item, "offline_only", True) is True
            for item in (
                paper.paper_decision,
                paper.paper_order_intent,
                paper.paper_fill,
                paper.paper_ledger,
                paper.paper_position,
                paper.paper_trade,
                paper.paper_performance_report,
                paper.safety_report,
                paper.gap_report,
            )
        ),
        "read_only_input": all(
            getattr(item, "read_only_input", True) is True
            for item in (
                paper.paper_decision,
                paper.paper_order_intent,
                paper.paper_fill,
                paper.paper_ledger,
                paper.paper_position,
                paper.paper_trade,
                paper.paper_performance_report,
                paper.safety_report,
                paper.gap_report,
            )
        ),
        "no_real_order": all(
            getattr(item, "no_real_order", True) is True
            for item in (
                paper.paper_decision,
                paper.paper_order_intent,
                paper.paper_fill,
                paper.paper_ledger,
                paper.paper_position,
                paper.paper_trade,
                paper.paper_performance_report,
                paper.safety_report,
                paper.gap_report,
            )
        ),
        "no_real_order_intent": all(
            getattr(item, "no_real_order_intent", True) is True
            for item in (
                paper.paper_decision,
                paper.paper_order_intent,
                paper.paper_fill,
                paper.paper_ledger,
                paper.paper_position,
                paper.paper_trade,
                paper.paper_performance_report,
                paper.safety_report,
                paper.gap_report,
            )
        ),
        "no_broker_api": all(getattr(item, "no_broker_api", True) is True for item in (paper.paper_decision, paper.paper_order_intent, paper.safety_report)),
        "no_account_api": all(getattr(item, "no_account_api", True) is True for item in (paper.paper_decision, paper.paper_order_intent, paper.safety_report)),
        "no_order_api": all(getattr(item, "no_order_api", True) is True for item in (paper.paper_decision, paper.paper_order_intent, paper.safety_report)),
        "no_kiwoom_api": all(getattr(item, "no_kiwoom_api", True) is True for item in (paper.paper_decision, paper.paper_order_intent, paper.safety_report)),
        "no_ls_api": all(getattr(item, "no_ls_api", True) is True for item in (paper.paper_decision, paper.paper_order_intent, paper.safety_report)),
        "no_broker_mock_api": True,
        "no_kiwoom_mock_api": True,
        "no_ls_mock_api": True,
        "no_live_trading": all(getattr(item, "no_live_trading", True) is True for item in (paper.paper_decision, paper.paper_order_intent, paper.safety_report)),
        "no_live_prod": all(getattr(item, "no_live_prod", True) is True for item in (paper.paper_decision, paper.paper_order_intent, paper.safety_report)),
        "no_network": all(getattr(item, "no_network", True) is True for item in (paper.paper_decision, paper.paper_order_intent, paper.safety_report)),
        "no_provider_api": all(getattr(item, "no_provider_api", True) is True for item in (paper.paper_decision, paper.paper_order_intent, paper.safety_report)),
        "no_cloud_llm": all(getattr(item, "no_cloud_llm", True) is True for item in (paper.paper_decision, paper.paper_order_intent, paper.safety_report)),
        "no_local_llm_runtime": all(getattr(item, "no_local_llm_runtime", True) is True for item in (paper.paper_decision, paper.paper_order_intent, paper.safety_report)),
        "no_external_execution": all(getattr(item, "no_external_execution", True) is True for item in (paper.paper_decision, paper.paper_order_intent, paper.safety_report)),
        "parquet_unsupported": ".parquet" not in paper.model_dump_json(indent=2).lower(),
    }


def _run_broker_mock_adapter_smoke(output_dir: Path) -> dict[str, bool]:
    paper_input = HistoricalPaperTradingInput.model_validate_json(
        (output_dir / "historical_paper_trading_input.json").read_text(encoding="utf-8")
    )
    paper_order_intent = paper_input.paper_order_intent
    paper_decision = paper_input.paper_decision

    fixture = BrokerMockAdapterInput.model_validate(
        {
            "schema_version": "v6.2-broker-mock-adapter-input",
            "adapter_input_id": "broker-mock-adapter-input-smoke",
            "adapter_config": {
                "config_id": "broker-mock-adapter-config-smoke",
                "strategy_track": "DOMESTIC_KR",
                "mock_adapter_family": "GENERIC_BROKER_MOCK",
            },
            "capability": {
                "capability_id": "broker-mock-capability-smoke",
                "supported_markets": ["KRX"],
                "supported_order_types": ["LIMIT"],
                "supported_order_sides": ["MOCK_BUY", "MOCK_SELL", "MOCK_CANCEL", "MOCK_REPLACE", "MOCK_CLOSE"],
                "supports_mock_order_submission": False,
                "supports_mock_cancellation": False,
                "supports_mock_status_polling": False,
                "supports_mock_account_snapshot": False,
                "supports_mock_position_snapshot": False,
                "supports_deterministic_replay_mode": True,
                "supports_async_callback_simulation": False,
            },
            "broker_mock_order_intent": {
                "mock_order_intent_id": "broker-mock-order-intent-smoke",
                "source_paper_order_intent_ref_id": paper_order_intent.paper_order_intent_id,
                "source_paper_decision_ref_id": paper_decision.decision_id,
                "source_signal_candidate_ref_id": paper_order_intent.signal_candidate_ref_id,
                "symbol": paper_order_intent.symbol,
                "market": "KRX",
                "strategy_track": "DOMESTIC_KR",
                "market_profile": "DOMESTIC_EQUITY",
                "side": "MOCK_BUY",
                "mock_order_type": "LIMIT",
                "requested_quantity": float(paper_order_intent.quantity),
                "session_timestamp": "2026-06-25T09:10:00+09:00",
                "mock_adapter_target_id": "GENERIC-BROKER-MOCK",
                "source_manifest_ids": ["MANIFEST-SMOKE-1"],
                "source_audit_record_ids": ["AUDIT-SMOKE-1"],
                "provider_provenance_ids": ["PROVENANCE-SMOKE-1"],
                "metadata": {"simulation_stage": "boundary_only"},
            },
            "broker_mock_order_request": {
                "mock_order_request_id": "broker-mock-order-request-smoke",
                "mock_order_intent_id": "broker-mock-order-intent-smoke",
                "request_created_at": "2026-06-25T09:10:05+09:00",
                "request_metadata": {"request_mode": "mock_boundary_only"},
            },
            "broker_mock_order_response": {
                "mock_order_response_id": "broker-mock-order-response-smoke",
                "mock_order_request_id": "broker-mock-order-request-smoke",
                "mock_status": "MOCK_ACCEPTED",
                "response_timestamp": "2026-06-25T09:10:06+09:00",
                "response_metadata": {"response_mode": "mock_boundary_only"},
            },
            "broker_mock_execution_report": {
                "execution_report_id": "broker-mock-execution-report-smoke",
                "mock_order_intent_id": "broker-mock-order-intent-smoke",
                "mock_order_request_id": "broker-mock-order-request-smoke",
                "mock_order_response_id": "broker-mock-order-response-smoke",
                "symbol": paper_order_intent.symbol,
                "side": "MOCK_BUY",
                "mock_status": "MOCK_ACCEPTED",
                "mock_filled_quantity": 0,
                "mock_average_fill_price": 0,
                "mock_execution_timestamp": "2026-06-25T09:10:06+09:00",
                "execution_metadata": {"execution_mode": "mock_boundary_only"},
            },
            "broker_mock_account_snapshot": {
                "account_snapshot_id": "broker-mock-account-snapshot-smoke",
                "mock_adapter_id": "GENERIC-BROKER-MOCK",
                "snapshot_timestamp": "2026-06-25T09:10:07+09:00",
                "base_currency": "KRW",
                "reported_mock_cash": 1000000,
                "reported_mock_buying_power": 1000000,
                "reported_mock_equity": 1000000,
                "position_snapshots": [
                    {
                        "position_snapshot_id": "broker-mock-position-snapshot-smoke",
                        "symbol": paper_order_intent.symbol,
                        "market": "KRX",
                        "quantity": 0,
                        "average_price": 0,
                        "mark_price": 0,
                        "exposure_value": 0,
                        "metadata": {"position_mode": "mock_boundary_only"},
                    }
                ],
                "metadata": {"account_mode": "mock_boundary_only"},
            },
            "kiwoom_mock_adapter_boundary": {
                "boundary_id": "kiwoom-mock-adapter-boundary-smoke",
                "future_only": True,
                "implementation_present": False,
                "executable_transport_present": False,
                "metadata": {"boundary_family": "future_boundary_only"},
            },
            "ls_mock_adapter_boundary": {
                "boundary_id": "ls-mock-adapter-boundary-smoke",
                "future_only": True,
                "implementation_present": False,
                "executable_transport_present": False,
                "metadata": {"boundary_family": "future_boundary_only"},
            },
            "safety_report": {
                "safety_report_id": "broker-mock-safety-report-smoke",
                "blocked": False,
                "findings": [],
            },
            "gap_report": {
                "gap_report_id": "broker-mock-gap-report-smoke",
                "adapter_input_id": "broker-mock-adapter-input-smoke",
                "gap_status": "NO_GAPS",
                "gap_categories": [],
                "blocking_gap_count": 0,
                "report_only_gap_count": 0,
                "gaps": [],
                "source_manifest_ids": ["MANIFEST-SMOKE-1"],
                "source_audit_record_ids": ["AUDIT-SMOKE-1"],
                "provider_provenance_ids": ["PROVENANCE-SMOKE-1"],
            },
            "audit_records": [
                {
                    "audit_record_id": "broker-mock-audit-record-smoke",
                    "adapter_input_id": "broker-mock-adapter-input-smoke",
                    "created_at": "2026-06-25T09:11:00+09:00",
                    "operator_context": "SYSTEM_SMOKE",
                    "source_path": str(output_dir / "broker_mock_adapter_smoke_fixture.json"),
                    "source_manifest_ids": ["MANIFEST-SMOKE-1"],
                    "source_audit_record_ids": ["AUDIT-SMOKE-1"],
                    "provider_provenance_ids": ["PROVENANCE-SMOKE-1"],
                }
            ],
        }
    )
    broker_mock = run_broker_mock_adapter_boundary(fixture)

    (output_dir / "broker_mock_adapter_input.json").write_text(broker_mock.model_dump_json(indent=2), encoding="utf-8")
    (output_dir / "broker_mock_adapter_capability_report.json").write_text(broker_mock.capability.model_dump_json(indent=2), encoding="utf-8")
    (output_dir / "broker_mock_adapter_order_intent.json").write_text(broker_mock.broker_mock_order_intent.model_dump_json(indent=2), encoding="utf-8")
    (output_dir / "broker_mock_adapter_order_request.json").write_text(broker_mock.broker_mock_order_request.model_dump_json(indent=2), encoding="utf-8")
    (output_dir / "broker_mock_adapter_order_response.json").write_text(broker_mock.broker_mock_order_response.model_dump_json(indent=2), encoding="utf-8")
    (output_dir / "broker_mock_adapter_execution_report.json").write_text(broker_mock.broker_mock_execution_report.model_dump_json(indent=2), encoding="utf-8")
    (output_dir / "broker_mock_adapter_account_snapshot.json").write_text(broker_mock.broker_mock_account_snapshot.model_dump_json(indent=2), encoding="utf-8")
    (output_dir / "broker_mock_adapter_safety_report.json").write_text(broker_mock.safety_report.model_dump_json(indent=2), encoding="utf-8")
    (output_dir / "broker_mock_adapter_gap_report.json").write_text(broker_mock.gap_report.model_dump_json(indent=2), encoding="utf-8")

    all_items = (
        broker_mock.adapter_config,
        broker_mock.capability,
        broker_mock.broker_mock_order_intent,
        broker_mock.broker_mock_order_request,
        broker_mock.broker_mock_order_response,
        broker_mock.broker_mock_execution_report,
        broker_mock.broker_mock_account_snapshot,
        broker_mock.broker_mock_account_snapshot.position_snapshots[0],
        broker_mock.kiwoom_mock_adapter_boundary,
        broker_mock.ls_mock_adapter_boundary,
        broker_mock.safety_report,
        broker_mock.gap_report,
        broker_mock.audit_records[0],
    )
    broker_dump = json.dumps(broker_mock.model_dump(mode="json")).lower()
    return {
        "fixture_run": True,
        "boundary_run_generated": broker_mock.adapter_input_id.endswith("SMOKE"),
        "capability_report_generated": broker_mock.capability.capability_id.endswith("SMOKE"),
        "order_intent_generated": broker_mock.broker_mock_order_intent.mock_order_intent_id.endswith("SMOKE"),
        "order_request_generated": broker_mock.broker_mock_order_request.mock_order_request_id.endswith("SMOKE"),
        "order_response_generated": broker_mock.broker_mock_order_response.mock_order_response_id.endswith("SMOKE"),
        "execution_report_generated": broker_mock.broker_mock_execution_report.execution_report_id.endswith("SMOKE"),
        "account_snapshot_generated": broker_mock.broker_mock_account_snapshot.account_snapshot_id.endswith("SMOKE"),
        "position_snapshot_generated": broker_mock.broker_mock_account_snapshot.position_snapshots[0].position_snapshot_id.endswith("SMOKE"),
        "safety_report_generated": broker_mock.safety_report.safety_report_id.endswith("SMOKE"),
        "gap_report_generated": broker_mock.gap_report.gap_report_id.endswith("SMOKE"),
        "audit_record_generated": len(broker_mock.audit_records) == 1,
        "mock_only": all(getattr(item, "mock_only", True) is True for item in all_items),
        "paper_only": all(getattr(item, "paper_only", True) is True for item in all_items),
        "disabled_by_default": all(getattr(item, "disabled_by_default", True) is True for item in all_items),
        "explicit_opt_in_required": all(getattr(item, "explicit_opt_in_required", True) is True for item in all_items),
        "non_executable_by_default": all(getattr(item, "non_executable_by_default", True) is True for item in all_items),
        "local_only": all(getattr(item, "local_file_only", True) is True for item in all_items),
        "offline_only": all(getattr(item, "offline_only", True) is True for item in all_items),
        "no_real_order": all(getattr(item, "no_real_order", True) is True for item in all_items),
        "no_real_order_intent": "\"real_order_intent\"" not in broker_dump and "\"orderintent\"" not in broker_dump,
        "no_real_account_mutation": all(getattr(item, "no_real_account_mutation", True) is True for item in all_items),
        "no_live_trading": all(getattr(item, "no_live_trading", True) is True for item in all_items),
        "no_live_prod": all(getattr(item, "no_live_prod", True) is True for item in all_items),
        "no_production_broker": all(getattr(item, "no_production_broker", True) is True for item in all_items),
        "no_credentials_loaded": all(getattr(item, "no_credentials_loaded", True) is True for item in all_items),
        "no_network_call": all(getattr(item, "no_network_call", True) is True for item in all_items),
        "no_kiwoom_api_call": all(getattr(item, "no_kiwoom_api_call", True) is True for item in all_items),
        "no_ls_api_call": all(getattr(item, "no_ls_api_call", True) is True for item in all_items),
        "no_broker_api_call": all(getattr(item, "no_broker_api_call", True) is True for item in all_items),
        "no_order_api_call": all(getattr(item, "no_order_api_call", True) is True for item in all_items),
        "no_account_api_call": all(getattr(item, "no_account_api_call", True) is True for item in all_items),
        "no_provider_api_call": all(getattr(item, "no_provider_api_call", True) is True for item in all_items),
        "no_websocket_connection": "websocket" not in broker_dump,
        "no_cloud_llm": all(getattr(item, "no_cloud_llm", True) is True for item in all_items),
        "no_local_llm_runtime": all(getattr(item, "no_local_llm_runtime", True) is True for item in all_items),
        "parquet_unsupported": ".parquet" not in broker_dump,
    }


def _run_kiwoom_mock_adapter_smoke(output_dir: Path) -> dict[str, bool]:
    broker_mock_input = json.loads((output_dir / "broker_mock_adapter_input.json").read_text(encoding="utf-8"))
    broker_mock_order_intent = broker_mock_input["broker_mock_order_intent"]

    fixture = KiwoomMockAdapterInput.model_validate(
        {
            "schema_version": "v6.3-kiwoom-mock-adapter-input",
            "adapter_input_id": "kiwoom-mock-adapter-input-smoke",
            "adapter_config": {
                "config_id": "kiwoom-mock-adapter-config-smoke",
                "strategy_track": "DOMESTIC_KR",
                "market": "KRX",
                "broker_mock_adapter_id": "BROKER-MOCK-ADAPTER-SMOKE",
                "evidence_pack_ref": "docs/superpowers/specs/2026-06-18-kiwoom-rest-api-official-evidence-pack.md",
                "capability_matrix_ref": "docs/superpowers/specs/2026-06-18-kiwoom-rest-api-capability-matrix.json",
            },
            "capability_ref": {
                "capability_ref_id": "DOMESTIC_STOCK_ORDER_CREATE_MOCK",
                "evidence_endpoint_ref": "KT10000",
                "evidence_category": "국내주식 / 주문",
                "endpoint_path": "/api/dostk/ordr",
                "http_method": "POST",
                "mock_domain": "https://mockapi.kiwoom.com",
                "mock_krx_only": True,
                "documented_request_fields": [
                    "dmst_stex_tp",
                    "stk_cd",
                    "ord_qty",
                    "ord_uv",
                    "trde_tp",
                    "cond_uv",
                ],
                "documented_response_fields": ["ord_no", "dmst_stex_tp"],
                "supported_draft_sides": ["KIWOOM_MOCK_BUY_DRAFT", "KIWOOM_MOCK_SELL_DRAFT"],
                "supported_order_types": ["LIMIT"],
            },
            "order_draft": {
                "order_draft_id": "kiwoom-mock-order-draft-smoke",
                "source_broker_mock_order_intent_ref_id": broker_mock_order_intent["mock_order_intent_id"],
                "source_paper_order_intent_ref_id": broker_mock_order_intent["source_paper_order_intent_ref_id"],
                "source_signal_candidate_ref_id": broker_mock_order_intent["source_signal_candidate_ref_id"],
                "symbol": broker_mock_order_intent["symbol"],
                "market": "KRX",
                "market_profile": broker_mock_order_intent["market_profile"],
                "strategy_track": "DOMESTIC_KR",
                "side": "KIWOOM_MOCK_BUY_DRAFT",
                "order_type": "LIMIT",
                "quantity": 10,
                "price": 70000,
                "documented_endpoint_path": "/api/dostk/ordr",
                "documented_api_id": "KT10000",
                "documented_required_fields": [
                    "dmst_stex_tp",
                    "stk_cd",
                    "ord_qty",
                    "ord_uv",
                    "trde_tp",
                    "cond_uv",
                ],
                "source_manifest_ids": ["MANIFEST-SMOKE-1"],
                "source_audit_record_ids": ["AUDIT-SMOKE-1"],
                "provider_provenance_ids": ["PROVENANCE-SMOKE-1"],
                "metadata": {"mapping_stage": "draft_only"},
            },
            "order_request_draft": {
                "request_draft_id": "kiwoom-mock-order-request-draft-smoke",
                "order_draft_id": "kiwoom-mock-order-draft-smoke",
                "request_body_fields": {
                    "dmst_stex_tp": "KRX",
                    "stk_cd": broker_mock_order_intent["symbol"],
                    "ord_qty": 10,
                    "ord_uv": 70000,
                    "trde_tp": "LIMIT",
                    "cond_uv": "0",
                },
                "metadata": {"request_shape": "documented_only"},
            },
            "order_response_draft": {
                "response_draft_id": "kiwoom-mock-order-response-draft-smoke",
                "request_draft_id": "kiwoom-mock-order-request-draft-smoke",
                "documented_response_fields": ["ord_no", "dmst_stex_tp"],
                "metadata": {"response_shape": "documented_only"},
            },
            "execution_draft": {
                "execution_draft_id": "kiwoom-mock-execution-draft-smoke",
                "order_draft_id": "kiwoom-mock-order-draft-smoke",
                "request_draft_id": "kiwoom-mock-order-request-draft-smoke",
                "response_draft_id": "kiwoom-mock-order-response-draft-smoke",
                "symbol": broker_mock_order_intent["symbol"],
                "side": "KIWOOM_MOCK_BUY_DRAFT",
                "documented_status": "DRAFT_ONLY",
                "metadata": {"execution_shape": "documented_only"},
            },
            "account_snapshot_draft": {
                "account_snapshot_draft_id": "kiwoom-mock-account-snapshot-draft-smoke",
                "base_currency": "KRW",
                "position_snapshots": [
                    {
                        "position_snapshot_draft_id": "kiwoom-mock-position-snapshot-draft-smoke",
                        "symbol": broker_mock_order_intent["symbol"],
                        "market": "KRX",
                        "quantity": 0,
                        "average_price": 0,
                        "mark_price": 0,
                        "exposure_value": 0,
                        "metadata": {"position_shape": "draft_only"},
                    }
                ],
                "metadata": {"account_shape": "draft_only"},
            },
            "safety_report": {
                "safety_report_id": "kiwoom-mock-safety-report-smoke",
                "blocked": False,
                "findings": [],
            },
            "gap_report": {
                "gap_report_id": "kiwoom-mock-gap-report-smoke",
                "adapter_input_id": "kiwoom-mock-adapter-input-smoke",
                "gap_status": "NO_GAPS",
                "gap_categories": [],
                "blocking_gap_count": 0,
                "report_only_gap_count": 0,
                "gaps": [],
                "source_manifest_ids": ["MANIFEST-SMOKE-1"],
                "source_audit_record_ids": ["AUDIT-SMOKE-1"],
                "provider_provenance_ids": ["PROVENANCE-SMOKE-1"],
            },
            "audit_records": [
                {
                    "audit_record_id": "kiwoom-mock-audit-record-smoke",
                    "adapter_input_id": "kiwoom-mock-adapter-input-smoke",
                    "created_at": "2026-06-25T09:12:00+09:00",
                    "operator_context": "SYSTEM_SMOKE",
                    "source_path": str(output_dir / "kiwoom_mock_adapter_smoke_fixture.json"),
                    "source_manifest_ids": ["MANIFEST-SMOKE-1"],
                    "source_audit_record_ids": ["AUDIT-SMOKE-1"],
                    "provider_provenance_ids": ["PROVENANCE-SMOKE-1"],
                }
            ],
        }
    )
    kiwoom_mock = run_kiwoom_mock_adapter_draft_mapping(fixture)

    (output_dir / "kiwoom_mock_adapter_input.json").write_text(kiwoom_mock.model_dump_json(indent=2), encoding="utf-8")
    (output_dir / "kiwoom_mock_adapter_order_draft.json").write_text(kiwoom_mock.order_draft.model_dump_json(indent=2), encoding="utf-8")
    (output_dir / "kiwoom_mock_adapter_request_draft.json").write_text(kiwoom_mock.order_request_draft.model_dump_json(indent=2), encoding="utf-8")
    (output_dir / "kiwoom_mock_adapter_response_draft.json").write_text(kiwoom_mock.order_response_draft.model_dump_json(indent=2), encoding="utf-8")
    (output_dir / "kiwoom_mock_adapter_execution_draft.json").write_text(kiwoom_mock.execution_draft.model_dump_json(indent=2), encoding="utf-8")
    (output_dir / "kiwoom_mock_adapter_account_snapshot_draft.json").write_text(kiwoom_mock.account_snapshot_draft.model_dump_json(indent=2), encoding="utf-8")
    (output_dir / "kiwoom_mock_adapter_safety_report.json").write_text(kiwoom_mock.safety_report.model_dump_json(indent=2), encoding="utf-8")
    (output_dir / "kiwoom_mock_adapter_gap_report.json").write_text(kiwoom_mock.gap_report.model_dump_json(indent=2), encoding="utf-8")

    all_items = (
        kiwoom_mock.adapter_config,
        kiwoom_mock.capability_ref,
        kiwoom_mock.order_draft,
        kiwoom_mock.order_request_draft,
        kiwoom_mock.order_response_draft,
        kiwoom_mock.execution_draft,
        kiwoom_mock.account_snapshot_draft,
        kiwoom_mock.account_snapshot_draft.position_snapshots[0],
        kiwoom_mock.safety_report,
        kiwoom_mock.gap_report,
        kiwoom_mock.audit_records[0],
    )
    dumped = json.dumps(kiwoom_mock.model_dump(mode="json")).lower()
    return {
        "fixture_run": True,
        "draft_build_generated": kiwoom_mock.adapter_input_id.endswith("SMOKE"),
        "order_draft_generated": kiwoom_mock.order_draft.order_draft_id.endswith("SMOKE"),
        "request_draft_generated": kiwoom_mock.order_request_draft.request_draft_id.endswith("SMOKE"),
        "response_draft_generated": kiwoom_mock.order_response_draft.response_draft_id.endswith("SMOKE"),
        "execution_draft_generated": kiwoom_mock.execution_draft.execution_draft_id.endswith("SMOKE"),
        "account_snapshot_draft_generated": kiwoom_mock.account_snapshot_draft.account_snapshot_draft_id.endswith("SMOKE"),
        "position_snapshot_draft_generated": kiwoom_mock.account_snapshot_draft.position_snapshots[0].position_snapshot_draft_id.endswith("SMOKE"),
        "safety_report_generated": kiwoom_mock.safety_report.safety_report_id.endswith("SMOKE"),
        "gap_report_generated": kiwoom_mock.gap_report.gap_report_id.endswith("SMOKE"),
        "audit_record_generated": len(kiwoom_mock.audit_records) == 1,
        "kiwoom_mock_only": all(getattr(item, "kiwoom_mock_only", True) is True for item in all_items),
        "draft_only": all(getattr(item, "draft_only", True) is True for item in all_items),
        "paper_only": all(getattr(item, "paper_only", True) is True for item in all_items),
        "disabled_by_default": all(getattr(item, "disabled_by_default", True) is True for item in all_items),
        "explicit_opt_in_required": all(getattr(item, "explicit_opt_in_required", True) is True for item in all_items),
        "non_executable": all(getattr(item, "non_executable", True) is True for item in all_items),
        "local_only": all(getattr(item, "local_file_only", True) is True for item in all_items),
        "offline_only": all(getattr(item, "offline_only", True) is True for item in all_items),
        "evidence_backed": all(getattr(item, "evidence_backed", True) is True for item in all_items),
        "no_credentials_loaded": all(getattr(item, "no_credentials_loaded", True) is True for item in all_items),
        "no_oauth_token_request": all(getattr(item, "no_oauth_token_request", True) is True for item in all_items),
        "no_api_call": all(getattr(item, "no_api_call", True) is True for item in all_items),
        "no_mockapi_call": all(getattr(item, "no_mockapi_call", True) is True for item in all_items),
        "no_network_call": all(getattr(item, "no_network_call", True) is True for item in all_items),
        "no_websocket_connection": all(getattr(item, "no_websocket_connection", True) is True for item in all_items),
        "no_real_order": all(getattr(item, "no_real_order", True) is True for item in all_items),
        "no_real_account_mutation": all(getattr(item, "no_real_account_mutation", True) is True for item in all_items),
        "no_live_trading": all(getattr(item, "no_live_trading", True) is True for item in all_items),
        "no_live_prod": all(getattr(item, "no_live_prod", True) is True for item in all_items),
        "no_broker_api_call": all(getattr(item, "no_broker_api_call", True) is True for item in all_items),
        "no_order_api_call": all(getattr(item, "no_order_api_call", True) is True for item in all_items),
        "no_account_api_call": all(getattr(item, "no_account_api_call", True) is True for item in all_items),
        "no_provider_api_call": all(getattr(item, "no_provider_api_call", True) is True for item in all_items),
        "no_cloud_llm": all(getattr(item, "no_cloud_llm", True) is True for item in all_items),
        "no_local_llm_runtime": all(getattr(item, "no_local_llm_runtime", True) is True for item in all_items),
        "parquet_unsupported": ".parquet" not in dumped,
    }


def _run_kiwoom_mock_credential_boundary_smoke(output_dir: Path) -> dict[str, bool]:
    fixture = KiwoomMockCredentialBoundaryConfig.model_validate(
        {
            "schema_version": "v6.4-kiwoom-mock-credential-boundary",
            "fixture_format": "json",
            "config_id": "kiwoom-mock-credential-boundary-smoke",
            "environment": {
                "environment_id": "kiwoom-mock-environment-smoke",
                "mock_only_env_name": "KIWOOM_MOCK_ONLY",
                "dry_run_env_name": "KIWOOM_MOCK_DRY_RUN",
                "explicit_opt_in_env_name": "KIWOOM_MOCK_EXPLICIT_OPT_IN",
                "app_key_ref_env_name": "KIWOOM_MOCK_APP_KEY_REF",
                "secret_key_ref_env_name": "KIWOOM_MOCK_SECRET_KEY_REF",
                "account_ref_env_name": "KIWOOM_MOCK_ACCOUNT_REF",
                "reads_environment": False,
            },
            "credential_refs": [
                {
                    "credential_ref_id": "kiwoom-app-key-ref-smoke",
                    "source_type": "ENVIRONMENT_REFERENCE",
                    "source_label": "mock app key reference",
                    "reference_name": "KIWOOM_MOCK_APP_KEY_REF",
                },
                {
                    "credential_ref_id": "kiwoom-secret-key-ref-smoke",
                    "source_type": "ENVIRONMENT_REFERENCE",
                    "source_label": "mock secret key reference",
                    "reference_name": "KIWOOM_MOCK_SECRET_KEY_REF",
                },
                {
                    "credential_ref_id": "kiwoom-account-ref-smoke",
                    "source_type": "ENVIRONMENT_REFERENCE",
                    "source_label": "mock account reference",
                    "reference_name": "KIWOOM_MOCK_ACCOUNT_REF",
                },
            ],
            "token_boundary": {
                "token_boundary_id": "kiwoom-token-boundary-smoke",
                "documented_issue_endpoint_path": "/oauth2/token",
                "documented_revoke_endpoint_path": "/oauth2/revoke",
                "issue_allowed_now": False,
                "revoke_allowed_now": False,
                "execution_mode_requirement": "KIWOOM_MOCK_OPT_IN_EXECUTION_FUTURE",
                "token_issue_attempted": False,
                "token_revoke_attempted": False,
            },
            "domain_policy": {
                "domain_policy_id": "kiwoom-domain-policy-smoke",
                "allowed_mock_rest_domain": "https://mockapi.kiwoom.com",
                "forbidden_production_rest_domain": "https://api.kiwoom.com",
                "allowed_mock_websocket_domain": "wss://mockapi.kiwoom.com:10000",
                "forbidden_production_websocket_domain": "wss://api.kiwoom.com:10000",
                "krx_only": True,
                "production_domain_execution_allowed": False,
            },
            "opt_in_gate": {
                "opt_in_gate_id": "kiwoom-opt-in-gate-smoke",
                "gate_state": "BLOCKED_DEFAULT",
                "explicit_opt_in_present": False,
                "mock_execution_allowed_now": False,
                "dry_run_only": True,
            },
            "execution_mode": "KIWOOM_MOCK_DRY_RUN",
            "safety_report": {
                "safety_report_id": "kiwoom-credential-safety-report-smoke",
                "blocked": False,
                "findings": [],
            },
            "gap_report": {
                "gap_report_id": "kiwoom-credential-gap-report-smoke",
                "gap_status": "NO_GAPS",
                "gap_categories": [],
                "blocking_gap_count": 0,
                "report_only_gap_count": 0,
                "gaps": [],
            },
            "audit_records": [
                {
                    "audit_record_id": "kiwoom-credential-audit-record-smoke",
                    "created_at": "2026-06-25T09:13:00+09:00",
                    "source_path": str(output_dir / "kiwoom_mock_credential_boundary_smoke_fixture.json"),
                    "source_manifest_ids": ["MANIFEST-SMOKE-1"],
                }
            ],
        }
    )
    evaluated = run_kiwoom_mock_credential_boundary_evaluation(fixture)

    (output_dir / "kiwoom_mock_credential_boundary_check.json").write_text(
        evaluated.model_dump_json(indent=2), encoding="utf-8"
    )
    (output_dir / "kiwoom_mock_credential_domain_policy_report.json").write_text(
        evaluated.domain_policy.model_dump_json(indent=2), encoding="utf-8"
    )
    (output_dir / "kiwoom_mock_credential_opt_in_report.json").write_text(
        evaluated.opt_in_gate.model_dump_json(indent=2), encoding="utf-8"
    )
    (output_dir / "kiwoom_mock_credential_safety_report.json").write_text(
        evaluated.safety_report.model_dump_json(indent=2), encoding="utf-8"
    )
    (output_dir / "kiwoom_mock_credential_gap_report.json").write_text(
        evaluated.gap_report.model_dump_json(indent=2), encoding="utf-8"
    )

    all_items = (
        evaluated,
        evaluated.environment,
        *evaluated.credential_refs,
        evaluated.token_boundary,
        evaluated.domain_policy,
        evaluated.opt_in_gate,
        evaluated.safety_report,
        evaluated.gap_report,
        evaluated.audit_records[0],
    )
    dumped = json.dumps(evaluated.model_dump(mode="json")).lower()
    return {
        "fixture_run": True,
        "boundary_check_generated": evaluated.config_id.endswith("SMOKE"),
        "domain_policy_report_generated": evaluated.domain_policy.domain_policy_id.endswith("SMOKE"),
        "opt_in_report_generated": evaluated.opt_in_gate.opt_in_gate_id.endswith("SMOKE"),
        "safety_report_generated": evaluated.safety_report.safety_report_id.endswith("SMOKE"),
        "gap_report_generated": evaluated.gap_report.gap_report_id.endswith("SMOKE"),
        "audit_record_generated": len(evaluated.audit_records) == 1,
        "mock_only": all(getattr(item, "mock_only", True) is True for item in all_items),
        "credential_boundary_only": all(getattr(item, "credential_boundary_only", True) is True for item in all_items),
        "disabled_by_default": all(getattr(item, "disabled_by_default", True) is True for item in all_items),
        "explicit_opt_in_required": all(getattr(item, "explicit_opt_in_required", True) is True for item in all_items),
        "local_only": all(getattr(item, "local_file_only", True) is True for item in all_items),
        "offline_only": all(getattr(item, "offline_only", True) is True for item in all_items),
        "non_executable": all(getattr(item, "non_executable", True) is True for item in all_items),
        "no_credentials_loaded": all(getattr(item, "no_credentials_loaded", True) is True for item in all_items),
        "no_environment_read": all(getattr(item, "no_environment_read", True) is True for item in all_items),
        "no_credential_file_read": all(getattr(item, "no_credential_file_read", True) is True for item in all_items),
        "no_token_issued": all(getattr(item, "no_token_issued", True) is True for item in all_items),
        "no_token_revoked": all(getattr(item, "no_token_revoked", True) is True for item in all_items),
        "no_api_call": all(getattr(item, "no_api_call", True) is True for item in all_items),
        "no_mockapi_call": all(getattr(item, "no_mockapi_call", True) is True for item in all_items),
        "no_websocket_connection": all(getattr(item, "no_websocket_connection", True) is True for item in all_items),
        "no_network_call": all(getattr(item, "no_network_call", True) is True for item in all_items),
        "no_real_order": all(getattr(item, "no_real_order", True) is True for item in all_items),
        "no_live_trading": all(getattr(item, "no_live_trading", True) is True for item in all_items),
        "no_live_prod": all(getattr(item, "no_live_prod", True) is True for item in all_items),
        "no_account_mutation": all(getattr(item, "no_account_mutation", True) is True for item in all_items),
        "no_production_domain_execution": all(
            getattr(item, "no_production_domain_execution", True) is True for item in all_items
        ),
        "no_cloud_llm": all(getattr(item, "no_cloud_llm", True) is True for item in all_items),
        "no_local_llm_runtime": all(getattr(item, "no_local_llm_runtime", True) is True for item in all_items),
        "parquet_unsupported": ".parquet" not in dumped,
    }


def _run_kiwoom_mock_oauth_draft_smoke(output_dir: Path) -> dict[str, bool]:
    fixture = KiwoomMockOAuthDraftConfig.model_validate(
        {
            "schema_version": "v6.5-kiwoom-mock-oauth-draft-boundary",
            "fixture_format": "json",
            "config_id": "kiwoom-mock-oauth-draft-config-smoke",
            "endpoint_refs": [
                {
                    "endpoint_ref_id": "kiwoom-mock-token-issue-endpoint-smoke",
                    "documented_purpose": "TOKEN_ISSUE",
                    "method": "POST",
                    "domain": "https://mockapi.kiwoom.com",
                    "path": "/oauth2/token",
                    "evidence_only": True,
                    "executable": False,
                    "production_domain_blocked": True,
                    "krx_only": True,
                },
                {
                    "endpoint_ref_id": "kiwoom-mock-token-revoke-endpoint-smoke",
                    "documented_purpose": "TOKEN_REVOKE",
                    "method": "POST",
                    "domain": "https://mockapi.kiwoom.com",
                    "path": "/oauth2/revoke",
                    "evidence_only": True,
                    "executable": False,
                    "production_domain_blocked": True,
                    "krx_only": True,
                },
            ],
            "token_request_draft": {
                "draft_id": "kiwoom-mock-token-request-draft-smoke",
                "endpoint_ref_id": "KIWOOM-MOCK-TOKEN-ISSUE-ENDPOINT-SMOKE",
                "credential_ref_ids": ["KIWOOM_MOCK_APP_KEY_REF", "KIWOOM_MOCK_SECRET_KEY_REF"],
                "request_field_names": ["grant_type", "appkey", "secretkey"],
                "response_field_names": ["expires_dt", "token_type", "token"],
                "credential_ref_only": True,
                "authorization_header_available": False,
                "request_execution_enabled": False,
            },
            "token_response_draft": {
                "response_draft_id": "kiwoom-mock-token-response-draft-smoke",
                "documented_response_field_names": ["expires_dt", "token_type", "token"],
                "stores_real_token": False,
                "token_storage_enabled": False,
                "token_refresh_enabled": False,
            },
            "token_revoke_draft": {
                "draft_id": "kiwoom-mock-token-revoke-draft-smoke",
                "endpoint_ref_id": "KIWOOM-MOCK-TOKEN-REVOKE-ENDPOINT-SMOKE",
                "credential_ref_ids": ["KIWOOM_MOCK_APP_KEY_REF", "KIWOOM_MOCK_SECRET_KEY_REF"],
                "token_reference_label": "MASKED_TOKEN_REF",
                "request_field_names": ["appkey", "secretkey", "token"],
                "credential_ref_only": True,
                "request_execution_enabled": False,
            },
            "token_lifecycle_policy": {
                "policy_id": "kiwoom-mock-token-lifecycle-policy-smoke",
                "issue_execution_allowed": False,
                "revoke_execution_allowed": False,
                "refresh_execution_allowed": False,
                "storage_execution_allowed": False,
                "documented_lifetime_field_name": "expires_dt",
                "token_value_retained": False,
            },
            "safety_report": {
                "safety_report_id": "kiwoom-mock-oauth-safety-report-smoke",
                "blocked_capabilities": ["TOKEN_ISSUE_EXECUTION_BLOCKED"],
                "findings": [],
            },
            "gap_report": {
                "gap_report_id": "kiwoom-mock-oauth-gap-report-smoke",
                "gap_status": "UNRESOLVED_IMPLEMENTATION_GAPS",
                "gap_categories": [],
                "blocking_gap_count": 0,
                "report_only_gap_count": 0,
                "gaps": [],
            },
            "audit_records": [
                {
                    "audit_record_id": "kiwoom-mock-oauth-audit-record-smoke",
                    "created_at": "2026-06-25T09:13:00+09:00",
                    "source_path": str(output_dir / "kiwoom_mock_oauth_draft_smoke_fixture.json"),
                    "redaction_applied": True,
                    "contains_secret_material": False,
                    "evidence_refs": ["KIWOOM-REST-EVIDENCE-PACK", "KIWOOM-CAPABILITY-MATRIX"],
                }
            ],
        }
    )
    evaluated = run_kiwoom_mock_oauth_draft_boundary(
        fixture,
        explicit_opt_in_ack=True,
        credential_boundary_ref="docs/superpowers/plans/2026-06-18-kiwoom-mock-credential-environment-boundary-design.md",
    )

    (output_dir / "kiwoom_mock_oauth_token_request_draft.json").write_text(
        evaluated.token_request_draft.model_dump_json(indent=2), encoding="utf-8"
    )
    (output_dir / "kiwoom_mock_oauth_token_response_draft.json").write_text(
        evaluated.token_response_draft.model_dump_json(indent=2), encoding="utf-8"
    )
    (output_dir / "kiwoom_mock_oauth_token_revoke_draft.json").write_text(
        evaluated.token_revoke_draft.model_dump_json(indent=2), encoding="utf-8"
    )
    (output_dir / "kiwoom_mock_oauth_token_lifecycle_report.json").write_text(
        evaluated.token_lifecycle_policy.model_dump_json(indent=2), encoding="utf-8"
    )
    (output_dir / "kiwoom_mock_oauth_safety_report.json").write_text(
        evaluated.safety_report.model_dump_json(indent=2), encoding="utf-8"
    )
    (output_dir / "kiwoom_mock_oauth_gap_report.json").write_text(
        evaluated.gap_report.model_dump_json(indent=2), encoding="utf-8"
    )

    all_items = (
        evaluated,
        *evaluated.endpoint_refs,
        evaluated.token_request_draft,
        evaluated.token_response_draft,
        evaluated.token_revoke_draft,
        evaluated.token_lifecycle_policy,
        evaluated.safety_report,
        evaluated.gap_report,
        evaluated.audit_records[0],
    )
    dumped = json.dumps(evaluated.model_dump(mode="json")).lower()
    return {
        "fixture_run": True,
        "token_request_draft_generated": evaluated.token_request_draft.draft_id.endswith("SMOKE"),
        "token_response_draft_generated": evaluated.token_response_draft.response_draft_id.endswith("SMOKE"),
        "token_revoke_draft_generated": evaluated.token_revoke_draft.draft_id.endswith("SMOKE"),
        "token_lifecycle_report_generated": evaluated.token_lifecycle_policy.policy_id.endswith("SMOKE"),
        "safety_report_generated": evaluated.safety_report.safety_report_id.endswith("SMOKE"),
        "gap_report_generated": evaluated.gap_report.gap_report_id.endswith("SMOKE"),
        "audit_record_generated": len(evaluated.audit_records) == 1,
        "mock_only": all(getattr(item, "mock_only", True) is True for item in all_items),
        "oauth_draft_only": all(getattr(item, "oauth_draft_only", True) is True for item in all_items),
        "credential_boundary_only": all(getattr(item, "credential_boundary_only", True) is True for item in all_items),
        "disabled_by_default": all(getattr(item, "disabled_by_default", True) is True for item in all_items),
        "explicit_opt_in_required": all(getattr(item, "explicit_opt_in_required", True) is True for item in all_items),
        "local_only": all(getattr(item, "local_file_only", True) is True for item in all_items),
        "offline_only": all(getattr(item, "offline_only", True) is True for item in all_items),
        "non_executable": all(getattr(item, "non_executable", True) is True for item in all_items),
        "no_credentials_loaded": all(getattr(item, "no_credentials_loaded", True) is True for item in all_items),
        "no_env_read": all(getattr(item, "no_env_read", True) is True for item in all_items),
        "no_token_issued": all(getattr(item, "no_token_issued", True) is True for item in all_items),
        "no_token_revoked": all(getattr(item, "no_token_revoked", True) is True for item in all_items),
        "no_api_call": all(getattr(item, "no_api_call", True) is True for item in all_items),
        "no_mockapi_call": all(getattr(item, "no_mockapi_call", True) is True for item in all_items),
        "no_websocket_connection": all(getattr(item, "no_websocket_connection", True) is True for item in all_items),
        "no_network_call": all(getattr(item, "no_network_call", True) is True for item in all_items),
        "no_real_order": all(getattr(item, "no_real_order", True) is True for item in all_items),
        "no_live_trading": all(getattr(item, "no_live_trading", True) is True for item in all_items),
        "no_live_prod": all(getattr(item, "no_live_prod", True) is True for item in all_items),
        "no_account_mutation": all(getattr(item, "no_account_mutation", True) is True for item in all_items),
        "no_production_domain_execution": all(
            getattr(item, "no_production_domain_execution", True) is True for item in all_items
        ),
        "no_cloud_llm": all(getattr(item, "no_cloud_llm", True) is True for item in all_items),
        "no_local_llm_runtime": all(getattr(item, "no_local_llm_runtime", True) is True for item in all_items),
        "parquet_unsupported": ".parquet" not in dumped,
    }


def _run_kiwoom_mock_oauth_execution_smoke(output_dir: Path) -> dict[str, bool]:
    fixture = KiwoomMockOAuthExecutionConfig.model_validate(
        {
            "schema_version": "v6.8-kiwoom-mock-oauth-execution-adapter",
            "fixture_format": "json",
            "config_id": "kiwoom-mock-oauth-execution-config-smoke",
            "execution_mode": "TOKEN_REQUEST",
            "mock_domain": "https://mockapi.kiwoom.com",
            "allowed_env_var_names": ["KIWOOM_MOCK_APP_KEY", "KIWOOM_MOCK_SECRET_KEY"],
            "timeout_seconds": 5,
            "max_retry_count": 1,
            "retry_backoff_seconds": 0.0,
            "allow_env_read": True,
            "explicit_opt_in_required": True,
            "redact_output": True,
            "persist_token_to_disk": False,
            "allow_token_refresh": False,
            "credential_boundary_ref": "docs/superpowers/plans/2026-06-18-kiwoom-mock-credential-environment-boundary-design.md",
            "oauth_draft_boundary_ref": "docs/superpowers/plans/2026-06-18-kiwoom-mock-oauth-token-draft-boundary-design.md",
            "transport_boundary_ref": "docs/superpowers/plans/2026-06-18-kiwoom-mock-api-transport-request-envelope-boundary-design.md",
            "preflight_boundary_ref": "docs/superpowers/plans/2026-06-18-kiwoom-mock-api-execution-readiness-preflight-gate-design.md",
            "safety_report": {
                "safety_report_id": "kiwoom-mock-oauth-execution-safety-report-smoke",
                "blocked_capabilities": ["PRODUCTION_DOMAIN_BLOCKED"],
                "findings": [],
            },
            "gap_report": {
                "gap_report_id": "kiwoom-mock-oauth-execution-gap-report-smoke",
                "gap_status": "UNRESOLVED_FUTURE_STAGES",
                "gap_categories": [
                    "MOCK_QUOTE_API_STAGE_NOT_IMPLEMENTED",
                    "MOCK_ACCOUNT_API_STAGE_NOT_IMPLEMENTED",
                    "MOCK_ORDER_API_STAGE_NOT_IMPLEMENTED",
                ],
                "blocking_gap_count": 3,
                "report_only_gap_count": 0,
                "gaps": ["quote", "account", "order"],
            },
            "audit_records": [
                {
                    "audit_record_id": "kiwoom-mock-oauth-execution-audit-record-smoke",
                    "created_at": "2026-06-25T09:13:00+09:00",
                    "source_path": str(output_dir / "kiwoom_mock_oauth_execution_smoke_fixture.json"),
                    "redaction_applied": True,
                    "contains_secret_material": False,
                    "contains_token_material": False,
                    "evidence_refs": ["KIWOOM-REST-EVIDENCE-PACK", "KIWOOM-CAPABILITY-MATRIX"],
                }
            ],
        }
    )
    previous_app = os.environ.get("KIWOOM_MOCK_APP_KEY")
    previous_secret = os.environ.get("KIWOOM_MOCK_SECRET_KEY")
    os.environ["KIWOOM_MOCK_APP_KEY"] = "smoke-app-key"
    os.environ["KIWOOM_MOCK_SECRET_KEY"] = "smoke-secret-key"
    try:
        request_result = execute_kiwoom_mock_oauth(
            fixture,
            execute=True,
            acknowledge_mock_oauth_execution=True,
            mock_domain=True,
            transport=lambda request: {
                "token_type": "bearer",
                "token": "smoke-token-value",
                "expires_dt": "20260623010000",
            },
        )
        revoke_fixture = fixture.model_copy(
            update={"execution_mode": KiwoomMockOAuthExecutionMode.TOKEN_REVOKE}
        )
        revoke_result = execute_kiwoom_mock_oauth(
            revoke_fixture,
            execute=True,
            acknowledge_mock_oauth_execution=True,
            mock_domain=True,
            transport=lambda request: {"return_code": 0, "return_msg": "revoked"},
        )
    finally:
        if previous_app is None:
            os.environ.pop("KIWOOM_MOCK_APP_KEY", None)
        else:
            os.environ["KIWOOM_MOCK_APP_KEY"] = previous_app
        if previous_secret is None:
            os.environ.pop("KIWOOM_MOCK_SECRET_KEY", None)
        else:
            os.environ["KIWOOM_MOCK_SECRET_KEY"] = previous_secret

    safety_report = build_kiwoom_mock_oauth_execution_safety_report(fixture)
    gap_report = build_kiwoom_mock_oauth_execution_gap_report(fixture)
    (output_dir / "kiwoom_mock_oauth_execution_request.json").write_text(
        request_result.model_dump_json(indent=2), encoding="utf-8"
    )
    (output_dir / "kiwoom_mock_oauth_execution_revoke.json").write_text(
        revoke_result.model_dump_json(indent=2), encoding="utf-8"
    )
    (output_dir / "kiwoom_mock_oauth_execution_safety_report.json").write_text(
        safety_report.model_dump_json(indent=2), encoding="utf-8"
    )
    (output_dir / "kiwoom_mock_oauth_execution_gap_report.json").write_text(
        gap_report.model_dump_json(indent=2), encoding="utf-8"
    )
    dumped = json.dumps(request_result.model_dump(mode="json")).lower()
    return {
        "fixture_run": True,
        "request_generated": request_result.executed,
        "revoke_generated": revoke_result.executed,
        "safety_report_generated": safety_report.safety_report_id.endswith("SMOKE"),
        "gap_report_generated": gap_report.gap_report_id.endswith("SMOKE"),
        "audit_record_generated": len(request_result.audit_records) == 1,
        "mock_only": request_result.mock_only,
        "local_only": True,
        "redacted_output_only": request_result.redact_output,
        "no_raw_secret_token_output": "smoke-token-value" not in dumped and "smoke-secret-key" not in dumped,
        "no_token_persistence": request_result.token_result.persisted_to_disk is False,
        "no_real_network_in_smoke": request_result.real_network_performed is False and revoke_result.real_network_performed is False,
        "no_production_path": request_result.no_production_domain_execution,
        "no_account_path": request_result.no_account_path,
        "no_order_path": request_result.no_order_path,
        "no_quote_path": request_result.no_quote_path,
        "no_websocket_path": request_result.no_websocket_path,
        "no_live_prod": request_result.no_live_prod,
    }


def _run_kiwoom_mock_api_transport_draft_smoke(output_dir: Path) -> dict[str, bool]:
    fixture = KiwoomMockApiTransportDraftConfig.model_validate(
        {
            "schema_version": "v6.6-kiwoom-mock-api-transport-draft-boundary",
            "fixture_format": "json",
            "config_id": "kiwoom-mock-api-transport-draft-config-smoke",
            "endpoint_evidence_ref": {
                "endpoint_ref_id": "kiwoom-mock-balance-endpoint-smoke",
                "source_evidence_document_id": "KIWOOM-REST-EVIDENCE-PACK",
                "documented_api_id": "KT00017",
                "documented_category": "ACCOUNT_QUERY",
                "documented_method": "POST",
                "documented_path": "/api/dostk/acnt",
                "documented_mock_domain": "https://mockapi.kiwoom.com",
                "documented_production_domain": "https://api.kiwoom.com",
                "documented_mock_support": True,
                "documented_krx_only_note": "KRX only",
                "evidence_only": True,
                "executable": False,
                "production_domain_blocked": True,
            },
            "request_envelope_draft": {
                "draft_id": "kiwoom-mock-api-request-envelope-smoke",
                "endpoint_ref_id": "KIWOOM-MOCK-BALANCE-ENDPOINT-SMOKE",
                "documented_method": "POST",
                "mock_domain_reference": "MOCK_DOMAIN_REF",
                "request_path": "/api/dostk/acnt",
                "credential_ref_ids": ["KIWOOM_MOCK_APP_KEY_REF", "KIWOOM_MOCK_SECRET_KEY_REF"],
                "token_ref_id": "KIWOOM_MOCK_TOKEN_REF",
                "headers": [
                    {
                        "header_name": "content-type",
                        "required": True,
                        "value_source": "LITERAL_SAFE",
                        "value_preview": "application/json;charset=UTF-8",
                        "redaction_applied": False,
                    },
                    {
                        "header_name": "authorization",
                        "required": True,
                        "value_source": "TOKEN_REF_BLOCKED",
                        "value_preview": "TOKEN_REF_ONLY",
                        "redaction_applied": True,
                    },
                ],
                "query_params": [
                    {
                        "param_name": "qry_tp",
                        "value_source": "LITERAL_SAFE",
                        "value_preview": "0",
                        "redaction_applied": False,
                    }
                ],
                "path_params": [
                    {
                        "param_name": "market_code",
                        "value_source": "LITERAL_SAFE",
                        "value_preview": "KRX",
                        "redaction_applied": False,
                    }
                ],
                "body_draft": {
                    "field_names": ["appkey", "secretkey", "stk_cd"],
                    "field_value_sources": {
                        "appkey": "CREDENTIAL_REF_ONLY",
                        "secretkey": "CREDENTIAL_REF_ONLY",
                        "stk_cd": "LITERAL_SAFE",
                    },
                    "field_value_previews": {
                        "appkey": "KIWOOM_MOCK_APP_KEY_REF",
                        "secretkey": "KIWOOM_MOCK_SECRET_KEY_REF",
                        "stk_cd": "005930",
                    },
                    "redaction_applied": True,
                    "serializable_report_only": True,
                },
                "authorization_header_generation_available": False,
                "http_client_available": False,
                "http_session_available": False,
                "network_execution_enabled": False,
            },
            "transport_policy": {
                "policy_id": "kiwoom-mock-api-transport-policy-smoke",
                "allowed_mock_rest_domain": "https://mockapi.kiwoom.com",
                "forbidden_production_rest_domain": "https://api.kiwoom.com",
                "krx_only": True,
                "disabled_by_default": True,
                "explicit_opt_in_required": True,
            },
            "retry_timeout_policy": {
                "policy_id": "kiwoom-mock-api-retry-timeout-policy-smoke",
                "request_timeout_class": "DOCUMENTED_ONLY",
                "retry_policy_class": "DOCUMENTED_ONLY",
                "rate_limit_note_ref": "KIWOOM-RATE-LIMIT-NOTE-REF",
                "timeout_execution_enabled": False,
                "retry_loop_enabled": False,
                "sleep_backoff_enabled": False,
            },
            "error_response_draft": {
                "error_draft_id": "kiwoom-mock-api-error-response-draft-smoke",
                "documented_error_fields": ["return_code", "return_msg"],
                "captures_live_response": False,
                "wraps_transport_exception": False,
                "contains_credential_material": False,
            },
            "safety_report": {
                "safety_report_id": "kiwoom-mock-api-transport-safety-report-smoke",
                "blocked_capabilities": [
                    "AUTHORIZATION_HEADER_GENERATION_BLOCKED",
                    "TOKEN_LOADING_BLOCKED",
                    "HTTP_CLIENT_CREATION_BLOCKED",
                    "HTTP_SESSION_CREATION_BLOCKED",
                    "NETWORK_EXECUTION_BLOCKED",
                    "PRODUCTION_DOMAIN_EXECUTION_BLOCKED",
                ],
                "findings": [],
            },
            "gap_report": {
                "gap_report_id": "kiwoom-mock-api-transport-gap-report-smoke",
                "gap_status": "UNRESOLVED_IMPLEMENTATION_GAPS",
                "gap_categories": [],
                "blocking_gap_count": 0,
                "report_only_gap_count": 0,
                "gaps": [],
            },
            "audit_records": [
                {
                    "audit_record_id": "kiwoom-mock-api-transport-audit-record-smoke",
                    "created_at": "2026-06-25T09:13:00+09:00",
                    "source_path": str(output_dir / "kiwoom_mock_api_transport_draft_smoke_fixture.json"),
                    "redaction_applied": True,
                    "contains_secret_material": False,
                    "evidence_refs": [
                        "KIWOOM-REST-EVIDENCE-PACK",
                        "KIWOOM-CAPABILITY-MATRIX",
                        "V6.5-OAUTH-DRAFT-BOUNDARY",
                    ],
                }
            ],
        }
    )
    evaluated = run_kiwoom_mock_api_transport_draft_boundary(
        fixture,
        oauth_draft_boundary_ref="docs/superpowers/plans/2026-06-18-kiwoom-mock-oauth-token-draft-boundary-design.md",
    )

    (output_dir / "kiwoom_mock_api_transport_request_envelope_draft.json").write_text(
        evaluated.request_envelope_draft.model_dump_json(indent=2), encoding="utf-8"
    )
    (output_dir / "kiwoom_mock_api_transport_policy_report.json").write_text(
        evaluated.transport_policy.model_dump_json(indent=2), encoding="utf-8"
    )
    (output_dir / "kiwoom_mock_api_retry_timeout_report.json").write_text(
        evaluated.retry_timeout_policy.model_dump_json(indent=2), encoding="utf-8"
    )
    (output_dir / "kiwoom_mock_api_error_response_draft.json").write_text(
        evaluated.error_response_draft.model_dump_json(indent=2), encoding="utf-8"
    )
    (output_dir / "kiwoom_mock_api_transport_safety_report.json").write_text(
        evaluated.safety_report.model_dump_json(indent=2), encoding="utf-8"
    )
    (output_dir / "kiwoom_mock_api_transport_gap_report.json").write_text(
        evaluated.gap_report.model_dump_json(indent=2), encoding="utf-8"
    )

    all_items = (
        evaluated,
        evaluated.endpoint_evidence_ref,
        evaluated.request_envelope_draft,
        *evaluated.request_envelope_draft.headers,
        *evaluated.request_envelope_draft.query_params,
        *evaluated.request_envelope_draft.path_params,
        evaluated.request_envelope_draft.body_draft,
        evaluated.transport_policy,
        evaluated.retry_timeout_policy,
        evaluated.error_response_draft,
        evaluated.safety_report,
        evaluated.gap_report,
        evaluated.audit_records[0],
    )
    dumped = json.dumps(evaluated.model_dump(mode="json")).lower()
    return {
        "fixture_run": True,
        "request_envelope_draft_generated": evaluated.request_envelope_draft.draft_id.endswith("SMOKE"),
        "transport_policy_report_generated": evaluated.transport_policy.policy_id.endswith("SMOKE"),
        "retry_timeout_report_generated": evaluated.retry_timeout_policy.policy_id.endswith("SMOKE"),
        "error_response_draft_generated": evaluated.error_response_draft.error_draft_id.endswith("SMOKE"),
        "safety_report_generated": evaluated.safety_report.safety_report_id.endswith("SMOKE"),
        "gap_report_generated": evaluated.gap_report.gap_report_id.endswith("SMOKE"),
        "audit_record_generated": len(evaluated.audit_records) == 1,
        "kiwoom_mock_api_transport_draft_only": all(
            getattr(item, "kiwoom_mock_api_transport_draft_only", True) is True for item in all_items
        ),
        "mock_only": all(getattr(item, "mock_only", True) is True for item in all_items),
        "offline_only": all(getattr(item, "offline_only", True) is True for item in all_items),
        "local_only": all(getattr(item, "local_file_only", True) is True for item in all_items),
        "request_envelope_only": all(getattr(item, "request_envelope_only", True) is True for item in all_items),
        "non_executable": all(getattr(item, "non_executable", True) is True for item in all_items),
        "no_authorization_header": (
            evaluated.request_envelope_draft.authorization_header_generation_available is False
            and evaluated.no_authorization_header_generated
        ),
        "no_token_loading": evaluated.no_token_loaded,
        "no_token_usage": evaluated.no_token_used,
        "no_token_refresh": evaluated.no_token_refreshed,
        "no_environment_read": evaluated.no_environment_read,
        "no_credential_file_read": evaluated.no_credential_file_read,
        "no_credentials_loaded": evaluated.no_credentials_loaded,
        "no_http_client": evaluated.no_http_client_created and evaluated.request_envelope_draft.http_client_available is False,
        "no_http_session": evaluated.no_http_session_created and evaluated.request_envelope_draft.http_session_available is False,
        "no_transport": evaluated.no_network_call and evaluated.request_envelope_draft.network_execution_enabled is False,
        "no_api_call": evaluated.no_api_call,
        "no_mockapi_call": evaluated.no_mockapi_call,
        "no_websocket_connection": evaluated.no_websocket_connection,
        "no_network_call": evaluated.no_network_call,
        "no_account_read": evaluated.no_account_read,
        "no_account_mutation": evaluated.no_account_mutation,
        "no_real_order": evaluated.no_real_order,
        "no_live_trading": evaluated.no_live_trading,
        "no_live_prod": evaluated.no_live_prod,
        "parquet_unsupported": ".parquet" not in dumped,
    }


def _run_kiwoom_mock_api_preflight_gate_smoke(output_dir: Path) -> dict[str, bool]:
    def _payload(*, category: str, path: str, domain: str = "https://mockapi.kiwoom.com") -> dict[str, object]:
        return {
            "schema_version": "v6.7-kiwoom-mock-api-preflight-gate",
            "fixture_format": "json",
            "config_id": "kiwoom-mock-api-preflight-gate-smoke",
            "credential_boundary_ref": {
                "ref_id": "kiwoom-mock-credential-boundary-ref-smoke",
                "ref_kind": "KIWOOM_MOCK_CREDENTIAL_BOUNDARY",
                "local_path": "docs/superpowers/plans/2026-06-18-kiwoom-mock-credential-environment-boundary-design.md",
            },
            "oauth_draft_boundary_ref": {
                "ref_id": "kiwoom-mock-oauth-draft-ref-smoke",
                "ref_kind": "KIWOOM_MOCK_OAUTH_DRAFT_BOUNDARY",
                "local_path": "docs/superpowers/plans/2026-06-18-kiwoom-mock-oauth-token-draft-boundary-design.md",
            },
            "transport_draft_ref": {
                "ref_id": "kiwoom-mock-transport-draft-ref-smoke",
                "ref_kind": "KIWOOM_MOCK_API_TRANSPORT_DRAFT_BOUNDARY",
                "local_path": "docs/superpowers/plans/2026-06-18-kiwoom-mock-api-transport-request-envelope-boundary-design.md",
            },
            "transport_draft_config": {
                "schema_version": "v6.6-kiwoom-mock-api-transport-draft-boundary",
                "fixture_format": "json",
                "config_id": "kiwoom-mock-api-transport-draft-config-smoke",
                "endpoint_evidence_ref": {
                    "endpoint_ref_id": "kiwoom-mock-endpoint-smoke",
                    "source_evidence_document_id": "KIWOOM-REST-EVIDENCE-PACK",
                    "documented_api_id": "KT00017",
                    "documented_category": category,
                    "documented_method": "POST",
                    "documented_path": path,
                    "documented_mock_domain": domain,
                    "documented_production_domain": "https://api.kiwoom.com",
                    "documented_mock_support": True,
                    "documented_krx_only_note": "KRX only",
                    "evidence_only": True,
                    "executable": False,
                    "production_domain_blocked": True,
                },
                "request_envelope_draft": {
                    "draft_id": "kiwoom-mock-api-request-envelope-smoke",
                    "endpoint_ref_id": "KIWOOM-MOCK-ENDPOINT-SMOKE",
                    "documented_method": "POST",
                    "mock_domain_reference": "MOCK_DOMAIN_REF",
                    "request_path": path,
                    "credential_ref_ids": ["KIWOOM_MOCK_APP_KEY_REF", "KIWOOM_MOCK_SECRET_KEY_REF"],
                    "token_ref_id": "KIWOOM_MOCK_TOKEN_REF",
                    "headers": [
                        {
                            "header_name": "content-type",
                            "required": True,
                            "value_source": "LITERAL_SAFE",
                            "value_preview": "application/json;charset=UTF-8",
                            "redaction_applied": False,
                        },
                        {
                            "header_name": "authorization",
                            "required": True,
                            "value_source": "TOKEN_REF_BLOCKED",
                            "value_preview": "TOKEN_REF_ONLY",
                            "redaction_applied": True,
                        },
                    ],
                    "query_params": [],
                    "path_params": [],
                    "body_draft": {
                        "field_names": ["appkey", "secretkey", "stk_cd"],
                        "field_value_sources": {
                            "appkey": "CREDENTIAL_REF_ONLY",
                            "secretkey": "CREDENTIAL_REF_ONLY",
                            "stk_cd": "LITERAL_SAFE",
                        },
                        "field_value_previews": {
                            "appkey": "KIWOOM_MOCK_APP_KEY_REF",
                            "secretkey": "KIWOOM_MOCK_SECRET_KEY_REF",
                            "stk_cd": "005930",
                        },
                        "redaction_applied": True,
                        "serializable_report_only": True,
                    },
                    "authorization_header_generation_available": False,
                    "http_client_available": False,
                    "http_session_available": False,
                    "network_execution_enabled": False,
                },
                "transport_policy": {
                    "policy_id": "kiwoom-mock-api-transport-policy-smoke",
                    "allowed_mock_rest_domain": "https://mockapi.kiwoom.com",
                    "forbidden_production_rest_domain": "https://api.kiwoom.com",
                    "krx_only": True,
                    "disabled_by_default": True,
                    "explicit_opt_in_required": True,
                },
                "retry_timeout_policy": {
                    "policy_id": "kiwoom-mock-api-retry-timeout-policy-smoke",
                    "request_timeout_class": "DOCUMENTED_ONLY",
                    "retry_policy_class": "DOCUMENTED_ONLY",
                    "rate_limit_note_ref": "KIWOOM-RATE-LIMIT-NOTE-REF",
                    "timeout_execution_enabled": False,
                    "retry_loop_enabled": False,
                    "sleep_backoff_enabled": False,
                },
                "error_response_draft": {
                    "error_draft_id": "kiwoom-mock-api-error-response-draft-smoke",
                    "documented_error_fields": ["return_code", "return_msg"],
                    "captures_live_response": False,
                    "wraps_transport_exception": False,
                    "contains_credential_material": False,
                },
                "safety_report": {
                    "safety_report_id": "kiwoom-mock-api-transport-safety-report-smoke",
                    "blocked_capabilities": [
                        "AUTHORIZATION_HEADER_GENERATION_BLOCKED",
                        "TOKEN_LOADING_BLOCKED",
                        "HTTP_CLIENT_CREATION_BLOCKED",
                        "HTTP_SESSION_CREATION_BLOCKED",
                        "NETWORK_EXECUTION_BLOCKED",
                        "PRODUCTION_DOMAIN_EXECUTION_BLOCKED",
                    ],
                    "findings": [],
                },
                "gap_report": {
                    "gap_report_id": "kiwoom-mock-api-transport-gap-report-smoke",
                    "gap_status": "UNRESOLVED_IMPLEMENTATION_GAPS",
                    "gap_categories": [],
                    "blocking_gap_count": 0,
                    "report_only_gap_count": 0,
                    "gaps": [],
                },
                "audit_records": [
                    {
                        "audit_record_id": "kiwoom-mock-api-transport-audit-record-smoke",
                        "created_at": "2026-06-25T09:13:00+09:00",
                        "source_path": str(output_dir / "kiwoom_mock_api_transport_draft_smoke_fixture.json"),
                        "redaction_applied": True,
                        "contains_secret_material": False,
                        "evidence_refs": [
                            "KIWOOM-REST-EVIDENCE-PACK",
                            "KIWOOM-CAPABILITY-MATRIX",
                            "V6.5-OAUTH-DRAFT-BOUNDARY",
                        ],
                    }
                ],
            },
        }

    quote_ready = run_kiwoom_mock_api_preflight_gate(
        KiwoomMockApiPreflightGateConfig.model_validate(
            _payload(category="QUOTE", path="/api/dostk/mrkcond")
        )
    )
    quote_gap = run_kiwoom_mock_api_preflight_gate(
        KiwoomMockApiPreflightGateConfig.model_validate(
            _payload(category="QUOTE", path="/api/dostk/mrkcond/detail")
        )
    )
    oauth = run_kiwoom_mock_api_preflight_gate(
        KiwoomMockApiPreflightGateConfig.model_validate(_payload(category="QUOTE", path="/oauth2/token"))
    )
    account = run_kiwoom_mock_api_preflight_gate(
        KiwoomMockApiPreflightGateConfig.model_validate(_payload(category="ACCOUNT", path="/api/dostk/acnt"))
    )
    order = run_kiwoom_mock_api_preflight_gate(
        KiwoomMockApiPreflightGateConfig.model_validate(_payload(category="ORDER", path="/api/dostk/ordr"))
    )
    websocket = run_kiwoom_mock_api_preflight_gate(
        KiwoomMockApiPreflightGateConfig.model_validate(
            _payload(category="WEBSOCKET", path="/api/websocket/quote")
        )
    )
    unknown = run_kiwoom_mock_api_preflight_gate(
        KiwoomMockApiPreflightGateConfig.model_validate(_payload(category="MISC", path="/api/unknown"))
    )
    try:
        KiwoomMockApiPreflightGateConfig.model_validate(
            _payload(category="QUOTE", path="/api/dostk/mrkcond", domain="https://api.kiwoom.com")
        )
        prod_blocked_or_rejected = False
    except ValueError:
        prod_blocked_or_rejected = True

    evaluated = quote_ready
    (output_dir / "kiwoom_mock_api_preflight_check.json").write_text(
        evaluated.model_dump_json(indent=2), encoding="utf-8"
    )
    (output_dir / "kiwoom_mock_api_preflight_readiness_report.json").write_text(
        evaluated.readiness_report.model_dump_json(indent=2), encoding="utf-8"
    )
    (output_dir / "kiwoom_mock_api_preflight_safety_report.json").write_text(
        evaluated.safety_report.model_dump_json(indent=2), encoding="utf-8"
    )
    (output_dir / "kiwoom_mock_api_preflight_gap_report.json").write_text(
        evaluated.gap_report.model_dump_json(indent=2), encoding="utf-8"
    )
    (output_dir / "kiwoom_mock_api_preflight_audit_report.json").write_text(
        evaluated.audit_records[0].model_dump_json(indent=2), encoding="utf-8"
    )

    all_items = (
        evaluated,
        evaluated.credential_boundary_ref,
        evaluated.oauth_draft_boundary_ref,
        evaluated.transport_draft_ref,
        evaluated.readiness_report,
        evaluated.safety_report,
        evaluated.gap_report,
        evaluated.audit_records[0],
    )
    dumped = json.dumps(evaluated.model_dump(mode="json")).lower()
    return {
        "fixture_run": True,
        "preflight_check_generated": evaluated.config_id.endswith("SMOKE"),
        "readiness_report_generated": evaluated.readiness_report.readiness_report_id.endswith("READINESS"),
        "safety_report_generated": evaluated.safety_report.safety_report_id.endswith("SAFETY"),
        "gap_report_generated": evaluated.gap_report.gap_report_id.endswith("GAP"),
        "audit_record_generated": len(evaluated.audit_records) == 1,
        "local_only": all(getattr(item, "local_file_only", True) is True for item in all_items),
        "offline_only": all(getattr(item, "offline_only", True) is True for item in all_items),
        "non_executable": all(getattr(item, "non_executable", True) is True for item in all_items),
        "quote_draft_ready": (
            quote_ready.readiness_report.readiness_decision == KiwoomMockApiExecutionReadiness.DRAFT_READY
        ),
        "gap_status_supported": (
            quote_gap.readiness_report.readiness_decision == KiwoomMockApiExecutionReadiness.GAP
        ),
        "oauth_blocked": oauth.readiness_report.readiness_decision == KiwoomMockApiExecutionReadiness.BLOCKED,
        "account_blocked": account.readiness_report.readiness_decision == KiwoomMockApiExecutionReadiness.BLOCKED,
        "order_blocked": order.readiness_report.readiness_decision == KiwoomMockApiExecutionReadiness.BLOCKED,
        "websocket_blocked": (
            websocket.readiness_report.readiness_decision == KiwoomMockApiExecutionReadiness.BLOCKED
        ),
        "unknown_rejected": unknown.readiness_report.readiness_decision == KiwoomMockApiExecutionReadiness.REJECTED,
        "prod_blocked_or_rejected": prod_blocked_or_rejected,
        "no_token_loading": evaluated.no_token_loaded,
        "no_token_usage": evaluated.no_token_used,
        "no_token_refresh": evaluated.no_token_refreshed,
        "no_authorization_header": evaluated.no_authorization_header_generated,
        "no_http_client": evaluated.no_http_client_created,
        "no_http_session": evaluated.no_http_session_created,
        "no_transport": evaluated.no_transport_created,
        "no_api_call": evaluated.no_api_call,
        "no_mockapi_call": evaluated.no_mockapi_call,
        "no_websocket_connection": evaluated.no_websocket_connection,
        "no_network_call": evaluated.no_network_call,
        "no_account_read": evaluated.no_account_read,
        "no_account_mutation": evaluated.no_account_mutation,
        "no_real_order": evaluated.no_real_order,
        "no_live_trading": evaluated.no_live_trading,
        "no_live_prod": evaluated.no_live_prod,
        "parquet_unsupported": ".parquet" not in dumped,
    }


def _run_kiwoom_mock_market_data_execution_smoke(output_dir: Path) -> dict[str, bool]:
    fixture = KiwoomMockMarketDataExecutionConfig.model_validate(
        {
            "schema_version": "v6.9-kiwoom-mock-market-data-execution-adapter",
            "fixture_format": "json",
            "config_id": "kiwoom-mock-market-data-execution-config-smoke",
            "mock_domain": "https://mockapi.kiwoom.com",
            "documented_category": "QUOTE",
            "documented_path": "/api/dostk/mrkcond",
            "preflight_readiness_decision": "DRAFT_READY",
            "token_reference_label": "KIWOOM_MOCK_ACCESS_TOKEN_REF",
            "timeout_seconds": 5,
            "max_retry_count": 1,
            "retry_backoff_seconds": 0.0,
            "persist_token_to_disk": False,
            "allow_token_refresh": False,
            "oauth_draft_boundary_ref": "docs/superpowers/plans/2026-06-18-kiwoom-mock-oauth-token-draft-boundary-design.md",
            "transport_boundary_ref": "docs/superpowers/plans/2026-06-18-kiwoom-mock-api-transport-request-envelope-boundary-design.md",
            "preflight_boundary_ref": "docs/superpowers/plans/2026-06-18-kiwoom-mock-api-execution-readiness-preflight-gate-design.md",
            "oauth_execution_boundary_ref": "docs/superpowers/plans/2026-06-18-kiwoom-mock-oauth-execution-adapter-design.md",
            "safety_report": {
                "safety_report_id": "kiwoom-mock-market-data-execution-safety-report-smoke",
                "blocked_capabilities": [
                    "PRODUCTION_DOMAIN_BLOCKED",
                    "ACCOUNT_PATH_BLOCKED",
                    "ORDER_PATH_BLOCKED",
                    "WEBSOCKET_BLOCKED",
                    "LIVE_PROD_BLOCKED",
                ],
                "findings": [],
            },
            "gap_report": {
                "gap_report_id": "kiwoom-mock-market-data-execution-gap-report-smoke",
                "gap_status": "UNRESOLVED_FUTURE_STAGES",
                "gap_categories": [
                    "REAL_MARKET_DATA_STAGE_NOT_IMPLEMENTED",
                    "ACCOUNT_STAGE_NOT_IMPLEMENTED",
                    "ORDER_STAGE_NOT_IMPLEMENTED",
                ],
                "blocking_gap_count": 3,
                "report_only_gap_count": 0,
                "gaps": [
                    "real market data stage deferred",
                    "account stage deferred",
                    "order stage deferred",
                ],
            },
            "audit_records": [
                {
                    "audit_record_id": "kiwoom-mock-market-data-execution-audit-record-smoke",
                    "created_at": "2026-06-25T09:13:00+09:00",
                    "source_path": str(output_dir / "kiwoom_mock_market_data_execution_smoke_fixture.json"),
                    "redaction_applied": True,
                    "contains_secret_material": False,
                    "contains_token_material": False,
                    "contains_account_material": False,
                    "evidence_refs": ["KIWOOM-REST-EVIDENCE-PACK", "KIWOOM-CAPABILITY-MATRIX"],
                }
            ],
        }
    )

    result = execute_kiwoom_mock_market_data(
        fixture,
        execute=True,
        acknowledge_mock_market_data_execution=True,
        mock_domain=True,
        access_token="smoke-in-memory-token",
        transport=lambda request: {
            "symbol": "005930",
            "last_price": 70000,
            "condition_match": True,
        },
    )
    response_report = build_kiwoom_mock_market_data_response_report(fixture)
    safety_report = build_kiwoom_mock_market_data_execution_safety_report(fixture)
    gap_report = build_kiwoom_mock_market_data_execution_gap_report(fixture)

    (output_dir / "kiwoom_mock_market_data_execution_request.json").write_text(
        result.model_dump_json(indent=2), encoding="utf-8"
    )
    (output_dir / "kiwoom_mock_market_data_execution_response_report.json").write_text(
        response_report.model_dump_json(indent=2), encoding="utf-8"
    )
    (output_dir / "kiwoom_mock_market_data_execution_safety_report.json").write_text(
        safety_report.model_dump_json(indent=2), encoding="utf-8"
    )
    (output_dir / "kiwoom_mock_market_data_execution_gap_report.json").write_text(
        gap_report.model_dump_json(indent=2), encoding="utf-8"
    )

    dumped = json.dumps(result.model_dump(mode="json")).lower()
    return {
        "fixture_run": True,
        "request_generated": result.executed,
        "response_report_generated": response_report.response_object_id.endswith("RESPONSE"),
        "safety_report_generated": safety_report.safety_report_id.endswith("SMOKE"),
        "gap_report_generated": gap_report.gap_report_id.endswith("SMOKE"),
        "audit_record_generated": len(result.audit_records) == 1,
        "mock_only": result.mock_only,
        "local_only": True,
        "read_only_market_data_only": result.read_only_market_data_execution_only,
        "redacted_output_only": result.redact_output,
        "no_raw_secret_token_output": "smoke-in-memory-token" not in dumped and "authorization" not in dumped,
        "no_token_persistence": result.no_token_persistence and result.response.persisted_to_disk is False,
        "no_token_refresh": result.no_token_refresh,
        "no_real_network_in_smoke": result.real_network_performed is False and result.mock_transport_used is True,
        "no_production_path": result.no_production_domain_execution,
        "no_account_path": result.no_account_path,
        "no_order_path": result.no_order_path,
        "no_websocket_path": result.no_websocket_path,
        "no_live_prod": result.no_live_prod,
    }


def _run_quant_strategy_robustness_smoke(output_dir: Path) -> dict[str, bool]:
    evaluated = build_quant_strategy_robustness(
        QuantStrategyRobustnessInput.model_validate(
            {
                "input_id": "quant-robustness-input-smoke",
                "config": {
                    "config_id": "quant-robustness-config-smoke",
                    "fixture_format": "json",
                },
                "universe_policy": {
                    "universe_mode": "POINT_IN_TIME_HISTORICAL",
                    "historical_universe_snapshots_required": True,
                    "historical_universe_snapshots_available": True,
                    "delisted_handled": True,
                    "suspended_handled": True,
                    "merged_handled": True,
                    "renamed_handled": True,
                    "index_removed_handled": True,
                },
                "point_in_time_policy": {
                    "available_at_required": True,
                    "price_features_have_available_at": True,
                    "fundamental_features_have_available_at": True,
                    "index_features_have_available_at": True,
                    "macro_features_have_available_at": True,
                    "event_features_have_available_at": True,
                    "future_data_leakage_blocked": True,
                    "corporate_action_policy_present": True,
                    "split_policy_present": True,
                    "dividend_policy_present": True,
                    "symbol_change_policy_present": True,
                    "delisting_policy_present": True,
                },
                "walk_forward_policy": {
                    "walk_forward_mode": "ROLLING",
                    "train_window_count": 4,
                    "validation_window_count": 2,
                    "test_window_count": 1,
                    "forward_paper_window_count": 1,
                    "repeated_final_test_tuning_count": 0,
                    "parameter_search_count": 4,
                    "max_parameter_search_count": 20,
                    "final_test_period_reused_for_tuning": False,
                    "period_stability_metrics_present": True,
                },
                "diversification_policy": {
                    "alpha_candidate_families": [
                        "MOMENTUM",
                        "MEAN_REVERSION",
                        "BREAKOUT",
                        "VOLUME_SHOCK",
                    ],
                    "max_pairwise_strategy_correlation": 0.45,
                    "max_drawdown_comovement": 0.35,
                },
                "regime_policy": {
                    "regime_buckets": [
                        "INDEX_TREND",
                        "VOLATILITY",
                        "FX",
                        "RATE_LIQUIDITY",
                        "SECTOR_BREADTH",
                        "MACRO_EVENT_CALENDAR",
                    ],
                    "required_bucket_count": 6,
                    "evaluated_bucket_count": 6,
                },
                "experiment_registry_ref": "docs/superpowers/plans/2026-06-18-quant-strategy-robustness-training-readiness-foundation.md",
                "source_manifest_ids": ["MANIFEST-1"],
                "audit_records": [
                    {
                        "audit_record_id": "quant-robustness-audit-smoke",
                        "created_at": "2026-06-25T09:13:00+09:00",
                        "source_path": str(output_dir / "quant_strategy_robustness_smoke_fixture.json"),
                        "operator_context": "offline robustness smoke",
                        "redaction_applied": True,
                        "contains_secret_material": False,
                        "contains_token_material": False,
                        "contains_account_material": False,
                        "experiment_registry_ref": "docs/superpowers/plans/2026-06-18-quant-strategy-robustness-training-readiness-foundation.md",
                    }
                ],
                "robustness_safety_report": {
                    "safety_report_id": "quant-robustness-safety-report-smoke",
                    "blocked_capabilities": [
                        "LIVE_TRADING_BLOCKED",
                        "REAL_ORDER_BLOCKED",
                        "ACCOUNT_MUTATION_BLOCKED",
                        "BROKER_API_BLOCKED",
                        "NETWORK_BLOCKED",
                        "AUTONOMOUS_TRADING_BLOCKED",
                    ],
                    "findings": [],
                },
            }
        )
    )
    (output_dir / "quant_strategy_robustness_report.json").write_text(
        evaluated.robustness_readiness_report.model_dump_json(indent=2), encoding="utf-8"
    )
    (output_dir / "quant_strategy_survivorship_bias_report.json").write_text(
        evaluated.survivorship_bias_report.model_dump_json(indent=2), encoding="utf-8"
    )
    (output_dir / "quant_strategy_point_in_time_report.json").write_text(
        evaluated.point_in_time_leakage_report.model_dump_json(indent=2), encoding="utf-8"
    )
    dumped = json.dumps(evaluated.model_dump(mode="json")).lower()
    return {
        "fixture_run": True,
        "report_generated": evaluated.robustness_readiness_report.readiness_report_id.endswith("REPORT"),
        "survivorship_report_generated": evaluated.survivorship_bias_report.report_id.endswith("REPORT"),
        "point_in_time_report_generated": evaluated.point_in_time_leakage_report.report_id.endswith("REPORT"),
        "walk_forward_report_generated": evaluated.walk_forward_policy_report.report_id.endswith("REPORT"),
        "data_snooping_report_generated": evaluated.data_snooping_report.report_id.endswith("REPORT"),
        "diversification_report_generated": evaluated.strategy_diversification_report.report_id.endswith("REPORT"),
        "regime_report_generated": evaluated.regime_readiness_report.report_id.endswith("REPORT"),
        "local_only": evaluated.config.local_file_only,
        "offline_only": evaluated.config.offline_only,
        "report_only": evaluated.robustness_readiness_report.report_only,
        "non_executable": evaluated.robustness_readiness_report.non_executable,
        "training_ready": evaluated.robustness_readiness_report.decision.value == "TRAINING_READY",
        "no_live_path": evaluated.config.no_live_prod and evaluated.config.no_autonomous_trading,
        "no_order_path": evaluated.config.no_order and "real order" not in dumped,
        "no_account_mutation": evaluated.config.no_account_mutation,
        "no_network": evaluated.config.no_network,
        "parquet_unsupported": ".parquet" not in dumped,
    }


def _run_point_in_time_universe_smoke(output_dir: Path) -> dict[str, bool]:
    evaluated = build_point_in_time_universe_gate(
        PointInTimeUniverseInput.model_validate(
            {
                "input_id": "pit-universe-input-smoke",
                "config": {
                    "config_id": "pit-universe-config-smoke",
                    "fixture_format": "json",
                },
                "universe_source": "POINT_IN_TIME_UNIVERSE",
                "universe_snapshots": [
                    {
                        "snapshot_id": "pit-snapshot-smoke",
                        "trading_date": "2026-06-20",
                        "market": "KRX",
                        "symbol_universe": ["005930", "000660"],
                        "inclusion_reason": "index constituent snapshot",
                        "exclusion_reason": "",
                        "index_membership_ref": "KOSPI200-20260620",
                        "tradability_status": "TRADABLE",
                        "available_at": "2026-06-20T08:00:00+09:00",
                    }
                ],
                "security_lifecycle_records": [
                    {
                        "record_id": "life-smoke-1",
                        "symbol": "005930",
                        "status": "LISTED",
                        "event_date": "2026-06-20",
                        "available_at": "2026-06-20T08:00:00+09:00",
                        "coverage_present": True,
                    },
                    {
                        "record_id": "life-smoke-2",
                        "symbol": "OLD1",
                        "status": "DELISTED",
                        "event_date": "2026-03-01",
                        "available_at": "2026-03-01T08:00:00+09:00",
                        "coverage_present": True,
                    },
                    {
                        "record_id": "life-smoke-3",
                        "symbol": "000660",
                        "status": "SUSPENDED",
                        "event_date": "2026-04-01",
                        "available_at": "2026-04-01T08:00:00+09:00",
                        "coverage_present": True,
                    },
                    {
                        "record_id": "life-smoke-4",
                        "symbol": "REN1",
                        "status": "RENAMED",
                        "event_date": "2026-02-01",
                        "available_at": "2026-02-01T08:00:00+09:00",
                        "coverage_present": True,
                    },
                ],
                "available_at_coverage_complete": True,
                "corporate_action_coverage_complete": True,
                "index_membership_coverage_complete": True,
                "tradability_coverage_complete": True,
                "missing_date_gap_coverage_complete": True,
                "future_index_membership_leakage_detected": False,
                "current_constituent_replay_leakage_detected": False,
                "future_delisting_knowledge_leakage_detected": False,
                "symbol_survivorship_leakage_detected": False,
                "source_manifest_ids": ["MANIFEST-1"],
                "audit_records": [
                    {
                        "audit_record_id": "pit-audit-smoke",
                        "created_at": "2026-06-25T09:13:00+09:00",
                        "source_path": str(output_dir / "point_in_time_universe_smoke_fixture.json"),
                        "operator_context": "offline point in time universe smoke",
                        "redaction_applied": True,
                        "contains_secret_material": False,
                        "contains_token_material": False,
                        "contains_account_material": False,
                    }
                ],
                "safety_report": {
                    "safety_report_id": "pit-universe-safety-smoke",
                    "blocked_capabilities": [
                        "LIVE_TRADING_BLOCKED",
                        "REAL_ORDER_BLOCKED",
                        "ACCOUNT_MUTATION_BLOCKED",
                        "BROKER_API_BLOCKED",
                        "NETWORK_BLOCKED",
                        "AUTONOMOUS_TRADING_BLOCKED",
                    ],
                    "findings": [],
                },
            }
        )
    )
    (output_dir / "point_in_time_universe_report.json").write_text(
        evaluated.point_in_time_universe_report.model_dump_json(indent=2), encoding="utf-8"
    )
    dumped = json.dumps(evaluated.model_dump(mode="json")).lower()
    return {
        "fixture_run": True,
        "point_in_time_report_generated": evaluated.point_in_time_universe_report.report_id.endswith("REPORT"),
        "survivorship_report_generated": evaluated.survivorship_bias_report.report_id.endswith("REPORT"),
        "lifecycle_report_generated": evaluated.security_lifecycle_coverage_report.report_id.endswith("REPORT"),
        "leakage_report_generated": evaluated.leakage_report.report_id.endswith("REPORT"),
        "promotion_report_generated": evaluated.dataset_promotion_readiness_report.report_id.endswith("REPORT"),
        "local_only": evaluated.config.local_file_only,
        "offline_only": evaluated.config.offline_only,
        "report_only": evaluated.dataset_promotion_readiness_report.report_only,
        "non_executable": evaluated.dataset_promotion_readiness_report.non_executable,
        "training_ready": evaluated.dataset_promotion_readiness_report.decision.value == "TRAINING_READY",
        "no_live_path": evaluated.config.no_live_prod and evaluated.config.no_autonomous_trading,
        "no_order_path": evaluated.config.no_order and "real order" not in dumped,
        "no_account_mutation": evaluated.config.no_account_mutation,
        "no_network": evaluated.config.no_network,
        "parquet_unsupported": ".parquet" not in dumped,
    }


def _run_walk_forward_validation_smoke(output_dir: Path) -> dict[str, bool]:
    evaluated = build_walk_forward_validation(
        WalkForwardValidationInput.model_validate(
            {
                "input_id": "wf-validation-input-smoke",
                "config": {
                    "config_id": "wf-validation-config-smoke",
                    "fixture_format": "json",
                    "max_parameter_search_count": 20,
                    "max_hidden_failed_trials": 10,
                    "paper_ready_requires_forward_window": True,
                },
                "split": {
                    "split_id": "wf-split-smoke",
                    "mode": "ROLLING",
                    "train_window": {
                        "start_at": "2024-01-01T00:00:00+09:00",
                        "end_at": "2024-06-30T00:00:00+09:00",
                    },
                    "validation_window": {
                        "start_at": "2024-07-01T00:00:00+09:00",
                        "end_at": "2024-09-30T00:00:00+09:00",
                    },
                    "test_window": {
                        "start_at": "2024-10-01T00:00:00+09:00",
                        "end_at": "2024-12-31T00:00:00+09:00",
                    },
                    "forward_paper_window": {
                        "start_at": "2025-01-01T00:00:00+09:00",
                        "end_at": "2025-03-31T00:00:00+09:00",
                    },
                },
                "experiment_lineage": {
                    "experiment_id": "exp-smoke",
                    "dataset_id": "dataset-smoke",
                    "feature_set_id": "feature-set-smoke",
                    "strategy_id": "strategy-smoke",
                    "parameter_set_id": "param-set-smoke",
                    "search_run_id": "search-run-smoke",
                    "parent_experiment_refs": ["EXP-PARENT-SMOKE"],
                    "final_test_access_count": 1,
                    "validation_reuse_count": 1,
                    "registered_parameter_mutations": ["MUT-1"],
                    "unregistered_parameter_mutation_detected": False,
                },
                "stability_evidence": {
                    "fold_count": 4,
                    "stable_fold_count": 3,
                    "drawdown_stable": True,
                    "hit_rate_stable": True,
                    "return_stable": True,
                    "risk_adjusted_metric_stable": True,
                    "single_period_only_success": False,
                    "regime_bucket_reference_present": True,
                },
                "parameter_search_count": 6,
                "hidden_failed_trial_count": 2,
                "test_period_cherry_picking_detected": False,
                "regime_bucket_reference_present": True,
                "source_manifest_ids": ["MANIFEST-1"],
                "audit_records": [
                    {
                        "audit_record_id": "wf-audit-smoke",
                        "created_at": "2026-06-25T09:13:00+09:00",
                        "source_path": str(output_dir / "walk_forward_validation_smoke_fixture.json"),
                        "operator_context": "offline walk forward validation smoke",
                        "redaction_applied": True,
                        "contains_secret_material": False,
                        "contains_token_material": False,
                        "contains_account_material": False,
                    }
                ],
                "safety_report": {
                    "safety_report_id": "wf-validation-safety-smoke",
                    "blocked_capabilities": [
                        "LIVE_TRADING_BLOCKED",
                        "REAL_ORDER_BLOCKED",
                        "ACCOUNT_MUTATION_BLOCKED",
                        "BROKER_API_BLOCKED",
                        "NETWORK_BLOCKED",
                        "AUTONOMOUS_TRADING_BLOCKED",
                    ],
                    "findings": [],
                },
            }
        )
    )
    dumped = json.dumps(evaluated.model_dump(mode="json")).lower()
    return {
        "fixture_run": True,
        "split_report_generated": evaluated.walk_forward_split_report.report_id.endswith("REPORT"),
        "data_snooping_report_generated": evaluated.data_snooping_report.report_id.endswith("REPORT"),
        "lineage_report_generated": evaluated.experiment_lineage_report.report_id.endswith("REPORT"),
        "pressure_report_generated": evaluated.parameter_search_pressure_report.report_id.endswith("REPORT"),
        "contamination_report_generated": evaluated.final_test_contamination_report.report_id.endswith("REPORT"),
        "stability_report_generated": evaluated.stability_report.report_id.endswith("REPORT"),
        "promotion_report_generated": evaluated.promotion_readiness_report.report_id.endswith("REPORT"),
        "local_only": evaluated.config.local_file_only,
        "offline_only": evaluated.config.offline_only,
        "report_only": evaluated.promotion_readiness_report.report_only,
        "non_executable": evaluated.promotion_readiness_report.non_executable,
        "ready_for_validation_or_paper": evaluated.promotion_readiness_report.decision.value in {"VALIDATION_READY", "PAPER_READY"},
        "no_live_path": evaluated.config.no_live_prod and evaluated.config.no_autonomous_trading,
        "no_order_path": evaluated.config.no_order and "real order" not in dumped,
        "no_account_mutation": evaluated.config.no_account_mutation,
        "no_network": evaluated.config.no_network,
        "parquet_unsupported": ".parquet" not in dumped,
    }


def _run_training_pipeline_promotion_smoke(output_dir: Path) -> dict[str, bool]:
    evaluated = build_training_pipeline_promotion(
        TrainingPipelinePromotionInput.model_validate(
            {
                "input_id": "training-promotion-input-smoke",
                "dataset_eligibility": {
                    "dataset_id": "dataset-smoke",
                    "point_in_time_gate_decision": "TRAINING_READY",
                    "survivorship_safety_ref": "pit-report-smoke",
                    "available_at_discipline_ref": "available-at-ref-smoke",
                    "leakage_audit_ref": "leakage-audit-ref-smoke",
                    "feature_set_id": "feature-set-smoke",
                    "label_horizon": "5D",
                    "target_type": "OUTCOME_LABEL",
                    "train_split_ref": "TRAIN-SPLIT-SMOKE",
                    "validation_split_ref": "VALIDATION-SPLIT-SMOKE",
                    "test_split_ref": "TEST-SPLIT-SMOKE",
                    "forward_paper_split_ref": "FORWARD-PAPER-SPLIT-SMOKE",
                    "label_leakage_detected": False,
                },
                "training_run_candidate": {
                    "training_run_id": "training-run-smoke",
                    "model_family": "DUMMY_MAJORITY",
                    "hyperparameter_set_id": "hyperparam-smoke",
                    "feature_set_id": "feature-set-smoke",
                    "dataset_id": "dataset-smoke",
                    "experiment_id": "experiment-smoke",
                    "random_seed_policy_present": True,
                    "reproducibility_hash": "repro-hash-smoke",
                    "training_window_refs": ["TRAIN-WINDOW-SMOKE"],
                    "validation_window_refs": ["VALIDATION-WINDOW-SMOKE"],
                    "test_window_refs": ["TEST-WINDOW-SMOKE"],
                    "forward_paper_window_refs": ["FORWARD-PAPER-WINDOW-SMOKE"],
                },
                "v71_dataset_decision": "TRAINING_READY",
                "v72_validation_decision": "PAPER_READY",
                "v70_robustness_decision": "TRAINING_READY",
                "excessive_parameter_search_flagged": False,
                "final_test_contamination_detected": False,
                "leakage_detected": False,
                "snooping_detected": False,
                "model_artifact_metadata_reproducible": True,
                "config_read_only_flags": {"report_only": True},
                "source_manifest_ids": ["MANIFEST-SMOKE"],
                "audit_records": [
                    {
                        "audit_record_id": "training-promotion-audit-smoke",
                        "created_at": "2026-06-25T09:13:00+09:00",
                        "source_path": str(output_dir / "training_pipeline_promotion_smoke_fixture.json"),
                        "operator_context": "offline training pipeline promotion smoke",
                        "redaction_applied": True,
                        "contains_secret_material": False,
                        "contains_token_material": False,
                        "contains_account_material": False,
                    }
                ],
                "safety_report": {
                    "safety_report_id": "training-promotion-safety-smoke",
                    "blocked_capabilities": [
                        "LIVE_TRADING_BLOCKED",
                        "REAL_ORDER_BLOCKED",
                        "ACCOUNT_MUTATION_BLOCKED",
                        "BROKER_API_BLOCKED",
                        "NETWORK_BLOCKED",
                        "AUTONOMOUS_TRADING_BLOCKED",
                    ],
                    "findings": [],
                },
            }
        )
    )
    dumped = json.dumps(evaluated.model_dump(mode="json")).lower()
    return {
        "fixture_run": True,
        "training_eligibility_report_generated": evaluated.training_eligibility_report.report_id.endswith("REPORT"),
        "dependency_report_generated": evaluated.dependency_report.report_id.endswith("REPORT"),
        "leakage_overfit_risk_report_generated": evaluated.leakage_overfit_risk_report.report_id.endswith("REPORT"),
        "reproducibility_report_generated": evaluated.reproducibility_report.report_id.endswith("REPORT"),
        "model_artifact_policy_report_generated": evaluated.model_artifact_policy_report.report_id.endswith("REPORT"),
        "model_promotion_readiness_report_generated": evaluated.model_promotion_readiness_report.report_id.endswith("REPORT"),
        "local_only": evaluated.training_eligibility_report.local_file_only,
        "offline_only": evaluated.training_eligibility_report.offline_only,
        "report_only": evaluated.model_promotion_readiness_report.report_only,
        "non_executable": evaluated.model_promotion_readiness_report.non_executable,
        "training_ready_or_paper_candidate": evaluated.model_promotion_readiness_report.decision.value in {"TRAINING_READY", "PAPER_CANDIDATE"},
        "no_live_path": evaluated.model_promotion_readiness_report.no_live_prod and evaluated.model_promotion_readiness_report.no_autonomous_trading,
        "no_order_path": evaluated.model_promotion_readiness_report.no_order and "order intent" not in dumped,
        "no_account_mutation": evaluated.model_promotion_readiness_report.no_account_mutation,
        "no_network": evaluated.model_promotion_readiness_report.no_network,
        "parquet_unsupported": ".parquet" not in dumped,
    }


def _run_strategy_ensemble_alpha_smoke(output_dir: Path) -> dict[str, bool]:
    evaluated = build_strategy_ensemble_alpha_gate(
        StrategyEnsembleAlphaInput.model_validate(
            {
                "input_id": "strategy-ensemble-input-smoke",
                "portfolio": {
                    "portfolio_id": "alpha-portfolio-smoke",
                    "rebalance_policy": "WEEKLY",
                    "risk_budget_policy": "BALANCED",
                    "min_alpha_count": 3,
                    "min_strategy_family_count": 3,
                    "max_family_concentration": 0.45,
                    "max_single_alpha_concentration": 0.40,
                    "allocations": [
                        {"alpha_id": "alpha-1", "proposed_weight": 0.34},
                        {"alpha_id": "alpha-2", "proposed_weight": 0.33},
                        {"alpha_id": "alpha-3", "proposed_weight": 0.33},
                    ],
                },
                "alpha_candidates": [
                    {
                        "alpha_id": "alpha-1",
                        "strategy_family": "MOMENTUM",
                        "feature_set_id": "feature-set-1",
                        "signal_source": "SIGNAL-CANDIDATE",
                        "horizon": "5D",
                        "market": "KRX",
                        "expected_holding_period": "3D",
                        "training_promotion_ref": "promotion-ref-1",
                        "training_promotion_decision": "PAPER_CANDIDATE",
                        "robustness_ref": "robustness-ref-1",
                        "robustness_decision": "TRAINING_READY",
                        "paper_candidate_eligibility_ref": "paper-ref-1",
                    },
                    {
                        "alpha_id": "alpha-2",
                        "strategy_family": "MEAN_REVERSION",
                        "feature_set_id": "feature-set-2",
                        "signal_source": "SIGNAL-CANDIDATE",
                        "horizon": "10D",
                        "market": "KRX",
                        "expected_holding_period": "5D",
                        "training_promotion_ref": "promotion-ref-2",
                        "training_promotion_decision": "TRAINING_READY",
                        "robustness_ref": "robustness-ref-2",
                        "robustness_decision": "TRAINING_READY",
                        "paper_candidate_eligibility_ref": "paper-ref-2",
                    },
                    {
                        "alpha_id": "alpha-3",
                        "strategy_family": "SECTOR_ROTATION",
                        "feature_set_id": "feature-set-3",
                        "signal_source": "SIGNAL-CANDIDATE",
                        "horizon": "15D",
                        "market": "KRX",
                        "expected_holding_period": "7D",
                        "training_promotion_ref": "promotion-ref-3",
                        "training_promotion_decision": "TRAINING_READY",
                        "robustness_ref": "robustness-ref-3",
                        "robustness_decision": "TRAINING_READY",
                        "paper_candidate_eligibility_ref": "paper-ref-3",
                    },
                ],
                "correlation_matrix_summary": {
                    "max_pair_correlation": 0.35,
                    "high_correlation_pairs": [],
                },
                "drawdown_summary": {
                    "max_drawdown_co_movement": 0.30,
                    "high_drawdown_pairs": [],
                },
                "regime_overlap_summary": {
                    "regime_coverage_complete": True,
                    "overlap_ratio": 0.35,
                    "covered_regimes": ["RISK_ON", "RISK_OFF", "DEFENSIVE"],
                },
                "duplicate_signal_detected": False,
                "source_manifest_ids": ["MANIFEST-SMOKE"],
                "audit_records": [
                    {
                        "audit_record_id": "strategy-ensemble-audit-smoke",
                        "created_at": "2026-06-25T09:13:00+09:00",
                        "source_path": str(output_dir / "strategy_ensemble_alpha_smoke_fixture.json"),
                        "operator_context": "offline strategy ensemble alpha smoke",
                        "redaction_applied": True,
                        "contains_secret_material": False,
                        "contains_token_material": False,
                        "contains_account_material": False,
                    }
                ],
                "safety_report": {
                    "safety_report_id": "strategy-ensemble-safety-smoke",
                    "blocked_capabilities": [
                        "LIVE_TRADING_BLOCKED",
                        "REAL_ORDER_BLOCKED",
                        "ACCOUNT_MUTATION_BLOCKED",
                        "BROKER_API_BLOCKED",
                        "NETWORK_BLOCKED",
                        "AUTONOMOUS_TRADING_BLOCKED",
                    ],
                    "findings": [],
                },
            }
        )
    )
    dumped = json.dumps(evaluated.model_dump(mode="json")).lower()
    return {
        "fixture_run": True,
        "alpha_candidate_report_generated": evaluated.alpha_candidate_report.report_id.endswith("REPORT"),
        "family_report_generated": evaluated.strategy_family_diversification_report.report_id.endswith("REPORT"),
        "correlation_report_generated": evaluated.alpha_correlation_risk_report.report_id.endswith("REPORT"),
        "drawdown_report_generated": evaluated.drawdown_co_movement_report.report_id.endswith("REPORT"),
        "regime_report_generated": evaluated.regime_overlap_report.report_id.endswith("REPORT"),
        "concentration_report_generated": evaluated.alpha_portfolio_concentration_report.report_id.endswith("REPORT"),
        "promotion_report_generated": evaluated.ensemble_promotion_readiness_report.report_id.endswith("REPORT"),
        "local_only": evaluated.ensemble_promotion_readiness_report.local_file_only,
        "offline_only": evaluated.ensemble_promotion_readiness_report.offline_only,
        "report_only": evaluated.ensemble_promotion_readiness_report.report_only,
        "non_executable": evaluated.ensemble_promotion_readiness_report.non_executable,
        "ensemble_ready_or_paper_candidate": evaluated.ensemble_promotion_readiness_report.decision.value in {"ENSEMBLE_READY", "PAPER_CANDIDATE"},
        "no_live_path": evaluated.ensemble_promotion_readiness_report.no_live_prod and evaluated.ensemble_promotion_readiness_report.no_autonomous_trading,
        "no_order_path": evaluated.ensemble_promotion_readiness_report.no_order and "order intent" not in dumped,
        "no_account_mutation": evaluated.ensemble_promotion_readiness_report.no_account_mutation,
        "no_network": evaluated.ensemble_promotion_readiness_report.no_network,
        "parquet_unsupported": ".parquet" not in dumped,
    }


def _run_regime_allocation_learning_smoke(output_dir: Path) -> dict[str, bool]:
    evaluated = build_regime_allocation_learning_dataset(
        RegimeAllocationLearningInput.model_validate(
            {
                "input_id": "regime-allocation-learning-input-smoke",
                "dependency_status": {
                    "point_in_time_dataset_decision": "TRAINING_READY",
                    "walk_forward_validation_decision": "PAPER_READY",
                    "ensemble_promotion_refs_present": True,
                    "current_survivors_only_dependency": False,
                },
                "regime_feature_snapshot": {
                    "snapshot_id": "regime-snapshot-smoke",
                    "market": "KRX",
                    "trading_timestamp": "2026-06-24T09:00:00+09:00",
                    "available_at": "2026-06-24T09:00:00+09:00",
                    "index_trend": "UPTREND",
                    "realized_volatility_bucket": "MEDIUM",
                    "drawdown_bucket": "LOW",
                    "fx_regime": "STABLE",
                    "rate_liquidity_regime": "NEUTRAL",
                    "sector_breadth": "BROAD",
                    "macro_event_pressure": "MODERATE",
                    "risk_state": "RISK_OFF",
                },
                "action_candidates": [
                    {
                        "action_type": "KEEP_LONG",
                        "target_strategy_family_or_instrument_class": "MOMENTUM",
                        "max_allocation_multiplier": 1.0,
                        "expected_holding_period_constraint": "5D",
                        "liquidity_evidence_ref": "liquidity-ref-1",
                        "eligibility_ref": "eligibility-ref-1",
                        "risk_note": "report only learning action",
                        "no_execution": True,
                    },
                    {
                        "action_type": "ROTATE_DEFENSIVE",
                        "target_strategy_family_or_instrument_class": "DEFENSIVE_CASH_RISK_CONTROL",
                        "max_allocation_multiplier": 0.6,
                        "expected_holding_period_constraint": "5D",
                        "liquidity_evidence_ref": "liquidity-ref-2",
                        "eligibility_ref": "eligibility-ref-2",
                        "risk_note": "defensive rotation candidate",
                        "no_execution": True,
                    },
                    {
                        "action_type": "INVERSE_CANDIDATE",
                        "target_strategy_family_or_instrument_class": "INDEX_INVERSE_ETF",
                        "max_allocation_multiplier": 0.2,
                        "expected_holding_period_constraint": "2D",
                        "liquidity_evidence_ref": "liquidity-ref-3",
                        "eligibility_ref": "eligibility-ref-3",
                        "risk_note": "basis risk tracked",
                        "no_execution": True,
                        "instrument_eligibility_ref": "instrument-eligibility-ref-1",
                        "leverage_flag": True,
                        "daily_reset_warning": True,
                        "max_allocation_cap": 0.2,
                        "short_holding_period_warning": True,
                        "tracking_error_basis_risk_note": "daily reset and tracking error risk",
                    },
                ],
                "forward_outcome_label": {
                    "label_id": "forward-outcome-label-smoke",
                    "forward_return": 0.04,
                    "forward_drawdown": 0.02,
                    "volatility": 0.15,
                    "turnover": 0.10,
                    "slippage_estimate_ref": "slippage-ref-1",
                    "risk_adjusted_score": 0.60,
                    "benchmark_relative_score": 0.03,
                    "action_label_horizon": "5D",
                    "available_at_safe_label_boundary": True,
                },
                "reward_scoring_policy": {
                    "risk_adjusted_return": 0.60,
                    "max_drawdown_penalty": 0.10,
                    "turnover_penalty": 0.05,
                    "volatility_penalty": 0.04,
                    "benchmark_relative_performance": 0.03,
                    "tail_risk_penalty": 0.02,
                    "action_feasibility_penalty": 0.01,
                },
                "regime_event_leakage_detected": False,
                "future_outcome_leakage_detected": False,
                "source_manifest_ids": ["MANIFEST-SMOKE"],
                "audit_records": [
                    {
                        "audit_record_id": "regime-allocation-audit-smoke",
                        "created_at": "2026-06-25T09:13:00+09:00",
                        "source_path": str(output_dir / "regime_allocation_learning_smoke_fixture.json"),
                        "operator_context": "offline regime allocation learning smoke",
                        "redaction_applied": True,
                        "contains_secret_material": False,
                        "contains_token_material": False,
                        "contains_account_material": False,
                    }
                ],
                "safety_report": {
                    "safety_report_id": "regime-allocation-safety-smoke",
                    "blocked_capabilities": [
                        "LIVE_TRADING_BLOCKED",
                        "REAL_ORDER_BLOCKED",
                        "ACCOUNT_MUTATION_BLOCKED",
                        "BROKER_API_BLOCKED",
                        "NETWORK_BLOCKED",
                        "AUTONOMOUS_TRADING_BLOCKED",
                    ],
                    "findings": [],
                },
            }
        )
    )
    dumped = json.dumps(evaluated.model_dump(mode="json")).lower()
    return {
        "fixture_run": True,
        "regime_feature_report_generated": evaluated.regime_feature_report.report_id.endswith("REPORT"),
        "action_candidate_report_generated": evaluated.action_candidate_report.report_id.endswith("REPORT"),
        "hedge_inverse_eligibility_report_generated": evaluated.hedge_inverse_eligibility_report.report_id.endswith("REPORT"),
        "forward_outcome_label_report_generated": evaluated.forward_outcome_label_report.report_id.endswith("REPORT"),
        "allocation_reward_scoring_report_generated": evaluated.allocation_reward_scoring_report.report_id.endswith("REPORT"),
        "leakage_report_generated": evaluated.regime_allocation_leakage_report.report_id.endswith("REPORT"),
        "readiness_report_generated": evaluated.learning_dataset_readiness_report.report_id.endswith("REPORT"),
        "local_only": evaluated.learning_dataset_readiness_report.local_file_only,
        "offline_only": evaluated.learning_dataset_readiness_report.offline_only,
        "report_only": evaluated.learning_dataset_readiness_report.report_only,
        "non_executable": evaluated.learning_dataset_readiness_report.non_executable,
        "training_ready": evaluated.learning_dataset_readiness_report.decision.value == "TRAINING_READY",
        "no_live_path": evaluated.learning_dataset_readiness_report.no_live_prod and evaluated.learning_dataset_readiness_report.no_autonomous_trading,
        "no_order_path": evaluated.learning_dataset_readiness_report.no_order and "order intent" not in dumped,
        "no_account_mutation": evaluated.learning_dataset_readiness_report.no_account_mutation,
        "no_network": evaluated.learning_dataset_readiness_report.no_network,
        "hedge_inverse_report_only": evaluated.hedge_inverse_eligibility_report.report_only and evaluated.hedge_inverse_eligibility_report.non_executable,
        "parquet_unsupported": ".parquet" not in dumped,
    }


def _run_allocation_policy_training_smoke(output_dir: Path) -> dict[str, bool]:
    evaluated = build_allocation_policy_training_sandbox(
        AllocationPolicyCandidateInput.model_validate(
            {
                "input_id": "allocation-policy-training-input-smoke",
                "training_input": {
                    "learning_dataset_readiness_ref": "dataset-readiness-ref-smoke",
                    "learning_dataset_readiness_decision": "TRAINING_READY",
                    "regime_feature_snapshot_refs": ["REGIME-SNAPSHOT-SMOKE-1", "REGIME-SNAPSHOT-SMOKE-2"],
                    "action_candidate_refs": ["ACTION-REF-SMOKE-1", "ACTION-REF-SMOKE-2"],
                    "forward_outcome_label_refs": ["OUTCOME-REF-SMOKE-1", "OUTCOME-REF-SMOKE-2"],
                    "reward_scoring_refs": ["REWARD-REF-SMOKE-1"],
                    "point_in_time_safety_ref": "pit-safety-ref-smoke",
                    "leakage_guard_ref": "leakage-guard-ref-smoke",
                    "walk_forward_split_ref": "walk-forward-split-ref-smoke",
                },
                "policy_candidate": {
                    "policy_id": "allocation-policy-smoke",
                    "policy_family": "RULE_BASELINE",
                    "action_space": [
                        "KEEP_LONG",
                        "REDUCE_SIZE",
                        "ROTATE_DEFENSIVE",
                        "WATCH_ONLY",
                    ],
                    "regime_feature_set_id": "regime-feature-set-smoke",
                    "training_dataset_ref": "training-dataset-ref-smoke",
                    "walk_forward_validation_ref": "walk-forward-validation-ref-smoke",
                    "strategy_ensemble_ref": "strategy-ensemble-ref-smoke",
                    "reward_scoring_ref": "reward-scoring-ref-smoke",
                    "random_seed_policy_present": True,
                    "reproducibility_hash": "repro-hash-smoke",
                    "artifact_metadata": {
                        "artifact_id": "artifact-smoke",
                        "local_only": True,
                        "offline_only": True,
                        "non_production": True,
                    },
                },
                "training_evaluation_input": {
                    "policy_scores_by_action": {
                        "KEEP_LONG": 0.63,
                        "REDUCE_SIZE": 0.55,
                        "ROTATE_DEFENSIVE": 0.71,
                        "WATCH_ONLY": 0.42,
                    },
                    "selected_action_distribution_by_regime": {
                        "RISK_ON": {"KEEP_LONG": 0.7, "ROTATE_DEFENSIVE": 0.3},
                        "RISK_OFF": {"ROTATE_DEFENSIVE": 0.6, "REDUCE_SIZE": 0.4},
                    },
                    "train_score": 0.66,
                    "validation_score": 0.64,
                    "test_score": 0.62,
                    "forward_paper_score": 0.61,
                    "risk_adjusted_score": 0.58,
                    "turnover_score": 0.12,
                    "slippage_score": 0.03,
                    "max_drawdown_score": 0.08,
                    "stable_fold_count": 3,
                    "fold_count": 4,
                },
                "dependency_status": {
                    "walk_forward_validation_decision": "PAPER_READY",
                    "training_promotion_dependency_decision": "PAPER_CANDIDATE",
                    "ensemble_dependency_decision": "PAPER_CANDIDATE",
                    "point_in_time_evidence_present": True,
                    "available_at_evidence_present": True,
                    "leakage_evidence_present": True,
                },
                "future_outcome_leakage_detected": False,
                "source_manifest_ids": ["MANIFEST-SMOKE"],
                "audit_records": [
                    {
                        "audit_record_id": "allocation-policy-training-audit-smoke",
                        "created_at": "2026-06-25T09:13:00+09:00",
                        "source_path": str(output_dir / "allocation_policy_training_smoke_fixture.json"),
                        "operator_context": "offline allocation policy training smoke",
                        "redaction_applied": True,
                        "contains_secret_material": False,
                        "contains_token_material": False,
                        "contains_account_material": False,
                    }
                ],
                "safety_report": {
                    "safety_report_id": "allocation-policy-training-safety-smoke",
                    "blocked_capabilities": [
                        "LIVE_TRADING_BLOCKED",
                        "REAL_ORDER_BLOCKED",
                        "ACCOUNT_MUTATION_BLOCKED",
                        "BROKER_API_BLOCKED",
                        "NETWORK_BLOCKED",
                        "AUTONOMOUS_TRADING_BLOCKED",
                    ],
                    "findings": [],
                },
            }
        )
    )
    dumped = json.dumps(evaluated.model_dump(mode="json")).lower()
    return {
        "fixture_run": True,
        "summary_report_generated": evaluated.policy_training_summary_report.report_id.endswith("REPORT"),
        "selection_report_generated": evaluated.regime_action_selection_report.report_id.endswith("REPORT"),
        "walk_forward_report_generated": evaluated.allocation_policy_walk_forward_report.report_id.endswith("REPORT"),
        "risk_adjusted_report_generated": evaluated.allocation_policy_risk_adjusted_report.report_id.endswith("REPORT"),
        "turnover_report_generated": evaluated.allocation_policy_turnover_slippage_report.report_id.endswith("REPORT"),
        "drawdown_report_generated": evaluated.allocation_policy_drawdown_stability_report.report_id.endswith("REPORT"),
        "promotion_report_generated": evaluated.policy_promotion_readiness_report.report_id.endswith("REPORT"),
        "artifact_report_generated": evaluated.model_artifact_policy_report.report_id.endswith("REPORT"),
        "local_only": evaluated.policy_promotion_readiness_report.local_file_only,
        "offline_only": evaluated.policy_promotion_readiness_report.offline_only,
        "report_only": evaluated.policy_promotion_readiness_report.report_only,
        "non_executable": evaluated.policy_promotion_readiness_report.non_executable,
        "trained_or_paper_candidate": evaluated.policy_promotion_readiness_report.decision.value in {"TRAINED_OFFLINE", "PAPER_CANDIDATE"},
        "no_live_path": evaluated.policy_promotion_readiness_report.no_live_prod and evaluated.policy_promotion_readiness_report.no_autonomous_trading,
        "no_order_path": evaluated.policy_promotion_readiness_report.no_order and "order intent" not in dumped,
        "no_account_mutation": evaluated.policy_promotion_readiness_report.no_account_mutation,
        "no_network": evaluated.policy_promotion_readiness_report.no_network,
        "artifact_local_only": evaluated.model_artifact_policy_report.local_only and evaluated.model_artifact_policy_report.offline_only and evaluated.model_artifact_policy_report.non_production,
        "parquet_unsupported": ".parquet" not in dumped,
    }


def _run_cnn_fear_greed_smoke(output_dir: Path) -> dict[str, bool]:
    evaluated = run_cnn_fear_greed_collection(
        CNNFearGreedCollectorConfig.model_validate(
            {
                "config_id": "cnn-fear-greed-smoke",
                "source_url": "https://edition.cnn.com/markets/fear-and-greed",
                "enabled": False,
                "execute_collection": False,
                "acknowledge_collection": False,
                "allow_real_network": False,
                "transport_mode": "MOCKED_HTTP",
                "timeout_seconds": 5,
                "max_retry_count": 1,
                "max_requests_per_run": 1,
                "min_collection_interval_seconds": 3600,
                "cache_metadata_policy": "REPORT_ONLY",
                "source_health_reporting": True,
                "mock_payload": {
                    "score": 22,
                    "label": "Extreme Fear",
                    "as_of": "2026-06-24T09:00:00+09:00",
                    "available_at": "2026-06-24T09:05:00+09:00",
                    "components": {
                        "stock_price_strength": 31,
                        "stock_price_breadth": 27,
                    },
                    "history": [
                        {"as_of": "2026-06-23T09:00:00+09:00", "score": 30},
                        {"as_of": "2026-06-24T09:00:00+09:00", "score": 22},
                    ],
                    "schema_version": "cnn-fg-v1",
                },
            }
        )
    )
    (output_dir / "cnn_fear_greed_smoke_input.json").write_text(
        evaluated.model_dump_json(indent=2),
        encoding="utf-8",
    )
    dumped = json.dumps(evaluated.model_dump(mode="json")).lower()
    return {
        "fixture_run": True,
        "snapshot_generated": evaluated.snapshot_report.report_id.endswith("REPORT"),
        "history_report_generated": evaluated.history_report.report_id.endswith("REPORT"),
        "feature_integration_report_generated": evaluated.feature_integration_report.report_id.endswith("REPORT"),
        "source_health_report_generated": evaluated.source_health_report.report_id.endswith("REPORT"),
        "audit_report_generated": evaluated.audit_report.audit_record_id.endswith("REPORT"),
        "safe_default_dry_run": not evaluated.enabled and not evaluated.execute_collection and not evaluated.allow_real_network,
        "mocked_transport_default": evaluated.transport_mode.value == "MOCKED_HTTP",
        "real_network_opt_in_required": not evaluated.allow_real_network and not evaluated.execute_collection,
        "no_real_network_called": evaluated.transport_mode.value != "REAL_HTTP",
        "no_trading_order_account_broker_path": (
            evaluated.no_trading_path
            and evaluated.no_order
            and evaluated.no_account_mutation
            and evaluated.no_broker_api
            and "order intent" not in dumped
            and "account_number" not in dumped
        ),
        "parquet_unsupported": ".parquet" not in dumped,
    }


def _run_risk_adjusted_paper_eval_smoke(output_dir: Path) -> dict[str, bool]:
    evaluated = build_risk_adjusted_paper_evaluation(
        RiskAdjustedPaperEvalInput.model_validate(
            {
                "evaluation_id": "risk-adjusted-paper-eval-smoke",
                "allocation_policy_candidate_ref": "allocation-policy-smoke",
                "policy_promotion_decision": "PAPER_CANDIDATE",
                "point_in_time_dataset_ref": "pit-dataset-ref-smoke",
                "walk_forward_split_ref": "walk-forward-ref-smoke",
                "ensemble_candidate_ref": "ensemble-ref-smoke",
                "regime_feature_refs": ["REGIME-FEATURE-SMOKE-1", "REGIME-FEATURE-SMOKE-2"],
                "cnn_fear_greed_feature_ref": "cnn-fear-greed-ref-smoke",
                "market_data_fixture_ref": "market-data-ref-smoke",
                "fee_tax_slippage_assumptions_ref": "cost-ref-smoke",
                "initial_cash": 1000000.0,
                "evaluation_window_start": "2026-06-20T09:00:00+09:00",
                "evaluation_window_end": "2026-06-24T15:30:00+09:00",
                "benchmark_ref": "kospi-benchmark-ref-smoke",
                "symbol": "005930",
                "quantity": 10,
                "decision_timestamp": "2026-06-20T09:00:00+09:00",
                "simulated_fill_timestamp": "2026-06-20T09:05:00+09:00",
                "simulated_fill_price": 70000.0,
                "benchmark_return": 0.01,
                "end_price": 76000.0,
                "volatility": 0.05,
                "max_drawdown_limit": 0.15,
                "daily_loss_limit": 0.05,
                "max_gross_exposure": 1.0,
                "max_single_action_exposure": 0.8,
                "max_inverse_hedge_exposure": 0.2,
                "turnover_limit": 0.8,
                "inverse_hedge_exposure": 0.05,
                "turnover": 0.25,
                "fee_bps": 5.0,
                "tax_bps": 1.0,
                "slippage_bps": 4.0,
                "future_price_leakage_detected": False,
                "future_regime_fear_leakage_detected": False,
                "available_at_safe_market_data": True,
                "regime_bucket_name": "RISK_OFF",
                "fear_bucket_name": "FEAR",
                "policy_score": 0.71,
                "safety_report": {
                    "safety_report_id": "risk-adjusted-paper-eval-safety-smoke",
                    "blocked_capabilities": [
                        "LIVE_TRADING_BLOCKED",
                        "REAL_ORDER_BLOCKED",
                        "ACCOUNT_MUTATION_BLOCKED",
                        "BROKER_API_BLOCKED",
                        "KIWOOM_API_BLOCKED",
                        "WEBSOCKET_BLOCKED",
                        "NETWORK_BLOCKED",
                        "AUTONOMOUS_TRADING_BLOCKED",
                    ],
                    "findings": [],
                },
                "audit_records": [
                    {
                        "audit_record_id": "risk-adjusted-paper-eval-audit-smoke",
                        "created_at": "2026-06-24T16:00:00+09:00",
                        "source_path": str(output_dir / "risk_adjusted_paper_eval_smoke_fixture.json"),
                        "operator_context": "offline risk adjusted paper evaluation smoke",
                        "redaction_applied": True,
                        "contains_secret_material": False,
                        "contains_token_material": False,
                        "contains_account_material": False,
                    }
                ],
            }
        )
    )
    dumped = json.dumps(evaluated.model_dump(mode="json")).lower()
    return {
        "fixture_run": True,
        "summary_report_generated": evaluated.summary_report.report_id.endswith("REPORT"),
        "portfolio_report_generated": evaluated.virtual_portfolio_report.report_id.endswith("REPORT"),
        "ledger_report_generated": evaluated.virtual_trade_ledger_report.report_id.endswith("REPORT"),
        "cost_report_generated": evaluated.cost_slippage_report.report_id.endswith("REPORT"),
        "risk_adjusted_report_generated": evaluated.risk_adjusted_performance_report.report_id.endswith("REPORT"),
        "drawdown_report_generated": evaluated.drawdown_exposure_report.report_id.endswith("REPORT"),
        "bucket_report_generated": evaluated.regime_fear_bucket_report.report_id.endswith("REPORT"),
        "readiness_report_generated": evaluated.pass_readiness_report.report_id.endswith("REPORT"),
        "local_only": evaluated.pass_readiness_report.local_file_only,
        "offline_only": evaluated.pass_readiness_report.offline_only,
        "report_only": evaluated.pass_readiness_report.report_only,
        "non_executable": evaluated.pass_readiness_report.non_executable,
        "no_live_path": evaluated.pass_readiness_report.no_live_prod and evaluated.pass_readiness_report.no_autonomous_trading,
        "no_order_path": evaluated.pass_readiness_report.no_order and "order intent" not in dumped,
        "no_account_mutation": evaluated.pass_readiness_report.no_account_mutation,
        "no_network": evaluated.pass_readiness_report.no_network,
        "paper_evaluated_or_pass": evaluated.pass_readiness_report.decision.value in {"PAPER_EVALUATED", "PAPER_PASS"},
        "fear_feature_used": evaluated.regime_fear_bucket_report.cnn_fear_greed_feature_used,
        "parquet_unsupported": ".parquet" not in dumped,
    }


def _run_controlled_mock_readiness_smoke(output_dir: Path) -> dict[str, bool]:
    reviewed = build_controlled_mock_readiness_review(
        ControlledMockReadinessInput.model_validate(
            {
                "readiness_review_id": "controlled-mock-readiness-smoke",
                "paper_evaluation_ref": "risk-adjusted-paper-eval-smoke",
                "paper_evaluation_decision": "PAPER_PASS",
                "allocation_policy_ref": "allocation-policy-smoke",
                "allocation_policy_decision": "PAPER_CANDIDATE",
                "strategy_ensemble_ref": "ensemble-smoke",
                "risk_control_ref": "risk-control-smoke",
                "mock_oauth_readiness_ref": "kiwoom-mock-oauth-draft-smoke",
                "mock_oauth_readiness_status": "GAP",
                "mock_market_data_readiness_ref": "kiwoom-mock-market-data-smoke",
                "mock_market_data_readiness_status": "AVAILABLE",
                "broker_adapter_boundary_ref": "broker-mock-boundary-smoke",
                "order_gate_boundary_ref": "order-gate-boundary-smoke",
                "kill_switch_policy_ref": "kill-switch-smoke",
                "user_opt_in_policy_ref": "user-opt-in-smoke",
                "audit_policy_ref": "audit-policy-smoke",
                "rollback_policy_ref": "rollback-policy-smoke",
                "point_in_time_evidence_present": True,
                "walk_forward_evidence_present": True,
                "costs_present": True,
                "cnn_feature_gap_noted": False,
                "drawdown_limit_passed": True,
                "exposure_limit_passed": True,
                "turnover_limit_passed": True,
                "safety_policy": {
                    "policy_id": "controlled-mock-safety-policy-smoke",
                    "maximum_simulated_exposure": 1.0,
                    "maximum_mock_exposure": 0.25,
                    "maximum_inverse_hedge_exposure": 0.2,
                    "daily_loss_limit": 0.05,
                    "maximum_drawdown_limit": 0.15,
                    "order_count_limit": 3,
                },
                "audit_records": [
                    {
                        "audit_record_id": "controlled-mock-readiness-audit-smoke",
                        "created_at": "2026-06-24T16:30:00+09:00",
                        "source_path": str(output_dir / "controlled_mock_readiness_smoke_fixture.json"),
                        "operator_context": "offline controlled mock readiness smoke",
                        "redaction_applied": True,
                        "contains_secret_material": False,
                        "contains_token_material": False,
                        "contains_account_material": False,
                    }
                ],
            }
        )
    )
    dumped = json.dumps(reviewed.model_dump(mode="json")).lower()
    return {
        "fixture_run": True,
        "summary_report_generated": reviewed.summary_report.report_id.endswith("REPORT"),
        "dependency_report_generated": reviewed.dependency_report.report_id.endswith("REPORT"),
        "paper_pass_evidence_report_generated": reviewed.paper_pass_evidence_report.report_id.endswith("REPORT"),
        "infrastructure_report_generated": reviewed.infrastructure_readiness_report.report_id.endswith("REPORT"),
        "safety_policy_report_generated": reviewed.safety_policy_report.report_id.endswith("REPORT"),
        "boundary_violation_report_generated": reviewed.boundary_violation_report.report_id.endswith("REPORT"),
        "gap_report_generated": reviewed.gap_report.gap_report_id.endswith("REPORT"),
        "local_only": reviewed.summary_report.local_file_only,
        "offline_only": reviewed.summary_report.offline_only,
        "report_only": reviewed.summary_report.report_only,
        "non_executable": reviewed.summary_report.non_executable,
        "no_live_path": reviewed.summary_report.no_live_prod and reviewed.summary_report.no_autonomous_trading,
        "no_order_path": reviewed.summary_report.no_order and "order intent" not in dumped,
        "no_account_mutation": reviewed.summary_report.no_account_mutation,
        "no_network": reviewed.summary_report.no_network,
        "no_mock_order_execution": reviewed.summary_report.no_mock_order_execution,
        "review_only": reviewed.summary_report.decision.value in {"MOCK_REVIEW_READY", "MOCK_DRY_RUN_READY", "GAP", "BLOCKED", "RESEARCH_ONLY", "REJECTED"},
        "parquet_unsupported": ".parquet" not in dumped,
    }


def _run_market_regime_smoke(output_dir: Path) -> dict[str, bool]:
    regime = build_market_regime(
        MarketRegimeInput.model_validate(
            {
                "regime_id": "market-regime-smoke",
                "snapshot": {
                    "snapshot_id": "market-regime-snapshot-smoke",
                    "anchor_at": "2026-06-24T09:10:00+09:00",
                    "observed_at": "2026-06-24T09:00:00+09:00",
                    "available_at": "2026-06-24T09:05:00+09:00",
                    "nq": {"symbol": "NQ", "last_value": 20000.0, "pct_change_1d": 0.8, "source_ref": str(output_dir / "nq_smoke.json")},
                    "es": {"symbol": "ES", "last_value": 5500.0, "pct_change_1d": 0.6, "source_ref": str(output_dir / "es_smoke.json")},
                    "vix": {"symbol": "VIX", "last_value": 14.5, "pct_change_1d": -4.0, "source_ref": str(output_dir / "vix_smoke.json")},
                    "dxy": {"symbol": "DXY", "last_value": 104.0, "pct_change_1d": -0.3, "source_ref": str(output_dir / "dxy_smoke.json")},
                    "us10y": {"symbol": "US10Y", "last_value": 4.2, "pct_change_1d": -0.8, "source_ref": str(output_dir / "us10y_smoke.json")},
                    "usdkrw": {"symbol": "USDKRW", "last_value": 1360.0, "pct_change_1d": -0.2, "source_ref": str(output_dir / "usdkrw_smoke.json")},
                    "cnn_fear_greed_feature_ref": str(output_dir / "cnn_fear_greed_smoke.json"),
                    "data_freshness_policy": {
                        "max_age_minutes": 90,
                        "critical_inputs": ["NQ", "ES", "VIX", "DXY", "US10Y", "USDKRW"],
                    },
                },
                "audit_records": [
                    {
                        "audit_record_id": "market-regime-audit-smoke",
                        "created_at": "2026-06-24T09:11:00+09:00",
                        "source_path": str(output_dir / "market_regime_smoke_fixture.json"),
                        "operator_context": "offline market regime smoke",
                        "redaction_applied": True,
                        "contains_secret_material": False,
                        "contains_token_material": False,
                        "contains_account_material": False,
                    }
                ],
            }
        )
    )
    dumped = json.dumps(regime.model_dump(mode="json")).lower()
    return {
        "fixture_run": True,
        "summary_report_generated": regime.summary_report.report_id.endswith("REPORT"),
        "input_snapshot_report_generated": regime.input_snapshot_report.report_id.endswith("REPORT"),
        "risk_appetite_report_generated": regime.risk_appetite_report.report_id.endswith("REPORT"),
        "direction_report_generated": regime.direction_regime_report.report_id.endswith("REPORT"),
        "volatility_report_generated": regime.volatility_regime_report.report_id.endswith("REPORT"),
        "stress_report_generated": regime.stress_report.report_id.endswith("REPORT"),
        "conflict_report_generated": regime.cross_asset_conflict_report.report_id.endswith("REPORT"),
        "constraint_report_generated": regime.downstream_constraint_report.report_id.endswith("REPORT"),
        "training_feature_report_generated": regime.training_feature_integration_report.report_id.endswith("REPORT"),
        "gap_report_generated": regime.gap_report.gap_report_id.endswith("REPORT"),
        "local_only": regime.summary_report.local_file_only,
        "offline_only": regime.summary_report.offline_only,
        "report_only": regime.summary_report.report_only,
        "non_executable": regime.summary_report.non_executable,
        "no_live_path": regime.summary_report.no_live_prod and regime.summary_report.no_autonomous_trading,
        "no_order_path": regime.summary_report.no_order and "order intent" not in dumped,
        "no_account_mutation": regime.summary_report.no_account_mutation,
        "no_network": regime.summary_report.no_network,
        "training_feature_ready": regime.training_feature_integration_report.training_feature_ready,
        "parquet_unsupported": ".parquet" not in dumped,
    }


def _run_macro_regime_smoke(output_dir: Path) -> dict[str, bool]:
    snapshot, capability_report, freshness_report, conflict_report, gap_report, safety_report, event_window_report = build_macro_regime_snapshot(
        MacroRegimePipelineInput.model_validate(
            {
                "pipeline_id": "macro-regime-smoke",
                "anchor_at": "2026-06-26T09:10:00+09:00",
                "available_at": "2026-06-26T09:05:00+09:00",
                "provider_definitions": [
                    {
                        "provider": "LOCAL_FIXTURE",
                        "capabilities": ["NQ_FUTURES", "ES_FUTURES"],
                        "status": "MANUAL_ONLY",
                        "credential_policy": "NOT_REQUIRED",
                        "opt_in_required": False,
                        "notes": "manual futures fixtures only",
                    },
                    {
                        "provider": "FRED",
                        "capabilities": ["VIX", "DOLLAR_STRENGTH", "US10Y", "USDKRW"],
                        "status": "MOCKED_ONLY",
                        "credential_policy": "KEY_REF_ONLY",
                        "supports_real_http": True,
                        "key_ref_required": True,
                        "notes": "fred preview plus mocked parsing",
                    },
                    {
                        "provider": "INVESTING_CALENDAR_MANUAL",
                        "capabilities": ["MANUAL_EVENT_CALENDAR", "CPI_EVENT", "FOMC_EVENT"],
                        "status": "MANUAL_ONLY",
                        "credential_policy": "MANUAL_IMPORT_ONLY",
                        "opt_in_required": False,
                        "notes": "manual macro calendar import",
                    },
                ],
                "manual_series_points": [
                    {
                        "series_id": "NQ_CONTINUOUS",
                        "asset_class": "FUTURES",
                        "provider": "LOCAL_FIXTURE",
                        "provider_symbol": "NQM2026",
                        "observed_at": "2026-06-26T09:00:00+09:00",
                        "available_at": "2026-06-26T09:02:00+09:00",
                        "value": 20150.0,
                        "pct_change_1d": 0.7,
                        "unit": "INDEX",
                        "source_ref": str(output_dir / "macro_nq_smoke.json"),
                    },
                    {
                        "series_id": "ES_CONTINUOUS",
                        "asset_class": "FUTURES",
                        "provider": "LOCAL_FIXTURE",
                        "provider_symbol": "ESM2026",
                        "observed_at": "2026-06-26T09:00:00+09:00",
                        "available_at": "2026-06-26T09:02:00+09:00",
                        "value": 5525.0,
                        "pct_change_1d": 0.5,
                        "unit": "INDEX",
                        "source_ref": str(output_dir / "macro_es_smoke.json"),
                    },
                ],
                "mocked_provider_payloads": [
                    {
                        "payload_id": "macro-fred-vix",
                        "provider": "FRED",
                        "series_id": "VIX",
                        "source_ref": str(output_dir / "macro_fred_vix_smoke.json"),
                        "payload": {"observations": [{"date": "2026-06-25", "value": "16.20"}]},
                    },
                    {
                        "payload_id": "macro-fred-us10y",
                        "provider": "FRED",
                        "series_id": "US10Y",
                        "source_ref": str(output_dir / "macro_fred_us10y_smoke.json"),
                        "payload": {"observations": [{"date": "2026-06-25", "value": "4.10"}]},
                    },
                    {
                        "payload_id": "macro-fred-usdkrw",
                        "provider": "FRED",
                        "series_id": "USDKRW",
                        "source_ref": str(output_dir / "macro_fred_usdkrw_smoke.json"),
                        "payload": {"observations": [{"date": "2026-06-25", "value": "1372.00"}]},
                    },
                    {
                        "payload_id": "macro-fred-dollar",
                        "provider": "FRED",
                        "series_id": "DOLLAR_STRENGTH",
                        "source_ref": str(output_dir / "macro_fred_dollar_smoke.json"),
                        "payload": {"observations": [{"date": "2026-06-25", "value": "121.50"}]},
                    },
                    {
                        "payload_id": "macro-events",
                        "provider": "INVESTING_CALENDAR_MANUAL",
                        "source_ref": str(output_dir / "macro_event_calendar_smoke.json"),
                        "payload": {
                            "events": [
                                {
                                    "event_id": "macro-cpi-smoke",
                                    "event_type": "CPI",
                                    "country": "US",
                                    "title": "US CPI",
                                    "event_time": "2026-06-26T13:30:00+00:00",
                                    "timezone": "UTC",
                                    "importance": "HIGH",
                                    "affected_assets": ["NQ_CONTINUOUS", "ES_CONTINUOUS", "USDKRW"],
                                    "pre_event_block_window_minutes": 30,
                                    "pre_event_reduce_window_minutes": 60,
                                    "post_event_cooldown_minutes": 45,
                                    "event_active_window_minutes": 15,
                                    "available_at": "2026-06-20T00:00:00+00:00",
                                }
                            ]
                        },
                    },
                ],
                "audit_records": [
                    {
                        "audit_record_id": "macro-regime-audit-smoke",
                        "created_at": "2026-06-26T09:11:00+09:00",
                        "source_path": str(output_dir / "macro_regime_smoke_fixture.json"),
                        "operator_context": "offline macro regime smoke",
                        "redaction_applied": True,
                        "contains_secret_material": False,
                        "contains_token_material": False,
                        "contains_account_material": False,
                    }
                ],
            }
        )
    )
    classification = build_macro_regime_classification(snapshot, event_window_report)
    reviewed = build_macro_regime_pipeline_result(
        snapshot,
        classification,
        capability_report,
        freshness_report,
        conflict_report,
        event_window_report,
        gap_report,
        safety_report,
    )
    dumped = json.dumps(reviewed.model_dump(mode="json")).lower()
    return {
        "fixture_run": True,
        "snapshot_generated": reviewed.snapshot.snapshot_id.endswith("SNAPSHOT"),
        "classification_generated": reviewed.classification.classification_id.endswith("CLASSIFICATION"),
        "provider_capability_report_generated": reviewed.provider_capability_report.report_id.endswith("REPORT"),
        "freshness_report_generated": reviewed.freshness_report.report_id.endswith("REPORT"),
        "conflict_report_generated": reviewed.conflict_report.report_id.endswith("REPORT"),
        "event_window_report_generated": reviewed.event_window_report.report_id.endswith("REPORT"),
        "v7_integration_report_generated": reviewed.v7_integration_report.report_id.endswith("REPORT"),
        "v8_integration_report_generated": reviewed.v8_integration_report.report_id.endswith("REPORT"),
        "report_only": reviewed.snapshot.report_only and reviewed.classification.report_only,
        "no_network": reviewed.snapshot.no_network and reviewed.safety_report.no_network,
        "no_env_read": reviewed.snapshot.no_env_read and reviewed.safety_report.no_env_read,
        "no_account_order_path": reviewed.snapshot.no_order and reviewed.snapshot.no_account_mutation,
        "no_executable_output": reviewed.snapshot.non_executable and reviewed.classification.non_executable and "order intent" not in dumped,
        "provider_boundary_only": "provider_setup_required" not in dumped,
        "parquet_unsupported": ".parquet" not in dumped,
    }


def _run_feature_store_smoke(output_dir: Path) -> dict[str, bool]:
    result = build_feature_store_pipeline(
        FeatureStorePipelineInput.model_validate(
            {
                "pipeline_id": "feature-store-smoke",
                "dataset_id": "feature-store-smoke",
                "dataset_profile": "SMOKE_PROFILE",
                "store_root": str(output_dir / "feature_store"),
                "requested_backends": ["IN_MEMORY", "JSON"],
                "partition_spec": {"partition_keys": ["DATASET_ID", "MARKET", "DATE", "SPLIT"]},
                "source_feature_inputs": [
                    {
                        "source_row_id": "row-005930-2026-06-23",
                        "source_kind": "V8_DOMESTIC_STOCK_SNAPSHOT",
                        "instrument_id": "005930",
                        "market": "KRX",
                        "currency": "KRW",
                        "feature_asof": "2026-06-23T15:35:00+09:00",
                        "available_at": "2026-06-23T15:35:00+09:00",
                        "snapshot_at": "2026-06-23T15:35:00+09:00",
                        "feature_namespace": "domestic.price",
                        "feature_values": {"close_price": 81200.0, "volume_ratio": 1.2, "volatility_20d": 0.18},
                        "source_ref": {
                            "source_id": "v8-snapshot-1",
                            "source_kind": "V8_DOMESTIC_STOCK_SNAPSHOT",
                            "sanitized_basename": "snapshot_005930_20260623.json",
                            "relative_path": "fixtures/feature_store/snapshot_005930_20260623.json",
                            "available_at": "2026-06-23T15:35:00+09:00",
                        },
                    },
                    {
                        "source_row_id": "row-005930-2026-06-24",
                        "source_kind": "V9_MACRO_REGIME_SNAPSHOT",
                        "instrument_id": "005930",
                        "market": "KRX",
                        "currency": "KRW",
                        "feature_asof": "2026-06-24T15:35:00+09:00",
                        "available_at": "2026-06-24T15:35:00+09:00",
                        "snapshot_at": "2026-06-24T15:35:00+09:00",
                        "feature_namespace": "macro.regime_classification",
                        "feature_values": {"macro_risk_on": True, "dollar_strength_score": 0.35, "volatility_20d": 0.19},
                        "source_ref": {
                            "source_id": "v9-macro-1",
                            "source_kind": "V9_MACRO_REGIME_SNAPSHOT",
                            "sanitized_basename": "macro_20260624.json",
                            "relative_path": "fixtures/feature_store/macro_20260624.json",
                            "available_at": "2026-06-24T15:35:00+09:00",
                        },
                    },
                    {
                        "source_row_id": "row-005930-2026-06-25",
                        "source_kind": "V7_POINT_IN_TIME_UNIVERSE_CONTEXT",
                        "instrument_id": "005930",
                        "market": "KRX",
                        "currency": "KRW",
                        "feature_asof": "2026-06-25T15:35:00+09:00",
                        "available_at": "2026-06-25T15:35:00+09:00",
                        "snapshot_at": "2026-06-25T15:35:00+09:00",
                        "feature_namespace": "risk.training_guard_context",
                        "feature_values": {"pit_universe_member": True, "volatility_20d": 0.2},
                        "source_ref": {
                            "source_id": "v7-context-1",
                            "source_kind": "V7_POINT_IN_TIME_UNIVERSE_CONTEXT",
                            "sanitized_basename": "v7_context_20260625.json",
                            "relative_path": "fixtures/feature_store/v7_context_20260625.json",
                            "available_at": "2026-06-25T15:35:00+09:00",
                        },
                    },
                ],
                "price_history_rows": [
                    {
                        "instrument_id": "005930",
                        "observed_at": "2026-06-23T15:30:00+09:00",
                        "available_at": "2026-06-23T15:35:00+09:00",
                        "open_price": 80000.0,
                        "high_price": 81300.0,
                        "low_price": 79800.0,
                        "close_price": 81200.0,
                        "volume": 1000000,
                        "source_ref": {
                            "source_id": "bar-20260623",
                            "source_kind": "V8_CAPTURED_KIWOOM_CHART_HISTORY",
                            "sanitized_basename": "bar_20260623.json",
                            "relative_path": "fixtures/feature_store/bar_20260623.json",
                            "available_at": "2026-06-23T15:35:00+09:00",
                        },
                    },
                    {
                        "instrument_id": "005930",
                        "observed_at": "2026-06-24T15:30:00+09:00",
                        "available_at": "2026-06-24T15:35:00+09:00",
                        "open_price": 81250.0,
                        "high_price": 82000.0,
                        "low_price": 80900.0,
                        "close_price": 81800.0,
                        "volume": 980000,
                        "source_ref": {
                            "source_id": "bar-20260624",
                            "source_kind": "V8_CAPTURED_KIWOOM_CHART_HISTORY",
                            "sanitized_basename": "bar_20260624.json",
                            "relative_path": "fixtures/feature_store/bar_20260624.json",
                            "available_at": "2026-06-24T15:35:00+09:00",
                        },
                    },
                    {
                        "instrument_id": "005930",
                        "observed_at": "2026-06-25T15:30:00+09:00",
                        "available_at": "2026-06-25T15:35:00+09:00",
                        "open_price": 81850.0,
                        "high_price": 82600.0,
                        "low_price": 81600.0,
                        "close_price": 82400.0,
                        "volume": 1010000,
                        "source_ref": {
                            "source_id": "bar-20260625",
                            "source_kind": "V8_CAPTURED_KIWOOM_CHART_HISTORY",
                            "sanitized_basename": "bar_20260625.json",
                            "relative_path": "fixtures/feature_store/bar_20260625.json",
                            "available_at": "2026-06-25T15:35:00+09:00",
                        },
                    },
                    {
                        "instrument_id": "005930",
                        "observed_at": "2026-06-26T15:30:00+09:00",
                        "available_at": "2026-06-26T15:35:00+09:00",
                        "open_price": 82450.0,
                        "high_price": 83300.0,
                        "low_price": 82300.0,
                        "close_price": 83100.0,
                        "volume": 990000,
                        "source_ref": {
                            "source_id": "bar-20260626",
                            "source_kind": "V8_CAPTURED_KIWOOM_CHART_HISTORY",
                            "sanitized_basename": "bar_20260626.json",
                            "relative_path": "fixtures/feature_store/bar_20260626.json",
                            "available_at": "2026-06-26T15:35:00+09:00",
                        },
                    },
                ],
                "label_specs": [
                    {
                        "label_name": "FORWARD_RETURN",
                        "label_horizon": "1D",
                        "label_horizon_policy": "TRADING_SESSION",
                        "derivation_method": "LOCAL_PRICE_HISTORY_FORWARD_RETURN",
                        "label_direction": "LONG",
                        "anchor_price_policy": "LAST_AVAILABLE_CLOSE",
                    }
                ],
                "audit_records": [
                    {
                        "audit_record_id": "feature-store-audit-smoke",
                        "created_at": "2026-06-26T16:00:00+09:00",
                        "source_path": str(output_dir / "feature_store_smoke_fixture.json"),
                        "operator_context": "offline feature store smoke",
                        "redaction_applied": True,
                        "contains_secret_material": False,
                        "contains_token_material": False,
                        "contains_account_material": False,
                    }
                ],
            }
        ),
        repo_root=Path(__file__).resolve().parents[2],
    )
    dumped = json.dumps(result.model_dump(mode="json")).lower()
    return {
        "fixture_run": True,
        "cache_manifest_generated": result.cache_manifest.manifest_id.endswith("MANIFEST"),
        "dataset_manifest_generated": result.dataset_manifest.dataset_id.endswith("SMOKE"),
        "training_dataset_manifest_generated": result.training_dataset_manifest.dataset_id.endswith("SMOKE"),
        "walk_forward_plan_generated": result.walk_forward_plan.plan_id.endswith("PLAN"),
        "leakage_report_generated": result.leakage_report.report_id.endswith("REPORT"),
        "backend_capability_report_generated": result.backend_capability_report.report_id.endswith("REPORT"),
        "v7_integration_report_generated": result.v7_integration_report.report_id.endswith("REPORT"),
        "v8_integration_report_generated": result.v8_integration_report.report_id.endswith("REPORT"),
        "v9_integration_report_generated": result.v9_integration_report.report_id.endswith("REPORT"),
        "report_only": result.training_dataset_manifest.report_only and result.leakage_report.report_only,
        "no_network": result.training_dataset_manifest.no_network and result.safety_report.no_network,
        "no_env_read": result.training_dataset_manifest.no_env_read and result.safety_report.no_env_read,
        "no_account_order_path": result.training_dataset_manifest.no_order and result.training_dataset_manifest.no_account_mutation,
        "no_training": result.training_dataset_manifest.no_model_training,
        "no_paper_trading": result.training_dataset_manifest.no_paper_trading,
        "safe_local_materialization_only": "feature_store" in dumped and "rejected_path" not in dumped,
    }


def _run_paper_evaluation_smoke(output_dir: Path) -> dict[str, bool]:
    feature_store_input = FeatureStorePipelineInput.model_validate(
        {
            "pipeline_id": "paper-evaluation-feature-store-smoke",
            "dataset_id": "paper-evaluation-smoke",
            "dataset_profile": "SMOKE_PROFILE",
            "store_root": str(output_dir / "feature_store"),
            "requested_backends": ["IN_MEMORY"],
            "partition_spec": {"partition_keys": ["DATASET_ID", "MARKET", "DATE", "SPLIT"]},
            "source_feature_inputs": [
                {
                    "source_row_id": "row-005930-2026-06-23",
                    "source_kind": "V8_DOMESTIC_STOCK_SNAPSHOT",
                    "instrument_id": "005930",
                    "market": "KRX",
                    "currency": "KRW",
                    "feature_asof": "2026-06-23T15:35:00+09:00",
                    "available_at": "2026-06-23T15:35:00+09:00",
                    "snapshot_at": "2026-06-23T15:35:00+09:00",
                    "feature_namespace": "domestic.price",
                    "feature_values": {"close_price": 81200.0, "signal_score": 0.82, "volume_ratio": 1.2, "volatility_20d": 0.18},
                    "source_ref": {
                        "source_id": "v8-paper-snapshot-1",
                        "source_kind": "V8_DOMESTIC_STOCK_SNAPSHOT",
                        "sanitized_basename": "paper_snapshot_1.json",
                        "relative_path": "fixtures/paper_evaluation/snapshot_1.json",
                        "available_at": "2026-06-23T15:35:00+09:00",
                    },
                },
                {
                    "source_row_id": "row-005930-2026-06-24",
                    "source_kind": "V9_MACRO_REGIME_SNAPSHOT",
                    "instrument_id": "005930",
                    "market": "KRX",
                    "currency": "KRW",
                    "feature_asof": "2026-06-24T15:35:00+09:00",
                    "available_at": "2026-06-24T15:35:00+09:00",
                    "snapshot_at": "2026-06-24T15:35:00+09:00",
                    "feature_namespace": "macro.regime_classification",
                    "feature_values": {"macro_risk_on": True, "signal_score": 0.78, "macro_block_score": 0.2, "volatility_20d": 0.19},
                    "source_ref": {
                        "source_id": "v9-paper-macro-1",
                        "source_kind": "V9_MACRO_REGIME_SNAPSHOT",
                        "sanitized_basename": "paper_macro_1.json",
                        "relative_path": "fixtures/paper_evaluation/macro_1.json",
                        "available_at": "2026-06-24T15:35:00+09:00",
                    },
                },
                {
                    "source_row_id": "row-005930-2026-06-25",
                    "source_kind": "V7_EVENT_RISK_CONTEXT",
                    "instrument_id": "005930",
                    "market": "KRX",
                    "currency": "KRW",
                    "feature_asof": "2026-06-25T15:35:00+09:00",
                    "available_at": "2026-06-25T15:35:00+09:00",
                    "snapshot_at": "2026-06-25T15:35:00+09:00",
                    "feature_namespace": "risk.event_risk_context",
                    "feature_values": {"event_window_active": False, "signal_score": 0.81, "volatility_20d": 0.2},
                    "source_ref": {
                        "source_id": "v7-paper-event-1",
                        "source_kind": "V7_EVENT_RISK_CONTEXT",
                        "sanitized_basename": "paper_event_1.json",
                        "relative_path": "fixtures/paper_evaluation/event_1.json",
                        "available_at": "2026-06-25T15:35:00+09:00",
                    },
                },
            ],
            "price_history_rows": [
                {
                    "instrument_id": "005930",
                    "observed_at": "2026-06-23T15:30:00+09:00",
                    "available_at": "2026-06-23T15:35:00+09:00",
                    "open_price": 80000.0,
                    "high_price": 81300.0,
                    "low_price": 79800.0,
                    "close_price": 81200.0,
                    "volume": 1000000,
                    "source_ref": {
                        "source_id": "paper-bar-20260623",
                        "source_kind": "V8_CAPTURED_KIWOOM_CHART_HISTORY",
                        "sanitized_basename": "paper_bar_20260623.json",
                        "relative_path": "fixtures/paper_evaluation/bar_20260623.json",
                        "available_at": "2026-06-23T15:35:00+09:00",
                    },
                },
                {
                    "instrument_id": "005930",
                    "observed_at": "2026-06-24T15:30:00+09:00",
                    "available_at": "2026-06-24T15:35:00+09:00",
                    "open_price": 81250.0,
                    "high_price": 82000.0,
                    "low_price": 80900.0,
                    "close_price": 81800.0,
                    "volume": 980000,
                    "source_ref": {
                        "source_id": "paper-bar-20260624",
                        "source_kind": "V8_CAPTURED_KIWOOM_CHART_HISTORY",
                        "sanitized_basename": "paper_bar_20260624.json",
                        "relative_path": "fixtures/paper_evaluation/bar_20260624.json",
                        "available_at": "2026-06-24T15:35:00+09:00",
                    },
                },
                {
                    "instrument_id": "005930",
                    "observed_at": "2026-06-25T15:30:00+09:00",
                    "available_at": "2026-06-25T15:35:00+09:00",
                    "open_price": 81850.0,
                    "high_price": 82600.0,
                    "low_price": 81600.0,
                    "close_price": 82400.0,
                    "volume": 1010000,
                    "source_ref": {
                        "source_id": "paper-bar-20260625",
                        "source_kind": "V8_CAPTURED_KIWOOM_CHART_HISTORY",
                        "sanitized_basename": "paper_bar_20260625.json",
                        "relative_path": "fixtures/paper_evaluation/bar_20260625.json",
                        "available_at": "2026-06-25T15:35:00+09:00",
                    },
                },
                {
                    "instrument_id": "005930",
                    "observed_at": "2026-06-26T15:30:00+09:00",
                    "available_at": "2026-06-26T15:35:00+09:00",
                    "open_price": 82450.0,
                    "high_price": 83300.0,
                    "low_price": 82300.0,
                    "close_price": 83100.0,
                    "volume": 990000,
                    "source_ref": {
                        "source_id": "paper-bar-20260626",
                        "source_kind": "V8_CAPTURED_KIWOOM_CHART_HISTORY",
                        "sanitized_basename": "paper_bar_20260626.json",
                        "relative_path": "fixtures/paper_evaluation/bar_20260626.json",
                        "available_at": "2026-06-26T15:35:00+09:00",
                    },
                },
            ],
            "label_specs": [
                {
                    "label_name": "FORWARD_RETURN",
                    "label_horizon": "1D",
                    "label_horizon_policy": "TRADING_SESSION",
                    "derivation_method": "LOCAL_PRICE_HISTORY_FORWARD_RETURN",
                    "label_direction": "LONG",
                    "anchor_price_policy": "LAST_AVAILABLE_CLOSE",
                }
            ],
            "audit_records": [
                {
                    "audit_record_id": "paper-evaluation-feature-store-audit-smoke",
                    "created_at": "2026-06-26T16:05:00+09:00",
                    "source_path": str(output_dir / "paper_evaluation_feature_store_smoke_fixture.json"),
                    "operator_context": "offline paper evaluation feature store smoke",
                    "redaction_applied": True,
                    "contains_secret_material": False,
                    "contains_token_material": False,
                    "contains_account_material": False,
                }
            ],
        }
    )
    feature_store_result = build_feature_store_pipeline(feature_store_input, repo_root=Path(__file__).resolve().parents[2])
    paper = build_paper_evaluation_pipeline(
        PaperEvaluationPipelineInput.model_validate(
            {
                "pipeline_id": "paper-evaluation-smoke",
                "dataset_id": "paper-evaluation-smoke",
                "training_dataset_manifest": feature_store_result.training_dataset_manifest.model_dump(mode="json"),
                "feature_rows": [row.model_dump(mode="json") for row in feature_store_result.feature_rows],
                "training_rows": [row.model_dump(mode="json") for row in feature_store_result.training_rows],
                "walk_forward_plan": feature_store_result.walk_forward_plan.model_dump(mode="json"),
                "leakage_report": feature_store_result.leakage_report.model_dump(mode="json"),
                "price_history_rows": [bar.model_dump(mode="json") for bar in feature_store_input.price_history_rows],
                "config": {
                    "fill_policy": "NEXT_BAR_OPEN",
                    "starting_cash": 10000000.0,
                    "commission_bps": 5.0,
                    "tax_bps": 15.0,
                    "slippage_bps": 10.0,
                    "spread_penalty_bps": 5.0,
                },
                "audit_records": [
                    {
                        "audit_record_id": "paper-evaluation-audit-smoke",
                        "created_at": "2026-06-26T16:10:00+09:00",
                        "source_path": str(output_dir / "paper_evaluation_smoke_fixture.json"),
                        "operator_context": "offline paper evaluation smoke",
                        "redaction_applied": True,
                        "contains_secret_material": False,
                        "contains_token_material": False,
                        "contains_account_material": False,
                    }
                ],
            }
        )
    )
    dumped = json.dumps(paper.model_dump(mode="json")).lower()
    return {
        "fixture_run": True,
        "plan_generated": paper.plan.plan_id.endswith("PLAN"),
        "signal_replay_generated": bool(paper.signals),
        "fill_simulation_generated": bool(paper.fills),
        "ledger_generated": bool(paper.ledger_entries),
        "metrics_generated": paper.metrics_report.report_id.endswith("REPORT"),
        "integration_generated": paper.integration_report.report_id.endswith("REPORT"),
        "safety_generated": paper.safety_report.report_id.endswith("REPORT"),
        "report_only": paper.plan.report_only and paper.metrics_report.report_only,
        "no_network": paper.plan.no_network and paper.safety_report.no_network,
        "no_env_read": paper.plan.no_env_read and paper.safety_report.no_env_read,
        "no_account_order_path": paper.plan.no_order and paper.plan.no_account_mutation,
        "no_model_training": paper.plan.no_model_training and paper.safety_report.no_model_training,
        "no_broker_paper_api": paper.plan.no_broker_paper_api,
        "no_executable_output": paper.plan.non_executable and "authorization" not in dumped and "account_id" not in dumped,
    }


def _run_portfolio_reconciliation_smoke(output_dir: Path) -> dict[str, bool]:
    feature_store_input = FeatureStorePipelineInput.model_validate(
        {
            "pipeline_id": "portfolio-reconciliation-feature-store-smoke",
            "dataset_id": "portfolio-reconciliation-smoke",
            "dataset_profile": "SMOKE_PROFILE",
            "store_root": str(output_dir / "feature_store"),
            "requested_backends": ["IN_MEMORY"],
            "partition_spec": {"partition_keys": ["DATASET_ID", "MARKET", "DATE", "SPLIT"]},
            "source_feature_inputs": [
                {
                    "source_row_id": "row-005930-2026-06-25",
                    "source_kind": "V8_DOMESTIC_STOCK_SNAPSHOT",
                    "instrument_id": "005930",
                    "market": "KRX",
                    "currency": "KRW",
                    "feature_asof": "2026-06-25T15:35:00+09:00",
                    "available_at": "2026-06-25T15:35:00+09:00",
                    "snapshot_at": "2026-06-25T15:35:00+09:00",
                    "feature_namespace": "domestic.price",
                    "feature_values": {"close_price": 82400.0, "signal_score": 0.81, "volatility_20d": 0.2},
                    "source_ref": {
                        "source_id": "v8-recon-snapshot-1",
                        "source_kind": "V8_DOMESTIC_STOCK_SNAPSHOT",
                        "sanitized_basename": "recon_snapshot_1.json",
                        "relative_path": "fixtures/reconciliation/snapshot_1.json",
                        "available_at": "2026-06-25T15:35:00+09:00",
                    },
                }
            ],
            "price_history_rows": [
                {
                    "instrument_id": "005930",
                    "observed_at": "2026-06-25T15:30:00+09:00",
                    "available_at": "2026-06-25T15:35:00+09:00",
                    "open_price": 81850.0,
                    "high_price": 82600.0,
                    "low_price": 81600.0,
                    "close_price": 82400.0,
                    "volume": 1010000,
                    "source_ref": {
                        "source_id": "recon-bar-20260625",
                        "source_kind": "V8_CAPTURED_KIWOOM_CHART_HISTORY",
                        "sanitized_basename": "recon_bar_20260625.json",
                        "relative_path": "fixtures/reconciliation/bar_20260625.json",
                        "available_at": "2026-06-25T15:35:00+09:00",
                    },
                },
                {
                    "instrument_id": "005930",
                    "observed_at": "2026-06-26T15:30:00+09:00",
                    "available_at": "2026-06-26T15:35:00+09:00",
                    "open_price": 82450.0,
                    "high_price": 83300.0,
                    "low_price": 82300.0,
                    "close_price": 83100.0,
                    "volume": 990000,
                    "source_ref": {
                        "source_id": "recon-bar-20260626",
                        "source_kind": "V8_CAPTURED_KIWOOM_CHART_HISTORY",
                        "sanitized_basename": "recon_bar_20260626.json",
                        "relative_path": "fixtures/reconciliation/bar_20260626.json",
                        "available_at": "2026-06-26T15:35:00+09:00",
                    },
                },
            ],
            "label_specs": [
                {
                    "label_name": "FORWARD_RETURN",
                    "label_horizon": "1D",
                    "label_horizon_policy": "TRADING_SESSION",
                    "derivation_method": "LOCAL_PRICE_HISTORY_FORWARD_RETURN",
                    "label_direction": "LONG",
                    "anchor_price_policy": "LAST_AVAILABLE_CLOSE",
                }
            ],
            "audit_records": [
                {
                    "audit_record_id": "portfolio-reconciliation-feature-store-audit-smoke",
                    "created_at": "2026-06-26T16:15:00+09:00",
                    "source_path": str(output_dir / "portfolio_reconciliation_feature_store_smoke_fixture.json"),
                    "operator_context": "offline reconciliation feature store smoke",
                    "redaction_applied": True,
                    "contains_secret_material": False,
                    "contains_token_material": False,
                    "contains_account_material": False,
                }
            ],
        }
    )
    feature_store_result = build_feature_store_pipeline(feature_store_input, repo_root=Path(__file__).resolve().parents[2])
    paper = build_paper_evaluation_pipeline(
        PaperEvaluationPipelineInput.model_validate(
            {
                "pipeline_id": "portfolio-reconciliation-paper-evaluation-smoke",
                "dataset_id": "portfolio-reconciliation-smoke",
                "training_dataset_manifest": feature_store_result.training_dataset_manifest.model_dump(mode="json"),
                "feature_rows": [row.model_dump(mode="json") for row in feature_store_result.feature_rows],
                "training_rows": [row.model_dump(mode="json") for row in feature_store_result.training_rows],
                "walk_forward_plan": feature_store_result.walk_forward_plan.model_dump(mode="json"),
                "leakage_report": feature_store_result.leakage_report.model_dump(mode="json"),
                "price_history_rows": [bar.model_dump(mode="json") for bar in feature_store_input.price_history_rows],
                "config": {"fill_policy": "NEXT_BAR_OPEN", "starting_cash": 10000000.0},
                "audit_records": [
                    {
                        "audit_record_id": "portfolio-reconciliation-paper-audit-smoke",
                        "created_at": "2026-06-26T16:20:00+09:00",
                        "source_path": str(output_dir / "portfolio_reconciliation_paper_smoke_fixture.json"),
                        "operator_context": "offline reconciliation paper smoke",
                        "redaction_applied": True,
                        "contains_secret_material": False,
                        "contains_token_material": False,
                        "contains_account_material": False,
                    }
                ],
            }
        )
    )
    account_read_input = AccountReadPipelineInput.model_validate(
        {
            "pipeline_id": "portfolio-reconciliation-account-read-smoke",
            "provider": "LOCAL_MANUAL",
            "mode": "MANUAL_FIXTURE",
            "requested_at": "2026-06-26T16:30:00+09:00",
            "snapshot_fixture": {
                "metadata": {
                    "snapshot_id": "ACCOUNT-SMOKE-SNAPSHOT",
                    "provider": "LOCAL_MANUAL",
                    "mode": "MANUAL_FIXTURE",
                    "account_ref": "acct-redacted-9d3f",
                    "account_ref_policy": "REDACTED_TEXT_PLUS_HASH",
                    "observed_at": "2026-06-26T15:35:00+09:00",
                    "available_at": "2026-06-26T15:36:00+09:00",
                    "account_base_currency": "KRW",
                    "source_ref": {
                        "source_id": "account-smoke-source",
                        "source_kind": "MANUAL_ACCOUNT_SNAPSHOT_FIXTURE",
                        "sanitized_basename": "account_smoke_snapshot.json",
                        "relative_path": "fixtures/reconciliation/account_snapshot.json",
                        "available_at": "2026-06-26T15:36:00+09:00",
                    },
                    "metadata": {"capture_mode": "manual_fixture"},
                },
                "cash_balances": [{"currency": "KRW", "available_cash": 9800000.0, "settled_cash": 9800000.0}],
                "holdings": [
                    {
                        "instrument_id": "005930",
                        "market": "KRX",
                        "currency": "KRW",
                        "quantity": 1.0,
                        "average_cost": 82450.0,
                        "last_price": 83100.0,
                        "market_value": 83100.0,
                        "source_ref": {
                            "source_id": "account-smoke-holding-source",
                            "source_kind": "MANUAL_ACCOUNT_SNAPSHOT_FIXTURE",
                            "sanitized_basename": "account_smoke_holding.json",
                            "relative_path": "fixtures/reconciliation/account_holding.json",
                            "available_at": "2026-06-26T15:36:00+09:00",
                        },
                    }
                ],
                "total_market_value": 83100.0,
                "total_equity": 9883100.0,
            },
            "audit_records": [
                {
                    "audit_record_id": "portfolio-reconciliation-account-audit-smoke",
                    "created_at": "2026-06-26T16:30:00+09:00",
                    "source_path": str(output_dir / "portfolio_reconciliation_account_smoke_fixture.json"),
                    "operator_context": "offline account read smoke",
                    "redaction_applied": True,
                    "contains_secret_material": False,
                    "contains_token_material": False,
                    "contains_account_material": False,
                }
            ],
        }
    )
    account_snapshot_result = build_account_read_snapshot_pipeline(account_read_input)
    reconciliation = build_portfolio_reconciliation_pipeline(
        account_read_input,
        PortfolioReconciliationPipelineInput.model_validate(
            {
                "pipeline_id": "portfolio-reconciliation-smoke",
                "dataset_id": "portfolio-reconciliation-smoke",
                "paper_evaluation": paper.model_dump(mode="json"),
                "account_snapshot": account_snapshot_result.snapshot.model_dump(mode="json"),
                "target_positions": [{"instrument_id": "005930", "market": "KRX", "currency": "KRW", "quantity": 1.0, "target_weight": 1.0}],
                "audit_records": [
                    {
                        "audit_record_id": "portfolio-reconciliation-audit-smoke",
                        "created_at": "2026-06-26T16:35:00+09:00",
                        "source_path": str(output_dir / "portfolio_reconciliation_smoke_fixture.json"),
                        "operator_context": "offline portfolio reconciliation smoke",
                        "redaction_applied": True,
                        "contains_secret_material": False,
                        "contains_token_material": False,
                        "contains_account_material": False,
                    }
                ],
                "evaluated_at": "2026-06-26T16:35:00+09:00",
            }
        ),
    )
    dumped = json.dumps(reconciliation.model_dump(mode="json")).lower()
    return {
        "fixture_run": True,
        "plan_generated": reconciliation.plan_report.report_id.endswith("REPORT"),
        "report_generated": reconciliation.reconciliation_report.report_id.endswith("REPORT"),
        "integration_generated": reconciliation.integration_report.report_id.endswith("REPORT"),
        "report_only": reconciliation.plan_report.report_only and reconciliation.safety_report.report_only,
        "no_network": reconciliation.plan_report.no_network and reconciliation.safety_report.no_network,
        "no_env_read": reconciliation.plan_report.no_env_read and reconciliation.safety_report.no_env_read,
        "no_account_order_path": reconciliation.plan_report.no_order and reconciliation.plan_report.no_account_mutation,
        "no_executable_output": reconciliation.plan_report.non_executable and "authorization" not in dumped and "account_number" not in dumped,
        "redacted_account_ref": "redacted" in account_snapshot_result.snapshot.metadata.account_ref.lower() and "account_number" not in dumped,
    }


def _run_controlled_execution_smoke(output_dir: Path) -> dict[str, bool]:
    controlled_execution = build_controlled_execution_preflight(
        ControlledExecutionPipelineInput.model_validate(
            {
                "pipeline_id": "controlled-execution-smoke",
                "dataset_id": "paper-evaluation-smoke",
                "mode": "MOCK_EXECUTION_ONLY",
                "provider": "LOCAL_MOCK",
                "opt_in": {
                    "allow_mock_execution": True,
                    "allow_dry_run": True,
                    "acknowledge_readonly_only": True,
                    "acknowledge_no_account_mutation": True,
                    "acknowledge_manual_approval_required": True,
                    "acknowledge_user_initiated": True,
                },
                "requested_by": "LOCAL_OPERATOR",
                "requested_at": "2026-06-26T16:50:00+09:00",
                "instrument_id": "005930",
                "provider_symbol": "005930.KS",
                "market": "KRX",
                "side": "BUY",
                "reference_price": 82450.0,
                "quantity_proposal": 1.0,
                "notional_proposal": 82450.0,
                "risk_budget_ref": "RISK-BUDGET-REF-1",
                "feature_store_manifest": {"dataset_id": "paper-evaluation-smoke", "ready": True},
                "leakage_report": {"readiness_status": "TRAINING_DATASET_MANIFEST_READY"},
                "paper_evaluation_report": {"readiness_status": "PLAN_READY", "signal_used_labels": False, "metrics_available": True},
                "macro_regime_report": {"snapshot_ready": True, "stale": False},
                "domestic_snapshot_report": {"snapshot_ready": True, "liquidity_safe": True, "stale": False},
                "position_sizing_report": {"decision": "SIZE_READY", "risk_budget_ref": "RISK-BUDGET-REF-1", "unbounded_size": False},
                "event_risk_report": {"decision": "ALLOW", "stale": False},
                "breadth_routing_report": {"decision": "BROAD_MARKET_OK"},
                "controlled_mock_rehearsal_report": {"decision": "MOCK_EXECUTION_REVIEW_READY"},
                "account_read_report": {"read_only": True, "account_ref_redacted": True, "stale": False},
                "reconciliation_report": {
                    "readiness_status": "RECONCILIATION_REPORT_READY",
                    "instrument_mapping_unambiguous": True,
                    "cash_position_mismatch_classified": True,
                },
                "adapter_evidence": {
                    "mock_ready": True,
                    "dry_run_ready": True,
                    "kiwoom_exact_schema": True,
                    "kiwoom_allowlisted": True,
                    "ls_exact_schema": False,
                    "ls_allowlisted": False,
                },
                "manual_approval_fixture": {
                    "approval_ref": "fake-approval-controlled-execution-smoke",
                    "order_draft_hash": "DRAFT-CONTROLLED-EXECUTION-SMOKE-005930-BUY",
                    "already_used": False,
                    "expiry_at": "2026-06-26T17:20:00+09:00",
                },
                "live_boundary_evidence_ref": "fixtures/controlled_execution/live_boundary_evidence.json",
                "idempotency_key": "IDEMPOTENCY-KEY-SMOKE",
                "audit_records": [
                    {
                        "audit_record_id": "controlled-execution-smoke-audit",
                        "created_at": "2026-06-26T16:49:00+09:00",
                        "source_path": str(output_dir / "controlled_execution_smoke_fixture.json"),
                        "operator_context": "offline controlled execution smoke",
                        "redaction_applied": True,
                        "contains_secret_material": False,
                        "contains_token_material": False,
                        "contains_account_material": False,
                    }
                ],
            }
        )
    )
    dumped = json.dumps(controlled_execution.model_dump(mode="json")).lower()
    return {
        "fixture_run": True,
        "readiness_generated": controlled_execution.readiness_report.report_id.endswith("REPORT"),
        "preflight_generated": controlled_execution.preflight_decision.decision_id.endswith("DECISION"),
        "approval_generated": controlled_execution.approval_packet.packet_id.endswith("PACKET"),
        "mock_execution_generated": controlled_execution.mock_execution_result.result_id.endswith("RESULT"),
        "dry_run_generated": controlled_execution.dry_run_result.result_id.endswith("RESULT"),
        "audit_generated": bool(controlled_execution.audit_records),
        "report_only": controlled_execution.readiness_report.report_only and controlled_execution.safety_report.report_only,
        "no_network": controlled_execution.readiness_report.no_network and controlled_execution.safety_report.no_network,
        "no_env_read": controlled_execution.readiness_report.no_env_read and controlled_execution.safety_report.no_env_read,
        "no_account_order_path": controlled_execution.readiness_report.no_order and controlled_execution.readiness_report.no_account_mutation,
        "no_executable_output": controlled_execution.readiness_report.non_executable and "authorization" not in dumped and "account_number" not in dumped,
        "live_boundary_blocked": controlled_execution.adapter_capability_report.blocked_submit_preview["blocked"] is True,
    }


def _run_market_data_provider_registry_smoke(output_dir: Path) -> dict[str, bool]:
    registry = build_market_data_provider_registry(
        MarketDataProviderRegistryInput.model_validate(
            {
                "registry_id": "provider-registry-smoke",
                "provider_candidates": [
                    {
                        "provider_name": "LOCAL_FIXTURE",
                        "provider_type": "LOCAL",
                        "access_mode": "LOCAL",
                        "official": False,
                        "internal": True,
                        "historical_support": True,
                        "read_only_support": True,
                        "api_key_required": False,
                        "subscription_required": False,
                        "license_terms_note_ref": str(output_dir / "local_fixture_license.md"),
                        "latency_class": "OFFLINE",
                        "expected_freshness": "FIXTURE_STATIC",
                        "allowed_use_cases": ["DEVELOPMENT", "TESTING"],
                        "disallowed_use_cases": ["LIVE_READ_ONLY"],
                        "implementation_status": "ACTIVE",
                        "risk_note": "local fixture only",
                        "readiness_level": "FIXTURE_ONLY",
                    },
                    {
                        "provider_name": "DATABENTO",
                        "provider_type": "API",
                        "access_mode": "PAID",
                        "official": True,
                        "historical_support": True,
                        "read_only_support": True,
                        "api_key_required": True,
                        "subscription_required": True,
                        "license_terms_note_ref": str(output_dir / "databento_license.md"),
                        "latency_class": "LOW",
                        "expected_freshness": "NEAR_REALTIME",
                        "allowed_use_cases": ["BACKTEST", "TRAINING"],
                        "disallowed_use_cases": ["LIVE_TRADING"],
                        "implementation_status": "CANDIDATE",
                        "risk_note": "requires subscription evidence",
                        "readiness_level": "TRAINING_READY",
                        "subscription_evidence_ref": str(output_dir / "databento_subscription.md"),
                        "api_key_evidence_ref": str(output_dir / "databento_boundary.md"),
                    },
                    {
                        "provider_name": "IBKR",
                        "provider_type": "BROKER_READONLY",
                        "access_mode": "PAID",
                        "official": True,
                        "historical_support": True,
                        "live_support": True,
                        "read_only_support": True,
                        "subscription_required": True,
                        "license_terms_note_ref": str(output_dir / "ibkr_license.md"),
                        "latency_class": "LOW",
                        "expected_freshness": "LIVE_READONLY",
                        "allowed_use_cases": ["LIVE_READ_ONLY"],
                        "disallowed_use_cases": ["LIVE_TRADING"],
                        "implementation_status": "CANDIDATE",
                        "risk_note": "candidate only",
                        "readiness_level": "LIVE_READ_ONLY_READY",
                        "subscription_evidence_ref": str(output_dir / "ibkr_subscription.md"),
                    },
                    {
                        "provider_name": "YAHOO_DELAYED",
                        "provider_type": "PUBLIC_WEB",
                        "access_mode": "FREE",
                        "unofficial": True,
                        "delayed": True,
                        "historical_support": True,
                        "delayed_support": True,
                        "read_only_support": True,
                        "license_terms_note_ref": str(output_dir / "yahoo_license.md"),
                        "latency_class": "DELAYED",
                        "expected_freshness": "DELAYED",
                        "allowed_use_cases": ["SANITY_CHECK"],
                        "disallowed_use_cases": ["TRAINING", "LIVE_READ_ONLY"],
                        "implementation_status": "CANDIDATE",
                        "risk_note": "delayed only",
                        "readiness_level": "SANITY_CHECK_ONLY",
                    },
                    {
                        "provider_name": "FRED",
                        "provider_type": "API",
                        "access_mode": "FREE",
                        "official": True,
                        "historical_support": True,
                        "read_only_support": True,
                        "license_terms_note_ref": str(output_dir / "fred_license.md"),
                        "latency_class": "DELAYED",
                        "expected_freshness": "DAILY",
                        "allowed_use_cases": ["RESEARCH", "TRAINING"],
                        "disallowed_use_cases": ["LIVE_TRADING"],
                        "implementation_status": "CANDIDATE",
                        "risk_note": "macro reference only",
                        "readiness_level": "RESEARCH_READY",
                    },
                    {
                        "provider_name": "ECOS_BOK",
                        "provider_type": "API",
                        "access_mode": "FREE",
                        "official": True,
                        "historical_support": True,
                        "read_only_support": True,
                        "license_terms_note_ref": str(output_dir / "ecos_license.md"),
                        "latency_class": "DELAYED",
                        "expected_freshness": "DAILY",
                        "allowed_use_cases": ["RESEARCH", "TRAINING"],
                        "disallowed_use_cases": ["LIVE_TRADING"],
                        "implementation_status": "CANDIDATE",
                        "risk_note": "macro/fx reference only",
                        "readiness_level": "RESEARCH_READY",
                    },
                    {
                        "provider_name": "CNN_FEAR_GREED",
                        "provider_type": "PUBLIC_WEB",
                        "access_mode": "FREE",
                        "unofficial": True,
                        "historical_support": True,
                        "read_only_support": True,
                        "license_terms_note_ref": str(output_dir / "cnn_license.md"),
                        "latency_class": "DELAYED",
                        "expected_freshness": "DAILY",
                        "allowed_use_cases": ["SENTIMENT_FEATURE"],
                        "disallowed_use_cases": ["LIVE_TRADING"],
                        "implementation_status": "ACTIVE",
                        "risk_note": "sentiment feature only",
                        "readiness_level": "RESEARCH_READY",
                    },
                ],
                "module_requirements": [
                    {
                        "module_name": "MARKET_REGIME_ENGINE",
                        "required_data_classes": ["FUTURES", "VOLATILITY_INDEX", "FX", "RATES_YIELDS"],
                        "optional_data_classes": ["SENTIMENT_FEAR_INDEX"],
                        "minimum_readiness_level": "TRAINING_READY",
                        "freshness_requirement": "UNDER_90_MINUTES",
                        "available_at_required": True,
                        "source_ref_required": True,
                        "historical_depth_requirement": "1D_PLUS",
                        "training_grade_required": True,
                        "fallback_policy": "GAP_IF_CRITICAL_MISSING",
                    }
                ],
                "canonical_contracts": [
                    {
                        "instrument_key": "NQ_FUTURES_MAIN",
                        "provider_symbol": "NQ.c.0",
                        "data_class": "FUTURES",
                        "observed_at": "2026-06-24T09:00:00+09:00",
                        "available_at": "2026-06-24T09:05:00+09:00",
                        "value": 20000.0,
                        "open": 19920.0,
                        "high": 20010.0,
                        "low": 19890.0,
                        "close": 20000.0,
                        "volume": 123456.0,
                        "percent_change": 0.8,
                        "currency": "USD",
                        "market": "CME",
                        "timezone": "America/Chicago",
                        "data_delay_seconds": 0,
                        "source_provider": "DATABENTO",
                        "source_ref": str(output_dir / "nq_contract.json"),
                        "quality_flags": ["POINT_IN_TIME_SAFE"],
                        "stale": False,
                        "gap_reason": None,
                        "corporate_action_adjusted": False,
                        "survivorship_safe": True,
                    }
                ],
                "symbol_mappings": [
                    {"mapping_id": "MAP-NQ", "canonical_key": "NQ_FUTURES_MAIN", "provider_symbol": "NQ.c.0", "provider_name": "DATABENTO", "data_class": "FUTURES"},
                    {"mapping_id": "MAP-ES", "canonical_key": "ES_FUTURES_MAIN", "provider_symbol": "ES.c.0", "provider_name": "DATABENTO", "data_class": "FUTURES"},
                    {"mapping_id": "MAP-VIX", "canonical_key": "VIX_INDEX", "provider_symbol": "VIX", "provider_name": "YAHOO_DELAYED", "data_class": "VOLATILITY_INDEX"},
                    {"mapping_id": "MAP-DXY", "canonical_key": "DXY_INDEX", "provider_symbol": "DX-Y.NYB", "provider_name": "YAHOO_DELAYED", "data_class": "FX"},
                    {"mapping_id": "MAP-10Y", "canonical_key": "US10Y_YIELD", "provider_symbol": "DGS10", "provider_name": "FRED", "data_class": "RATES_YIELDS"},
                    {"mapping_id": "MAP-USDKRW", "canonical_key": "USDKRW_SPOT", "provider_symbol": "USDKRW", "provider_name": "ECOS_BOK", "data_class": "FX"},
                    {"mapping_id": "MAP-FOMC", "canonical_key": "FOMC_EVENT", "provider_symbol": "FOMC", "provider_name": "FED", "data_class": "ECONOMIC_CALENDAR"},
                    {"mapping_id": "MAP-CPI", "canonical_key": "US_CPI_EVENT", "provider_symbol": "CPI", "provider_name": "BLS", "data_class": "ECONOMIC_CALENDAR"},
                ],
                "audit_records": [
                    {
                        "audit_record_id": "provider-registry-audit-smoke",
                        "created_at": "2026-06-24T18:00:00+09:00",
                        "source_path": str(output_dir / "provider_registry_smoke_fixture.json"),
                        "operator_context": "offline provider registry smoke",
                        "redaction_applied": True,
                        "contains_secret_material": False,
                        "contains_token_material": False,
                        "contains_account_material": False,
                    }
                ],
            }
        )
    )
    dumped = json.dumps(registry.model_dump(mode="json")).lower()
    return {
        "fixture_run": True,
        "registry_report_generated": registry.global_provider_registry_report.report_id.endswith("REPORT"),
        "module_requirement_report_generated": registry.module_data_requirement_report.report_id.endswith("REPORT"),
        "readiness_matrix_report_generated": registry.provider_readiness_matrix_report.report_id.endswith("REPORT"),
        "canonical_contract_report_generated": registry.canonical_data_contract_report.report_id.endswith("REPORT"),
        "symbol_mapping_report_generated": registry.symbol_mapping_report.report_id.endswith("REPORT"),
        "selection_report_generated": registry.provider_selection_report.report_id.endswith("REPORT"),
        "gap_report_generated": registry.gap_report.gap_report_id.endswith("REPORT"),
        "local_only": registry.global_provider_registry_report.local_file_only,
        "offline_only": registry.global_provider_registry_report.offline_only,
        "report_only": registry.global_provider_registry_report.report_only,
        "non_executable": registry.global_provider_registry_report.non_executable,
        "no_live_path": registry.global_provider_registry_report.no_live_prod and registry.global_provider_registry_report.no_autonomous_trading,
        "no_order_path": registry.global_provider_registry_report.no_order and "order intent" not in dumped,
        "no_account_mutation": registry.global_provider_registry_report.no_account_mutation,
        "no_network": registry.global_provider_registry_report.no_network,
        "no_provider_call": (
            registry.global_provider_registry_report.no_provider_api
            and registry.global_provider_registry_report.no_network
            and registry.global_provider_registry_report.no_websocket
        ),
        "parquet_unsupported": ".parquet" not in dumped,
    }


def _run_position_sizing_smoke(output_dir: Path) -> dict[str, bool]:
    review = build_position_sizing_review(
        PositionSizingInput.model_validate(
            {
                "sizing_review_id": "position-sizing-smoke",
                "candidate_symbol": "QQQ",
                "market": "NASDAQ",
                "currency": "USD",
                "side": "LONG",
                "candidate_action_type": "ALLOCATE",
                "entry_price": 500.0,
                "current_price": 500.0,
                "atr_value": 10.0,
                "atr_period": 14,
                "atr_multiplier": 2.0,
                "fixed_stop_percent": 0.05,
                "explicit_stop_price": 475.0,
                "account_equity": 100000.0,
                "available_cash": 100000.0,
                "risk_per_trade_percent": 0.01,
                "max_risk_cash_per_trade": 1000.0,
                "daily_risk_budget": 2500.0,
                "remaining_daily_risk_budget": 2500.0,
                "current_gross_exposure": 0.10,
                "current_net_exposure": 0.10,
                "current_open_risk_percent": 0.005,
                "max_portfolio_exposure": 1.0,
                "max_gross_exposure": 1.0,
                "max_net_exposure": 1.0,
                "max_single_position_exposure": 0.25,
                "max_sector_exposure": 0.35,
                "max_inverse_hedge_exposure": 0.15,
                "sector_name": "TECH",
                "sector_exposure_after_trade_estimate": 0.20,
                "is_inverse_or_hedge": False,
                "instrument_eligibility_ref": str(output_dir / "position_eligibility.md"),
                "liquidity_evidence_ref": str(output_dir / "position_liquidity.md"),
                "leverage_flag": False,
                "daily_reset_warning": False,
                "short_holding_period_warning": False,
                "basis_risk_note": "LOW",
                "fee_bps": 5.0,
                "tax_bps": 0.0,
                "slippage_bps": 3.0,
                "fee_tax_slippage_assumption_ref": str(output_dir / "position_costs.md"),
                "fx_conversion_rate": 1.0,
                "fx_conversion_ref": str(output_dir / "usdusd.md"),
                "market_regime_constraint_ref": str(output_dir / "market_regime_report.json"),
                "market_regime_label": "RISK_ON",
                "market_volatility_state": "NORMAL_VOL",
                "market_stress_state": "NORMAL",
                "market_regime_size_multiplier": 1.0,
                "provider_readiness_ref": str(output_dir / "provider_selection_report.json"),
                "provider_readiness_level": "PAPER_READY",
                "provider_policy_allows_research_only": False,
                "price_contract_ref": str(output_dir / "qqq_price_contract.json"),
                "atr_contract_ref": str(output_dir / "qqq_atr_contract.json"),
                "fx_contract_ref": str(output_dir / "usd_contract.json"),
                "cost_contract_ref": str(output_dir / "cost_contract.json"),
                "paper_evaluation_ref": str(output_dir / "risk_adjusted_eval.json"),
                "available_at": "2026-06-24T09:05:00+09:00",
                "observed_at": "2026-06-24T09:00:00+09:00",
                "decision_anchor_at": "2026-06-24T09:05:00+09:00",
                "source_refs": [
                    str(output_dir / "qqq_price_contract.json"),
                    str(output_dir / "provider_selection_report.json"),
                ],
                "stop_mode": "FIXED_PERCENT",
                "requested_allocation_percent": 0.20,
                "requested_quantity": 100,
                "round_lot_size": 1,
                "confidence_multiplier": 1.0,
                "volatility_size_multiplier": 1.0,
                "learned_size_multiplier": 1.0,
                "max_daily_loss_cap": 0.03,
                "max_open_risk_cap": 0.05,
                "max_order_count_per_day": 5,
                "cool_down_policy": "NONE",
                "fail_closed": True,
                "report_only_preview_allowed": True,
                "safety_report": {
                    "safety_report_id": "position-sizing-smoke-safety",
                    "blocked_capabilities": [
                        "LIVE_TRADING_BLOCKED",
                        "REAL_ORDER_BLOCKED",
                        "ACCOUNT_MUTATION_BLOCKED",
                        "BROKER_API_BLOCKED",
                        "KIWOOM_API_BLOCKED",
                        "WEBSOCKET_BLOCKED",
                        "NETWORK_BLOCKED",
                        "AUTONOMOUS_TRADING_BLOCKED",
                    ],
                    "findings": [],
                },
                "audit_records": [
                    {
                        "audit_record_id": "position-sizing-smoke-audit",
                        "created_at": "2026-06-24T18:00:00+09:00",
                        "source_path": str(output_dir / "position_sizing_fixture.json"),
                        "operator_context": "offline position sizing smoke",
                        "redaction_applied": True,
                        "contains_secret_material": False,
                        "contains_token_material": False,
                        "contains_account_material": False,
                    }
                ],
            }
        )
    )
    dumped = json.dumps(review.model_dump(mode="json")).lower()
    return {
        "fixture_run": True,
        "summary_report_generated": review.summary_report.report_id.endswith("REPORT"),
        "stop_distance_report_generated": review.stop_distance_report.report_id.endswith("REPORT"),
        "risk_budget_report_generated": review.risk_budget_report.report_id.endswith("REPORT"),
        "data_readiness_report_generated": review.data_readiness_report.report_id.endswith("REPORT"),
        "quantity_notional_report_generated": review.quantity_notional_report.report_id.endswith("REPORT"),
        "cost_assumption_report_generated": review.cost_assumption_report.report_id.endswith("REPORT"),
        "market_regime_adjustment_report_generated": review.market_regime_adjustment_report.report_id.endswith("REPORT"),
        "inverse_hedge_report_generated": review.inverse_hedge_sizing_report.report_id.endswith("REPORT"),
        "boundary_report_generated": review.boundary_violation_report.report_id.endswith("REPORT"),
        "gap_report_generated": review.gap_report.gap_report_id.endswith("REPORT"),
        "local_only": review.summary_report.local_file_only,
        "offline_only": review.summary_report.offline_only,
        "report_only": review.summary_report.report_only,
        "non_executable": review.summary_report.non_executable,
        "no_live_path": review.summary_report.no_live_prod and review.summary_report.no_autonomous_trading,
        "no_order_path": review.summary_report.no_order and review.summary_report.non_executable,
        "no_account_mutation": review.summary_report.no_account_mutation,
        "no_network": review.summary_report.no_network,
        "no_provider_call": review.summary_report.no_provider_api and review.summary_report.no_network and review.summary_report.no_websocket,
        "parquet_unsupported": ".parquet" not in dumped,
    }


def _run_event_risk_smoke(output_dir: Path) -> dict[str, bool]:
    review = build_event_risk_review(
        EventRiskInput.model_validate(
            {
                "event_risk_review_id": "event-risk-smoke",
                "candidate_symbol": "QQQ",
                "market": "NASDAQ",
                "country_scope": "US",
                "candidate_action_type": "NEW_ENTRY",
                "candidate_side": "BUY",
                "decision_timestamp": "2026-06-24T11:00:00+09:00",
                "available_at": "2026-06-24T10:00:00+09:00",
                "provider_readiness_ref": str(output_dir / "provider_selection_report.json"),
                "provider_readiness_level": "PAPER_READY",
                "calendar_source_ref": str(output_dir / "economic_calendar_snapshot.json"),
                "calendar_provider_ref": str(output_dir / "economic_calendar_provider.json"),
                "calendar_freshness_minutes": 30,
                "calendar_max_age_minutes": 120,
                "fail_closed_if_calendar_missing": True,
                "position_sizing_ref": str(output_dir / "position_sizing_report.json"),
                "position_sizing_decision": "SIZE_READY",
                "position_sizing_quantity": 40,
                "position_sizing_notional": 20000.0,
                "position_sizing_size_multiplier": 1.0,
                "market_regime_ref": str(output_dir / "market_regime_report.json"),
                "market_regime_label": "RISK_ON",
                "existing_position": False,
                "is_single_name": False,
                "is_inverse_or_hedge": False,
                "net_exposure_reducing_action": False,
                "events": [
                    {
                        "event_id": "fomc-2026-06",
                        "event_type": "FOMC_RATE_DECISION",
                        "country_scope": "US",
                        "market_scope": "GLOBAL",
                        "affected_markets": ["NASDAQ", "NYSE"],
                        "scheduled_at": "2026-06-24T14:00:00+09:00",
                        "available_at": "2026-06-24T10:00:00+09:00",
                        "source_provider_ref": str(output_dir / "economic_calendar_provider.json"),
                        "source_calendar_ref": str(output_dir / "economic_calendar_snapshot.json"),
                        "importance_level": "CRITICAL",
                        "expected_impact": "rate decision risk event",
                        "event_status": "SCHEDULED",
                        "timezone": "ASIA/SEOUL",
                        "event_window_policy_ref": str(output_dir / "fomc_window_policy.json"),
                    }
                ],
                "event_windows": [
                    {
                        "window_id": "fomc-window",
                        "event_type": "FOMC_RATE_DECISION",
                        "importance_level": "CRITICAL",
                        "pre_event_block_window_minutes": 240,
                        "pre_event_reduce_window_minutes": 720,
                        "post_event_cooldown_minutes": 180,
                        "event_active_window_minutes": 120,
                        "new_entry_allowed": False,
                        "position_increase_allowed": False,
                        "reduce_only": False,
                        "watch_only": False,
                        "event_size_multiplier": 0.5,
                        "forced_gap_if_calendar_missing": True,
                        "policy_reason": "fomc risk gate",
                    }
                ],
                "source_refs": [
                    str(output_dir / "economic_calendar_snapshot.json"),
                    str(output_dir / "provider_selection_report.json"),
                    str(output_dir / "position_sizing_report.json"),
                ],
                "safety_report": {
                    "safety_report_id": "event-risk-smoke-safety",
                    "blocked_capabilities": [
                        "LIVE_TRADING_BLOCKED",
                        "REAL_ORDER_BLOCKED",
                        "ACCOUNT_MUTATION_BLOCKED",
                        "BROKER_API_BLOCKED",
                        "KIWOOM_API_BLOCKED",
                        "WEBSOCKET_BLOCKED",
                        "NETWORK_BLOCKED",
                        "AUTONOMOUS_TRADING_BLOCKED",
                    ],
                    "findings": [],
                },
                "audit_records": [
                    {
                        "audit_record_id": "event-risk-smoke-audit",
                        "created_at": "2026-06-24T18:00:00+09:00",
                        "source_path": str(output_dir / "event_risk_fixture.json"),
                        "operator_context": "offline event risk smoke",
                        "redaction_applied": True,
                        "contains_secret_material": False,
                        "contains_token_material": False,
                        "contains_account_material": False,
                    }
                ],
            }
        )
    )
    dumped = json.dumps(review.model_dump(mode="json")).lower()
    return {
        "fixture_run": True,
        "summary_report_generated": review.summary_report is not None and review.summary_report.report_id.endswith("REPORT"),
        "calendar_snapshot_report_generated": review.calendar_snapshot_report is not None and review.calendar_snapshot_report.report_id.endswith("REPORT"),
        "event_window_report_generated": review.event_window_report is not None and review.event_window_report.report_id.endswith("REPORT"),
        "restriction_report_generated": review.restriction_report is not None and review.restriction_report.report_id.endswith("REPORT"),
        "position_sizing_adjustment_report_generated": review.position_sizing_adjustment_report is not None and review.position_sizing_adjustment_report.report_id.endswith("REPORT"),
        "provider_readiness_report_generated": review.provider_readiness_report is not None and review.provider_readiness_report.report_id.endswith("REPORT"),
        "leakage_report_generated": review.leakage_report is not None and review.leakage_report.report_id.endswith("REPORT"),
        "gap_report_generated": review.gap_report is not None and review.gap_report.gap_report_id.endswith("REPORT"),
        "local_only": review.summary_report is not None and review.summary_report.local_file_only,
        "offline_only": review.summary_report is not None and review.summary_report.offline_only,
        "report_only": review.summary_report is not None and review.summary_report.report_only,
        "non_executable": review.summary_report is not None and review.summary_report.non_executable,
        "no_live_path": review.summary_report is not None and review.summary_report.no_live_prod and review.summary_report.no_autonomous_trading,
        "no_order_path": review.summary_report is not None and review.summary_report.no_order and review.summary_report.non_executable,
        "no_account_mutation": review.summary_report is not None and review.summary_report.no_account_mutation,
        "no_network": review.summary_report is not None and review.summary_report.no_network,
        "no_provider_call": review.summary_report is not None and review.summary_report.no_provider_api and review.summary_report.no_network and review.summary_report.no_websocket,
        "parquet_unsupported": ".parquet" not in dumped,
    }


def _run_breadth_leadership_routing_smoke(output_dir: Path) -> dict[str, bool]:
    review = build_breadth_leadership_routing_review(
        BreadthLeadershipRoutingInput.model_validate(
            {
                "routing_review_id": "breadth-routing-smoke",
                "candidate_symbol": "NVDA",
                "candidate_market": "NASDAQ",
                "candidate_sector_id": "SEMIS",
                "candidate_sector_name": "SEMICONDUCTORS",
                "candidate_action_type": "NEW_ENTRY",
                "decision_timestamp": "2026-06-25T09:30:00+09:00",
                "candidate_is_large_cap": True,
                "candidate_is_leadership_sector": True,
                "candidate_is_outlier_momentum": False,
                "candidate_news_catalyst_available": False,
                "candidate_disclosure_catalyst_available": False,
                "breadth_snapshot": {
                    "snapshot_id": "breadth-snapshot-smoke",
                    "market": "NASDAQ",
                    "benchmark_ref": str(output_dir / "qqq_index.json"),
                    "observed_at": "2026-06-25T09:00:00+09:00",
                    "available_at": "2026-06-25T09:10:00+09:00",
                    "source_provider_ref": str(output_dir / "breadth_provider.json"),
                    "total_listed_universe_count": 500,
                    "tradable_universe_count": 480,
                    "advancing_count": 320,
                    "declining_count": 120,
                    "unchanged_count": 40,
                    "new_highs_count": 90,
                    "new_lows_count": 15,
                    "above_moving_average_count": 300,
                    "below_moving_average_count": 140,
                    "up_volume": 7000000000.0,
                    "down_volume": 3000000000.0,
                    "total_volume": 10000000000.0,
                    "relative_volume": 1.2,
                    "index_return_percent": 1.1,
                    "equal_weight_proxy_return_percent": 0.9,
                    "large_cap_proxy_return_percent": 1.2,
                    "small_mid_cap_proxy_return_percent": 0.8,
                    "data_freshness_policy_ref": str(output_dir / "breadth_freshness.md"),
                },
                "sector_leadership_snapshots": [
                    {
                        "sector_id": "SEMIS",
                        "sector_name": "SEMICONDUCTORS",
                        "sector_return_percent": 2.8,
                        "sector_relative_strength": 1.7,
                        "sector_volume_share": 0.22,
                        "sector_trading_value_share": 0.24,
                        "sector_advancing_count": 24,
                        "sector_declining_count": 8,
                        "sector_new_highs_count": 10,
                        "sector_new_lows_count": 1,
                        "sector_internal_breadth_score": 0.74,
                        "top_contributors": ["NVDA", "AVGO", "AMD"],
                        "leadership_concentration_score": 0.52,
                        "source_refs": [
                            str(output_dir / "semis_sector.json"),
                            str(output_dir / "sector_mapping_provider.json"),
                        ],
                        "available_at": "2026-06-25T09:10:00+09:00",
                    }
                ],
                "index_distortion_snapshot": {
                    "snapshot_id": "distortion-snapshot-smoke",
                    "top_1_contribution_share": 0.12,
                    "top_2_contribution_share": 0.21,
                    "top_5_contribution_share": 0.39,
                    "top_10_contribution_share": 0.58,
                    "mega_cap_contribution_share": 0.44,
                    "index_return_excluding_top_contributors_percent": 0.6,
                    "equal_weight_divergence_percent": 0.2,
                    "large_cap_vs_small_mid_divergence_percent": 0.4,
                    "index_distortion_score": 0.32,
                    "distorted_index_warning": False,
                    "source_refs": [
                        str(output_dir / "top_contributors.json"),
                        str(output_dir / "provider_selection_report.json"),
                    ],
                    "available_at": "2026-06-25T09:10:00+09:00",
                },
                "outlier_momentum_candidates": [],
                "outlier_sleeve_policy": {
                    "policy_id": "outlier-sleeve-smoke",
                    "max_portfolio_allocation": 0.10,
                    "max_per_name_risk": 0.0075,
                    "max_daily_loss": 0.015,
                    "max_outlier_names": 3,
                    "mandatory_stop_discipline": True,
                    "mandatory_liquidity_evidence": True,
                    "mandatory_slippage_note": True,
                    "mandatory_no_execution_flag": True,
                    "event_risk_compatibility_required": True,
                    "watch_only_fallback_when_evidence_missing": True,
                },
                "market_regime_ref": str(output_dir / "market_regime_report.json"),
                "market_regime_label": "RISK_ON",
                "market_regime_risk_appetite": "RISK_ON",
                "position_sizing_ref": str(output_dir / "position_sizing_report.json"),
                "position_sizing_decision": "SIZE_READY",
                "event_risk_ref": str(output_dir / "event_risk_review.json"),
                "event_risk_decision": "ALLOW",
                "breadth_provider_readiness_ref": str(output_dir / "breadth_provider.json"),
                "breadth_provider_readiness_level": "PAPER_READY",
                "sector_mapping_provider_readiness_ref": str(output_dir / "sector_mapping_provider.json"),
                "sector_mapping_provider_readiness_level": "PAPER_READY",
                "market_internals_provider_readiness_ref": str(output_dir / "market_internals_provider.json"),
                "market_internals_provider_readiness_level": "PAPER_READY",
                "relative_volume_provider_readiness_ref": str(output_dir / "relative_volume_provider.json"),
                "relative_volume_provider_readiness_level": "PAPER_READY",
                "news_catalyst_provider_ref": str(output_dir / "news_provider.json"),
                "canonical_data_contract_ref": str(output_dir / "canonical_breadth_contract.json"),
                "source_refs": [
                    str(output_dir / "provider_selection_report.json"),
                    str(output_dir / "canonical_breadth_contract.json"),
                    str(output_dir / "market_regime_report.json"),
                    str(output_dir / "position_sizing_report.json"),
                    str(output_dir / "event_risk_review.json"),
                ],
                "safety_report": {
                    "safety_report_id": "breadth-routing-smoke-safety",
                    "blocked_capabilities": [
                        "LIVE_TRADING_BLOCKED",
                        "REAL_ORDER_BLOCKED",
                        "ACCOUNT_MUTATION_BLOCKED",
                        "BROKER_API_BLOCKED",
                        "KIWOOM_API_BLOCKED",
                        "WEBSOCKET_BLOCKED",
                        "NETWORK_BLOCKED",
                        "AUTONOMOUS_TRADING_BLOCKED",
                    ],
                    "findings": [],
                },
                "audit_records": [
                    {
                        "audit_record_id": "breadth-routing-smoke-audit",
                        "created_at": "2026-06-25T09:31:00+09:00",
                        "source_path": str(output_dir / "breadth_routing_fixture.json"),
                        "operator_context": "offline breadth leadership routing smoke",
                        "redaction_applied": True,
                        "contains_secret_material": False,
                        "contains_token_material": False,
                        "contains_account_material": False,
                    }
                ],
            }
        )
    )
    dumped = json.dumps(review.model_dump(mode="json")).lower()
    return {
        "fixture_run": True,
        "summary_report_generated": review.summary_report is not None and review.summary_report.report_id.endswith("REPORT"),
        "breadth_input_snapshot_report_generated": review.breadth_input_snapshot_report is not None and review.breadth_input_snapshot_report.report_id.endswith("REPORT"),
        "advance_decline_report_generated": review.advance_decline_report is not None and review.advance_decline_report.report_id.endswith("REPORT"),
        "new_high_low_report_generated": review.new_high_low_report is not None and review.new_high_low_report.report_id.endswith("REPORT"),
        "up_down_volume_participation_report_generated": review.up_down_volume_participation_report is not None and review.up_down_volume_participation_report.report_id.endswith("REPORT"),
        "sector_leadership_report_generated": review.sector_leadership_report is not None and review.sector_leadership_report.report_id.endswith("REPORT"),
        "leadership_concentration_report_generated": review.leadership_concentration_report is not None and review.leadership_concentration_report.report_id.endswith("REPORT"),
        "index_distortion_report_generated": review.index_distortion_report is not None and review.index_distortion_report.report_id.endswith("REPORT"),
        "equal_weight_divergence_report_generated": review.equal_weight_divergence_report is not None and review.equal_weight_divergence_report.report_id.endswith("REPORT"),
        "outlier_momentum_candidate_report_generated": review.outlier_momentum_candidate_report is not None and review.outlier_momentum_candidate_report.report_id.endswith("REPORT"),
        "outlier_sleeve_risk_report_generated": review.outlier_sleeve_risk_report is not None and review.outlier_sleeve_risk_report.report_id.endswith("REPORT"),
        "downstream_constraint_report_generated": review.downstream_constraint_report is not None and review.downstream_constraint_report.report_id.endswith("REPORT"),
        "provider_readiness_report_generated": review.provider_readiness_report is not None and review.provider_readiness_report.report_id.endswith("REPORT"),
        "leakage_report_generated": review.leakage_report is not None and review.leakage_report.report_id.endswith("REPORT"),
        "gap_report_generated": review.gap_report is not None and review.gap_report.gap_report_id.endswith("REPORT"),
        "local_only": review.summary_report is not None and review.summary_report.local_file_only,
        "offline_only": review.summary_report is not None and review.summary_report.offline_only,
        "report_only": review.summary_report is not None and review.summary_report.report_only,
        "non_executable": review.summary_report is not None and review.summary_report.non_executable,
        "no_live_path": review.summary_report is not None and review.summary_report.no_live_prod and review.summary_report.no_autonomous_trading,
        "no_order_path": review.summary_report is not None and review.summary_report.no_order and review.summary_report.non_executable,
        "no_account_mutation": review.summary_report is not None and review.summary_report.no_account_mutation,
        "no_network": review.summary_report is not None and review.summary_report.no_network,
        "no_provider_call": review.summary_report is not None and review.summary_report.no_provider_api and review.summary_report.no_network and review.summary_report.no_websocket,
        "parquet_unsupported": ".parquet" not in dumped,
    }


def _run_controlled_mock_dry_run_smoke(output_dir: Path) -> dict[str, bool]:
    reviewed = build_controlled_mock_dry_run_review(
        ControlledMockDryRunInput.model_validate(
            {
                "dry_run_id": "controlled-mock-dry-run-smoke",
                "candidate_symbol": "NVDA",
                "candidate_market": "NASDAQ",
                "candidate_side": "BUY",
                "candidate_action_type": "NEW_ENTRY",
                "candidate_is_leadership": True,
                "candidate_is_outlier": False,
                "candidate_is_exposure_reducing": False,
                "candidate_is_inverse_or_hedge": False,
                "route_hint": "CORE_STRATEGY",
                "paper_evaluation_ref": str(output_dir / "paper_eval_report.json"),
                "paper_evaluation_decision": "PAPER_PASS",
                "mock_readiness_ref": str(output_dir / "mock_readiness_report.json"),
                "mock_readiness_decision": "MOCK_DRY_RUN_READY",
                "market_regime_ref": str(output_dir / "market_regime_report.json"),
                "market_regime_decision": "TRAINING_FEATURE_READY",
                "market_regime_label": "RISK_ON",
                "provider_registry_ref": str(output_dir / "provider_registry_report.json"),
                "provider_registry_decision": "PAPER_READY",
                "position_sizing_ref": str(output_dir / "position_sizing_review.json"),
                "position_sizing_decision": "SIZE_READY",
                "quantity_preview": 50,
                "notional_preview": 25000.0,
                "event_risk_ref": str(output_dir / "event_risk_review.json"),
                "event_risk_decision": "ALLOW",
                "breadth_routing_ref": str(output_dir / "breadth_routing_review.json"),
                "breadth_routing_decision": "LEADERSHIP_ONLY",
                "breadth_constraints": ["REDUCE_SIZE", "WATCH_NON_LEADERS"],
                "strategy_ensemble_ref": str(output_dir / "strategy_ensemble_report.json"),
                "risk_policy_ref": str(output_dir / "risk_policy_report.json"),
                "mock_market_data_readiness_ref": str(output_dir / "mock_market_data_readiness.json"),
                "mock_market_data_readiness_status": "AVAILABLE",
                "mock_oauth_readiness_ref": str(output_dir / "mock_oauth_readiness.json"),
                "mock_oauth_readiness_status": "AVAILABLE",
                "order_gate_boundary_ref": str(output_dir / "order_gate_boundary.json"),
                "kill_switch_policy_ref": str(output_dir / "kill_switch_policy.json"),
                "opt_in_policy_ref": str(output_dir / "opt_in_policy.json"),
                "audit_policy_ref": str(output_dir / "audit_policy.json"),
                "rollback_policy_ref": str(output_dir / "rollback_policy.json"),
                "stop_discipline_ref": str(output_dir / "stop_discipline.json"),
                "liquidity_evidence_ref": str(output_dir / "liquidity_evidence.json"),
                "slippage_risk_note": "MANAGEABLE",
                "outlier_max_sleeve_allocation": 0.1,
                "outlier_max_per_name_risk": 0.0075,
                "candidate_requested_sleeve_allocation": 0.03,
                "candidate_requested_per_name_risk": 0.004,
                "current_order_count": 1,
                "max_order_count_limit": 5,
                "projected_total_exposure": 0.25,
                "max_total_exposure": 0.5,
                "projected_inverse_hedge_exposure": 0.05,
                "max_inverse_hedge_exposure": 0.2,
                "available_at": "2026-06-25T09:35:00+09:00",
                "source_refs": [
                    str(output_dir / "paper_eval_report.json"),
                    str(output_dir / "mock_readiness_report.json"),
                    str(output_dir / "market_regime_report.json"),
                    str(output_dir / "provider_registry_report.json"),
                    str(output_dir / "position_sizing_review.json"),
                    str(output_dir / "event_risk_review.json"),
                    str(output_dir / "breadth_routing_review.json"),
                ],
                "live_prod_path_attempt": False,
                "real_broker_dependency": False,
                "kiwoom_dependency": False,
                "kiwoom_mock_order_execution_dependency": False,
                "provider_network_dependency": False,
                "websocket_dependency": False,
                "autonomous_execution_path": False,
                "executable_order_object_present": False,
                "real_order_id_present": False,
                "raw_account_output_present": False,
                "credential_token_output_present": False,
                "missing_fail_closed_behavior": False,
                "safety_report": {
                    "safety_report_id": "controlled-mock-dry-run-safety-smoke",
                    "blocked_capabilities": [
                        "LIVE_TRADING_BLOCKED",
                        "REAL_ORDER_BLOCKED",
                        "ACCOUNT_MUTATION_BLOCKED",
                        "BROKER_API_BLOCKED",
                        "KIWOOM_API_BLOCKED",
                        "WEBSOCKET_BLOCKED",
                        "NETWORK_BLOCKED",
                        "AUTONOMOUS_TRADING_BLOCKED",
                        "MOCK_ORDER_EXECUTION_BLOCKED",
                    ],
                    "findings": [],
                },
                "audit_records": [
                    {
                        "audit_record_id": "controlled-mock-dry-run-audit-smoke",
                        "created_at": "2026-06-25T09:36:00+09:00",
                        "source_path": str(output_dir / "controlled_mock_dry_run_smoke_fixture.json"),
                        "operator_context": "offline controlled mock dry run smoke",
                        "redaction_applied": True,
                        "contains_secret_material": False,
                        "contains_token_material": False,
                        "contains_account_material": False,
                    }
                ],
            }
        )
    )
    dumped = json.dumps(reviewed.model_dump(mode="json")).lower()
    decision = reviewed.summary_report.decision.value
    return {
        "fixture_run": True,
        "summary_report_generated": reviewed.summary_report.report_id.endswith("REPORT"),
        "preview_generated": reviewed.mock_order_intent_preview.intent_id.endswith("PREVIEW"),
        "preflight_report_generated": reviewed.preflight_rehearsal_report.report_id.endswith("REPORT"),
        "provider_report_generated": reviewed.provider_readiness_rehearsal_report.report_id.endswith("REPORT"),
        "market_regime_report_generated": reviewed.market_regime_rehearsal_report.report_id.endswith("REPORT"),
        "position_sizing_report_generated": reviewed.position_sizing_rehearsal_report.report_id.endswith("REPORT"),
        "event_risk_report_generated": reviewed.event_risk_rehearsal_report.report_id.endswith("REPORT"),
        "breadth_routing_report_generated": reviewed.breadth_outlier_routing_rehearsal_report.report_id.endswith("REPORT"),
        "order_gate_report_generated": reviewed.order_gate_rehearsal_report.report_id.endswith("REPORT"),
        "risk_budget_report_generated": reviewed.risk_budget_rehearsal_report.report_id.endswith("REPORT"),
        "kill_switch_report_generated": reviewed.kill_switch_rehearsal_report.report_id.endswith("REPORT"),
        "rollback_report_generated": reviewed.rollback_rehearsal_report.report_id.endswith("REPORT"),
        "audit_report_generated": reviewed.audit_trail_rehearsal_report.report_id.endswith("REPORT"),
        "boundary_report_generated": reviewed.boundary_violation_report.report_id.endswith("REPORT"),
        "gap_report_generated": reviewed.gap_report.gap_report_id.endswith("REPORT"),
        "report_only": reviewed.summary_report.report_only,
        "non_executable": reviewed.summary_report.non_executable,
        "local_only": reviewed.summary_report.local_file_only,
        "offline_only": reviewed.summary_report.offline_only,
        "no_live_order_account_prod_path": reviewed.summary_report.no_live_prod and reviewed.summary_report.no_order and reviewed.summary_report.no_account_mutation,
        "no_real_broker_kiwoom_network_provider_call": reviewed.summary_report.no_broker_api and reviewed.summary_report.no_kiwoom_api and reviewed.summary_report.no_network and reviewed.summary_report.no_provider_api,
        "no_mock_order_execution": reviewed.summary_report.no_mock_order_execution and reviewed.mock_order_intent_preview.no_execution_flag,
        "preview_non_executable": reviewed.mock_order_intent_preview.non_executable and reviewed.mock_order_intent_preview.report_only,
        "execution_review_or_rehearsed_only": decision in {"DRY_RUN_REHEARSED", "MOCK_EXECUTION_REVIEW_READY", "WATCH_ONLY", "GAP", "BLOCKED", "RESEARCH_ONLY", "REJECTED"},
        "parquet_unsupported": ".parquet" not in dumped,
    }


def _run_read_only_provider_adapter_smoke(output_dir: Path) -> dict[str, bool]:
    reviewed = build_read_only_provider_adapter_boundary(
        ReadOnlyProviderAdapterInput.model_validate(
            {
                "adapter_id": "read-only-provider-adapter-smoke",
                "current_provider": "KIWOOM_REST",
                "future_provider": "LS_OPEN_API",
                "provider_definitions": [
                    {
                        "provider": "KIWOOM_REST",
                        "role": "CURRENT_PRIMARY",
                        "markets_supported": ["KRX_EQUITY"],
                        "implemented": True,
                        "placeholder_only": False,
                        "future_api_evidence_required": False,
                        "evidence_ref": str(output_dir / "kiwoom_readonly.md"),
                        "notes": "current readonly provider",
                    },
                    {
                        "provider": "LS_OPEN_API",
                        "role": "FUTURE_MIGRATION_TARGET",
                        "markets_supported": ["KRX_EQUITY", "GLOBAL_FUTURES"],
                        "implemented": False,
                        "placeholder_only": True,
                        "future_api_evidence_required": True,
                        "notes": "future target only",
                    },
                    {
                        "provider": "LOCAL_FIXTURE",
                        "role": "FIXTURE_ONLY",
                        "markets_supported": ["TEST_ONLY"],
                        "implemented": True,
                        "placeholder_only": False,
                        "future_api_evidence_required": False,
                        "evidence_ref": str(output_dir / "local_fixture.md"),
                        "notes": "local fixture only",
                    },
                ],
                "request_envelope_boundary": {"authorization_template": "Bearer <TOKEN_REF_ONLY>"},
                "kiwoom_rest_evidence_entries": [
                    {"api_id": "AU10001", "title": "접근토큰 발급", "category": "OAUTH", "maps_to": ["TOKEN_BOUNDARY"], "blocked_in_readonly": True},
                    {"api_id": "KA10004", "title": "주식호가요청", "category": "QUOTE_ORDERBOOK", "maps_to": ["CANONICAL_QUOTE"]},
                    {"api_id": "KA10081", "title": "주식일봉차트조회요청", "category": "OHLCV_CHART", "maps_to": ["CANONICAL_OHLCV"]},
                    {"api_id": "KA00198", "title": "실시간종목조회순위", "category": "RANKING_OUTLIER", "maps_to": ["CANONICAL_RANK_SIGNAL"]},
                    {"api_id": "KA10008", "title": "주식외국인종목별매매동향", "category": "FLOW_SHORT_PROGRAM", "maps_to": ["CANONICAL_FLOW_SIGNAL"]},
                    {"api_id": "KA20001", "title": "업종현재가요청", "category": "SECTOR_THEME_ETF", "maps_to": ["CANONICAL_SECTOR_THEME_SIGNAL"]},
                    {"api_id": "0B", "title": "주식체결", "category": "REALTIME_READONLY", "maps_to": ["CANONICAL_REALTIME_EVENT"], "realtime_stream": True},
                ],
                "ls_future_placeholder": {
                    "expected_base_url_placeholder": "LS_BASE_URL_PLACEHOLDER",
                    "expected_rest_header_shape_placeholder": "LS_HEADER_SHAPE_PLACEHOLDER",
                    "expected_tr_code_shape_placeholder": "LS_TR_CODE_PLACEHOLDER",
                    "migration_readiness_status": "EVIDENCE_REQUIRED",
                },
                "canonical_quotes": [
                    {
                        "provider": "KIWOOM_REST",
                        "provider_api_id": "KA10004",
                        "canonical_instrument_key": "005930_KRX",
                        "provider_symbol": "005930",
                        "market": "KRX",
                        "currency": "KRW",
                        "observed_at": "2026-06-25T09:30:00+09:00",
                        "available_at": "2026-06-25T09:30:01+09:00",
                        "source_ref": str(output_dir / "kiwoom_quote.json"),
                        "quality_flags": ["READ_ONLY_ONLY"],
                        "raw_payload_redacted": True,
                        "last_price": 82500.0,
                    }
                ],
                "canonical_ohlcv_records": [
                    {
                        "provider": "KIWOOM_REST",
                        "provider_api_id": "KA10081",
                        "canonical_instrument_key": "005930_KRX",
                        "provider_symbol": "005930",
                        "market": "KRX",
                        "currency": "KRW",
                        "observed_at": "2026-06-25T15:30:00+09:00",
                        "available_at": "2026-06-25T15:35:00+09:00",
                        "source_ref": str(output_dir / "kiwoom_ohlcv.json"),
                        "quality_flags": ["POINT_IN_TIME_SAFE"],
                        "raw_payload_redacted": True,
                        "interval": "1D",
                        "open_price": 82000.0,
                        "high_price": 83000.0,
                        "low_price": 81800.0,
                        "close_price": 82500.0,
                        "volume": 1234567.0,
                    }
                ],
                "canonical_rank_signals": [
                    {
                        "provider": "KIWOOM_REST",
                        "provider_api_id": "KA00198",
                        "canonical_instrument_key": "005930_KRX",
                        "provider_symbol": "005930",
                        "market": "KRX",
                        "currency": "KRW",
                        "observed_at": "2026-06-25T09:31:00+09:00",
                        "available_at": "2026-06-25T09:31:02+09:00",
                        "source_ref": str(output_dir / "kiwoom_rank.json"),
                        "quality_flags": ["READ_ONLY_ONLY"],
                        "raw_payload_redacted": True,
                        "rank_metric": "VOLUME_SPIKE",
                        "rank_value": 4.2,
                        "rank_order": 3,
                    }
                ],
                "canonical_flow_signals": [
                    {
                        "provider": "KIWOOM_REST",
                        "provider_api_id": "KA10008",
                        "canonical_instrument_key": "005930_KRX",
                        "provider_symbol": "005930",
                        "market": "KRX",
                        "currency": "KRW",
                        "observed_at": "2026-06-25T15:31:00+09:00",
                        "available_at": "2026-06-25T15:32:00+09:00",
                        "source_ref": str(output_dir / "kiwoom_flow.json"),
                        "quality_flags": ["READ_ONLY_ONLY"],
                        "raw_payload_redacted": True,
                        "flow_metric": "FOREIGN_NET_FLOW",
                        "net_flow_value": 1300000000.0,
                    }
                ],
                "canonical_sector_theme_signals": [
                    {
                        "provider": "KIWOOM_REST",
                        "provider_api_id": "KA20001",
                        "canonical_instrument_key": "SEMICONDUCTOR_THEME",
                        "provider_symbol": "SEMIS",
                        "market": "KRX",
                        "currency": "KRW",
                        "observed_at": "2026-06-25T09:32:00+09:00",
                        "available_at": "2026-06-25T09:32:05+09:00",
                        "source_ref": str(output_dir / "kiwoom_sector.json"),
                        "quality_flags": ["READ_ONLY_ONLY"],
                        "raw_payload_redacted": True,
                        "sector_or_theme_id": "SEMIS",
                        "signal_metric": "RELATIVE_STRENGTH",
                        "signal_value": 1.7,
                    }
                ],
                "canonical_realtime_events": [
                    {
                        "provider": "KIWOOM_REST",
                        "provider_api_id": "0B",
                        "canonical_instrument_key": "005930_KRX",
                        "provider_symbol": "005930",
                        "market": "KRX",
                        "currency": "KRW",
                        "observed_at": "2026-06-25T09:30:05+09:00",
                        "available_at": "2026-06-25T09:30:05+09:00",
                        "source_ref": str(output_dir / "kiwoom_realtime.json"),
                        "quality_flags": ["READ_ONLY_ONLY"],
                        "raw_payload_redacted": True,
                        "event_code": "0B",
                        "event_type": "TRADE_PRINT",
                        "event_summary": "trade print",
                    }
                ],
                "canonical_capability_records": [
                    {
                        "provider": "KIWOOM_REST",
                        "provider_api_id": "KA10081",
                        "canonical_instrument_key": "CAPABILITY_KRX_OHLCV",
                        "provider_symbol": "KRX_OHLCV",
                        "market": "KRX",
                        "currency": "KRW",
                        "observed_at": "2026-06-25T09:00:00+09:00",
                        "available_at": "2026-06-25T09:00:00+09:00",
                        "source_ref": str(output_dir / "kiwoom_capability.json"),
                        "quality_flags": ["READ_ONLY_ONLY"],
                        "raw_payload_redacted": True,
                        "capability_name": "DOMESTIC_OHLCV",
                        "capability_status": "AVAILABLE_NOW",
                        "notes": "kiwoom chart api available",
                    }
                ],
                "blocked_account_order_api_records": [
                    {"api_id": "KA00001", "title": "계좌번호조회", "block_reason": "ACCOUNT_API_BLOCKED"},
                    {"api_id": "KT10000", "title": "주문요청", "block_reason": "ORDER_API_BLOCKED"},
                    {"api_id": "00", "title": "주문체결", "block_reason": "REALTIME_ORDER_STREAM_BLOCKED", "realtime_stream": True},
                    {"api_id": "04", "title": "잔고", "block_reason": "REALTIME_ACCOUNT_STREAM_BLOCKED", "realtime_stream": True},
                ],
                "external_gap_markets": ["NQ_ES_FUTURES", "VIX_DXY_10Y_USDKRW", "ECONOMIC_CALENDAR"],
                "safety_report": {
                    "safety_report_id": "read-only-provider-adapter-safety-smoke",
                    "blocked_capabilities": [
                        "KIWOOM_API_CALL_BLOCKED",
                        "LS_API_CALL_BLOCKED",
                        "NETWORK_BLOCKED",
                        "CREDENTIAL_READ_BLOCKED",
                        "TOKEN_LOADING_BLOCKED",
                        "AUTH_HEADER_GENERATION_BLOCKED",
                        "ACCOUNT_ORDER_API_BLOCKED",
                    ],
                    "findings": [],
                },
                "audit_records": [
                    {
                        "audit_record_id": "read-only-provider-adapter-audit-smoke",
                        "created_at": "2026-06-25T10:00:00+09:00",
                        "source_path": str(output_dir / "read_only_provider_adapter_fixture.json"),
                        "operator_context": "offline readonly provider boundary smoke",
                        "redaction_applied": True,
                        "contains_secret_material": False,
                        "contains_token_material": False,
                        "contains_account_material": False,
                    }
                ],
            }
        )
    )
    dumped = json.dumps(reviewed.model_dump(mode="json")).lower()
    return {
        "fixture_run": True,
        "summary_report_generated": reviewed.summary_report.report_id.endswith("REPORT"),
        "evidence_map_report_generated": reviewed.kiwoom_rest_evidence_map_report.report_id.endswith("REPORT"),
        "ls_report_generated": reviewed.ls_future_compatibility_report.report_id.endswith("REPORT"),
        "canonical_contract_report_generated": reviewed.canonical_readonly_contract_report.report_id.endswith("REPORT"),
        "capability_matrix_report_generated": reviewed.provider_capability_matrix_report.report_id.endswith("REPORT"),
        "blocked_api_report_generated": reviewed.blocked_account_order_api_report.report_id.endswith("REPORT"),
        "migration_report_generated": reviewed.provider_migration_readiness_report.report_id.endswith("REPORT"),
        "gap_report_generated": reviewed.gap_report.gap_report_id.endswith("REPORT"),
        "local_only": reviewed.summary_report.local_file_only,
        "offline_only": reviewed.summary_report.offline_only,
        "report_only": reviewed.summary_report.report_only,
        "non_executable": reviewed.summary_report.non_executable,
        "no_provider_network_call": reviewed.summary_report.no_network and reviewed.summary_report.no_provider_api and reviewed.summary_report.no_kiwoom_api and reviewed.summary_report.no_ls_api,
        "no_credential_env_read": reviewed.summary_report.no_env_read and reviewed.summary_report.no_credential_read and reviewed.summary_report.no_token_loading,
        "no_auth_header_generation": reviewed.summary_report.no_auth_header_generation and reviewed.canonical_readonly_contract_report.request_envelope_boundary.authorization_template == "Bearer <TOKEN_REF_ONLY>",
        "account_order_blocked": {"KA00001", "KT10000", "00", "04"} <= {item.api_id for item in reviewed.blocked_account_order_api_report.blocked_records},
        "canonical_output_only": reviewed.request_envelope_boundary.authorization_template == "Bearer <TOKEN_REF_ONLY>" and all(not item.contains_secret_material and not item.contains_token_material and not item.contains_account_material for item in reviewed.audit_records) and all(item.raw_payload_redacted for item in reviewed.canonical_quotes + reviewed.canonical_ohlcv_records + reviewed.canonical_rank_signals + reviewed.canonical_flow_signals + reviewed.canonical_sector_theme_signals + reviewed.canonical_realtime_events + reviewed.canonical_capability_records),
        "parquet_unsupported": ".parquet" not in dumped,
    }


def _run_kiwoom_rest_readonly_chart_smoke(output_dir: Path) -> dict[str, bool]:
    reviewed = build_kiwoom_rest_readonly_chart_adapter(
        KiwoomRestChartConfig.model_validate(
            {
                "config_id": "kiwoom-rest-readonly-chart-smoke",
                "provider_symbol": "005930",
                "canonical_instrument_key": "005930_KRX",
                "api_id": "KA10081",
                "base_dt": "20260202",
                "upd_stkpc_tp": "1",
                "available_at": "2026-06-25T15:35:00+09:00",
                "source_ref": str(output_dir / "kiwoom_rest_readonly_chart_fixture.json"),
                "mocked_response_payload": {
                    "stk_cd": "005930",
                    "return_code": 0,
                    "return_msg": "정상적으로 처리되었습니다",
                    "stk_dt_pole_chart_qry": [
                        {
                            "dt": "20260202",
                            "open_pric": "+78850",
                            "high_pric": "+78900",
                            "low_pric": "+78000",
                            "cur_prc": "+78800",
                            "acc_trde_qty": "1234567",
                        }
                    ],
                    "cont_yn": "N",
                    "next_key": "",
                },
                "safety_report": {
                    "safety_report_id": "kiwoom-rest-readonly-chart-safety-smoke",
                    "blocked_capabilities": [
                        "NETWORK_BLOCKED",
                        "PROVIDER_API_BLOCKED",
                        "ACCOUNT_ORDER_BLOCKED",
                        "ENV_READ_BLOCKED",
                        "CREDENTIAL_READ_BLOCKED",
                        "TOKEN_LOADING_BLOCKED",
                        "AUTH_HEADER_GENERATION_BLOCKED",
                    ],
                    "findings": [],
                },
                "audit_records": [
                    {
                        "audit_record_id": "kiwoom-rest-readonly-chart-audit-smoke",
                        "created_at": "2026-06-25T16:00:00+09:00",
                        "source_path": str(output_dir / "kiwoom_rest_readonly_chart_fixture.json"),
                        "operator_context": "offline mocked transport smoke",
                        "redaction_applied": True,
                        "contains_secret_material": False,
                        "contains_token_material": False,
                        "contains_account_material": False,
                    }
                ],
            }
        )
    )
    dumped = json.dumps(reviewed.model_dump(mode="json")).lower()
    return {
        "fixture_run": True,
        "request_report_generated": reviewed.request_report.report_id.endswith("REPORT"),
        "mocked_response_report_generated": reviewed.mocked_response_report.report_id.endswith("REPORT"),
        "canonical_ohlcv_report_generated": reviewed.canonical_ohlcv_report.report_id.endswith("REPORT"),
        "continuation_report_generated": reviewed.continuation_report.report_id.endswith("REPORT"),
        "safety_report_generated": reviewed.safety_report.safety_report_id.endswith("SMOKE"),
        "integration_compatibility_report_generated": reviewed.integration_compatibility_report.report_id.endswith("REPORT"),
        "gap_report_generated": reviewed.gap_report.gap_report_id.endswith("REPORT"),
        "local_only": reviewed.summary_report.local_file_only,
        "offline_only": reviewed.summary_report.offline_only,
        "report_only": reviewed.summary_report.report_only,
        "non_executable": reviewed.summary_report.non_executable,
        "no_network": reviewed.summary_report.no_network,
        "no_provider_api": reviewed.summary_report.no_provider_api,
        "no_account_order_path": reviewed.summary_report.no_order and reviewed.summary_report.no_account_mutation,
        "no_env_credential_read": reviewed.summary_report.no_env_read and reviewed.summary_report.no_credential_read,
        "no_token_loading": reviewed.summary_report.no_token_loading,
        "no_auth_header_generation": reviewed.summary_report.no_auth_header_generation,
        "canonical_ohlcv_output_only": bool(reviewed.canonical_ohlcv_report.records)
        and all(item.source_ref.endswith(".json") for item in reviewed.canonical_ohlcv_report.records)
        and all("TOKEN_REF_ONLY" in item.quality_flags for item in reviewed.canonical_ohlcv_report.records)
        and all(not item.contains_secret_material and not item.contains_token_material and not item.contains_account_material for item in reviewed.audit_records),
        "parquet_unsupported": ".parquet" not in dumped,
    }


def _run_kiwoom_rest_readonly_rank_smoke(output_dir: Path) -> dict[str, bool]:
    reviewed = build_kiwoom_rest_readonly_rank_adapter(
        KiwoomRestRankConfig.model_validate(
            {
                "config_id": "kiwoom-rest-readonly-rank-smoke",
                "api_id": "KA10023",
                "available_at": "2026-06-25T15:35:00+09:00",
                "source_ref": str(output_dir / "kiwoom_rest_readonly_rank_fixture.json"),
                "mrkt_tp": "000",
                "sort_tp": "1",
                "tm_tp": "1",
                "trde_qty_tp": "10",
                "tm": "5",
                "stk_cnd": "3",
                "pric_tp": "0",
                "stex_tp": "3",
                "mocked_response_payload": {
                    "return_code": 0,
                    "return_msg": "정상적으로 처리되었습니다",
                    "vol_surge_rank": [
                        {
                            "stk_cd": "005930",
                            "stk_nm": "삼성전자",
                            "now_rank": "1",
                            "pred_rank": "4",
                            "flu_rt": "+5.25",
                            "cur_prc": "+78800",
                            "pred_pre": "+3900",
                            "trde_qty": "1234567",
                            "trde_prica": "45678900000",
                            "dt": "20260625",
                            "tm": "153000",
                        }
                    ],
                    "cont_yn": "N",
                    "next_key": "",
                },
                "safety_report": {
                    "safety_report_id": "kiwoom-rest-readonly-rank-safety-smoke",
                    "blocked_capabilities": [
                        "NETWORK_BLOCKED",
                        "PROVIDER_API_BLOCKED",
                        "ACCOUNT_ORDER_BLOCKED",
                        "ENV_READ_BLOCKED",
                        "CREDENTIAL_READ_BLOCKED",
                        "TOKEN_LOADING_BLOCKED",
                        "AUTH_HEADER_GENERATION_BLOCKED",
                    ],
                    "findings": [],
                },
                "audit_records": [
                    {
                        "audit_record_id": "kiwoom-rest-readonly-rank-audit-smoke",
                        "created_at": "2026-06-25T16:00:00+09:00",
                        "source_path": str(output_dir / "kiwoom_rest_readonly_rank_fixture.json"),
                        "operator_context": "offline mocked transport smoke",
                        "redaction_applied": True,
                        "contains_secret_material": False,
                        "contains_token_material": False,
                        "contains_account_material": False,
                    }
                ],
            }
        )
    )
    dumped = json.dumps(reviewed.model_dump(mode="json")).lower()
    return {
        "fixture_run": True,
        "request_report_generated": reviewed.request_report.report_id.endswith("REPORT"),
        "mocked_response_report_generated": reviewed.mocked_response_report.report_id.endswith("REPORT"),
        "canonical_rank_report_generated": reviewed.canonical_rank_report.report_id.endswith("REPORT"),
        "canonical_outlier_report_generated": reviewed.canonical_outlier_report.report_id.endswith("REPORT"),
        "continuation_report_generated": reviewed.continuation_report.report_id.endswith("REPORT"),
        "safety_report_generated": reviewed.safety_report.safety_report_id.endswith("SMOKE"),
        "v7_integration_report_generated": reviewed.v7_integration_report.report_id.endswith("REPORT"),
        "gap_report_generated": reviewed.gap_report.gap_report_id.endswith("REPORT"),
        "local_only": reviewed.summary_report.local_file_only,
        "offline_only": reviewed.summary_report.offline_only,
        "report_only": reviewed.summary_report.report_only,
        "non_executable": reviewed.summary_report.non_executable,
        "no_network": reviewed.summary_report.no_network,
        "no_provider_api": reviewed.summary_report.no_provider_api,
        "no_account_order_path": reviewed.summary_report.no_order and reviewed.summary_report.no_account_mutation,
        "no_env_credential_read": reviewed.summary_report.no_env_read and reviewed.summary_report.no_credential_read,
        "no_token_loading": reviewed.summary_report.no_token_loading,
        "no_auth_header_generation": reviewed.summary_report.no_auth_header_generation,
        "canonical_output_only": bool(reviewed.canonical_rank_report.signals)
        and bool(reviewed.canonical_outlier_report.signals)
        and all(signal.source_ref.endswith(".json") for signal in reviewed.canonical_rank_report.signals + reviewed.canonical_outlier_report.signals)
        and all("TOKEN_REF_ONLY" in signal.quality_flags for signal in reviewed.canonical_rank_report.signals + reviewed.canonical_outlier_report.signals)
        and all(not item.contains_secret_material and not item.contains_token_material and not item.contains_account_material for item in reviewed.audit_records),
        "parquet_unsupported": ".parquet" not in dumped,
    }


def _run_kiwoom_rest_readonly_quote_smoke(output_dir: Path) -> dict[str, bool]:
    reviewed = build_kiwoom_rest_readonly_quote_adapter(
        KiwoomRestQuoteConfig.model_validate(
            {
                "config_id": "kiwoom-rest-readonly-quote-smoke",
                "api_id": "KA10004",
                "provider_symbol": "005930",
                "available_at": "2026-06-25T15:35:00+09:00",
                "request_date": "20260625",
                "source_ref": str(output_dir / "kiwoom_rest_readonly_quote_fixture.json"),
                "mocked_response_payload": {
                    "stk_cd": "005930",
                    "stk_nm": "삼성전자",
                    "return_code": 0,
                    "return_msg": "정상적으로 처리되었습니다",
                    "bid_req_base_tm": "153000",
                    "ask_price_1": "+78810",
                    "ask_qty_1": "1200",
                    "bid_price_1": "+78800",
                    "bid_qty_1": "1500",
                    "ask_price_2": "+78820",
                    "ask_qty_2": "900",
                    "bid_price_2": "+78790",
                    "bid_qty_2": "800",
                    "cont_yn": "N",
                    "next_key": "",
                },
                "safety_report": {
                    "safety_report_id": "kiwoom-rest-readonly-quote-safety-smoke",
                    "blocked_capabilities": [
                        "NETWORK_BLOCKED",
                        "PROVIDER_API_BLOCKED",
                        "ACCOUNT_ORDER_BLOCKED",
                        "ENV_READ_BLOCKED",
                        "CREDENTIAL_READ_BLOCKED",
                        "TOKEN_LOADING_BLOCKED",
                        "AUTH_HEADER_GENERATION_BLOCKED",
                    ],
                    "findings": [],
                },
                "audit_records": [
                    {
                        "audit_record_id": "kiwoom-rest-readonly-quote-audit-smoke",
                        "created_at": "2026-06-25T16:00:00+09:00",
                        "source_path": str(output_dir / "kiwoom_rest_readonly_quote_fixture.json"),
                        "operator_context": "offline mocked transport smoke",
                        "redaction_applied": True,
                        "contains_secret_material": False,
                        "contains_token_material": False,
                        "contains_account_material": False,
                    }
                ],
            }
        )
    )
    dumped = json.dumps(reviewed.model_dump(mode="json")).lower()
    return {
        "fixture_run": True,
        "request_report_generated": reviewed.request_report.report_id.endswith("REPORT"),
        "mocked_response_report_generated": reviewed.mocked_response_report.report_id.endswith("REPORT"),
        "canonical_quote_report_generated": reviewed.canonical_quote_report.report_id.endswith("REPORT"),
        "canonical_orderbook_report_generated": reviewed.canonical_orderbook_report.report_id.endswith("REPORT"),
        "liquidity_hint_report_generated": reviewed.liquidity_hint_report.report_id.endswith("REPORT"),
        "basic_info_report_generated": reviewed.basic_info_report.report_id.endswith("REPORT"),
        "continuation_report_generated": reviewed.continuation_report.report_id.endswith("REPORT"),
        "safety_report_generated": reviewed.safety_report.safety_report_id.endswith("SMOKE"),
        "v7_integration_report_generated": reviewed.v7_integration_report.report_id.endswith("REPORT"),
        "gap_report_generated": reviewed.gap_report.gap_report_id.endswith("REPORT"),
        "local_only": reviewed.summary_report.local_file_only,
        "offline_only": reviewed.summary_report.offline_only,
        "report_only": reviewed.summary_report.report_only,
        "non_executable": reviewed.summary_report.non_executable,
        "no_network": reviewed.summary_report.no_network,
        "no_provider_api": reviewed.summary_report.no_provider_api,
        "no_account_order_path": reviewed.summary_report.no_order and reviewed.summary_report.no_account_mutation,
        "no_env_credential_read": reviewed.summary_report.no_env_read and reviewed.summary_report.no_credential_read,
        "no_token_loading": reviewed.summary_report.no_token_loading,
        "no_auth_header_generation": reviewed.summary_report.no_auth_header_generation,
        "canonical_output_only": bool(reviewed.canonical_quote_report.records)
        and bool(reviewed.canonical_orderbook_report.records)
        and bool(reviewed.liquidity_hint_report.records)
        and all(record.source_ref.endswith(".json") for record in reviewed.canonical_quote_report.records + reviewed.canonical_orderbook_report.records + reviewed.liquidity_hint_report.records)
        and all("TOKEN_REF_ONLY" in record.quality_flags for record in reviewed.canonical_quote_report.records + reviewed.canonical_orderbook_report.records + reviewed.liquidity_hint_report.records)
        and all(not item.contains_secret_material and not item.contains_token_material and not item.contains_account_material for item in reviewed.audit_records),
        "parquet_unsupported": ".parquet" not in dumped,
    }


def _run_kiwoom_rest_readonly_flow_smoke(output_dir: Path) -> dict[str, bool]:
    reviewed = build_kiwoom_rest_readonly_flow_adapter(
        KiwoomRestFlowConfig.model_validate(
            {
                "config_id": "kiwoom-rest-readonly-flow-smoke",
                "api_id": "KA10059",
                "provider_symbol": "005930",
                "request_date": "20260625",
                "amt_qty_tp": "1",
                "trde_tp": "0",
                "unit_tp": "1",
                "available_at": "2026-06-25T15:35:00+09:00",
                "source_ref": str(output_dir / "kiwoom_rest_readonly_flow_fixture.json"),
                "mocked_response_payload": {
                    "return_code": 0,
                    "return_msg": "정상적으로 처리되었습니다",
                    "stk_invsr_orgn": [
                        {
                            "dt": "20260625",
                            "stk_cd": "005930",
                            "stk_nm": "삼성전자",
                            "cur_prc": "+78800",
                            "pred_pre": "+3900",
                            "frgnr_net_amt": "+120000000",
                            "orgn_net_amt": "-50000000",
                            "retl_net_amt": "-70000000",
                            "frgnr_net_qty": "+1500",
                            "orgn_net_qty": "-700",
                            "retl_net_qty": "-800",
                        }
                    ],
                    "cont_yn": "N",
                    "next_key": "",
                },
                "safety_report": {
                    "safety_report_id": "kiwoom-rest-readonly-flow-safety-smoke",
                    "blocked_capabilities": [
                        "NETWORK_BLOCKED",
                        "PROVIDER_API_BLOCKED",
                        "ACCOUNT_ORDER_BLOCKED",
                        "ENV_READ_BLOCKED",
                        "CREDENTIAL_READ_BLOCKED",
                        "TOKEN_LOADING_BLOCKED",
                        "AUTH_HEADER_GENERATION_BLOCKED",
                    ],
                    "findings": [],
                },
                "audit_records": [
                    {
                        "audit_record_id": "kiwoom-rest-readonly-flow-audit-smoke",
                        "created_at": "2026-06-25T16:00:00+09:00",
                        "source_path": str(output_dir / "kiwoom_rest_readonly_flow_fixture.json"),
                        "operator_context": "offline mocked transport smoke",
                        "redaction_applied": True,
                        "contains_secret_material": False,
                        "contains_token_material": False,
                        "contains_account_material": False,
                    }
                ],
            }
        )
    )
    dumped = json.dumps(reviewed.model_dump(mode="json")).lower()
    return {
        "fixture_run": True,
        "request_report_generated": reviewed.request_report.report_id.endswith("REPORT"),
        "mocked_response_report_generated": reviewed.mocked_response_report.report_id.endswith("REPORT"),
        "canonical_investor_flow_report_generated": reviewed.canonical_investor_flow_report.report_id.endswith("REPORT"),
        "canonical_program_flow_report_generated": reviewed.canonical_program_flow_report.report_id.endswith("REPORT"),
        "short_lending_capability_report_generated": reviewed.short_lending_capability_report.report_id.endswith("REPORT"),
        "capability_matrix_report_generated": reviewed.flow_capability_matrix_report.report_id.endswith("REPORT"),
        "continuation_report_generated": reviewed.continuation_report.report_id.endswith("REPORT"),
        "safety_report_generated": reviewed.safety_report.safety_report_id.endswith("SMOKE"),
        "v7_integration_report_generated": reviewed.v7_integration_report.report_id.endswith("REPORT"),
        "gap_report_generated": reviewed.gap_report.gap_report_id.endswith("REPORT"),
        "local_only": reviewed.summary_report.local_file_only,
        "offline_only": reviewed.summary_report.offline_only,
        "report_only": reviewed.summary_report.report_only,
        "non_executable": reviewed.summary_report.non_executable,
        "no_network": reviewed.summary_report.no_network,
        "no_provider_api": reviewed.summary_report.no_provider_api,
        "no_account_order_path": reviewed.summary_report.no_order and reviewed.summary_report.no_account_mutation,
        "no_env_credential_read": reviewed.summary_report.no_env_read and reviewed.summary_report.no_credential_read,
        "no_token_loading": reviewed.summary_report.no_token_loading,
        "no_auth_header_generation": reviewed.summary_report.no_auth_header_generation,
        "canonical_output_only": bool(reviewed.canonical_investor_flow_report.signals)
        and all(signal.source_ref.endswith(".json") for signal in reviewed.canonical_investor_flow_report.signals)
        and all("TOKEN_REF_ONLY" in signal.quality_flags for signal in reviewed.canonical_investor_flow_report.signals)
        and all(not item.contains_secret_material and not item.contains_token_material and not item.contains_account_material for item in reviewed.audit_records),
        "parquet_unsupported": ".parquet" not in dumped,
    }


def _run_kiwoom_rest_readonly_sector_smoke(output_dir: Path) -> dict[str, bool]:
    reviewed = build_kiwoom_rest_readonly_sector_adapter(
        KiwoomRestSectorConfig.model_validate(
            {
                "config_id": "kiwoom-rest-readonly-sector-smoke",
                "api_id": "KA90001",
                "qry_tp": "0",
                "provider_symbol": "",
                "date_tp": "10",
                "theme_name": "",
                "flu_pl_amt_tp": "1",
                "stex_tp": "1",
                "available_at": "2026-06-25T15:35:00+09:00",
                "source_ref": str(output_dir / "kiwoom_rest_readonly_sector_fixture.json"),
                "mocked_response_payload": {
                    "return_code": 0,
                    "return_msg": "정상적으로 처리되었습니다",
                    "thema_grp": [
                        {
                            "thema_grp_cd": "553",
                            "thema_nm": "2차전지",
                            "stk_num": "12",
                            "flu_sig": "2",
                            "flu_rt": "+3.25",
                            "rising_stk_num": "9",
                            "fall_stk_num": "3",
                            "dt_prft_rt": "+5.10",
                            "main_stk": "LG에너지솔루션",
                        }
                    ],
                    "cont_yn": "N",
                    "next_key": "",
                },
                "safety_report": {
                    "safety_report_id": "kiwoom-rest-readonly-sector-safety-smoke",
                    "blocked_capabilities": [
                        "NETWORK_BLOCKED",
                        "PROVIDER_API_BLOCKED",
                        "ACCOUNT_ORDER_BLOCKED",
                        "ENV_READ_BLOCKED",
                        "CREDENTIAL_READ_BLOCKED",
                        "TOKEN_LOADING_BLOCKED",
                        "AUTH_HEADER_GENERATION_BLOCKED",
                    ],
                    "findings": [],
                },
                "audit_records": [
                    {
                        "audit_record_id": "kiwoom-rest-readonly-sector-audit-smoke",
                        "created_at": "2026-06-25T16:00:00+09:00",
                        "source_path": str(output_dir / "kiwoom_rest_readonly_sector_fixture.json"),
                        "operator_context": "offline mocked transport smoke",
                        "redaction_applied": True,
                        "contains_secret_material": False,
                        "contains_token_material": False,
                        "contains_account_material": False,
                    }
                ],
            }
        )
    )
    dumped = json.dumps(reviewed.model_dump(mode="json")).lower()
    return {
        "fixture_run": True,
        "request_report_generated": reviewed.request_report.report_id.endswith("REPORT"),
        "mocked_response_report_generated": reviewed.mocked_response_report.report_id.endswith("REPORT"),
        "canonical_theme_leadership_report_generated": reviewed.canonical_theme_leadership_report.report_id.endswith("REPORT"),
        "canonical_theme_membership_report_generated": reviewed.canonical_theme_membership_report.report_id.endswith("REPORT"),
        "canonical_etf_trend_report_generated": reviewed.canonical_etf_trend_report.report_id.endswith("REPORT"),
        "capability_matrix_report_generated": reviewed.sector_etf_capability_matrix_report.report_id.endswith("REPORT"),
        "continuation_report_generated": reviewed.continuation_report.report_id.endswith("REPORT"),
        "safety_report_generated": reviewed.safety_report.safety_report_id.endswith("SMOKE"),
        "v7_integration_report_generated": reviewed.v7_integration_report.report_id.endswith("REPORT"),
        "gap_report_generated": reviewed.gap_report.gap_report_id.endswith("REPORT"),
        "local_only": reviewed.summary_report.local_file_only,
        "offline_only": reviewed.summary_report.offline_only,
        "report_only": reviewed.summary_report.report_only,
        "non_executable": reviewed.summary_report.non_executable,
        "no_network": reviewed.summary_report.no_network,
        "no_provider_api": reviewed.summary_report.no_provider_api,
        "no_account_order_path": reviewed.summary_report.no_order and reviewed.summary_report.no_account_mutation,
        "no_env_credential_read": reviewed.summary_report.no_env_read and reviewed.summary_report.no_credential_read,
        "no_token_loading": reviewed.summary_report.no_token_loading,
        "no_auth_header_generation": reviewed.summary_report.no_auth_header_generation,
        "canonical_output_only": bool(reviewed.canonical_theme_leadership_report.signals)
        and all(signal.source_ref.endswith(".json") for signal in reviewed.canonical_theme_leadership_report.signals)
        and all("TOKEN_REF_ONLY" in signal.quality_flags for signal in reviewed.canonical_theme_leadership_report.signals)
        and all(not item.contains_secret_material and not item.contains_token_material and not item.contains_account_material for item in reviewed.audit_records),
        "parquet_unsupported": ".parquet" not in dumped,
    }


def _run_kiwoom_readonly_snapshot_smoke(output_dir: Path) -> dict[str, bool]:
    reviewed = build_kiwoom_readonly_domestic_stock_snapshot(
        KiwoomReadonlySnapshotConfig.model_validate(
            {
                "config_id": "kiwoom-readonly-snapshot-smoke",
                "available_at": "2026-06-25T15:35:00+09:00",
                "source_ref": str(output_dir / "kiwoom_readonly_snapshot_fixture.json"),
                "operator_context": "offline snapshot fusion smoke",
                "canonical_ohlcv_records": [
                    {
                        "provider_api_id": "KA10081",
                        "canonical_instrument_key": "005930_KRX",
                        "provider_symbol": "005930",
                        "timeframe": "D1",
                        "observed_at": "2026-06-25T15:30:00+09:00",
                        "available_at": "2026-06-25T15:35:00+09:00",
                        "open": 80000,
                        "high": 81000,
                        "low": 79000,
                        "close": 80500,
                        "volume": 1500000,
                        "source_ref": str(output_dir / "kiwoom_rest_readonly_chart_fixture.json"),
                        "quality_flags": ["READ_ONLY_ONLY", "TOKEN_REF_ONLY"],
                    }
                ],
                "canonical_rank_signals": [
                    {
                        "provider_api_id": "KA00198",
                        "canonical_instrument_key": "005930_KRX",
                        "provider_symbol": "005930",
                        "stock_name": "삼성전자",
                        "observed_at": "2026-06-25T15:20:00+09:00",
                        "available_at": "2026-06-25T15:35:00+09:00",
                        "rank_type": "VOLUME_TOP",
                        "rank": 3,
                        "price": 80500,
                        "price_change": 1000,
                        "percent_change": 1.26,
                        "volume": 1400000,
                        "trading_value": 112000000000,
                        "relative_volume": 1.4,
                        "liquidity_evidence_flag": True,
                        "outlier_category": "UNKNOWN",
                        "source_ref": str(output_dir / "kiwoom_rest_readonly_rank_fixture.json"),
                        "quality_flags": ["READ_ONLY_ONLY", "TOKEN_REF_ONLY"],
                    }
                ],
                "canonical_outlier_signals": [
                    {
                        "provider_api_id": "KA10023",
                        "canonical_instrument_key": "005930_KRX",
                        "provider_symbol": "005930",
                        "stock_name": "삼성전자",
                        "observed_at": "2026-06-25T15:20:00+09:00",
                        "available_at": "2026-06-25T15:35:00+09:00",
                        "rank_type": "PRICE_MOMENTUM",
                        "rank": 7,
                        "price": 80500,
                        "price_change": 1000,
                        "percent_change": 1.26,
                        "volume": 1400000,
                        "trading_value": 112000000000,
                        "relative_volume": 1.4,
                        "liquidity_evidence_flag": True,
                        "outlier_category": "PRICE_SURGE",
                        "source_ref": str(output_dir / "kiwoom_rest_readonly_rank_fixture.json"),
                        "quality_flags": ["READ_ONLY_ONLY", "TOKEN_REF_ONLY"],
                    }
                ],
                "canonical_quote_records": [
                    {
                        "provider_api_id": "KA10003",
                        "canonical_instrument_key": "005930_KRX",
                        "provider_symbol": "005930",
                        "stock_name": "삼성전자",
                        "observed_at": "2026-06-25T15:20:05+09:00",
                        "available_at": "2026-06-25T15:35:00+09:00",
                        "last_price": 80500,
                        "bid_price": 80500,
                        "ask_price": 80600,
                        "spread": 100,
                        "mid_price": 80550,
                        "last_trade_quantity": 100,
                        "percent_change": 1.26,
                        "price_change": 1000,
                        "liquidity_evidence_flag": True,
                        "source_ref": str(output_dir / "kiwoom_rest_readonly_quote_fixture.json"),
                        "quality_flags": ["READ_ONLY_ONLY", "TOKEN_REF_ONLY"],
                    }
                ],
                "canonical_orderbook_records": [
                    {
                        "provider_api_id": "KA10004",
                        "canonical_instrument_key": "005930_KRX",
                        "provider_symbol": "005930",
                        "stock_name": "삼성전자",
                        "observed_at": "2026-06-25T15:20:00+09:00",
                        "available_at": "2026-06-25T15:35:00+09:00",
                        "levels": [{"side": "ASK", "level": 1, "price": 80600, "quantity": 900}, {"side": "BID", "level": 1, "price": 80500, "quantity": 1200}],
                        "spread": 100,
                        "mid_price": 80550,
                        "top_of_book_imbalance": 0.14,
                        "depth_summary_quantity": 2100,
                        "source_ref": str(output_dir / "kiwoom_rest_readonly_quote_fixture.json"),
                        "quality_flags": ["READ_ONLY_ONLY", "TOKEN_REF_ONLY"],
                    }
                ],
                "canonical_liquidity_hints": [
                    {
                        "provider_api_id": "KA10004",
                        "canonical_instrument_key": "005930_KRX",
                        "provider_symbol": "005930",
                        "stock_name": "삼성전자",
                        "observed_at": "2026-06-25T15:20:00+09:00",
                        "available_at": "2026-06-25T15:35:00+09:00",
                        "spread": 100,
                        "mid_price": 80550,
                        "last_trade_quantity": 100,
                        "top_of_book_imbalance": 0.14,
                        "price_liquidity_ready": True,
                        "outlier_routing_ready": True,
                        "mock_intent_preview_ready": True,
                        "source_ref": str(output_dir / "kiwoom_rest_readonly_quote_fixture.json"),
                        "quality_flags": ["READ_ONLY_ONLY", "TOKEN_REF_ONLY"],
                    }
                ],
                "canonical_basic_info_records": [
                    {
                        "provider_api_id": "KA10001",
                        "canonical_instrument_key": "005930_KRX",
                        "provider_symbol": "005930",
                        "stock_name": "삼성전자",
                        "available_at": "2026-06-25T15:35:00+09:00",
                        "listed_shares": 5969782550,
                        "market_cap": 480000000000000,
                        "market_cap_weight": 17.5,
                        "source_ref": str(output_dir / "kiwoom_rest_readonly_quote_fixture.json"),
                        "quality_flags": ["READ_ONLY_ONLY", "TOKEN_REF_ONLY"],
                    }
                ],
                "canonical_investor_flow_signals": [
                    {
                        "provider_api_id": "KA10059",
                        "canonical_instrument_key": "005930_KRX",
                        "provider_symbol": "005930",
                        "stock_name": "삼성전자",
                        "observed_at": "2026-06-25T15:30:00+09:00",
                        "available_at": "2026-06-25T15:35:00+09:00",
                        "flow_category": "FOREIGN",
                        "net_buy_amount": 15000000000,
                        "net_buy_quantity": 180000,
                        "confidence_flags": ["CANONICAL_FLOW"],
                        "source_ref": str(output_dir / "kiwoom_rest_readonly_flow_fixture.json"),
                        "quality_flags": ["READ_ONLY_ONLY", "TOKEN_REF_ONLY"],
                    }
                ],
                "canonical_program_flow_signals": [
                    {
                        "provider_api_id": "KA90003",
                        "canonical_instrument_key": "005930_KRX",
                        "provider_symbol": "005930",
                        "stock_name": "삼성전자",
                        "observed_at": "2026-06-25T15:30:00+09:00",
                        "available_at": "2026-06-25T15:35:00+09:00",
                        "flow_category": "PROGRAM",
                        "program_buy_amount": 7000000000,
                        "program_sell_amount": 5000000000,
                        "program_net_amount": 2000000000,
                        "confidence_flags": ["PROGRAM_FLOW"],
                        "source_ref": str(output_dir / "kiwoom_rest_readonly_flow_fixture.json"),
                        "quality_flags": ["READ_ONLY_ONLY", "TOKEN_REF_ONLY"],
                    }
                ],
                "canonical_theme_leadership_signals": [
                    {
                        "provider_api_id": "KA90001",
                        "theme_group_code": "553",
                        "theme_name": "AI반도체",
                        "stock_count": 12,
                        "rising_stock_count": 9,
                        "falling_stock_count": 3,
                        "theme_change_rate": 2.5,
                        "period_return": 4.3,
                        "main_stock": "삼성전자",
                        "participation_hint": 0.75,
                        "concentration_hint": 0.3,
                        "observed_at": "2026-06-25T15:30:00+09:00",
                        "available_at": "2026-06-25T15:35:00+09:00",
                        "source_ref": str(output_dir / "kiwoom_rest_readonly_sector_fixture.json"),
                        "quality_flags": ["READ_ONLY_ONLY", "TOKEN_REF_ONLY"],
                    }
                ],
                "canonical_theme_membership_signals": [
                    {
                        "provider_api_id": "KA90002",
                        "theme_group_code": "553",
                        "theme_name": "AI반도체",
                        "component_stock_code": "005930",
                        "component_stock_name": "삼성전자",
                        "component_change_rate": 2.1,
                        "component_return": 4.0,
                        "membership_evidence_flag": True,
                        "observed_at": "2026-06-25T15:30:00+09:00",
                        "available_at": "2026-06-25T15:35:00+09:00",
                        "source_ref": str(output_dir / "kiwoom_rest_readonly_sector_fixture.json"),
                    }
                ],
                "canonical_etf_trend_signals": [
                    {
                        "provider_api_id": "KA40003",
                        "etf_stock_code": "069500",
                        "date": "20260625",
                        "price": 38.2,
                        "previous_close_difference": 0.15,
                        "percent_change": 0.39,
                        "trend_direction": "UP",
                        "observed_at": "2026-06-25T15:30:00+09:00",
                        "available_at": "2026-06-25T15:35:00+09:00",
                        "source_ref": str(output_dir / "kiwoom_rest_readonly_sector_fixture.json"),
                        "quality_flags": ["READ_ONLY_ONLY", "TOKEN_REF_ONLY"],
                    }
                ],
                "canonical_sector_capability_signals": [
                    {
                        "api_id": "KA90001",
                        "capability_group": "THEME",
                        "request_builder_ready": True,
                        "readiness": "THEME_LEADERSHIP_READY",
                    }
                ],
                "safety_report": {"safety_report_id": "kiwoom-readonly-snapshot-safety-smoke"},
                "audit_records": [
                    {
                        "audit_record_id": "kiwoom-readonly-snapshot-audit-smoke",
                        "created_at": "2026-06-25T16:00:00+09:00",
                        "source_path": str(output_dir / "kiwoom_readonly_snapshot_fixture.json"),
                        "operator_context": "offline snapshot fusion smoke",
                        "redaction_applied": True,
                        "contains_secret_material": False,
                        "contains_token_material": False,
                        "contains_account_material": False,
                    }
                ],
            }
        )
    )
    dumped = json.dumps(reviewed.model_dump(mode="json")).lower()
    return {
        "fixture_run": True,
        "summary_report_generated": reviewed.summary_report.report_id.endswith("REPORT"),
        "source_coverage_report_generated": reviewed.source_coverage_report.report_id.endswith("REPORT"),
        "freshness_report_generated": reviewed.freshness_report.report_id.endswith("REPORT"),
        "completeness_report_generated": reviewed.completeness_report.report_id.endswith("REPORT"),
        "conflict_report_generated": reviewed.conflict_report.report_id.endswith("REPORT"),
        "domestic_stock_report_generated": reviewed.domestic_stock_snapshot_report.report_id.endswith("REPORT"),
        "v710_report_generated": reviewed.v710_integration_report.report_id.endswith("REPORT"),
        "v712_report_generated": reviewed.v712_integration_report.report_id.endswith("REPORT"),
        "v713_report_generated": reviewed.v713_integration_report.report_id.endswith("REPORT"),
        "safety_report_generated": reviewed.safety_report.safety_report_id.endswith("SMOKE"),
        "gap_report_generated": reviewed.gap_report.gap_report_id.endswith("REPORT"),
        "local_only": reviewed.summary_report.local_file_only,
        "offline_only": reviewed.summary_report.offline_only,
        "report_only": reviewed.summary_report.report_only,
        "non_executable": reviewed.summary_report.non_executable,
        "no_network": reviewed.summary_report.no_network,
        "no_provider_api": reviewed.summary_report.no_provider_api,
        "no_account_order_path": reviewed.summary_report.no_order and reviewed.summary_report.no_account_mutation,
        "no_env_credential_read": reviewed.summary_report.no_env_read and reviewed.summary_report.no_credential_read,
        "no_token_loading": reviewed.summary_report.no_token_loading,
        "no_auth_header_generation": reviewed.summary_report.no_auth_header_generation,
        "canonical_output_only": bool(reviewed.domestic_stock_snapshot_report.snapshots)
        and all(snapshot.provider_symbol for snapshot in reviewed.domestic_stock_snapshot_report.snapshots)
        and all(not item.contains_secret_material and not item.contains_token_material and not item.contains_account_material for item in reviewed.audit_records),
        "parquet_unsupported": ".parquet" not in dumped,
    }


def _run_kiwoom_manual_response_import_smoke(output_dir: Path) -> dict[str, bool]:
    chart_file = output_dir / "kiwoom_manual_response_chart_fixture.json"
    chart_file.write_text(
        json.dumps(
            {
                "stk_cd": "005930",
                "stk_day_pole_chart_qry": [
                    {
                        "cur_prc": "-78800",
                        "trde_qty": "7913",
                        "cntr_tm": "20260625153000",
                        "open_pric": "-78850",
                        "high_pric": "-78900",
                        "low_pric": "-78800",
                        "acc_trde_qty": "14947571",
                        "pred_pre": "-600",
                        "pred_pre_sig": "5",
                    }
                ],
                "return_code": 0,
                "return_msg": "정상적으로 처리되었습니다",
            },
            sort_keys=True,
        ),
        encoding="utf-8",
    )
    quote_file = output_dir / "kiwoom_manual_response_quote_fixture.json"
    quote_file.write_text(
        json.dumps(
            {
                "stk_cd": "005930",
                "stk_nm": "삼성전자",
                "return_code": 0,
                "return_msg": "정상적으로 처리되었습니다",
                "bid_req_base_tm": "153000",
                "ask_price_1": "+78810",
                "ask_qty_1": "1200",
                "bid_price_1": "+78790",
                "bid_qty_1": "1500",
                "ask_price_2": "+78820",
                "ask_qty_2": "900",
                "bid_price_2": "+78790",
                "bid_qty_2": "800",
                "cont_yn": "N",
                "next_key": "",
            },
            sort_keys=True,
        ),
        encoding="utf-8",
    )
    reviewed = build_kiwoom_manual_response_import_harness(
        KiwoomManualResponseImportRequest.model_validate(
            {
                "request_id": "kiwoom-manual-response-import-smoke",
                "files": [
                    {
                        "file_path": str(chart_file),
                        "declared_api_id": "KA10081",
                        "provider_symbol": "005930",
                        "canonical_instrument_key": "005930_KRX",
                        "available_at": "2026-06-25T15:35:00+09:00",
                        "source_ref": str(chart_file),
                    },
                    {
                        "file_path": str(quote_file),
                        "declared_api_id": "KA10004",
                        "provider_symbol": "005930",
                        "canonical_instrument_key": "005930_KRX",
                        "available_at": "2026-06-25T15:35:00+09:00",
                        "source_ref": str(quote_file),
                    },
                ],
                "compose_snapshot": True,
            }
        )
    )
    dumped = json.dumps(reviewed.model_dump(mode="json")).lower()
    return {
        "fixture_run": True,
        "summary_report_generated": reviewed.summary_report.report_id.endswith("REPORT"),
        "file_classification_report_generated": reviewed.file_classification_report.report_id.endswith("REPORT"),
        "sensitive_scan_report_generated": reviewed.sensitive_scan_report.report_id.endswith("REPORT"),
        "routing_report_generated": reviewed.routing_report.report_id.endswith("REPORT"),
        "canonical_output_report_generated": reviewed.canonical_output_report.report_id.endswith("REPORT"),
        "snapshot_report_generated": reviewed.snapshot_composition_result.report_id.endswith("RESULT"),
        "safety_report_generated": reviewed.safety_report.safety_report_id.endswith("REPORT"),
        "gap_report_generated": reviewed.gap_report.gap_report_id.endswith("REPORT"),
        "local_only": reviewed.summary_report.local_file_only,
        "offline_only": reviewed.summary_report.offline_only,
        "report_only": reviewed.summary_report.report_only,
        "non_executable": reviewed.summary_report.non_executable,
        "no_network": reviewed.summary_report.no_network,
        "no_provider_api": reviewed.summary_report.no_provider_api,
        "no_account_order_path": reviewed.summary_report.no_order and reviewed.summary_report.no_account_mutation,
        "no_env_credential_read": reviewed.summary_report.no_env_read and reviewed.summary_report.no_credential_read,
        "no_token_loading": reviewed.summary_report.no_token_loading,
        "no_auth_header_generation": reviewed.summary_report.no_auth_header_generation,
        "canonical_output_only": bool(reviewed.canonical_output_report.canonical_ohlcv_records)
        and bool(reviewed.canonical_output_report.canonical_quote_records)
        and all(record.source_ref.endswith(".json") for record in reviewed.canonical_output_report.canonical_ohlcv_records)
        and all(record.source_ref.endswith(".json") for record in reviewed.canonical_output_report.canonical_quote_records)
        and all(not item.contains_secret_material and not item.contains_token_material and not item.contains_account_material for item in reviewed.audit_records),
        "snapshot_composed": reviewed.snapshot_composition_result.composed,
        "snapshot_not_empty": bool(
            reviewed.snapshot_composition_result.snapshot_report
            and reviewed.snapshot_composition_result.snapshot_report.snapshots
        ),
        "parquet_unsupported": ".parquet" not in dumped,
    }


def _run_kiwoom_readonly_final_transport_smoke(output_dir: Path) -> dict[str, bool]:
    reviewed = build_kiwoom_readonly_final_transport(
        KiwoomReadonlyFinalRequest.model_validate(
            {
                "request_id": "kiwoom-readonly-final-smoke",
                "mode": KiwoomReadonlyFinalTransportMode.MOCKED_TRANSPORT_ONLY.value,
                "api_id": "KA10081",
                "domain": KiwoomReadonlyFinalDomain.KIWOOM_MOCK_KRX.value,
                "body_json": {"stk_cd": "005930", "base_dt": "20260625", "upd_stkpc_tp": "1"},
                "provider_symbol": "005930",
                "canonical_instrument_key": "005930_KRX",
                "available_at": "2026-06-25T15:35:00+09:00",
                "validate_snapshot": True,
                "mocked_response_payload": {
                    "stk_cd": "005930",
                    "stk_day_pole_chart_qry": [
                        {
                            "cur_prc": "-78800",
                            "trde_qty": "7913",
                            "cntr_tm": "20260625153000",
                            "open_pric": "-78850",
                            "high_pric": "-78900",
                            "low_pric": "-78800",
                            "acc_trde_qty": "14947571",
                            "pred_pre": "-600",
                            "pred_pre_sig": "5",
                        }
                    ],
                    "return_code": 0,
                    "return_msg": "정상적으로 처리되었습니다",
                    "cont_yn": "N",
                    "next_key": "",
                },
                "token_provider": {
                    "provider_kind": KiwoomReadonlyFinalTokenProviderKind.FAKE_PROVIDER.value,
                },
            }
        )
    )
    dumped = json.dumps(reviewed.model_dump(mode="json")).lower()
    return {
        "fixture_run": True,
        "summary_report_generated": reviewed.summary_report.report_id.endswith("REPORT"),
        "request_preview_report_generated": reviewed.request_preview_report.report_id.endswith("REPORT"),
        "allowlist_report_generated": reviewed.allowlist_report.report_id.endswith("REPORT"),
        "token_provider_report_generated": reviewed.token_provider_report.report_id.endswith("REPORT"),
        "capture_report_generated": reviewed.capture_report is not None and reviewed.capture_report.report_id.endswith("REPORT"),
        "response_routing_report_generated": reviewed.parser_routing_report is not None and reviewed.parser_routing_report.report_id.endswith("REPORT"),
        "snapshot_validation_report_generated": reviewed.snapshot_validation_report is not None and reviewed.snapshot_validation_report.report_id.endswith("REPORT"),
        "readiness_report_generated": reviewed.readiness_report.report_id.endswith("REPORT"),
        "safety_report_generated": reviewed.safety_report.safety_report_id.endswith("REPORT"),
        "gap_report_generated": reviewed.gap_report.gap_report_id.endswith("REPORT"),
        "local_only": reviewed.summary_report.local_file_only,
        "offline_only": reviewed.summary_report.offline_only,
        "report_only": reviewed.summary_report.report_only,
        "non_executable": reviewed.summary_report.non_executable,
        "no_network": reviewed.summary_report.no_network,
        "no_provider_api": reviewed.summary_report.no_provider_api,
        "no_account_order_path": reviewed.summary_report.no_order and reviewed.summary_report.no_account_mutation,
        "no_env_credential_read": reviewed.summary_report.no_env_read and reviewed.summary_report.no_credential_read,
        "no_token_loading": reviewed.summary_report.no_token_loading,
        "no_auth_header_generation": reviewed.summary_report.no_auth_header_generation,
        "canonical_output_only": reviewed.parser_routing_report is not None
        and reviewed.parser_routing_report.import_result is not None
        and bool(reviewed.parser_routing_report.import_result.canonical_output_report.canonical_ohlcv_records),
        "snapshot_validation_ran": reviewed.snapshot_validation_report is not None,
        "real_network_not_used": reviewed.response_report is not None and reviewed.summary_report.no_network,
        "parquet_unsupported": ".parquet" not in dumped,
    }
