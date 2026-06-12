from __future__ import annotations

import statistics
from datetime import datetime
from enum import StrEnum
from uuid import uuid4

from pydantic import Field

from stock_risk_mcp.models import StrictModel
from stock_risk_mcp.policy_replay_result import PolicyReplayResult, PolicyReplayStatus


class PolicyEvaluationDecision(StrEnum):
    ACCEPT = "ACCEPT"
    REJECT = "REJECT"
    NEED_MORE_DATA = "NEED_MORE_DATA"


class PolicyEvaluationSuiteResult(StrictModel):
    suite_id: str
    baseline_policy_id: str
    baseline_policy_version: str
    candidate_policy_id: str
    candidate_policy_version: str
    replay_run_count: int
    completed_pair_count: int
    no_data_replay_count: int
    incomplete_pair_count: int
    baseline_avg_return_pct: float | None = None
    candidate_avg_return_pct: float | None = None
    return_delta_pct: float | None = None
    baseline_avg_objective_score: float | None = None
    candidate_avg_objective_score: float | None = None
    objective_delta: float | None = None
    baseline_win_rate: float | None = None
    candidate_win_rate: float | None = None
    win_rate_delta: float | None = None
    baseline_loss_rate: float | None = None
    candidate_loss_rate: float | None = None
    no_data_rate: float
    recommendation: PolicyEvaluationDecision
    notes: list[str] = Field(default_factory=list)
    created_at: datetime


def evaluate_policy_suite(
    pairs: list[tuple[PolicyReplayResult | None, PolicyReplayResult | None]],
    min_replay_runs: int = 5,
    min_completed_replays: int = 3,
) -> PolicyEvaluationSuiteResult:
    baseline_first = next((baseline for baseline, _ in pairs if baseline is not None), None)
    candidate_first = next((candidate for _, candidate in pairs if candidate is not None), None)
    if baseline_first is None or candidate_first is None:
        raise ValueError("At least one policy replay result is required")
    completed = [
        (baseline, candidate)
        for baseline, candidate in pairs
        if baseline is not None and candidate is not None
        and baseline.status == PolicyReplayStatus.COMPLETED
        and candidate.status == PolicyReplayStatus.COMPLETED
    ]
    no_data_count = sum(
        baseline is not None and candidate is not None
        and (baseline.status == PolicyReplayStatus.NO_DATA or candidate.status == PolicyReplayStatus.NO_DATA)
        for baseline, candidate in pairs
    )
    incomplete_count = len(pairs) - len(completed) - no_data_count
    unavailable = no_data_count + incomplete_count
    no_data_rate = unavailable / len(pairs) if pairs else 0.0
    baseline_returns = [item.realized_return_pct for item, _ in completed if item.realized_return_pct is not None]
    candidate_returns = [item.realized_return_pct for _, item in completed if item.realized_return_pct is not None]
    baseline_objectives = [item.objective_score for item, _ in completed if item.objective_score is not None]
    candidate_objectives = [item.objective_score for _, item in completed if item.objective_score is not None]
    baseline_wins = [_win_rate(item) for item, _ in completed]
    candidate_wins = [_win_rate(item) for _, item in completed]
    baseline_losses = [_loss_rate(item) for item, _ in completed]
    candidate_losses = [_loss_rate(item) for _, item in completed]
    b_return, c_return = _mean(baseline_returns), _mean(candidate_returns)
    b_objective, c_objective = _mean(baseline_objectives), _mean(candidate_objectives)
    b_win, c_win = _mean(baseline_wins), _mean(candidate_wins)
    b_loss, c_loss = _mean(baseline_losses), _mean(candidate_losses)
    return_delta, objective_delta, win_delta = _delta(c_return, b_return), _delta(c_objective, b_objective), _delta(c_win, b_win)
    notes = [
        f"completed pair count: {len(completed)}",
        f"excluded NO_DATA pair count: {no_data_count}",
        f"excluded incomplete pair count: {incomplete_count}",
    ]
    if len(pairs) < min_replay_runs:
        recommendation = PolicyEvaluationDecision.NEED_MORE_DATA
        notes.append("replay_run_count below minimum")
    elif len(completed) < min_completed_replays:
        recommendation = PolicyEvaluationDecision.NEED_MORE_DATA
        notes.append("completed_pair_count below minimum")
    elif no_data_rate > 0.4:
        recommendation = PolicyEvaluationDecision.NEED_MORE_DATA
        notes.append("no_data_rate above 0.4")
    elif any(min(b.candidate_count, c.candidate_count) < 3 for b, c in completed):
        recommendation = PolicyEvaluationDecision.NEED_MORE_DATA
        notes.append("candidate_count below minimum basket size")
    elif objective_delta is not None and return_delta is not None and win_delta is not None and objective_delta >= 5 and return_delta > 0 and win_delta >= 0:
        recommendation = PolicyEvaluationDecision.ACCEPT
    elif (objective_delta is not None and objective_delta <= -5) or (return_delta is not None and return_delta < -2):
        recommendation = PolicyEvaluationDecision.REJECT
    else:
        recommendation = PolicyEvaluationDecision.NEED_MORE_DATA
    return PolicyEvaluationSuiteResult(
        suite_id=uuid4().hex,
        baseline_policy_id=completed[0][0].policy_id if completed else baseline_first.policy_id,
        baseline_policy_version=completed[0][0].policy_version if completed else baseline_first.policy_version,
        candidate_policy_id=completed[0][1].policy_id if completed else candidate_first.policy_id,
        candidate_policy_version=completed[0][1].policy_version if completed else candidate_first.policy_version,
        replay_run_count=len(pairs), completed_pair_count=len(completed), no_data_replay_count=no_data_count,
        incomplete_pair_count=incomplete_count, baseline_avg_return_pct=b_return, candidate_avg_return_pct=c_return,
        return_delta_pct=return_delta, baseline_avg_objective_score=b_objective,
        candidate_avg_objective_score=c_objective, objective_delta=objective_delta, baseline_win_rate=b_win,
        candidate_win_rate=c_win, win_rate_delta=win_delta, baseline_loss_rate=b_loss, candidate_loss_rate=c_loss,
        no_data_rate=round(no_data_rate, 4), recommendation=recommendation, notes=notes, created_at=datetime.now(),
    )


def _win_rate(result: PolicyReplayResult) -> float:
    total = (result.win_count or 0) + (result.loss_count or 0) + (result.no_data_count or 0)
    return (result.win_count or 0) / total if total else 0.0


def _loss_rate(result: PolicyReplayResult) -> float:
    total = (result.win_count or 0) + (result.loss_count or 0) + (result.no_data_count or 0)
    return (result.loss_count or 0) / total if total else 0.0


def _mean(values) -> float | None:
    return round(statistics.fmean(values), 4) if values else None


def _delta(candidate: float | None, baseline: float | None) -> float | None:
    return round(candidate - baseline, 4) if candidate is not None and baseline is not None else None
