from datetime import date, datetime

from stock_risk_mcp.policy_evaluation_suite import (
    PolicyEvaluationDecision,
    PolicyEvaluationSuiteResult,
    evaluate_policy_suite,
)
from stock_risk_mcp.policy_replay_result import PolicyReplayMode, PolicyReplayResult, PolicyReplayStatus
from stock_risk_mcp.repository import RiskRepository


def test_suite_uses_only_completed_pairs_and_counts_exclusions(tmp_path) -> None:
    pairs = [
        (_replay("r1", "base", PolicyReplayStatus.COMPLETED, 1, 50), _replay("r1", "candidate", PolicyReplayStatus.COMPLETED, 3, 56)),
        (_replay("r2", "base", PolicyReplayStatus.COMPLETED, 2, 50), _replay("r2", "candidate", PolicyReplayStatus.NO_DATA)),
        (_replay("r3", "base", PolicyReplayStatus.NO_DATA), _replay("r3", "candidate", PolicyReplayStatus.NO_DATA)),
        (_replay("r4", "base", PolicyReplayStatus.COMPLETED), None),
    ]

    suite = evaluate_policy_suite(pairs, min_replay_runs=1, min_completed_replays=1)

    assert suite.replay_run_count == 4
    assert suite.completed_pair_count == 1
    assert suite.no_data_replay_count == 2
    assert suite.incomplete_pair_count == 1
    assert suite.baseline_avg_return_pct == 1
    assert suite.candidate_avg_return_pct == 3
    assert suite.recommendation == PolicyEvaluationDecision.NEED_MORE_DATA


def test_suite_accept_reject_and_data_gates() -> None:
    accepted_pairs = [
        (_replay(f"r{i}", "base", return_pct=1, objective=50), _replay(f"r{i}", "candidate", return_pct=3, objective=56))
        for i in range(5)
    ]
    accepted = evaluate_policy_suite(accepted_pairs, min_replay_runs=5, min_completed_replays=3)
    rejected = evaluate_policy_suite(
        [(_replay(f"x{i}", "base", objective=60), _replay(f"x{i}", "candidate", objective=50)) for i in range(5)],
        5, 3,
    )
    small = evaluate_policy_suite(
        [(_replay(f"s{i}", "base", candidate_count=2), _replay(f"s{i}", "candidate")) for i in range(5)],
        5, 3,
    )

    assert accepted.recommendation == PolicyEvaluationDecision.ACCEPT
    assert rejected.recommendation == PolicyEvaluationDecision.REJECT
    assert small.recommendation == PolicyEvaluationDecision.NEED_MORE_DATA


def test_suite_excludes_candidate_only_completed_pair() -> None:
    suite = evaluate_policy_suite(
        [(None, _replay("r1", "candidate")), (_replay("r2", "base"), _replay("r2", "candidate"))],
        min_replay_runs=1,
        min_completed_replays=1,
    )

    assert suite.completed_pair_count == 1
    assert suite.incomplete_pair_count == 1


def test_suite_data_sufficiency_precedes_good_deltas_and_return_drop_rejects() -> None:
    no_data_heavy = evaluate_policy_suite(
        [
            (_replay("r1", "base"), _replay("r1", "candidate", return_pct=5, objective=90)),
            (_replay("r2", "base"), _replay("r2", "candidate", PolicyReplayStatus.NO_DATA)),
            (_replay("r3", "base"), _replay("r3", "candidate", PolicyReplayStatus.NO_DATA)),
        ],
        min_replay_runs=1,
        min_completed_replays=1,
    )
    too_few_runs = evaluate_policy_suite(
        [(_replay("r1", "base"), _replay("r1", "candidate"))], min_replay_runs=5, min_completed_replays=1
    )
    return_reject = evaluate_policy_suite(
        [(_replay(f"x{i}", "base", return_pct=2), _replay(f"x{i}", "candidate", return_pct=-1)) for i in range(5)],
        min_replay_runs=5,
        min_completed_replays=3,
    )

    assert no_data_heavy.no_data_rate > 0.4
    assert no_data_heavy.recommendation == PolicyEvaluationDecision.NEED_MORE_DATA
    assert too_few_runs.recommendation == PolicyEvaluationDecision.NEED_MORE_DATA
    assert return_reject.recommendation == PolicyEvaluationDecision.REJECT


def test_repository_round_trips_suite(tmp_path) -> None:
    repository = RiskRepository(tmp_path / "risk.sqlite3")
    suite = evaluate_policy_suite(
        [(_replay("r1", "base"), _replay("r1", "candidate"))], min_replay_runs=1, min_completed_replays=1
    )

    repository.save_policy_evaluation_suite(suite)

    assert repository.get_policy_evaluation_suite(suite.suite_id) == suite
    assert repository.list_policy_evaluation_suites() == [suite]


def _replay(
    run_id: str,
    policy_id: str,
    status: PolicyReplayStatus = PolicyReplayStatus.COMPLETED,
    return_pct: float = 1,
    objective: float = 50,
    candidate_count: int = 3,
) -> PolicyReplayResult:
    return PolicyReplayResult(
        policy_replay_id=f"{run_id}-{policy_id}",
        source_replay_run_id=run_id,
        replay_mode=PolicyReplayMode.FULL_POLICY_REPLAY,
        policy_id=policy_id,
        policy_version="v1",
        as_of_date=date(2026, 1, 1),
        horizon_days=10,
        candidate_count=candidate_count,
        trade_plan_count=3,
        realized_return_pct=return_pct if status == PolicyReplayStatus.COMPLETED else None,
        objective_score=objective if status == PolicyReplayStatus.COMPLETED else None,
        win_count=2 if status == PolicyReplayStatus.COMPLETED else None,
        loss_count=1 if status == PolicyReplayStatus.COMPLETED else None,
        no_data_count=0,
        status=status,
        notes=[],
        created_at=datetime(2026, 1, 2),
    )
