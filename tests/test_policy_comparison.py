from datetime import date, datetime

from stock_risk_mcp.policy_comparison import create_policy_comparison
from stock_risk_mcp.policy_replay_result import PolicyReplayMode, PolicyReplayResult, PolicyReplayStatus
from stock_risk_mcp.strategy_objective import StrategyRecommendation


def test_policy_comparison_accepts_and_rejects_by_objective_delta() -> None:
    accepted = create_policy_comparison(_replay("base", 50), _replay("candidate", 55))
    rejected = create_policy_comparison(_replay("base", 50), _replay("candidate", 45))
    inconclusive = create_policy_comparison(_replay("base", 50), _replay("candidate", 54))

    assert accepted.recommendation == StrategyRecommendation.ACCEPT
    assert rejected.recommendation == StrategyRecommendation.REJECT
    assert inconclusive.recommendation == StrategyRecommendation.NEED_MORE_DATA
    assert accepted.objective_delta == 5


def test_policy_comparison_small_basket_forces_need_more_data() -> None:
    comparison = create_policy_comparison(
        _replay("base", 10, candidate_count=3),
        _replay("candidate", 90, candidate_count=2),
    )

    assert comparison.objective_delta == 80
    assert comparison.recommendation == StrategyRecommendation.NEED_MORE_DATA
    assert any("candidate_count below minimum basket size" in note for note in comparison.notes)


def _replay(policy_id: str, objective: float, candidate_count: int = 3) -> PolicyReplayResult:
    return PolicyReplayResult(
        policy_replay_id=f"replay-{policy_id}-{objective}",
        source_replay_run_id="source-1",
        replay_mode=PolicyReplayMode.FULL_POLICY_REPLAY,
        policy_id=policy_id,
        policy_version="v1",
        as_of_date=date(2026, 1, 1),
        horizon_days=10,
        candidate_count=candidate_count,
        trade_plan_count=3,
        realized_return_pct=objective / 10,
        objective_score=objective,
        status=PolicyReplayStatus.COMPLETED,
        notes=[],
        created_at=datetime(2026, 1, 2),
    )
