from __future__ import annotations

from datetime import date, datetime
from uuid import uuid4

from stock_risk_mcp.basket import BasketPlan, BasketPolicy, candidate_from_trade_plan
from stock_risk_mcp.basket_backtest import run_basket_backtest
from stock_risk_mcp.basket_builder import build_basket
from stock_risk_mcp.models import StrictModel
from stock_risk_mcp.paper_trading import BasketBacktestResult
from stock_risk_mcp.replay_snapshot import (
    ReplayCandidateSnapshot,
    ReplayRun,
    ReplayRunStatus,
    ReplaySnapshotMode,
    ReplayTradePlanSnapshot,
    basket_snapshot_from_plan,
    outcome_snapshot_from_result,
)
from stock_risk_mcp.strategy_policy import StrategyPolicy, apply_strategy_policy_to_basket_policy


class ReplayRunResult(StrictModel):
    run: ReplayRun
    basket: BasketPlan
    outcome: BasketBacktestResult | None = None
    saved_to_basket_plans: bool


class ReplayRunService:
    def __init__(self, repository) -> None:
        self.repository = repository

    def snapshot_from_basket(self, basket_id: str, as_of_date: date | None = None) -> ReplayRunResult:
        plan = self.repository.get_basket_plan(basket_id)
        outcome = self.repository.get_basket_backtest_result(basket_id)
        run = self._new_run(
            source_type="EXISTING_BASKET",
            source_basket_id=basket_id,
            as_of_date=as_of_date,
            plan=plan,
            notes=["Snapshot created from existing basket.", "saved_to_basket_plans: true", *_boundary_notes()],
        )
        self._save_plan_snapshots(run.run_id, plan)
        if outcome is not None:
            self.repository.save_replay_outcome_snapshot(outcome_snapshot_from_result(run.run_id, outcome))
        return ReplayRunResult(run=run, basket=plan, outcome=outcome, saved_to_basket_plans=True)

    def snapshot_from_recent_trade_plans(
        self,
        account_equity: float,
        cash_available: float,
        max_candidates: int = 10,
        horizon_days: int = 10,
        as_of_date: date | None = None,
        save_basket: bool = False,
        strategy_policy: StrategyPolicy | None = None,
    ) -> ReplayRunResult:
        plans = self.repository.list_trade_plans(limit=max_candidates)
        policy = BasketPolicy(
            account_equity=account_equity,
            cash_available=cash_available,
            max_candidates=max_candidates,
        )
        if strategy_policy is not None:
            policy = apply_strategy_policy_to_basket_policy(policy, strategy_policy)
        basket = build_basket([candidate_from_trade_plan(plan) for plan in plans], policy, strategy_policy)
        if save_basket:
            self.repository.save_basket_plan(basket)
        storage_note = (
            "Basket was also saved to basket_plans."
            if save_basket
            else "Basket was stored only as replay snapshot."
        )
        run = self._new_run(
            source_type="RECENT_TRADE_PLANS",
            source_basket_id=None,
            as_of_date=as_of_date,
            plan=basket,
            notes=[storage_note, f"saved_to_basket_plans: {str(save_basket).lower()}", *_boundary_notes()],
        )
        for plan in plans:
            candidate = candidate_from_trade_plan(plan)
            self.repository.save_replay_candidate_snapshot(
                ReplayCandidateSnapshot(
                    run_id=run.run_id,
                    ticker=plan.ticker,
                    source="recent_trade_plan",
                    snapshot_json=candidate.model_dump(mode="json"),
                )
            )
            self.repository.save_replay_trade_plan_snapshot(
                ReplayTradePlanSnapshot(
                    run_id=run.run_id,
                    ticker=plan.ticker,
                    decision=plan.decision.value,
                    snapshot_json=plan.model_dump(mode="json"),
                )
            )
        self.repository.save_replay_basket_snapshot(basket_snapshot_from_plan(run.run_id, basket))
        outcome = self._optional_outcome(run.run_id, basket, horizon_days)
        return ReplayRunResult(run=run, basket=basket, outcome=outcome, saved_to_basket_plans=save_basket)

    def _new_run(
        self,
        source_type: str,
        source_basket_id: str | None,
        as_of_date: date | None,
        plan: BasketPlan,
        notes: list[str],
    ) -> ReplayRun:
        run = ReplayRun(
            run_id=uuid4().hex,
            status=ReplayRunStatus.COMPLETED,
            snapshot_mode=ReplaySnapshotMode(plan.basket_scoring_mode),
            source_type=source_type,
            source_basket_id=source_basket_id,
            as_of_date=as_of_date,
            policy_id=plan.policy_id,
            policy_version=plan.policy_version,
            notes=notes,
            created_at=datetime.now(),
        )
        self.repository.save_replay_run(run)
        return run

    def _save_plan_snapshots(self, run_id: str, plan: BasketPlan) -> None:
        for allocation in plan.allocations:
            payload = allocation.model_dump(mode="json")
            self.repository.save_replay_candidate_snapshot(
                ReplayCandidateSnapshot(
                    run_id=run_id, ticker=allocation.ticker, source="basket_allocation", snapshot_json=payload
                )
            )
            self.repository.save_replay_trade_plan_snapshot(
                ReplayTradePlanSnapshot(
                    run_id=run_id, ticker=allocation.ticker, decision="PROPOSE", snapshot_json=payload
                )
            )
        self.repository.save_replay_basket_snapshot(basket_snapshot_from_plan(run_id, plan))

    def _optional_outcome(
        self,
        run_id: str,
        basket: BasketPlan,
        horizon_days: int,
    ) -> BasketBacktestResult | None:
        if not basket.allocations:
            return None
        prices = {item.ticker: self.repository.get_all_price_history(item.ticker) for item in basket.allocations}
        if any(not bars for bars in prices.values()):
            return None
        result, _ = run_basket_backtest(basket, prices, basket.created_at.date(), horizon_days)
        self.repository.save_replay_outcome_snapshot(outcome_snapshot_from_result(run_id, result))
        return result


def _boundary_notes() -> list[str]:
    return [
        "This is not FULL_POLICY_REPLAY.",
        "as_of_date is metadata; historical cutoff regeneration was not performed.",
    ]
