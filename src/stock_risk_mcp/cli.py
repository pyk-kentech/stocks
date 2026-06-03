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
from stock_risk_mcp.compliance import NASDAQ_NONCOMPLIANT_SOURCE_NAME
from stock_risk_mcp.ingestion import save_evaluation_inputs_and_result
from stock_risk_mcp.models import DataSource, IngestionStatus, SourceType, TradeProposal
from stock_risk_mcp.policy import load_policy
from stock_risk_mcp.reporting import ReportService
from stock_risk_mcp.repository import RiskRepository
from stock_risk_mcp.service import RiskEvaluationService


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
    return parser


def add_proposal_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--ticker", required=True, help="Ticker symbol, e.g. SAFE")
    parser.add_argument("--side", required=True, choices=["BUY", "SELL"], help="Trade side")
    parser.add_argument("--confidence", required=True, type=float, help="LLM confidence from 0 to 1")
    parser.add_argument("--reason", required=True, help="Reason supplied by the LLM or client")
    parser.add_argument("--holding-days", type=int, default=30, help="Intended holding period in days")
    parser.add_argument("--policy", type=Path, default=None, help="Optional path to a policy YAML file")
    parser.add_argument("--price-history-file", type=Path, default=None, help="CSV/JSON price history file for market data")


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
