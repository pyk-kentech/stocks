from __future__ import annotations

import argparse
import json
import sys
from datetime import date
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
from stock_risk_mcp.connector_registry import default_connector_registry
from stock_risk_mcp.data_import import run_unified_import
from stock_risk_mcp.dashboard import build_daily_dashboard, build_overview_dashboard, build_pipeline_dashboard, build_policy_dashboard
from stock_risk_mcp.dashboard_models import DashboardBuildResult, DashboardBuildStatus, DashboardType
from stock_risk_mcp.import_report import import_run_report
from stock_risk_mcp.ingestion import save_evaluation_inputs_and_result
from stock_risk_mcp.indicators import analyze_price_bars
from stock_risk_mcp.dilution_signal_file import load_dilution_signals
from stock_risk_mcp.flow_signal_file import load_flow_signals
from stock_risk_mcp.models import DataSource, IngestionStatus, PriceBar, SourceType, TradeProposal
from stock_risk_mcp.local_llm import LocalLLMBackend, LocalLLMRequest
from stock_risk_mcp.local_llm_client import LocalLLMClient
from stock_risk_mcp.notification_digest import build_daily_digest
from stock_risk_mcp.notification_outbox import deliver_notifications
from stock_risk_mcp.notification_templates import (
    build_notifications_from_agent_brief,
    build_notifications_from_local_llm_response,
    build_notifications_from_pipeline,
    build_notifications_from_report,
)
from stock_risk_mcp.notifications import NotificationChannelType, NotificationSeverity
from stock_risk_mcp.news_signal_file import load_news_signals
from stock_risk_mcp.operational_pipeline import OperationalPipeline
from stock_risk_mcp.pipeline_report import build_pipeline_summary
from stock_risk_mcp.pipeline_run import PipelineMode
from stock_risk_mcp.policy import load_policy
from stock_risk_mcp.policy_comparison import compare_policy_replays
from stock_risk_mcp.policy_evaluation_report import policy_evaluation_report
from stock_risk_mcp.policy_evaluation_suite import evaluate_policy_suite
from stock_risk_mcp.policy_promotion import activate_policy, approve_policy, create_policy_promotion_proposal
from stock_risk_mcp.policy_replay import replay_policy_on_replay_run
from stock_risk_mcp.policy_replay_batch import run_policy_replay_batch
from stock_risk_mcp.reporting import ReportService
from stock_risk_mcp.report_json import render_json
from stock_risk_mcp.report_markdown import render_markdown
from stock_risk_mcp.repository import RiskRepository
from stock_risk_mcp.replay_dataset import load_replay_dataset
from stock_risk_mcp.replay_run import ReplayRunService
from stock_risk_mcp.scan_pipeline import run_candidate_scan
from stock_risk_mcp.scan_run import create_basket_from_scan_run, create_replay_snapshot_from_scan_run
from stock_risk_mcp.signal_enrichment import merge_signal_sources
from stock_risk_mcp.service import RiskEvaluationService
from stock_risk_mcp.setup import TradeDecision, TradeSizingPolicy
from stock_risk_mcp.setup_grading import SetupGrader
from stock_risk_mcp.strategy_optimizer import StrategyOptimizer
from stock_risk_mcp.strategy_policy import apply_strategy_policy_to_basket_policy, create_default_strategy_policy
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
    add_signal_file_args(import_data)
    import_runs = subparsers.add_parser("import-runs", help="List unified import runs.")
    import_runs.add_argument("--db", type=Path, required=True)
    import_runs.add_argument("--limit", type=int, default=50)
    import_show = subparsers.add_parser("import-show", help="Show a unified import run.")
    import_show.add_argument("--db", type=Path, required=True)
    import_show.add_argument("--import-run-id", required=True)

    subparsers.add_parser("connectors", help="List registered network-free connectors.")
    for name in ("run-connectors", "run-connectors-and-import"):
        connector_command = subparsers.add_parser(name)
        connector_command.add_argument("--db", type=Path, required=True)
        connector_command.add_argument("--as-of-date", type=date.fromisoformat, required=True)
        connector_command.add_argument("--output-dir", type=Path, required=True)
        connector_command.add_argument("--connector", action="append", required=True)
        connector_command.add_argument("--ticker", action="append", default=[])
    connector_runs = subparsers.add_parser("connector-runs", help="List connector runs.")
    connector_runs.add_argument("--db", type=Path, required=True)
    connector_runs.add_argument("--limit", type=int, default=50)
    connector_show = subparsers.add_parser("connector-show", help="Show a connector run.")
    connector_show.add_argument("--db", type=Path, required=True)
    connector_show.add_argument("--connector-run-id", required=True)

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
    add_pipeline_dashboard_args(watch)
    return parser


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


def add_paper_trade_basket_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--db", type=Path, required=True)
    parser.add_argument("--basket-id", required=True)
    parser.add_argument("--horizon-days", type=int, required=True)


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
        "connectors",
        "run-connectors",
        "run-connectors-and-import",
        "connector-runs",
        "connector-show",
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
    if args.command == "connectors":
        return {"connectors": [
            {"name": item.name, "connector_type": item.connector_type.value, "mode": item.mode.value}
            for item in default_connector_registry().list_connectors()
        ]}
    if args.command == "run-connectors":
        results = run_connectors(
            RiskRepository(args.db), default_connector_registry(), args.as_of_date,
            args.output_dir, args.connector, args.ticker,
        )
        return {
            "as_of_date": args.as_of_date.isoformat(),
            "connector_runs": [item.connector_run.model_dump(mode="json") for item in results],
            "output_file_count": sum(item.output is not None for item in results),
        }
    if args.command == "run-connectors-and-import":
        return run_connectors_and_import(
            RiskRepository(args.db), default_connector_registry(), args.as_of_date,
            args.output_dir, args.connector, args.ticker,
        )
    if args.command == "connector-runs":
        return {"connector_runs": [item.model_dump(mode="json") for item in RiskRepository(args.db).list_connector_runs(args.limit)]}
    if args.command == "connector-show":
        return RiskRepository(args.db).get_connector_run(args.connector_run_id).model_dump(mode="json")
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
        as_of_date=args.as_of_date,
    )
    return import_run_report(run)


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
    execution = OperationalPipeline(repository).run_paper_basket_pipeline(
        args.as_of_date, args.account_equity, args.cash_available, args.horizon_days,
        price_history_file=args.price_history_file, signal_files=_operational_signal_files(args),
        ignore_db_signals=args.ignore_db_signals, strategy_policy=_resolve_strategy_policy(args, repository),
        include_watch=args.include_watch, save_basket=args.save_basket,
        save_replay_snapshot=not getattr(args, "no_replay_snapshot", False),
        paper_trade=not args.no_paper_trade, mode=mode,
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
