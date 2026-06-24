from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import date, datetime
from pathlib import Path

from stock_risk_mcp.adapters.file_price_history import FilePriceHistoryAdapter
from stock_risk_mcp.adapters.file_company_risk import FileCompanyRiskAdapter, FileCompanyRiskWithComplianceAdapter
from stock_risk_mcp.adapters.file_market_data import FileMarketDataAdapter
from stock_risk_mcp.adapters.file_news import FileNewsAdapter
from stock_risk_mcp.adapters.file_toss_signal import FileTossSignalAdapter
from stock_risk_mcp.adapters.mock_company_risk import MockCompanyRiskAdapter
from stock_risk_mcp.adapters.nasdaq_noncompliant_file import NasdaqNoncompliantFileAdapter
from stock_risk_mcp.adapters.price_history_market_data import PriceHistoryMarketDataAdapter
from stock_risk_mcp.asof_price_history import AsOfPriceHistoryProvider
from stock_risk_mcp.backtest import BacktestService
from stock_risk_mcp.basket import BasketPolicy, candidate_from_trade_plan
from stock_risk_mcp.basket_backtest import run_basket_backtest
from stock_risk_mcp.basket_builder import build_basket
from stock_risk_mcp.broker_adapter_service import BrokerAdapterService
from stock_risk_mcp.broker_models import BrokerEnvironment, BrokerId, BrokerOrderStatus
from stock_risk_mcp.candidate_universe import (
    CandidateScanPolicy,
    CandidateSource,
    load_db_universe,
    load_file_universe,
    load_manual_universe,
)
from stock_risk_mcp.compliance import NASDAQ_NONCOMPLIANT_SOURCE_NAME
from stock_risk_mcp.analysis_report import (
    build_basket_plan_report,
    build_candidate_scan_report,
    build_pipeline_summary_report,
    build_policy_evaluation_report,
)
from stock_risk_mcp.agent_brief import build_agent_brief
from stock_risk_mcp.agent_context import build_agent_context_from_pipeline, build_agent_context_from_report
from stock_risk_mcp.agent_prompt import build_agent_prompt
from stock_risk_mcp.agent_tools import read_only_tool_manifest
from stock_risk_mcp.connector_pipeline import run_connectors, run_connectors_and_import
from stock_risk_mcp.connector_registry import default_connector_registry, register_http_providers
from stock_risk_mcp.data_import import run_unified_import
from stock_risk_mcp.dashboard import build_daily_dashboard, build_overview_dashboard, build_pipeline_dashboard, build_policy_dashboard
from stock_risk_mcp.dashboard_models import DashboardBuildResult, DashboardBuildStatus, DashboardType
from stock_risk_mcp.demo_pipeline import run_local_demo
from stock_risk_mcp.demo_report import DEMO_DISCLAIMER
from stock_risk_mcp.import_report import import_run_report
from stock_risk_mcp.ingestion import save_evaluation_inputs_and_result
from stock_risk_mcp.indicators import analyze_price_bars
from stock_risk_mcp.kiwoom_readonly_adapter import KiwoomRestReadOnlyAdapter
from stock_risk_mcp.kiwoom_readonly_models import KiwoomEnvironment
from stock_risk_mcp.kiwoom_readonly_service import KiwoomReadOnlyService
from stock_risk_mcp.kiwoom_mock_execution_service import KiwoomMockExecutionService
from stock_risk_mcp.kiwoom_official_manifest import (
    KiwoomOfficialEndpointClass,
    load_kiwoom_official_manifest,
)
from stock_risk_mcp.kiwoom_official_manifest_validator import validate_kiwoom_official_manifest
from stock_risk_mcp.kiwoom_credentials import load_kiwoom_credentials
from stock_risk_mcp.kiwoom_real_readonly_models import (
    KiwoomCredentialSource,
    KiwoomRealNetworkConfig,
    KiwoomRealNetworkEnvironment,
)
from stock_risk_mcp.kiwoom_real_readonly_service import KiwoomRealReadOnlyService
from stock_risk_mcp.kiwoom_real_readonly_smoke import KiwoomRealReadOnlySmokeService, build_smoke_plan
from stock_risk_mcp.kiwoom_sandbox_order_models import KiwoomSandboxOrderConfig
from stock_risk_mcp.kiwoom_sandbox_order_service import KiwoomSandboxOrderService
from stock_risk_mcp.kiwoom_sandbox_sell_dry_run import KiwoomSandboxSellDryRunService
from stock_risk_mcp.kiwoom_sandbox_sell_schema_verifier import KiwoomSandboxSellSchemaVerifier
from stock_risk_mcp.kiwoom_official_sell_schema_evidence import OfficialSellSchemaEvidenceReviewStatus
from stock_risk_mcp.kiwoom_official_sell_schema_evidence_service import KiwoomOfficialSellSchemaEvidenceService
from stock_risk_mcp.kiwoom_account_read_models import KiwoomAccountReadConfig
from stock_risk_mcp.kiwoom_account_read_service import KiwoomAccountReadService
from stock_risk_mcp.kiwoom_account_read_transport import RealKiwoomAccountReadTransport
from stock_risk_mcp.kiwoom_account_read_smoke import KiwoomAccountReadSmokeService, build_account_read_smoke_plan
from stock_risk_mcp.dilution_signal_file import load_dilution_signals
from stock_risk_mcp.flow_signal_file import load_flow_signals
from stock_risk_mcp.fx_service import FXService
from stock_risk_mcp.models import DataSource, IngestionStatus, PriceBar, SourceType, TradeProposal
from stock_risk_mcp.local_llm import LocalLLMBackend, LocalLLMRequest
from stock_risk_mcp.local_llm_client import LocalLLMClient
from stock_risk_mcp.local_ledger_service import LocalLedgerService
from stock_risk_mcp.local_model_runtime_service import (
    run_local_model_advisory_dry_run,
    run_local_model_candidates_list,
    run_local_model_runtime_check,
)
from stock_risk_mcp.local_model_benchmark_service import (
    load_local_model_benchmark_report,
    rank_local_model_candidates_from_report,
    run_local_model_benchmark_cli,
)
from stock_risk_mcp.local_model_decision_report_service import (
    run_local_model_decision_report_cli,
    load_local_model_decision_report,
    validate_local_model_benchmark_pack,
)
from stock_risk_mcp.strategy_track_service import (
    load_strategy_track_validation_report,
    run_strategy_track_compare,
    run_strategy_track_profile_validation,
)
from stock_risk_mcp.market_profit_service import (
    load_market_profit_report,
    load_market_profit_validation_report,
    run_market_profit_compare_tracks,
    run_market_profit_estimate,
    run_market_profit_profile_validation,
)
from stock_risk_mcp.domestic_realtime_service import (
    run_domestic_realtime_event_normalize,
    run_domestic_realtime_plan_show,
    run_domestic_realtime_profile_validate,
    run_domestic_realtime_quality_report,
)
from stock_risk_mcp.domestic_scanner_service import (
    run_domestic_scanner_candidates,
    run_domestic_scanner_config_validate,
    run_domestic_scanner_quality_report,
    run_domestic_scanner_watchlist_plan,
)
from stock_risk_mcp.domestic_candidate_evaluation_service import (
    run_domestic_candidate_evaluate,
    run_domestic_candidate_evaluation_config_validate,
    run_domestic_candidate_evaluation_gap_report,
    run_domestic_candidate_evaluation_safety_report,
)
from stock_risk_mcp.domestic_replay_service import (
    run_domestic_replay_config_validate,
    run_domestic_replay_metrics_report,
    run_domestic_replay_promotion_readiness,
    run_domestic_replay_run,
)
from stock_risk_mcp.domestic_calibration_service import (
    run_domestic_calibration_config_validate,
    run_domestic_calibration_run,
    run_domestic_policy_compare,
    run_domestic_promotion_gate_report,
)
from stock_risk_mcp.domestic_paper_shadow_service import (
    run_domestic_paper_shadow_config_validate,
    run_domestic_paper_shadow_journal_build,
    run_domestic_paper_shadow_review_report,
    run_domestic_paper_shadow_safety_report,
)
from stock_risk_mcp.domestic_shadow_outcome_service import (
    run_domestic_shadow_outcome_config_validate,
    run_domestic_shadow_outcome_label,
    run_domestic_shadow_outcome_review_report,
    run_domestic_shadow_outcome_safety_report,
)
from stock_risk_mcp.domestic_shadow_advisory_context_service import (
    run_domestic_shadow_advisory_context_build,
    run_domestic_shadow_advisory_context_config_validate,
    run_domestic_shadow_advisory_context_gap_report,
    run_domestic_shadow_advisory_context_safety_report,
    run_domestic_shadow_advisory_context_validate,
)
from stock_risk_mcp.domestic_distillation_dataset_service import (
    run_domestic_distillation_dataset_build,
    run_domestic_distillation_dataset_config_validate,
    run_domestic_distillation_dataset_gap_report,
    run_domestic_distillation_dataset_safety_report,
    run_domestic_distillation_dataset_validate,
)
from stock_risk_mcp.domestic_market_regime_service import (
    run_domestic_market_regime_classify,
    run_domestic_market_regime_config_validate,
    run_domestic_market_regime_gap_report,
    run_domestic_market_regime_report,
    run_domestic_market_regime_safety_report,
)
from stock_risk_mcp.domestic_regime_aware_integration_service import (
    run_domestic_regime_aware_gap_report,
    run_domestic_regime_aware_integration_build,
    run_domestic_regime_aware_integration_config_validate,
    run_domestic_regime_aware_integration_report,
    run_domestic_regime_aware_safety_report,
)
from stock_risk_mcp.offline_prompt_pack_service import (
    run_prompt_pack_validate,
    run_prompt_pack_show,
    run_prompt_pack_coverage_report,
    run_prompt_pack_gap_report,
)
from stock_risk_mcp.historical_data_service import (
    run_historical_data_config_validate,
    run_historical_data_gap_report,
    run_historical_data_manifest_build,
    run_historical_data_quality_report,
    run_historical_data_validate,
)
from stock_risk_mcp.historical_calendar_service import (
    run_historical_calendar_config_validate,
    run_historical_calendar_gap_report,
    run_historical_calendar_validate,
)
from stock_risk_mcp.historical_replay_bridge_engine import (
    build_historical_replay_event_stream,
    build_historical_replay_windows,
    build_historical_scanner_replay_input,
)
from stock_risk_mcp.historical_replay_bridge_fixture import load_historical_replay_bridge_fixture
from stock_risk_mcp.historical_replay_bridge_models import (
    HistoricalReplayBridgeReport,
    HistoricalReplayBridgeSafetyReport,
)
from stock_risk_mcp.historical_outcome_engine import (
    build_historical_outcome_label_report,
    build_historical_outcome_windows,
)
from stock_risk_mcp.historical_outcome_fixture import load_historical_outcome_fixture
from stock_risk_mcp.historical_dataset_engine import build_historical_dataset_assembly as build_historical_dataset_assembly_input
from stock_risk_mcp.historical_dataset_fixture import load_historical_dataset_fixture
from stock_risk_mcp.historical_dataset_validation_engine import build_historical_dataset_validation
from stock_risk_mcp.historical_dataset_validation_fixture import load_historical_dataset_validation_fixture
from stock_risk_mcp.historical_dataset_readiness_engine import build_historical_dataset_readiness
from stock_risk_mcp.historical_dataset_readiness_fixture import load_historical_dataset_readiness_fixture
from stock_risk_mcp.historical_model_training_engine import (
    build_historical_model_training_plan_check,
    run_historical_model_training_sandbox,
)
from stock_risk_mcp.historical_model_experiment_engine import build_historical_model_experiment_registry
from stock_risk_mcp.historical_model_experiment_fixture import load_historical_model_experiment_fixture
from stock_risk_mcp.broker_mock_adapter_engine import run_broker_mock_adapter_boundary
from stock_risk_mcp.broker_mock_adapter_fixture import load_broker_mock_adapter_fixture
from stock_risk_mcp.kiwoom_mock_adapter_engine import run_kiwoom_mock_adapter_draft_mapping
from stock_risk_mcp.kiwoom_mock_adapter_fixture import load_kiwoom_mock_adapter_fixture
from stock_risk_mcp.kiwoom_mock_credential_boundary_engine import (
    run_kiwoom_mock_credential_boundary_evaluation,
)
from stock_risk_mcp.kiwoom_mock_credential_boundary_fixture import (
    load_kiwoom_mock_credential_boundary_fixture,
)
from stock_risk_mcp.kiwoom_mock_oauth_draft_engine import run_kiwoom_mock_oauth_draft_boundary
from stock_risk_mcp.kiwoom_mock_oauth_draft_fixture import load_kiwoom_mock_oauth_draft_fixture
from stock_risk_mcp.kiwoom_mock_oauth_execution_engine import (
    build_kiwoom_mock_oauth_execution_gap_report,
    build_kiwoom_mock_oauth_execution_safety_report,
    execute_kiwoom_mock_oauth,
)
from stock_risk_mcp.kiwoom_mock_oauth_execution_fixture import (
    load_kiwoom_mock_oauth_execution_fixture,
)
from stock_risk_mcp.kiwoom_mock_api_transport_draft_engine import (
    run_kiwoom_mock_api_transport_draft_boundary,
)
from stock_risk_mcp.kiwoom_mock_api_transport_draft_fixture import (
    load_kiwoom_mock_api_transport_draft_fixture,
)
from stock_risk_mcp.kiwoom_mock_api_preflight_gate_engine import (
    run_kiwoom_mock_api_preflight_gate,
)
from stock_risk_mcp.kiwoom_mock_api_preflight_gate_fixture import (
    load_kiwoom_mock_api_preflight_gate_fixture,
)
from stock_risk_mcp.cnn_fear_greed_engine import run_cnn_fear_greed_collection
from stock_risk_mcp.cnn_fear_greed_fixture import load_cnn_fear_greed_fixture
from stock_risk_mcp.risk_adjusted_paper_eval_engine import build_risk_adjusted_paper_evaluation
from stock_risk_mcp.risk_adjusted_paper_eval_fixture import load_risk_adjusted_paper_eval_fixture
from stock_risk_mcp.controlled_mock_readiness_engine import build_controlled_mock_readiness_review
from stock_risk_mcp.controlled_mock_readiness_fixture import load_controlled_mock_readiness_fixture
from stock_risk_mcp.market_regime_engine import build_market_regime
from stock_risk_mcp.market_regime_fixture import load_market_regime_fixture
from stock_risk_mcp.kiwoom_mock_market_data_execution_engine import (
    build_kiwoom_mock_market_data_execution_gap_report,
    build_kiwoom_mock_market_data_execution_safety_report,
    build_kiwoom_mock_market_data_response_report,
    execute_kiwoom_mock_market_data,
)
from stock_risk_mcp.kiwoom_mock_market_data_execution_fixture import (
    load_kiwoom_mock_market_data_execution_fixture,
)
from stock_risk_mcp.quant_strategy_robustness_engine import build_quant_strategy_robustness
from stock_risk_mcp.quant_strategy_robustness_fixture import load_quant_strategy_robustness_fixture
from stock_risk_mcp.point_in_time_universe_engine import build_point_in_time_universe_gate
from stock_risk_mcp.point_in_time_universe_fixture import load_point_in_time_universe_fixture
from stock_risk_mcp.walk_forward_validation_engine import build_walk_forward_validation
from stock_risk_mcp.walk_forward_validation_fixture import load_walk_forward_validation_fixture
from stock_risk_mcp.training_pipeline_promotion_engine import build_training_pipeline_promotion
from stock_risk_mcp.training_pipeline_promotion_fixture import load_training_pipeline_promotion_fixture
from stock_risk_mcp.strategy_ensemble_alpha_engine import build_strategy_ensemble_alpha_gate
from stock_risk_mcp.strategy_ensemble_alpha_fixture import load_strategy_ensemble_alpha_fixture
from stock_risk_mcp.regime_allocation_learning_engine import build_regime_allocation_learning_dataset
from stock_risk_mcp.regime_allocation_learning_fixture import load_regime_allocation_learning_fixture
from stock_risk_mcp.allocation_policy_training_engine import build_allocation_policy_training_sandbox
from stock_risk_mcp.allocation_policy_training_fixture import load_allocation_policy_training_fixture
from stock_risk_mcp.historical_paper_trading_engine import run_historical_paper_trading
from stock_risk_mcp.historical_paper_trading_fixture import load_historical_paper_trading_fixture
from stock_risk_mcp.historical_signal_candidate_engine import build_historical_signal_candidate_batch
from stock_risk_mcp.historical_signal_candidate_fixture import load_historical_signal_candidate_fixture
from stock_risk_mcp.historical_model_training_fixture import load_historical_model_training_fixture
from stock_risk_mcp.sell_safety_gate import SellSafetyGate
from stock_risk_mcp.notification_digest import build_daily_digest
from stock_risk_mcp.notification_outbox import deliver_notifications
from stock_risk_mcp.notification_templates import (
    build_notifications_from_agent_brief,
    build_notifications_from_local_llm_response,
    build_notifications_from_pipeline,
    build_notifications_from_report,
)
from stock_risk_mcp.provider_normalization import load_normalizer_config, normalize_sources
from stock_risk_mcp.provider_pack_config import load_provider_pack_config
from stock_risk_mcp.provider_pack_pipeline import run_provider_pack
from stock_risk_mcp.provider_packs import ProviderPackType
from stock_risk_mcp.notifications import NotificationChannelType, NotificationSeverity
from stock_risk_mcp.news_signal_file import load_news_signals
from stock_risk_mcp.operational_pipeline import OperationalPipeline
from stock_risk_mcp.order_intent import ExecutionMode, OrderIntent, OrderIntentStatus, OrderSide, OrderType
from stock_risk_mcp.order_intent_service import OrderIntentService
from stock_risk_mcp.order_risk_gate import RiskGateConfig
from stock_risk_mcp.pipeline_report import build_pipeline_summary
from stock_risk_mcp.pipeline_run import PipelineMode
from stock_risk_mcp.policy import load_policy
from stock_risk_mcp.policy_comparison import compare_policy_replays
from stock_risk_mcp.policy_evaluation_report import policy_evaluation_report
from stock_risk_mcp.policy_evaluation_suite import evaluate_policy_suite
from stock_risk_mcp.policy_promotion import activate_policy, approve_policy, create_policy_promotion_proposal
from stock_risk_mcp.policy_replay import replay_policy_on_replay_run
from stock_risk_mcp.policy_replay_batch import run_policy_replay_batch
from stock_risk_mcp.portfolio_currency import build_portfolio_currency_context
from stock_risk_mcp.provider_config import load_provider_configs, validate_provider_config_file
from stock_risk_mcp.reporting import ReportService
from stock_risk_mcp.release_check import build_release_check
from stock_risk_mcp.report_json import render_json
from stock_risk_mcp.report_markdown import render_markdown
from stock_risk_mcp.repository import RiskRepository
from stock_risk_mcp.realtime_market_data import MarketRegion, WatchlistStatus
from stock_risk_mcp.realtime_monitor import run_realtime_monitor
from stock_risk_mcp.realtime_provider_mock import MockRealtimeMarketDataProvider
from stock_risk_mcp.realtime_provider_replay import LocalReplayMarketDataProvider
from stock_risk_mcp.replay_dataset import load_replay_dataset
from stock_risk_mcp.replay_run import ReplayRunService
from stock_risk_mcp.scan_pipeline import run_candidate_scan
from stock_risk_mcp.scan_run import create_basket_from_scan_run, create_replay_snapshot_from_scan_run
from stock_risk_mcp.signal_enrichment import merge_signal_sources
from stock_risk_mcp.service import RiskEvaluationService
from stock_risk_mcp.setup import TradeDecision, TradeSizingPolicy
from stock_risk_mcp.setup_grading import SetupGrader
from stock_risk_mcp.strategy_optimizer import StrategyOptimizer
from stock_risk_mcp.strategy_advisor import DisabledLocalLLMAdvisor
from stock_risk_mcp.strategy_core import StrategyDecisionStatus
from stock_risk_mcp.strategy_order_intent_draft import create_order_intent_draft
from stock_risk_mcp.strategy_service import StrategyService
from stock_risk_mcp.strategy_backtest_service import StrategyBacktestService
from stock_risk_mcp.technical_evidence_service import load_technical_evidence_result, run_technical_evidence
from stock_risk_mcp.market_discovery_service import load_market_discovery_result, run_market_discovery
from stock_risk_mcp.llm_feature_service import load_llm_signal_evaluation_report, run_feature_store, run_signal_evaluation
from stock_risk_mcp.paper_eval_service import load_paper_eval_report, run_paper_eval
from stock_risk_mcp.trade_plan_service import load_trade_plan_report, run_trade_plan
from stock_risk_mcp.walk_forward_policy_service import load_walk_forward_policy_report, run_walk_forward_policy_replay
from stock_risk_mcp.local_llm_advisory_service import load_local_llm_advisory_result, run_local_llm_advisory
from stock_risk_mcp.strategy_policy import apply_strategy_policy_to_basket_policy, create_default_strategy_policy
from stock_risk_mcp.system_smoke import run_system_smoke
from stock_risk_mcp.trade_plan import create_trade_plan
from stock_risk_mcp.toss_signal_file import load_toss_signals
from stock_risk_mcp.watch_loop import run_watch_loop


def build_legacy_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Evaluate a stock trade proposal with the local risk MVP.")
    add_proposal_args(parser)
    return parser


def build_command_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Evaluate, ingest, and persist local stock risk data.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    evaluate_and_save = subparsers.add_parser(
        "evaluate-and-save",
        help="Evaluate a proposal and save adapter snapshots plus result to SQLite.",
    )
    add_proposal_args(evaluate_and_save)
    evaluate_and_save.add_argument("--db", type=Path, default=Path("data/stock_risk_mcp.sqlite3"))
    evaluate_and_save.add_argument("--market-file", type=Path, default=None, help="CSV/JSON market snapshots file")
    evaluate_and_save.add_argument("--company-risk-file", type=Path, default=None, help="CSV/JSON company risks file")
    evaluate_and_save.add_argument("--toss-file", type=Path, default=None, help="CSV/JSON toss investor snapshots file")
    evaluate_and_save.add_argument("--news-file", type=Path, default=None, help="CSV/JSON news events file")
    evaluate_and_save.add_argument(
        "--nasdaq-noncompliant-file",
        type=Path,
        default=None,
        help="CSV Nasdaq noncompliant companies file",
    )
    evaluate_and_save.add_argument(
        "--use-db-price-history",
        action="store_true",
        help="Use the SQLite price_history table to calculate market data.",
    )
    evaluate_and_save.add_argument("--source", default="adapter", help="Source label stored with snapshot rows")

    ingest_compliance = subparsers.add_parser(
        "ingest-nasdaq-noncompliant",
        help="Ingest a local Nasdaq noncompliant companies CSV into SQLite.",
    )
    ingest_compliance.add_argument("--file", type=Path, required=True, help="CSV Nasdaq noncompliant companies file")
    ingest_compliance.add_argument("--db", type=Path, default=Path("data/stock_risk_mcp.sqlite3"))

    check_compliance = subparsers.add_parser("check-compliance", help="Check a ticker against a local compliance CSV.")
    check_compliance.add_argument("--ticker", required=True, help="Ticker symbol")
    check_compliance.add_argument("--file", type=Path, required=True, help="CSV Nasdaq noncompliant companies file")

    ingest_prices = subparsers.add_parser("ingest-prices", help="Ingest CSV/JSON price history into SQLite.")
    ingest_prices.add_argument("--file", type=Path, required=True, help="CSV/JSON price history file")
    ingest_prices.add_argument("--db", type=Path, default=Path("data/stock_risk_mcp.sqlite3"))

    import_data = subparsers.add_parser("import-data", help="Run append-only local unified data import.")
    import_data.add_argument("--db", type=Path, required=True)
    import_data.add_argument("--as-of-date", type=date.fromisoformat)
    import_data.add_argument("--price-history-file", type=Path)
    import_data.add_argument("--nasdaq-noncompliant-file", type=Path)
    import_data.add_argument("--fx-rate-file", type=Path)
    add_signal_file_args(import_data)
    import_runs = subparsers.add_parser("import-runs", help="List unified import runs.")
    import_runs.add_argument("--db", type=Path, required=True)
    import_runs.add_argument("--limit", type=int, default=50)
    import_show = subparsers.add_parser("import-show", help="Show a unified import run.")
    import_show.add_argument("--db", type=Path, required=True)
    import_show.add_argument("--import-run-id", required=True)
    fx_rates = subparsers.add_parser("fx-rates")
    fx_rates.add_argument("--db", type=Path, required=True)
    fx_rates.add_argument("--base-currency")
    fx_rates.add_argument("--quote-currency")
    fx_latest = subparsers.add_parser("fx-latest")
    fx_latest.add_argument("--db", type=Path, required=True)
    fx_latest.add_argument("--base-currency", required=True)
    fx_latest.add_argument("--quote-currency", required=True)
    fx_latest.add_argument("--as-of-date", type=date.fromisoformat, required=True)
    fx_convert = subparsers.add_parser("fx-convert")
    fx_convert.add_argument("--db", type=Path, required=True)
    fx_convert.add_argument("--amount", type=float, required=True)
    fx_convert.add_argument("--from-currency", required=True)
    fx_convert.add_argument("--to-currency", required=True)
    fx_convert.add_argument("--as-of-date", type=date.fromisoformat, required=True)

    normalize_file = subparsers.add_parser("normalize-file")
    normalize_file.add_argument("--db", type=Path, required=True)
    normalize_file.add_argument("--normalizer", required=True)
    normalize_file.add_argument("--input-file", type=Path, required=True)
    normalize_file.add_argument("--output-dir", type=Path, required=True)
    normalize_file.add_argument("--output-name")
    normalize_file.add_argument("--as-of-date", type=date.fromisoformat)
    normalize_file.add_argument("--save", action="store_true")
    add_normalizer_column_args(normalize_file)
    for name in ("normalize-run", "normalize-and-import"):
        normalize = subparsers.add_parser(name)
        normalize.add_argument("--db", type=Path, required=True)
        normalize.add_argument("--config-file", type=Path, required=True)
        normalize.add_argument("--output-dir", type=Path, required=True)
        normalize.add_argument("--as-of-date", type=date.fromisoformat)
        if name == "normalize-run":
            normalize.add_argument("--save", action="store_true")
    normalize_runs = subparsers.add_parser("normalize-runs")
    normalize_runs.add_argument("--db", type=Path, required=True)
    normalize_runs.add_argument("--limit", type=int, default=50)
    normalize_show = subparsers.add_parser("normalize-show")
    normalize_show.add_argument("--db", type=Path, required=True)
    normalize_show.add_argument("--normalize-run-id", required=True)

    subparsers.add_parser("connectors", help="List registered connectors.")
    for name in ("run-connectors", "run-connectors-and-import"):
        connector_command = subparsers.add_parser(name)
        connector_command.add_argument("--db", type=Path, required=True)
        connector_command.add_argument("--as-of-date", type=date.fromisoformat, required=True)
        connector_command.add_argument("--output-dir", type=Path, required=True)
        connector_command.add_argument("--connector", action="append", default=[])
        connector_command.add_argument("--ticker", action="append", default=[])
        add_http_provider_args(connector_command)
    validate_provider = subparsers.add_parser("validate-provider-config")
    validate_provider.add_argument("--provider-config-file", type=Path, required=True)
    validate_provider.add_argument("--allowed-host", action="append", default=None)
    run_http = subparsers.add_parser("run-http-connector")
    run_http.add_argument("--db", type=Path, required=True)
    run_http.add_argument("--as-of-date", type=date.fromisoformat, required=True)
    run_http.add_argument("--output-dir", type=Path, required=True)
    run_http.add_argument("--provider-config-file", type=Path, required=True)
    run_http.add_argument("--provider", required=True)
    run_http.add_argument("--enable-network", action="store_true")
    run_http.add_argument("--allowed-host", action="append", default=None)
    connector_runs = subparsers.add_parser("connector-runs", help="List connector runs.")
    connector_runs.add_argument("--db", type=Path, required=True)
    connector_runs.add_argument("--limit", type=int, default=50)
    connector_show = subparsers.add_parser("connector-show", help="Show a connector run.")
    connector_show.add_argument("--db", type=Path, required=True)
    connector_show.add_argument("--connector-run-id", required=True)
    for name in ("run-price-provider-pack", "run-fx-provider-pack", "run-price-fx-provider-pack", "run-news-provider-pack", "run-dilution-provider-pack", "run-flow-provider-pack"):
        provider_pack = subparsers.add_parser(name)
        provider_pack.add_argument("--db", type=Path, required=True)
        provider_pack.add_argument("--as-of-date", type=date.fromisoformat, required=True)
        provider_pack.add_argument("--provider-pack-config", type=Path, required=True)
        provider_pack.add_argument("--output-dir", type=Path, required=True)
        provider_pack.add_argument("--ticker", action="append", default=[])
        provider_pack.add_argument("--enable-network", action="store_true")
        provider_pack.add_argument("--allowed-host", action="append", default=None)
    provider_pack_runs = subparsers.add_parser("provider-pack-runs")
    provider_pack_runs.add_argument("--db", type=Path, required=True)
    provider_pack_runs.add_argument("--limit", type=int, default=50)
    provider_pack_show = subparsers.add_parser("provider-pack-show")
    provider_pack_show.add_argument("--db", type=Path, required=True)
    provider_pack_show.add_argument("--provider-pack-run-id", required=True)

    realtime_monitor = subparsers.add_parser("run-realtime-monitor")
    realtime_monitor.add_argument("--db", type=Path, required=True)
    realtime_monitor.add_argument("--provider", choices=["mock", "local-replay"], required=True)
    realtime_monitor.add_argument("--region", choices=["US", "KR"], required=True)
    realtime_monitor.add_argument("--symbols", required=True)
    realtime_monitor.add_argument("--replay-file", type=Path)
    realtime_monitor.add_argument("--output-dir", type=Path)
    realtime_monitor.add_argument("--max-events", type=int, default=10_000)
    realtime_monitor.add_argument("--max-symbols", type=int, default=500)
    realtime_monitor.add_argument("--max-hot-watchlist-size", type=int, default=20)
    realtime_monitor.add_argument("--min-dollar-volume-5m", type=float, default=1_000_000)
    watchlist_list = subparsers.add_parser("watchlist-list")
    watchlist_list.add_argument("--db", type=Path, required=True)
    watchlist_list.add_argument("--status", choices=[item.value for item in WatchlistStatus])
    watchlist_list.add_argument("--limit", type=int, default=200)
    realtime_runs = subparsers.add_parser("realtime-runs")
    realtime_runs.add_argument("--db", type=Path, required=True)
    realtime_runs.add_argument("--limit", type=int, default=50)
    realtime_show = subparsers.add_parser("realtime-show")
    realtime_show.add_argument("--db", type=Path, required=True)
    realtime_show.add_argument("--realtime-monitor-run-id", required=True)

    ledger_upsert = subparsers.add_parser("local-ledger-position-upsert")
    ledger_upsert.add_argument("--db", type=Path, required=True)
    ledger_upsert.add_argument("--symbol", required=True)
    ledger_upsert.add_argument("--region", choices=[item.value for item in MarketRegion], required=True)
    ledger_upsert.add_argument("--quantity", type=int, required=True)
    ledger_upsert.add_argument("--reserved-quantity", type=int, default=0)
    ledger_upsert.add_argument("--average-price", type=float)
    ledger_positions = subparsers.add_parser("local-ledger-positions")
    ledger_positions.add_argument("--db", type=Path, required=True)
    ledger_snapshot = subparsers.add_parser("local-ledger-snapshot")
    ledger_snapshot.add_argument("--db", type=Path, required=True)
    ledger_transactions = subparsers.add_parser("local-ledger-transactions")
    ledger_transactions.add_argument("--db", type=Path, required=True)
    sell_check = subparsers.add_parser("sell-safety-check")
    sell_check.add_argument("--db", type=Path, required=True)
    sell_check.add_argument("--symbol", required=True)
    sell_check.add_argument("--region", choices=[item.value for item in MarketRegion], required=True)
    sell_check.add_argument("--quantity", type=float, required=True)
    sell_check.add_argument("--order-intent-id")
    sell_check.add_argument("--reconciliation-status")
    sell_decisions = subparsers.add_parser("sell-safety-decisions")
    sell_decisions.add_argument("--db", type=Path, required=True)
    sell_decisions.add_argument("--limit", type=int, default=100)
    sell_show = subparsers.add_parser("sell-safety-show")
    sell_show.add_argument("--db", type=Path, required=True)
    sell_show.add_argument("--decision-id", required=True)

    strategy_run = subparsers.add_parser("strategy-run")
    strategy_run.add_argument("--db", type=Path, required=True)
    strategy_run.add_argument("--fixture-file", type=Path, required=True)
    strategy_run.add_argument("--include-local-llm-review", action="store_true")
    strategy_decisions = subparsers.add_parser("strategy-decisions")
    strategy_decisions.add_argument("--db", type=Path, required=True)
    strategy_decisions.add_argument("--status", choices=[item.value for item in StrategyDecisionStatus])
    strategy_decisions.add_argument("--limit", type=int, default=100)
    strategy_decision_show = subparsers.add_parser("strategy-decision-show")
    strategy_decision_show.add_argument("--db", type=Path, required=True)
    strategy_decision_show.add_argument("--decision-id", required=True)
    strategy_candidates = subparsers.add_parser("strategy-candidates")
    strategy_candidates.add_argument("--db", type=Path, required=True)
    strategy_candidates.add_argument("--limit", type=int, default=100)
    strategy_candidate_show = subparsers.add_parser("strategy-candidate-show")
    strategy_candidate_show.add_argument("--db", type=Path, required=True)
    strategy_candidate_show.add_argument("--candidate-id", required=True)
    strategy_draft = subparsers.add_parser("strategy-create-order-intent-draft")
    strategy_draft.add_argument("--db", type=Path, required=True)
    strategy_draft.add_argument("--decision-id", required=True)
    subparsers.add_parser("local-llm-health")
    strategy_backtest_run = subparsers.add_parser("strategy-backtest-run")
    strategy_backtest_run.add_argument("--db", type=Path, required=True)
    strategy_backtest_run.add_argument("--fixture-file", type=Path, required=True)
    strategy_backtest_reports = subparsers.add_parser("strategy-backtest-reports")
    strategy_backtest_reports.add_argument("--db", type=Path, required=True)
    strategy_backtest_reports.add_argument("--limit", type=int, default=100)
    strategy_backtest_show = subparsers.add_parser("strategy-backtest-show")
    strategy_backtest_show.add_argument("--db", type=Path, required=True)
    strategy_backtest_show.add_argument("--report-id", required=True)
    technical_run = subparsers.add_parser("technical-evidence-run")
    technical_run.add_argument("--fixture-file", type=Path, required=True)
    technical_run.add_argument("--output-file", type=Path)
    technical_show = subparsers.add_parser("technical-evidence-show")
    technical_show.add_argument("--output-file", type=Path, required=True)
    discovery_run = subparsers.add_parser("market-discovery-run")
    discovery_run.add_argument("--fixture-file", type=Path, required=True)
    discovery_run.add_argument("--output-file", type=Path)
    discovery_show = subparsers.add_parser("market-discovery-show")
    discovery_show.add_argument("--output-file", type=Path, required=True)
    feature_store = subparsers.add_parser("llm-feature-store-run")
    feature_store.add_argument("--signal-fixture-file", type=Path, required=True)
    feature_store.add_argument("--db", type=Path)
    feature_store.add_argument("--output-file", type=Path)
    signal_evaluate = subparsers.add_parser("llm-signal-evaluate")
    signal_evaluate.add_argument("--signal-fixture-file", type=Path, required=True)
    signal_evaluate.add_argument("--outcome-fixture-file", type=Path, required=True)
    signal_evaluate.add_argument("--db", type=Path)
    signal_evaluate.add_argument("--output-file", type=Path)
    evaluation_show = subparsers.add_parser("llm-signal-evaluation-show")
    evaluation_show.add_argument("--output-file", type=Path, required=True)
    trade_plan_run = subparsers.add_parser("trade-plan-run")
    trade_plan_run.add_argument("--fixture-file", type=Path, required=True)
    trade_plan_run.add_argument("--output-file", type=Path)
    trade_plan_show = subparsers.add_parser("trade-plan-show")
    trade_plan_show.add_argument("--output-file", type=Path, required=True)
    paper_eval_run = subparsers.add_parser("paper-eval-run")
    paper_eval_run.add_argument("--fixture-file", type=Path, required=True)
    paper_eval_run.add_argument("--output-file", type=Path)
    paper_eval_show = subparsers.add_parser("paper-eval-show")
    paper_eval_show.add_argument("--output-file", type=Path, required=True)
    policy_replay_run = subparsers.add_parser("policy-replay-run")
    policy_replay_run.add_argument("--fixture-file", type=Path, required=True)
    policy_replay_run.add_argument("--output-file", type=Path)
    policy_replay_show = subparsers.add_parser("policy-replay-show")
    policy_replay_show.add_argument("--output-file", type=Path, required=True)
    local_llm_advisory_run = subparsers.add_parser("local-llm-advisory-run")
    local_llm_advisory_run.add_argument("--fixture-file", type=Path, required=True)
    local_llm_advisory_run.add_argument("--output-file", type=Path)
    local_llm_advisory_show = subparsers.add_parser("local-llm-advisory-show")
    local_llm_advisory_show.add_argument("--output-file", type=Path, required=True)
    local_model_candidates = subparsers.add_parser("local-model-candidates-list")
    local_model_candidates.add_argument("--fixture-file", type=Path, required=True)
    local_model_candidates.add_argument("--output-file", type=Path)
    local_model_runtime_check = subparsers.add_parser("local-model-runtime-check")
    local_model_runtime_check.add_argument("--fixture-file", type=Path, required=True)
    local_model_runtime_check.add_argument("--output-file", type=Path)
    local_model_advisory_dry_run = subparsers.add_parser("local-model-advisory-dry-run")
    local_model_advisory_dry_run.add_argument("--fixture-file", type=Path, required=True)
    local_model_advisory_dry_run.add_argument("--output-file", type=Path)
    local_model_benchmark_run = subparsers.add_parser("local-model-benchmark-run")
    local_model_benchmark_run.add_argument("--fixture-file", type=Path, required=True)
    local_model_benchmark_run.add_argument("--candidate-output-file", type=Path, required=True)
    local_model_benchmark_run.add_argument("--output-file", type=Path)
    local_model_benchmark_show = subparsers.add_parser("local-model-benchmark-show")
    local_model_benchmark_show.add_argument("--output-file", type=Path, required=True)
    local_model_candidates_rank = subparsers.add_parser("local-model-candidates-rank")
    local_model_candidates_rank.add_argument("--benchmark-report-file", type=Path, required=True)
    local_model_candidates_rank.add_argument("--output-file", type=Path)
    local_model_decision_report = subparsers.add_parser("local-model-decision-report")
    local_model_decision_report.add_argument("--pack-file", type=Path, required=True)
    local_model_decision_report.add_argument("--output-file", type=Path)
    local_model_benchmark_pack_validate = subparsers.add_parser("local-model-benchmark-pack-validate")
    local_model_benchmark_pack_validate.add_argument("--pack-file", type=Path, required=True)
    strategy_track_profile_validate = subparsers.add_parser("strategy-track-profile-validate")
    strategy_track_profile_validate.add_argument("--fixture-file", type=Path, required=True)
    strategy_track_profile_validate.add_argument("--output-file", type=Path)
    strategy_track_profile_show = subparsers.add_parser("strategy-track-profile-show")
    strategy_track_profile_show.add_argument("--output-file", type=Path, required=True)
    strategy_track_compare = subparsers.add_parser("strategy-track-compare")
    strategy_track_compare.add_argument("--fixture-file", type=Path, required=True)
    strategy_track_compare.add_argument("--output-file", type=Path)
    market_profit_profile_validate = subparsers.add_parser("market-profit-profile-validate")
    market_profit_profile_validate.add_argument("--fixture-file", type=Path, required=True)
    market_profit_profile_validate.add_argument("--output-file", type=Path)
    market_profit_estimate = subparsers.add_parser("market-profit-estimate")
    market_profit_estimate.add_argument("--fixture-file", type=Path, required=True)
    market_profit_estimate.add_argument("--output-file", type=Path)
    market_profit_compare_tracks = subparsers.add_parser("market-profit-compare-tracks")
    market_profit_compare_tracks.add_argument("--fixture-file", type=Path, required=True)
    market_profit_compare_tracks.add_argument("--output-file", type=Path)
    market_profit_break_even = subparsers.add_parser("market-profit-break-even")
    market_profit_break_even.add_argument("--fixture-file", type=Path, required=True)
    domestic_realtime_profile_validate = subparsers.add_parser("domestic-realtime-profile-validate")
    domestic_realtime_profile_validate.add_argument("--fixture-file", type=Path, required=True)
    domestic_realtime_profile_validate.add_argument("--output-file", type=Path)
    domestic_realtime_plan_show = subparsers.add_parser("domestic-realtime-plan-show")
    domestic_realtime_plan_show.add_argument("--fixture-file", type=Path, required=True)
    domestic_realtime_event_normalize = subparsers.add_parser("domestic-realtime-event-normalize")
    domestic_realtime_event_normalize.add_argument("--fixture-file", type=Path, required=True)
    domestic_realtime_event_normalize.add_argument("--output-file", type=Path)
    domestic_realtime_quality_report = subparsers.add_parser("domestic-realtime-quality-report")
    domestic_realtime_quality_report.add_argument("--fixture-file", type=Path, required=True)
    domestic_realtime_quality_report.add_argument("--output-file", type=Path)
    domestic_scanner_config_validate = subparsers.add_parser("domestic-scanner-config-validate")
    domestic_scanner_config_validate.add_argument("--fixture-file", type=Path, required=True)
    domestic_scanner_config_validate.add_argument("--output-file", type=Path)
    domestic_scanner_candidates = subparsers.add_parser("domestic-scanner-candidates")
    domestic_scanner_candidates.add_argument("--fixture-file", type=Path, required=True)
    domestic_scanner_candidates.add_argument("--output-file", type=Path)
    domestic_scanner_watchlist_plan = subparsers.add_parser("domestic-scanner-watchlist-plan")
    domestic_scanner_watchlist_plan.add_argument("--fixture-file", type=Path, required=True)
    domestic_scanner_watchlist_plan.add_argument("--output-file", type=Path)
    domestic_scanner_quality_report = subparsers.add_parser("domestic-scanner-quality-report")
    domestic_scanner_quality_report.add_argument("--fixture-file", type=Path, required=True)
    domestic_scanner_quality_report.add_argument("--output-file", type=Path)
    domestic_candidate_eval_validate = subparsers.add_parser("domestic-candidate-evaluation-config-validate")
    domestic_candidate_eval_validate.add_argument("--fixture-file", type=Path, required=True)
    domestic_candidate_eval_validate.add_argument("--output-file", type=Path)
    domestic_candidate_evaluate = subparsers.add_parser("domestic-candidate-evaluate")
    domestic_candidate_evaluate.add_argument("--fixture-file", type=Path, required=True)
    domestic_candidate_evaluate.add_argument("--output-file", type=Path)
    domestic_candidate_eval_gap = subparsers.add_parser("domestic-candidate-evaluation-gap-report")
    domestic_candidate_eval_gap.add_argument("--fixture-file", type=Path, required=True)
    domestic_candidate_eval_gap.add_argument("--output-file", type=Path)
    domestic_candidate_eval_safety = subparsers.add_parser("domestic-candidate-evaluation-safety-report")
    domestic_candidate_eval_safety.add_argument("--fixture-file", type=Path, required=True)
    domestic_candidate_eval_safety.add_argument("--output-file", type=Path)
    domestic_replay_validate = subparsers.add_parser("domestic-replay-config-validate")
    domestic_replay_validate.add_argument("--fixture-file", type=Path, required=True)
    domestic_replay_validate.add_argument("--output-file", type=Path)
    domestic_replay_run = subparsers.add_parser("domestic-replay-run")
    domestic_replay_run.add_argument("--fixture-file", type=Path, required=True)
    domestic_replay_run.add_argument("--output-file", type=Path)
    domestic_replay_metrics = subparsers.add_parser("domestic-replay-metrics-report")
    domestic_replay_metrics.add_argument("--fixture-file", type=Path, required=True)
    domestic_replay_metrics.add_argument("--output-file", type=Path)
    domestic_replay_readiness = subparsers.add_parser("domestic-replay-promotion-readiness")
    domestic_replay_readiness.add_argument("--fixture-file", type=Path, required=True)
    domestic_replay_readiness.add_argument("--output-file", type=Path)
    domestic_calibration_validate = subparsers.add_parser("domestic-calibration-config-validate")
    domestic_calibration_validate.add_argument("--fixture-file", type=Path, required=True)
    domestic_calibration_validate.add_argument("--output-file", type=Path)
    domestic_calibration_run = subparsers.add_parser("domestic-calibration-run")
    domestic_calibration_run.add_argument("--fixture-file", type=Path, required=True)
    domestic_calibration_run.add_argument("--output-file", type=Path)
    domestic_policy_compare = subparsers.add_parser("domestic-policy-compare")
    domestic_policy_compare.add_argument("--fixture-file", type=Path, required=True)
    domestic_policy_compare.add_argument("--output-file", type=Path)
    domestic_promotion_gate = subparsers.add_parser("domestic-promotion-gate-report")
    domestic_promotion_gate.add_argument("--fixture-file", type=Path, required=True)
    domestic_promotion_gate.add_argument("--output-file", type=Path)
    domestic_paper_shadow_validate = subparsers.add_parser("domestic-paper-shadow-config-validate")
    domestic_paper_shadow_validate.add_argument("--fixture-file", type=Path, required=True)
    domestic_paper_shadow_validate.add_argument("--output-file", type=Path)
    domestic_paper_shadow_journal = subparsers.add_parser("domestic-paper-shadow-journal-build")
    domestic_paper_shadow_journal.add_argument("--fixture-file", type=Path, required=True)
    domestic_paper_shadow_journal.add_argument("--output-file", type=Path)
    domestic_paper_shadow_review = subparsers.add_parser("domestic-paper-shadow-review-report")
    domestic_paper_shadow_review.add_argument("--fixture-file", type=Path, required=True)
    domestic_paper_shadow_review.add_argument("--output-file", type=Path)
    domestic_paper_shadow_safety = subparsers.add_parser("domestic-paper-shadow-safety-report")
    domestic_paper_shadow_safety.add_argument("--fixture-file", type=Path, required=True)
    domestic_paper_shadow_safety.add_argument("--output-file", type=Path)
    domestic_shadow_outcome_validate = subparsers.add_parser("domestic-shadow-outcome-config-validate")
    domestic_shadow_outcome_validate.add_argument("--fixture-file", type=Path, required=True)
    domestic_shadow_outcome_validate.add_argument("--output-file", type=Path)
    domestic_shadow_outcome_label = subparsers.add_parser("domestic-shadow-outcome-label")
    domestic_shadow_outcome_label.add_argument("--fixture-file", type=Path, required=True)
    domestic_shadow_outcome_label.add_argument("--output-file", type=Path)
    domestic_shadow_outcome_review = subparsers.add_parser("domestic-shadow-outcome-review-report")
    domestic_shadow_outcome_review.add_argument("--fixture-file", type=Path, required=True)
    domestic_shadow_outcome_review.add_argument("--output-file", type=Path)
    domestic_shadow_outcome_safety = subparsers.add_parser("domestic-shadow-outcome-safety-report")
    domestic_shadow_outcome_safety.add_argument("--fixture-file", type=Path, required=True)
    domestic_shadow_outcome_safety.add_argument("--output-file", type=Path)
    domestic_shadow_advisory_validate = subparsers.add_parser("domestic-shadow-advisory-context-config-validate")
    domestic_shadow_advisory_validate.add_argument("--fixture-file", type=Path, required=True)
    domestic_shadow_advisory_validate.add_argument("--output-file", type=Path)
    domestic_shadow_advisory_build = subparsers.add_parser("domestic-shadow-advisory-context-build")
    domestic_shadow_advisory_build.add_argument("--fixture-file", type=Path, required=True)
    domestic_shadow_advisory_build.add_argument("--output-file", type=Path)
    domestic_shadow_advisory_report = subparsers.add_parser("domestic-shadow-advisory-context-validate")
    domestic_shadow_advisory_report.add_argument("--fixture-file", type=Path, required=True)
    domestic_shadow_advisory_report.add_argument("--output-file", type=Path)
    domestic_shadow_advisory_gap = subparsers.add_parser("domestic-shadow-advisory-context-gap-report")
    domestic_shadow_advisory_gap.add_argument("--fixture-file", type=Path, required=True)
    domestic_shadow_advisory_gap.add_argument("--output-file", type=Path)
    domestic_shadow_advisory_safety = subparsers.add_parser("domestic-shadow-advisory-context-safety-report")
    domestic_shadow_advisory_safety.add_argument("--fixture-file", type=Path, required=True)
    domestic_shadow_advisory_safety.add_argument("--output-file", type=Path)
    domestic_distillation_validate = subparsers.add_parser("domestic-distillation-dataset-config-validate")
    domestic_distillation_validate.add_argument("--fixture-file", type=Path, required=True)
    domestic_distillation_validate.add_argument("--output-file", type=Path)
    domestic_distillation_build = subparsers.add_parser("domestic-distillation-dataset-build")
    domestic_distillation_build.add_argument("--fixture-file", type=Path, required=True)
    domestic_distillation_build.add_argument("--output-file", type=Path)
    domestic_distillation_report = subparsers.add_parser("domestic-distillation-dataset-validate")
    domestic_distillation_report.add_argument("--fixture-file", type=Path, required=True)
    domestic_distillation_report.add_argument("--output-file", type=Path)
    domestic_distillation_gap = subparsers.add_parser("domestic-distillation-dataset-gap-report")
    domestic_distillation_gap.add_argument("--fixture-file", type=Path, required=True)
    domestic_distillation_gap.add_argument("--output-file", type=Path)
    domestic_distillation_safety = subparsers.add_parser("domestic-distillation-dataset-safety-report")
    domestic_distillation_safety.add_argument("--fixture-file", type=Path, required=True)
    domestic_distillation_safety.add_argument("--output-file", type=Path)
    domestic_market_regime_validate = subparsers.add_parser("domestic-market-regime-config-validate")
    domestic_market_regime_validate.add_argument("--fixture-file", type=Path, required=True)
    domestic_market_regime_validate.add_argument("--output-file", type=Path)
    domestic_market_regime_classify = subparsers.add_parser("domestic-market-regime-classify")
    domestic_market_regime_classify.add_argument("--fixture-file", type=Path, required=True)
    domestic_market_regime_classify.add_argument("--output-file", type=Path)
    domestic_market_regime_report = subparsers.add_parser("domestic-market-regime-report")
    domestic_market_regime_report.add_argument("--fixture-file", type=Path, required=True)
    domestic_market_regime_report.add_argument("--output-file", type=Path)
    domestic_market_regime_gap = subparsers.add_parser("domestic-market-regime-gap-report")
    domestic_market_regime_gap.add_argument("--fixture-file", type=Path, required=True)
    domestic_market_regime_gap.add_argument("--output-file", type=Path)
    domestic_market_regime_safety = subparsers.add_parser("domestic-market-regime-safety-report")
    domestic_market_regime_safety.add_argument("--fixture-file", type=Path, required=True)
    domestic_market_regime_safety.add_argument("--output-file", type=Path)
    domestic_regime_aware_validate = subparsers.add_parser("domestic-regime-aware-integration-config-validate")
    domestic_regime_aware_validate.add_argument("--fixture-file", type=Path, required=True)
    domestic_regime_aware_validate.add_argument("--output-file", type=Path)
    domestic_regime_aware_build = subparsers.add_parser("domestic-regime-aware-integration-build")
    domestic_regime_aware_build.add_argument("--fixture-file", type=Path, required=True)
    domestic_regime_aware_build.add_argument("--output-file", type=Path)
    domestic_regime_aware_report = subparsers.add_parser("domestic-regime-aware-integration-report")
    domestic_regime_aware_report.add_argument("--fixture-file", type=Path, required=True)
    domestic_regime_aware_report.add_argument("--output-file", type=Path)
    domestic_regime_aware_gap = subparsers.add_parser("domestic-regime-aware-gap-report")
    domestic_regime_aware_gap.add_argument("--fixture-file", type=Path, required=True)
    domestic_regime_aware_gap.add_argument("--output-file", type=Path)
    domestic_regime_aware_safety = subparsers.add_parser("domestic-regime-aware-safety-report")
    domestic_regime_aware_safety.add_argument("--fixture-file", type=Path, required=True)
    domestic_regime_aware_safety.add_argument("--output-file", type=Path)
    prompt_pack_validate = subparsers.add_parser("prompt-pack-validate")
    prompt_pack_validate.add_argument("--fixture-file", type=Path, required=True)
    prompt_pack_validate.add_argument("--output-file", type=Path)
    prompt_pack_show = subparsers.add_parser("prompt-pack-show")
    prompt_pack_show.add_argument("--fixture-file", type=Path, required=True)
    prompt_pack_coverage_report = subparsers.add_parser("prompt-pack-coverage-report")
    prompt_pack_coverage_report.add_argument("--fixture-file", type=Path, required=True)
    prompt_pack_coverage_report.add_argument("--output-file", type=Path)
    prompt_pack_gap_report = subparsers.add_parser("prompt-pack-gap-report")
    prompt_pack_gap_report.add_argument("--fixture-file", type=Path, required=True)
    prompt_pack_gap_report.add_argument("--output-file", type=Path)
    historical_data_config_validate = subparsers.add_parser("historical-data-config-validate")
    historical_data_config_validate.add_argument("--fixture-file", type=Path, required=True)
    historical_data_manifest_build = subparsers.add_parser("historical-data-manifest-build")
    historical_data_manifest_build.add_argument("--fixture-file", type=Path, required=True)
    historical_data_manifest_build.add_argument("--output-file", type=Path)
    historical_data_validate = subparsers.add_parser("historical-data-validate")
    historical_data_validate.add_argument("--fixture-file", type=Path, required=True)
    historical_data_validate.add_argument("--output-file", type=Path)
    historical_data_quality_report = subparsers.add_parser("historical-data-quality-report")
    historical_data_quality_report.add_argument("--fixture-file", type=Path, required=True)
    historical_data_quality_report.add_argument("--output-file", type=Path)
    historical_data_gap_report = subparsers.add_parser("historical-data-gap-report")
    historical_data_gap_report.add_argument("--fixture-file", type=Path, required=True)
    historical_data_gap_report.add_argument("--output-file", type=Path)
    historical_calendar_config_validate = subparsers.add_parser("historical-calendar-config-validate")
    historical_calendar_config_validate.add_argument("--fixture-file", type=Path, required=True)
    historical_calendar_validate = subparsers.add_parser("historical-calendar-validate")
    historical_calendar_validate.add_argument("--fixture-file", type=Path, required=True)
    historical_calendar_validate.add_argument("--output-file", type=Path)
    historical_calendar_gap_report = subparsers.add_parser("historical-calendar-gap-report")
    historical_calendar_gap_report.add_argument("--fixture-file", type=Path, required=True)
    historical_calendar_gap_report.add_argument("--output-file", type=Path)
    historical_replay_bridge_build = subparsers.add_parser("historical-replay-bridge-build")
    historical_replay_bridge_build.add_argument("--fixture-file", type=Path, required=True)
    historical_replay_bridge_build.add_argument("--output-file", type=Path)
    historical_replay_event_stream = subparsers.add_parser("historical-replay-event-stream")
    historical_replay_event_stream.add_argument("--fixture-file", type=Path, required=True)
    historical_replay_event_stream.add_argument("--output-file", type=Path)
    historical_replay_window_report = subparsers.add_parser("historical-replay-window-report")
    historical_replay_window_report.add_argument("--fixture-file", type=Path, required=True)
    historical_replay_window_report.add_argument("--output-file", type=Path)
    historical_scanner_replay_input = subparsers.add_parser("historical-scanner-replay-input")
    historical_scanner_replay_input.add_argument("--fixture-file", type=Path, required=True)
    historical_scanner_replay_input.add_argument("--output-file", type=Path)
    historical_replay_gap_report = subparsers.add_parser("historical-replay-gap-report")
    historical_replay_gap_report.add_argument("--fixture-file", type=Path, required=True)
    historical_replay_gap_report.add_argument("--output-file", type=Path)
    historical_replay_safety_report = subparsers.add_parser("historical-replay-safety-report")
    historical_replay_safety_report.add_argument("--fixture-file", type=Path, required=True)
    historical_replay_safety_report.add_argument("--output-file", type=Path)
    historical_outcome_observe = subparsers.add_parser("historical-outcome-observe")
    historical_outcome_observe.add_argument("--fixture-file", type=Path, required=True)
    historical_outcome_observe.add_argument("--output-file", type=Path)
    historical_outcome_label_report = subparsers.add_parser("historical-outcome-label-report")
    historical_outcome_label_report.add_argument("--fixture-file", type=Path, required=True)
    historical_outcome_label_report.add_argument("--output-file", type=Path)
    historical_outcome_gap_report = subparsers.add_parser("historical-outcome-gap-report")
    historical_outcome_gap_report.add_argument("--fixture-file", type=Path, required=True)
    historical_outcome_gap_report.add_argument("--output-file", type=Path)
    historical_outcome_safety_report = subparsers.add_parser("historical-outcome-safety-report")
    historical_outcome_safety_report.add_argument("--fixture-file", type=Path, required=True)
    historical_outcome_safety_report.add_argument("--output-file", type=Path)
    historical_dataset_assemble = subparsers.add_parser("historical-dataset-assemble")
    historical_dataset_assemble.add_argument("--fixture-file", type=Path, required=True)
    historical_dataset_assemble.add_argument("--output-file", type=Path)
    historical_dataset_export_manifest = subparsers.add_parser("historical-dataset-export-manifest")
    historical_dataset_export_manifest.add_argument("--fixture-file", type=Path, required=True)
    historical_dataset_export_manifest.add_argument("--output-file", type=Path)
    historical_dataset_quality_report = subparsers.add_parser("historical-dataset-quality-report")
    historical_dataset_quality_report.add_argument("--fixture-file", type=Path, required=True)
    historical_dataset_quality_report.add_argument("--output-file", type=Path)
    historical_dataset_gap_report = subparsers.add_parser("historical-dataset-gap-report")
    historical_dataset_gap_report.add_argument("--fixture-file", type=Path, required=True)
    historical_dataset_gap_report.add_argument("--output-file", type=Path)
    historical_dataset_safety_report = subparsers.add_parser("historical-dataset-safety-report")
    historical_dataset_safety_report.add_argument("--fixture-file", type=Path, required=True)
    historical_dataset_safety_report.add_argument("--output-file", type=Path)
    historical_dataset_validate = subparsers.add_parser("historical-dataset-validate")
    historical_dataset_validate.add_argument("--fixture-file", type=Path, required=True)
    historical_dataset_validate.add_argument("--output-file", type=Path)
    historical_dataset_leakage_audit = subparsers.add_parser("historical-dataset-leakage-audit")
    historical_dataset_leakage_audit.add_argument("--fixture-file", type=Path, required=True)
    historical_dataset_leakage_audit.add_argument("--output-file", type=Path)
    historical_dataset_split_manifest = subparsers.add_parser("historical-dataset-split-manifest")
    historical_dataset_split_manifest.add_argument("--fixture-file", type=Path, required=True)
    historical_dataset_split_manifest.add_argument("--output-file", type=Path)
    historical_dataset_coverage_report = subparsers.add_parser("historical-dataset-coverage-report")
    historical_dataset_coverage_report.add_argument("--fixture-file", type=Path, required=True)
    historical_dataset_coverage_report.add_argument("--output-file", type=Path)
    historical_dataset_label_distribution = subparsers.add_parser("historical-dataset-label-distribution")
    historical_dataset_label_distribution.add_argument("--fixture-file", type=Path, required=True)
    historical_dataset_label_distribution.add_argument("--output-file", type=Path)
    historical_dataset_readiness_report = subparsers.add_parser("historical-dataset-readiness-report")
    historical_dataset_readiness_report.add_argument("--fixture-file", type=Path, required=True)
    historical_dataset_readiness_report.add_argument("--output-file", type=Path)
    historical_dataset_split_quality_report = subparsers.add_parser("historical-dataset-split-quality-report")
    historical_dataset_split_quality_report.add_argument("--fixture-file", type=Path, required=True)
    historical_dataset_split_quality_report.add_argument("--output-file", type=Path)
    historical_dataset_imbalance_report = subparsers.add_parser("historical-dataset-imbalance-report")
    historical_dataset_imbalance_report.add_argument("--fixture-file", type=Path, required=True)
    historical_dataset_imbalance_report.add_argument("--output-file", type=Path)
    historical_dataset_baseline_evaluation = subparsers.add_parser("historical-dataset-baseline-evaluation")
    historical_dataset_baseline_evaluation.add_argument("--fixture-file", type=Path, required=True)
    historical_dataset_baseline_evaluation.add_argument("--output-file", type=Path)
    historical_dataset_readiness_safety_report = subparsers.add_parser("historical-dataset-readiness-safety-report")
    historical_dataset_readiness_safety_report.add_argument("--fixture-file", type=Path, required=True)
    historical_dataset_readiness_safety_report.add_argument("--output-file", type=Path)
    historical_model_training_plan_check = subparsers.add_parser("historical-model-training-plan-check")
    historical_model_training_plan_check.add_argument("--fixture-file", type=Path, required=True)
    historical_model_training_plan_check.add_argument("--output-file", type=Path)
    historical_model_train_sandbox = subparsers.add_parser("historical-model-train-sandbox")
    historical_model_train_sandbox.add_argument("--fixture-file", type=Path, required=True)
    historical_model_train_sandbox.add_argument("--output-file", type=Path)
    historical_model_evaluation_report = subparsers.add_parser("historical-model-evaluation-report")
    historical_model_evaluation_report.add_argument("--fixture-file", type=Path, required=True)
    historical_model_evaluation_report.add_argument("--output-file", type=Path)
    historical_model_artifact_manifest = subparsers.add_parser("historical-model-artifact-manifest")
    historical_model_artifact_manifest.add_argument("--fixture-file", type=Path, required=True)
    historical_model_artifact_manifest.add_argument("--output-file", type=Path)
    historical_model_training_safety_report = subparsers.add_parser("historical-model-training-safety-report")
    historical_model_training_safety_report.add_argument("--fixture-file", type=Path, required=True)
    historical_model_training_safety_report.add_argument("--output-file", type=Path)
    historical_model_experiment_register = subparsers.add_parser("historical-model-experiment-register")
    historical_model_experiment_register.add_argument("--fixture-file", type=Path, required=True)
    historical_model_experiment_register.add_argument("--output-file", type=Path)
    historical_model_experiment_compare = subparsers.add_parser("historical-model-experiment-compare")
    historical_model_experiment_compare.add_argument("--fixture-file", type=Path, required=True)
    historical_model_experiment_compare.add_argument("--output-file", type=Path)
    historical_model_risk_review = subparsers.add_parser("historical-model-risk-review")
    historical_model_risk_review.add_argument("--fixture-file", type=Path, required=True)
    historical_model_risk_review.add_argument("--output-file", type=Path)
    historical_model_promotion_block_report = subparsers.add_parser("historical-model-promotion-block-report")
    historical_model_promotion_block_report.add_argument("--fixture-file", type=Path, required=True)
    historical_model_promotion_block_report.add_argument("--output-file", type=Path)
    historical_model_experiment_safety_report = subparsers.add_parser("historical-model-experiment-safety-report")
    historical_model_experiment_safety_report.add_argument("--fixture-file", type=Path, required=True)
    historical_model_experiment_safety_report.add_argument("--output-file", type=Path)
    historical_signal_candidate_build = subparsers.add_parser("historical-signal-candidate-build")
    historical_signal_candidate_build.add_argument("--fixture-file", type=Path, required=True)
    historical_signal_candidate_build.add_argument("--output-file", type=Path)
    historical_signal_candidate_report = subparsers.add_parser("historical-signal-candidate-report")
    historical_signal_candidate_report.add_argument("--fixture-file", type=Path, required=True)
    historical_signal_candidate_report.add_argument("--output-file", type=Path)
    historical_signal_candidate_safety_report = subparsers.add_parser("historical-signal-candidate-safety-report")
    historical_signal_candidate_safety_report.add_argument("--fixture-file", type=Path, required=True)
    historical_signal_candidate_safety_report.add_argument("--output-file", type=Path)
    historical_signal_candidate_gap_report = subparsers.add_parser("historical-signal-candidate-gap-report")
    historical_signal_candidate_gap_report.add_argument("--fixture-file", type=Path, required=True)
    historical_signal_candidate_gap_report.add_argument("--output-file", type=Path)
    historical_paper_trading_run = subparsers.add_parser("historical-paper-trading-run")
    historical_paper_trading_run.add_argument("--fixture-file", type=Path, required=True)
    historical_paper_trading_run.add_argument("--output-file", type=Path)
    historical_paper_trading_performance_report = subparsers.add_parser("historical-paper-trading-performance-report")
    historical_paper_trading_performance_report.add_argument("--fixture-file", type=Path, required=True)
    historical_paper_trading_performance_report.add_argument("--output-file", type=Path)
    historical_paper_trading_safety_report = subparsers.add_parser("historical-paper-trading-safety-report")
    historical_paper_trading_safety_report.add_argument("--fixture-file", type=Path, required=True)
    historical_paper_trading_safety_report.add_argument("--output-file", type=Path)
    historical_paper_trading_gap_report = subparsers.add_parser("historical-paper-trading-gap-report")
    historical_paper_trading_gap_report.add_argument("--fixture-file", type=Path, required=True)
    historical_paper_trading_gap_report.add_argument("--output-file", type=Path)
    broker_mock_adapter_boundary_run = subparsers.add_parser("broker-mock-adapter-boundary-run")
    broker_mock_adapter_boundary_run.add_argument("--fixture-file", type=Path, required=True)
    broker_mock_adapter_boundary_run.add_argument("--output-file", type=Path)
    broker_mock_adapter_capability_report = subparsers.add_parser("broker-mock-adapter-capability-report")
    broker_mock_adapter_capability_report.add_argument("--fixture-file", type=Path, required=True)
    broker_mock_adapter_capability_report.add_argument("--output-file", type=Path)
    broker_mock_adapter_order_boundary_report = subparsers.add_parser("broker-mock-adapter-order-boundary-report")
    broker_mock_adapter_order_boundary_report.add_argument("--fixture-file", type=Path, required=True)
    broker_mock_adapter_order_boundary_report.add_argument("--output-file", type=Path)
    broker_mock_adapter_safety_report = subparsers.add_parser("broker-mock-adapter-safety-report")
    broker_mock_adapter_safety_report.add_argument("--fixture-file", type=Path, required=True)
    broker_mock_adapter_safety_report.add_argument("--output-file", type=Path)
    broker_mock_adapter_gap_report = subparsers.add_parser("broker-mock-adapter-gap-report")
    broker_mock_adapter_gap_report.add_argument("--fixture-file", type=Path, required=True)
    broker_mock_adapter_gap_report.add_argument("--output-file", type=Path)
    kiwoom_mock_adapter_draft_build = subparsers.add_parser("kiwoom-mock-adapter-draft-build")
    kiwoom_mock_adapter_draft_build.add_argument("--fixture-file", type=Path, required=True)
    kiwoom_mock_adapter_draft_build.add_argument("--output-file", type=Path)
    kiwoom_mock_adapter_request_draft_report = subparsers.add_parser("kiwoom-mock-adapter-request-draft-report")
    kiwoom_mock_adapter_request_draft_report.add_argument("--fixture-file", type=Path, required=True)
    kiwoom_mock_adapter_request_draft_report.add_argument("--output-file", type=Path)
    kiwoom_mock_adapter_response_draft_report = subparsers.add_parser("kiwoom-mock-adapter-response-draft-report")
    kiwoom_mock_adapter_response_draft_report.add_argument("--fixture-file", type=Path, required=True)
    kiwoom_mock_adapter_response_draft_report.add_argument("--output-file", type=Path)
    kiwoom_mock_adapter_safety_report = subparsers.add_parser("kiwoom-mock-adapter-safety-report")
    kiwoom_mock_adapter_safety_report.add_argument("--fixture-file", type=Path, required=True)
    kiwoom_mock_adapter_safety_report.add_argument("--output-file", type=Path)
    kiwoom_mock_adapter_gap_report = subparsers.add_parser("kiwoom-mock-adapter-gap-report")
    kiwoom_mock_adapter_gap_report.add_argument("--fixture-file", type=Path, required=True)
    kiwoom_mock_adapter_gap_report.add_argument("--output-file", type=Path)
    kiwoom_mock_credential_boundary_check = subparsers.add_parser("kiwoom-mock-credential-boundary-check")
    kiwoom_mock_credential_boundary_check.add_argument("--fixture-file", type=Path, required=True)
    kiwoom_mock_credential_boundary_check.add_argument("--output-file", type=Path)
    kiwoom_mock_credential_domain_policy_report = subparsers.add_parser("kiwoom-mock-credential-domain-policy-report")
    kiwoom_mock_credential_domain_policy_report.add_argument("--fixture-file", type=Path, required=True)
    kiwoom_mock_credential_domain_policy_report.add_argument("--output-file", type=Path)
    kiwoom_mock_credential_opt_in_report = subparsers.add_parser("kiwoom-mock-credential-opt-in-report")
    kiwoom_mock_credential_opt_in_report.add_argument("--fixture-file", type=Path, required=True)
    kiwoom_mock_credential_opt_in_report.add_argument("--output-file", type=Path)
    kiwoom_mock_credential_safety_report = subparsers.add_parser("kiwoom-mock-credential-safety-report")
    kiwoom_mock_credential_safety_report.add_argument("--fixture-file", type=Path, required=True)
    kiwoom_mock_credential_safety_report.add_argument("--output-file", type=Path)
    kiwoom_mock_credential_gap_report = subparsers.add_parser("kiwoom-mock-credential-gap-report")
    kiwoom_mock_credential_gap_report.add_argument("--fixture-file", type=Path, required=True)
    kiwoom_mock_credential_gap_report.add_argument("--output-file", type=Path)
    kiwoom_mock_oauth_token_request_draft = subparsers.add_parser("kiwoom-mock-oauth-token-request-draft")
    kiwoom_mock_oauth_token_request_draft.add_argument("--fixture-file", type=Path, required=True)
    kiwoom_mock_oauth_token_request_draft.add_argument("--output-file", type=Path)
    kiwoom_mock_oauth_token_response_draft_report = subparsers.add_parser("kiwoom-mock-oauth-token-response-draft-report")
    kiwoom_mock_oauth_token_response_draft_report.add_argument("--fixture-file", type=Path, required=True)
    kiwoom_mock_oauth_token_response_draft_report.add_argument("--output-file", type=Path)
    kiwoom_mock_oauth_token_revoke_draft = subparsers.add_parser("kiwoom-mock-oauth-token-revoke-draft")
    kiwoom_mock_oauth_token_revoke_draft.add_argument("--fixture-file", type=Path, required=True)
    kiwoom_mock_oauth_token_revoke_draft.add_argument("--output-file", type=Path)
    kiwoom_mock_oauth_token_lifecycle_report = subparsers.add_parser("kiwoom-mock-oauth-token-lifecycle-report")
    kiwoom_mock_oauth_token_lifecycle_report.add_argument("--fixture-file", type=Path, required=True)
    kiwoom_mock_oauth_token_lifecycle_report.add_argument("--output-file", type=Path)
    kiwoom_mock_oauth_safety_report = subparsers.add_parser("kiwoom-mock-oauth-safety-report")
    kiwoom_mock_oauth_safety_report.add_argument("--fixture-file", type=Path, required=True)
    kiwoom_mock_oauth_safety_report.add_argument("--output-file", type=Path)
    kiwoom_mock_oauth_gap_report = subparsers.add_parser("kiwoom-mock-oauth-gap-report")
    kiwoom_mock_oauth_gap_report.add_argument("--fixture-file", type=Path, required=True)
    kiwoom_mock_oauth_gap_report.add_argument("--output-file", type=Path)
    kiwoom_mock_oauth_token_request_execute = subparsers.add_parser("kiwoom-mock-oauth-token-request-execute")
    kiwoom_mock_oauth_token_request_execute.add_argument("--fixture-file", type=Path, required=True)
    kiwoom_mock_oauth_token_request_execute.add_argument("--output-file", type=Path)
    kiwoom_mock_oauth_token_request_execute.add_argument("--mock-domain", action="store_true")
    kiwoom_mock_oauth_token_request_execute.add_argument("--execute", action="store_true")
    kiwoom_mock_oauth_token_request_execute.add_argument("--acknowledge-mock-oauth-execution", action="store_true")
    kiwoom_mock_oauth_token_revoke_execute = subparsers.add_parser("kiwoom-mock-oauth-token-revoke-execute")
    kiwoom_mock_oauth_token_revoke_execute.add_argument("--fixture-file", type=Path, required=True)
    kiwoom_mock_oauth_token_revoke_execute.add_argument("--output-file", type=Path)
    kiwoom_mock_oauth_token_revoke_execute.add_argument("--mock-domain", action="store_true")
    kiwoom_mock_oauth_token_revoke_execute.add_argument("--execute", action="store_true")
    kiwoom_mock_oauth_token_revoke_execute.add_argument("--acknowledge-mock-oauth-execution", action="store_true")
    kiwoom_mock_oauth_execution_safety_report = subparsers.add_parser("kiwoom-mock-oauth-execution-safety-report")
    kiwoom_mock_oauth_execution_safety_report.add_argument("--fixture-file", type=Path, required=True)
    kiwoom_mock_oauth_execution_safety_report.add_argument("--output-file", type=Path)
    kiwoom_mock_oauth_execution_gap_report = subparsers.add_parser("kiwoom-mock-oauth-execution-gap-report")
    kiwoom_mock_oauth_execution_gap_report.add_argument("--fixture-file", type=Path, required=True)
    kiwoom_mock_oauth_execution_gap_report.add_argument("--output-file", type=Path)
    kiwoom_mock_oauth_execution_audit_report = subparsers.add_parser("kiwoom-mock-oauth-execution-audit-report")
    kiwoom_mock_oauth_execution_audit_report.add_argument("--fixture-file", type=Path, required=True)
    kiwoom_mock_oauth_execution_audit_report.add_argument("--output-file", type=Path)
    kiwoom_mock_api_transport_request_envelope_draft = subparsers.add_parser(
        "kiwoom-mock-api-transport-request-envelope-draft"
    )
    kiwoom_mock_api_transport_request_envelope_draft.add_argument("--fixture-file", type=Path, required=True)
    kiwoom_mock_api_transport_request_envelope_draft.add_argument("--output-file", type=Path)
    kiwoom_mock_api_transport_policy_report = subparsers.add_parser("kiwoom-mock-api-transport-policy-report")
    kiwoom_mock_api_transport_policy_report.add_argument("--fixture-file", type=Path, required=True)
    kiwoom_mock_api_transport_policy_report.add_argument("--output-file", type=Path)
    kiwoom_mock_api_retry_timeout_report = subparsers.add_parser("kiwoom-mock-api-retry-timeout-report")
    kiwoom_mock_api_retry_timeout_report.add_argument("--fixture-file", type=Path, required=True)
    kiwoom_mock_api_retry_timeout_report.add_argument("--output-file", type=Path)
    kiwoom_mock_api_error_response_draft_report = subparsers.add_parser(
        "kiwoom-mock-api-error-response-draft-report"
    )
    kiwoom_mock_api_error_response_draft_report.add_argument("--fixture-file", type=Path, required=True)
    kiwoom_mock_api_error_response_draft_report.add_argument("--output-file", type=Path)
    kiwoom_mock_api_transport_safety_report = subparsers.add_parser("kiwoom-mock-api-transport-safety-report")
    kiwoom_mock_api_transport_safety_report.add_argument("--fixture-file", type=Path, required=True)
    kiwoom_mock_api_transport_safety_report.add_argument("--output-file", type=Path)
    kiwoom_mock_api_transport_gap_report = subparsers.add_parser("kiwoom-mock-api-transport-gap-report")
    kiwoom_mock_api_transport_gap_report.add_argument("--fixture-file", type=Path, required=True)
    kiwoom_mock_api_transport_gap_report.add_argument("--output-file", type=Path)
    kiwoom_mock_api_preflight_check = subparsers.add_parser("kiwoom-mock-api-preflight-check")
    kiwoom_mock_api_preflight_check.add_argument("--fixture-file", type=Path, required=True)
    kiwoom_mock_api_preflight_check.add_argument("--output-file", type=Path)
    kiwoom_mock_api_preflight_readiness_report = subparsers.add_parser(
        "kiwoom-mock-api-preflight-readiness-report"
    )
    kiwoom_mock_api_preflight_readiness_report.add_argument("--fixture-file", type=Path, required=True)
    kiwoom_mock_api_preflight_readiness_report.add_argument("--output-file", type=Path)
    kiwoom_mock_api_preflight_safety_report = subparsers.add_parser(
        "kiwoom-mock-api-preflight-safety-report"
    )
    kiwoom_mock_api_preflight_safety_report.add_argument("--fixture-file", type=Path, required=True)
    kiwoom_mock_api_preflight_safety_report.add_argument("--output-file", type=Path)
    kiwoom_mock_api_preflight_gap_report = subparsers.add_parser("kiwoom-mock-api-preflight-gap-report")
    kiwoom_mock_api_preflight_gap_report.add_argument("--fixture-file", type=Path, required=True)
    kiwoom_mock_api_preflight_gap_report.add_argument("--output-file", type=Path)
    kiwoom_mock_api_preflight_audit_report = subparsers.add_parser("kiwoom-mock-api-preflight-audit-report")
    kiwoom_mock_api_preflight_audit_report.add_argument("--fixture-file", type=Path, required=True)
    kiwoom_mock_api_preflight_audit_report.add_argument("--output-file", type=Path)
    kiwoom_mock_market_data_request_execute = subparsers.add_parser("kiwoom-mock-market-data-request-execute")
    kiwoom_mock_market_data_request_execute.add_argument("--fixture-file", type=Path, required=True)
    kiwoom_mock_market_data_request_execute.add_argument("--output-file", type=Path)
    kiwoom_mock_market_data_request_execute.add_argument("--mock-domain", action="store_true")
    kiwoom_mock_market_data_request_execute.add_argument("--execute", action="store_true")
    kiwoom_mock_market_data_request_execute.add_argument(
        "--acknowledge-mock-market-data-execution",
        action="store_true",
    )
    kiwoom_mock_market_data_response_report = subparsers.add_parser("kiwoom-mock-market-data-response-report")
    kiwoom_mock_market_data_response_report.add_argument("--fixture-file", type=Path, required=True)
    kiwoom_mock_market_data_response_report.add_argument("--output-file", type=Path)
    kiwoom_mock_market_data_safety_report = subparsers.add_parser("kiwoom-mock-market-data-safety-report")
    kiwoom_mock_market_data_safety_report.add_argument("--fixture-file", type=Path, required=True)
    kiwoom_mock_market_data_safety_report.add_argument("--output-file", type=Path)
    kiwoom_mock_market_data_gap_report = subparsers.add_parser("kiwoom-mock-market-data-gap-report")
    kiwoom_mock_market_data_gap_report.add_argument("--fixture-file", type=Path, required=True)
    kiwoom_mock_market_data_gap_report.add_argument("--output-file", type=Path)
    kiwoom_mock_market_data_audit_report = subparsers.add_parser("kiwoom-mock-market-data-audit-report")
    kiwoom_mock_market_data_audit_report.add_argument("--fixture-file", type=Path, required=True)
    kiwoom_mock_market_data_audit_report.add_argument("--output-file", type=Path)
    quant_robustness_check = subparsers.add_parser("quant-robustness-check")
    quant_robustness_check.add_argument("--fixture-file", type=Path, required=True)
    quant_robustness_check.add_argument("--output-file", type=Path)
    quant_survivorship_bias_report = subparsers.add_parser("quant-survivorship-bias-report")
    quant_survivorship_bias_report.add_argument("--fixture-file", type=Path, required=True)
    quant_survivorship_bias_report.add_argument("--output-file", type=Path)
    quant_point_in_time_leakage_report = subparsers.add_parser("quant-point-in-time-leakage-report")
    quant_point_in_time_leakage_report.add_argument("--fixture-file", type=Path, required=True)
    quant_point_in_time_leakage_report.add_argument("--output-file", type=Path)
    quant_walk_forward_policy_report = subparsers.add_parser("quant-walk-forward-policy-report")
    quant_walk_forward_policy_report.add_argument("--fixture-file", type=Path, required=True)
    quant_walk_forward_policy_report.add_argument("--output-file", type=Path)
    quant_data_snooping_report = subparsers.add_parser("quant-data-snooping-report")
    quant_data_snooping_report.add_argument("--fixture-file", type=Path, required=True)
    quant_data_snooping_report.add_argument("--output-file", type=Path)
    quant_strategy_diversification_report = subparsers.add_parser("quant-strategy-diversification-report")
    quant_strategy_diversification_report.add_argument("--fixture-file", type=Path, required=True)
    quant_strategy_diversification_report.add_argument("--output-file", type=Path)
    quant_regime_readiness_report = subparsers.add_parser("quant-regime-readiness-report")
    quant_regime_readiness_report.add_argument("--fixture-file", type=Path, required=True)
    quant_regime_readiness_report.add_argument("--output-file", type=Path)
    point_in_time_universe_check = subparsers.add_parser("point-in-time-universe-check")
    point_in_time_universe_check.add_argument("--fixture-file", type=Path, required=True)
    point_in_time_universe_check.add_argument("--output-file", type=Path)
    point_in_time_universe_report = subparsers.add_parser("point-in-time-universe-report")
    point_in_time_universe_report.add_argument("--fixture-file", type=Path, required=True)
    point_in_time_universe_report.add_argument("--output-file", type=Path)
    survivorship_bias_dataset_report = subparsers.add_parser("survivorship-bias-dataset-report")
    survivorship_bias_dataset_report.add_argument("--fixture-file", type=Path, required=True)
    survivorship_bias_dataset_report.add_argument("--output-file", type=Path)
    security_lifecycle_coverage_report = subparsers.add_parser("security-lifecycle-coverage-report")
    security_lifecycle_coverage_report.add_argument("--fixture-file", type=Path, required=True)
    security_lifecycle_coverage_report.add_argument("--output-file", type=Path)
    dataset_leakage_report = subparsers.add_parser("dataset-leakage-report")
    dataset_leakage_report.add_argument("--fixture-file", type=Path, required=True)
    dataset_leakage_report.add_argument("--output-file", type=Path)
    dataset_promotion_readiness_report = subparsers.add_parser("dataset-promotion-readiness-report")
    dataset_promotion_readiness_report.add_argument("--fixture-file", type=Path, required=True)
    dataset_promotion_readiness_report.add_argument("--output-file", type=Path)
    walk_forward_validation_check = subparsers.add_parser("walk-forward-validation-check")
    walk_forward_validation_check.add_argument("--fixture-file", type=Path, required=True)
    walk_forward_validation_check.add_argument("--output-file", type=Path)
    walk_forward_split_report = subparsers.add_parser("walk-forward-split-report")
    walk_forward_split_report.add_argument("--fixture-file", type=Path, required=True)
    walk_forward_split_report.add_argument("--output-file", type=Path)
    data_snooping_report = subparsers.add_parser("data-snooping-report")
    data_snooping_report.add_argument("--fixture-file", type=Path, required=True)
    data_snooping_report.add_argument("--output-file", type=Path)
    experiment_lineage_report = subparsers.add_parser("experiment-lineage-report")
    experiment_lineage_report.add_argument("--fixture-file", type=Path, required=True)
    experiment_lineage_report.add_argument("--output-file", type=Path)
    parameter_search_pressure_report = subparsers.add_parser("parameter-search-pressure-report")
    parameter_search_pressure_report.add_argument("--fixture-file", type=Path, required=True)
    parameter_search_pressure_report.add_argument("--output-file", type=Path)
    final_test_contamination_report = subparsers.add_parser("final-test-contamination-report")
    final_test_contamination_report.add_argument("--fixture-file", type=Path, required=True)
    final_test_contamination_report.add_argument("--output-file", type=Path)
    strategy_stability_report = subparsers.add_parser("strategy-stability-report")
    strategy_stability_report.add_argument("--fixture-file", type=Path, required=True)
    strategy_stability_report.add_argument("--output-file", type=Path)
    validation_promotion_readiness_report = subparsers.add_parser("validation-promotion-readiness-report")
    validation_promotion_readiness_report.add_argument("--fixture-file", type=Path, required=True)
    validation_promotion_readiness_report.add_argument("--output-file", type=Path)
    training_pipeline_promotion_check = subparsers.add_parser("training-pipeline-promotion-check")
    training_pipeline_promotion_check.add_argument("--fixture-file", type=Path, required=True)
    training_pipeline_promotion_check.add_argument("--output-file", type=Path)
    training_dataset_eligibility_report = subparsers.add_parser("training-dataset-eligibility-report")
    training_dataset_eligibility_report.add_argument("--fixture-file", type=Path, required=True)
    training_dataset_eligibility_report.add_argument("--output-file", type=Path)
    training_dependency_report = subparsers.add_parser("training-dependency-report")
    training_dependency_report.add_argument("--fixture-file", type=Path, required=True)
    training_dependency_report.add_argument("--output-file", type=Path)
    training_leakage_overfit_risk_report = subparsers.add_parser("training-leakage-overfit-risk-report")
    training_leakage_overfit_risk_report.add_argument("--fixture-file", type=Path, required=True)
    training_leakage_overfit_risk_report.add_argument("--output-file", type=Path)
    training_reproducibility_report = subparsers.add_parser("training-reproducibility-report")
    training_reproducibility_report.add_argument("--fixture-file", type=Path, required=True)
    training_reproducibility_report.add_argument("--output-file", type=Path)
    model_artifact_policy_report = subparsers.add_parser("model-artifact-policy-report")
    model_artifact_policy_report.add_argument("--fixture-file", type=Path, required=True)
    model_artifact_policy_report.add_argument("--output-file", type=Path)
    model_promotion_readiness_report = subparsers.add_parser("model-promotion-readiness-report")
    model_promotion_readiness_report.add_argument("--fixture-file", type=Path, required=True)
    model_promotion_readiness_report.add_argument("--output-file", type=Path)
    strategy_ensemble_check = subparsers.add_parser("strategy-ensemble-check")
    strategy_ensemble_check.add_argument("--fixture-file", type=Path, required=True)
    strategy_ensemble_check.add_argument("--output-file", type=Path)
    alpha_candidate_report = subparsers.add_parser("alpha-candidate-report")
    alpha_candidate_report.add_argument("--fixture-file", type=Path, required=True)
    alpha_candidate_report.add_argument("--output-file", type=Path)
    strategy_family_diversification_report = subparsers.add_parser("strategy-family-diversification-report")
    strategy_family_diversification_report.add_argument("--fixture-file", type=Path, required=True)
    strategy_family_diversification_report.add_argument("--output-file", type=Path)
    alpha_correlation_risk_report = subparsers.add_parser("alpha-correlation-risk-report")
    alpha_correlation_risk_report.add_argument("--fixture-file", type=Path, required=True)
    alpha_correlation_risk_report.add_argument("--output-file", type=Path)
    drawdown_co_movement_report = subparsers.add_parser("drawdown-co-movement-report")
    drawdown_co_movement_report.add_argument("--fixture-file", type=Path, required=True)
    drawdown_co_movement_report.add_argument("--output-file", type=Path)
    regime_overlap_report = subparsers.add_parser("regime-overlap-report")
    regime_overlap_report.add_argument("--fixture-file", type=Path, required=True)
    regime_overlap_report.add_argument("--output-file", type=Path)
    alpha_portfolio_concentration_report = subparsers.add_parser("alpha-portfolio-concentration-report")
    alpha_portfolio_concentration_report.add_argument("--fixture-file", type=Path, required=True)
    alpha_portfolio_concentration_report.add_argument("--output-file", type=Path)
    ensemble_promotion_readiness_report = subparsers.add_parser("ensemble-promotion-readiness-report")
    ensemble_promotion_readiness_report.add_argument("--fixture-file", type=Path, required=True)
    ensemble_promotion_readiness_report.add_argument("--output-file", type=Path)
    regime_allocation_learning_check = subparsers.add_parser("regime-allocation-learning-check")
    regime_allocation_learning_check.add_argument("--fixture-file", type=Path, required=True)
    regime_allocation_learning_check.add_argument("--output-file", type=Path)
    regime_feature_report = subparsers.add_parser("regime-feature-report")
    regime_feature_report.add_argument("--fixture-file", type=Path, required=True)
    regime_feature_report.add_argument("--output-file", type=Path)
    allocation_action_candidate_report = subparsers.add_parser("allocation-action-candidate-report")
    allocation_action_candidate_report.add_argument("--fixture-file", type=Path, required=True)
    allocation_action_candidate_report.add_argument("--output-file", type=Path)
    hedge_inverse_eligibility_report = subparsers.add_parser("hedge-inverse-eligibility-report")
    hedge_inverse_eligibility_report.add_argument("--fixture-file", type=Path, required=True)
    hedge_inverse_eligibility_report.add_argument("--output-file", type=Path)
    forward_outcome_label_report = subparsers.add_parser("forward-outcome-label-report")
    forward_outcome_label_report.add_argument("--fixture-file", type=Path, required=True)
    forward_outcome_label_report.add_argument("--output-file", type=Path)
    allocation_reward_scoring_report = subparsers.add_parser("allocation-reward-scoring-report")
    allocation_reward_scoring_report.add_argument("--fixture-file", type=Path, required=True)
    allocation_reward_scoring_report.add_argument("--output-file", type=Path)
    regime_allocation_leakage_report = subparsers.add_parser("regime-allocation-leakage-report")
    regime_allocation_leakage_report.add_argument("--fixture-file", type=Path, required=True)
    regime_allocation_leakage_report.add_argument("--output-file", type=Path)
    regime_allocation_dataset_readiness_report = subparsers.add_parser("regime-allocation-dataset-readiness-report")
    regime_allocation_dataset_readiness_report.add_argument("--fixture-file", type=Path, required=True)
    regime_allocation_dataset_readiness_report.add_argument("--output-file", type=Path)
    allocation_policy_training_check = subparsers.add_parser("allocation-policy-training-check")
    allocation_policy_training_check.add_argument("--fixture-file", type=Path, required=True)
    allocation_policy_training_check.add_argument("--output-file", type=Path)
    allocation_policy_training_summary_report = subparsers.add_parser("allocation-policy-training-summary-report")
    allocation_policy_training_summary_report.add_argument("--fixture-file", type=Path, required=True)
    allocation_policy_training_summary_report.add_argument("--output-file", type=Path)
    regime_action_selection_report = subparsers.add_parser("regime-action-selection-report")
    regime_action_selection_report.add_argument("--fixture-file", type=Path, required=True)
    regime_action_selection_report.add_argument("--output-file", type=Path)
    allocation_policy_walk_forward_report = subparsers.add_parser("allocation-policy-walk-forward-report")
    allocation_policy_walk_forward_report.add_argument("--fixture-file", type=Path, required=True)
    allocation_policy_walk_forward_report.add_argument("--output-file", type=Path)
    allocation_policy_risk_adjusted_report = subparsers.add_parser("allocation-policy-risk-adjusted-report")
    allocation_policy_risk_adjusted_report.add_argument("--fixture-file", type=Path, required=True)
    allocation_policy_risk_adjusted_report.add_argument("--output-file", type=Path)
    allocation_policy_turnover_slippage_report = subparsers.add_parser("allocation-policy-turnover-slippage-report")
    allocation_policy_turnover_slippage_report.add_argument("--fixture-file", type=Path, required=True)
    allocation_policy_turnover_slippage_report.add_argument("--output-file", type=Path)
    allocation_policy_drawdown_stability_report = subparsers.add_parser("allocation-policy-drawdown-stability-report")
    allocation_policy_drawdown_stability_report.add_argument("--fixture-file", type=Path, required=True)
    allocation_policy_drawdown_stability_report.add_argument("--output-file", type=Path)
    allocation_policy_promotion_readiness_report = subparsers.add_parser("allocation-policy-promotion-readiness-report")
    allocation_policy_promotion_readiness_report.add_argument("--fixture-file", type=Path, required=True)
    allocation_policy_promotion_readiness_report.add_argument("--output-file", type=Path)
    allocation_policy_artifact_report = subparsers.add_parser("allocation-policy-artifact-report")
    allocation_policy_artifact_report.add_argument("--fixture-file", type=Path, required=True)
    allocation_policy_artifact_report.add_argument("--output-file", type=Path)
    cnn_fear_greed_collect = subparsers.add_parser("cnn-fear-greed-collect")
    cnn_fear_greed_collect.add_argument("--fixture-file", type=Path, required=True)
    cnn_fear_greed_collect.add_argument("--output-file", type=Path)
    cnn_fear_greed_collect.add_argument("--execute", action="store_true")
    cnn_fear_greed_collect.add_argument("--acknowledge-cnn-fear-greed-collection", action="store_true")
    cnn_fear_greed_snapshot_report = subparsers.add_parser("cnn-fear-greed-snapshot-report")
    cnn_fear_greed_snapshot_report.add_argument("--fixture-file", type=Path, required=True)
    cnn_fear_greed_snapshot_report.add_argument("--output-file", type=Path)
    cnn_fear_greed_history_report = subparsers.add_parser("cnn-fear-greed-history-report")
    cnn_fear_greed_history_report.add_argument("--fixture-file", type=Path, required=True)
    cnn_fear_greed_history_report.add_argument("--output-file", type=Path)
    cnn_fear_greed_feature_integration_report = subparsers.add_parser("cnn-fear-greed-feature-integration-report")
    cnn_fear_greed_feature_integration_report.add_argument("--fixture-file", type=Path, required=True)
    cnn_fear_greed_feature_integration_report.add_argument("--output-file", type=Path)
    cnn_fear_greed_source_health_report = subparsers.add_parser("cnn-fear-greed-source-health-report")
    cnn_fear_greed_source_health_report.add_argument("--fixture-file", type=Path, required=True)
    cnn_fear_greed_source_health_report.add_argument("--output-file", type=Path)
    cnn_fear_greed_audit_report = subparsers.add_parser("cnn-fear-greed-audit-report")
    cnn_fear_greed_audit_report.add_argument("--fixture-file", type=Path, required=True)
    cnn_fear_greed_audit_report.add_argument("--output-file", type=Path)
    risk_adjusted_paper_eval_check = subparsers.add_parser("risk-adjusted-paper-eval-check")
    risk_adjusted_paper_eval_check.add_argument("--fixture-file", type=Path, required=True)
    risk_adjusted_paper_eval_check.add_argument("--output-file", type=Path)
    paper_evaluation_summary_report = subparsers.add_parser("paper-evaluation-summary-report")
    paper_evaluation_summary_report.add_argument("--fixture-file", type=Path, required=True)
    paper_evaluation_summary_report.add_argument("--output-file", type=Path)
    virtual_portfolio_report = subparsers.add_parser("virtual-portfolio-report")
    virtual_portfolio_report.add_argument("--fixture-file", type=Path, required=True)
    virtual_portfolio_report.add_argument("--output-file", type=Path)
    virtual_trade_ledger_report = subparsers.add_parser("virtual-trade-ledger-report")
    virtual_trade_ledger_report.add_argument("--fixture-file", type=Path, required=True)
    virtual_trade_ledger_report.add_argument("--output-file", type=Path)
    paper_cost_slippage_report = subparsers.add_parser("paper-cost-slippage-report")
    paper_cost_slippage_report.add_argument("--fixture-file", type=Path, required=True)
    paper_cost_slippage_report.add_argument("--output-file", type=Path)
    paper_risk_adjusted_performance_report = subparsers.add_parser("paper-risk-adjusted-performance-report")
    paper_risk_adjusted_performance_report.add_argument("--fixture-file", type=Path, required=True)
    paper_risk_adjusted_performance_report.add_argument("--output-file", type=Path)
    paper_drawdown_exposure_report = subparsers.add_parser("paper-drawdown-exposure-report")
    paper_drawdown_exposure_report.add_argument("--fixture-file", type=Path, required=True)
    paper_drawdown_exposure_report.add_argument("--output-file", type=Path)
    paper_regime_fear_bucket_report = subparsers.add_parser("paper-regime-fear-bucket-report")
    paper_regime_fear_bucket_report.add_argument("--fixture-file", type=Path, required=True)
    paper_regime_fear_bucket_report.add_argument("--output-file", type=Path)
    paper_pass_readiness_report = subparsers.add_parser("paper-pass-readiness-report")
    paper_pass_readiness_report.add_argument("--fixture-file", type=Path, required=True)
    paper_pass_readiness_report.add_argument("--output-file", type=Path)
    controlled_mock_readiness_check = subparsers.add_parser("controlled-mock-readiness-check")
    controlled_mock_readiness_check.add_argument("--fixture-file", type=Path, required=True)
    controlled_mock_readiness_check.add_argument("--output-file", type=Path)
    mock_readiness_summary_report = subparsers.add_parser("mock-readiness-summary-report")
    mock_readiness_summary_report.add_argument("--fixture-file", type=Path, required=True)
    mock_readiness_summary_report.add_argument("--output-file", type=Path)
    mock_readiness_dependency_report = subparsers.add_parser("mock-readiness-dependency-report")
    mock_readiness_dependency_report.add_argument("--fixture-file", type=Path, required=True)
    mock_readiness_dependency_report.add_argument("--output-file", type=Path)
    paper_pass_evidence_report = subparsers.add_parser("paper-pass-evidence-report")
    paper_pass_evidence_report.add_argument("--fixture-file", type=Path, required=True)
    paper_pass_evidence_report.add_argument("--output-file", type=Path)
    mock_infrastructure_readiness_report = subparsers.add_parser("mock-infrastructure-readiness-report")
    mock_infrastructure_readiness_report.add_argument("--fixture-file", type=Path, required=True)
    mock_infrastructure_readiness_report.add_argument("--output-file", type=Path)
    mock_safety_policy_report = subparsers.add_parser("mock-safety-policy-report")
    mock_safety_policy_report.add_argument("--fixture-file", type=Path, required=True)
    mock_safety_policy_report.add_argument("--output-file", type=Path)
    mock_boundary_violation_report = subparsers.add_parser("mock-boundary-violation-report")
    mock_boundary_violation_report.add_argument("--fixture-file", type=Path, required=True)
    mock_boundary_violation_report.add_argument("--output-file", type=Path)
    mock_readiness_gap_report = subparsers.add_parser("mock-readiness-gap-report")
    mock_readiness_gap_report.add_argument("--fixture-file", type=Path, required=True)
    mock_readiness_gap_report.add_argument("--output-file", type=Path)
    market_regime_check = subparsers.add_parser("market-regime-check")
    market_regime_check.add_argument("--fixture-file", type=Path, required=True)
    market_regime_check.add_argument("--output-file", type=Path)
    market_regime_summary_report = subparsers.add_parser("market-regime-summary-report")
    market_regime_summary_report.add_argument("--fixture-file", type=Path, required=True)
    market_regime_summary_report.add_argument("--output-file", type=Path)
    market_regime_input_snapshot_report = subparsers.add_parser("market-regime-input-snapshot-report")
    market_regime_input_snapshot_report.add_argument("--fixture-file", type=Path, required=True)
    market_regime_input_snapshot_report.add_argument("--output-file", type=Path)
    risk_appetite_report = subparsers.add_parser("risk-appetite-report")
    risk_appetite_report.add_argument("--fixture-file", type=Path, required=True)
    risk_appetite_report.add_argument("--output-file", type=Path)
    market_direction_regime_report = subparsers.add_parser("market-direction-regime-report")
    market_direction_regime_report.add_argument("--fixture-file", type=Path, required=True)
    market_direction_regime_report.add_argument("--output-file", type=Path)
    volatility_regime_report = subparsers.add_parser("volatility-regime-report")
    volatility_regime_report.add_argument("--fixture-file", type=Path, required=True)
    volatility_regime_report.add_argument("--output-file", type=Path)
    fx_rate_dollar_stress_report = subparsers.add_parser("fx-rate-dollar-stress-report")
    fx_rate_dollar_stress_report.add_argument("--fixture-file", type=Path, required=True)
    fx_rate_dollar_stress_report.add_argument("--output-file", type=Path)
    cross_asset_conflict_report = subparsers.add_parser("cross-asset-conflict-report")
    cross_asset_conflict_report.add_argument("--fixture-file", type=Path, required=True)
    cross_asset_conflict_report.add_argument("--output-file", type=Path)
    market_regime_downstream_constraint_report = subparsers.add_parser("market-regime-downstream-constraint-report")
    market_regime_downstream_constraint_report.add_argument("--fixture-file", type=Path, required=True)
    market_regime_downstream_constraint_report.add_argument("--output-file", type=Path)
    market_regime_training_feature_report = subparsers.add_parser("market-regime-training-feature-report")
    market_regime_training_feature_report.add_argument("--fixture-file", type=Path, required=True)
    market_regime_training_feature_report.add_argument("--output-file", type=Path)
    market_regime_gap_report = subparsers.add_parser("market-regime-gap-report")
    market_regime_gap_report.add_argument("--fixture-file", type=Path, required=True)
    market_regime_gap_report.add_argument("--output-file", type=Path)

    create_intent = subparsers.add_parser("create-order-intent")
    create_intent.add_argument("--db", type=Path, required=True)
    create_intent.add_argument("--ticker", required=True)
    create_intent.add_argument("--region", required=True)
    create_intent.add_argument("--side", required=True)
    create_intent.add_argument("--order-type", required=True)
    create_intent.add_argument("--quantity", type=float)
    create_intent.add_argument("--notional", type=float)
    create_intent.add_argument("--limit-price", type=float)
    create_intent.add_argument("--stop-loss-price", type=float)
    create_intent.add_argument("--take-profit-price", type=float)
    create_intent.add_argument("--source-type", required=True)
    create_intent.add_argument("--source-id", default="cli")
    create_intent.add_argument("--reason", required=True)
    create_intent.add_argument("--confidence-score", type=float, default=1.0)
    create_intent.add_argument("--expires-at", type=datetime.fromisoformat)
    order_list = subparsers.add_parser("order-intents-list")
    order_list.add_argument("--db", type=Path, required=True)
    order_list.add_argument("--status", choices=[item.value for item in OrderIntentStatus])
    order_list.add_argument("--ticker")
    order_list.add_argument("--side", choices=["BUY", "SELL"])
    order_list.add_argument("--limit", type=int, default=100)
    evaluate_intents = subparsers.add_parser("evaluate-order-intents")
    evaluate_intents.add_argument("--db", type=Path, required=True)
    evaluate_intents.add_argument("--order-intent-id")
    evaluate_intents.add_argument("--execution-mode", choices=[item.value for item in ExecutionMode], default="PAPER")
    evaluate_intents.add_argument("--allow-market-orders", action="store_true")
    evaluate_intents.add_argument("--max-risk-per-trade", type=float)
    evaluate_intents.add_argument("--max-position-notional", type=float)
    evaluate_intents.add_argument("--max-daily-loss", type=float)
    evaluate_intents.add_argument("--current-daily-loss", type=float, default=0)
    evaluate_intents.add_argument("--blocked-ticker", action="append", default=[])
    evaluate_intents.add_argument("--enable-sandbox-order", action="store_true")
    evaluate_intents.add_argument("--limit", type=int, default=100)
    paper_execute = subparsers.add_parser("paper-execute-approved-intents")
    paper_execute.add_argument("--db", type=Path, required=True)
    paper_execute.add_argument("--order-intent-id")
    paper_execute.add_argument("--fill-price", type=float)
    paper_execute.add_argument("--limit", type=int, default=100)
    paper_list = subparsers.add_parser("paper-executions-list")
    paper_list.add_argument("--db", type=Path, required=True)
    paper_list.add_argument("--ticker")
    paper_list.add_argument("--side", choices=["BUY", "SELL"])
    paper_list.add_argument("--limit", type=int, default=100)
    broker_health = subparsers.add_parser("broker-adapter-health")
    broker_health.add_argument("--db", type=Path, required=True)
    broker_health.add_argument("--broker", type=str.upper, choices=[item.value for item in BrokerId], default="MOCK")
    broker_health.add_argument(
        "--environment", choices=[item.value for item in BrokerEnvironment], default="LOCAL_MOCK"
    )
    broker_submit = subparsers.add_parser("broker-submit-mock-order")
    broker_submit.add_argument("--db", type=Path, required=True)
    broker_submit.add_argument("--order-intent-id", required=True)
    broker_submit.add_argument("--mock-fill-price", type=float)
    broker_submit.add_argument("--broker", type=str.upper, choices=[item.value for item in BrokerId], default="MOCK")
    broker_submit.add_argument(
        "--environment", choices=[item.value for item in BrokerEnvironment], default="LOCAL_MOCK"
    )
    broker_requests = subparsers.add_parser("broker-order-requests-list")
    broker_requests.add_argument("--db", type=Path, required=True)
    broker_requests.add_argument("--broker", type=str.upper, choices=[item.value for item in BrokerId])
    broker_requests.add_argument("--order-intent-id")
    broker_requests.add_argument("--limit", type=int, default=100)
    broker_receipts = subparsers.add_parser("broker-order-receipts-list")
    broker_receipts.add_argument("--db", type=Path, required=True)
    broker_receipts.add_argument("--broker", type=str.upper, choices=[item.value for item in BrokerId])
    broker_receipts.add_argument("--order-intent-id")
    broker_receipts.add_argument("--status", choices=[item.value for item in BrokerOrderStatus])
    broker_receipts.add_argument("--limit", type=int, default=100)

    kiwoom_health = subparsers.add_parser("kiwoom-readonly-health")
    kiwoom_health.add_argument("--db", type=Path, required=True)
    kiwoom_health.add_argument("--environment", choices=[item.value for item in KiwoomEnvironment], default="MOCK")
    kiwoom_endpoints = subparsers.add_parser("kiwoom-readonly-endpoints")
    kiwoom_endpoints.add_argument("--db", type=Path, required=True)
    kiwoom_endpoints.add_argument("--environment", choices=[item.value for item in KiwoomEnvironment], default="MOCK")
    for name in ("kiwoom-readonly-stock-info", "kiwoom-readonly-quote"):
        command = subparsers.add_parser(name)
        command.add_argument("--db", type=Path, required=True)
        command.add_argument("--ticker", required=True)
        command.add_argument("--environment", choices=[item.value for item in KiwoomEnvironment], default="MOCK")
    kiwoom_rankings = subparsers.add_parser("kiwoom-readonly-rankings")
    kiwoom_rankings.add_argument("--db", type=Path, required=True)
    kiwoom_rankings.add_argument("--rank-type", required=True)
    kiwoom_rankings.add_argument("--market", required=True)
    kiwoom_rankings.add_argument("--environment", choices=[item.value for item in KiwoomEnvironment], default="MOCK")
    kiwoom_flow = subparsers.add_parser("kiwoom-readonly-flow")
    kiwoom_flow.add_argument("--db", type=Path, required=True)
    kiwoom_flow.add_argument("--ticker")
    kiwoom_flow.add_argument("--market")
    kiwoom_flow.add_argument("--environment", choices=[item.value for item in KiwoomEnvironment], default="MOCK")
    kiwoom_chart = subparsers.add_parser("kiwoom-readonly-chart")
    kiwoom_chart.add_argument("--db", type=Path, required=True)
    kiwoom_chart.add_argument("--ticker", required=True)
    kiwoom_chart.add_argument("--interval", required=True)
    kiwoom_chart.add_argument("--count", type=int, default=100)
    kiwoom_chart.add_argument("--environment", choices=[item.value for item in KiwoomEnvironment], default="MOCK")
    kiwoom_condition_list = subparsers.add_parser("kiwoom-readonly-condition-list")
    kiwoom_condition_list.add_argument("--db", type=Path, required=True)
    kiwoom_condition_list.add_argument("--environment", choices=[item.value for item in KiwoomEnvironment], default="MOCK")
    kiwoom_condition_run = subparsers.add_parser("kiwoom-readonly-condition-run")
    kiwoom_condition_run.add_argument("--db", type=Path, required=True)
    kiwoom_condition_run.add_argument("--condition-id", required=True)
    kiwoom_condition_run.add_argument("--environment", choices=[item.value for item in KiwoomEnvironment], default="MOCK")
    kiwoom_mock_health = subparsers.add_parser("kiwoom-mock-execution-health")
    kiwoom_mock_health.add_argument("--db", type=Path, required=True)
    kiwoom_mock_submit = subparsers.add_parser("kiwoom-mock-submit-order")
    kiwoom_mock_submit.add_argument("--db", type=Path, required=True)
    kiwoom_mock_submit.add_argument("--order-intent-id", required=True)
    kiwoom_mock_submit.add_argument("--mock-fill-price", type=float)
    for name in ("kiwoom-mock-cancel-order", "kiwoom-mock-order-status"):
        command = subparsers.add_parser(name)
        command.add_argument("--db", type=Path, required=True)
        command.add_argument("--mock-order-id", required=True)
    for name in ("kiwoom-mock-order-requests-list", "kiwoom-mock-order-receipts-list"):
        command = subparsers.add_parser(name)
        command.add_argument("--db", type=Path, required=True)
        command.add_argument("--order-intent-id")
        command.add_argument("--limit", type=int, default=100)
    official_list = subparsers.add_parser("kiwoom-official-endpoints-list")
    official_list.add_argument("--class", dest="endpoint_class", choices=[item.value for item in KiwoomOfficialEndpointClass])
    official_list.add_argument("--category")
    official_list.add_argument("--runtime-allowed", action="store_true")
    official_list.add_argument("--limit", type=int, default=100)
    subparsers.add_parser("kiwoom-official-endpoints-validate")
    official_show = subparsers.add_parser("kiwoom-official-endpoint-show")
    official_show.add_argument("--api-id")
    official_show.add_argument("--path")
    for name in (
        "kiwoom-real-readonly-health",
        "kiwoom-real-readonly-stock-info",
        "kiwoom-real-readonly-quote",
        "kiwoom-real-readonly-rankings",
        "kiwoom-real-readonly-flow",
        "kiwoom-real-readonly-minute-chart",
        "kiwoom-real-readonly-daily-chart",
    ):
        command = subparsers.add_parser(name)
        command.add_argument("--db", type=Path, required=True)
        command.add_argument("--enable-real-network", action="store_true")
        command.add_argument("--environment", choices=[item.value for item in KiwoomRealNetworkEnvironment], default="MOCK")
        command.add_argument("--base-url", default="https://mockapi.kiwoom.com")
        command.add_argument("--credential-source", choices=[item.value for item in KiwoomCredentialSource], default="NONE")
        command.add_argument("--credential-file", type=Path)
        command.add_argument("--allow-auth-token-request", action="store_true")
        command.add_argument("--timeout-seconds", type=float, default=10)
        command.add_argument("--max-requests-per-run", type=int, default=5)
        if name in {"kiwoom-real-readonly-stock-info", "kiwoom-real-readonly-quote", "kiwoom-real-readonly-flow", "kiwoom-real-readonly-minute-chart", "kiwoom-real-readonly-daily-chart"}:
            command.add_argument("--ticker", required=True)
        if name == "kiwoom-real-readonly-rankings":
            command.add_argument("--market", default="0")
            command.add_argument("--sort-type", default="1")
    subparsers.add_parser("kiwoom-real-readonly-smoke-plan")
    smoke_run = subparsers.add_parser("kiwoom-real-readonly-smoke-run")
    smoke_run.add_argument("--db", type=Path, required=True)
    smoke_run.add_argument("--enable-real-network", action="store_true")
    smoke_run.add_argument("--environment", choices=[item.value for item in KiwoomRealNetworkEnvironment], default="MOCK")
    smoke_run.add_argument("--base-url", default="https://mockapi.kiwoom.com")
    smoke_run.add_argument("--credential-source", choices=[item.value for item in KiwoomCredentialSource], default="NONE")
    smoke_run.add_argument("--credential-file", type=Path)
    smoke_run.add_argument("--allow-auth-token-request", action="store_true")
    smoke_run.add_argument("--endpoint-id", action="append", default=[])
    smoke_run.add_argument("--endpoint-set", choices=["minimal"])
    smoke_run.add_argument("--dry-run", action="store_true")
    smoke_run.add_argument("--timeout-seconds", type=float, default=10)
    smoke_run.add_argument("--max-requests-per-run", type=int, default=3)
    smoke_reports = subparsers.add_parser("kiwoom-real-readonly-smoke-reports")
    smoke_reports.add_argument("--db", type=Path, required=True)
    smoke_reports.add_argument("--limit", type=int, default=100)
    smoke_show = subparsers.add_parser("kiwoom-real-readonly-smoke-show")
    smoke_show.add_argument("--db", type=Path, required=True)
    smoke_show.add_argument("--smoke-run-id", required=True)
    sandbox_health = subparsers.add_parser("kiwoom-sandbox-order-health")
    sandbox_health.add_argument("--db", type=Path, required=True)
    sandbox_plan = subparsers.add_parser("kiwoom-sandbox-order-plan")
    sandbox_plan.add_argument("--db", type=Path, required=True)
    sandbox_plan.add_argument("--order-intent-id", required=True)
    sandbox_submit = subparsers.add_parser("kiwoom-sandbox-order-submit")
    sandbox_submit.add_argument("--db", type=Path, required=True)
    sandbox_submit.add_argument("--order-intent-id", required=True)
    sandbox_submit.add_argument("--client-order-id")
    sandbox_submit.add_argument("--dry-run", action="store_true")
    for command in (sandbox_submit,):
        _add_sandbox_runtime_args(command)
    sandbox_cancel = subparsers.add_parser("kiwoom-sandbox-order-cancel")
    sandbox_cancel.add_argument("--db", type=Path, required=True)
    sandbox_cancel.add_argument("--broker-order-id", action="append", required=True)
    _add_sandbox_runtime_args(sandbox_cancel)
    sandbox_status = subparsers.add_parser("kiwoom-sandbox-order-status")
    sandbox_status.add_argument("--db", type=Path, required=True)
    sandbox_status.add_argument("--broker-order-id", action="append", required=True)
    for name in ("kiwoom-sandbox-order-requests", "kiwoom-sandbox-order-receipts"):
        command = subparsers.add_parser(name)
        command.add_argument("--db", type=Path, required=True)
        command.add_argument("--limit", type=int, default=100)
    sandbox_show = subparsers.add_parser("kiwoom-sandbox-order-show")
    sandbox_show.add_argument("--db", type=Path, required=True)
    sandbox_show.add_argument("--broker-order-id", required=True)
    sell_schema_verify = subparsers.add_parser("kiwoom-sandbox-sell-schema-verify")
    sell_schema_verify.add_argument("--db", type=Path, required=True)
    sell_schema_reports = subparsers.add_parser("kiwoom-sandbox-sell-schema-reports")
    sell_schema_reports.add_argument("--db", type=Path, required=True)
    sell_schema_reports.add_argument("--limit", type=int, default=100)
    sell_schema_show = subparsers.add_parser("kiwoom-sandbox-sell-schema-show")
    sell_schema_show.add_argument("--db", type=Path, required=True)
    sell_schema_show.add_argument("--report-id", required=True)
    sell_dry_run = subparsers.add_parser("kiwoom-sandbox-sell-dry-run")
    sell_dry_run.add_argument("--db", type=Path, required=True)
    sell_dry_run.add_argument("--order-intent-id", required=True)
    evidence_validate = subparsers.add_parser("kiwoom-official-sell-schema-evidence-validate")
    evidence_validate.add_argument("--evidence-file", type=Path, required=True)
    evidence_import = subparsers.add_parser("kiwoom-official-sell-schema-evidence-import")
    evidence_import.add_argument("--db", type=Path, required=True)
    evidence_import.add_argument("--evidence-file", type=Path, required=True)
    evidence_list = subparsers.add_parser("kiwoom-official-sell-schema-evidence-list")
    evidence_list.add_argument("--db", type=Path, required=True)
    evidence_list.add_argument("--limit", type=int, default=100)
    evidence_show = subparsers.add_parser("kiwoom-official-sell-schema-evidence-show")
    evidence_show.add_argument("--db", type=Path, required=True)
    evidence_show.add_argument("--evidence-id", required=True)
    evidence_review = subparsers.add_parser("kiwoom-official-sell-schema-evidence-review")
    evidence_review.add_argument("--db", type=Path, required=True)
    evidence_review.add_argument("--evidence-id", required=True)
    evidence_review.add_argument("--status", choices=[item.value for item in OfficialSellSchemaEvidenceReviewStatus], required=True)
    evidence_review.add_argument("--reviewed-by")
    evidence_review.add_argument("--notes")
    account_health = subparsers.add_parser("kiwoom-account-read-health")
    account_health.add_argument("--db", type=Path, required=True)
    account_plan = subparsers.add_parser("kiwoom-account-read-plan")
    account_plan.add_argument("--db", type=Path, required=True)
    account_plan.add_argument("--endpoint-id", action="append", default=[])
    _add_account_read_runtime_args(account_plan)
    account_run = subparsers.add_parser("kiwoom-account-read-run")
    account_run.add_argument("--db", type=Path, required=True)
    account_run.add_argument("--endpoint-id", action="append", default=[])
    account_run.add_argument("--dry-run", action="store_true")
    _add_account_read_runtime_args(account_run)
    account_reports = subparsers.add_parser("kiwoom-account-read-reports")
    account_reports.add_argument("--db", type=Path, required=True)
    account_reports.add_argument("--limit", type=int, default=100)
    for name in ("kiwoom-account-read-show", "kiwoom-account-read-reconcile-preview"):
        command = subparsers.add_parser(name)
        command.add_argument("--db", type=Path, required=True)
        command.add_argument("--run-id", required=True)
        if name == "kiwoom-account-read-reconcile-preview":
            command.add_argument("--kill-switch-inactive", action="store_true")
            command.add_argument("--local-ledger-file", type=Path)
            command.add_argument("--include-redacted-symbol-details", action="store_true")
    subparsers.add_parser("kiwoom-account-read-smoke-plan")
    account_smoke_run = subparsers.add_parser("kiwoom-account-read-smoke-run")
    account_smoke_run.add_argument("--db", type=Path, required=True)
    account_smoke_run.add_argument("--endpoint-id", action="append", default=[])
    account_smoke_run.add_argument("--endpoint-set", choices=["minimal"])
    account_smoke_run.add_argument("--dry-run", action="store_true")
    _add_account_read_runtime_args(account_smoke_run)
    account_smoke_reports = subparsers.add_parser("kiwoom-account-read-smoke-reports")
    account_smoke_reports.add_argument("--db", type=Path, required=True)
    account_smoke_reports.add_argument("--limit", type=int, default=100)
    account_smoke_show = subparsers.add_parser("kiwoom-account-read-smoke-show")
    account_smoke_show.add_argument("--db", type=Path, required=True)
    account_smoke_show.add_argument("--smoke-run-id", required=True)

    for name, id_option in (
        ("report-pipeline", "--pipeline-run-id"), ("report-scan", "--scan-run-id"),
        ("report-basket", "--basket-id"), ("report-policy-suite", "--suite-id"),
    ):
        report_command = subparsers.add_parser(name)
        report_command.add_argument("--db", type=Path, required=True)
        report_command.add_argument(id_option, required=True)
        report_command.add_argument("--format", choices=["json", "markdown"], default="json")
        report_command.add_argument("--language", choices=["en", "ko"], default="en")
        report_command.add_argument("--save", action="store_true")
        report_command.add_argument("--output-file", type=Path)
    reports = subparsers.add_parser("reports", help="List saved analysis reports.")
    reports.add_argument("--db", type=Path, required=True)
    reports.add_argument("--limit", type=int, default=50)
    report_show = subparsers.add_parser("report-show", help="Show a saved analysis report.")
    report_show.add_argument("--db", type=Path, required=True)
    report_show.add_argument("--report-id", required=True)

    context_report = subparsers.add_parser("agent-context-from-report")
    context_report.add_argument("--db", type=Path, required=True)
    context_report.add_argument("--report-id", required=True)
    context_report.add_argument("--save", action="store_true")
    context_pipeline = subparsers.add_parser("agent-context-from-pipeline")
    context_pipeline.add_argument("--db", type=Path, required=True)
    context_pipeline.add_argument("--pipeline-run-id", required=True)
    context_pipeline.add_argument("--save", action="store_true")
    agent_prompt = subparsers.add_parser("agent-prompt")
    agent_prompt.add_argument("--db", type=Path, required=True)
    agent_prompt.add_argument("--context-id", required=True)
    agent_prompt.add_argument("--language", choices=["en", "ko"], default="en")
    agent_prompt.add_argument("--save", action="store_true")
    agent_brief = subparsers.add_parser("agent-brief")
    agent_brief.add_argument("--db", type=Path, required=True)
    agent_brief.add_argument("--context-id", required=True)
    agent_brief.add_argument("--save", action="store_true")
    agent_run = subparsers.add_parser("agent-run-local")
    agent_run.add_argument("--db", type=Path, required=True)
    agent_run.add_argument("--prompt-id", required=True)
    agent_run.add_argument("--backend", choices=["dry-run", "ollama-local", "openai-compat-local", "disabled"], default="dry-run")
    agent_run.add_argument("--model")
    agent_run.add_argument("--endpoint-url")
    agent_run.add_argument("--temperature", type=float, default=0.2)
    agent_run.add_argument("--max-tokens", type=int)
    agent_run.add_argument("--save", action="store_true")
    for name in ("agent-contexts", "agent-prompts", "agent-briefs", "local-llm-responses"):
        item = subparsers.add_parser(name)
        item.add_argument("--db", type=Path, required=True)
        item.add_argument("--limit", type=int, default=50)
    subparsers.add_parser("agent-tools")

    for name, id_option in (
        ("notify-pipeline", "--pipeline-run-id"), ("notify-report", "--report-id"),
        ("notify-brief", "--brief-id"), ("notify-local-response", "--response-id"),
    ):
        notification = subparsers.add_parser(name)
        notification.add_argument("--db", type=Path, required=True)
        notification.add_argument(id_option, required=True)
        add_notification_args(notification)
    digest = subparsers.add_parser("notify-digest")
    digest.add_argument("--db", type=Path, required=True)
    digest.add_argument("--as-of-date", type=date.fromisoformat, required=True)
    digest.add_argument("--include-local-llm-responses", action="store_true")
    add_notification_args(digest)
    notification_runs = subparsers.add_parser("notification-runs")
    notification_runs.add_argument("--db", type=Path, required=True)
    notification_runs.add_argument("--limit", type=int, default=50)
    notification_show = subparsers.add_parser("notification-show")
    notification_show.add_argument("--db", type=Path, required=True)
    notification_show.add_argument("--notification-run-id", required=True)
    notifications = subparsers.add_parser("notifications")
    notifications.add_argument("--db", type=Path, required=True)
    notifications.add_argument("--source-id")
    notifications.add_argument("--limit", type=int, default=100)

    dashboard_overview = subparsers.add_parser("dashboard-overview")
    dashboard_overview.add_argument("--db", type=Path, required=True)
    dashboard_overview.add_argument("--output-file", type=Path, required=True)
    dashboard_overview.add_argument("--as-of-date", type=date.fromisoformat)
    dashboard_overview.add_argument("--limit", type=int, default=20)
    dashboard_overview.add_argument("--save", action="store_true")
    dashboard_pipeline = subparsers.add_parser("dashboard-pipeline")
    dashboard_pipeline.add_argument("--db", type=Path, required=True)
    dashboard_pipeline.add_argument("--pipeline-run-id", required=True)
    dashboard_pipeline.add_argument("--output-file", type=Path, required=True)
    dashboard_pipeline.add_argument("--save", action="store_true")
    dashboard_daily = subparsers.add_parser("dashboard-daily")
    dashboard_daily.add_argument("--db", type=Path, required=True)
    dashboard_daily.add_argument("--as-of-date", type=date.fromisoformat, required=True)
    dashboard_daily.add_argument("--output-file", type=Path, required=True)
    dashboard_daily.add_argument("--save", action="store_true")
    dashboard_policy = subparsers.add_parser("dashboard-policy")
    dashboard_policy.add_argument("--db", type=Path, required=True)
    dashboard_policy.add_argument("--output-file", type=Path, required=True)
    dashboard_policy.add_argument("--limit", type=int, default=20)
    dashboard_policy.add_argument("--save", action="store_true")
    dashboard_builds = subparsers.add_parser("dashboard-builds")
    dashboard_builds.add_argument("--db", type=Path, required=True)
    dashboard_builds.add_argument("--limit", type=int, default=50)
    dashboard_show = subparsers.add_parser("dashboard-show")
    dashboard_show.add_argument("--db", type=Path, required=True)
    dashboard_show.add_argument("--dashboard-id", required=True)

    demo = subparsers.add_parser("run-local-demo")
    demo.add_argument("--db", type=Path, required=True)
    demo.add_argument("--as-of-date", type=date.fromisoformat, required=True)
    demo.add_argument("--output-dir", type=Path, required=True)
    demo.add_argument("--ticker", action="append")
    demo.add_argument("--account-equity", type=float, default=10_000)
    demo.add_argument("--cash-available", type=float, default=5_000)
    demo.add_argument("--horizon-days", type=int, default=10)
    demo.add_argument("--no-save-intermediate", action="store_true")
    smoke = subparsers.add_parser("system-smoke")
    smoke.add_argument("--db", type=Path, required=True)
    smoke.add_argument("--output-dir", type=Path, required=True)
    smoke.add_argument("--as-of-date", type=date.fromisoformat)
    subparsers.add_parser("release-check")

    backtest = subparsers.add_parser("backtest", help="Run backtests for saved risk evaluations.")
    backtest.add_argument("--db", type=Path, default=Path("data/stock_risk_mcp.sqlite3"))
    backtest.add_argument("--horizon-days", type=int, required=True)

    backtest_summary = subparsers.add_parser("backtest-summary", help="Summarize saved backtest results.")
    backtest_summary.add_argument("--db", type=Path, default=Path("data/stock_risk_mcp.sqlite3"))

    report = subparsers.add_parser("report", help="Analyze policy effectiveness from backtest results.")
    report.add_argument("--db", type=Path, default=Path("data/stock_risk_mcp.sqlite3"))

    reasons = subparsers.add_parser("reasons", help="Show normalized reasons for a risk evaluation.")
    reasons.add_argument("--db", type=Path, default=Path("data/stock_risk_mcp.sqlite3"))
    reasons.add_argument("--evaluation-id", type=int, required=True)

    sources = subparsers.add_parser("sources", help="List registered data sources.")
    sources.add_argument("--db", type=Path, default=Path("data/stock_risk_mcp.sqlite3"))

    ingestion_runs = subparsers.add_parser("ingestion-runs", help="List recent ingestion runs.")
    ingestion_runs.add_argument("--db", type=Path, default=Path("data/stock_risk_mcp.sqlite3"))
    ingestion_runs.add_argument("--limit", type=int, default=50)

    analyze_indicators = subparsers.add_parser("analyze-indicators", help="Analyze indicators from local price history.")
    add_indicator_args(analyze_indicators, require_db=False)

    analyze_and_save = subparsers.add_parser(
        "analyze-indicators-and-save",
        help="Analyze indicators from local price history and save them to SQLite.",
    )
    add_indicator_args(analyze_and_save, require_db=True)

    analyze_setup = subparsers.add_parser("analyze-setup", help="Grade an ABC setup from local price history.")
    add_indicator_args(analyze_setup, require_db=False, support_policy=True)

    create_plan = subparsers.add_parser("create-trade-plan", help="Create a paper trade plan from local price history.")
    add_trade_plan_args(create_plan, require_db=False)

    create_plan_and_save = subparsers.add_parser(
        "create-trade-plan-and-save",
        help="Create and save a paper trade plan from local price history.",
    )
    add_trade_plan_args(create_plan_and_save, require_db=True)

    build_basket_parser = subparsers.add_parser(
        "build-basket-from-trade-plans", help="Build a paper basket from recent saved trade plans."
    )
    add_basket_args(build_basket_parser)

    build_basket_save = subparsers.add_parser("build-basket-and-save", help="Build and save a paper basket.")
    add_basket_args(build_basket_save)

    show_basket = subparsers.add_parser("show-basket", help="Show a saved basket plan.")
    show_basket.add_argument("--db", type=Path, required=True)
    show_basket.add_argument("--basket-id", required=True)

    paper_trade_basket = subparsers.add_parser("paper-trade-basket", help="Backtest a saved basket using DB prices.")
    add_paper_trade_basket_args(paper_trade_basket)

    paper_trade_file = subparsers.add_parser(
        "paper-trade-basket-from-file", help="Backtest a saved basket using a local price history file."
    )
    add_paper_trade_basket_args(paper_trade_file)
    paper_trade_file.add_argument("--price-history-file", type=Path, required=True)

    paper_trades = subparsers.add_parser("paper-trades", help="List saved paper trades for a basket.")
    paper_trades.add_argument("--db", type=Path, required=True)
    paper_trades.add_argument("--basket-id", required=True)

    basket_performance = subparsers.add_parser("basket-performance", help="Summarize saved basket backtests.")
    basket_performance.add_argument("--db", type=Path, required=True)

    strategy_init = subparsers.add_parser("strategy-init", help="Create or show the default active strategy policy.")
    strategy_init.add_argument("--db", type=Path, required=True)

    strategy_active = subparsers.add_parser("strategy-active", help="Show the active strategy policy.")
    strategy_active.add_argument("--db", type=Path, required=True)

    strategy_propose = subparsers.add_parser("strategy-propose", help="Create deterministic draft strategy policies.")
    strategy_propose.add_argument("--db", type=Path, required=True)
    strategy_propose.add_argument("--n", type=int, required=True)

    strategy_evaluate = subparsers.add_parser(
        "strategy-evaluate", help="Evaluate a policy using common stored basket outcomes."
    )
    strategy_evaluate.add_argument("--db", type=Path, required=True)
    strategy_evaluate.add_argument("--policy-id", required=True)
    strategy_evaluate.add_argument("--version", required=True)
    strategy_evaluate.add_argument("--horizon-days", type=int, required=True)

    strategy_experiments = subparsers.add_parser("strategy-experiments", help="List strategy experiments.")
    strategy_experiments.add_argument("--db", type=Path, required=True)

    strategy_policies = subparsers.add_parser("strategy-policies", help="List strategy policies.")
    strategy_policies.add_argument("--db", type=Path, required=True)

    replay_basket = subparsers.add_parser("replay-snapshot-from-basket", help="Snapshot an existing saved basket.")
    replay_basket.add_argument("--db", type=Path, required=True)
    replay_basket.add_argument("--basket-id", required=True)
    replay_basket.add_argument("--as-of-date", type=date.fromisoformat)

    replay_recent = subparsers.add_parser(
        "replay-snapshot-from-recent-trade-plans",
        help="Build and store replay snapshots from recent saved trade plans.",
    )
    replay_recent.add_argument("--db", type=Path, required=True)
    replay_recent.add_argument("--account-equity", type=float, required=True)
    replay_recent.add_argument("--cash-available", type=float, required=True)
    replay_recent.add_argument("--max-candidates", type=int, default=10)
    replay_recent.add_argument("--horizon-days", type=int, default=10)
    replay_recent.add_argument("--as-of-date", type=date.fromisoformat)
    replay_recent.add_argument("--save-basket", action="store_true")
    add_strategy_policy_args(replay_recent)

    replay_runs = subparsers.add_parser("replay-runs", help="List replay snapshot runs.")
    replay_runs.add_argument("--db", type=Path, required=True)
    replay_runs.add_argument("--limit", type=int, default=50)

    replay_show = subparsers.add_parser("replay-show", help="Show a replay snapshot dataset.")
    replay_show.add_argument("--db", type=Path, required=True)
    replay_show.add_argument("--run-id", required=True)

    policy_replay = subparsers.add_parser("policy-replay", help="Run FULL_POLICY_REPLAY for an explicit policy.")
    add_policy_replay_args(policy_replay)
    policy_replay.add_argument("--policy-id", required=True)
    policy_replay.add_argument("--policy-version", required=True)

    policy_replay_active = subparsers.add_parser("policy-replay-active", help="Run FULL_POLICY_REPLAY for active policy.")
    add_policy_replay_args(policy_replay_active)

    policy_replay_results = subparsers.add_parser("policy-replay-results", help="List FULL_POLICY_REPLAY results.")
    policy_replay_results.add_argument("--db", type=Path, required=True)
    policy_replay_results.add_argument("--replay-run-id")
    policy_replay_results.add_argument("--limit", type=int, default=50)

    policy_compare = subparsers.add_parser("policy-compare", help="Compare baseline and candidate FULL_POLICY_REPLAY.")
    add_policy_replay_args(policy_compare, storage_options=False)
    policy_compare.add_argument("--baseline-policy-id", required=True)
    policy_compare.add_argument("--baseline-policy-version", required=True)
    policy_compare.add_argument("--candidate-policy-id", required=True)
    policy_compare.add_argument("--candidate-policy-version", required=True)

    suite = subparsers.add_parser("policy-evaluate-suite", help="Evaluate policies across multiple ReplayRuns.")
    add_policy_replay_args(suite, storage_options=False, include_run_id=False)
    suite.add_argument("--replay-run-id", action="append")
    suite.add_argument("--baseline-policy-id", required=True)
    suite.add_argument("--baseline-policy-version", required=True)
    suite.add_argument("--candidate-policy-id", required=True)
    suite.add_argument("--candidate-policy-version", required=True)
    suite.add_argument("--min-replay-runs", type=int, default=5)
    suite.add_argument("--min-completed-replays", type=int, default=3)
    for name in ("policy-evaluation-suites", "policy-promotion-proposals"):
        item = subparsers.add_parser(name)
        item.add_argument("--db", type=Path, required=True)
    proposal = subparsers.add_parser("policy-propose-promotion")
    proposal.add_argument("--db", type=Path, required=True)
    proposal.add_argument("--suite-id", required=True)
    for name in ("policy-approve", "policy-activate"):
        item = subparsers.add_parser(name)
        item.add_argument("--db", type=Path, required=True)
        item.add_argument("--policy-id", required=True)
        item.add_argument("--policy-version", required=True)

    scan_candidates = subparsers.add_parser("scan-candidates", help="Build a local as-of candidate universe.")
    scan_candidates.add_argument("--db", type=Path, required=True)
    scan_candidates.add_argument("--as-of-date", type=date.fromisoformat, required=True)
    scan_candidates.add_argument("--price-history-file", type=Path)
    scan_candidates.add_argument("--ticker", action="append")
    scan_candidates.add_argument("--max-candidates", type=int, default=100)
    scan_candidates.add_argument("--min-avg-dollar-volume-20d", type=float, default=10_000_000)
    scan_candidates.add_argument("--min-volume-spike-ratio", type=float, default=1.5)
    scan_candidates.add_argument("--save", action="store_true")
    scan_candidates.add_argument("--save-signals", action="store_true")
    scan_candidates.add_argument("--ignore-db-signals", action="store_true")
    add_signal_file_args(scan_candidates)
    add_strategy_policy_args(scan_candidates)

    ingest_signals = subparsers.add_parser("ingest-signals", help="Normalize and save local signal files.")
    ingest_signals.add_argument("--db", type=Path, required=True)
    ingest_signals.add_argument("--as-of-date", type=date.fromisoformat, required=True)
    add_signal_file_args(ingest_signals)

    signals = subparsers.add_parser("signals", help="List normalized ticker signals.")
    signals.add_argument("--db", type=Path, required=True)
    signals.add_argument("--ticker")
    signals.add_argument("--as-of-date", type=date.fromisoformat)
    signals.add_argument("--limit", type=int, default=200)

    scan_runs = subparsers.add_parser("scan-runs", help="List saved candidate scan runs.")
    scan_runs.add_argument("--db", type=Path, required=True)
    scan_runs.add_argument("--limit", type=int, default=50)

    scan_results = subparsers.add_parser("scan-results", help="List saved candidate scan results.")
    scan_results.add_argument("--db", type=Path, required=True)
    scan_results.add_argument("--scan-run-id", required=True)
    scan_results.add_argument("--decision", choices=["INCLUDE", "WATCH", "EXCLUDE"])
    scan_results.add_argument("--limit", type=int, default=200)

    scan_to_basket = subparsers.add_parser("scan-to-basket", help="Build a basket from saved scan results.")
    scan_to_basket.add_argument("--scan-run-id", required=True)
    scan_to_basket.add_argument("--include-watch", action="store_true")
    scan_to_basket.add_argument("--save-basket", action="store_true")
    add_basket_args(scan_to_basket)

    scan_to_replay = subparsers.add_parser("scan-to-replay-snapshot", help="Snapshot saved scan candidates.")
    scan_to_replay.add_argument("--db", type=Path, required=True)
    scan_to_replay.add_argument("--scan-run-id", required=True)
    scan_to_replay.add_argument("--as-of-date", type=date.fromisoformat, required=True)
    scan_to_replay.add_argument("--include-watch", action="store_true")

    run_scan_pipeline = subparsers.add_parser("run-scan-pipeline", help="Run the persisted one-shot scan pipeline.")
    add_operational_scan_args(run_scan_pipeline)

    run_paper_pipeline = subparsers.add_parser("run-paper-pipeline", help="Run the local paper basket pipeline.")
    add_operational_scan_args(run_paper_pipeline)
    run_paper_pipeline.add_argument("--account-equity", type=float, required=True)
    run_paper_pipeline.add_argument("--cash-available", type=float, required=True)
    run_paper_pipeline.add_argument("--horizon-days", type=int, required=True)
    run_paper_pipeline.add_argument("--include-watch", action="store_true")
    run_paper_pipeline.add_argument("--save-basket", action="store_true")
    run_paper_pipeline.add_argument("--no-paper-trade", action="store_true")
    run_paper_pipeline.add_argument("--no-replay-snapshot", action="store_true")
    add_pipeline_notification_args(run_paper_pipeline)
    add_pipeline_dashboard_args(run_paper_pipeline)
    add_fx_pipeline_args(run_paper_pipeline)

    run_policy_pipeline = subparsers.add_parser("run-policy-evaluation-pipeline", help="Run policy replay evaluation.")
    add_policy_replay_args(run_policy_pipeline, storage_options=False, include_run_id=False)
    run_policy_pipeline.add_argument("--replay-run-id", action="append")
    run_policy_pipeline.add_argument("--baseline-policy-id", required=True)
    run_policy_pipeline.add_argument("--baseline-policy-version", required=True)
    run_policy_pipeline.add_argument("--candidate-policy-id", required=True)
    run_policy_pipeline.add_argument("--candidate-policy-version", required=True)

    pipeline_runs = subparsers.add_parser("pipeline-runs", help="List operational pipeline runs.")
    pipeline_runs.add_argument("--db", type=Path, required=True)
    pipeline_runs.add_argument("--limit", type=int, default=50)
    pipeline_show = subparsers.add_parser("pipeline-show", help="Show an operational pipeline run.")
    pipeline_show.add_argument("--db", type=Path, required=True)
    pipeline_show.add_argument("--pipeline-run-id", required=True)
    pipeline_alerts = subparsers.add_parser("alerts", help="List operational pipeline alerts.")
    pipeline_alerts.add_argument("--db", type=Path, required=True)
    pipeline_alerts.add_argument("--pipeline-run-id")
    pipeline_alerts.add_argument("--limit", type=int, default=100)

    watch = subparsers.add_parser("watch-loop", help="Run an explicit bounded local paper watch loop.")
    add_operational_scan_args(watch)
    watch.add_argument("--account-equity", type=float, required=True)
    watch.add_argument("--cash-available", type=float, required=True)
    watch.add_argument("--horizon-days", type=int, default=10)
    watch.add_argument("--interval-seconds", type=float, required=True)
    watch.add_argument("--max-iterations", type=int)
    watch.add_argument("--include-watch", action="store_true")
    watch.add_argument("--save-basket", action="store_true")
    watch.add_argument("--no-paper-trade", action="store_true")
    add_pipeline_notification_args(watch)
    add_fx_pipeline_args(watch)
    add_pipeline_dashboard_args(watch)
    return parser


def _add_sandbox_runtime_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--enable-real-network", action="store_true")
    parser.add_argument("--enable-sandbox-order", action="store_true")
    parser.add_argument("--environment", choices=[item.value for item in KiwoomRealNetworkEnvironment], default="MOCK")
    parser.add_argument("--base-url", default="https://mockapi.kiwoom.com")
    parser.add_argument("--credential-source", choices=[item.value for item in KiwoomCredentialSource], default="NONE")
    parser.add_argument("--credential-file", type=Path)
    parser.add_argument("--allow-auth-token-request", action="store_true")
    parser.add_argument("--timeout-seconds", type=float, default=10)


def _sandbox_config_from_args(args) -> KiwoomSandboxOrderConfig:
    return KiwoomSandboxOrderConfig(
        enable_real_network=args.enable_real_network, enable_sandbox_order=args.enable_sandbox_order,
        environment=KiwoomRealNetworkEnvironment(args.environment), base_url=args.base_url,
        credential_source=KiwoomCredentialSource(args.credential_source), credential_file=args.credential_file,
        allow_auth_token_request=args.allow_auth_token_request, timeout_seconds=args.timeout_seconds,
    )


def _sandbox_credential_loader(source, credential_file):
    env = {
        key: value for key in ("KIWOOM_APPKEY", "KIWOOM_SECRETKEY", "KIWOOM_ACCOUNT_NUMBER")
        if (value := os.environ.get(key)) is not None
    } if source == KiwoomCredentialSource.ENV else {}
    return load_kiwoom_credentials(source, credential_file, env)


def _account_read_config_from_args(args) -> KiwoomAccountReadConfig:
    return KiwoomAccountReadConfig(
        enable_real_network=args.enable_real_network,
        enable_account_read=args.enable_account_read,
        environment=KiwoomRealNetworkEnvironment(args.environment),
        base_url=args.base_url,
        credential_source=KiwoomCredentialSource(args.credential_source),
        credential_file=args.credential_file,
        allow_auth_token_request=args.allow_auth_token_request,
        account_confirmed=args.confirm_account,
        account_fingerprint=args.account_fingerprint,
        acknowledged_account_data_read=args.i_understand_this_can_read_account_data,
        kill_switch_inactive=args.kill_switch_inactive,
        timeout_seconds=args.timeout_seconds,
    )


def _account_read_credential_loader(source, credential_file):
    return _sandbox_credential_loader(source, credential_file)


def add_proposal_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--ticker", required=True, help="Ticker symbol, e.g. SAFE")
    parser.add_argument("--side", required=True, choices=["BUY", "SELL"], help="Trade side")
    parser.add_argument("--confidence", required=True, type=float, help="LLM confidence from 0 to 1")
    parser.add_argument("--reason", required=True, help="Reason supplied by the LLM or client")
    parser.add_argument("--holding-days", type=int, default=30, help="Intended holding period in days")
    parser.add_argument("--policy", type=Path, default=None, help="Optional path to a policy YAML file")
    parser.add_argument("--price-history-file", type=Path, default=None, help="CSV/JSON price history file for market data")


def add_indicator_args(parser: argparse.ArgumentParser, require_db: bool, support_policy: bool = False) -> None:
    parser.add_argument("--ticker", required=True, help="Ticker symbol")
    parser.add_argument("--price-history-file", type=Path, default=None, help="CSV/JSON price history file")
    parser.add_argument("--db", type=Path, required=require_db, default=None if not require_db else None)
    parser.add_argument("--use-db-price-history", action="store_true", help="Use the SQLite price_history table")
    if support_policy:
        add_strategy_policy_args(parser)


def add_trade_plan_args(parser: argparse.ArgumentParser, require_db: bool) -> None:
    add_indicator_args(parser, require_db=require_db, support_policy=True)
    parser.add_argument("--account-equity", type=float, required=True)
    parser.add_argument("--cash-available", type=float, required=True)
    parser.add_argument("--max-single-trade-loss-pct", type=float, default=0.25)
    parser.add_argument("--max-position-pct", type=float, default=5.0)


def add_basket_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--db", type=Path, required=True)
    parser.add_argument("--account-equity", type=float, required=True)
    parser.add_argument("--cash-available", type=float, required=True)
    parser.add_argument("--max-candidates", type=int, default=10)
    parser.add_argument("--min-candidates", type=int, default=3)
    parser.add_argument("--max-basket-loss-pct", type=float, default=1.0)
    parser.add_argument("--max-basket-notional-pct", type=float, default=25.0)
    parser.add_argument("--max-same-sector-count", type=int, default=3)
    parser.add_argument("--max-same-theme-count", type=int, default=3)
    add_strategy_policy_args(parser)


def add_strategy_policy_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--use-active-policy", action="store_true")
    parser.add_argument("--policy-id")
    parser.add_argument("--policy-version")


def add_signal_file_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--news-signal-file", type=Path)
    parser.add_argument("--dilution-signal-file", type=Path)
    parser.add_argument("--toss-signal-file", type=Path)
    parser.add_argument("--flow-signal-file", type=Path)


def add_operational_scan_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--db", type=Path, required=True)
    parser.add_argument("--as-of-date", type=date.fromisoformat, required=True)
    parser.add_argument("--price-history-file", type=Path)
    parser.add_argument("--ignore-db-signals", action="store_true")
    add_signal_file_args(parser)
    add_strategy_policy_args(parser)


def add_notification_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--channel", choices=["console", "local-file", "mock", "disabled"], default="console")
    parser.add_argument("--output-file", type=Path)
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument("--min-severity", choices=["info", "warning", "high", "critical"], default="info")
    parser.add_argument("--save", action="store_true")


def add_pipeline_notification_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--notify", action="store_true")
    parser.add_argument("--notification-channel", choices=["console", "local-file", "mock", "disabled"], default="console")
    parser.add_argument("--notification-output-file", type=Path)
    parser.add_argument("--notification-min-severity", choices=["info", "warning", "high", "critical"], default="info")


def add_pipeline_dashboard_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--build-dashboard", action="store_true")
    parser.add_argument("--dashboard-output-file", type=Path)


def add_fx_pipeline_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--account-currency", choices=["KRW", "USD"], default="USD")
    parser.add_argument("--trading-currency", choices=["KRW", "USD"], default="USD")
    parser.add_argument("--fx-rate", type=float)
    parser.add_argument("--fx-source-name", default="manual")
    parser.add_argument("--max-fx-staleness-days", type=int, default=7)


def add_http_provider_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--provider-config-file", type=Path)
    parser.add_argument("--enable-network", action="store_true")
    parser.add_argument("--allowed-host", action="append", default=None)


def add_normalizer_column_args(parser: argparse.ArgumentParser) -> None:
    for name in (
        "ticker", "date", "open", "high", "low", "close", "volume", "observed-at",
        "title", "summary", "event-type", "sentiment", "materiality", "severity",
        "details", "foreign-net-buy", "institution-net-buy", "foreign-ownership-change",
        "flow-window-days", "base-currency", "quote-currency", "rate", "source-name",
    ):
        parser.add_argument(f"--{name}-column")


def _connector_registry_and_names(args: argparse.Namespace):
    registry = default_connector_registry()
    names = list(args.connector)
    if args.provider_config_file:
        configs = load_provider_configs(args.provider_config_file)
        register_http_providers(registry, configs, args.enable_network, args.allowed_host)
        names.extend(config.provider_name for config in configs if config.provider_name not in names)
    return registry, names


def add_paper_trade_basket_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--db", type=Path, required=True)
    parser.add_argument("--basket-id", required=True)
    parser.add_argument("--horizon-days", type=int, required=True)


def _add_account_read_runtime_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--enable-real-network", action="store_true")
    parser.add_argument("--enable-account-read", action="store_true")
    parser.add_argument("--environment", choices=[item.value for item in KiwoomRealNetworkEnvironment], default="MOCK")
    parser.add_argument("--base-url", default="https://mockapi.kiwoom.com")
    parser.add_argument("--credential-source", choices=[item.value for item in KiwoomCredentialSource], default="NONE")
    parser.add_argument("--credential-file", type=Path)
    parser.add_argument("--allow-auth-token-request", action="store_true")
    parser.add_argument("--confirm-account", action="store_true")
    parser.add_argument("--account-fingerprint")
    parser.add_argument("--i-understand-this-can-read-account-data", action="store_true")
    parser.add_argument("--kill-switch-inactive", action="store_true")
    parser.add_argument("--timeout-seconds", type=float, default=10)


def add_policy_replay_args(
    parser: argparse.ArgumentParser, storage_options: bool = True, include_run_id: bool = True
) -> None:
    parser.add_argument("--db", type=Path, required=True)
    if include_run_id:
        parser.add_argument("--replay-run-id", required=True)
    parser.add_argument("--horizon-days", type=int, required=True)
    parser.add_argument("--account-equity", type=float, required=True)
    parser.add_argument("--cash-available", type=float, required=True)
    parser.add_argument("--price-history-file", type=Path)
    if storage_options:
        parser.add_argument("--save-intermediate", action="store_true")
        parser.add_argument("--save-basket", action="store_true")


def main(argv: list[str] | None = None) -> None:
    args_list = sys.argv[1:] if argv is None else argv
    commands = {
        "evaluate-and-save",
        "ingest-nasdaq-noncompliant",
        "check-compliance",
        "ingest-prices",
        "import-data",
        "import-runs",
        "import-show",
        "fx-rates",
        "fx-latest",
        "fx-convert",
        "normalize-file",
        "normalize-run",
        "normalize-and-import",
        "normalize-runs",
        "normalize-show",
        "connectors",
        "run-connectors",
        "run-connectors-and-import",
        "validate-provider-config",
        "run-http-connector",
        "connector-runs",
        "connector-show",
        "run-price-provider-pack",
        "run-fx-provider-pack",
        "run-price-fx-provider-pack",
        "run-news-provider-pack",
        "run-dilution-provider-pack",
        "run-flow-provider-pack",
        "provider-pack-runs",
        "provider-pack-show",
        "run-realtime-monitor",
        "watchlist-list",
        "realtime-runs",
        "realtime-show",
        "local-ledger-position-upsert",
        "local-ledger-positions",
        "local-ledger-snapshot",
        "local-ledger-transactions",
        "sell-safety-check",
        "sell-safety-decisions",
        "sell-safety-show",
        "strategy-run",
        "strategy-decisions",
        "strategy-decision-show",
        "strategy-candidates",
        "strategy-candidate-show",
        "strategy-create-order-intent-draft",
        "local-llm-health",
        "strategy-backtest-run",
        "strategy-backtest-reports",
        "strategy-backtest-show",
        "technical-evidence-run",
        "technical-evidence-show",
        "market-discovery-run",
        "market-discovery-show",
        "llm-feature-store-run",
        "llm-signal-evaluate",
        "llm-signal-evaluation-show",
        "trade-plan-run",
        "trade-plan-show",
        "paper-eval-run",
        "paper-eval-show",
        "policy-replay-run",
        "policy-replay-show",
        "local-llm-advisory-run",
        "local-llm-advisory-show",
        "local-model-candidates-list",
        "local-model-runtime-check",
        "local-model-advisory-dry-run",
        "local-model-benchmark-run",
        "local-model-benchmark-show",
        "local-model-candidates-rank",
        "local-model-decision-report",
        "local-model-benchmark-pack-validate",
        "strategy-track-profile-validate",
        "strategy-track-profile-show",
        "strategy-track-compare",
        "market-profit-profile-validate",
        "market-profit-estimate",
        "market-profit-compare-tracks",
        "market-profit-break-even",
        "domestic-realtime-profile-validate",
        "domestic-realtime-plan-show",
        "domestic-realtime-event-normalize",
        "domestic-realtime-quality-report",
        "domestic-scanner-config-validate",
        "domestic-scanner-candidates",
        "domestic-scanner-watchlist-plan",
        "domestic-scanner-quality-report",
        "domestic-candidate-evaluation-config-validate",
        "domestic-candidate-evaluate",
        "domestic-candidate-evaluation-gap-report",
        "domestic-candidate-evaluation-safety-report",
        "domestic-replay-config-validate",
        "domestic-replay-run",
        "domestic-replay-metrics-report",
        "domestic-replay-promotion-readiness",
        "domestic-calibration-config-validate",
        "domestic-calibration-run",
        "domestic-policy-compare",
        "domestic-promotion-gate-report",
        "domestic-paper-shadow-config-validate",
        "domestic-paper-shadow-journal-build",
        "domestic-paper-shadow-review-report",
        "domestic-paper-shadow-safety-report",
        "domestic-shadow-outcome-config-validate",
        "domestic-shadow-outcome-label",
        "domestic-shadow-outcome-review-report",
        "domestic-shadow-outcome-safety-report",
        "domestic-shadow-advisory-context-config-validate",
        "domestic-shadow-advisory-context-build",
        "domestic-shadow-advisory-context-validate",
        "domestic-shadow-advisory-context-gap-report",
        "domestic-shadow-advisory-context-safety-report",
        "domestic-distillation-dataset-config-validate",
        "domestic-distillation-dataset-build",
        "domestic-distillation-dataset-validate",
        "domestic-distillation-dataset-gap-report",
        "domestic-distillation-dataset-safety-report",
        "domestic-market-regime-config-validate",
        "domestic-market-regime-classify",
        "domestic-market-regime-report",
        "domestic-market-regime-gap-report",
        "domestic-market-regime-safety-report",
        "domestic-regime-aware-integration-config-validate",
        "domestic-regime-aware-integration-build",
        "domestic-regime-aware-integration-report",
        "domestic-regime-aware-gap-report",
        "domestic-regime-aware-safety-report",
        "prompt-pack-validate",
        "prompt-pack-show",
        "prompt-pack-coverage-report",
        "prompt-pack-gap-report",
        "historical-data-config-validate",
        "historical-data-manifest-build",
        "historical-data-validate",
        "historical-data-quality-report",
        "historical-data-gap-report",
        "historical-calendar-config-validate",
        "historical-calendar-validate",
        "historical-calendar-gap-report",
        "historical-replay-bridge-build",
        "historical-replay-event-stream",
        "historical-replay-window-report",
        "historical-scanner-replay-input",
        "historical-replay-gap-report",
        "historical-replay-safety-report",
        "historical-outcome-observe",
        "historical-outcome-label-report",
        "historical-outcome-gap-report",
        "historical-outcome-safety-report",
        "historical-dataset-assemble",
        "historical-dataset-export-manifest",
        "historical-dataset-quality-report",
        "historical-dataset-gap-report",
        "historical-dataset-safety-report",
        "historical-dataset-validate",
        "historical-dataset-leakage-audit",
        "historical-dataset-split-manifest",
        "historical-dataset-coverage-report",
        "historical-dataset-label-distribution",
        "historical-dataset-readiness-report",
        "historical-dataset-split-quality-report",
        "historical-dataset-imbalance-report",
        "historical-dataset-baseline-evaluation",
        "historical-dataset-readiness-safety-report",
        "historical-model-training-plan-check",
        "historical-model-train-sandbox",
        "historical-model-evaluation-report",
        "historical-model-artifact-manifest",
        "historical-model-training-safety-report",
        "historical-model-experiment-register",
        "historical-model-experiment-compare",
        "historical-model-risk-review",
        "historical-model-promotion-block-report",
        "historical-model-experiment-safety-report",
        "historical-signal-candidate-build",
        "historical-signal-candidate-report",
        "historical-signal-candidate-safety-report",
        "historical-signal-candidate-gap-report",
        "historical-paper-trading-run",
        "historical-paper-trading-performance-report",
        "historical-paper-trading-safety-report",
        "historical-paper-trading-gap-report",
        "broker-mock-adapter-boundary-run",
        "broker-mock-adapter-capability-report",
        "broker-mock-adapter-order-boundary-report",
        "broker-mock-adapter-safety-report",
        "broker-mock-adapter-gap-report",
        "kiwoom-mock-adapter-draft-build",
        "kiwoom-mock-adapter-request-draft-report",
        "kiwoom-mock-adapter-response-draft-report",
        "kiwoom-mock-adapter-safety-report",
        "kiwoom-mock-adapter-gap-report",
        "kiwoom-mock-credential-boundary-check",
        "kiwoom-mock-credential-domain-policy-report",
        "kiwoom-mock-credential-opt-in-report",
        "kiwoom-mock-credential-safety-report",
        "kiwoom-mock-credential-gap-report",
        "kiwoom-mock-oauth-token-request-draft",
        "kiwoom-mock-oauth-token-response-draft-report",
        "kiwoom-mock-oauth-token-revoke-draft",
        "kiwoom-mock-oauth-token-lifecycle-report",
        "kiwoom-mock-oauth-safety-report",
        "kiwoom-mock-oauth-gap-report",
        "kiwoom-mock-oauth-token-request-execute",
        "kiwoom-mock-oauth-token-revoke-execute",
        "kiwoom-mock-oauth-execution-safety-report",
        "kiwoom-mock-oauth-execution-gap-report",
        "kiwoom-mock-oauth-execution-audit-report",
        "kiwoom-mock-api-transport-request-envelope-draft",
        "kiwoom-mock-api-transport-policy-report",
        "kiwoom-mock-api-retry-timeout-report",
        "kiwoom-mock-api-error-response-draft-report",
        "kiwoom-mock-api-transport-safety-report",
        "kiwoom-mock-api-transport-gap-report",
        "kiwoom-mock-api-preflight-check",
        "kiwoom-mock-api-preflight-readiness-report",
        "kiwoom-mock-api-preflight-safety-report",
        "kiwoom-mock-api-preflight-gap-report",
        "kiwoom-mock-api-preflight-audit-report",
        "create-order-intent",
        "order-intents-list",
        "evaluate-order-intents",
        "paper-execute-approved-intents",
        "paper-executions-list",
        "broker-adapter-health",
        "broker-submit-mock-order",
        "broker-order-requests-list",
        "broker-order-receipts-list",
        "kiwoom-readonly-health",
        "kiwoom-readonly-endpoints",
        "kiwoom-readonly-stock-info",
        "kiwoom-readonly-quote",
        "kiwoom-readonly-rankings",
        "kiwoom-readonly-flow",
        "kiwoom-readonly-chart",
        "kiwoom-readonly-condition-list",
        "kiwoom-readonly-condition-run",
        "kiwoom-mock-execution-health",
        "kiwoom-mock-submit-order",
        "kiwoom-mock-cancel-order",
        "kiwoom-mock-order-status",
        "kiwoom-mock-order-requests-list",
        "kiwoom-mock-order-receipts-list",
        "kiwoom-official-endpoints-list",
        "kiwoom-official-endpoints-validate",
        "kiwoom-official-endpoint-show",
        "kiwoom-real-readonly-health",
        "kiwoom-real-readonly-stock-info",
        "kiwoom-real-readonly-quote",
        "kiwoom-real-readonly-rankings",
        "kiwoom-real-readonly-flow",
        "kiwoom-real-readonly-minute-chart",
        "kiwoom-real-readonly-daily-chart",
        "kiwoom-real-readonly-smoke-plan",
        "kiwoom-real-readonly-smoke-run",
        "kiwoom-real-readonly-smoke-reports",
        "kiwoom-real-readonly-smoke-show",
        "kiwoom-sandbox-order-health",
        "kiwoom-sandbox-order-plan",
        "kiwoom-sandbox-order-submit",
        "kiwoom-sandbox-order-cancel",
        "kiwoom-sandbox-order-status",
        "kiwoom-sandbox-order-requests",
        "kiwoom-sandbox-order-receipts",
        "kiwoom-sandbox-order-show",
        "kiwoom-sandbox-sell-schema-verify",
        "kiwoom-sandbox-sell-schema-reports",
        "kiwoom-sandbox-sell-schema-show",
        "kiwoom-sandbox-sell-dry-run",
        "kiwoom-official-sell-schema-evidence-validate",
        "kiwoom-official-sell-schema-evidence-import",
        "kiwoom-official-sell-schema-evidence-list",
        "kiwoom-official-sell-schema-evidence-show",
        "kiwoom-official-sell-schema-evidence-review",
        "kiwoom-account-read-health",
        "kiwoom-account-read-plan",
        "kiwoom-account-read-run",
        "kiwoom-account-read-reports",
        "kiwoom-account-read-show",
        "kiwoom-account-read-reconcile-preview",
        "kiwoom-account-read-smoke-plan",
        "kiwoom-account-read-smoke-run",
        "kiwoom-account-read-smoke-reports",
        "kiwoom-account-read-smoke-show",
        "report-pipeline",
        "report-scan",
        "report-basket",
        "report-policy-suite",
        "reports",
        "report-show",
        "agent-context-from-report",
        "agent-context-from-pipeline",
        "agent-prompt",
        "agent-brief",
        "agent-run-local",
        "agent-contexts",
        "agent-prompts",
        "agent-briefs",
        "agent-tools",
        "local-llm-responses",
        "notify-pipeline",
        "notify-report",
        "notify-brief",
        "notify-local-response",
        "notify-digest",
        "notification-runs",
        "notification-show",
        "notifications",
        "dashboard-overview",
        "dashboard-pipeline",
        "dashboard-daily",
        "dashboard-policy",
        "dashboard-builds",
        "dashboard-show",
        "run-local-demo",
        "system-smoke",
        "release-check",
        "backtest",
        "backtest-summary",
        "report",
        "reasons",
        "sources",
        "ingestion-runs",
        "analyze-indicators",
        "analyze-indicators-and-save",
        "analyze-setup",
        "create-trade-plan",
        "create-trade-plan-and-save",
        "build-basket-from-trade-plans",
        "build-basket-and-save",
        "show-basket",
        "paper-trade-basket",
        "paper-trade-basket-from-file",
        "paper-trades",
        "basket-performance",
        "strategy-init",
        "strategy-active",
        "strategy-propose",
        "strategy-evaluate",
        "strategy-experiments",
        "strategy-policies",
        "replay-snapshot-from-basket",
        "replay-snapshot-from-recent-trade-plans",
        "replay-runs",
        "replay-show",
        "policy-replay",
        "policy-replay-active",
        "policy-replay-results",
        "policy-compare",
        "policy-evaluate-suite",
        "policy-evaluation-suites",
        "policy-propose-promotion",
        "policy-promotion-proposals",
        "policy-approve",
        "policy-activate",
        "scan-candidates",
        "scan-runs",
        "scan-results",
        "scan-to-basket",
        "scan-to-replay-snapshot",
        "ingest-signals",
        "signals",
        "kiwoom-mock-market-data-request-execute",
        "kiwoom-mock-market-data-response-report",
        "kiwoom-mock-market-data-safety-report",
        "kiwoom-mock-market-data-gap-report",
        "kiwoom-mock-market-data-audit-report",
        "quant-robustness-check",
        "quant-survivorship-bias-report",
        "quant-point-in-time-leakage-report",
        "quant-walk-forward-policy-report",
        "quant-data-snooping-report",
        "quant-strategy-diversification-report",
        "quant-regime-readiness-report",
        "point-in-time-universe-check",
        "point-in-time-universe-report",
        "survivorship-bias-dataset-report",
        "security-lifecycle-coverage-report",
        "dataset-leakage-report",
        "dataset-promotion-readiness-report",
        "walk-forward-validation-check",
        "walk-forward-split-report",
        "data-snooping-report",
        "experiment-lineage-report",
        "parameter-search-pressure-report",
        "final-test-contamination-report",
        "strategy-stability-report",
        "validation-promotion-readiness-report",
        "training-pipeline-promotion-check",
        "training-dataset-eligibility-report",
        "training-dependency-report",
        "training-leakage-overfit-risk-report",
        "training-reproducibility-report",
        "model-artifact-policy-report",
        "model-promotion-readiness-report",
        "strategy-ensemble-check",
        "alpha-candidate-report",
        "strategy-family-diversification-report",
        "alpha-correlation-risk-report",
        "drawdown-co-movement-report",
        "regime-overlap-report",
        "alpha-portfolio-concentration-report",
        "ensemble-promotion-readiness-report",
        "regime-allocation-learning-check",
        "regime-feature-report",
        "allocation-action-candidate-report",
        "hedge-inverse-eligibility-report",
        "forward-outcome-label-report",
        "allocation-reward-scoring-report",
        "regime-allocation-leakage-report",
        "regime-allocation-dataset-readiness-report",
        "allocation-policy-training-check",
        "allocation-policy-training-summary-report",
        "regime-action-selection-report",
        "allocation-policy-walk-forward-report",
        "allocation-policy-risk-adjusted-report",
        "allocation-policy-turnover-slippage-report",
        "allocation-policy-drawdown-stability-report",
        "allocation-policy-promotion-readiness-report",
        "allocation-policy-artifact-report",
        "cnn-fear-greed-collect",
        "cnn-fear-greed-snapshot-report",
        "cnn-fear-greed-history-report",
        "cnn-fear-greed-feature-integration-report",
        "cnn-fear-greed-source-health-report",
        "cnn-fear-greed-audit-report",
        "risk-adjusted-paper-eval-check",
        "paper-evaluation-summary-report",
        "virtual-portfolio-report",
        "virtual-trade-ledger-report",
        "paper-cost-slippage-report",
        "paper-risk-adjusted-performance-report",
        "paper-drawdown-exposure-report",
        "paper-regime-fear-bucket-report",
        "paper-pass-readiness-report",
        "controlled-mock-readiness-check",
        "mock-readiness-summary-report",
        "mock-readiness-dependency-report",
        "paper-pass-evidence-report",
        "mock-infrastructure-readiness-report",
        "mock-safety-policy-report",
        "mock-boundary-violation-report",
        "mock-readiness-gap-report",
        "market-regime-check",
        "market-regime-summary-report",
        "market-regime-input-snapshot-report",
        "risk-appetite-report",
        "market-direction-regime-report",
        "volatility-regime-report",
        "fx-rate-dollar-stress-report",
        "cross-asset-conflict-report",
        "market-regime-downstream-constraint-report",
        "market-regime-training-feature-report",
        "market-regime-gap-report",
        "run-scan-pipeline",
        "run-paper-pipeline",
        "run-policy-evaluation-pipeline",
        "pipeline-runs",
        "pipeline-show",
        "alerts",
        "watch-loop",
    }
    if args_list and args_list[0] in commands:
        args = build_command_parser().parse_args(args_list)
        output = run_command(args)
    else:
        args = build_legacy_parser().parse_args(args_list)
        output = run_evaluate(args)
    print(json.dumps(output, ensure_ascii=False, indent=2))


def run_command(args: argparse.Namespace) -> dict[str, object]:
    if args.command == "evaluate-and-save":
        return run_evaluate_and_save(args)
    if args.command == "ingest-nasdaq-noncompliant":
        return run_ingest_nasdaq_noncompliant(args)
    if args.command == "check-compliance":
        return run_check_compliance(args)
    if args.command == "ingest-prices":
        return run_ingest_prices(args)
    if args.command == "import-data":
        return run_import_data(args)
    if args.command == "import-runs":
        return {"import_runs": [import_run_report(item) for item in RiskRepository(args.db).list_import_runs(args.limit)]}
    if args.command == "import-show":
        return import_run_report(RiskRepository(args.db).get_import_run(args.import_run_id))
    if args.command == "fx-rates":
        items = RiskRepository(args.db).list_fx_rates()
        items = [
            item for item in items
            if (not args.base_currency or item["base_currency"] == args.base_currency.upper())
            and (not args.quote_currency or item["quote_currency"] == args.quote_currency.upper())
        ]
        return {"fx_rates": items}
    if args.command == "fx-latest":
        return FXService(RiskRepository(args.db)).get_latest_fx_rate(
            args.base_currency, args.quote_currency, args.as_of_date
        ).model_dump(mode="json")
    if args.command == "fx-convert":
        amount, conversion = FXService(RiskRepository(args.db)).convert_amount(
            args.amount, args.from_currency, args.to_currency, args.as_of_date
        )
        return {"amount": args.amount, "converted_amount": amount, **conversion.model_dump(mode="json")}
    if args.command == "normalize-file":
        columns = {
            key[:-7].replace("_", "-").replace("-", "_"): value
            for key, value in vars(args).items() if key.endswith("_column") and value
        }
        source = {
            "normalizer": args.normalizer, "input_file": str(args.input_file),
            "output_name": args.output_name, "columns": columns,
        }
        run, _ = normalize_sources(
            [source], args.output_dir, args.as_of_date,
            repository=RiskRepository(args.db), save=args.save,
        )
        return run.model_dump(mode="json")
    if args.command in {"normalize-run", "normalize-and-import"}:
        repository = RiskRepository(args.db)
        run, import_run = normalize_sources(
            load_normalizer_config(args.config_file), args.output_dir, args.as_of_date,
            repository=repository,
            save=True if args.command == "normalize-and-import" else args.save,
            import_outputs=args.command == "normalize-and-import",
        )
        output = run.model_dump(mode="json")
        output["import_run_id"] = import_run.import_run_id if import_run else None
        output["import_status"] = import_run.status.value if import_run else None
        return output
    if args.command == "normalize-runs":
        return {"normalize_runs": [
            item.model_dump(mode="json") for item in RiskRepository(args.db).list_normalize_runs(args.limit)
        ]}
    if args.command == "normalize-show":
        return RiskRepository(args.db).get_normalize_run(args.normalize_run_id).model_dump(mode="json")
    if args.command == "connectors":
        return {"connectors": [
            {"name": item.name, "connector_type": item.connector_type.value, "mode": item.mode.value}
            for item in default_connector_registry().list_connectors()
        ]}
    if args.command == "run-connectors":
        registry, connector_names = _connector_registry_and_names(args)
        results = run_connectors(
            RiskRepository(args.db), registry, args.as_of_date,
            args.output_dir, connector_names, args.ticker,
        )
        return {
            "as_of_date": args.as_of_date.isoformat(),
            "connector_runs": [item.connector_run.model_dump(mode="json") for item in results],
            "output_file_count": sum(item.output is not None for item in results),
        }
    if args.command == "run-connectors-and-import":
        registry, connector_names = _connector_registry_and_names(args)
        return run_connectors_and_import(
            RiskRepository(args.db), registry, args.as_of_date,
            args.output_dir, connector_names, args.ticker,
        )
    if args.command == "validate-provider-config":
        return {"providers": validate_provider_config_file(args.provider_config_file, args.allowed_host)}
    if args.command == "run-http-connector":
        configs = load_provider_configs(args.provider_config_file)
        selected = [item for item in configs if item.provider_name == args.provider]
        if not selected:
            raise LookupError(f"Provider not found: {args.provider}")
        registry = register_http_providers(
            default_connector_registry(), selected, args.enable_network, args.allowed_host,
        )
        result = run_connectors(
            RiskRepository(args.db), registry, args.as_of_date, args.output_dir, [args.provider], [],
        )[0]
        return {
            "as_of_date": args.as_of_date.isoformat(),
            "connector_run": result.connector_run.model_dump(mode="json"),
            "output": result.output.model_dump(mode="json") if result.output else None,
        }
    if args.command == "connector-runs":
        return {"connector_runs": [item.model_dump(mode="json") for item in RiskRepository(args.db).list_connector_runs(args.limit)]}
    if args.command == "connector-show":
        return RiskRepository(args.db).get_connector_run(args.connector_run_id).model_dump(mode="json")
    if args.command in {"run-price-provider-pack", "run-fx-provider-pack", "run-price-fx-provider-pack", "run-news-provider-pack", "run-dilution-provider-pack", "run-flow-provider-pack"}:
        pack_types = {
            "run-price-provider-pack": ProviderPackType.PRICE,
            "run-fx-provider-pack": ProviderPackType.FX,
            "run-price-fx-provider-pack": ProviderPackType.PRICE_AND_FX,
            "run-news-provider-pack": ProviderPackType.NEWS,
            "run-dilution-provider-pack": ProviderPackType.DILUTION,
            "run-flow-provider-pack": ProviderPackType.FLOW,
        }
        run = run_provider_pack(
            RiskRepository(args.db), load_provider_pack_config(args.provider_pack_config),
            pack_types[args.command], args.output_dir, args.as_of_date,
            enable_network=args.enable_network, allowed_hosts=args.allowed_host, tickers=args.ticker,
        )
        return run.model_dump(mode="json")
    if args.command == "provider-pack-runs":
        return {"provider_pack_runs": [
            item.model_dump(mode="json") for item in RiskRepository(args.db).list_provider_pack_runs(args.limit)
        ]}
    if args.command == "provider-pack-show":
        return RiskRepository(args.db).get_provider_pack_run(args.provider_pack_run_id).model_dump(mode="json")
    if args.command == "run-realtime-monitor":
        region = MarketRegion(args.region)
        if args.provider == "local-replay":
            if args.replay_file is None:
                return {"status": "FAILED", "error": "--replay-file is required for local-replay"}
            provider = LocalReplayMarketDataProvider(args.replay_file, region)
        else:
            provider = MockRealtimeMarketDataProvider(region)
        result = run_realtime_monitor(
            RiskRepository(args.db), provider, args.symbols.split(","), region,
            output_dir=args.output_dir, max_events=args.max_events, max_symbols=args.max_symbols,
            max_hot_watchlist_size=args.max_hot_watchlist_size,
            min_dollar_volume_5m=args.min_dollar_volume_5m,
        )
        return result.model_dump(mode="json")
    if args.command == "watchlist-list":
        status = WatchlistStatus(args.status) if args.status else None
        return {"watchlist_entries": [
            item.model_dump(mode="json")
            for item in RiskRepository(args.db).list_watchlist_entries(status, args.limit)
        ]}
    if args.command == "realtime-runs":
        return {"realtime_monitor_runs": [
            item.model_dump(mode="json")
            for item in RiskRepository(args.db).list_realtime_monitor_runs(args.limit)
        ]}
    if args.command == "realtime-show":
        return RiskRepository(args.db).get_realtime_monitor_run(
            args.realtime_monitor_run_id
        ).model_dump(mode="json")
    if args.command.startswith("local-ledger-"):
        service = LocalLedgerService(RiskRepository(args.db))
        if args.command == "local-ledger-position-upsert":
            try:
                position = service.upsert_position(
                    args.symbol, MarketRegion(args.region), args.quantity,
                    args.reserved_quantity, args.average_price,
                )
                return position.model_dump(mode="json") | {"available_quantity": position.available_quantity}
            except ValueError as error:
                return {"status": "FAILED", "errors": [str(error)]}
        if args.command == "local-ledger-positions":
            return {"positions": [item.model_dump(mode="json") | {"available_quantity": item.available_quantity} for item in service.list_positions()]}
        if args.command == "local-ledger-snapshot":
            return service.create_snapshot().model_dump(mode="json")
        return {"transactions": [item.model_dump(mode="json") for item in service.list_transactions()]}
    if args.command.startswith("sell-safety-"):
        repository = RiskRepository(args.db)
        if args.command == "sell-safety-decisions":
            return {"decisions": [item.model_dump(mode="json") for item in repository.list_sell_safety_decisions(args.limit)]}
        if args.command == "sell-safety-show":
            try:
                return repository.get_sell_safety_decision(args.decision_id).model_dump(mode="json")
            except LookupError as error:
                return {"status": "NOT_FOUND", "errors": [str(error)]}
        intent = repository.get_order_intent(args.order_intent_id) if args.order_intent_id else OrderIntent(
            ticker=args.symbol, region=MarketRegion(args.region), side=OrderSide.SELL,
            order_type=OrderType.LIMIT, quantity=args.quantity, limit_price=1,
            source_type="manual_sell_safety_check", source_id="cli",
            reason="offline local-ledger sell-safety check", confidence_score=1,
        )
        return SellSafetyGate(repository).evaluate(intent, args.reconciliation_status).model_dump(mode="json")
    if args.command == "strategy-run":
        try:
            result = StrategyService(RiskRepository(args.db)).run_fixture(
                args.fixture_file, args.include_local_llm_review
            )
            return {
                "run": result["run"].model_dump(mode="json"),
                "decisions": [item.model_dump(mode="json") for item in result["decisions"]],
                "local_llm_reviews": [item.model_dump(mode="json") for item in result["local_llm_reviews"]],
            }
        except Exception as exc:
            return {"status": "FAILED", "errors": [str(exc)], "decisions": []}
    if args.command == "strategy-decisions":
        items = RiskRepository(args.db).list_strategy_decisions(
            StrategyDecisionStatus(args.status) if args.status else None, args.limit
        )
        return {"decisions": [item.model_dump(mode="json") for item in items]}
    if args.command == "strategy-decision-show":
        try:
            return RiskRepository(args.db).get_strategy_decision(args.decision_id).model_dump(mode="json")
        except LookupError as exc:
            return {"status": "NOT_FOUND", "errors": [str(exc)]}
    if args.command == "strategy-candidates":
        return {"candidates": [
            item.model_dump(mode="json") for item in RiskRepository(args.db).list_strategy_candidates(args.limit)
        ]}
    if args.command == "strategy-candidate-show":
        try:
            return RiskRepository(args.db).get_strategy_candidate(args.candidate_id).model_dump(mode="json")
        except LookupError as exc:
            return {"status": "NOT_FOUND", "errors": [str(exc)]}
    if args.command == "strategy-create-order-intent-draft":
        try:
            repository = RiskRepository(args.db)
            intent = create_order_intent_draft(repository, repository.get_strategy_decision(args.decision_id))
            return {"status": "CREATED", "order_intent": intent.model_dump(mode="json")}
        except (LookupError, ValueError) as exc:
            return {"status": "BLOCKED", "errors": [str(exc)]}
    if args.command == "local-llm-health":
        return DisabledLocalLLMAdvisor().health()
    if args.command == "strategy-backtest-run":
        try:
            result = StrategyBacktestService(RiskRepository(args.db)).run_fixture(args.fixture_file)
            return {
                "run": result["run"].model_dump(mode="json"),
                "report": result["report"].model_dump(mode="json"),
            }
        except Exception as exc:
            return {"status": "FAILED", "errors": [str(exc)]}
    if args.command == "strategy-backtest-reports":
        return {"reports": [
            item.model_dump(mode="json") for item in RiskRepository(args.db).list_strategy_backtest_reports(args.limit)
        ]}
    if args.command == "strategy-backtest-show":
        try:
            return RiskRepository(args.db).get_strategy_backtest_report(args.report_id).model_dump(mode="json")
        except LookupError as exc:
            return {"status": "NOT_FOUND", "errors": [str(exc)]}
    if args.command == "technical-evidence-run":
        try:
            result = run_technical_evidence(args.fixture_file, args.output_file)
            if args.output_file:
                return {"status": "COMPLETED", "output_file": str(args.output_file), "ticker_count": len(result.evidence), "grades": {item.ticker: item.grade.value for item in result.evidence}}
            return result.model_dump(mode="json")
        except Exception as exc:
            return {"status": "FAILED", "errors": [str(exc)]}
    if args.command == "technical-evidence-show":
        try:
            return load_technical_evidence_result(args.output_file).model_dump(mode="json")
        except Exception as exc:
            return {"status": "FAILED", "errors": [str(exc)]}
    if args.command == "market-discovery-run":
        try:
            result = run_market_discovery(args.fixture_file, args.output_file)
            if args.output_file:
                return {
                    "status": "COMPLETED",
                    "output_file": str(args.output_file),
                    "summary_counts": result.summary_counts,
                }
            return result.model_dump(mode="json")
        except Exception as exc:
            return {"status": "FAILED", "errors": [str(exc)]}
    if args.command == "market-discovery-show":
        try:
            return load_market_discovery_result(args.output_file).model_dump(mode="json")
        except Exception as exc:
            return {"status": "FAILED", "errors": [str(exc)]}
    if args.command == "llm-feature-store-run":
        try:
            result = run_feature_store(args.signal_fixture_file, args.db, args.output_file)
            if args.output_file:
                return {"status": "COMPLETED", "output_file": str(args.output_file), "signal_count": result.signal_count}
            return result.model_dump(mode="json")
        except Exception as exc:
            return {"status": "FAILED", "errors": [str(exc)]}
    if args.command == "llm-signal-evaluate":
        try:
            result = run_signal_evaluation(args.signal_fixture_file, args.outcome_fixture_file, args.db, args.output_file)
            if args.output_file:
                return {"status": "COMPLETED", "output_file": str(args.output_file), "evaluation_count": len(result.evaluations)}
            return result.model_dump(mode="json")
        except Exception as exc:
            return {"status": "FAILED", "errors": [str(exc)]}
    if args.command == "llm-signal-evaluation-show":
        try:
            return load_llm_signal_evaluation_report(args.output_file).model_dump(mode="json")
        except Exception as exc:
            return {"status": "FAILED", "errors": [str(exc)]}
    if args.command == "trade-plan-run":
        try:
            result = run_trade_plan(args.fixture_file, args.output_file)
            if args.output_file:
                return {"status": "COMPLETED", "output_file": str(args.output_file), "summary_counts": result.summary_counts}
            return result.model_dump(mode="json")
        except Exception as exc:
            return {"status": "FAILED", "errors": [str(exc)]}
    if args.command == "trade-plan-show":
        try:
            return load_trade_plan_report(args.output_file).model_dump(mode="json")
        except Exception as exc:
            return {"status": "FAILED", "errors": [str(exc)]}
    if args.command == "paper-eval-run":
        try:
            result = run_paper_eval(args.fixture_file, args.output_file)
            if args.output_file:
                return {"status": "COMPLETED", "output_file": str(args.output_file), "trade_count": result.metrics.trade_count}
            return result.model_dump(mode="json")
        except Exception as exc:
            return {"status": "FAILED", "errors": [str(exc)]}
    if args.command == "paper-eval-show":
        try:
            return load_paper_eval_report(args.output_file).model_dump(mode="json")
        except Exception as exc:
            return {"status": "FAILED", "errors": [str(exc)]}
    if args.command == "policy-replay-run":
        try:
            result = run_walk_forward_policy_replay(args.fixture_file, args.output_file)
            if args.output_file:
                return {"status": "COMPLETED", "output_file": str(args.output_file), "candidate_count": len(result.candidate_comparisons)}
            return result.model_dump(mode="json")
        except Exception as exc:
            return {"status": "FAILED", "errors": [str(exc)]}
    if args.command == "policy-replay-show":
        try:
            return load_walk_forward_policy_report(args.output_file).model_dump(mode="json")
        except Exception as exc:
            return {"status": "FAILED", "errors": [str(exc)]}
    if args.command == "local-llm-advisory-run":
        try:
            result = run_local_llm_advisory(args.fixture_file, args.output_file)
            if args.output_file:
                return {"status": "COMPLETED", "output_file": str(args.output_file), "result_status": result.status.value}
            return result.model_dump(mode="json")
        except Exception as exc:
            return {"status": "FAILED", "errors": [str(exc)]}
    if args.command == "local-llm-advisory-show":
        try:
            return load_local_llm_advisory_result(args.output_file).model_dump(mode="json")
        except Exception as exc:
            return {"status": "FAILED", "errors": [str(exc)]}
    if args.command == "local-model-candidates-list":
        try:
            result = run_local_model_candidates_list(args.fixture_file, args.output_file)
            if args.output_file:
                return {"status": "COMPLETED", "output_file": str(args.output_file), "candidate_count": result.candidate_count}
            return result.model_dump(mode="json")
        except Exception as exc:
            return {"status": "FAILED", "errors": [str(exc)]}
    if args.command == "local-model-runtime-check":
        try:
            result = run_local_model_runtime_check(args.fixture_file, args.output_file)
            if args.output_file:
                return {"status": "COMPLETED", "output_file": str(args.output_file), "result_status": result.status.value}
            return result.model_dump(mode="json")
        except Exception as exc:
            return {"status": "FAILED", "errors": [str(exc)]}
    if args.command == "local-model-advisory-dry-run":
        try:
            result = run_local_model_advisory_dry_run(args.fixture_file, args.output_file)
            if args.output_file:
                return {"status": "COMPLETED", "output_file": str(args.output_file), "result_status": result.status.value}
            return result.model_dump(mode="json")
        except Exception as exc:
            return {"status": "FAILED", "errors": [str(exc)]}
    if args.command == "local-model-benchmark-run":
        try:
            result = run_local_model_benchmark_cli(args.fixture_file, args.candidate_output_file, args.output_file)
            if args.output_file:
                return {"status": "COMPLETED", "output_file": str(args.output_file), "eligible_count": result.summary_counts["eligible_count"]}
            return result.model_dump(mode="json")
        except Exception as exc:
            return {"status": "FAILED", "errors": [str(exc)]}
    if args.command == "local-model-benchmark-show":
        try:
            return load_local_model_benchmark_report(args.output_file).model_dump(mode="json")
        except Exception as exc:
            return {"status": "FAILED", "errors": [str(exc)]}
    if args.command == "local-model-candidates-rank":
        try:
            ranked = rank_local_model_candidates_from_report(args.benchmark_report_file)
            if args.output_file:
                Path(args.output_file).write_text(json.dumps({"ranked_candidates": ranked}, indent=2), encoding="utf-8")
                return {"status": "COMPLETED", "output_file": str(args.output_file), "ranked_count": len(ranked)}
            return {"ranked_candidates": ranked}
        except Exception as exc:
            return {"status": "FAILED", "errors": [str(exc)]}
    if args.command == "local-model-decision-report":
        try:
            result = run_local_model_decision_report_cli(args.pack_file, args.output_file)
            if args.output_file:
                return {"status": "COMPLETED", "output_file": str(args.output_file), "recommendation_status": result.recommendation_status.value}
            return result.model_dump(mode="json")
        except Exception as exc:
            return {"status": "FAILED", "errors": [str(exc)]}
    if args.command == "local-model-benchmark-pack-validate":
        try:
            return validate_local_model_benchmark_pack(args.pack_file)
        except Exception as exc:
            return {"status": "FAILED", "errors": [str(exc)]}
    if args.command == "strategy-track-profile-validate":
        try:
            result = run_strategy_track_profile_validation(args.fixture_file, args.output_file)
            if args.output_file:
                return {"status": "COMPLETED", "output_file": str(args.output_file), "request_count": result.summary["request_count"]}
            return result.model_dump(mode="json")
        except Exception as exc:
            return {"status": "FAILED", "errors": [str(exc)]}
    if args.command == "strategy-track-profile-show":
        try:
            return load_strategy_track_validation_report(args.output_file).model_dump(mode="json")
        except Exception as exc:
            return {"status": "FAILED", "errors": [str(exc)]}
    if args.command == "strategy-track-compare":
        try:
            result = run_strategy_track_compare(args.fixture_file, args.output_file)
            if args.output_file:
                return {"status": "COMPLETED", "output_file": str(args.output_file), "comparison_count": result.comparison_count}
            return result.model_dump(mode="json")
        except Exception as exc:
            return {"status": "FAILED", "errors": [str(exc)]}
    if args.command == "market-profit-profile-validate":
        try:
            result = run_market_profit_profile_validation(args.fixture_file, args.output_file)
            if args.output_file:
                return {"status": "COMPLETED", "output_file": str(args.output_file), "strategy_track": result.summary["strategy_track"]}
            return result.model_dump(mode="json")
        except Exception as exc:
            return {"status": "FAILED", "errors": [str(exc)]}
    if args.command == "market-profit-estimate":
        try:
            result = run_market_profit_estimate(args.fixture_file, args.output_file)
            if args.output_file:
                return {"status": "COMPLETED", "output_file": str(args.output_file), "eligibility_status": result.check.eligibility_status.value}
            return result.model_dump(mode="json")
        except Exception as exc:
            return {"status": "FAILED", "errors": [str(exc)]}
    if args.command == "market-profit-compare-tracks":
        try:
            result = run_market_profit_compare_tracks(args.fixture_file, args.output_file)
            if args.output_file:
                return {"status": "COMPLETED", "output_file": str(args.output_file), "comparison_count": result.comparison_count}
            return result.model_dump(mode="json")
        except Exception as exc:
            return {"status": "FAILED", "errors": [str(exc)]}
    if args.command == "market-profit-break-even":
        try:
            result = run_market_profit_estimate(args.fixture_file)
            return {"break_even_estimate": result.check.break_even_estimate.model_dump(mode="json")}
        except Exception as exc:
            return {"status": "FAILED", "errors": [str(exc)]}
    if args.command == "domestic-realtime-profile-validate":
        try:
            result = run_domestic_realtime_profile_validate(args.fixture_file)
            if args.output_file:
                args.output_file.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
                return {"status": "COMPLETED", "output_file": str(args.output_file), "strategy_track": result["strategy_track"]}
            return result
        except Exception as exc:
            return {"status": "FAILED", "errors": [str(exc)]}
    if args.command == "domestic-realtime-plan-show":
        try:
            return run_domestic_realtime_plan_show(args.fixture_file).model_dump(mode="json")
        except Exception as exc:
            return {"status": "FAILED", "errors": [str(exc)]}
    if args.command == "domestic-realtime-event-normalize":
        try:
            result = run_domestic_realtime_event_normalize(args.fixture_file, args.output_file)
            if args.output_file:
                return {"status": "COMPLETED", "output_file": str(args.output_file), "event_count": len(result["events"])}
            return result
        except Exception as exc:
            return {"status": "FAILED", "errors": [str(exc)]}
    if args.command == "domestic-realtime-quality-report":
        try:
            result = run_domestic_realtime_quality_report(args.fixture_file, args.output_file)
            if args.output_file:
                return {"status": "COMPLETED", "output_file": str(args.output_file), "quality_status": result.quality_status.value}
            return result.model_dump(mode="json")
        except Exception as exc:
            return {"status": "FAILED", "errors": [str(exc)]}
    if args.command == "domestic-scanner-config-validate":
        try:
            result = run_domestic_scanner_config_validate(args.fixture_file)
            if args.output_file:
                args.output_file.write_text(result.model_dump_json(indent=2), encoding="utf-8")
                return {"status": "COMPLETED", "output_file": str(args.output_file), "config_id": result.config_id}
            return {"status": "COMPLETED", **result.model_dump(mode="json")}
        except Exception as exc:
            return {"status": "FAILED", "errors": [str(exc)]}
    if args.command == "domestic-scanner-candidates":
        try:
            result = run_domestic_scanner_candidates(args.fixture_file, args.output_file)
            if args.output_file:
                return {"status": "COMPLETED", "output_file": str(args.output_file), "candidate_count": result.candidate_count}
            return result.model_dump(mode="json")
        except Exception as exc:
            return {"status": "FAILED", "errors": [str(exc)]}
    if args.command == "domestic-scanner-watchlist-plan":
        try:
            result = run_domestic_scanner_watchlist_plan(args.fixture_file, args.output_file)
            if args.output_file:
                return {"status": "COMPLETED", "output_file": str(args.output_file), "additions": len(result.additions), "removals": len(result.removals)}
            return result.model_dump(mode="json")
        except Exception as exc:
            return {"status": "FAILED", "errors": [str(exc)]}
    if args.command == "domestic-scanner-quality-report":
        try:
            result = run_domestic_scanner_quality_report(args.fixture_file, args.output_file)
            if args.output_file:
                return {"status": "COMPLETED", "output_file": str(args.output_file), "candidate_count": result.candidate_count}
            return result.model_dump(mode="json")
        except Exception as exc:
            return {"status": "FAILED", "errors": [str(exc)]}
    if args.command == "domestic-candidate-evaluation-config-validate":
        try:
            result = run_domestic_candidate_evaluation_config_validate(args.fixture_file)
            if args.output_file:
                args.output_file.write_text(result.model_dump_json(indent=2), encoding="utf-8")
                return {"status": "COMPLETED", "output_file": str(args.output_file), "config_id": result.config_id}
            return {"status": "COMPLETED", **result.model_dump(mode="json")}
        except Exception as exc:
            return {"status": "FAILED", "errors": [str(exc)]}
    if args.command == "domestic-candidate-evaluate":
        try:
            result = run_domestic_candidate_evaluate(args.fixture_file, args.output_file)
            if args.output_file:
                return {"status": "COMPLETED", "output_file": str(args.output_file), "candidate_count": result.candidate_count}
            return result.model_dump(mode="json")
        except Exception as exc:
            return {"status": "FAILED", "errors": [str(exc)]}
    if args.command == "domestic-candidate-evaluation-gap-report":
        try:
            result = run_domestic_candidate_evaluation_gap_report(args.fixture_file, args.output_file)
            if args.output_file:
                return {"status": "COMPLETED", "output_file": str(args.output_file), "gap_reasons": len(result.gap_reasons)}
            return result.model_dump(mode="json")
        except Exception as exc:
            return {"status": "FAILED", "errors": [str(exc)]}
    if args.command == "domestic-candidate-evaluation-safety-report":
        try:
            result = run_domestic_candidate_evaluation_safety_report(args.fixture_file, args.output_file)
            if args.output_file:
                return {"status": "COMPLETED", "output_file": str(args.output_file), "decision_count": len(result.decisions)}
            return result.model_dump(mode="json")
        except Exception as exc:
            return {"status": "FAILED", "errors": [str(exc)]}
    if args.command == "domestic-replay-config-validate":
        try:
            result = run_domestic_replay_config_validate(args.fixture_file)
            if args.output_file:
                args.output_file.write_text(result.model_dump_json(indent=2), encoding="utf-8")
                return {"status": "COMPLETED", "output_file": str(args.output_file), "config_id": result.config_id}
            return {"status": "COMPLETED", **result.model_dump(mode="json")}
        except Exception as exc:
            return {"status": "FAILED", "errors": [str(exc)]}
    if args.command == "domestic-replay-run":
        try:
            result = run_domestic_replay_run(args.fixture_file, args.output_file)
            if args.output_file:
                return {"status": "COMPLETED", "output_file": str(args.output_file), "step_count": len(result.step_results)}
            return result.model_dump(mode="json")
        except Exception as exc:
            return {"status": "FAILED", "errors": [str(exc)]}
    if args.command == "domestic-replay-metrics-report":
        try:
            result = run_domestic_replay_metrics_report(args.fixture_file, args.output_file)
            if args.output_file:
                return {"status": "COMPLETED", "output_file": str(args.output_file), "total_events_processed": result.total_events_processed}
            return result.model_dump(mode="json")
        except Exception as exc:
            return {"status": "FAILED", "errors": [str(exc)]}
    if args.command == "domestic-replay-promotion-readiness":
        try:
            result = run_domestic_replay_promotion_readiness(args.fixture_file, args.output_file)
            if args.output_file:
                return {"status": "COMPLETED", "output_file": str(args.output_file), "readiness_status": result.readiness_status.value}
            return result.model_dump(mode="json")
        except Exception as exc:
            return {"status": "FAILED", "errors": [str(exc)]}
    if args.command == "domestic-calibration-config-validate":
        try:
            result = run_domestic_calibration_config_validate(args.fixture_file)
            if args.output_file:
                args.output_file.write_text(result.model_dump_json(indent=2), encoding="utf-8")
                return {"status": "COMPLETED", "output_file": str(args.output_file), "calibration_run_id": result.calibration_run_id}
            return {"status": "COMPLETED", **result.model_dump(mode="json")}
        except Exception as exc:
            return {"status": "FAILED", "errors": [str(exc)]}
    if args.command == "domestic-calibration-run":
        try:
            result = run_domestic_calibration_run(args.fixture_file, args.output_file)
            if args.output_file:
                return {"status": "COMPLETED", "output_file": str(args.output_file), "single_run_count": len(result.single_run_results)}
            return result.model_dump(mode="json")
        except Exception as exc:
            return {"status": "FAILED", "errors": [str(exc)]}
    if args.command == "domestic-policy-compare":
        try:
            result = run_domestic_policy_compare(args.fixture_file, args.output_file)
            if args.output_file:
                return {"status": "COMPLETED", "output_file": str(args.output_file), "candidate_count": len(result.candidate_policy_ids)}
            return result.model_dump(mode="json")
        except Exception as exc:
            return {"status": "FAILED", "errors": [str(exc)]}
    if args.command == "domestic-promotion-gate-report":
        try:
            result = run_domestic_promotion_gate_report(args.fixture_file, args.output_file)
            if args.output_file:
                return {"status": "COMPLETED", "output_file": str(args.output_file), "gate_status": result.gate_status.value}
            return result.model_dump(mode="json")
        except Exception as exc:
            return {"status": "FAILED", "errors": [str(exc)]}
    if args.command == "domestic-paper-shadow-config-validate":
        try:
            result = run_domestic_paper_shadow_config_validate(args.fixture_file)
            if args.output_file:
                args.output_file.write_text(result.model_dump_json(indent=2), encoding="utf-8")
                return {"status": "COMPLETED", "output_file": str(args.output_file), "config_id": result.config_id}
            return {"status": "COMPLETED", **result.model_dump(mode="json")}
        except Exception as exc:
            return {"status": "FAILED", "errors": [str(exc)]}
    if args.command == "domestic-paper-shadow-journal-build":
        try:
            result = run_domestic_paper_shadow_journal_build(args.fixture_file, args.output_file)
            if args.output_file:
                return {"status": "COMPLETED", "output_file": str(args.output_file), "entry_count": result.entry_count}
            return result.model_dump(mode="json")
        except Exception as exc:
            return {"status": "FAILED", "errors": [str(exc)]}
    if args.command == "domestic-paper-shadow-review-report":
        try:
            result = run_domestic_paper_shadow_review_report(args.fixture_file, args.output_file)
            if args.output_file:
                return {"status": "COMPLETED", "output_file": str(args.output_file), "entry_count": result.total_journal_entries}
            return result.model_dump(mode="json")
        except Exception as exc:
            return {"status": "FAILED", "errors": [str(exc)]}
    if args.command == "domestic-paper-shadow-safety-report":
        try:
            result = run_domestic_paper_shadow_safety_report(args.fixture_file, args.output_file)
            if args.output_file:
                return {"status": "COMPLETED", "output_file": str(args.output_file), "block_reasons": len(result.block_reasons)}
            return result.model_dump(mode="json")
        except Exception as exc:
            return {"status": "FAILED", "errors": [str(exc)]}
    if args.command == "domestic-shadow-outcome-config-validate":
        try:
            result = run_domestic_shadow_outcome_config_validate(args.fixture_file)
            if args.output_file:
                args.output_file.write_text(result.model_dump_json(indent=2), encoding="utf-8")
                return {"status": "COMPLETED", "output_file": str(args.output_file), "config_id": result.config_id}
            return {"status": "COMPLETED", **result.model_dump(mode="json")}
        except Exception as exc:
            return {"status": "FAILED", "errors": [str(exc)]}
    if args.command == "domestic-shadow-outcome-label":
        try:
            result = run_domestic_shadow_outcome_label(args.fixture_file, args.output_file)
            if args.output_file:
                return {"status": "COMPLETED", "output_file": str(args.output_file), "label_count": result.label_count}
            return result.model_dump(mode="json")
        except Exception as exc:
            return {"status": "FAILED", "errors": [str(exc)]}
    if args.command == "domestic-shadow-outcome-review-report":
        try:
            result = run_domestic_shadow_outcome_review_report(args.fixture_file, args.output_file)
            if args.output_file:
                return {"status": "COMPLETED", "output_file": str(args.output_file), "label_count": result.total_outcome_labels}
            return result.model_dump(mode="json")
        except Exception as exc:
            return {"status": "FAILED", "errors": [str(exc)]}
    if args.command == "domestic-shadow-outcome-safety-report":
        try:
            result = run_domestic_shadow_outcome_safety_report(args.fixture_file, args.output_file)
            if args.output_file:
                return {"status": "COMPLETED", "output_file": str(args.output_file), "warnings": len(result.warnings)}
            return result.model_dump(mode="json")
        except Exception as exc:
            return {"status": "FAILED", "errors": [str(exc)]}
    if args.command == "domestic-shadow-advisory-context-config-validate":
        try:
            result = run_domestic_shadow_advisory_context_config_validate(args.fixture_file)
            if args.output_file:
                args.output_file.write_text(result.model_dump_json(indent=2), encoding="utf-8")
                return {"status": "COMPLETED", "output_file": str(args.output_file), "valid": result.valid}
            return {"status": "COMPLETED", **result.model_dump(mode="json")}
        except Exception as exc:
            return {"status": "FAILED", "errors": [str(exc)]}
    if args.command == "domestic-shadow-advisory-context-build":
        try:
            result = run_domestic_shadow_advisory_context_build(args.fixture_file, args.output_file)
            if args.output_file:
                return {"status": "COMPLETED", "output_file": str(args.output_file), "bundle_id": result.bundle_id}
            return result.model_dump(mode="json")
        except Exception as exc:
            return {"status": "FAILED", "errors": [str(exc)]}
    if args.command == "domestic-shadow-advisory-context-validate":
        try:
            result = run_domestic_shadow_advisory_context_validate(args.fixture_file, args.output_file)
            if args.output_file:
                return {"status": "COMPLETED", "output_file": str(args.output_file), "valid": result.valid}
            return result.model_dump(mode="json")
        except Exception as exc:
            return {"status": "FAILED", "errors": [str(exc)]}
    if args.command == "domestic-shadow-advisory-context-gap-report":
        try:
            result = run_domestic_shadow_advisory_context_gap_report(args.fixture_file, args.output_file)
            if args.output_file:
                return {"status": "COMPLETED", "output_file": str(args.output_file), "gap_count": len(result.gap_categories)}
            return result.model_dump(mode="json")
        except Exception as exc:
            return {"status": "FAILED", "errors": [str(exc)]}
    if args.command == "domestic-shadow-advisory-context-safety-report":
        try:
            result = run_domestic_shadow_advisory_context_safety_report(args.fixture_file, args.output_file)
            if args.output_file:
                return {"status": "COMPLETED", "output_file": str(args.output_file), "block_reasons": len(result.block_reasons)}
            return result.model_dump(mode="json")
        except Exception as exc:
            return {"status": "FAILED", "errors": [str(exc)]}
    if args.command == "domestic-distillation-dataset-config-validate":
        try:
            result = run_domestic_distillation_dataset_config_validate(args.fixture_file)
            if args.output_file:
                args.output_file.write_text(result.model_dump_json(indent=2), encoding="utf-8")
                return {"status": "COMPLETED", "output_file": str(args.output_file), "valid": result.valid}
            return {"status": "COMPLETED", **result.model_dump(mode="json")}
        except Exception as exc:
            return {"status": "FAILED", "errors": [str(exc)]}
    if args.command == "domestic-distillation-dataset-build":
        try:
            result = run_domestic_distillation_dataset_build(args.fixture_file, args.output_file)
            if args.output_file:
                return {"status": "COMPLETED", "output_file": str(args.output_file), "pack_id": result.pack_id}
            return result.model_dump(mode="json")
        except Exception as exc:
            return {"status": "FAILED", "errors": [str(exc)]}
    if args.command == "domestic-distillation-dataset-validate":
        try:
            result = run_domestic_distillation_dataset_validate(args.fixture_file, args.output_file)
            if args.output_file:
                return {"status": "COMPLETED", "output_file": str(args.output_file), "valid": result.valid}
            return result.model_dump(mode="json")
        except Exception as exc:
            return {"status": "FAILED", "errors": [str(exc)]}
    if args.command == "domestic-distillation-dataset-gap-report":
        try:
            result = run_domestic_distillation_dataset_gap_report(args.fixture_file, args.output_file)
            if args.output_file:
                return {"status": "COMPLETED", "output_file": str(args.output_file), "gap_count": len(result.gap_categories)}
            return result.model_dump(mode="json")
        except Exception as exc:
            return {"status": "FAILED", "errors": [str(exc)]}
    if args.command == "domestic-distillation-dataset-safety-report":
        try:
            result = run_domestic_distillation_dataset_safety_report(args.fixture_file, args.output_file)
            if args.output_file:
                return {"status": "COMPLETED", "output_file": str(args.output_file), "block_reasons": len(result.block_reasons)}
            return result.model_dump(mode="json")
        except Exception as exc:
            return {"status": "FAILED", "errors": [str(exc)]}
    if args.command == "domestic-market-regime-config-validate":
        try:
            result = run_domestic_market_regime_config_validate(args.fixture_file)
            if args.output_file:
                args.output_file.write_text(result.model_dump_json(indent=2), encoding="utf-8")
                return {"status": "COMPLETED", "output_file": str(args.output_file), "gap_count": len(result.gap_categories)}
            return {"status": "COMPLETED", **result.model_dump(mode="json")}
        except Exception as exc:
            return {"status": "FAILED", "errors": [str(exc)]}
    if args.command == "domestic-market-regime-classify":
        try:
            result = run_domestic_market_regime_classify(args.fixture_file, args.output_file)
            if args.output_file:
                return {"status": "COMPLETED", "output_file": str(args.output_file), "primary_regime_label": result.primary_regime_label.value}
            return result.model_dump(mode="json")
        except Exception as exc:
            return {"status": "FAILED", "errors": [str(exc)]}
    if args.command == "domestic-market-regime-report":
        try:
            result = run_domestic_market_regime_report(args.fixture_file, args.output_file)
            if args.output_file:
                return {"status": "COMPLETED", "output_file": str(args.output_file), "report_id": result.report_id}
            return result.model_dump(mode="json")
        except Exception as exc:
            return {"status": "FAILED", "errors": [str(exc)]}
    if args.command == "domestic-market-regime-gap-report":
        try:
            result = run_domestic_market_regime_gap_report(args.fixture_file, args.output_file)
            if args.output_file:
                return {"status": "COMPLETED", "output_file": str(args.output_file), "gap_count": len(result.gap_categories)}
            return result.model_dump(mode="json")
        except Exception as exc:
            return {"status": "FAILED", "errors": [str(exc)]}
    if args.command == "domestic-market-regime-safety-report":
        try:
            result = run_domestic_market_regime_safety_report(args.fixture_file, args.output_file)
            if args.output_file:
                return {"status": "COMPLETED", "output_file": str(args.output_file), "block_reasons": len(result.block_reasons)}
            return result.model_dump(mode="json")
        except Exception as exc:
            return {"status": "FAILED", "errors": [str(exc)]}
    if args.command == "domestic-regime-aware-integration-config-validate":
        try:
            result = run_domestic_regime_aware_integration_config_validate(args.fixture_file)
            if args.output_file:
                args.output_file.write_text(result.model_dump_json(indent=2), encoding="utf-8")
                return {"status": "COMPLETED", "output_file": str(args.output_file), "gap_count": len(result.gap_categories)}
            return {"status": "COMPLETED", **result.model_dump(mode="json")}
        except Exception as exc:
            return {"status": "FAILED", "errors": [str(exc)]}
    if args.command == "domestic-regime-aware-integration-build":
        try:
            result = run_domestic_regime_aware_integration_build(args.fixture_file, args.output_file)
            if args.output_file:
                return {"status": "COMPLETED", "output_file": str(args.output_file), "integration_report_id": result.integration_report_id}
            return result.model_dump(mode="json")
        except Exception as exc:
            return {"status": "FAILED", "errors": [str(exc)]}
    if args.command == "domestic-regime-aware-integration-report":
        try:
            result = run_domestic_regime_aware_integration_report(args.fixture_file, args.output_file)
            if args.output_file:
                return {"status": "COMPLETED", "output_file": str(args.output_file), "integration_report_id": result.integration_report_id}
            return result.model_dump(mode="json")
        except Exception as exc:
            return {"status": "FAILED", "errors": [str(exc)]}
    if args.command == "domestic-regime-aware-gap-report":
        try:
            result = run_domestic_regime_aware_gap_report(args.fixture_file, args.output_file)
            if args.output_file:
                return {"status": "COMPLETED", "output_file": str(args.output_file), "gap_count": len(result.gap_categories)}
            return result.model_dump(mode="json")
        except Exception as exc:
            return {"status": "FAILED", "errors": [str(exc)]}
    if args.command == "domestic-regime-aware-safety-report":
        try:
            result = run_domestic_regime_aware_safety_report(args.fixture_file, args.output_file)
            if args.output_file:
                return {"status": "COMPLETED", "output_file": str(args.output_file), "block_reasons": len(result.block_reasons)}
            return result.model_dump(mode="json")
        except Exception as exc:
            return {"status": "FAILED", "errors": [str(exc)]}
    if args.command == "prompt-pack-validate":
        try:
            result = run_prompt_pack_validate(args.fixture_file, args.output_file)
            if args.output_file:
                return {"status": "COMPLETED", "output_file": str(args.output_file), "valid": result.valid}
            return result.model_dump(mode="json")
        except Exception as exc:
            return {"status": "FAILED", "errors": [str(exc)]}
    if args.command == "prompt-pack-show":
        try:
            return run_prompt_pack_show(args.fixture_file).model_dump(mode="json")
        except Exception as exc:
            return {"status": "FAILED", "errors": [str(exc)]}
    if args.command == "prompt-pack-coverage-report":
        try:
            result = run_prompt_pack_coverage_report(args.fixture_file, args.output_file)
            if args.output_file:
                return {"status": "COMPLETED", "output_file": str(args.output_file), "task_count": result.total_task_count}
            return result.model_dump(mode="json")
        except Exception as exc:
            return {"status": "FAILED", "errors": [str(exc)]}
    if args.command == "prompt-pack-gap-report":
        try:
            result = run_prompt_pack_gap_report(args.fixture_file, args.output_file)
            if args.output_file:
                return {"status": "COMPLETED", "output_file": str(args.output_file), "validation_passed": result.validation_passed}
            return result.model_dump(mode="json")
        except Exception as exc:
            return {"status": "FAILED", "errors": [str(exc)]}
    if args.command == "historical-data-config-validate":
        try:
            result = run_historical_data_config_validate(args.fixture_file)
            return {"status": "COMPLETED", "fixture_id": result.fixture_id}
        except Exception as exc:
            return {"status": "FAILED", "errors": [str(exc)]}
    if args.command == "historical-data-manifest-build":
        try:
            result = run_historical_data_manifest_build(args.fixture_file, args.output_file)
            if args.output_file:
                return {"status": "COMPLETED", "output_file": str(args.output_file), "record_count": result.record_count}
            return result.model_dump(mode="json")
        except Exception as exc:
            return {"status": "FAILED", "errors": [str(exc)]}
    if args.command == "historical-data-validate":
        try:
            result = run_historical_data_validate(args.fixture_file, args.output_file)
            if args.output_file:
                return {"status": "COMPLETED", "output_file": str(args.output_file), "validation_status": result.validation_status.value}
            return result.model_dump(mode="json")
        except Exception as exc:
            return {"status": "FAILED", "errors": [str(exc)]}
    if args.command == "historical-data-quality-report":
        try:
            result = run_historical_data_quality_report(args.fixture_file, args.output_file)
            if args.output_file:
                return {"status": "COMPLETED", "output_file": str(args.output_file), "quality_bucket": result.quality_bucket.value}
            return result.model_dump(mode="json")
        except Exception as exc:
            return {"status": "FAILED", "errors": [str(exc)]}
    if args.command == "historical-data-gap-report":
        try:
            result = run_historical_data_gap_report(args.fixture_file, args.output_file)
            if args.output_file:
                return {"status": "COMPLETED", "output_file": str(args.output_file), "gap_count": len(result.gap_categories)}
            return result.model_dump(mode="json")
        except Exception as exc:
            return {"status": "FAILED", "errors": [str(exc)]}
    if args.command == "historical-calendar-config-validate":
        try:
            result = run_historical_calendar_config_validate(args.fixture_file)
            return {"status": "COMPLETED", "fixture_id": result.fixture_id}
        except Exception as exc:
            return {"status": "FAILED", "errors": [str(exc)]}
    if args.command == "historical-calendar-validate":
        try:
            result = run_historical_calendar_validate(args.fixture_file, args.output_file)
            if args.output_file:
                return {"status": "COMPLETED", "output_file": str(args.output_file), "validation_status": result.validation_status.value}
            return result.model_dump(mode="json")
        except Exception as exc:
            return {"status": "FAILED", "errors": [str(exc)]}
    if args.command == "historical-calendar-gap-report":
        try:
            result = run_historical_calendar_gap_report(args.fixture_file, args.output_file)
            if args.output_file:
                return {"status": "COMPLETED", "output_file": str(args.output_file), "gap_count": len(result.gap_categories)}
            return result.model_dump(mode="json")
        except Exception as exc:
            return {"status": "FAILED", "errors": [str(exc)]}
    if args.command == "historical-replay-bridge-build":
        try:
            result = _build_historical_replay_bridge_report(args.fixture_file)
            if args.output_file:
                args.output_file.write_text(result.model_dump_json(indent=2), encoding="utf-8")
                return {"status": "COMPLETED", "output_file": str(args.output_file), "window_count": result.window_count}
            return result.model_dump(mode="json")
        except Exception as exc:
            return {"status": "FAILED", "errors": [str(exc)]}
    if args.command == "historical-replay-event-stream":
        try:
            result = _build_historical_replay_event_stream_payload(args.fixture_file)
            if args.output_file:
                args.output_file.write_text(result.model_dump_json(indent=2), encoding="utf-8")
                return {"status": "COMPLETED", "output_file": str(args.output_file), "event_count": len(result.events)}
            return result.model_dump(mode="json")
        except Exception as exc:
            return {"status": "FAILED", "errors": [str(exc)]}
    if args.command == "historical-replay-window-report":
        try:
            result = _build_historical_replay_window_bundle(args.fixture_file)
            if args.output_file:
                args.output_file.write_text(result.model_dump_json(indent=2), encoding="utf-8")
                return {"status": "COMPLETED", "output_file": str(args.output_file), "window_count": len(result.windows)}
            return result.model_dump(mode="json")
        except Exception as exc:
            return {"status": "FAILED", "errors": [str(exc)]}
    if args.command == "historical-scanner-replay-input":
        try:
            result = _build_historical_scanner_replay_input_payload(args.fixture_file)
            if args.output_file:
                args.output_file.write_text(result.model_dump_json(indent=2), encoding="utf-8")
                return {
                    "status": "COMPLETED",
                    "output_file": str(args.output_file),
                    "candidate_seed_count": len(result.candidate_seeds),
                }
            return result.model_dump(mode="json")
        except Exception as exc:
            return {"status": "FAILED", "errors": [str(exc)]}
    if args.command == "historical-replay-gap-report":
        try:
            result = _build_historical_replay_window_bundle(args.fixture_file).gap_report
            if args.output_file:
                args.output_file.write_text(result.model_dump_json(indent=2), encoding="utf-8")
                return {"status": "COMPLETED", "output_file": str(args.output_file), "gap_count": len(result.gap_categories)}
            return result.model_dump(mode="json")
        except Exception as exc:
            return {"status": "FAILED", "errors": [str(exc)]}
    if args.command == "historical-replay-safety-report":
        try:
            result = _build_historical_replay_safety_report(args.fixture_file)
            if args.output_file:
                args.output_file.write_text(result.model_dump_json(indent=2), encoding="utf-8")
                return {"status": "COMPLETED", "output_file": str(args.output_file), "safety_report_id": result.safety_report_id}
            return result.model_dump(mode="json")
        except Exception as exc:
            return {"status": "FAILED", "errors": [str(exc)]}
    if args.command == "historical-outcome-observe":
        try:
            result = _build_historical_outcome_observation_input(args.fixture_file)
            if args.output_file:
                args.output_file.write_text(result.model_dump_json(indent=2), encoding="utf-8")
                return {"status": "COMPLETED", "output_file": str(args.output_file), "window_count": len(result.observation_windows)}
            return result.model_dump(mode="json")
        except Exception as exc:
            return {"status": "FAILED", "errors": [str(exc)]}
    if args.command == "historical-outcome-label-report":
        try:
            result = _build_historical_outcome_label_observation(args.fixture_file)
            scanner_replay_input = result.scanner_replay_input.model_dump(mode="json")
            if args.output_file:
                args.output_file.write_text(result.label_report.model_dump_json(indent=2), encoding="utf-8")
                return {"status": "COMPLETED", "output_file": str(args.output_file), "label_count": len(result.label_report.labels)}
            return {
                **result.label_report.model_dump(mode="json"),
                "scanner_replay_input": scanner_replay_input,
                "replay_input_unchanged": True,
            }
        except Exception as exc:
            return {"status": "FAILED", "errors": [str(exc)]}
    if args.command == "historical-outcome-gap-report":
        try:
            result = _build_historical_outcome_label_observation(args.fixture_file).gap_report
            if args.output_file:
                args.output_file.write_text(result.model_dump_json(indent=2), encoding="utf-8")
                return {"status": "COMPLETED", "output_file": str(args.output_file), "gap_count": len(result.gaps)}
            return result.model_dump(mode="json")
        except Exception as exc:
            return {"status": "FAILED", "errors": [str(exc)]}
    if args.command == "historical-outcome-safety-report":
        try:
            result = _build_historical_outcome_label_observation(args.fixture_file).safety_report
            if args.output_file:
                args.output_file.write_text(result.model_dump_json(indent=2), encoding="utf-8")
                return {"status": "COMPLETED", "output_file": str(args.output_file), "safety_report_id": result.safety_report_id}
            return result.model_dump(mode="json")
        except Exception as exc:
            return {"status": "FAILED", "errors": [str(exc)]}
    if args.command == "historical-dataset-assemble":
        try:
            result = _build_historical_dataset_assembly(args.fixture_file)
            scanner_replay_input = result.scanner_replay_input.model_dump(mode="json")
            if args.output_file:
                args.output_file.write_text(result.model_dump_json(indent=2), encoding="utf-8")
                return {"status": "COMPLETED", "output_file": str(args.output_file), "record_count": len(result.records)}
            return {
                **result.model_dump(mode="json"),
                "scanner_replay_input": scanner_replay_input,
                "replay_input_unchanged": True,
            }
        except Exception as exc:
            return {"status": "FAILED", "errors": [str(exc)]}
    if args.command == "historical-dataset-export-manifest":
        try:
            result = _build_historical_dataset_assembly(args.fixture_file).export_manifest
            if args.output_file:
                args.output_file.write_text(result.model_dump_json(indent=2), encoding="utf-8")
                return {"status": "COMPLETED", "output_file": str(args.output_file), "manifest_id": result.manifest_id}
            return result.model_dump(mode="json")
        except Exception as exc:
            return {"status": "FAILED", "errors": [str(exc)]}
    if args.command == "historical-dataset-quality-report":
        try:
            result = _build_historical_dataset_assembly(args.fixture_file).quality_report
            if args.output_file:
                args.output_file.write_text(result.model_dump_json(indent=2), encoding="utf-8")
                return {"status": "COMPLETED", "output_file": str(args.output_file), "record_count": result.record_count}
            return result.model_dump(mode="json")
        except Exception as exc:
            return {"status": "FAILED", "errors": [str(exc)]}
    if args.command == "historical-dataset-gap-report":
        try:
            result = _build_historical_dataset_assembly(args.fixture_file).gap_report
            if args.output_file:
                args.output_file.write_text(result.model_dump_json(indent=2), encoding="utf-8")
                return {"status": "COMPLETED", "output_file": str(args.output_file), "gap_count": len(result.gaps)}
            return result.model_dump(mode="json")
        except Exception as exc:
            return {"status": "FAILED", "errors": [str(exc)]}
    if args.command == "historical-dataset-safety-report":
        try:
            result = _build_historical_dataset_assembly(args.fixture_file).safety_report
            if args.output_file:
                args.output_file.write_text(result.model_dump_json(indent=2), encoding="utf-8")
                return {"status": "COMPLETED", "output_file": str(args.output_file), "safety_report_id": result.safety_report_id}
            return result.model_dump(mode="json")
        except Exception as exc:
            return {"status": "FAILED", "errors": [str(exc)]}
    if args.command == "historical-dataset-validate":
        try:
            result = _build_historical_dataset_validation(args.fixture_file).validation_report
            if args.output_file:
                args.output_file.write_text(result.model_dump_json(indent=2), encoding="utf-8")
                return {"status": "COMPLETED", "output_file": str(args.output_file), "record_count": result.record_count}
            return result.model_dump(mode="json")
        except Exception as exc:
            return {"status": "FAILED", "errors": [str(exc)]}
    if args.command == "historical-dataset-leakage-audit":
        try:
            result = _build_historical_dataset_validation(args.fixture_file).leakage_audit_report
            if args.output_file:
                args.output_file.write_text(result.model_dump_json(indent=2), encoding="utf-8")
                return {"status": "COMPLETED", "output_file": str(args.output_file), "audited_record_count": result.audited_record_count}
            return result.model_dump(mode="json")
        except Exception as exc:
            return {"status": "FAILED", "errors": [str(exc)]}
    if args.command == "historical-dataset-split-manifest":
        try:
            result = _build_historical_dataset_validation(args.fixture_file).split_manifest
            if args.output_file:
                args.output_file.write_text(result.model_dump_json(indent=2), encoding="utf-8")
                return {"status": "COMPLETED", "output_file": str(args.output_file), "record_count": len(result.record_refs)}
            return result.model_dump(mode="json")
        except Exception as exc:
            return {"status": "FAILED", "errors": [str(exc)]}
    if args.command == "historical-dataset-coverage-report":
        try:
            result = _build_historical_dataset_validation(args.fixture_file).coverage_report
            if args.output_file:
                args.output_file.write_text(result.model_dump_json(indent=2), encoding="utf-8")
                return {"status": "COMPLETED", "output_file": str(args.output_file), "record_count": result.record_count}
            return result.model_dump(mode="json")
        except Exception as exc:
            return {"status": "FAILED", "errors": [str(exc)]}
    if args.command == "historical-dataset-label-distribution":
        try:
            result = _build_historical_dataset_validation(args.fixture_file).label_distribution_report
            if args.output_file:
                args.output_file.write_text(result.model_dump_json(indent=2), encoding="utf-8")
                return {"status": "COMPLETED", "output_file": str(args.output_file), "record_count": result.record_count}
            return result.model_dump(mode="json")
        except Exception as exc:
            return {"status": "FAILED", "errors": [str(exc)]}
    if args.command == "historical-dataset-readiness-report":
        try:
            result = _build_historical_dataset_readiness(args.fixture_file).readiness_report
            if args.output_file:
                args.output_file.write_text(result.model_dump_json(indent=2), encoding="utf-8")
                return {"status": "COMPLETED", "output_file": str(args.output_file), "record_count": result.record_count}
            return result.model_dump(mode="json")
        except Exception as exc:
            return {"status": "FAILED", "errors": [str(exc)]}
    if args.command == "historical-dataset-split-quality-report":
        try:
            result = _build_historical_dataset_readiness(args.fixture_file).split_quality_report
            if args.output_file:
                args.output_file.write_text(result.model_dump_json(indent=2), encoding="utf-8")
                return {"status": "COMPLETED", "output_file": str(args.output_file), "record_count": result.train_record_count + result.validation_record_count + result.test_record_count}
            return result.model_dump(mode="json")
        except Exception as exc:
            return {"status": "FAILED", "errors": [str(exc)]}
    if args.command == "historical-dataset-imbalance-report":
        try:
            result = _build_historical_dataset_readiness(args.fixture_file).imbalance_report
            if args.output_file:
                args.output_file.write_text(result.model_dump_json(indent=2), encoding="utf-8")
                return {"status": "COMPLETED", "output_file": str(args.output_file), "label_count": len(result.label_counts)}
            return result.model_dump(mode="json")
        except Exception as exc:
            return {"status": "FAILED", "errors": [str(exc)]}
    if args.command == "historical-dataset-baseline-evaluation":
        try:
            result = _build_historical_dataset_readiness(args.fixture_file).baseline_evaluation_report
            if args.output_file:
                args.output_file.write_text(result.model_dump_json(indent=2), encoding="utf-8")
                return {"status": "COMPLETED", "output_file": str(args.output_file), "baseline_count": len(result.baseline_names)}
            return result.model_dump(mode="json")
        except Exception as exc:
            return {"status": "FAILED", "errors": [str(exc)]}
    if args.command == "historical-dataset-readiness-safety-report":
        try:
            result = _build_historical_dataset_readiness(args.fixture_file).readiness_safety_report
            if args.output_file:
                args.output_file.write_text(result.model_dump_json(indent=2), encoding="utf-8")
                return {"status": "COMPLETED", "output_file": str(args.output_file), "safety_report_id": result.safety_report_id}
            return result.model_dump(mode="json")
        except Exception as exc:
            return {"status": "FAILED", "errors": [str(exc)]}
    if args.command == "historical-model-training-plan-check":
        try:
            result = _build_historical_model_training_plan_check(args.fixture_file).plan_check_report
            if args.output_file:
                args.output_file.write_text(result.model_dump_json(indent=2), encoding="utf-8")
                return {"status": "COMPLETED", "output_file": str(args.output_file), "eligible_for_sandbox_training": result.eligible_for_sandbox_training}
            return result.model_dump(mode="json")
        except Exception as exc:
            return {"status": "FAILED", "errors": [str(exc)]}
    if args.command == "historical-model-train-sandbox":
        try:
            result = _build_historical_model_training_sandbox(args.fixture_file)
            if args.output_file:
                args.output_file.write_text(result.model_dump_json(indent=2), encoding="utf-8")
                return {"status": "COMPLETED", "output_file": str(args.output_file), "training_executed": result.run_report.training_executed}
            return result.model_dump(mode="json")
        except Exception as exc:
            return {"status": "FAILED", "errors": [str(exc)]}
    if args.command == "historical-model-evaluation-report":
        try:
            result = _build_historical_model_training_sandbox(args.fixture_file).evaluation_report
            if args.output_file:
                args.output_file.write_text(result.model_dump_json(indent=2), encoding="utf-8")
                return {"status": "COMPLETED", "output_file": str(args.output_file), "report_only_prediction_count": result.report_only_prediction_count}
            return result.model_dump(mode="json")
        except Exception as exc:
            return {"status": "FAILED", "errors": [str(exc)]}
    if args.command == "historical-model-artifact-manifest":
        try:
            result = _build_historical_model_training_sandbox(args.fixture_file).artifact_manifest
            if args.output_file:
                args.output_file.write_text(result.model_dump_json(indent=2), encoding="utf-8")
                return {"status": "COMPLETED", "output_file": str(args.output_file), "artifact_manifest_id": result.artifact_manifest_id}
            return result.model_dump(mode="json")
        except Exception as exc:
            return {"status": "FAILED", "errors": [str(exc)]}
    if args.command == "historical-model-training-safety-report":
        try:
            result = _build_historical_model_training_sandbox(args.fixture_file).safety_report
            if args.output_file:
                args.output_file.write_text(result.model_dump_json(indent=2), encoding="utf-8")
                return {"status": "COMPLETED", "output_file": str(args.output_file), "safety_report_id": result.safety_report_id}
            return result.model_dump(mode="json")
        except Exception as exc:
            return {"status": "FAILED", "errors": [str(exc)]}
    if args.command == "historical-model-experiment-register":
        try:
            result = _build_historical_model_experiment_registry(args.fixture_file).registry_report
            if args.output_file:
                args.output_file.write_text(result.model_dump_json(indent=2), encoding="utf-8")
                return {"status": "COMPLETED", "output_file": str(args.output_file), "experiment_count": result.experiment_count}
            return result.model_dump(mode="json")
        except Exception as exc:
            return {"status": "FAILED", "errors": [str(exc)]}
    if args.command == "historical-model-experiment-compare":
        try:
            result = _build_historical_model_experiment_registry(args.fixture_file).comparison_report
            if args.output_file:
                args.output_file.write_text(result.model_dump_json(indent=2), encoding="utf-8")
                return {"status": "COMPLETED", "output_file": str(args.output_file), "compared_experiment_count": len(result.compared_experiment_ids)}
            return result.model_dump(mode="json")
        except Exception as exc:
            return {"status": "FAILED", "errors": [str(exc)]}
    if args.command == "historical-model-risk-review":
        try:
            result = _build_historical_model_experiment_registry(args.fixture_file).risk_review_report
            if args.output_file:
                args.output_file.write_text(result.model_dump_json(indent=2), encoding="utf-8")
                return {"status": "COMPLETED", "output_file": str(args.output_file), "unsafe_artifact_metadata": result.unsafe_artifact_metadata}
            return result.model_dump(mode="json")
        except Exception as exc:
            return {"status": "FAILED", "errors": [str(exc)]}
    if args.command == "historical-model-promotion-block-report":
        try:
            result = _build_historical_model_experiment_registry(args.fixture_file).promotion_block_report
            if args.output_file:
                args.output_file.write_text(result.model_dump_json(indent=2), encoding="utf-8")
                return {"status": "COMPLETED", "output_file": str(args.output_file), "promotion_block_report_id": result.promotion_block_report_id}
            return result.model_dump(mode="json")
        except Exception as exc:
            return {"status": "FAILED", "errors": [str(exc)]}
    if args.command == "historical-model-experiment-safety-report":
        try:
            result = _build_historical_model_experiment_registry(args.fixture_file).safety_report
            if args.output_file:
                args.output_file.write_text(result.model_dump_json(indent=2), encoding="utf-8")
                return {"status": "COMPLETED", "output_file": str(args.output_file), "safety_report_id": result.safety_report_id}
            return result.model_dump(mode="json")
        except Exception as exc:
            return {"status": "FAILED", "errors": [str(exc)]}
    if args.command == "historical-signal-candidate-build":
        try:
            result = _build_historical_signal_candidate_batch(args.fixture_file).candidate_batch
            if args.output_file:
                args.output_file.write_text(result.model_dump_json(indent=2), encoding="utf-8")
                return {"status": "COMPLETED", "output_file": str(args.output_file), "accepted_candidate_count": result.accepted_candidate_count}
            return result.model_dump(mode="json")
        except Exception as exc:
            return {"status": "FAILED", "errors": [str(exc)]}
    if args.command == "historical-signal-candidate-report":
        try:
            result = _build_historical_signal_candidate_batch(args.fixture_file).candidate_report
            if args.output_file:
                args.output_file.write_text(result.model_dump_json(indent=2), encoding="utf-8")
                return {"status": "COMPLETED", "output_file": str(args.output_file), "candidate_count": result.candidate_count}
            return result.model_dump(mode="json")
        except Exception as exc:
            return {"status": "FAILED", "errors": [str(exc)]}
    if args.command == "historical-signal-candidate-safety-report":
        try:
            result = _build_historical_signal_candidate_batch(args.fixture_file).safety_report
            if args.output_file:
                args.output_file.write_text(result.model_dump_json(indent=2), encoding="utf-8")
                return {"status": "COMPLETED", "output_file": str(args.output_file), "safety_report_id": result.safety_report_id}
            return result.model_dump(mode="json")
        except Exception as exc:
            return {"status": "FAILED", "errors": [str(exc)]}
    if args.command == "historical-signal-candidate-gap-report":
        try:
            result = _build_historical_signal_candidate_batch(args.fixture_file).gap_report
            if args.output_file:
                args.output_file.write_text(result.model_dump_json(indent=2), encoding="utf-8")
                return {"status": "COMPLETED", "output_file": str(args.output_file), "gap_report_id": result.gap_report_id}
            return result.model_dump(mode="json")
        except Exception as exc:
            return {"status": "FAILED", "errors": [str(exc)]}
    if args.command == "historical-paper-trading-run":
        try:
            result = _run_historical_paper_trading(args.fixture_file)
            output = result.paper_order_intent
            if args.output_file:
                args.output_file.write_text(output.model_dump_json(indent=2), encoding="utf-8")
                return {"status": "COMPLETED", "output_file": str(args.output_file), "paper_order_intent_id": output.paper_order_intent_id}
            return output.model_dump(mode="json")
        except Exception as exc:
            return {"status": "FAILED", "errors": [str(exc)]}
    if args.command == "historical-paper-trading-performance-report":
        try:
            result = _run_historical_paper_trading(args.fixture_file).paper_performance_report
            if args.output_file:
                args.output_file.write_text(result.model_dump_json(indent=2), encoding="utf-8")
                return {"status": "COMPLETED", "output_file": str(args.output_file), "performance_report_id": result.performance_report_id}
            return result.model_dump(mode="json")
        except Exception as exc:
            return {"status": "FAILED", "errors": [str(exc)]}
    if args.command == "historical-paper-trading-safety-report":
        try:
            result = _run_historical_paper_trading(args.fixture_file).safety_report
            if args.output_file:
                args.output_file.write_text(result.model_dump_json(indent=2), encoding="utf-8")
                return {"status": "COMPLETED", "output_file": str(args.output_file), "safety_report_id": result.safety_report_id}
            return result.model_dump(mode="json")
        except Exception as exc:
            return {"status": "FAILED", "errors": [str(exc)]}
    if args.command == "historical-paper-trading-gap-report":
        try:
            result = _run_historical_paper_trading(args.fixture_file).gap_report
            if args.output_file:
                args.output_file.write_text(result.model_dump_json(indent=2), encoding="utf-8")
                return {"status": "COMPLETED", "output_file": str(args.output_file), "gap_report_id": result.gap_report_id}
            return result.model_dump(mode="json")
        except Exception as exc:
            return {"status": "FAILED", "errors": [str(exc)]}
    if args.command == "broker-mock-adapter-boundary-run":
        try:
            result = _run_broker_mock_adapter_boundary(args.fixture_file)
            output = {
                "mock_only": True,
                "paper_only": True,
                "disabled_by_default": True,
                "explicit_opt_in_required": True,
                "non_executable_by_default": True,
                "local_file_only": True,
                "offline_only": True,
                "no_real_order": True,
                "no_real_account_mutation": True,
                "no_live_trading": True,
                "no_live_prod": True,
                "no_production_broker": True,
                "no_credentials_loaded": True,
                "no_network_call": True,
                "no_kiwoom_api_call": True,
                "no_ls_api_call": True,
                "no_broker_api_call": True,
                "no_order_api_call": True,
                "no_account_api_call": True,
                "no_provider_api_call": True,
                "no_cloud_llm": True,
                "no_local_llm_runtime": True,
                "adapter_boundary": result.model_dump(mode="json"),
            }
            if args.output_file:
                args.output_file.write_text(json.dumps(output, indent=2), encoding="utf-8")
                return {"status": "COMPLETED", "output_file": str(args.output_file), "config_id": result.adapter_config.config_id}
            return output
        except Exception as exc:
            return {"status": "FAILED", "errors": [str(exc)]}
    if args.command == "broker-mock-adapter-capability-report":
        try:
            result = _run_broker_mock_adapter_boundary(args.fixture_file).capability
            if args.output_file:
                args.output_file.write_text(result.model_dump_json(indent=2), encoding="utf-8")
                return {"status": "COMPLETED", "output_file": str(args.output_file), "capability_id": result.capability_id}
            return result.model_dump(mode="json")
        except Exception as exc:
            return {"status": "FAILED", "errors": [str(exc)]}
    if args.command == "broker-mock-adapter-order-boundary-report":
        try:
            result = _run_broker_mock_adapter_boundary(args.fixture_file)
            output = {
                "mock_only": True,
                "paper_only": True,
                "disabled_by_default": True,
                "explicit_opt_in_required": True,
                "non_executable_by_default": True,
                "local_file_only": True,
                "offline_only": True,
                "no_real_order": True,
                "no_real_account_mutation": True,
                "no_live_trading": True,
                "no_live_prod": True,
                "no_production_broker": True,
                "no_credentials_loaded": True,
                "no_network_call": True,
                "no_kiwoom_api_call": True,
                "no_ls_api_call": True,
                "no_broker_api_call": True,
                "no_order_api_call": True,
                "no_account_api_call": True,
                "no_provider_api_call": True,
                "no_cloud_llm": True,
                "no_local_llm_runtime": True,
                "broker_mock_order_intent": result.broker_mock_order_intent.model_dump(mode="json"),
                "broker_mock_order_request": result.broker_mock_order_request.model_dump(mode="json"),
                "broker_mock_order_response": result.broker_mock_order_response.model_dump(mode="json"),
                "broker_mock_execution_report": result.broker_mock_execution_report.model_dump(mode="json"),
            }
            if args.output_file:
                args.output_file.write_text(json.dumps(output, indent=2), encoding="utf-8")
                return {
                    "status": "COMPLETED",
                    "output_file": str(args.output_file),
                    "mock_order_intent_id": result.broker_mock_order_intent.mock_order_intent_id,
                }
            return output
        except Exception as exc:
            return {"status": "FAILED", "errors": [str(exc)]}
    if args.command == "broker-mock-adapter-safety-report":
        try:
            result = _run_broker_mock_adapter_boundary(args.fixture_file).safety_report
            if args.output_file:
                args.output_file.write_text(result.model_dump_json(indent=2), encoding="utf-8")
                return {"status": "COMPLETED", "output_file": str(args.output_file), "safety_report_id": result.safety_report_id}
            return result.model_dump(mode="json")
        except Exception as exc:
            return {"status": "FAILED", "errors": [str(exc)]}
    if args.command == "broker-mock-adapter-gap-report":
        try:
            result = _run_broker_mock_adapter_boundary(args.fixture_file).gap_report
            if args.output_file:
                args.output_file.write_text(result.model_dump_json(indent=2), encoding="utf-8")
                return {"status": "COMPLETED", "output_file": str(args.output_file), "gap_report_id": result.gap_report_id}
            return result.model_dump(mode="json")
        except Exception as exc:
            return {"status": "FAILED", "errors": [str(exc)]}
    if args.command == "kiwoom-mock-adapter-draft-build":
        try:
            result = _run_kiwoom_mock_adapter_draft_mapping(args.fixture_file)
            output = {
                "kiwoom_mock_only": True,
                "draft_only": True,
                "paper_only": True,
                "disabled_by_default": True,
                "explicit_opt_in_required": True,
                "non_executable": True,
                "local_file_only": True,
                "offline_only": True,
                "evidence_backed": True,
                "no_credentials_loaded": True,
                "no_oauth_token_request": True,
                "no_api_call": True,
                "no_mockapi_call": True,
                "no_network_call": True,
                "no_websocket_connection": True,
                "no_real_order": True,
                "no_real_account_mutation": True,
                "no_live_trading": True,
                "no_live_prod": True,
                "no_broker_api_call": True,
                "no_order_api_call": True,
                "no_account_api_call": True,
                "no_provider_api_call": True,
                "no_cloud_llm": True,
                "no_local_llm_runtime": True,
                "adapter_draft_boundary": result.model_dump(mode="json"),
            }
            if args.output_file:
                args.output_file.write_text(json.dumps(output, indent=2), encoding="utf-8")
                return {"status": "COMPLETED", "output_file": str(args.output_file), "adapter_input_id": result.adapter_input_id}
            return output
        except Exception as exc:
            return {"status": "FAILED", "errors": [str(exc)]}
    if args.command == "kiwoom-mock-adapter-request-draft-report":
        try:
            result = _run_kiwoom_mock_adapter_draft_mapping(args.fixture_file).order_request_draft
            if args.output_file:
                args.output_file.write_text(result.model_dump_json(indent=2), encoding="utf-8")
                return {"status": "COMPLETED", "output_file": str(args.output_file), "request_draft_id": result.request_draft_id}
            return result.model_dump(mode="json")
        except Exception as exc:
            return {"status": "FAILED", "errors": [str(exc)]}
    if args.command == "kiwoom-mock-adapter-response-draft-report":
        try:
            result = _run_kiwoom_mock_adapter_draft_mapping(args.fixture_file).order_response_draft
            if args.output_file:
                args.output_file.write_text(result.model_dump_json(indent=2), encoding="utf-8")
                return {"status": "COMPLETED", "output_file": str(args.output_file), "response_draft_id": result.response_draft_id}
            return result.model_dump(mode="json")
        except Exception as exc:
            return {"status": "FAILED", "errors": [str(exc)]}
    if args.command == "kiwoom-mock-adapter-safety-report":
        try:
            result = _run_kiwoom_mock_adapter_draft_mapping(args.fixture_file).safety_report
            if args.output_file:
                args.output_file.write_text(result.model_dump_json(indent=2), encoding="utf-8")
                return {"status": "COMPLETED", "output_file": str(args.output_file), "safety_report_id": result.safety_report_id}
            return result.model_dump(mode="json")
        except Exception as exc:
            return {"status": "FAILED", "errors": [str(exc)]}
    if args.command == "kiwoom-mock-adapter-gap-report":
        try:
            result = _run_kiwoom_mock_adapter_draft_mapping(args.fixture_file).gap_report
            if args.output_file:
                args.output_file.write_text(result.model_dump_json(indent=2), encoding="utf-8")
                return {"status": "COMPLETED", "output_file": str(args.output_file), "gap_report_id": result.gap_report_id}
            return result.model_dump(mode="json")
        except Exception as exc:
            return {"status": "FAILED", "errors": [str(exc)]}
    if args.command == "kiwoom-mock-credential-boundary-check":
        try:
            result = _run_kiwoom_mock_credential_boundary(args.fixture_file)
            output = {
                "mock_only": True,
                "credential_boundary_only": True,
                "disabled_by_default": True,
                "explicit_opt_in_required": True,
                "local_file_only": True,
                "offline_only": True,
                "non_executable": True,
                "no_credentials_loaded": True,
                "no_environment_read": True,
                "no_credential_file_read": True,
                "no_token_issued": True,
                "no_token_revoked": True,
                "no_api_call": True,
                "no_mockapi_call": True,
                "no_websocket_connection": True,
                "no_network_call": True,
                "no_real_order": True,
                "no_live_trading": True,
                "no_live_prod": True,
                "no_account_mutation": True,
                "no_production_domain_execution": True,
                "no_cloud_llm": True,
                "no_local_llm_runtime": True,
                "credential_boundary": result.model_dump(mode="json"),
            }
            if args.output_file:
                args.output_file.write_text(json.dumps(output, indent=2), encoding="utf-8")
                return {"status": "COMPLETED", "output_file": str(args.output_file), "config_id": result.config_id}
            return output
        except Exception as exc:
            return {"status": "FAILED", "errors": [str(exc)]}
    if args.command == "kiwoom-mock-credential-domain-policy-report":
        try:
            result = _run_kiwoom_mock_credential_boundary(args.fixture_file).domain_policy
            if args.output_file:
                args.output_file.write_text(result.model_dump_json(indent=2), encoding="utf-8")
                return {"status": "COMPLETED", "output_file": str(args.output_file), "domain_policy_id": result.domain_policy_id}
            return result.model_dump(mode="json")
        except Exception as exc:
            return {"status": "FAILED", "errors": [str(exc)]}
    if args.command == "kiwoom-mock-credential-opt-in-report":
        try:
            result = _run_kiwoom_mock_credential_boundary(args.fixture_file).opt_in_gate
            if args.output_file:
                args.output_file.write_text(result.model_dump_json(indent=2), encoding="utf-8")
                return {"status": "COMPLETED", "output_file": str(args.output_file), "opt_in_gate_id": result.opt_in_gate_id}
            return result.model_dump(mode="json")
        except Exception as exc:
            return {"status": "FAILED", "errors": [str(exc)]}
    if args.command == "kiwoom-mock-credential-safety-report":
        try:
            result = _run_kiwoom_mock_credential_boundary(args.fixture_file).safety_report
            if args.output_file:
                args.output_file.write_text(result.model_dump_json(indent=2), encoding="utf-8")
                return {"status": "COMPLETED", "output_file": str(args.output_file), "safety_report_id": result.safety_report_id}
            return result.model_dump(mode="json")
        except Exception as exc:
            return {"status": "FAILED", "errors": [str(exc)]}
    if args.command == "kiwoom-mock-credential-gap-report":
        try:
            result = _run_kiwoom_mock_credential_boundary(args.fixture_file).gap_report
            if args.output_file:
                args.output_file.write_text(result.model_dump_json(indent=2), encoding="utf-8")
                return {"status": "COMPLETED", "output_file": str(args.output_file), "gap_report_id": result.gap_report_id}
            return result.model_dump(mode="json")
        except Exception as exc:
            return {"status": "FAILED", "errors": [str(exc)]}
    if args.command == "kiwoom-mock-oauth-token-request-draft":
        try:
            result = _run_kiwoom_mock_oauth_draft_boundary(args.fixture_file).token_request_draft
            if args.output_file:
                args.output_file.write_text(result.model_dump_json(indent=2), encoding="utf-8")
                return {"status": "COMPLETED", "output_file": str(args.output_file), "draft_id": result.draft_id}
            return result.model_dump(mode="json")
        except Exception as exc:
            return {"status": "FAILED", "errors": [str(exc)]}
    if args.command == "kiwoom-mock-oauth-token-response-draft-report":
        try:
            result = _run_kiwoom_mock_oauth_draft_boundary(args.fixture_file).token_response_draft
            if args.output_file:
                args.output_file.write_text(result.model_dump_json(indent=2), encoding="utf-8")
                return {"status": "COMPLETED", "output_file": str(args.output_file), "response_draft_id": result.response_draft_id}
            return result.model_dump(mode="json")
        except Exception as exc:
            return {"status": "FAILED", "errors": [str(exc)]}
    if args.command == "kiwoom-mock-oauth-token-revoke-draft":
        try:
            result = _run_kiwoom_mock_oauth_draft_boundary(args.fixture_file).token_revoke_draft
            if args.output_file:
                args.output_file.write_text(result.model_dump_json(indent=2), encoding="utf-8")
                return {"status": "COMPLETED", "output_file": str(args.output_file), "draft_id": result.draft_id}
            return result.model_dump(mode="json")
        except Exception as exc:
            return {"status": "FAILED", "errors": [str(exc)]}
    if args.command == "kiwoom-mock-oauth-token-lifecycle-report":
        try:
            result = _run_kiwoom_mock_oauth_draft_boundary(args.fixture_file).token_lifecycle_policy
            if args.output_file:
                args.output_file.write_text(result.model_dump_json(indent=2), encoding="utf-8")
                return {"status": "COMPLETED", "output_file": str(args.output_file), "policy_id": result.policy_id}
            return result.model_dump(mode="json")
        except Exception as exc:
            return {"status": "FAILED", "errors": [str(exc)]}
    if args.command == "kiwoom-mock-oauth-safety-report":
        try:
            result = _run_kiwoom_mock_oauth_draft_boundary(args.fixture_file).safety_report
            if args.output_file:
                args.output_file.write_text(result.model_dump_json(indent=2), encoding="utf-8")
                return {"status": "COMPLETED", "output_file": str(args.output_file), "safety_report_id": result.safety_report_id}
            return result.model_dump(mode="json")
        except Exception as exc:
            return {"status": "FAILED", "errors": [str(exc)]}
    if args.command == "kiwoom-mock-oauth-gap-report":
        try:
            result = _run_kiwoom_mock_oauth_draft_boundary(args.fixture_file).gap_report
            if args.output_file:
                args.output_file.write_text(result.model_dump_json(indent=2), encoding="utf-8")
                return {"status": "COMPLETED", "output_file": str(args.output_file), "gap_report_id": result.gap_report_id}
            return result.model_dump(mode="json")
        except Exception as exc:
            return {"status": "FAILED", "errors": [str(exc)]}
    if args.command == "kiwoom-mock-oauth-token-request-execute":
        try:
            result = _run_kiwoom_mock_oauth_execution(
                args.fixture_file,
                execute=args.execute,
                acknowledge_mock_oauth_execution=args.acknowledge_mock_oauth_execution,
                mock_domain=args.mock_domain,
            )
            if args.output_file:
                args.output_file.write_text(result.model_dump_json(indent=2), encoding="utf-8")
                return {"status": "COMPLETED", "output_file": str(args.output_file), "execution_result_id": result.execution_result_id}
            return result.model_dump(mode="json")
        except Exception as exc:
            return {"status": "FAILED", "errors": [str(exc)]}
    if args.command == "kiwoom-mock-oauth-token-revoke-execute":
        try:
            result = _run_kiwoom_mock_oauth_execution(
                args.fixture_file,
                execute=args.execute,
                acknowledge_mock_oauth_execution=args.acknowledge_mock_oauth_execution,
                mock_domain=args.mock_domain,
            )
            if args.output_file:
                args.output_file.write_text(result.model_dump_json(indent=2), encoding="utf-8")
                return {"status": "COMPLETED", "output_file": str(args.output_file), "execution_result_id": result.execution_result_id}
            return result.model_dump(mode="json")
        except Exception as exc:
            return {"status": "FAILED", "errors": [str(exc)]}
    if args.command == "kiwoom-mock-oauth-execution-safety-report":
        try:
            result = build_kiwoom_mock_oauth_execution_safety_report(
                _load_kiwoom_mock_oauth_execution_fixture_or_raise(args.fixture_file)
            )
            if args.output_file:
                args.output_file.write_text(result.model_dump_json(indent=2), encoding="utf-8")
                return {"status": "COMPLETED", "output_file": str(args.output_file), "safety_report_id": result.safety_report_id}
            return result.model_dump(mode="json")
        except Exception as exc:
            return {"status": "FAILED", "errors": [str(exc)]}
    if args.command == "kiwoom-mock-oauth-execution-gap-report":
        try:
            result = build_kiwoom_mock_oauth_execution_gap_report(
                _load_kiwoom_mock_oauth_execution_fixture_or_raise(args.fixture_file)
            )
            if args.output_file:
                args.output_file.write_text(result.model_dump_json(indent=2), encoding="utf-8")
                return {"status": "COMPLETED", "output_file": str(args.output_file), "gap_report_id": result.gap_report_id}
            return result.model_dump(mode="json")
        except Exception as exc:
            return {"status": "FAILED", "errors": [str(exc)]}
    if args.command == "kiwoom-mock-oauth-execution-audit-report":
        try:
            result = _load_kiwoom_mock_oauth_execution_fixture_or_raise(args.fixture_file).audit_records[0]
            if args.output_file:
                args.output_file.write_text(result.model_dump_json(indent=2), encoding="utf-8")
                return {"status": "COMPLETED", "output_file": str(args.output_file), "audit_record_id": result.audit_record_id}
            return result.model_dump(mode="json")
        except Exception as exc:
            return {"status": "FAILED", "errors": [str(exc)]}
    if args.command == "kiwoom-mock-api-transport-request-envelope-draft":
        try:
            result = _run_kiwoom_mock_api_transport_draft_boundary(args.fixture_file).request_envelope_draft
            if args.output_file:
                args.output_file.write_text(result.model_dump_json(indent=2), encoding="utf-8")
                return {"status": "COMPLETED", "output_file": str(args.output_file), "draft_id": result.draft_id}
            return result.model_dump(mode="json")
        except Exception as exc:
            return {"status": "FAILED", "errors": [str(exc)]}
    if args.command == "kiwoom-mock-api-transport-policy-report":
        try:
            result = _run_kiwoom_mock_api_transport_draft_boundary(args.fixture_file).transport_policy
            if args.output_file:
                args.output_file.write_text(result.model_dump_json(indent=2), encoding="utf-8")
                return {"status": "COMPLETED", "output_file": str(args.output_file), "policy_id": result.policy_id}
            return result.model_dump(mode="json")
        except Exception as exc:
            return {"status": "FAILED", "errors": [str(exc)]}
    if args.command == "kiwoom-mock-api-retry-timeout-report":
        try:
            result = _run_kiwoom_mock_api_transport_draft_boundary(args.fixture_file).retry_timeout_policy
            if args.output_file:
                args.output_file.write_text(result.model_dump_json(indent=2), encoding="utf-8")
                return {"status": "COMPLETED", "output_file": str(args.output_file), "policy_id": result.policy_id}
            return result.model_dump(mode="json")
        except Exception as exc:
            return {"status": "FAILED", "errors": [str(exc)]}
    if args.command == "kiwoom-mock-api-error-response-draft-report":
        try:
            result = _run_kiwoom_mock_api_transport_draft_boundary(args.fixture_file).error_response_draft
            if args.output_file:
                args.output_file.write_text(result.model_dump_json(indent=2), encoding="utf-8")
                return {
                    "status": "COMPLETED",
                    "output_file": str(args.output_file),
                    "error_draft_id": result.error_draft_id,
                }
            return result.model_dump(mode="json")
        except Exception as exc:
            return {"status": "FAILED", "errors": [str(exc)]}
    if args.command == "kiwoom-mock-api-transport-safety-report":
        try:
            result = _run_kiwoom_mock_api_transport_draft_boundary(args.fixture_file).safety_report
            if args.output_file:
                args.output_file.write_text(result.model_dump_json(indent=2), encoding="utf-8")
                return {
                    "status": "COMPLETED",
                    "output_file": str(args.output_file),
                    "safety_report_id": result.safety_report_id,
                }
            return result.model_dump(mode="json")
        except Exception as exc:
            return {"status": "FAILED", "errors": [str(exc)]}
    if args.command == "kiwoom-mock-api-transport-gap-report":
        try:
            result = _run_kiwoom_mock_api_transport_draft_boundary(args.fixture_file).gap_report
            if args.output_file:
                args.output_file.write_text(result.model_dump_json(indent=2), encoding="utf-8")
                return {"status": "COMPLETED", "output_file": str(args.output_file), "gap_report_id": result.gap_report_id}
            return result.model_dump(mode="json")
        except Exception as exc:
            return {"status": "FAILED", "errors": [str(exc)]}
    if args.command == "kiwoom-mock-api-preflight-check":
        try:
            result = _run_kiwoom_mock_api_preflight_gate(args.fixture_file)
            if args.output_file:
                args.output_file.write_text(result.model_dump_json(indent=2), encoding="utf-8")
                return {"status": "COMPLETED", "output_file": str(args.output_file), "config_id": result.config_id}
            return result.model_dump(mode="json")
        except Exception as exc:
            return {"status": "FAILED", "errors": [str(exc)]}
    if args.command == "kiwoom-mock-api-preflight-readiness-report":
        try:
            result = _run_kiwoom_mock_api_preflight_gate(args.fixture_file).readiness_report
            if args.output_file:
                args.output_file.write_text(result.model_dump_json(indent=2), encoding="utf-8")
                return {
                    "status": "COMPLETED",
                    "output_file": str(args.output_file),
                    "readiness_report_id": result.readiness_report_id,
                }
            return result.model_dump(mode="json")
        except Exception as exc:
            return {"status": "FAILED", "errors": [str(exc)]}
    if args.command == "kiwoom-mock-api-preflight-safety-report":
        try:
            result = _run_kiwoom_mock_api_preflight_gate(args.fixture_file).safety_report
            if args.output_file:
                args.output_file.write_text(result.model_dump_json(indent=2), encoding="utf-8")
                return {
                    "status": "COMPLETED",
                    "output_file": str(args.output_file),
                    "safety_report_id": result.safety_report_id,
                }
            return result.model_dump(mode="json")
        except Exception as exc:
            return {"status": "FAILED", "errors": [str(exc)]}
    if args.command == "kiwoom-mock-api-preflight-gap-report":
        try:
            result = _run_kiwoom_mock_api_preflight_gate(args.fixture_file).gap_report
            if args.output_file:
                args.output_file.write_text(result.model_dump_json(indent=2), encoding="utf-8")
                return {"status": "COMPLETED", "output_file": str(args.output_file), "gap_report_id": result.gap_report_id}
            return result.model_dump(mode="json")
        except Exception as exc:
            return {"status": "FAILED", "errors": [str(exc)]}
    if args.command == "kiwoom-mock-api-preflight-audit-report":
        try:
            result = _run_kiwoom_mock_api_preflight_gate(args.fixture_file).audit_records[0]
            if args.output_file:
                args.output_file.write_text(result.model_dump_json(indent=2), encoding="utf-8")
                return {"status": "COMPLETED", "output_file": str(args.output_file), "audit_record_id": result.audit_record_id}
            return result.model_dump(mode="json")
        except Exception as exc:
            return {"status": "FAILED", "errors": [str(exc)]}
    if args.command == "kiwoom-mock-market-data-request-execute":
        try:
            result = _run_kiwoom_mock_market_data_execution(
                args.fixture_file,
                execute=args.execute,
                acknowledge_mock_market_data_execution=args.acknowledge_mock_market_data_execution,
                mock_domain=args.mock_domain,
            )
            if args.output_file:
                args.output_file.write_text(result.model_dump_json(indent=2), encoding="utf-8")
                return {
                    "status": "COMPLETED",
                    "output_file": str(args.output_file),
                    "execution_result_id": result.execution_result_id,
                }
            return result.model_dump(mode="json")
        except Exception as exc:
            return {"status": "FAILED", "errors": [str(exc)]}
    if args.command == "kiwoom-mock-market-data-response-report":
        try:
            result = build_kiwoom_mock_market_data_response_report(
                _load_kiwoom_mock_market_data_execution_fixture_or_raise(args.fixture_file)
            )
            if args.output_file:
                args.output_file.write_text(result.model_dump_json(indent=2), encoding="utf-8")
                return {
                    "status": "COMPLETED",
                    "output_file": str(args.output_file),
                    "response_object_id": result.response_object_id,
                }
            return result.model_dump(mode="json")
        except Exception as exc:
            return {"status": "FAILED", "errors": [str(exc)]}
    if args.command == "kiwoom-mock-market-data-safety-report":
        try:
            result = build_kiwoom_mock_market_data_execution_safety_report(
                _load_kiwoom_mock_market_data_execution_fixture_or_raise(args.fixture_file)
            )
            if args.output_file:
                args.output_file.write_text(result.model_dump_json(indent=2), encoding="utf-8")
                return {
                    "status": "COMPLETED",
                    "output_file": str(args.output_file),
                    "safety_report_id": result.safety_report_id,
                }
            return result.model_dump(mode="json")
        except Exception as exc:
            return {"status": "FAILED", "errors": [str(exc)]}
    if args.command == "kiwoom-mock-market-data-gap-report":
        try:
            result = build_kiwoom_mock_market_data_execution_gap_report(
                _load_kiwoom_mock_market_data_execution_fixture_or_raise(args.fixture_file)
            )
            if args.output_file:
                args.output_file.write_text(result.model_dump_json(indent=2), encoding="utf-8")
                return {"status": "COMPLETED", "output_file": str(args.output_file), "gap_report_id": result.gap_report_id}
            return result.model_dump(mode="json")
        except Exception as exc:
            return {"status": "FAILED", "errors": [str(exc)]}
    if args.command == "kiwoom-mock-market-data-audit-report":
        try:
            result = _load_kiwoom_mock_market_data_execution_fixture_or_raise(args.fixture_file).audit_records[0]
            if args.output_file:
                args.output_file.write_text(result.model_dump_json(indent=2), encoding="utf-8")
                return {
                    "status": "COMPLETED",
                    "output_file": str(args.output_file),
                    "audit_record_id": result.audit_record_id,
                }
            return result.model_dump(mode="json")
        except Exception as exc:
            return {"status": "FAILED", "errors": [str(exc)]}
    if args.command == "quant-robustness-check":
        try:
            result = _run_quant_strategy_robustness(args.fixture_file).robustness_readiness_report
            if args.output_file:
                args.output_file.write_text(result.model_dump_json(indent=2), encoding="utf-8")
                return {"status": "COMPLETED", "output_file": str(args.output_file), "readiness_report_id": result.readiness_report_id}
            return result.model_dump(mode="json")
        except Exception as exc:
            return {"status": "FAILED", "errors": [str(exc)]}
    if args.command == "quant-survivorship-bias-report":
        try:
            result = _run_quant_strategy_robustness(args.fixture_file).survivorship_bias_report
            if args.output_file:
                args.output_file.write_text(result.model_dump_json(indent=2), encoding="utf-8")
                return {"status": "COMPLETED", "output_file": str(args.output_file), "report_id": result.report_id}
            return result.model_dump(mode="json")
        except Exception as exc:
            return {"status": "FAILED", "errors": [str(exc)]}
    if args.command == "quant-point-in-time-leakage-report":
        try:
            result = _run_quant_strategy_robustness(args.fixture_file).point_in_time_leakage_report
            if args.output_file:
                args.output_file.write_text(result.model_dump_json(indent=2), encoding="utf-8")
                return {"status": "COMPLETED", "output_file": str(args.output_file), "report_id": result.report_id}
            return result.model_dump(mode="json")
        except Exception as exc:
            return {"status": "FAILED", "errors": [str(exc)]}
    if args.command == "quant-walk-forward-policy-report":
        try:
            result = _run_quant_strategy_robustness(args.fixture_file).walk_forward_policy_report
            if args.output_file:
                args.output_file.write_text(result.model_dump_json(indent=2), encoding="utf-8")
                return {"status": "COMPLETED", "output_file": str(args.output_file), "report_id": result.report_id}
            return result.model_dump(mode="json")
        except Exception as exc:
            return {"status": "FAILED", "errors": [str(exc)]}
    if args.command == "quant-data-snooping-report":
        try:
            result = _run_quant_strategy_robustness(args.fixture_file).data_snooping_report
            if args.output_file:
                args.output_file.write_text(result.model_dump_json(indent=2), encoding="utf-8")
                return {"status": "COMPLETED", "output_file": str(args.output_file), "report_id": result.report_id}
            return result.model_dump(mode="json")
        except Exception as exc:
            return {"status": "FAILED", "errors": [str(exc)]}
    if args.command == "quant-strategy-diversification-report":
        try:
            result = _run_quant_strategy_robustness(args.fixture_file).strategy_diversification_report
            if args.output_file:
                args.output_file.write_text(result.model_dump_json(indent=2), encoding="utf-8")
                return {"status": "COMPLETED", "output_file": str(args.output_file), "report_id": result.report_id}
            return result.model_dump(mode="json")
        except Exception as exc:
            return {"status": "FAILED", "errors": [str(exc)]}
    if args.command == "quant-regime-readiness-report":
        try:
            result = _run_quant_strategy_robustness(args.fixture_file).regime_readiness_report
            if args.output_file:
                args.output_file.write_text(result.model_dump_json(indent=2), encoding="utf-8")
                return {"status": "COMPLETED", "output_file": str(args.output_file), "report_id": result.report_id}
            return result.model_dump(mode="json")
        except Exception as exc:
            return {"status": "FAILED", "errors": [str(exc)]}
    if args.command == "point-in-time-universe-check":
        try:
            result = _run_point_in_time_universe_gate(args.fixture_file).dataset_promotion_readiness_report
            if args.output_file:
                args.output_file.write_text(result.model_dump_json(indent=2), encoding="utf-8")
                return {"status": "COMPLETED", "output_file": str(args.output_file), "report_id": result.report_id}
            return result.model_dump(mode="json")
        except Exception as exc:
            return {"status": "FAILED", "errors": [str(exc)]}
    if args.command == "point-in-time-universe-report":
        try:
            result = _run_point_in_time_universe_gate(args.fixture_file).point_in_time_universe_report
            if args.output_file:
                args.output_file.write_text(result.model_dump_json(indent=2), encoding="utf-8")
                return {"status": "COMPLETED", "output_file": str(args.output_file), "report_id": result.report_id}
            return result.model_dump(mode="json")
        except Exception as exc:
            return {"status": "FAILED", "errors": [str(exc)]}
    if args.command == "survivorship-bias-dataset-report":
        try:
            result = _run_point_in_time_universe_gate(args.fixture_file).survivorship_bias_report
            if args.output_file:
                args.output_file.write_text(result.model_dump_json(indent=2), encoding="utf-8")
                return {"status": "COMPLETED", "output_file": str(args.output_file), "report_id": result.report_id}
            return result.model_dump(mode="json")
        except Exception as exc:
            return {"status": "FAILED", "errors": [str(exc)]}
    if args.command == "security-lifecycle-coverage-report":
        try:
            result = _run_point_in_time_universe_gate(args.fixture_file).security_lifecycle_coverage_report
            if args.output_file:
                args.output_file.write_text(result.model_dump_json(indent=2), encoding="utf-8")
                return {"status": "COMPLETED", "output_file": str(args.output_file), "report_id": result.report_id}
            return result.model_dump(mode="json")
        except Exception as exc:
            return {"status": "FAILED", "errors": [str(exc)]}
    if args.command == "dataset-leakage-report":
        try:
            result = _run_point_in_time_universe_gate(args.fixture_file).leakage_report
            if args.output_file:
                args.output_file.write_text(result.model_dump_json(indent=2), encoding="utf-8")
                return {"status": "COMPLETED", "output_file": str(args.output_file), "report_id": result.report_id}
            return result.model_dump(mode="json")
        except Exception as exc:
            return {"status": "FAILED", "errors": [str(exc)]}
    if args.command == "dataset-promotion-readiness-report":
        try:
            result = _run_point_in_time_universe_gate(args.fixture_file).dataset_promotion_readiness_report
            if args.output_file:
                args.output_file.write_text(result.model_dump_json(indent=2), encoding="utf-8")
                return {"status": "COMPLETED", "output_file": str(args.output_file), "report_id": result.report_id}
            return result.model_dump(mode="json")
        except Exception as exc:
            return {"status": "FAILED", "errors": [str(exc)]}
    if args.command == "walk-forward-validation-check":
        try:
            result = _run_walk_forward_validation(args.fixture_file).promotion_readiness_report
            if args.output_file:
                args.output_file.write_text(result.model_dump_json(indent=2), encoding="utf-8")
                return {"status": "COMPLETED", "output_file": str(args.output_file), "report_id": result.report_id}
            return result.model_dump(mode="json")
        except Exception as exc:
            return {"status": "FAILED", "errors": [str(exc)]}
    if args.command == "walk-forward-split-report":
        try:
            result = _run_walk_forward_validation(args.fixture_file).walk_forward_split_report
            if args.output_file:
                args.output_file.write_text(result.model_dump_json(indent=2), encoding="utf-8")
                return {"status": "COMPLETED", "output_file": str(args.output_file), "report_id": result.report_id}
            return result.model_dump(mode="json")
        except Exception as exc:
            return {"status": "FAILED", "errors": [str(exc)]}
    if args.command == "data-snooping-report":
        try:
            result = _run_walk_forward_validation(args.fixture_file).data_snooping_report
            if args.output_file:
                args.output_file.write_text(result.model_dump_json(indent=2), encoding="utf-8")
                return {"status": "COMPLETED", "output_file": str(args.output_file), "report_id": result.report_id}
            return result.model_dump(mode="json")
        except Exception as exc:
            return {"status": "FAILED", "errors": [str(exc)]}
    if args.command == "experiment-lineage-report":
        try:
            result = _run_walk_forward_validation(args.fixture_file).experiment_lineage_report
            if args.output_file:
                args.output_file.write_text(result.model_dump_json(indent=2), encoding="utf-8")
                return {"status": "COMPLETED", "output_file": str(args.output_file), "report_id": result.report_id}
            return result.model_dump(mode="json")
        except Exception as exc:
            return {"status": "FAILED", "errors": [str(exc)]}
    if args.command == "parameter-search-pressure-report":
        try:
            result = _run_walk_forward_validation(args.fixture_file).parameter_search_pressure_report
            if args.output_file:
                args.output_file.write_text(result.model_dump_json(indent=2), encoding="utf-8")
                return {"status": "COMPLETED", "output_file": str(args.output_file), "report_id": result.report_id}
            return result.model_dump(mode="json")
        except Exception as exc:
            return {"status": "FAILED", "errors": [str(exc)]}
    if args.command == "final-test-contamination-report":
        try:
            result = _run_walk_forward_validation(args.fixture_file).final_test_contamination_report
            if args.output_file:
                args.output_file.write_text(result.model_dump_json(indent=2), encoding="utf-8")
                return {"status": "COMPLETED", "output_file": str(args.output_file), "report_id": result.report_id}
            return result.model_dump(mode="json")
        except Exception as exc:
            return {"status": "FAILED", "errors": [str(exc)]}
    if args.command == "strategy-stability-report":
        try:
            result = _run_walk_forward_validation(args.fixture_file).stability_report
            if args.output_file:
                args.output_file.write_text(result.model_dump_json(indent=2), encoding="utf-8")
                return {"status": "COMPLETED", "output_file": str(args.output_file), "report_id": result.report_id}
            return result.model_dump(mode="json")
        except Exception as exc:
            return {"status": "FAILED", "errors": [str(exc)]}
    if args.command == "validation-promotion-readiness-report":
        try:
            result = _run_walk_forward_validation(args.fixture_file).promotion_readiness_report
            if args.output_file:
                args.output_file.write_text(result.model_dump_json(indent=2), encoding="utf-8")
                return {"status": "COMPLETED", "output_file": str(args.output_file), "report_id": result.report_id}
            return result.model_dump(mode="json")
        except Exception as exc:
            return {"status": "FAILED", "errors": [str(exc)]}
    if args.command == "training-pipeline-promotion-check":
        try:
            result = _run_training_pipeline_promotion(args.fixture_file).model_promotion_readiness_report
            if args.output_file:
                args.output_file.write_text(result.model_dump_json(indent=2), encoding="utf-8")
                return {"status": "COMPLETED", "output_file": str(args.output_file), "report_id": result.report_id}
            return result.model_dump(mode="json")
        except Exception as exc:
            return {"status": "FAILED", "errors": [str(exc)]}
    if args.command == "training-dataset-eligibility-report":
        try:
            result = _run_training_pipeline_promotion(args.fixture_file).training_eligibility_report
            if args.output_file:
                args.output_file.write_text(result.model_dump_json(indent=2), encoding="utf-8")
                return {"status": "COMPLETED", "output_file": str(args.output_file), "report_id": result.report_id}
            return result.model_dump(mode="json")
        except Exception as exc:
            return {"status": "FAILED", "errors": [str(exc)]}
    if args.command == "training-dependency-report":
        try:
            result = _run_training_pipeline_promotion(args.fixture_file).dependency_report
            if args.output_file:
                args.output_file.write_text(result.model_dump_json(indent=2), encoding="utf-8")
                return {"status": "COMPLETED", "output_file": str(args.output_file), "report_id": result.report_id}
            return result.model_dump(mode="json")
        except Exception as exc:
            return {"status": "FAILED", "errors": [str(exc)]}
    if args.command == "training-leakage-overfit-risk-report":
        try:
            result = _run_training_pipeline_promotion(args.fixture_file).leakage_overfit_risk_report
            if args.output_file:
                args.output_file.write_text(result.model_dump_json(indent=2), encoding="utf-8")
                return {"status": "COMPLETED", "output_file": str(args.output_file), "report_id": result.report_id}
            return result.model_dump(mode="json")
        except Exception as exc:
            return {"status": "FAILED", "errors": [str(exc)]}
    if args.command == "training-reproducibility-report":
        try:
            result = _run_training_pipeline_promotion(args.fixture_file).reproducibility_report
            if args.output_file:
                args.output_file.write_text(result.model_dump_json(indent=2), encoding="utf-8")
                return {"status": "COMPLETED", "output_file": str(args.output_file), "report_id": result.report_id}
            return result.model_dump(mode="json")
        except Exception as exc:
            return {"status": "FAILED", "errors": [str(exc)]}
    if args.command == "model-artifact-policy-report":
        try:
            result = _run_training_pipeline_promotion(args.fixture_file).model_artifact_policy_report
            if args.output_file:
                args.output_file.write_text(result.model_dump_json(indent=2), encoding="utf-8")
                return {"status": "COMPLETED", "output_file": str(args.output_file), "report_id": result.report_id}
            return result.model_dump(mode="json")
        except Exception as exc:
            return {"status": "FAILED", "errors": [str(exc)]}
    if args.command == "model-promotion-readiness-report":
        try:
            result = _run_training_pipeline_promotion(args.fixture_file).model_promotion_readiness_report
            if args.output_file:
                args.output_file.write_text(result.model_dump_json(indent=2), encoding="utf-8")
                return {"status": "COMPLETED", "output_file": str(args.output_file), "report_id": result.report_id}
            return result.model_dump(mode="json")
        except Exception as exc:
            return {"status": "FAILED", "errors": [str(exc)]}
    if args.command == "strategy-ensemble-check":
        try:
            result = _run_strategy_ensemble_alpha_gate(args.fixture_file).ensemble_promotion_readiness_report
            if args.output_file:
                args.output_file.write_text(result.model_dump_json(indent=2), encoding="utf-8")
                return {"status": "COMPLETED", "output_file": str(args.output_file), "report_id": result.report_id}
            return result.model_dump(mode="json")
        except Exception as exc:
            return {"status": "FAILED", "errors": [str(exc)]}
    if args.command == "alpha-candidate-report":
        try:
            result = _run_strategy_ensemble_alpha_gate(args.fixture_file).alpha_candidate_report
            if args.output_file:
                args.output_file.write_text(result.model_dump_json(indent=2), encoding="utf-8")
                return {"status": "COMPLETED", "output_file": str(args.output_file), "report_id": result.report_id}
            return result.model_dump(mode="json")
        except Exception as exc:
            return {"status": "FAILED", "errors": [str(exc)]}
    if args.command == "strategy-family-diversification-report":
        try:
            result = _run_strategy_ensemble_alpha_gate(args.fixture_file).strategy_family_diversification_report
            if args.output_file:
                args.output_file.write_text(result.model_dump_json(indent=2), encoding="utf-8")
                return {"status": "COMPLETED", "output_file": str(args.output_file), "report_id": result.report_id}
            return result.model_dump(mode="json")
        except Exception as exc:
            return {"status": "FAILED", "errors": [str(exc)]}
    if args.command == "alpha-correlation-risk-report":
        try:
            result = _run_strategy_ensemble_alpha_gate(args.fixture_file).alpha_correlation_risk_report
            if args.output_file:
                args.output_file.write_text(result.model_dump_json(indent=2), encoding="utf-8")
                return {"status": "COMPLETED", "output_file": str(args.output_file), "report_id": result.report_id}
            return result.model_dump(mode="json")
        except Exception as exc:
            return {"status": "FAILED", "errors": [str(exc)]}
    if args.command == "drawdown-co-movement-report":
        try:
            result = _run_strategy_ensemble_alpha_gate(args.fixture_file).drawdown_co_movement_report
            if args.output_file:
                args.output_file.write_text(result.model_dump_json(indent=2), encoding="utf-8")
                return {"status": "COMPLETED", "output_file": str(args.output_file), "report_id": result.report_id}
            return result.model_dump(mode="json")
        except Exception as exc:
            return {"status": "FAILED", "errors": [str(exc)]}
    if args.command == "regime-overlap-report":
        try:
            result = _run_strategy_ensemble_alpha_gate(args.fixture_file).regime_overlap_report
            if args.output_file:
                args.output_file.write_text(result.model_dump_json(indent=2), encoding="utf-8")
                return {"status": "COMPLETED", "output_file": str(args.output_file), "report_id": result.report_id}
            return result.model_dump(mode="json")
        except Exception as exc:
            return {"status": "FAILED", "errors": [str(exc)]}
    if args.command == "alpha-portfolio-concentration-report":
        try:
            result = _run_strategy_ensemble_alpha_gate(args.fixture_file).alpha_portfolio_concentration_report
            if args.output_file:
                args.output_file.write_text(result.model_dump_json(indent=2), encoding="utf-8")
                return {"status": "COMPLETED", "output_file": str(args.output_file), "report_id": result.report_id}
            return result.model_dump(mode="json")
        except Exception as exc:
            return {"status": "FAILED", "errors": [str(exc)]}
    if args.command == "ensemble-promotion-readiness-report":
        try:
            result = _run_strategy_ensemble_alpha_gate(args.fixture_file).ensemble_promotion_readiness_report
            if args.output_file:
                args.output_file.write_text(result.model_dump_json(indent=2), encoding="utf-8")
                return {"status": "COMPLETED", "output_file": str(args.output_file), "report_id": result.report_id}
            return result.model_dump(mode="json")
        except Exception as exc:
            return {"status": "FAILED", "errors": [str(exc)]}
    if args.command == "regime-allocation-learning-check":
        try:
            result = _run_regime_allocation_learning_dataset(args.fixture_file).learning_dataset_readiness_report
            if args.output_file:
                args.output_file.write_text(result.model_dump_json(indent=2), encoding="utf-8")
                return {"status": "COMPLETED", "output_file": str(args.output_file), "report_id": result.report_id}
            return result.model_dump(mode="json")
        except Exception as exc:
            return {"status": "FAILED", "errors": [str(exc)]}
    if args.command == "regime-feature-report":
        try:
            result = _run_regime_allocation_learning_dataset(args.fixture_file).regime_feature_report
            if args.output_file:
                args.output_file.write_text(result.model_dump_json(indent=2), encoding="utf-8")
                return {"status": "COMPLETED", "output_file": str(args.output_file), "report_id": result.report_id}
            return result.model_dump(mode="json")
        except Exception as exc:
            return {"status": "FAILED", "errors": [str(exc)]}
    if args.command == "allocation-action-candidate-report":
        try:
            result = _run_regime_allocation_learning_dataset(args.fixture_file).action_candidate_report
            if args.output_file:
                args.output_file.write_text(result.model_dump_json(indent=2), encoding="utf-8")
                return {"status": "COMPLETED", "output_file": str(args.output_file), "report_id": result.report_id}
            return result.model_dump(mode="json")
        except Exception as exc:
            return {"status": "FAILED", "errors": [str(exc)]}
    if args.command == "hedge-inverse-eligibility-report":
        try:
            result = _run_regime_allocation_learning_dataset(args.fixture_file).hedge_inverse_eligibility_report
            if args.output_file:
                args.output_file.write_text(result.model_dump_json(indent=2), encoding="utf-8")
                return {"status": "COMPLETED", "output_file": str(args.output_file), "report_id": result.report_id}
            return result.model_dump(mode="json")
        except Exception as exc:
            return {"status": "FAILED", "errors": [str(exc)]}
    if args.command == "forward-outcome-label-report":
        try:
            result = _run_regime_allocation_learning_dataset(args.fixture_file).forward_outcome_label_report
            if args.output_file:
                args.output_file.write_text(result.model_dump_json(indent=2), encoding="utf-8")
                return {"status": "COMPLETED", "output_file": str(args.output_file), "report_id": result.report_id}
            return result.model_dump(mode="json")
        except Exception as exc:
            return {"status": "FAILED", "errors": [str(exc)]}
    if args.command == "allocation-reward-scoring-report":
        try:
            result = _run_regime_allocation_learning_dataset(args.fixture_file).allocation_reward_scoring_report
            if args.output_file:
                args.output_file.write_text(result.model_dump_json(indent=2), encoding="utf-8")
                return {"status": "COMPLETED", "output_file": str(args.output_file), "report_id": result.report_id}
            return result.model_dump(mode="json")
        except Exception as exc:
            return {"status": "FAILED", "errors": [str(exc)]}
    if args.command == "regime-allocation-leakage-report":
        try:
            result = _run_regime_allocation_learning_dataset(args.fixture_file).regime_allocation_leakage_report
            if args.output_file:
                args.output_file.write_text(result.model_dump_json(indent=2), encoding="utf-8")
                return {"status": "COMPLETED", "output_file": str(args.output_file), "report_id": result.report_id}
            return result.model_dump(mode="json")
        except Exception as exc:
            return {"status": "FAILED", "errors": [str(exc)]}
    if args.command == "regime-allocation-dataset-readiness-report":
        try:
            result = _run_regime_allocation_learning_dataset(args.fixture_file).learning_dataset_readiness_report
            if args.output_file:
                args.output_file.write_text(result.model_dump_json(indent=2), encoding="utf-8")
                return {"status": "COMPLETED", "output_file": str(args.output_file), "report_id": result.report_id}
            return result.model_dump(mode="json")
        except Exception as exc:
            return {"status": "FAILED", "errors": [str(exc)]}
    if args.command == "allocation-policy-training-check":
        try:
            result = _run_allocation_policy_training_sandbox(args.fixture_file).policy_promotion_readiness_report
            if args.output_file:
                args.output_file.write_text(result.model_dump_json(indent=2), encoding="utf-8")
                return {"status": "COMPLETED", "output_file": str(args.output_file), "report_id": result.report_id}
            return result.model_dump(mode="json")
        except Exception as exc:
            return {"status": "FAILED", "errors": [str(exc)]}
    if args.command == "allocation-policy-training-summary-report":
        try:
            result = _run_allocation_policy_training_sandbox(args.fixture_file).policy_training_summary_report
            if args.output_file:
                args.output_file.write_text(result.model_dump_json(indent=2), encoding="utf-8")
                return {"status": "COMPLETED", "output_file": str(args.output_file), "report_id": result.report_id}
            return result.model_dump(mode="json")
        except Exception as exc:
            return {"status": "FAILED", "errors": [str(exc)]}
    if args.command == "regime-action-selection-report":
        try:
            result = _run_allocation_policy_training_sandbox(args.fixture_file).regime_action_selection_report
            if args.output_file:
                args.output_file.write_text(result.model_dump_json(indent=2), encoding="utf-8")
                return {"status": "COMPLETED", "output_file": str(args.output_file), "report_id": result.report_id}
            return result.model_dump(mode="json")
        except Exception as exc:
            return {"status": "FAILED", "errors": [str(exc)]}
    if args.command == "allocation-policy-walk-forward-report":
        try:
            result = _run_allocation_policy_training_sandbox(args.fixture_file).allocation_policy_walk_forward_report
            if args.output_file:
                args.output_file.write_text(result.model_dump_json(indent=2), encoding="utf-8")
                return {"status": "COMPLETED", "output_file": str(args.output_file), "report_id": result.report_id}
            return result.model_dump(mode="json")
        except Exception as exc:
            return {"status": "FAILED", "errors": [str(exc)]}
    if args.command == "allocation-policy-risk-adjusted-report":
        try:
            result = _run_allocation_policy_training_sandbox(args.fixture_file).allocation_policy_risk_adjusted_report
            if args.output_file:
                args.output_file.write_text(result.model_dump_json(indent=2), encoding="utf-8")
                return {"status": "COMPLETED", "output_file": str(args.output_file), "report_id": result.report_id}
            return result.model_dump(mode="json")
        except Exception as exc:
            return {"status": "FAILED", "errors": [str(exc)]}
    if args.command == "allocation-policy-turnover-slippage-report":
        try:
            result = _run_allocation_policy_training_sandbox(args.fixture_file).allocation_policy_turnover_slippage_report
            if args.output_file:
                args.output_file.write_text(result.model_dump_json(indent=2), encoding="utf-8")
                return {"status": "COMPLETED", "output_file": str(args.output_file), "report_id": result.report_id}
            return result.model_dump(mode="json")
        except Exception as exc:
            return {"status": "FAILED", "errors": [str(exc)]}
    if args.command == "allocation-policy-drawdown-stability-report":
        try:
            result = _run_allocation_policy_training_sandbox(args.fixture_file).allocation_policy_drawdown_stability_report
            if args.output_file:
                args.output_file.write_text(result.model_dump_json(indent=2), encoding="utf-8")
                return {"status": "COMPLETED", "output_file": str(args.output_file), "report_id": result.report_id}
            return result.model_dump(mode="json")
        except Exception as exc:
            return {"status": "FAILED", "errors": [str(exc)]}
    if args.command == "allocation-policy-promotion-readiness-report":
        try:
            result = _run_allocation_policy_training_sandbox(args.fixture_file).policy_promotion_readiness_report
            if args.output_file:
                args.output_file.write_text(result.model_dump_json(indent=2), encoding="utf-8")
                return {"status": "COMPLETED", "output_file": str(args.output_file), "report_id": result.report_id}
            return result.model_dump(mode="json")
        except Exception as exc:
            return {"status": "FAILED", "errors": [str(exc)]}
    if args.command == "allocation-policy-artifact-report":
        try:
            result = _run_allocation_policy_training_sandbox(args.fixture_file).model_artifact_policy_report
            if args.output_file:
                args.output_file.write_text(result.model_dump_json(indent=2), encoding="utf-8")
                return {"status": "COMPLETED", "output_file": str(args.output_file), "report_id": result.report_id}
            return result.model_dump(mode="json")
        except Exception as exc:
            return {"status": "FAILED", "errors": [str(exc)]}
    if args.command == "cnn-fear-greed-collect":
        try:
            result = _run_cnn_fear_greed_collection(
                args.fixture_file,
                execute=args.execute,
                acknowledge_collection=args.acknowledge_cnn_fear_greed_collection,
            )
            if args.output_file:
                args.output_file.write_text(result.model_dump_json(indent=2), encoding="utf-8")
                return {"status": "COMPLETED", "output_file": str(args.output_file), "config_id": result.config_id}
            return result.model_dump(mode="json")
        except Exception as exc:
            return {"status": "FAILED", "errors": [str(exc)]}
    if args.command == "cnn-fear-greed-snapshot-report":
        try:
            result = _run_cnn_fear_greed_collection(args.fixture_file).snapshot_report
            if args.output_file:
                args.output_file.write_text(result.model_dump_json(indent=2), encoding="utf-8")
                return {"status": "COMPLETED", "output_file": str(args.output_file), "report_id": result.report_id}
            return result.model_dump(mode="json")
        except Exception as exc:
            return {"status": "FAILED", "errors": [str(exc)]}
    if args.command == "cnn-fear-greed-history-report":
        try:
            result = _run_cnn_fear_greed_collection(args.fixture_file).history_report
            if args.output_file:
                args.output_file.write_text(result.model_dump_json(indent=2), encoding="utf-8")
                return {"status": "COMPLETED", "output_file": str(args.output_file), "report_id": result.report_id}
            return result.model_dump(mode="json")
        except Exception as exc:
            return {"status": "FAILED", "errors": [str(exc)]}
    if args.command == "cnn-fear-greed-feature-integration-report":
        try:
            result = _run_cnn_fear_greed_collection(args.fixture_file).feature_integration_report
            if args.output_file:
                args.output_file.write_text(result.model_dump_json(indent=2), encoding="utf-8")
                return {"status": "COMPLETED", "output_file": str(args.output_file), "report_id": result.report_id}
            return result.model_dump(mode="json")
        except Exception as exc:
            return {"status": "FAILED", "errors": [str(exc)]}
    if args.command == "cnn-fear-greed-source-health-report":
        try:
            result = _run_cnn_fear_greed_collection(args.fixture_file).source_health_report
            if args.output_file:
                args.output_file.write_text(result.model_dump_json(indent=2), encoding="utf-8")
                return {"status": "COMPLETED", "output_file": str(args.output_file), "report_id": result.report_id}
            return result.model_dump(mode="json")
        except Exception as exc:
            return {"status": "FAILED", "errors": [str(exc)]}
    if args.command == "cnn-fear-greed-audit-report":
        try:
            result = _run_cnn_fear_greed_collection(args.fixture_file).audit_report
            if args.output_file:
                args.output_file.write_text(result.model_dump_json(indent=2), encoding="utf-8")
                return {"status": "COMPLETED", "output_file": str(args.output_file), "audit_record_id": result.audit_record_id}
            return result.model_dump(mode="json")
        except Exception as exc:
            return {"status": "FAILED", "errors": [str(exc)]}
    if args.command == "risk-adjusted-paper-eval-check":
        try:
            result = _run_risk_adjusted_paper_eval(args.fixture_file).pass_readiness_report
            if args.output_file:
                args.output_file.write_text(result.model_dump_json(indent=2), encoding="utf-8")
                return {"status": "COMPLETED", "output_file": str(args.output_file), "decision": result.decision.value}
            return result.model_dump(mode="json")
        except Exception as exc:
            return {"status": "FAILED", "errors": [str(exc)]}
    if args.command == "paper-evaluation-summary-report":
        try:
            result = _run_risk_adjusted_paper_eval(args.fixture_file).summary_report
            if args.output_file:
                args.output_file.write_text(result.model_dump_json(indent=2), encoding="utf-8")
                return {"status": "COMPLETED", "output_file": str(args.output_file), "decision": result.decision.value}
            return result.model_dump(mode="json")
        except Exception as exc:
            return {"status": "FAILED", "errors": [str(exc)]}
    if args.command == "virtual-portfolio-report":
        try:
            result = _run_risk_adjusted_paper_eval(args.fixture_file).virtual_portfolio_report
            if args.output_file:
                args.output_file.write_text(result.model_dump_json(indent=2), encoding="utf-8")
                return {"status": "COMPLETED", "output_file": str(args.output_file), "report_id": result.report_id}
            return result.model_dump(mode="json")
        except Exception as exc:
            return {"status": "FAILED", "errors": [str(exc)]}
    if args.command == "virtual-trade-ledger-report":
        try:
            result = _run_risk_adjusted_paper_eval(args.fixture_file).virtual_trade_ledger_report
            if args.output_file:
                args.output_file.write_text(result.model_dump_json(indent=2), encoding="utf-8")
                return {"status": "COMPLETED", "output_file": str(args.output_file), "report_id": result.report_id}
            return result.model_dump(mode="json")
        except Exception as exc:
            return {"status": "FAILED", "errors": [str(exc)]}
    if args.command == "paper-cost-slippage-report":
        try:
            result = _run_risk_adjusted_paper_eval(args.fixture_file).cost_slippage_report
            if args.output_file:
                args.output_file.write_text(result.model_dump_json(indent=2), encoding="utf-8")
                return {"status": "COMPLETED", "output_file": str(args.output_file), "report_id": result.report_id}
            return result.model_dump(mode="json")
        except Exception as exc:
            return {"status": "FAILED", "errors": [str(exc)]}
    if args.command == "paper-risk-adjusted-performance-report":
        try:
            result = _run_risk_adjusted_paper_eval(args.fixture_file).risk_adjusted_performance_report
            if args.output_file:
                args.output_file.write_text(result.model_dump_json(indent=2), encoding="utf-8")
                return {"status": "COMPLETED", "output_file": str(args.output_file), "report_id": result.report_id}
            return result.model_dump(mode="json")
        except Exception as exc:
            return {"status": "FAILED", "errors": [str(exc)]}
    if args.command == "paper-drawdown-exposure-report":
        try:
            result = _run_risk_adjusted_paper_eval(args.fixture_file).drawdown_exposure_report
            if args.output_file:
                args.output_file.write_text(result.model_dump_json(indent=2), encoding="utf-8")
                return {"status": "COMPLETED", "output_file": str(args.output_file), "report_id": result.report_id}
            return result.model_dump(mode="json")
        except Exception as exc:
            return {"status": "FAILED", "errors": [str(exc)]}
    if args.command == "paper-regime-fear-bucket-report":
        try:
            result = _run_risk_adjusted_paper_eval(args.fixture_file).regime_fear_bucket_report
            if args.output_file:
                args.output_file.write_text(result.model_dump_json(indent=2), encoding="utf-8")
                return {"status": "COMPLETED", "output_file": str(args.output_file), "report_id": result.report_id}
            return result.model_dump(mode="json")
        except Exception as exc:
            return {"status": "FAILED", "errors": [str(exc)]}
    if args.command == "paper-pass-readiness-report":
        try:
            result = _run_risk_adjusted_paper_eval(args.fixture_file).pass_readiness_report
            if args.output_file:
                args.output_file.write_text(result.model_dump_json(indent=2), encoding="utf-8")
                return {"status": "COMPLETED", "output_file": str(args.output_file), "decision": result.decision.value}
            return result.model_dump(mode="json")
        except Exception as exc:
            return {"status": "FAILED", "errors": [str(exc)]}
    if args.command == "controlled-mock-readiness-check":
        try:
            result = _run_controlled_mock_readiness(args.fixture_file).summary_report
            if args.output_file:
                args.output_file.write_text(result.model_dump_json(indent=2), encoding="utf-8")
                return {"status": "COMPLETED", "output_file": str(args.output_file), "decision": result.decision.value}
            return result.model_dump(mode="json")
        except Exception as exc:
            return {"status": "FAILED", "errors": [str(exc)]}
    if args.command == "mock-readiness-summary-report":
        try:
            result = _run_controlled_mock_readiness(args.fixture_file).summary_report
            if args.output_file:
                args.output_file.write_text(result.model_dump_json(indent=2), encoding="utf-8")
                return {"status": "COMPLETED", "output_file": str(args.output_file), "decision": result.decision.value}
            return result.model_dump(mode="json")
        except Exception as exc:
            return {"status": "FAILED", "errors": [str(exc)]}
    if args.command == "mock-readiness-dependency-report":
        try:
            result = _run_controlled_mock_readiness(args.fixture_file).dependency_report
            if args.output_file:
                args.output_file.write_text(result.model_dump_json(indent=2), encoding="utf-8")
                return {"status": "COMPLETED", "output_file": str(args.output_file), "report_id": result.report_id}
            return result.model_dump(mode="json")
        except Exception as exc:
            return {"status": "FAILED", "errors": [str(exc)]}
    if args.command == "paper-pass-evidence-report":
        try:
            result = _run_controlled_mock_readiness(args.fixture_file).paper_pass_evidence_report
            if args.output_file:
                args.output_file.write_text(result.model_dump_json(indent=2), encoding="utf-8")
                return {"status": "COMPLETED", "output_file": str(args.output_file), "report_id": result.report_id}
            return result.model_dump(mode="json")
        except Exception as exc:
            return {"status": "FAILED", "errors": [str(exc)]}
    if args.command == "mock-infrastructure-readiness-report":
        try:
            result = _run_controlled_mock_readiness(args.fixture_file).infrastructure_readiness_report
            if args.output_file:
                args.output_file.write_text(result.model_dump_json(indent=2), encoding="utf-8")
                return {"status": "COMPLETED", "output_file": str(args.output_file), "report_id": result.report_id}
            return result.model_dump(mode="json")
        except Exception as exc:
            return {"status": "FAILED", "errors": [str(exc)]}
    if args.command == "mock-safety-policy-report":
        try:
            result = _run_controlled_mock_readiness(args.fixture_file).safety_policy_report
            if args.output_file:
                args.output_file.write_text(result.model_dump_json(indent=2), encoding="utf-8")
                return {"status": "COMPLETED", "output_file": str(args.output_file), "report_id": result.report_id}
            return result.model_dump(mode="json")
        except Exception as exc:
            return {"status": "FAILED", "errors": [str(exc)]}
    if args.command == "mock-boundary-violation-report":
        try:
            result = _run_controlled_mock_readiness(args.fixture_file).boundary_violation_report
            if args.output_file:
                args.output_file.write_text(result.model_dump_json(indent=2), encoding="utf-8")
                return {"status": "COMPLETED", "output_file": str(args.output_file), "report_id": result.report_id}
            return result.model_dump(mode="json")
        except Exception as exc:
            return {"status": "FAILED", "errors": [str(exc)]}
    if args.command == "mock-readiness-gap-report":
        try:
            result = _run_controlled_mock_readiness(args.fixture_file).gap_report
            if args.output_file:
                args.output_file.write_text(result.model_dump_json(indent=2), encoding="utf-8")
                return {"status": "COMPLETED", "output_file": str(args.output_file), "gap_report_id": result.gap_report_id}
            return result.model_dump(mode="json")
        except Exception as exc:
            return {"status": "FAILED", "errors": [str(exc)]}
    if args.command == "market-regime-check":
        try:
            result = _run_market_regime(args.fixture_file).summary_report
            if args.output_file:
                args.output_file.write_text(result.model_dump_json(indent=2), encoding="utf-8")
                return {"status": "COMPLETED", "output_file": str(args.output_file), "decision": result.decision.value}
            return result.model_dump(mode="json")
        except Exception as exc:
            return {"status": "FAILED", "errors": [str(exc)]}
    if args.command == "market-regime-summary-report":
        try:
            result = _run_market_regime(args.fixture_file).summary_report
            if args.output_file:
                args.output_file.write_text(result.model_dump_json(indent=2), encoding="utf-8")
                return {"status": "COMPLETED", "output_file": str(args.output_file), "decision": result.decision.value}
            return result.model_dump(mode="json")
        except Exception as exc:
            return {"status": "FAILED", "errors": [str(exc)]}
    if args.command == "market-regime-input-snapshot-report":
        try:
            result = _run_market_regime(args.fixture_file).input_snapshot_report
            if args.output_file:
                args.output_file.write_text(result.model_dump_json(indent=2), encoding="utf-8")
                return {"status": "COMPLETED", "output_file": str(args.output_file), "report_id": result.report_id}
            return result.model_dump(mode="json")
        except Exception as exc:
            return {"status": "FAILED", "errors": [str(exc)]}
    if args.command == "risk-appetite-report":
        try:
            result = _run_market_regime(args.fixture_file).risk_appetite_report
            if args.output_file:
                args.output_file.write_text(result.model_dump_json(indent=2), encoding="utf-8")
                return {"status": "COMPLETED", "output_file": str(args.output_file), "report_id": result.report_id}
            return result.model_dump(mode="json")
        except Exception as exc:
            return {"status": "FAILED", "errors": [str(exc)]}
    if args.command == "market-direction-regime-report":
        try:
            result = _run_market_regime(args.fixture_file).direction_regime_report
            if args.output_file:
                args.output_file.write_text(result.model_dump_json(indent=2), encoding="utf-8")
                return {"status": "COMPLETED", "output_file": str(args.output_file), "report_id": result.report_id}
            return result.model_dump(mode="json")
        except Exception as exc:
            return {"status": "FAILED", "errors": [str(exc)]}
    if args.command == "volatility-regime-report":
        try:
            result = _run_market_regime(args.fixture_file).volatility_regime_report
            if args.output_file:
                args.output_file.write_text(result.model_dump_json(indent=2), encoding="utf-8")
                return {"status": "COMPLETED", "output_file": str(args.output_file), "report_id": result.report_id}
            return result.model_dump(mode="json")
        except Exception as exc:
            return {"status": "FAILED", "errors": [str(exc)]}
    if args.command == "fx-rate-dollar-stress-report":
        try:
            result = _run_market_regime(args.fixture_file).stress_report
            if args.output_file:
                args.output_file.write_text(result.model_dump_json(indent=2), encoding="utf-8")
                return {"status": "COMPLETED", "output_file": str(args.output_file), "report_id": result.report_id}
            return result.model_dump(mode="json")
        except Exception as exc:
            return {"status": "FAILED", "errors": [str(exc)]}
    if args.command == "cross-asset-conflict-report":
        try:
            result = _run_market_regime(args.fixture_file).cross_asset_conflict_report
            if args.output_file:
                args.output_file.write_text(result.model_dump_json(indent=2), encoding="utf-8")
                return {"status": "COMPLETED", "output_file": str(args.output_file), "report_id": result.report_id}
            return result.model_dump(mode="json")
        except Exception as exc:
            return {"status": "FAILED", "errors": [str(exc)]}
    if args.command == "market-regime-downstream-constraint-report":
        try:
            result = _run_market_regime(args.fixture_file).downstream_constraint_report
            if args.output_file:
                args.output_file.write_text(result.model_dump_json(indent=2), encoding="utf-8")
                return {"status": "COMPLETED", "output_file": str(args.output_file), "report_id": result.report_id}
            return result.model_dump(mode="json")
        except Exception as exc:
            return {"status": "FAILED", "errors": [str(exc)]}
    if args.command == "market-regime-training-feature-report":
        try:
            result = _run_market_regime(args.fixture_file).training_feature_integration_report
            if args.output_file:
                args.output_file.write_text(result.model_dump_json(indent=2), encoding="utf-8")
                return {"status": "COMPLETED", "output_file": str(args.output_file), "report_id": result.report_id}
            return result.model_dump(mode="json")
        except Exception as exc:
            return {"status": "FAILED", "errors": [str(exc)]}
    if args.command == "market-regime-gap-report":
        try:
            result = _run_market_regime(args.fixture_file).gap_report
            if args.output_file:
                args.output_file.write_text(result.model_dump_json(indent=2), encoding="utf-8")
                return {"status": "COMPLETED", "output_file": str(args.output_file), "gap_report_id": result.gap_report_id}
            return result.model_dump(mode="json")
        except Exception as exc:
            return {"status": "FAILED", "errors": [str(exc)]}
    if args.command == "create-order-intent":
        try:
            intent = OrderIntent(
                ticker=args.ticker, region=MarketRegion(args.region), side=OrderSide(args.side),
                order_type=OrderType(args.order_type), quantity=args.quantity, notional=args.notional,
                limit_price=args.limit_price, stop_loss_price=args.stop_loss_price,
                take_profit_price=args.take_profit_price, source_type=args.source_type,
                source_id=args.source_id, reason=args.reason, confidence_score=args.confidence_score,
                expires_at=args.expires_at,
            )
            OrderIntentService(RiskRepository(args.db)).create(intent)
            return {"status": "CREATED", "order_intent": intent.model_dump(mode="json")}
        except Exception as exc:
            return {"status": "FAILED", "errors": [str(exc)]}
    if args.command == "order-intents-list":
        return {"order_intents": [
            item.model_dump(mode="json") for item in RiskRepository(args.db).list_order_intents(
                OrderIntentStatus(args.status) if args.status else None,
                args.ticker, OrderSide(args.side) if args.side else None, args.limit,
            )
        ]}
    if args.command == "evaluate-order-intents":
        config = RiskGateConfig(
            allow_market_orders=args.allow_market_orders, max_risk_per_trade=args.max_risk_per_trade,
            max_position_notional=args.max_position_notional, max_daily_loss=args.max_daily_loss,
            current_daily_loss=args.current_daily_loss, blocked_tickers=set(args.blocked_ticker),
        )
        try:
            results = OrderIntentService(RiskRepository(args.db)).evaluate_many(
                config, ExecutionMode(args.execution_mode), args.order_intent_id, args.limit,
                enable_sandbox_order=args.enable_sandbox_order,
            )
            return {"results": [_dump_order_result(item) for item in results]}
        except (LookupError, ValueError) as exc:
            return {"status": "FAILED", "errors": [str(exc)], "results": []}
    if args.command == "paper-execute-approved-intents":
        try:
            results = OrderIntentService(RiskRepository(args.db)).paper_execute_many(
                args.order_intent_id, args.fill_price, args.limit
            )
            return {"results": [_dump_order_result(item) for item in results]}
        except (LookupError, ValueError) as exc:
            return {"status": "FAILED", "errors": [str(exc)], "results": []}
    if args.command == "paper-executions-list":
        return {"paper_executions": [
            item.model_dump(mode="json") for item in RiskRepository(args.db).list_paper_executions(
                args.ticker, OrderSide(args.side) if args.side else None, args.limit,
            )
        ]}
    if args.command == "broker-adapter-health":
        return BrokerAdapterService(RiskRepository(args.db)).health(
            BrokerId(args.broker), BrokerEnvironment(args.environment)
        ).model_dump(mode="json")
    if args.command == "broker-submit-mock-order":
        try:
            result = BrokerAdapterService(RiskRepository(args.db)).submit_mock_order(
                args.order_intent_id, args.mock_fill_price,
                BrokerId(args.broker), BrokerEnvironment(args.environment),
            )
            return _dump_order_result(result)
        except (LookupError, ValueError) as exc:
            return {"status": "FAILED", "errors": [str(exc)]}
    if args.command == "broker-order-requests-list":
        return {"broker_order_requests": [
            item.model_dump(mode="json") for item in RiskRepository(args.db).list_broker_order_requests(
                BrokerId(args.broker) if args.broker else None, args.order_intent_id, args.limit,
            )
        ]}
    if args.command == "broker-order-receipts-list":
        return {"broker_order_receipts": [
            item.model_dump(mode="json") for item in RiskRepository(args.db).list_broker_order_receipts(
                BrokerId(args.broker) if args.broker else None, args.order_intent_id,
                BrokerOrderStatus(args.status) if args.status else None, args.limit,
            )
        ]}
    if args.command == "kiwoom-readonly-health":
        return KiwoomRestReadOnlyAdapter(KiwoomEnvironment(args.environment)).health_check()
    if args.command == "kiwoom-readonly-endpoints":
        adapter = KiwoomRestReadOnlyAdapter(KiwoomEnvironment(args.environment))
        return {"endpoints": _dump_order_result(adapter.list_readonly_endpoints())}
    if args.command.startswith("kiwoom-readonly-"):
        service = KiwoomReadOnlyService(RiskRepository(args.db), KiwoomEnvironment(args.environment))
        operations = {
            "kiwoom-readonly-stock-info": lambda: service.get_stock_info(args.ticker),
            "kiwoom-readonly-quote": lambda: service.get_quote(args.ticker),
            "kiwoom-readonly-rankings": lambda: service.get_rankings(args.rank_type, args.market),
            "kiwoom-readonly-flow": lambda: service.get_flow(args.ticker, args.market),
            "kiwoom-readonly-chart": lambda: service.get_chart_bars(args.ticker, args.interval, args.count),
            "kiwoom-readonly-condition-list": service.list_condition_searches,
            "kiwoom-readonly-condition-run": lambda: service.run_condition_search(args.condition_id),
        }
        try:
            return _dump_order_result(operations[args.command]())
        except (LookupError, ValueError) as exc:
            return {"status": "FAILED", "errors": [str(exc)]}
    if args.command == "kiwoom-mock-execution-health":
        return KiwoomMockExecutionService(RiskRepository(args.db)).health().model_dump(mode="json")
    if args.command == "kiwoom-mock-order-requests-list":
        return {"kiwoom_mock_order_requests": [
            item.model_dump(mode="json") for item in RiskRepository(args.db).list_kiwoom_mock_order_requests(
                args.order_intent_id, args.limit
            )
        ]}
    if args.command == "kiwoom-mock-order-receipts-list":
        return {"kiwoom_mock_order_receipts": [
            item.model_dump(mode="json") for item in RiskRepository(args.db).list_kiwoom_mock_order_receipts(
                args.order_intent_id, args.limit
            )
        ]}
    if args.command.startswith("kiwoom-mock-"):
        service = KiwoomMockExecutionService(RiskRepository(args.db))
        operations = {
            "kiwoom-mock-submit-order": lambda: service.submit_order(args.order_intent_id, args.mock_fill_price),
            "kiwoom-mock-cancel-order": lambda: service.cancel_order(args.mock_order_id),
            "kiwoom-mock-order-status": lambda: service.order_status(args.mock_order_id),
        }
        try:
            return _dump_order_result(operations[args.command]())
        except (LookupError, ValueError) as exc:
            return {"status": "FAILED", "errors": [str(exc)]}
    if args.command == "kiwoom-official-endpoints-list":
        endpoints = load_kiwoom_official_manifest().endpoints
        if args.endpoint_class:
            endpoints = [item for item in endpoints if item.read_write_class.value == args.endpoint_class]
        if args.category:
            endpoints = [item for item in endpoints if item.category == args.category]
        if args.runtime_allowed:
            endpoints = [item for item in endpoints if item.runtime_allowed_in_current_version]
        return {"endpoints": [item.model_dump(mode="json") for item in endpoints[:args.limit]]}
    if args.command == "kiwoom-official-endpoints-validate":
        return validate_kiwoom_official_manifest(
            load_kiwoom_official_manifest()
        ).model_dump(mode="json")
    if args.command == "kiwoom-official-endpoint-show":
        endpoints = load_kiwoom_official_manifest().endpoints
        matches = [
            item for item in endpoints
            if (not args.api_id or item.api_id == args.api_id) and (not args.path or item.path == args.path)
        ]
        return matches[0].model_dump(mode="json") if matches else {
            "status": "NOT_FOUND", "errors": ["official endpoint manifest entry not found"],
        }
    if args.command == "kiwoom-real-readonly-smoke-plan":
        return build_smoke_plan()
    if args.command == "kiwoom-real-readonly-smoke-reports":
        return {"smoke_reports": [
            item.model_dump(mode="json")
            for item in RiskRepository(args.db).list_kiwoom_real_readonly_smoke_runs(args.limit)
        ]}
    if args.command == "kiwoom-real-readonly-smoke-show":
        try:
            return RiskRepository(args.db).get_kiwoom_real_readonly_smoke_report(
                args.smoke_run_id
            ).model_dump(mode="json")
        except LookupError as error:
            return {"status": "NOT_FOUND", "errors": [str(error)]}
    if args.command == "kiwoom-real-readonly-smoke-run":
        repository = RiskRepository(args.db)
        config = KiwoomRealNetworkConfig(
            enabled=args.enable_real_network, environment=KiwoomRealNetworkEnvironment(args.environment),
            base_url=args.base_url, timeout_seconds=args.timeout_seconds,
            max_requests_per_run=args.max_requests_per_run,
            allow_auth_token_request=args.allow_auth_token_request,
            credential_source=KiwoomCredentialSource(args.credential_source),
            credential_file=args.credential_file,
        )

        def explicit_credential_loader(source, credential_file):
            env = {
                key: value for key in ("KIWOOM_APPKEY", "KIWOOM_SECRETKEY")
                if (value := os.environ.get(key)) is not None
            } if source == KiwoomCredentialSource.ENV else {}
            return load_kiwoom_credentials(source, credential_file, env)

        smoke = KiwoomRealReadOnlySmokeService(
            repository=repository, credential_loader=explicit_credential_loader,
            service_factory=lambda current_config, credentials: KiwoomRealReadOnlyService(
                repository, current_config, credentials
            ),
        )
        return smoke.run(config, args.endpoint_id, args.endpoint_set, args.dry_run).model_dump(mode="json")
    if args.command.startswith("kiwoom-sandbox-order-"):
        repository = RiskRepository(args.db)
        service = KiwoomSandboxOrderService(repository, credential_loader=_sandbox_credential_loader)
        if args.command == "kiwoom-sandbox-order-health":
            return service.health().model_dump(mode="json")
        if args.command == "kiwoom-sandbox-order-plan":
            return service.plan(args.order_intent_id).model_dump(mode="json")
        if args.command == "kiwoom-sandbox-order-requests":
            return {"requests": [item.model_dump(mode="json") for item in repository.list_kiwoom_sandbox_order_requests(args.limit)]}
        if args.command == "kiwoom-sandbox-order-receipts":
            return {"receipts": [item.model_dump(mode="json") for item in repository.list_kiwoom_sandbox_order_receipts(args.limit)]}
        if args.command == "kiwoom-sandbox-order-status":
            return {"status_checks": [item.model_dump(mode="json") for item in service.status(args.broker_order_id)]}
        if args.command == "kiwoom-sandbox-order-show":
            item = repository.get_kiwoom_sandbox_receipt_by_broker_order_id(args.broker_order_id)
            return item.model_dump(mode="json") if item else {"status": "NOT_FOUND"}
        config = _sandbox_config_from_args(args)
        if args.command == "kiwoom-sandbox-order-cancel":
            return {"receipts": [item.model_dump(mode="json") for item in service.cancel(args.broker_order_id, config)]}
        return _dump_order_result(service.submit(args.order_intent_id, config, args.dry_run, args.client_order_id))
    if args.command.startswith("kiwoom-sandbox-sell-"):
        repository = RiskRepository(args.db)
        if args.command == "kiwoom-sandbox-sell-schema-verify":
            return KiwoomSandboxSellSchemaVerifier(repository).verify().model_dump(mode="json")
        if args.command == "kiwoom-sandbox-sell-schema-reports":
            return {"reports": [item.model_dump(mode="json") for item in repository.list_kiwoom_sandbox_sell_schema_reports(args.limit)]}
        if args.command == "kiwoom-sandbox-sell-schema-show":
            try:
                return repository.get_kiwoom_sandbox_sell_schema_report(args.report_id).model_dump(mode="json")
            except LookupError as error:
                return {"status": "NOT_FOUND", "errors": [str(error)]}
        return KiwoomSandboxSellDryRunService(repository).run(args.order_intent_id).model_dump(mode="json")
    if args.command == "kiwoom-official-sell-schema-evidence-validate":
        return KiwoomOfficialSellSchemaEvidenceService().validate(args.evidence_file).model_dump(mode="json")
    if args.command.startswith("kiwoom-official-sell-schema-evidence-"):
        repository = RiskRepository(args.db)
        service = KiwoomOfficialSellSchemaEvidenceService(repository)
        if args.command == "kiwoom-official-sell-schema-evidence-import":
            return service.import_evidence(args.evidence_file).model_dump(mode="json")
        if args.command == "kiwoom-official-sell-schema-evidence-list":
            return {"evidence": [item.model_dump(mode="json") for item in repository.list_official_sell_schema_evidence(args.limit)]}
        if args.command == "kiwoom-official-sell-schema-evidence-show":
            try:
                return repository.get_official_sell_schema_evidence(args.evidence_id).model_dump(mode="json")
            except LookupError as error:
                return {"status": "NOT_FOUND", "errors": [str(error)]}
        try:
            return service.review(
                args.evidence_id, OfficialSellSchemaEvidenceReviewStatus(args.status),
                args.reviewed_by, args.notes,
            ).model_dump(mode="json")
        except (LookupError, ValueError) as error:
            return {"status": "FAILED", "errors": [str(error)]}
    if args.command == "kiwoom-account-read-smoke-plan":
        return build_account_read_smoke_plan()
    if args.command.startswith("kiwoom-account-read-smoke-"):
        repository = RiskRepository(args.db)
        if args.command == "kiwoom-account-read-smoke-reports":
            return {"smoke_reports": [item.model_dump(mode="json") for item in repository.list_kiwoom_account_read_smoke_reports(args.limit)]}
        if args.command == "kiwoom-account-read-smoke-show":
            try:
                return repository.get_kiwoom_account_read_smoke_report(args.smoke_run_id).model_dump(mode="json")
            except LookupError as error:
                return {"status": "NOT_FOUND", "errors": [str(error)]}
        config = _account_read_config_from_args(args)
        account_service = KiwoomAccountReadService(
            repository, credential_loader=_account_read_credential_loader,
            transport_factory=lambda current, credentials: RealKiwoomAccountReadTransport(current, credentials),
        )
        return KiwoomAccountReadSmokeService(repository, account_service).run(
            config, args.endpoint_id, args.endpoint_set, args.dry_run
        ).model_dump(mode="json")
    if args.command.startswith("kiwoom-account-read-"):
        repository = RiskRepository(args.db)

        service = KiwoomAccountReadService(
            repository,
            credential_loader=_account_read_credential_loader,
            transport_factory=lambda config, credentials: RealKiwoomAccountReadTransport(config, credentials),
        )
        if args.command == "kiwoom-account-read-health":
            return service.health().model_dump(mode="json")
        if args.command == "kiwoom-account-read-reports":
            return {"reports": [item.model_dump(mode="json") for item in repository.list_kiwoom_account_read_reports(args.limit)]}
        if args.command == "kiwoom-account-read-show":
            try:
                return repository.get_kiwoom_account_read_report(args.run_id).model_dump(mode="json")
            except LookupError as error:
                return {"status": "NOT_FOUND", "errors": [str(error)]}
        if args.command == "kiwoom-account-read-reconcile-preview":
            try:
                return service.reconcile_preview(
                    args.run_id, args.kill_switch_inactive, args.local_ledger_file,
                    args.include_redacted_symbol_details,
                ).model_dump(mode="json")
            except (LookupError, PermissionError) as error:
                return {"status": "NOT_FOUND", "errors": [str(error)]}
        config = _account_read_config_from_args(args)
        if args.command == "kiwoom-account-read-plan":
            return service.plan(config, args.endpoint_id)
        return service.run(config, args.endpoint_id, args.dry_run).model_dump(mode="json")
    if args.command.startswith("kiwoom-real-readonly-"):
        config = KiwoomRealNetworkConfig(
            enabled=args.enable_real_network, environment=KiwoomRealNetworkEnvironment(args.environment),
            base_url=args.base_url, timeout_seconds=args.timeout_seconds,
            max_requests_per_run=args.max_requests_per_run,
            allow_auth_token_request=args.allow_auth_token_request,
            credential_source=KiwoomCredentialSource(args.credential_source),
            credential_file=args.credential_file,
        )
        credentials = load_kiwoom_credentials(
            config.credential_source, config.credential_file,
            {
                key: value for key in ("KIWOOM_APPKEY", "KIWOOM_SECRETKEY", "KIWOOM_ACCOUNT_NUMBER")
                if (value := os.environ.get(key)) is not None
            } if config.enabled and config.credential_source == KiwoomCredentialSource.ENV else {},
        ) if config.enabled else load_kiwoom_credentials(KiwoomCredentialSource.NONE)
        service = KiwoomRealReadOnlyService(RiskRepository(args.db), config, credentials)
        if args.command == "kiwoom-real-readonly-health":
            return service.health()
        operations = {
            "kiwoom-real-readonly-stock-info": ("ka10001", {"stk_cd": getattr(args, "ticker", None)}),
            "kiwoom-real-readonly-quote": ("ka10004", {"stk_cd": getattr(args, "ticker", None)}),
            "kiwoom-real-readonly-rankings": ("ka10020", {"mrkt_tp": getattr(args, "market", None), "sort_tp": getattr(args, "sort_type", None)}),
            "kiwoom-real-readonly-flow": ("ka10008", {"stk_cd": getattr(args, "ticker", None)}),
            "kiwoom-real-readonly-minute-chart": ("ka10080", {"stk_cd": getattr(args, "ticker", None)}),
            "kiwoom-real-readonly-daily-chart": ("ka10081", {"stk_cd": getattr(args, "ticker", None)}),
        }
        api_id, body = operations[args.command]
        return service.request(api_id, body)
    if args.command == "report-pipeline":
        return run_analysis_report(args, build_pipeline_summary_report, args.pipeline_run_id)
    if args.command == "report-scan":
        return run_analysis_report(args, build_candidate_scan_report, args.scan_run_id)
    if args.command == "report-basket":
        return run_analysis_report(args, build_basket_plan_report, args.basket_id)
    if args.command == "report-policy-suite":
        return run_analysis_report(args, build_policy_evaluation_report, args.suite_id)
    if args.command == "reports":
        return {"reports": [item.model_dump(mode="json") for item in RiskRepository(args.db).list_analysis_reports(args.limit)]}
    if args.command == "report-show":
        return RiskRepository(args.db).get_analysis_report(args.report_id).model_dump(mode="json")
    if args.command == "agent-context-from-report":
        repository = RiskRepository(args.db)
        context = build_agent_context_from_report(repository.get_analysis_report(args.report_id))
        if args.save:
            repository.save_agent_context(context)
        return {**context.model_dump(mode="json"), "saved": args.save}
    if args.command == "agent-context-from-pipeline":
        repository = RiskRepository(args.db)
        context = build_agent_context_from_pipeline(repository, args.pipeline_run_id)
        if args.save:
            repository.save_agent_context(context)
        return {**context.model_dump(mode="json"), "saved": args.save}
    if args.command == "agent-prompt":
        repository = RiskRepository(args.db)
        prompt = build_agent_prompt(repository.get_agent_context(args.context_id), args.language)
        if args.save:
            repository.save_agent_prompt(prompt)
        return {**prompt.model_dump(mode="json"), "saved": args.save}
    if args.command == "agent-brief":
        repository = RiskRepository(args.db)
        brief = build_agent_brief(repository.get_agent_context(args.context_id))
        if args.save:
            repository.save_agent_brief(brief)
        return {**brief.model_dump(mode="json"), "saved": args.save}
    if args.command == "agent-run-local":
        return run_agent_local(args)
    if args.command == "agent-contexts":
        return {"agent_contexts": [item.model_dump(mode="json") for item in RiskRepository(args.db).list_agent_contexts(args.limit)]}
    if args.command == "agent-prompts":
        return {"agent_prompts": [item.model_dump(mode="json") for item in RiskRepository(args.db).list_agent_prompts(args.limit)]}
    if args.command == "agent-briefs":
        return {"agent_briefs": [item.model_dump(mode="json") for item in RiskRepository(args.db).list_agent_briefs(args.limit)]}
    if args.command == "agent-tools":
        return {"tools": read_only_tool_manifest()}
    if args.command == "local-llm-responses":
        return {"responses": [item.model_dump(mode="json") for item in RiskRepository(args.db).list_local_llm_responses(args.limit)]}
    if args.command in {"notify-pipeline", "notify-report", "notify-brief", "notify-local-response", "notify-digest"}:
        return run_notification_command(args)
    if args.command == "notification-runs":
        return {"notification_runs": [item.model_dump(mode="json") for item in RiskRepository(args.db).list_notification_runs(args.limit)]}
    if args.command == "notification-show":
        repository = RiskRepository(args.db)
        run = repository.get_notification_run(args.notification_run_id)
        return {
            "run": run.model_dump(mode="json"),
            "notifications": [item.model_dump(mode="json") for item in repository.list_notification_messages(run.source_id)],
        }
    if args.command == "notifications":
        return {
            "notifications": [
                item.model_dump(mode="json")
                for item in RiskRepository(args.db).list_notification_messages(args.source_id, args.limit)
            ]
        }
    if args.command == "dashboard-overview":
        return build_overview_dashboard(RiskRepository(args.db), args.output_file, args.as_of_date, args.limit, args.save).model_dump(mode="json")
    if args.command == "dashboard-pipeline":
        return build_pipeline_dashboard(RiskRepository(args.db), args.pipeline_run_id, args.output_file, args.save).model_dump(mode="json")
    if args.command == "dashboard-daily":
        return build_daily_dashboard(RiskRepository(args.db), args.as_of_date, args.output_file, args.save).model_dump(mode="json")
    if args.command == "dashboard-policy":
        return build_policy_dashboard(RiskRepository(args.db), args.output_file, args.limit, args.save).model_dump(mode="json")
    if args.command == "dashboard-builds":
        return {"dashboard_builds": [item.model_dump(mode="json") for item in RiskRepository(args.db).list_dashboard_builds(args.limit)]}
    if args.command == "dashboard-show":
        return RiskRepository(args.db).get_dashboard_build(args.dashboard_id).model_dump(mode="json")
    if args.command == "run-local-demo":
        result = run_local_demo(
            args.db, args.as_of_date, args.output_dir, tickers=args.ticker,
            account_equity=args.account_equity, cash_available=args.cash_available,
            horizon_days=args.horizon_days, save_intermediate=not args.no_save_intermediate,
        )
        return {**result.model_dump(mode="json"), **result.key_outputs, "disclaimer": DEMO_DISCLAIMER}
    if args.command == "system-smoke":
        return run_system_smoke(args.db, args.output_dir, args.as_of_date)
    if args.command == "release-check":
        return build_release_check()
    if args.command == "backtest":
        return run_backtest(args)
    if args.command == "backtest-summary":
        return run_backtest_summary(args)
    if args.command == "report":
        return run_report(args)
    if args.command == "reasons":
        return run_reasons(args)
    if args.command == "sources":
        return run_sources(args)
    if args.command == "ingestion-runs":
        return run_ingestion_runs(args)
    if args.command == "analyze-indicators":
        return run_analyze_indicators(args, save=False)
    if args.command == "analyze-indicators-and-save":
        return run_analyze_indicators(args, save=True)
    if args.command == "analyze-setup":
        setup, _ = _analyze_setup(args)
        return setup.model_dump(mode="json")
    if args.command == "create-trade-plan":
        return run_create_trade_plan(args, save=False)
    if args.command == "create-trade-plan-and-save":
        return run_create_trade_plan(args, save=True)
    if args.command == "build-basket-from-trade-plans":
        return run_build_basket(args, save=False)
    if args.command == "build-basket-and-save":
        return run_build_basket(args, save=True)
    if args.command == "show-basket":
        return RiskRepository(args.db).get_basket_plan(args.basket_id).model_dump(mode="json")
    if args.command == "paper-trade-basket":
        return run_paper_trade_basket(args, from_file=False)
    if args.command == "paper-trade-basket-from-file":
        return run_paper_trade_basket(args, from_file=True)
    if args.command == "paper-trades":
        trades = RiskRepository(args.db).list_paper_trades(args.basket_id)
        return {"trades": [trade.model_dump(mode="json") for trade in trades]}
    if args.command == "basket-performance":
        return RiskRepository(args.db).basket_performance_summary().model_dump(mode="json")
    if args.command == "strategy-init":
        return run_strategy_init(args)
    if args.command == "strategy-active":
        policy = RiskRepository(args.db).get_active_strategy_policy()
        return policy.model_dump(mode="json") if policy else {"policy": None}
    if args.command == "strategy-propose":
        return run_strategy_propose(args)
    if args.command == "strategy-evaluate":
        return run_strategy_evaluate(args)
    if args.command == "strategy-experiments":
        experiments = RiskRepository(args.db).list_strategy_experiments()
        return {"experiments": [item.model_dump(mode="json") for item in experiments]}
    if args.command == "strategy-policies":
        policies = RiskRepository(args.db).list_strategy_policies()
        return {"policies": [item.model_dump(mode="json") for item in policies]}
    if args.command == "replay-snapshot-from-basket":
        result = ReplayRunService(RiskRepository(args.db)).snapshot_from_basket(args.basket_id, args.as_of_date)
        return result.model_dump(mode="json")
    if args.command == "replay-snapshot-from-recent-trade-plans":
        repository = RiskRepository(args.db)
        result = ReplayRunService(repository).snapshot_from_recent_trade_plans(
            account_equity=args.account_equity,
            cash_available=args.cash_available,
            max_candidates=args.max_candidates,
            horizon_days=args.horizon_days,
            as_of_date=args.as_of_date,
            save_basket=args.save_basket,
            strategy_policy=_resolve_strategy_policy(args, repository),
        )
        return result.model_dump(mode="json")
    if args.command == "replay-runs":
        runs = RiskRepository(args.db).list_replay_runs(args.limit)
        return {"runs": [run.model_dump(mode="json") for run in runs]}
    if args.command == "replay-show":
        return load_replay_dataset(RiskRepository(args.db), args.run_id).model_dump(mode="json")
    if args.command == "policy-replay":
        return run_policy_replay(args, active=False)
    if args.command == "policy-replay-active":
        return run_policy_replay(args, active=True)
    if args.command == "policy-replay-results":
        results = RiskRepository(args.db).list_policy_replay_results(args.replay_run_id, args.limit)
        return {"results": [result.model_dump(mode="json") for result in results]}
    if args.command == "policy-compare":
        return run_policy_compare(args)
    if args.command == "policy-evaluate-suite":
        return run_policy_evaluate_suite(args)
    if args.command == "policy-evaluation-suites":
        return {"suites": [item.model_dump(mode="json") for item in RiskRepository(args.db).list_policy_evaluation_suites()]}
    if args.command == "policy-propose-promotion":
        repository = RiskRepository(args.db)
        suite = repository.get_policy_evaluation_suite(args.suite_id)
        policy = repository.get_strategy_policy(suite.candidate_policy_id, suite.candidate_policy_version)
        proposal = create_policy_promotion_proposal(suite, policy.status.value)
        repository.save_policy_promotion_proposal(proposal)
        return proposal.model_dump(mode="json")
    if args.command == "policy-promotion-proposals":
        return {"proposals": [item.model_dump(mode="json") for item in RiskRepository(args.db).list_policy_promotion_proposals()]}
    if args.command == "policy-approve":
        return approve_policy(RiskRepository(args.db), args.policy_id, args.policy_version).model_dump(mode="json")
    if args.command == "policy-activate":
        return activate_policy(RiskRepository(args.db), args.policy_id, args.policy_version).model_dump(mode="json")
    if args.command == "scan-candidates":
        return run_scan_candidates(args)
    if args.command == "scan-runs":
        runs = RiskRepository(args.db).list_scan_runs(args.limit)
        return {"scan_runs": [item.model_dump(mode="json") for item in runs]}
    if args.command == "scan-results":
        results = RiskRepository(args.db).list_candidate_scan_results(args.scan_run_id, args.decision, args.limit)
        return {"results": [item.model_dump(mode="json") for item in results]}
    if args.command == "scan-to-basket":
        return run_scan_to_basket(args)
    if args.command == "scan-to-replay-snapshot":
        replay = create_replay_snapshot_from_scan_run(
            RiskRepository(args.db), args.scan_run_id, args.as_of_date, include_watch=args.include_watch
        )
        return replay.model_dump(mode="json")
    if args.command == "ingest-signals":
        return run_ingest_signals(args)
    if args.command == "signals":
        items = RiskRepository(args.db).list_ticker_signals(args.ticker, args.as_of_date, args.limit)
        return {"signals": [item.model_dump(mode="json") for item in items]}
    if args.command == "run-scan-pipeline":
        repository = RiskRepository(args.db)
        execution = OperationalPipeline(repository).run_scan_only_pipeline(
            args.as_of_date, price_history_file=args.price_history_file,
            signal_files=_operational_signal_files(args), ignore_db_signals=args.ignore_db_signals,
            strategy_policy=_resolve_strategy_policy(args, repository),
        )
        return _operational_output(execution)
    if args.command == "run-paper-pipeline":
        return _run_operational_paper(args)
    if args.command == "run-policy-evaluation-pipeline":
        repository = RiskRepository(args.db)
        execution = OperationalPipeline(repository).run_replay_evaluation_pipeline(
            args.replay_run_id, args.baseline_policy_id, args.baseline_policy_version,
            args.candidate_policy_id, args.candidate_policy_version, args.horizon_days,
            args.account_equity, args.cash_available, price_history_file=args.price_history_file,
        )
        return _operational_output(execution)
    if args.command == "pipeline-runs":
        return {"pipeline_runs": [item.model_dump(mode="json") for item in RiskRepository(args.db).list_pipeline_runs(args.limit)]}
    if args.command == "pipeline-show":
        repository = RiskRepository(args.db)
        run = repository.get_pipeline_run(args.pipeline_run_id)
        alerts = repository.list_pipeline_alerts(args.pipeline_run_id)
        return {
            "run": run.model_dump(mode="json"),
            "summary": build_pipeline_summary(run, alerts).model_dump(mode="json"),
            "alerts": [item.model_dump(mode="json") for item in alerts],
        }
    if args.command == "alerts":
        items = RiskRepository(args.db).list_pipeline_alerts(args.pipeline_run_id, args.limit)
        return {"alerts": [item.model_dump(mode="json") for item in items]}
    if args.command == "watch-loop":
        outputs = run_watch_loop(
            lambda: _run_operational_paper(args, mode=PipelineMode.WATCH_LOOP),
            args.interval_seconds,
            args.max_iterations,
        )
        return {"iterations": outputs, "warning": "Watch loop performs local paper operations only and never places orders."}
    raise ValueError(f"Unsupported command: {args.command}")


def run_evaluate(args: argparse.Namespace) -> dict[str, object]:
    policy = load_policy(args.policy) if args.policy else None
    proposal = build_proposal(args)
    result = RiskEvaluationService(
        policy=policy,
        market_adapter=PriceHistoryMarketDataAdapter(
            price_history_file=args.price_history_file,
            source_name="price_history_file",
        )
        if args.price_history_file
        else None,
    ).evaluate(proposal)
    return result.model_dump(mode="json")


def _load_historical_replay_bridge_fixture_or_raise(fixture_file: Path):
    return load_historical_replay_bridge_fixture(fixture_file)


def _build_historical_replay_event_stream_payload(fixture_file: Path):
    fixture = _load_historical_replay_bridge_fixture_or_raise(fixture_file)
    return build_historical_replay_event_stream(fixture)


def _build_historical_replay_window_bundle(fixture_file: Path):
    fixture = _load_historical_replay_bridge_fixture_or_raise(fixture_file)
    stream = build_historical_replay_event_stream(fixture)
    return build_historical_replay_windows(stream, fixture)


def _build_historical_scanner_replay_input_payload(fixture_file: Path):
    fixture = _load_historical_replay_bridge_fixture_or_raise(fixture_file)
    stream = build_historical_replay_event_stream(fixture)
    window_bundle = build_historical_replay_windows(stream, fixture)
    scanner_input, _scanner_report, gap_report = build_historical_scanner_replay_input(stream, window_bundle)
    if scanner_input is None:
        categories = ", ".join(gap_report.gap_categories) if gap_report.gap_categories else "unknown gap"
        raise ValueError(f"historical scanner replay input unavailable: {categories}")
    return scanner_input


def _build_historical_replay_safety_report(fixture_file: Path):
    _load_historical_replay_bridge_fixture_or_raise(fixture_file)
    return HistoricalReplayBridgeSafetyReport()


def _build_historical_replay_bridge_report(fixture_file: Path):
    fixture = _load_historical_replay_bridge_fixture_or_raise(fixture_file)
    stream = build_historical_replay_event_stream(fixture)
    window_bundle = build_historical_replay_windows(stream, fixture)
    warnings = sorted({warning for window in window_bundle.windows for warning in window.warnings})
    return HistoricalReplayBridgeReport.model_validate(
        {
            "report_id": f"{stream.stream_id}-REPORT",
            "bridge_input_id": stream.bridge_input_id,
            "strategy_track": stream.strategy_track,
            "market_profile_id": stream.market_profile_id,
            "historical_market_snapshot_id": stream.historical_market_snapshot_id,
            "historical_calendar_snapshot_id": stream.historical_calendar_snapshot_id,
            "source_manifest_ids": stream.source_manifest_ids,
            "source_audit_record_ids": stream.source_audit_record_ids,
            "provider_provenance_ids": stream.provider_provenance_ids,
            "event_count": len(stream.events),
            "window_count": len(window_bundle.windows),
            "safety_report": _build_historical_replay_safety_report(fixture_file).model_dump(mode="json"),
            "warnings": warnings,
        }
    )


def _load_historical_outcome_fixture_or_raise(fixture_file: Path):
    return load_historical_outcome_fixture(fixture_file)


def _build_historical_outcome_observation_input(fixture_file: Path):
    fixture = _load_historical_outcome_fixture_or_raise(fixture_file)
    return build_historical_outcome_windows(fixture)


def _build_historical_outcome_label_observation(fixture_file: Path):
    observed = _build_historical_outcome_observation_input(fixture_file)
    return build_historical_outcome_label_report(observed)


def _load_historical_dataset_fixture_or_raise(fixture_file: Path):
    return load_historical_dataset_fixture(fixture_file)


def _build_historical_dataset_assembly(fixture_file: Path):
    fixture = _load_historical_dataset_fixture_or_raise(fixture_file)
    return build_historical_dataset_assembly_input(fixture)


def _load_historical_dataset_validation_fixture_or_raise(fixture_file: Path):
    return load_historical_dataset_validation_fixture(fixture_file)


def _build_historical_dataset_validation(fixture_file: Path):
    fixture = _load_historical_dataset_validation_fixture_or_raise(fixture_file)
    return build_historical_dataset_validation(fixture)


def _load_historical_dataset_readiness_fixture_or_raise(fixture_file: Path):
    return load_historical_dataset_readiness_fixture(fixture_file)


def _build_historical_dataset_readiness(fixture_file: Path):
    fixture = _load_historical_dataset_readiness_fixture_or_raise(fixture_file)
    return build_historical_dataset_readiness(fixture)


def _load_historical_model_training_fixture_or_raise(fixture_file: Path):
    return load_historical_model_training_fixture(fixture_file)


def _build_historical_model_training_plan_check(fixture_file: Path):
    fixture = _load_historical_model_training_fixture_or_raise(fixture_file)
    return build_historical_model_training_plan_check(fixture)


def _build_historical_model_training_sandbox(fixture_file: Path):
    fixture = _load_historical_model_training_fixture_or_raise(fixture_file)
    return run_historical_model_training_sandbox(fixture)


def _load_historical_model_experiment_fixture_or_raise(fixture_file: Path):
    return load_historical_model_experiment_fixture(fixture_file)


def _build_historical_model_experiment_registry(fixture_file: Path):
    fixture = _load_historical_model_experiment_fixture_or_raise(fixture_file)
    return build_historical_model_experiment_registry(fixture)


def _load_historical_signal_candidate_fixture_or_raise(fixture_file: Path):
    return load_historical_signal_candidate_fixture(fixture_file)


def _build_historical_signal_candidate_batch(fixture_file: Path):
    fixture = _load_historical_signal_candidate_fixture_or_raise(fixture_file)
    return build_historical_signal_candidate_batch(fixture)


def _load_historical_paper_trading_fixture_or_raise(fixture_file: Path):
    return load_historical_paper_trading_fixture(fixture_file)


def _run_historical_paper_trading(fixture_file: Path):
    fixture = _load_historical_paper_trading_fixture_or_raise(fixture_file)
    return run_historical_paper_trading(fixture)


def _load_broker_mock_adapter_fixture_or_raise(fixture_file: Path):
    return load_broker_mock_adapter_fixture(fixture_file)


def _run_broker_mock_adapter_boundary(fixture_file: Path):
    fixture = _load_broker_mock_adapter_fixture_or_raise(fixture_file)
    return run_broker_mock_adapter_boundary(fixture)


def _load_kiwoom_mock_adapter_fixture_or_raise(fixture_file: Path):
    return load_kiwoom_mock_adapter_fixture(fixture_file)


def _run_kiwoom_mock_adapter_draft_mapping(fixture_file: Path):
    fixture = _load_kiwoom_mock_adapter_fixture_or_raise(fixture_file)
    return run_kiwoom_mock_adapter_draft_mapping(fixture)


def _load_kiwoom_mock_credential_boundary_fixture_or_raise(fixture_file: Path):
    return load_kiwoom_mock_credential_boundary_fixture(fixture_file)


def _run_kiwoom_mock_credential_boundary(fixture_file: Path):
    fixture = _load_kiwoom_mock_credential_boundary_fixture_or_raise(fixture_file)
    return run_kiwoom_mock_credential_boundary_evaluation(fixture)


def _load_kiwoom_mock_oauth_draft_fixture_or_raise(fixture_file: Path):
    return load_kiwoom_mock_oauth_draft_fixture(fixture_file)


def _run_kiwoom_mock_oauth_draft_boundary(fixture_file: Path):
    fixture = _load_kiwoom_mock_oauth_draft_fixture_or_raise(fixture_file)
    return run_kiwoom_mock_oauth_draft_boundary(
        fixture,
        explicit_opt_in_ack=True,
        credential_boundary_ref="docs/superpowers/plans/2026-06-18-kiwoom-mock-credential-environment-boundary-design.md",
    )


def _load_kiwoom_mock_oauth_execution_fixture_or_raise(fixture_file: Path):
    return load_kiwoom_mock_oauth_execution_fixture(fixture_file)


def _run_kiwoom_mock_oauth_execution(
    fixture_file: Path,
    *,
    execute: bool,
    acknowledge_mock_oauth_execution: bool,
    mock_domain: bool,
):
    fixture = _load_kiwoom_mock_oauth_execution_fixture_or_raise(fixture_file)
    return execute_kiwoom_mock_oauth(
        fixture,
        execute=execute,
        acknowledge_mock_oauth_execution=acknowledge_mock_oauth_execution,
        mock_domain=mock_domain,
    )


def _load_kiwoom_mock_api_transport_draft_fixture_or_raise(fixture_file: Path):
    return load_kiwoom_mock_api_transport_draft_fixture(fixture_file)


def _run_kiwoom_mock_api_transport_draft_boundary(fixture_file: Path):
    fixture = _load_kiwoom_mock_api_transport_draft_fixture_or_raise(fixture_file)
    return run_kiwoom_mock_api_transport_draft_boundary(
        fixture,
        oauth_draft_boundary_ref="docs/superpowers/plans/2026-06-18-kiwoom-mock-oauth-token-draft-boundary-design.md",
    )


def _load_kiwoom_mock_api_preflight_gate_fixture_or_raise(fixture_file: Path):
    return load_kiwoom_mock_api_preflight_gate_fixture(fixture_file)


def _run_kiwoom_mock_api_preflight_gate(fixture_file: Path):
    fixture = _load_kiwoom_mock_api_preflight_gate_fixture_or_raise(fixture_file)
    return run_kiwoom_mock_api_preflight_gate(fixture)


def _load_kiwoom_mock_market_data_execution_fixture_or_raise(fixture_file: Path):
    return load_kiwoom_mock_market_data_execution_fixture(fixture_file)


def _run_kiwoom_mock_market_data_execution(
    fixture_file: Path,
    *,
    execute: bool,
    acknowledge_mock_market_data_execution: bool,
    mock_domain: bool,
):
    fixture = _load_kiwoom_mock_market_data_execution_fixture_or_raise(fixture_file)
    return execute_kiwoom_mock_market_data(
        fixture,
        execute=execute,
        acknowledge_mock_market_data_execution=acknowledge_mock_market_data_execution,
        mock_domain=mock_domain,
        access_token="redacted-cli-in-memory-token",
    )


def _load_quant_strategy_robustness_fixture_or_raise(fixture_file: Path):
    return load_quant_strategy_robustness_fixture(fixture_file)


def _run_quant_strategy_robustness(fixture_file: Path):
    fixture = _load_quant_strategy_robustness_fixture_or_raise(fixture_file)
    return build_quant_strategy_robustness(fixture)


def _load_point_in_time_universe_fixture_or_raise(fixture_file: Path):
    return load_point_in_time_universe_fixture(fixture_file)


def _run_point_in_time_universe_gate(fixture_file: Path):
    fixture = _load_point_in_time_universe_fixture_or_raise(fixture_file)
    return build_point_in_time_universe_gate(fixture)


def _load_walk_forward_validation_fixture_or_raise(fixture_file: Path):
    return load_walk_forward_validation_fixture(fixture_file)


def _run_walk_forward_validation(fixture_file: Path):
    fixture = _load_walk_forward_validation_fixture_or_raise(fixture_file)
    return build_walk_forward_validation(fixture)


def _load_training_pipeline_promotion_fixture_or_raise(fixture_file: Path):
    return load_training_pipeline_promotion_fixture(fixture_file)


def _run_training_pipeline_promotion(fixture_file: Path):
    fixture = _load_training_pipeline_promotion_fixture_or_raise(fixture_file)
    return build_training_pipeline_promotion(fixture)


def _load_strategy_ensemble_alpha_fixture_or_raise(fixture_file: Path):
    return load_strategy_ensemble_alpha_fixture(fixture_file)


def _run_strategy_ensemble_alpha_gate(fixture_file: Path):
    fixture = _load_strategy_ensemble_alpha_fixture_or_raise(fixture_file)
    return build_strategy_ensemble_alpha_gate(fixture)


def _load_regime_allocation_learning_fixture_or_raise(fixture_file: Path):
    return load_regime_allocation_learning_fixture(fixture_file)


def _run_regime_allocation_learning_dataset(fixture_file: Path):
    fixture = _load_regime_allocation_learning_fixture_or_raise(fixture_file)
    return build_regime_allocation_learning_dataset(fixture)


def _load_allocation_policy_training_fixture_or_raise(fixture_file: Path):
    return load_allocation_policy_training_fixture(fixture_file)


def _run_allocation_policy_training_sandbox(fixture_file: Path):
    fixture = _load_allocation_policy_training_fixture_or_raise(fixture_file)
    return build_allocation_policy_training_sandbox(fixture)


def _load_cnn_fear_greed_fixture_or_raise(fixture_file: Path):
    return load_cnn_fear_greed_fixture(fixture_file)


def _run_cnn_fear_greed_collection(
    fixture_file: Path,
    *,
    execute: bool = False,
    acknowledge_collection: bool = False,
):
    fixture = _load_cnn_fear_greed_fixture_or_raise(fixture_file)
    if execute or acknowledge_collection:
        fixture = fixture.model_copy(
            update={
                "enabled": execute or fixture.enabled,
                "execute_collection": execute,
                "acknowledge_collection": acknowledge_collection,
                "allow_real_network": execute and acknowledge_collection,
            }
        )
    return run_cnn_fear_greed_collection(fixture)


def _load_risk_adjusted_paper_eval_fixture_or_raise(fixture_file: Path):
    return load_risk_adjusted_paper_eval_fixture(fixture_file)


def _run_risk_adjusted_paper_eval(fixture_file: Path):
    fixture = _load_risk_adjusted_paper_eval_fixture_or_raise(fixture_file)
    return build_risk_adjusted_paper_evaluation(fixture)


def _load_controlled_mock_readiness_fixture_or_raise(fixture_file: Path):
    return load_controlled_mock_readiness_fixture(fixture_file)


def _run_controlled_mock_readiness(fixture_file: Path):
    fixture = _load_controlled_mock_readiness_fixture_or_raise(fixture_file)
    return build_controlled_mock_readiness_review(fixture)


def _load_market_regime_fixture_or_raise(fixture_file: Path):
    return load_market_regime_fixture(fixture_file)


def _run_market_regime(fixture_file: Path):
    fixture = _load_market_regime_fixture_or_raise(fixture_file)
    return build_market_regime(fixture)


def run_evaluate_and_save(args: argparse.Namespace) -> dict[str, object]:
    policy = load_policy(args.policy) if args.policy else None
    proposal = build_proposal(args)
    repository = RiskRepository(args.db)
    company_adapter = _build_company_risk_adapter(args.company_risk_file, args.nasdaq_noncompliant_file)
    service = RiskEvaluationService(
        policy=policy,
        market_adapter=_build_market_data_adapter(args, repository),
        company_risk_adapter=company_adapter,
        toss_signal_adapter=FileTossSignalAdapter(args.toss_file) if args.toss_file else None,
    )
    context = service.evaluate_with_context(proposal)
    news_events = FileNewsAdapter(args.news_file).get_news_events(proposal.ticker) if args.news_file else []
    saved = save_evaluation_inputs_and_result(
        repository=repository,
        proposal=context.proposal,
        policy=context.policy,
        market=context.market,
        company=context.company,
        toss_signal=context.toss_signal,
        result=context.result,
        news_events=news_events,
        source=args.source,
    )
    if args.nasdaq_noncompliant_file:
        repository.upsert_data_source(_nasdaq_data_source())
    if args.price_history_file:
        repository.upsert_data_source(_price_history_data_source("price_history_file", SourceType.FILE))
    if args.use_db_price_history:
        repository.upsert_data_source(_price_history_data_source("price_history_db", SourceType.SYSTEM))
    return {
        "result": context.result.model_dump(mode="json"),
        "saved": {
            "db": str(args.db),
            "evaluation_id": saved.evaluation_id,
            "market_snapshot_id": saved.market_snapshot_id,
            "company_risk_id": saved.company_risk_id,
            "toss_investor_snapshot_id": saved.toss_investor_snapshot_id,
            "news_event_ids": saved.news_event_ids,
        },
    }


def run_ingest_nasdaq_noncompliant(args: argparse.Namespace) -> dict[str, object]:
    repository = RiskRepository(args.db)
    repository.upsert_data_source(_nasdaq_data_source())
    run_id = repository.start_ingestion_run(NASDAQ_NONCOMPLIANT_SOURCE_NAME, SourceType.FILE.value, {"file": str(args.file)})
    records_seen = 0
    try:
        records = NasdaqNoncompliantFileAdapter(args.file).load_records()
        records_seen = len(records)
        ids = repository.save_compliance_records(records)
        repository.finish_ingestion_run(
            run_id,
            IngestionStatus.SUCCESS.value,
            records_seen=records_seen,
            records_saved=len(ids),
        )
    except Exception as error:
        repository.finish_ingestion_run(
            run_id,
            IngestionStatus.FAILED.value,
            records_seen=records_seen,
            records_saved=0,
            error_message=str(error),
        )
        raise
    return {
        "source_name": NASDAQ_NONCOMPLIANT_SOURCE_NAME,
        "records_seen": records_seen,
        "records_saved": len(ids),
        "status": IngestionStatus.SUCCESS.value,
    }


def run_check_compliance(args: argparse.Namespace) -> dict[str, object]:
    status = NasdaqNoncompliantFileAdapter(args.file).is_noncompliant(args.ticker)
    return status.model_dump(mode="json", exclude_none=True)


def run_ingest_prices(args: argparse.Namespace) -> dict[str, object]:
    repository = RiskRepository(args.db)
    run_id = repository.start_ingestion_run("file_price_history", "FILE", {"file": str(args.file)})
    bars = FilePriceHistoryAdapter(args.file).load_price_bars()
    ids = repository.save_price_bars(bars)
    repository.finish_ingestion_run(run_id, "SUCCESS", records_seen=len(bars), records_saved=len(ids))
    return {
        "db": str(args.db),
        "file": str(args.file),
        "ingestion_run_id": run_id,
        "inserted_or_updated": len(ids),
        "price_bar_ids": ids,
    }


def run_import_data(args: argparse.Namespace) -> dict[str, object]:
    run = run_unified_import(
        RiskRepository(args.db),
        price_history_file=args.price_history_file,
        nasdaq_noncompliant_file=args.nasdaq_noncompliant_file,
        news_signal_file=args.news_signal_file,
        dilution_signal_file=args.dilution_signal_file,
        toss_signal_file=args.toss_signal_file,
        flow_signal_file=args.flow_signal_file,
        fx_rate_file=args.fx_rate_file,
        as_of_date=args.as_of_date,
    )
    return import_run_report(run)


def _dump_order_result(result):
    if hasattr(result, "model_dump"):
        return result.model_dump(mode="json")
    if isinstance(result, list):
        return [_dump_order_result(item) for item in result]
    if isinstance(result, dict):
        return {key: _dump_order_result(value) for key, value in result.items()}
    return result


def run_analysis_report(args: argparse.Namespace, builder, source_id: str) -> dict[str, object]:
    repository = RiskRepository(args.db)
    report = builder(repository, source_id, args.language)
    requested = args.output_file is not None
    saved = False
    output_error = None
    if requested:
        try:
            args.output_file.parent.mkdir(parents=True, exist_ok=True)
            content = report.markdown if args.format == "markdown" else json.dumps(render_json(report), ensure_ascii=False, indent=2)
            args.output_file.write_text(content or "", encoding="utf-8")
            saved = True
        except Exception as error:
            output_error = str(error)
            report = report.model_copy(update={"warnings": [*report.warnings, f"failed to write output file: {error}"]})
            report = report.model_copy(update={"markdown": render_markdown(report, args.language)})
    saved_to_db = False
    if args.save:
        repository.save_analysis_report(report)
        saved_to_db = True
    return {
        "report": render_json(report),
        "content": report.markdown if args.format == "markdown" else render_json(report),
        "format": args.format,
        "output_file_requested": requested,
        "output_file_saved": saved,
        "output_file_error": output_error,
        "saved_to_analysis_reports": saved_to_db,
    }


def run_agent_local(args: argparse.Namespace) -> dict[str, object]:
    repository = RiskRepository(args.db)
    prompt = repository.get_agent_prompt(args.prompt_id)
    backend = LocalLLMBackend(args.backend.replace("-", "_").upper())
    request = LocalLLMRequest(
        backend=backend, model=args.model, endpoint_url=args.endpoint_url, prompt_id=prompt.prompt_id,
        system_instructions=prompt.system_instructions, user_prompt=prompt.user_prompt,
        context_json=prompt.context_json, temperature=args.temperature, max_tokens=args.max_tokens,
    )
    response = LocalLLMClient().run(request)
    if args.save:
        repository.save_local_llm_request(request)
        repository.save_local_llm_response(response)
    return {
        **response.model_dump(mode="json"), "endpoint_url": request.endpoint_url,
        "request_saved": args.save, "response_saved": args.save,
    }


def run_backtest(args: argparse.Namespace) -> dict[str, object]:
    results = BacktestService(repository=RiskRepository(args.db)).run_all(args.horizon_days)
    return {
        "db": str(args.db),
        "horizon_days": args.horizon_days,
        "total": len(results),
        "results": [result.model_dump(mode="json") for result in results],
    }


def run_backtest_summary(args: argparse.Namespace) -> dict[str, object]:
    return BacktestService(repository=RiskRepository(args.db)).summarize_results()


def run_report(args: argparse.Namespace) -> dict[str, object]:
    return ReportService(repository=RiskRepository(args.db)).full_report()


def run_reasons(args: argparse.Namespace) -> dict[str, object]:
    reasons = RiskRepository(args.db).get_evaluation_reasons(args.evaluation_id)
    return {
        "risk_evaluation_id": args.evaluation_id,
        "reasons": [reason.model_dump(mode="json", exclude_none=True) for reason in reasons],
    }


def run_sources(args: argparse.Namespace) -> dict[str, object]:
    sources = RiskRepository(args.db).get_data_sources()
    return {"sources": [source.model_dump(mode="json") for source in sources]}


def run_ingestion_runs(args: argparse.Namespace) -> dict[str, object]:
    runs = RiskRepository(args.db).get_ingestion_runs(args.limit)
    return {"ingestion_runs": [run.model_dump(mode="json", exclude_none=True) for run in runs]}


def run_analyze_indicators(args: argparse.Namespace, save: bool) -> dict[str, object]:
    bars, repository, source_name, source_type = _load_price_bars_for_analysis(args)

    indicator_set, score = analyze_price_bars(args.ticker, bars, source_name, source_type)
    output: dict[str, object] = {
        **indicator_set.model_dump(mode="json"),
        "score": score.model_dump(mode="json"),
    }
    if save:
        if repository is None:
            raise ValueError("--db is required when saving indicators")
        ids = repository.save_indicator_values(indicator_set.indicators)
        repository.upsert_data_source(_price_history_data_source(source_name, source_type))
        output["saved"] = {"db": str(args.db), "indicator_values": len(ids), "indicator_value_ids": ids}
    return output


def run_create_trade_plan(args: argparse.Namespace, save: bool) -> dict[str, object]:
    setup, bars = _analyze_setup(args)
    policy = TradeSizingPolicy(
        account_equity=args.account_equity,
        cash_available=args.cash_available,
        max_single_trade_loss_pct=args.max_single_trade_loss_pct,
        max_position_pct=args.max_position_pct,
    )
    plan = create_trade_plan(setup, bars, policy)
    output = plan.model_dump(mode="json")
    if save:
        repository = RiskRepository(args.db)
        output["saved"] = {"db": str(args.db), "trade_plan_id": repository.save_trade_plan(plan)}
    return output


def _analyze_setup(args: argparse.Namespace):
    bars, _, source_name, source_type = _load_price_bars_for_analysis(args)
    indicator_set, _ = analyze_price_bars(args.ticker, bars, source_name, source_type)
    return SetupGrader().grade(indicator_set, _resolve_strategy_policy(args)), bars


def _load_price_bars_for_analysis(args: argparse.Namespace):
    repository = RiskRepository(args.db) if args.db else None
    if args.price_history_file:
        return FilePriceHistoryAdapter(args.price_history_file).load_price_bars(), repository, "price_history_file", SourceType.FILE
    if args.use_db_price_history and repository is not None:
        return repository.get_all_price_history(args.ticker), repository, "price_history_db", SourceType.SYSTEM
    raise ValueError("Provide --price-history-file or --use-db-price-history with --db")


def run_build_basket(args: argparse.Namespace, save: bool) -> dict[str, object]:
    repository = RiskRepository(args.db)
    strategy_policy = _resolve_strategy_policy(args, repository)
    trade_plans = [
        plan
        for plan in repository.list_trade_plans(limit=max(args.max_candidates * 3, 50))
        if plan.decision in {TradeDecision.PROPOSE, TradeDecision.REVIEW}
    ]
    policy = BasketPolicy(
        account_equity=args.account_equity,
        cash_available=args.cash_available,
        max_candidates=args.max_candidates,
        min_candidates=args.min_candidates,
        max_basket_loss_pct=args.max_basket_loss_pct,
        max_basket_notional_pct=args.max_basket_notional_pct,
        max_same_sector_count=args.max_same_sector_count,
        max_same_theme_count=args.max_same_theme_count,
    )
    if strategy_policy is not None:
        policy = apply_strategy_policy_to_basket_policy(policy, strategy_policy)
    plan = build_basket([candidate_from_trade_plan(item) for item in trade_plans], policy, strategy_policy)
    output = plan.model_dump(mode="json")
    if save:
        output["saved"] = {"db": str(args.db), "basket_plan_id": repository.save_basket_plan(plan)}
    return output


def run_paper_trade_basket(args: argparse.Namespace, from_file: bool) -> dict[str, object]:
    repository = RiskRepository(args.db)
    plan = repository.get_basket_plan(args.basket_id)
    if from_file:
        bars = FilePriceHistoryAdapter(args.price_history_file).load_price_bars()
        prices = _group_price_bars(bars)
    else:
        prices = {
            allocation.ticker: repository.get_all_price_history(allocation.ticker)
            for allocation in plan.allocations
        }
    result, trades = run_basket_backtest(plan, prices, plan.created_at.date(), args.horizon_days)
    trade_ids = repository.save_paper_trades(trades)
    result_id = repository.save_basket_backtest_result(result)
    return {
        **result.model_dump(mode="json"),
        "trades": [trade.model_dump(mode="json") for trade in trades],
        "saved": {
            "db": str(args.db),
            "paper_trade_ids": trade_ids,
            "basket_backtest_result_id": result_id,
        },
    }


def run_strategy_init(args: argparse.Namespace) -> dict[str, object]:
    repository = RiskRepository(args.db)
    try:
        policy = repository.get_strategy_policy("default", "v1")
    except LookupError:
        policy = create_default_strategy_policy()
        repository.save_strategy_policy(policy)
    return policy.model_dump(mode="json")


def run_strategy_propose(args: argparse.Namespace) -> dict[str, object]:
    repository = RiskRepository(args.db)
    baseline = repository.get_active_strategy_policy()
    if baseline is None:
        raise LookupError("No active strategy policy. Run strategy-init first.")
    policies = StrategyOptimizer().propose_candidate_policies(baseline, args.n)
    ids = [repository.save_strategy_policy(policy) for policy in policies]
    return {
        "policies": [policy.model_dump(mode="json") for policy in policies],
        "saved": {"db": str(args.db), "strategy_policy_ids": ids},
    }


def run_strategy_evaluate(args: argparse.Namespace) -> dict[str, object]:
    repository = RiskRepository(args.db)
    policy = repository.get_strategy_policy(args.policy_id, args.version)
    experiment = StrategyOptimizer(repository).evaluate_policy_from_basket_results(policy, args.horizon_days)
    experiment_id = repository.save_strategy_experiment(experiment)
    return {
        **experiment.model_dump(mode="json"),
        "warning": (
            "COMMON_OUTCOME_EVALUATION is not actual candidate policy performance comparison; "
            "the candidate was not replayed against historical features."
        ),
        "saved": {"db": str(args.db), "strategy_experiment_id": experiment_id},
    }


def run_scan_candidates(args: argparse.Namespace) -> dict[str, object]:
    repository = RiskRepository(args.db)
    if args.ticker:
        source = CandidateSource.MANUAL_LIST
        tickers = load_manual_universe(args.ticker)
    elif args.price_history_file:
        source = CandidateSource.PRICE_HISTORY_FILE
        tickers = load_file_universe(args.price_history_file, args.as_of_date)
    else:
        source = CandidateSource.PRICE_HISTORY_DB
        tickers = load_db_universe(repository, args.as_of_date)
    policy = CandidateScanPolicy(
        max_candidates=args.max_candidates,
        min_avg_dollar_volume_20d=args.min_avg_dollar_volume_20d,
        min_volume_spike_ratio=args.min_volume_spike_ratio,
    )
    file_signals = _load_signal_files(args)
    db_signals = [] if args.ignore_db_signals else repository.list_ticker_signals(as_of_date=args.as_of_date)
    merged = merge_signal_sources(db_signals, file_signals, args.as_of_date)
    saved_signal_ids = repository.save_ticker_signals(file_signals) if args.save_signals else []
    skipped_duplicate_count = len(file_signals) - len(saved_signal_ids) if args.save_signals else 0
    signal_counts = {
        "db_signal_count": merged.db_signal_count,
        "file_signal_count": merged.file_signal_count,
        "merged_signal_count": merged.merged_signal_count,
        "deduped_signal_count": merged.deduped_signal_count,
    }
    output = run_candidate_scan(
        repository=repository,
        price_provider=AsOfPriceHistoryProvider(
            repository=None if args.price_history_file else repository,
            price_history_file=args.price_history_file,
        ),
        tickers=tickers,
        as_of_date=args.as_of_date,
        source=source,
        policy=policy,
        strategy_policy=_resolve_strategy_policy(args, repository),
        save=args.save,
        signals=merged.signals,
        signal_counts=signal_counts,
    )
    return {
        **output.run.model_dump(mode="json"),
        "saved": output.saved,
        **signal_counts,
        "saved_signal_count": len(saved_signal_ids),
        "skipped_duplicate_count": skipped_duplicate_count,
        "top_candidates": [item.model_dump(mode="json") for item in output.results],
    }


def run_ingest_signals(args: argparse.Namespace) -> dict[str, object]:
    repository = RiskRepository(args.db)
    file_signals = _load_signal_files(args)
    ids = repository.save_ticker_signals(file_signals)
    return {
        "file_signal_count": len(file_signals),
        "saved_signal_count": len(ids),
        "skipped_duplicate_count": len(file_signals) - len(ids),
        "ticker_signal_ids": ids,
    }


def _load_signal_files(args: argparse.Namespace):
    as_of_date = args.as_of_date
    signals = []
    loaders = (
        ("news_signal_file", load_news_signals),
        ("dilution_signal_file", load_dilution_signals),
        ("toss_signal_file", load_toss_signals),
        ("flow_signal_file", load_flow_signals),
    )
    for attribute, loader in loaders:
        path = getattr(args, attribute, None)
        if path:
            signals.extend(loader(path, as_of_date))
    return signals


def _run_operational_paper(args: argparse.Namespace, mode: PipelineMode = PipelineMode.PAPER_BASKET) -> dict[str, object]:
    repository = RiskRepository(args.db)
    context = build_portfolio_currency_context(
        FXService(repository), args.account_currency, args.trading_currency, args.as_of_date,
        account_equity=args.account_equity, cash_available=args.cash_available,
        manual_rate=args.fx_rate, manual_source_name=args.fx_source_name,
        max_staleness_days=args.max_fx_staleness_days,
    )
    execution = OperationalPipeline(repository).run_paper_basket_pipeline(
        args.as_of_date, context.account_equity_trading, context.cash_available_trading, args.horizon_days,
        price_history_file=args.price_history_file, signal_files=_operational_signal_files(args),
        ignore_db_signals=args.ignore_db_signals, strategy_policy=_resolve_strategy_policy(args, repository),
        include_watch=args.include_watch, save_basket=args.save_basket,
        save_replay_snapshot=not getattr(args, "no_replay_snapshot", False),
        paper_trade=not args.no_paper_trade, mode=mode, currency_context=context,
    )
    output = _operational_output(execution)
    if getattr(args, "notify", False):
        try:
            notification = _deliver_pipeline_notification(
                repository, execution.run.pipeline_run_id, args.notification_channel,
                args.notification_output_file, args.notification_min_severity,
            )
            output["notification_run_id"] = notification.notification_run_id
            output["notification_status"] = notification.status.value
        except Exception as error:
            run = repository.get_pipeline_run(execution.run.pipeline_run_id)
            note = f"notification_status=FAILED; notification_error={error}"
            repository.update_pipeline_run(run.model_copy(update={"notes": [*run.notes, note]}))
            output.update({"notification_run_id": None, "notification_status": "FAILED", "notification_error": str(error)})
    if getattr(args, "build_dashboard", False):
        dashboard_path = args.dashboard_output_file or Path("dashboard") / f"pipeline_{execution.run.pipeline_run_id}.html"
        try:
            dashboard = build_pipeline_dashboard(repository, execution.run.pipeline_run_id, dashboard_path, save=True)
        except Exception as error:
            dashboard = DashboardBuildResult(
                dashboard_type=DashboardType.PIPELINE_RUN, source_id=execution.run.pipeline_run_id,
                status=DashboardBuildStatus.FAILED, output_path=str(dashboard_path),
                errors=[f"dashboard build failed: {error}"],
            )
            repository.save_dashboard_build(dashboard)
        run = repository.get_pipeline_run(execution.run.pipeline_run_id)
        note = f"dashboard_id={dashboard.dashboard_id}; dashboard_status={dashboard.status.value}"
        repository.update_pipeline_run(run.model_copy(update={"notes": [*run.notes, note]}))
        output["dashboard_id"] = dashboard.dashboard_id
        output["dashboard_status"] = dashboard.status.value
    return output


def _operational_output(execution) -> dict[str, object]:
    return {
        **execution.summary.model_dump(mode="json"),
        "mode": execution.run.mode.value,
        "scan_run_id": execution.run.scan_run_id,
        "basket_id": execution.run.basket_id,
        "replay_run_id": execution.run.replay_run_id,
        "policy_replay_id": execution.run.policy_replay_id,
        "evaluation_suite_id": execution.run.evaluation_suite_id,
        "save_basket": execution.save_basket,
        "paper_trade": execution.paper_trade,
        "paper_result_persisted": execution.paper_result_persisted,
        "basket_saved_to_basket_plans": execution.basket_saved_to_basket_plans,
    }


def run_notification_command(args: argparse.Namespace) -> dict[str, object]:
    repository = RiskRepository(args.db)
    minimum = _notification_severity(args.min_severity)
    if args.command == "notify-pipeline":
        messages = build_notifications_from_pipeline(repository, args.pipeline_run_id, minimum)
    elif args.command == "notify-report":
        messages = build_notifications_from_report(repository, args.report_id, minimum)
    elif args.command == "notify-brief":
        messages = build_notifications_from_agent_brief(repository, args.brief_id, minimum)
    elif args.command == "notify-local-response":
        messages = build_notifications_from_local_llm_response(repository, args.response_id, minimum)
    else:
        messages = [build_daily_digest(
            repository, args.as_of_date, minimum,
            include_local_llm_responses=args.include_local_llm_responses,
        )]
    run = deliver_notifications(
        repository, messages, _notification_channel(args.channel),
        output_path=args.output_file, output_dir=args.output_dir, save=args.save,
    )
    return run.model_dump(mode="json")


def _deliver_pipeline_notification(repository, pipeline_run_id, channel, output_file, min_severity):
    messages = build_notifications_from_pipeline(repository, pipeline_run_id, _notification_severity(min_severity))
    notification = deliver_notifications(
        repository, messages, _notification_channel(channel), output_path=output_file, save=True,
    )
    run = repository.get_pipeline_run(pipeline_run_id)
    note = f"notification_run_id={notification.notification_run_id}; notification_status={notification.status.value}"
    repository.update_pipeline_run(run.model_copy(update={"notes": [*run.notes, note]}))
    return notification


def _notification_channel(value: str) -> NotificationChannelType:
    return NotificationChannelType(value.replace("-", "_").upper())


def _notification_severity(value: str) -> NotificationSeverity:
    return NotificationSeverity(value.upper())


def _operational_signal_files(args: argparse.Namespace) -> dict[str, Path]:
    return {
        name: path for name, path in {
            "news": getattr(args, "news_signal_file", None),
            "dilution": getattr(args, "dilution_signal_file", None),
            "toss": getattr(args, "toss_signal_file", None),
            "flow": getattr(args, "flow_signal_file", None),
        }.items() if path is not None
    }


def run_scan_to_basket(args: argparse.Namespace) -> dict[str, object]:
    repository = RiskRepository(args.db)
    strategy_policy = _resolve_strategy_policy(args, repository)
    policy = BasketPolicy(
        account_equity=args.account_equity,
        cash_available=args.cash_available,
        max_candidates=args.max_candidates,
        min_candidates=args.min_candidates,
        max_basket_loss_pct=args.max_basket_loss_pct,
        max_basket_notional_pct=args.max_basket_notional_pct,
        max_same_sector_count=args.max_same_sector_count,
        max_same_theme_count=args.max_same_theme_count,
    )
    if strategy_policy is not None:
        policy = apply_strategy_policy_to_basket_policy(policy, strategy_policy)
    basket, saved = create_basket_from_scan_run(
        repository,
        args.scan_run_id,
        args.account_equity,
        args.cash_available,
        include_watch=args.include_watch,
        save_basket=args.save_basket,
        basket_policy=policy,
        strategy_policy=strategy_policy,
    )
    return {**basket.model_dump(mode="json"), "saved_to_basket_plans": saved}


def run_policy_replay(args: argparse.Namespace, active: bool) -> dict[str, object]:
    repository = RiskRepository(args.db)
    if active:
        policy = repository.get_active_strategy_policy()
        if policy is None:
            raise LookupError("No active strategy policy. Run strategy-init first.")
        policy_id, policy_version = policy.policy_id, policy.version
    else:
        policy_id, policy_version = args.policy_id, args.policy_version
    execution = replay_policy_on_replay_run(
        repository=repository,
        price_provider=_policy_replay_price_provider(args, repository),
        source_replay_run_id=args.replay_run_id,
        policy_id=policy_id,
        policy_version=policy_version,
        horizon_days=args.horizon_days,
        account_equity=args.account_equity,
        cash_available=args.cash_available,
        save_intermediate=args.save_intermediate,
        save_basket=args.save_basket,
    )
    return execution.model_dump(mode="json")


def run_policy_compare(args: argparse.Namespace) -> dict[str, object]:
    repository = RiskRepository(args.db)
    comparison = compare_policy_replays(
        repository=repository,
        price_provider=_policy_replay_price_provider(args, repository),
        source_replay_run_id=args.replay_run_id,
        baseline_policy_id=args.baseline_policy_id,
        baseline_policy_version=args.baseline_policy_version,
        candidate_policy_id=args.candidate_policy_id,
        candidate_policy_version=args.candidate_policy_version,
        horizon_days=args.horizon_days,
        account_equity=args.account_equity,
        cash_available=args.cash_available,
    )
    return {
        "source_replay_run_id": comparison.source_replay_run_id,
        "baseline": {
            "policy_id": comparison.baseline_policy_id,
            "version": comparison.baseline_policy_version,
            "realized_return_pct": comparison.baseline_return_pct,
            "objective_score": comparison.baseline_objective_score,
        },
        "candidate": {
            "policy_id": comparison.candidate_policy_id,
            "version": comparison.candidate_policy_version,
            "realized_return_pct": comparison.candidate_return_pct,
            "objective_score": comparison.candidate_objective_score,
        },
        "return_delta_pct": comparison.return_delta_pct,
        "objective_delta": comparison.objective_delta,
        "recommendation": comparison.recommendation.value,
        "notes": comparison.notes,
    }


def run_policy_evaluate_suite(args: argparse.Namespace) -> dict[str, object]:
    repository = RiskRepository(args.db)
    run_ids = args.replay_run_id or [run.run_id for run in repository.list_replay_runs(limit=args.min_replay_runs)]
    pairs = run_policy_replay_batch(
        repository, _policy_replay_price_provider(args, repository), run_ids,
        args.baseline_policy_id, args.baseline_policy_version, args.candidate_policy_id,
        args.candidate_policy_version, args.horizon_days, args.account_equity, args.cash_available,
    )
    suite = evaluate_policy_suite(pairs, args.min_replay_runs, args.min_completed_replays)
    repository.save_policy_evaluation_suite(suite)
    return policy_evaluation_report(suite)


def _policy_replay_price_provider(args: argparse.Namespace, repository: RiskRepository) -> AsOfPriceHistoryProvider:
    return AsOfPriceHistoryProvider(
        repository=None if args.price_history_file else repository,
        price_history_file=args.price_history_file,
    )


def _group_price_bars(bars: list[PriceBar]) -> dict[str, list[PriceBar]]:
    grouped: dict[str, list[PriceBar]] = {}
    for bar in bars:
        grouped.setdefault(bar.ticker, []).append(bar)
    return grouped


def _resolve_strategy_policy(
    args: argparse.Namespace,
    repository: RiskRepository | None = None,
):
    use_active = bool(getattr(args, "use_active_policy", False))
    policy_id = getattr(args, "policy_id", None)
    policy_version = getattr(args, "policy_version", None)
    if use_active and (policy_id or policy_version):
        raise ValueError("--use-active-policy cannot be combined with --policy-id/--policy-version")
    if bool(policy_id) != bool(policy_version):
        raise ValueError("--policy-id and --policy-version must be provided together")
    if not use_active and not policy_id:
        return None
    db_path = getattr(args, "db", None)
    if repository is None:
        if db_path is None:
            raise ValueError("--db is required when selecting a strategy policy")
        repository = RiskRepository(db_path)
    if use_active:
        policy = repository.get_active_strategy_policy()
        if policy is None:
            raise LookupError("No active strategy policy. Run strategy-init first.")
        return policy
    return repository.get_strategy_policy(policy_id, policy_version)


def build_proposal(args: argparse.Namespace) -> TradeProposal:
    return TradeProposal(
        ticker=args.ticker,
        side=args.side,
        reason=args.reason,
        llm_confidence=args.confidence,
        intended_holding_days=args.holding_days,
    )


def _build_company_risk_adapter(company_risk_file: Path | None, nasdaq_noncompliant_file: Path | None):
    base_adapter = FileCompanyRiskAdapter(company_risk_file) if company_risk_file else MockCompanyRiskAdapter()
    if not nasdaq_noncompliant_file:
        return base_adapter if company_risk_file else None
    return FileCompanyRiskWithComplianceAdapter(
        base_company_risk_adapter=base_adapter,
        compliance_adapter=NasdaqNoncompliantFileAdapter(nasdaq_noncompliant_file),
    )


def _build_market_data_adapter(args: argparse.Namespace, repository: RiskRepository):
    if args.price_history_file:
        return PriceHistoryMarketDataAdapter(price_history_file=args.price_history_file, source_name="price_history_file")
    if args.use_db_price_history:
        return PriceHistoryMarketDataAdapter(repository=repository, source_name="price_history_db")
    if args.market_file:
        return FileMarketDataAdapter(args.market_file)
    return None


def _nasdaq_data_source() -> DataSource:
    return DataSource(
        name=NASDAQ_NONCOMPLIANT_SOURCE_NAME,
        source_type=SourceType.FILE,
        description="User-provided Nasdaq noncompliant companies CSV",
        base_url="https://www.nasdaq.com/market-activity/stocks/non-compliant-company-list",
    )


def _price_history_data_source(name: str, source_type: SourceType) -> DataSource:
    return DataSource(
        name=name,
        source_type=source_type,
        description="Local price history used to calculate market snapshots",
    )


if __name__ == "__main__":
    main()
