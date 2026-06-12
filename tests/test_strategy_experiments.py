from __future__ import annotations

from datetime import date, datetime

from stock_risk_mcp.models import BacktestOutcome
from stock_risk_mcp.paper_trading import BasketBacktestResult
from stock_risk_mcp.repository import RiskRepository
from stock_risk_mcp.strategy_experiments import StrategyEvaluationMode, create_common_outcome_experiment
from stock_risk_mcp.strategy_objective import StrategyRecommendation
from stock_risk_mcp.strategy_policy import create_default_strategy_policy


def test_common_outcome_experiment_aggregates_all_results_and_records_limitation() -> None:
    policy = create_default_strategy_policy()

    experiment = create_common_outcome_experiment(policy, policy, [_result("a", 10), _result("b", -5)], 10)

    assert experiment.sample_count == 2
    assert experiment.avg_realized_pnl == 2.5
    assert experiment.win_rate == 0.5
    assert experiment.loss_rate == 0.5
    assert experiment.profit_factor == 2
    assert experiment.evaluation_mode == StrategyEvaluationMode.COMMON_OUTCOME_EVALUATION
    assert experiment.recommendation == StrategyRecommendation.NEED_MORE_DATA
    assert "evaluation_mode=COMMON_OUTCOME_EVALUATION" in experiment.notes
    assert any("does not compare" in note for note in experiment.notes)


def test_repository_saves_and_lists_strategy_experiments(tmp_path) -> None:
    repository = RiskRepository(tmp_path / "risk.sqlite3")
    policy = create_default_strategy_policy()
    experiment = create_common_outcome_experiment(policy, policy, [_result("a", 10)], 10)

    assert repository.save_strategy_experiment(experiment) == 1
    assert repository.list_strategy_experiments() == [experiment]


def test_common_evaluation_can_load_all_basket_results_without_default_limit(tmp_path) -> None:
    repository = RiskRepository(tmp_path / "risk.sqlite3")
    for index in range(51):
        repository.save_basket_backtest_result(_result(str(index), 1))

    assert len(repository.list_basket_backtest_results()) == 50
    assert len(repository.list_basket_backtest_results(limit=None)) == 51


def _result(basket_id: str, pnl: float) -> BasketBacktestResult:
    return BasketBacktestResult(
        basket_id=basket_id,
        horizon_days=10,
        entry_date=date(2026, 1, 1),
        exit_date=date(2026, 1, 11),
        total_notional_value=100,
        total_allocated_loss=10,
        realized_pnl=pnl,
        realized_return_pct=pnl,
        max_drawdown=min(pnl, 0),
        max_gain=max(pnl, 0),
        win_count=int(pnl > 0),
        loss_count=int(pnl < 0),
        flat_count=int(pnl == 0),
        no_data_count=0,
        closed_trade_count=1,
        outcome=BacktestOutcome.WIN if pnl > 0 else BacktestOutcome.LOSS,
        created_at=datetime(2026, 1, 11),
    )
