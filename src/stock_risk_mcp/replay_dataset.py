from __future__ import annotations

from stock_risk_mcp.models import StrictModel
from stock_risk_mcp.replay_snapshot import (
    ReplayBasketSnapshot,
    ReplayCandidateSnapshot,
    ReplayOutcomeSnapshot,
    ReplayRun,
    ReplayTradePlanSnapshot,
)


class ReplayDataset(StrictModel):
    run: ReplayRun
    candidates: list[ReplayCandidateSnapshot]
    trade_plans: list[ReplayTradePlanSnapshot]
    basket: ReplayBasketSnapshot | None
    outcome: ReplayOutcomeSnapshot | None


def load_replay_dataset(repository, run_id: str) -> ReplayDataset:
    return ReplayDataset(
        run=repository.get_replay_run(run_id),
        candidates=repository.list_replay_candidate_snapshots(run_id),
        trade_plans=repository.list_replay_trade_plan_snapshots(run_id),
        basket=repository.get_replay_basket_snapshot(run_id),
        outcome=repository.get_replay_outcome_snapshot(run_id),
    )
