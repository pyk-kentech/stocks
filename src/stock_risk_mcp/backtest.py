from __future__ import annotations

from datetime import date, datetime
from pathlib import Path
from typing import Any

from stock_risk_mcp.models import BacktestOutcome, BacktestResult
from stock_risk_mcp.performance import (
    calculate_max_drawdown_pct,
    calculate_max_gain_pct,
    calculate_return_pct,
    classify_outcome,
)
from stock_risk_mcp.price_history import bars_between, select_entry_bar, select_exit_bar
from stock_risk_mcp.repository import RiskEvaluationRecord, RiskRepository


class BacktestService:
    def __init__(self, repository: RiskRepository | None = None, db_path: str | Path | None = None) -> None:
        if repository is None and db_path is None:
            raise ValueError("Either repository or db_path must be provided.")
        self.repository = repository or RiskRepository(db_path or "")

    def run_for_evaluation(self, risk_evaluation_id: int, horizon_days: int) -> BacktestResult:
        evaluation = self.repository.get_risk_evaluation_for_backtest(risk_evaluation_id)
        result = self._calculate_result(evaluation, horizon_days)
        self.repository.save_backtest_result(result)
        return result

    def run_all(self, horizon_days: int) -> list[BacktestResult]:
        results: list[BacktestResult] = []
        for evaluation in self.repository.get_pending_risk_evaluations_for_backtest():
            result = self._calculate_result(evaluation, horizon_days)
            self.repository.save_backtest_result(result)
            results.append(result)
        return results

    def summarize_results(self) -> dict[str, Any]:
        return self.repository.get_backtest_summary()

    def _calculate_result(self, evaluation: RiskEvaluationRecord, horizon_days: int) -> BacktestResult:
        evaluation_date = _parse_created_at(evaluation.created_at)
        price_bars = self.repository.get_price_history(evaluation.ticker, evaluation_date, date(9999, 12, 31))
        entry_bar = select_entry_bar(price_bars, evaluation_date)
        entry_price = entry_bar.close if entry_bar is not None else evaluation.market_price or 0.0

        if entry_bar is None:
            return _no_data_result(evaluation, horizon_days, entry_price)

        exit_bar = select_exit_bar(price_bars, entry_bar.date, horizon_days)
        if exit_bar is None:
            return _no_data_result(evaluation, horizon_days, entry_price)

        period_bars = bars_between(price_bars, entry_bar.date, exit_bar.date)
        return_pct = calculate_return_pct(entry_price, exit_bar.close)
        return BacktestResult(
            risk_evaluation_id=evaluation.id,
            ticker=evaluation.ticker,
            decision=evaluation.decision,
            score=evaluation.score,
            horizon_days=horizon_days,
            entry_price=entry_price,
            exit_price=exit_bar.close,
            return_pct=return_pct,
            max_drawdown_pct=calculate_max_drawdown_pct(period_bars, entry_price),
            max_gain_pct=calculate_max_gain_pct(period_bars, entry_price),
            outcome=classify_outcome(return_pct),
        )


def _no_data_result(
    evaluation: RiskEvaluationRecord,
    horizon_days: int,
    entry_price: float,
) -> BacktestResult:
    return BacktestResult(
        risk_evaluation_id=evaluation.id,
        ticker=evaluation.ticker,
        decision=evaluation.decision,
        score=evaluation.score,
        horizon_days=horizon_days,
        entry_price=entry_price,
        exit_price=None,
        return_pct=None,
        max_drawdown_pct=None,
        max_gain_pct=None,
        outcome=BacktestOutcome.NO_DATA,
    )


def _parse_created_at(value: str) -> date:
    return datetime.fromisoformat(value).date()
