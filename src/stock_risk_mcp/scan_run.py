from __future__ import annotations

from datetime import date, datetime
from uuid import uuid4

from stock_risk_mcp.basket import BasketPolicy, candidate_from_trade_plan
from stock_risk_mcp.basket_builder import build_basket
from stock_risk_mcp.candidate_universe import CandidateDecision
from stock_risk_mcp.replay_snapshot import ReplayCandidateSnapshot, ReplayRun, ReplayRunStatus, ReplaySnapshotMode
from stock_risk_mcp.setup import TradePlan
from stock_risk_mcp.strategy_policy import StrategyPolicy


def create_basket_from_scan_run(
    repository,
    scan_run_id: str,
    account_equity: float,
    cash_available: float,
    *,
    include_watch: bool = False,
    save_basket: bool = False,
    basket_policy: BasketPolicy | None = None,
    strategy_policy: StrategyPolicy | None = None,
):
    candidates = [
        candidate_from_trade_plan(TradePlan.model_validate(result.metadata["trade_plan"]))
        for result in _selected_results(repository, scan_run_id, include_watch)
        if "trade_plan" in result.metadata
    ]
    policy = basket_policy or BasketPolicy(account_equity=account_equity, cash_available=cash_available)
    basket = build_basket(candidates, policy, strategy_policy)
    if save_basket:
        repository.save_basket_plan(basket)
    return basket, save_basket


def create_replay_snapshot_from_scan_run(
    repository,
    scan_run_id: str,
    as_of_date: date,
    *,
    include_watch: bool = False,
) -> ReplayRun:
    scan_run = repository.get_scan_run(scan_run_id)
    replay = ReplayRun(
        run_id=uuid4().hex,
        status=ReplayRunStatus.COMPLETED,
        snapshot_mode=ReplaySnapshotMode.POLICY_WEIGHTED if scan_run.policy_id else ReplaySnapshotMode.FIXED_RULES,
        source_type="SCAN_RUN",
        as_of_date=as_of_date,
        policy_id=scan_run.policy_id,
        policy_version=scan_run.policy_version,
        notes=[
            f"Created from candidate scan run {scan_run_id}.",
            "Candidate snapshots preserve scan metadata; no basket was saved.",
        ],
        created_at=datetime.now(),
    )
    repository.save_replay_run(replay)
    for result in _selected_results(repository, scan_run_id, include_watch):
        payload = result.model_dump(mode="json")
        payload["scan_score"] = result.score
        payload["scan_decision"] = result.decision.value
        repository.save_replay_candidate_snapshot(
            ReplayCandidateSnapshot(run_id=replay.run_id, ticker=result.ticker, source="CANDIDATE_SCAN", snapshot_json=payload)
        )
    return replay


def _selected_results(repository, scan_run_id: str, include_watch: bool):
    allowed = {CandidateDecision.INCLUDE}
    if include_watch:
        allowed.add(CandidateDecision.WATCH)
    return [result for result in repository.list_candidate_scan_results(scan_run_id) if result.decision in allowed]
