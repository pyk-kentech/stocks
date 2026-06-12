from __future__ import annotations

from stock_risk_mcp.policy_replay import replay_policy_on_replay_run
from stock_risk_mcp.policy_replay_result import PolicyReplayStatus


def run_policy_replay_batch(
    repository,
    price_provider,
    replay_run_ids: list[str],
    baseline_policy_id: str,
    baseline_policy_version: str,
    candidate_policy_id: str,
    candidate_policy_version: str,
    horizon_days: int,
    account_equity: float,
    cash_available: float,
):
    pairs = []
    for run_id in list(dict.fromkeys(replay_run_ids)):
        baseline = _find_or_run(
            repository, price_provider, run_id, baseline_policy_id, baseline_policy_version,
            horizon_days, account_equity, cash_available,
        )
        candidate = _find_or_run(
            repository, price_provider, run_id, candidate_policy_id, candidate_policy_version,
            horizon_days, account_equity, cash_available,
        )
        pairs.append((baseline, candidate))
    return pairs


def _find_or_run(repository, provider, run_id, policy_id, version, horizon, equity, cash):
    matches = [
        item for item in repository.list_policy_replay_results(run_id, 1_000_000)
        if item.policy_id == policy_id and item.policy_version == version and item.horizon_days == horizon
        and item.status in {PolicyReplayStatus.COMPLETED, PolicyReplayStatus.NO_DATA}
    ]
    if matches:
        return matches[0]
    try:
        return replay_policy_on_replay_run(
            repository, provider, run_id, policy_id, version, horizon, equity, cash
        ).result
    except Exception:
        failed = [
            item for item in repository.list_policy_replay_results(run_id, 1_000_000)
            if item.policy_id == policy_id and item.policy_version == version and item.horizon_days == horizon
        ]
        return failed[0] if failed else None
