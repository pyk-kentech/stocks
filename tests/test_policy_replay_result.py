from datetime import date, datetime

from stock_risk_mcp.policy_replay_result import (
    PolicyComparisonResult,
    PolicyReplayMode,
    PolicyReplayResult,
    PolicyReplayStatus,
    calculate_policy_replay_objective,
)
from stock_risk_mcp.repository import RiskRepository
from stock_risk_mcp.strategy_objective import StrategyRecommendation


def test_single_replay_objective_penalizes_no_data_and_small_basket() -> None:
    strong = calculate_policy_replay_objective(5, 10, 100, 4, 1, 0)
    weak = calculate_policy_replay_objective(2, 10, 100, 4, 1, 3)

    assert weak < strong


def test_repository_round_trips_policy_replay_and_comparison(tmp_path) -> None:
    repository = RiskRepository(tmp_path / "risk.sqlite3")
    replay = _replay()
    comparison = PolicyComparisonResult(
        comparison_id="compare-1",
        source_replay_run_id="source-1",
        baseline_policy_id="default",
        baseline_policy_version="v1",
        candidate_policy_id="default",
        candidate_policy_version="v2",
        baseline_replay_id="replay-1",
        candidate_replay_id="replay-2",
        baseline_return_pct=1,
        candidate_return_pct=2,
        return_delta_pct=1,
        baseline_objective_score=50,
        candidate_objective_score=56,
        objective_delta=6,
        recommendation=StrategyRecommendation.ACCEPT,
        notes=["fixture"],
        created_at=datetime(2026, 6, 13),
    )

    repository.save_policy_replay_result(replay)
    repository.save_policy_comparison_result(comparison)

    assert repository.get_policy_replay_result("replay-1") == replay
    assert repository.list_policy_replay_results("source-1") == [replay]
    assert repository.list_policy_comparison_results("source-1") == [comparison]


def _replay() -> PolicyReplayResult:
    return PolicyReplayResult(
        policy_replay_id="replay-1",
        source_replay_run_id="source-1",
        replay_mode=PolicyReplayMode.FULL_POLICY_REPLAY,
        policy_id="default",
        policy_version="v1",
        as_of_date=date(2026, 6, 1),
        horizon_days=10,
        candidate_count=3,
        trade_plan_count=3,
        basket_id="basket-1",
        total_notional_value=1000,
        total_allocated_loss=100,
        realized_pnl=50,
        realized_return_pct=5,
        win_count=2,
        loss_count=1,
        no_data_count=0,
        outcome="WIN",
        objective_score=60,
        status=PolicyReplayStatus.COMPLETED,
        notes=["fixture"],
        created_at=datetime(2026, 6, 13),
    )
