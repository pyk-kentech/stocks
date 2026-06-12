from __future__ import annotations

from stock_risk_mcp.strategy_objective import StrategyRecommendation, calculate_objective_from_summary


def test_objective_needs_more_data_below_minimum_sample_count() -> None:
    result = calculate_objective_from_summary(10, 5, 4, 0.7, 0.3, 2, -3, 100)

    assert result.sample_count == 10
    assert result.recommendation == StrategyRecommendation.NEED_MORE_DATA
    assert any("sample_count" in note for note in result.notes)


def test_objective_rewards_positive_performance_and_clamps_score() -> None:
    result = calculate_objective_from_summary(50, 20, 15, 0.9, 0.1, 5, -1, 1000)

    assert 70 <= result.objective_score <= 100
    assert result.recommendation == StrategyRecommendation.ACCEPT


def test_large_drawdown_lowers_objective_even_with_positive_return() -> None:
    controlled = calculate_objective_from_summary(50, 5, 4, 0.65, 0.35, 2, -5, 100)
    large_drawdown = calculate_objective_from_summary(50, 5, 4, 0.65, 0.35, 2, -25, 100)

    assert large_drawdown.objective_score < controlled.objective_score
    assert large_drawdown.overfit_penalty > controlled.overfit_penalty
