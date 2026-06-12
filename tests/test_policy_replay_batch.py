from stock_risk_mcp.policy_replay_batch import run_policy_replay_batch
from stock_risk_mcp.repository import RiskRepository
from tests.test_policy_evaluation_suite import _replay


def test_batch_reuses_matching_replay_results(tmp_path) -> None:
    repository = RiskRepository(tmp_path / "risk.sqlite3")
    baseline = _replay("r1", "base")
    candidate = _replay("r1", "candidate")
    repository.save_policy_replay_result(baseline)
    repository.save_policy_replay_result(candidate)

    pairs = run_policy_replay_batch(
        repository, None, ["r1"], "base", "v1", "candidate", "v1", 10, 10_000, 5_000
    )

    assert pairs == [(baseline, candidate)]
