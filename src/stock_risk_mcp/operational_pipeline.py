from __future__ import annotations

from datetime import date, datetime
from pathlib import Path
from uuid import uuid4

from pydantic import Field

from stock_risk_mcp.alerts import basket_alert, candidate_alerts, error_alert, fx_summary_alert, paper_alert, policy_alert
from stock_risk_mcp.asof_price_history import AsOfPriceHistoryProvider
from stock_risk_mcp.basket import BasketPolicy
from stock_risk_mcp.basket_backtest import run_basket_backtest
from stock_risk_mcp.candidate_universe import CandidateScanPolicy, CandidateSource, load_db_universe, load_file_universe, load_manual_universe
from stock_risk_mcp.dilution_signal_file import load_dilution_signals
from stock_risk_mcp.flow_signal_file import load_flow_signals
from stock_risk_mcp.fx_risk import apply_fx_to_basket, apply_fx_to_paper_result
from stock_risk_mcp.models import StrictModel
from stock_risk_mcp.news_signal_file import load_news_signals
from stock_risk_mcp.pipeline_report import build_pipeline_summary
from stock_risk_mcp.pipeline_run import PipelineAlert, PipelineMode, PipelineRun, PipelineRunStatus, PipelineSummary
from stock_risk_mcp.policy_evaluation_suite import evaluate_policy_suite
from stock_risk_mcp.policy_replay_batch import run_policy_replay_batch
from stock_risk_mcp.replay_snapshot import basket_snapshot_from_plan
from stock_risk_mcp.scan_pipeline import run_candidate_scan
from stock_risk_mcp.scan_run import create_basket_from_scan_run, create_replay_snapshot_from_scan_run
from stock_risk_mcp.signal_enrichment import merge_signal_sources
from stock_risk_mcp.strategy_policy import StrategyPolicy, apply_strategy_policy_to_basket_policy
from stock_risk_mcp.toss_signal_file import load_toss_signals


class OperationalPipelineExecution(StrictModel):
    run: PipelineRun
    summary: PipelineSummary
    alerts: list[PipelineAlert] = Field(default_factory=list)
    scan_results: list = Field(default_factory=list)
    basket: object | None = None
    paper_result: object | None = None
    save_basket: bool = False
    paper_trade: bool = False
    paper_result_persisted: bool = False
    basket_saved_to_basket_plans: bool = False


class OperationalPipeline:
    def __init__(self, repository) -> None:
        self.repository = repository

    def run_scan_only_pipeline(
        self,
        as_of_date: date,
        *,
        tickers: list[str] | None = None,
        price_history_file: str | Path | None = None,
        signal_files: dict[str, str | Path] | None = None,
        ignore_db_signals: bool = False,
        strategy_policy: StrategyPolicy | None = None,
        save_scan: bool = True,
        mode: PipelineMode = PipelineMode.SCAN_ONLY,
    ) -> OperationalPipelineExecution:
        run = self._start_run(mode, as_of_date, strategy_policy)
        alerts: list[PipelineAlert] = []
        try:
            scan = self._scan(as_of_date, tickers, price_history_file, signal_files, ignore_db_signals, strategy_policy, save_scan)
            alerts = candidate_alerts(run.pipeline_run_id, scan.results)
            eligible = scan.run.included_count + scan.run.watch_count
            status = PipelineRunStatus.NO_CANDIDATES if eligible == 0 else PipelineRunStatus.COMPLETED
            run = self._finish_run(
                run, status, alerts, scan_run_id=scan.run.scan_run_id, candidate_count=scan.run.universe_size,
                included_count=scan.run.included_count, watch_count=scan.run.watch_count,
            )
            return OperationalPipelineExecution(
                run=run, summary=build_pipeline_summary(run, alerts), alerts=alerts, scan_results=scan.results
            )
        except Exception as exc:
            alerts = [error_alert(run.pipeline_run_id, exc)]
            run = self._finish_run(run, PipelineRunStatus.FAILED, alerts, error=str(exc), notes=[str(exc)])
            return OperationalPipelineExecution(run=run, summary=build_pipeline_summary(run, alerts), alerts=alerts)

    def run_paper_basket_pipeline(
        self,
        as_of_date: date,
        account_equity: float,
        cash_available: float,
        horizon_days: int,
        *,
        tickers: list[str] | None = None,
        price_history_file: str | Path | None = None,
        signal_files: dict[str, str | Path] | None = None,
        ignore_db_signals: bool = False,
        strategy_policy: StrategyPolicy | None = None,
        include_watch: bool = False,
        save_basket: bool = False,
        save_replay_snapshot: bool = True,
        paper_trade: bool = True,
        mode: PipelineMode = PipelineMode.PAPER_BASKET,
        currency_context=None,
    ) -> OperationalPipelineExecution:
        run = self._start_run(mode, as_of_date, strategy_policy, currency_context)
        alerts: list[PipelineAlert] = []
        notes: list[str] = []
        basket = paper_result = None
        replay_run_id = None
        try:
            if currency_context and (
                currency_context.account_currency != currency_context.trading_currency or currency_context.warnings
            ):
                alerts.append(fx_summary_alert(
                    run.pipeline_run_id, currency_context.account_currency, currency_context.trading_currency,
                    currency_context.fx_rate, currency_context.warnings,
                ))
            scan = self._scan(
                as_of_date, tickers, price_history_file, signal_files, ignore_db_signals, strategy_policy, True,
                account_equity if currency_context else 10_000,
                cash_available if currency_context else 5_000,
                currency_context,
            )
            alerts.extend(candidate_alerts(run.pipeline_run_id, scan.results))
            run = run.model_copy(update={
                "scan_run_id": scan.run.scan_run_id,
                "candidate_count": scan.run.universe_size,
                "included_count": scan.run.included_count,
                "watch_count": scan.run.watch_count,
            })
            self.repository.update_pipeline_run(run)
            eligible = scan.run.included_count + (scan.run.watch_count if include_watch else 0)
            if eligible == 0:
                if not paper_trade:
                    notes.append("paper trading skipped by option")
                run = self._finish_run(
                    run, PipelineRunStatus.NO_CANDIDATES, alerts, scan_run_id=scan.run.scan_run_id,
                    candidate_count=scan.run.universe_size, included_count=scan.run.included_count,
                    watch_count=scan.run.watch_count, notes=notes,
                )
                return OperationalPipelineExecution(
                    run=run, summary=build_pipeline_summary(run, alerts), alerts=alerts, scan_results=scan.results,
                    save_basket=save_basket, paper_trade=paper_trade,
                )
            basket_policy = BasketPolicy(account_equity=account_equity, cash_available=cash_available)
            if strategy_policy:
                basket_policy = apply_strategy_policy_to_basket_policy(basket_policy, strategy_policy)
            basket, _ = create_basket_from_scan_run(
                self.repository, scan.run.scan_run_id, account_equity, cash_available,
                include_watch=include_watch, save_basket=False, basket_policy=basket_policy,
                strategy_policy=strategy_policy,
            )
            if currency_context:
                basket = apply_fx_to_basket(basket, currency_context)
            if save_basket:
                self.repository.save_basket_plan(basket)
            alerts.append(basket_alert(run.pipeline_run_id, basket.decision, len(basket.allocations)))
            if save_replay_snapshot:
                replay = create_replay_snapshot_from_scan_run(
                    self.repository, scan.run.scan_run_id, as_of_date, include_watch=include_watch,
                    basket_saved_to_plans=save_basket,
                )
                self.repository.save_replay_basket_snapshot(basket_snapshot_from_plan(replay.run_id, basket))
                replay_run_id = replay.run_id
                notes.append(
                    "replay snapshot basket_id may not exist in basket_plans"
                    if not save_basket else "replay snapshot basket_id exists in basket_plans"
                )
            if paper_trade:
                provider = AsOfPriceHistoryProvider(
                    repository=None if price_history_file else self.repository,
                    price_history_file=price_history_file,
                )
                prices = {item.ticker: provider.get_forward_history(item.ticker, as_of_date, horizon_days) for item in basket.allocations}
                paper_result, trades = run_basket_backtest(basket, prices, as_of_date, horizon_days)
                if currency_context:
                    paper_result = apply_fx_to_paper_result(paper_result, currency_context)
                outcome_alert = paper_alert(run.pipeline_run_id, paper_result)
                if outcome_alert is not None:
                    alerts.append(outcome_alert)
                if save_basket:
                    self.repository.save_paper_trades(trades)
                    self.repository.save_basket_backtest_result(paper_result)
                    notes.append("paper trading result was persisted because save_basket=true")
                else:
                    notes.append("paper trading result was computed in memory because save_basket=false")
            else:
                notes.append("paper trading skipped by option")
            run = self._finish_run(
                run, PipelineRunStatus.COMPLETED, alerts, scan_run_id=scan.run.scan_run_id,
                basket_id=basket.basket_id, replay_run_id=replay_run_id, candidate_count=scan.run.universe_size,
                included_count=scan.run.included_count, watch_count=scan.run.watch_count,
                basket_allocation_count=len(basket.allocations), notes=notes,
            )
            summary = build_pipeline_summary(
                run, alerts, basket_decision=basket.decision.value,
                paper_outcome=paper_result.outcome.value if paper_result else None,
                realized_return_pct=paper_result.realized_return_pct if paper_result else None,
            )
            return OperationalPipelineExecution(
                run=run, summary=summary, alerts=alerts, scan_results=scan.results, basket=basket,
                paper_result=paper_result, save_basket=save_basket, paper_trade=paper_trade,
                paper_result_persisted=bool(save_basket and paper_result), basket_saved_to_basket_plans=save_basket,
            )
        except Exception as exc:
            alerts.append(error_alert(run.pipeline_run_id, exc))
            status = PipelineRunStatus.PARTIAL if run.scan_run_id or basket is not None else PipelineRunStatus.FAILED
            run = self._finish_run(run, status, alerts, error=str(exc), notes=[*notes, str(exc)])
            return OperationalPipelineExecution(
                run=run, summary=build_pipeline_summary(run, alerts), alerts=alerts, basket=basket,
                paper_result=paper_result, save_basket=save_basket, paper_trade=paper_trade,
                basket_saved_to_basket_plans=save_basket,
            )

    def run_replay_evaluation_pipeline(
        self,
        replay_run_ids: list[str] | None,
        baseline_policy_id: str,
        baseline_policy_version: str,
        candidate_policy_id: str,
        candidate_policy_version: str,
        horizon_days: int,
        account_equity: float,
        cash_available: float,
        *,
        price_history_file: str | Path | None = None,
        min_replay_runs: int = 5,
        min_completed_replays: int = 3,
    ) -> OperationalPipelineExecution:
        runs = replay_run_ids or [item.run_id for item in self.repository.list_replay_runs(limit=5)]
        run = self._start_run(PipelineMode.REPLAY_EVALUATION, date.today(), None)
        alerts: list[PipelineAlert] = []
        try:
            provider = AsOfPriceHistoryProvider(
                repository=None if price_history_file else self.repository,
                price_history_file=price_history_file,
            )
            pairs = run_policy_replay_batch(
                self.repository, provider, runs, baseline_policy_id, baseline_policy_version,
                candidate_policy_id, candidate_policy_version, horizon_days, account_equity, cash_available,
            )
            suite = evaluate_policy_suite(pairs, min_replay_runs, min_completed_replays)
            self.repository.save_policy_evaluation_suite(suite)
            alerts = [policy_alert(run.pipeline_run_id, suite.recommendation)]
            run = self._finish_run(
                run, PipelineRunStatus.COMPLETED, alerts, evaluation_suite_id=suite.suite_id,
                candidate_count=suite.replay_run_count,
            )
            return OperationalPipelineExecution(
                run=run,
                summary=build_pipeline_summary(run, alerts, policy_recommendation=suite.recommendation.value),
                alerts=alerts,
            )
        except Exception as exc:
            alerts = [error_alert(run.pipeline_run_id, exc)]
            run = self._finish_run(run, PipelineRunStatus.FAILED, alerts, error=str(exc), notes=[str(exc)])
            return OperationalPipelineExecution(run=run, summary=build_pipeline_summary(run, alerts), alerts=alerts)

    def _scan(self, as_of_date, tickers, price_file, signal_files, ignore_db, strategy_policy, save_scan, account_equity=10_000, cash_available=5_000, currency_context=None):
        if tickers is not None:
            universe, source = load_manual_universe(tickers), CandidateSource.MANUAL_LIST
        elif price_file:
            universe, source = load_file_universe(price_file, as_of_date), CandidateSource.PRICE_HISTORY_FILE
        else:
            universe, source = load_db_universe(self.repository, as_of_date), CandidateSource.PRICE_HISTORY_DB
        files = _load_signal_files(signal_files or {}, as_of_date)
        db = [] if ignore_db else self.repository.list_ticker_signals(as_of_date=as_of_date)
        merged = merge_signal_sources(db, files, as_of_date)
        counts = {name: getattr(merged, name) for name in ("db_signal_count", "file_signal_count", "merged_signal_count", "deduped_signal_count")}
        return run_candidate_scan(
            self.repository,
            AsOfPriceHistoryProvider(repository=None if price_file else self.repository, price_history_file=price_file),
            universe, as_of_date, source, CandidateScanPolicy(), strategy_policy, save=save_scan,
            account_equity=account_equity, cash_available=cash_available,
            signals=merged.signals, signal_counts=counts, currency_context=currency_context,
        )

    def _start_run(self, mode, as_of_date, strategy_policy, currency_context=None):
        fx = {}
        if currency_context:
            fx = {
                "account_currency": currency_context.account_currency,
                "trading_currency": currency_context.trading_currency,
                "fx_rate": currency_context.fx_rate, "fx_date": currency_context.fx_date,
                "fx_source_name": currency_context.fx_source_name, "fx_stale": currency_context.fx_stale,
                "account_equity_input": currency_context.account_equity_input,
                "cash_available_input": currency_context.cash_available_input,
                "account_equity_trading": currency_context.account_equity_trading,
                "cash_available_trading": currency_context.cash_available_trading,
                "fx_warnings_json": currency_context.warnings,
            }
        run = PipelineRun(
            pipeline_run_id=uuid4().hex, mode=mode, as_of_date=as_of_date,
            policy_id=strategy_policy.policy_id if strategy_policy else None,
            policy_version=strategy_policy.version if strategy_policy else None,
            status=PipelineRunStatus.CREATED, candidate_count=0, included_count=0, watch_count=0,
            basket_allocation_count=0, alert_count=0, created_at=datetime.now(),
            **fx,
        )
        self.repository.save_pipeline_run(run)
        run = run.model_copy(update={"status": PipelineRunStatus.RUNNING})
        self.repository.update_pipeline_run(run)
        return run

    def _finish_run(self, run, status, alerts, notes=None, **updates):
        updated = run.model_copy(update={
            **updates, "status": status, "alert_count": len(alerts),
            "notes": [*run.notes, *(notes or [])], "completed_at": datetime.now(),
        })
        self.repository.save_pipeline_alerts(alerts)
        self.repository.update_pipeline_run(updated)
        return updated


def _load_signal_files(paths: dict[str, str | Path], as_of_date: date):
    loaders = {
        "news": load_news_signals, "dilution": load_dilution_signals,
        "toss": load_toss_signals, "flow": load_flow_signals,
    }
    return [signal for name, path in paths.items() if path for signal in loaders[name](path, as_of_date)]
