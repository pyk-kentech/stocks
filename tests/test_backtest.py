from __future__ import annotations

import csv
from datetime import date

from stock_risk_mcp.adapters.file_price_history import FilePriceHistoryAdapter
from stock_risk_mcp.backtest import BacktestService
from stock_risk_mcp.models import BacktestOutcome, Decision, PriceBar
from stock_risk_mcp.repository import RiskRepository
from stock_risk_mcp.service import RiskEvaluationService

from tests.utils import make_policy, make_proposal


def test_price_history_csv_ingests(tmp_path) -> None:
    price_file = tmp_path / "prices.csv"
    _write_prices(
        price_file,
        [
            ("SAFE", "2026-01-01", 100, 105, 99, 100, 1000),
            ("SAFE", "2026-01-31", 110, 112, 108, 110, 1200),
        ],
    )
    bars = FilePriceHistoryAdapter(price_file).load_price_bars()
    repository = RiskRepository(tmp_path / "risk.sqlite3")
    ids = repository.save_price_bars(bars)

    assert len(ids) == 2
    assert repository.count_rows("price_history") == 2
    assert repository.get_price_history("SAFE", date(2026, 1, 1), date(2026, 1, 31))[1].close == 110


def test_backtest_selects_entry_exit_and_saves_result(tmp_path) -> None:
    repository = RiskRepository(tmp_path / "risk.sqlite3")
    evaluation_id = _save_safe_evaluation(repository)
    repository.save_price_bars(
        [
            PriceBar(ticker="SAFE", date=date(2026, 1, 2), open=101, high=104, low=99, close=100, volume=1000),
            PriceBar(ticker="SAFE", date=date(2026, 1, 15), open=103, high=108, low=94, close=104, volume=1100),
            PriceBar(ticker="SAFE", date=date(2026, 2, 1), open=109, high=112, low=106, close=110, volume=1200),
        ]
    )

    result = BacktestService(repository=repository).run_for_evaluation(evaluation_id, horizon_days=30)

    assert result.entry_price == 100
    assert result.exit_price == 110
    assert result.return_pct == 10.0
    assert result.max_drawdown_pct == -6.0
    assert result.max_gain_pct == 12.0
    assert result.outcome == BacktestOutcome.WIN
    assert repository.count_rows("backtest_results") == 1


def test_backtest_no_data_outcome_is_saved(tmp_path) -> None:
    repository = RiskRepository(tmp_path / "risk.sqlite3")
    evaluation_id = _save_safe_evaluation(repository)

    result = BacktestService(repository=repository).run_for_evaluation(evaluation_id, horizon_days=30)

    assert result.outcome == BacktestOutcome.NO_DATA
    assert result.exit_price is None
    assert repository.count_rows("backtest_results") == 1


def test_backtest_summary_groups_by_decision(tmp_path) -> None:
    repository = RiskRepository(tmp_path / "risk.sqlite3")
    safe_id = _save_safe_evaluation(repository)
    bad_id = _save_bad_evaluation(repository)
    repository.save_price_bars(
        [
            PriceBar(ticker="SAFE", date=date(2026, 1, 2), high=101, low=99, close=100),
            PriceBar(ticker="SAFE", date=date(2026, 2, 1), high=111, low=98, close=110),
            PriceBar(ticker="BAD", date=date(2026, 1, 2), high=50, low=49, close=50),
            PriceBar(ticker="BAD", date=date(2026, 2, 1), high=49, low=40, close=45),
        ]
    )
    service = BacktestService(repository=repository)
    service.run_for_evaluation(safe_id, horizon_days=30)
    service.run_for_evaluation(bad_id, horizon_days=30)

    summary = service.summarize_results()

    assert summary["total"] == 2
    assert summary["by_decision"][Decision.ALLOW.value]["count"] == 1
    assert summary["by_decision"][Decision.ALLOW.value]["avg_return_pct"] == 10.0
    assert summary["by_decision"][Decision.ALLOW.value]["win_rate"] == 1.0
    assert summary["by_decision"][Decision.BLOCK.value]["count"] == 1
    assert summary["by_decision"][Decision.BLOCK.value]["avg_return_pct"] == -10.0
    assert summary["by_decision"][Decision.BLOCK.value]["win_rate"] == 0.0


def _save_safe_evaluation(repository: RiskRepository) -> int:
    context = RiskEvaluationService(policy=make_policy()).evaluate_with_context(make_proposal("SAFE"))
    evaluation_id = repository.save_risk_evaluation(
        proposal=context.proposal,
        policy=context.policy,
        result=context.result,
        market_snapshot_id=repository.save_market_snapshot(context.market),
        company_risk_id=repository.save_company_risk(context.company),
        toss_investor_snapshot_id=repository.save_toss_signal(context.proposal.ticker, context.toss_signal),
    )
    _set_evaluation_created_at(repository, evaluation_id)
    return evaluation_id


def _save_bad_evaluation(repository: RiskRepository) -> int:
    context = RiskEvaluationService(policy=make_policy()).evaluate_with_context(make_proposal("BAD"))
    evaluation_id = repository.save_risk_evaluation(
        proposal=context.proposal,
        policy=context.policy,
        result=context.result,
        market_snapshot_id=repository.save_market_snapshot(context.market),
        company_risk_id=repository.save_company_risk(context.company),
        toss_investor_snapshot_id=repository.save_toss_signal(context.proposal.ticker, context.toss_signal),
    )
    _set_evaluation_created_at(repository, evaluation_id)
    return evaluation_id


def _set_evaluation_created_at(repository: RiskRepository, evaluation_id: int) -> None:
    with repository._connect() as connection:
        connection.execute(
            "UPDATE risk_evaluations SET created_at = ? WHERE id = ?",
            ("2026-01-01 00:00:00", evaluation_id),
        )


def _write_prices(path, rows: list[tuple[str, str, float, float, float, float, float]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.writer(file)
        writer.writerow(["ticker", "date", "open", "high", "low", "close", "volume"])
        writer.writerows(rows)
