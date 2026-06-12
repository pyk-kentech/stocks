from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from stock_risk_mcp.adapters.file_price_history import FilePriceHistoryAdapter
from stock_risk_mcp.adapters.file_company_risk import FileCompanyRiskAdapter, FileCompanyRiskWithComplianceAdapter
from stock_risk_mcp.adapters.file_market_data import FileMarketDataAdapter
from stock_risk_mcp.adapters.file_news import FileNewsAdapter
from stock_risk_mcp.adapters.file_toss_signal import FileTossSignalAdapter
from stock_risk_mcp.adapters.mock_company_risk import MockCompanyRiskAdapter
from stock_risk_mcp.adapters.nasdaq_noncompliant_file import NasdaqNoncompliantFileAdapter
from stock_risk_mcp.adapters.price_history_market_data import PriceHistoryMarketDataAdapter
from stock_risk_mcp.backtest import BacktestService
from stock_risk_mcp.basket import BasketPolicy, candidate_from_trade_plan
from stock_risk_mcp.basket_builder import build_basket
from stock_risk_mcp.compliance import NASDAQ_NONCOMPLIANT_SOURCE_NAME
from stock_risk_mcp.ingestion import save_evaluation_inputs_and_result
from stock_risk_mcp.indicators import analyze_price_bars
from stock_risk_mcp.models import DataSource, IngestionStatus, SourceType, TradeProposal
from stock_risk_mcp.policy import load_policy
from stock_risk_mcp.reporting import ReportService
from stock_risk_mcp.repository import RiskRepository
from stock_risk_mcp.service import RiskEvaluationService
from stock_risk_mcp.setup import TradeDecision, TradeSizingPolicy
from stock_risk_mcp.setup_grading import SetupGrader
from stock_risk_mcp.trade_plan import create_trade_plan


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
    add_indicator_args(analyze_setup, require_db=False)

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
    return parser


def add_proposal_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--ticker", required=True, help="Ticker symbol, e.g. SAFE")
    parser.add_argument("--side", required=True, choices=["BUY", "SELL"], help="Trade side")
    parser.add_argument("--confidence", required=True, type=float, help="LLM confidence from 0 to 1")
    parser.add_argument("--reason", required=True, help="Reason supplied by the LLM or client")
    parser.add_argument("--holding-days", type=int, default=30, help="Intended holding period in days")
    parser.add_argument("--policy", type=Path, default=None, help="Optional path to a policy YAML file")
    parser.add_argument("--price-history-file", type=Path, default=None, help="CSV/JSON price history file for market data")


def add_indicator_args(parser: argparse.ArgumentParser, require_db: bool) -> None:
    parser.add_argument("--ticker", required=True, help="Ticker symbol")
    parser.add_argument("--price-history-file", type=Path, default=None, help="CSV/JSON price history file")
    parser.add_argument("--db", type=Path, required=require_db, default=None if not require_db else None)
    parser.add_argument("--use-db-price-history", action="store_true", help="Use the SQLite price_history table")


def add_trade_plan_args(parser: argparse.ArgumentParser, require_db: bool) -> None:
    add_indicator_args(parser, require_db=require_db)
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


def main(argv: list[str] | None = None) -> None:
    args_list = sys.argv[1:] if argv is None else argv
    commands = {
        "evaluate-and-save",
        "ingest-nasdaq-noncompliant",
        "check-compliance",
        "ingest-prices",
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
    return SetupGrader().grade(indicator_set), bars


def _load_price_bars_for_analysis(args: argparse.Namespace):
    repository = RiskRepository(args.db) if args.db else None
    if args.price_history_file:
        return FilePriceHistoryAdapter(args.price_history_file).load_price_bars(), repository, "price_history_file", SourceType.FILE
    if args.use_db_price_history and repository is not None:
        return repository.get_all_price_history(args.ticker), repository, "price_history_db", SourceType.SYSTEM
    raise ValueError("Provide --price-history-file or --use-db-price-history with --db")


def run_build_basket(args: argparse.Namespace, save: bool) -> dict[str, object]:
    repository = RiskRepository(args.db)
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
    plan = build_basket([candidate_from_trade_plan(item) for item in trade_plans], policy)
    output = plan.model_dump(mode="json")
    if save:
        output["saved"] = {"db": str(args.db), "basket_plan_id": repository.save_basket_plan(plan)}
    return output


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
