from __future__ import annotations

from datetime import datetime
from uuid import uuid4

from stock_risk_mcp.policy_replay import MIN_POLICY_REPLAY_CANDIDATES, replay_policy_on_replay_run
from stock_risk_mcp.policy_replay_result import PolicyComparisonResult, PolicyReplayResult, PolicyReplayStatus
from stock_risk_mcp.strategy_objective import StrategyRecommendation


def create_policy_comparison(
    baseline: PolicyReplayResult,
    candidate: PolicyReplayResult,
) -> PolicyComparisonResult:
    return_delta = _delta(candidate.realized_return_pct, baseline.realized_return_pct)
    objective_delta = _delta(candidate.objective_score, baseline.objective_score)
    notes = [
        "FULL_POLICY_REPLAY used as_of_date cutoff for indicators.",
        "Forward data was used only for paper outcome.",
    ]
    if min(baseline.candidate_count, candidate.candidate_count) < minimum_policy_replay_candidates():
        recommendation = StrategyRecommendation.NEED_MORE_DATA
        notes.append("candidate_count below minimum basket size")
    elif objective_delta is not None and objective_delta >= 5:
        recommendation = StrategyRecommendation.ACCEPT
    elif objective_delta is not None and objective_delta <= -5:
        recommendation = StrategyRecommendation.REJECT
    else:
        recommendation = StrategyRecommendation.NEED_MORE_DATA
    return PolicyComparisonResult(
        comparison_id=uuid4().hex,
        source_replay_run_id=baseline.source_replay_run_id,
        baseline_policy_id=baseline.policy_id,
        baseline_policy_version=baseline.policy_version,
        candidate_policy_id=candidate.policy_id,
        candidate_policy_version=candidate.policy_version,
        baseline_replay_id=baseline.policy_replay_id,
        candidate_replay_id=candidate.policy_replay_id,
        baseline_return_pct=baseline.realized_return_pct,
        candidate_return_pct=candidate.realized_return_pct,
        return_delta_pct=return_delta,
        baseline_objective_score=baseline.objective_score,
        candidate_objective_score=candidate.objective_score,
        objective_delta=objective_delta,
        recommendation=recommendation,
        notes=notes,
        created_at=datetime.now(),
    )


def compare_policy_replays(
    repository,
    price_provider,
    source_replay_run_id: str,
    baseline_policy_id: str,
    baseline_policy_version: str,
    candidate_policy_id: str,
    candidate_policy_version: str,
    horizon_days: int,
    account_equity: float,
    cash_available: float,
) -> PolicyComparisonResult:
    baseline = _find_or_run(
        repository, price_provider, source_replay_run_id, baseline_policy_id, baseline_policy_version,
        horizon_days, account_equity, cash_available,
    )
    candidate = _find_or_run(
        repository, price_provider, source_replay_run_id, candidate_policy_id, candidate_policy_version,
        horizon_days, account_equity, cash_available,
    )
    comparison = create_policy_comparison(baseline, candidate)
    repository.save_policy_comparison_result(comparison)
    return comparison


def minimum_policy_replay_candidates() -> int:
    return MIN_POLICY_REPLAY_CANDIDATES


def _find_or_run(repository, provider, run_id, policy_id, version, horizon_days, equity, cash):
    matches = [
        result
        for result in repository.list_policy_replay_results(run_id, limit=1_000_000)
        if result.policy_id == policy_id
        and result.policy_version == version
        and result.horizon_days == horizon_days
        and result.status in {PolicyReplayStatus.COMPLETED, PolicyReplayStatus.NO_DATA}
    ]
    if matches:
        return matches[0]
    return replay_policy_on_replay_run(
        repository, provider, run_id, policy_id, version, horizon_days, equity, cash
    ).result


def _delta(candidate: float | None, baseline: float | None) -> float | None:
    if candidate is None or baseline is None:
        return None
    return round(candidate - baseline, 4)
