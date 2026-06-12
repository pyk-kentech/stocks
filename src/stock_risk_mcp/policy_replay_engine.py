from __future__ import annotations

from datetime import datetime
from uuid import uuid4

from stock_risk_mcp.basket import BasketCandidate, BasketPlan, BasketPolicy, candidate_from_trade_plan
from stock_risk_mcp.basket_backtest import run_basket_backtest
from stock_risk_mcp.basket_builder import build_basket
from stock_risk_mcp.indicators import analyze_price_bars
from stock_risk_mcp.models import SourceType, StrictModel
from stock_risk_mcp.policy_replay_result import (
    PolicyReplayMode,
    PolicyReplayResult,
    PolicyReplayStatus,
    calculate_policy_replay_objective,
)
from stock_risk_mcp.setup import TradePlan, TradeSizingPolicy
from stock_risk_mcp.setup_grading import SetupGrader
from stock_risk_mcp.strategy_policy import apply_strategy_policy_to_basket_policy, validate_strategy_policy
from stock_risk_mcp.trade_plan import create_trade_plan


class PolicyReplayExecution(StrictModel):
    result: PolicyReplayResult
    trade_plans: list[TradePlan]
    basket: BasketPlan | None = None
    save_intermediate: bool
    saved_trade_plan_count: int
    saved_to_basket_plans: bool


def replay_policy_on_replay_run(
    repository,
    price_provider,
    source_replay_run_id: str,
    policy_id: str,
    policy_version: str,
    horizon_days: int,
    account_equity: float,
    cash_available: float,
    save_intermediate: bool = False,
    save_basket: bool = False,
) -> PolicyReplayExecution:
    source_run = repository.get_replay_run(source_replay_run_id)
    if source_run.as_of_date is None:
        raise ValueError("ReplayRun as_of_date is required for FULL_POLICY_REPLAY")
    validate_strategy_policy(repository.get_strategy_policy(policy_id, policy_version))
    try:
        return _execute_policy_replay(
            repository, price_provider, source_replay_run_id, policy_id, policy_version,
            horizon_days, account_equity, cash_available, save_intermediate, save_basket,
        )
    except Exception as error:
        repository.save_policy_replay_result(
            PolicyReplayResult(
                policy_replay_id=uuid4().hex,
                source_replay_run_id=source_replay_run_id,
                replay_mode=PolicyReplayMode.FULL_POLICY_REPLAY,
                policy_id=policy_id,
                policy_version=policy_version,
                as_of_date=source_run.as_of_date,
                horizon_days=horizon_days,
                candidate_count=0,
                trade_plan_count=0,
                status=PolicyReplayStatus.FAILED,
                notes=[f"Unexpected FULL_POLICY_REPLAY failure: {error}"],
                created_at=datetime.now(),
            )
        )
        raise


def _execute_policy_replay(
    repository,
    price_provider,
    source_replay_run_id: str,
    policy_id: str,
    policy_version: str,
    horizon_days: int,
    account_equity: float,
    cash_available: float,
    save_intermediate: bool = False,
    save_basket: bool = False,
) -> PolicyReplayExecution:
    source_run = repository.get_replay_run(source_replay_run_id)
    if source_run.as_of_date is None:
        raise ValueError("ReplayRun as_of_date is required for FULL_POLICY_REPLAY")
    policy = validate_strategy_policy(repository.get_strategy_policy(policy_id, policy_version))
    snapshots = repository.list_replay_candidate_snapshots(source_replay_run_id)
    candidates_by_ticker = {snapshot.ticker: snapshot for snapshot in snapshots}
    notes = [
        "FULL_POLICY_REPLAY used as_of_date cutoff for indicators.",
        "Forward data was used only for paper outcome.",
        f"source candidate universe count: {len(candidates_by_ticker)}",
    ]
    trade_plans: list[TradePlan] = []
    basket_candidates: list[BasketCandidate] = []
    sizing_policy = TradeSizingPolicy(account_equity=account_equity, cash_available=cash_available)
    for ticker, snapshot in candidates_by_ticker.items():
        history = price_provider.get_history_until(ticker, source_run.as_of_date)
        if not history:
            continue
        indicator_set, _ = analyze_price_bars(ticker, history, "full_policy_replay", SourceType.SYSTEM)
        setup = SetupGrader().grade(indicator_set, policy)
        trade_plan = create_trade_plan(setup, history, sizing_policy)
        trade_plans.append(trade_plan)
        candidate = candidate_from_trade_plan(trade_plan)
        metadata = snapshot.snapshot_json
        candidate = candidate.model_copy(
            update={"sector": metadata.get("sector"), "theme": metadata.get("theme")}
        )
        basket_candidates.append(candidate)

    saved_trade_plan_count = 0
    if save_intermediate:
        saved_trade_plan_count = len([repository.save_trade_plan(plan) for plan in trade_plans])
        notes.append(
            "save_intermediate=true: regenerated TradePlans were saved to trade_plans without policy_replay_id linkage"
        )
    if not trade_plans:
        return _save_no_data(
            repository, source_replay_run_id, policy_id, policy_version, source_run.as_of_date,
            horizon_days, notes, save_intermediate, saved_trade_plan_count, save_basket,
        )

    base_policy = BasketPolicy(
        account_equity=account_equity,
        cash_available=cash_available,
        max_candidates=max(len(basket_candidates), 1),
    )
    basket_policy = apply_strategy_policy_to_basket_policy(base_policy, policy)
    basket = build_basket(basket_candidates, basket_policy, policy)
    if save_basket:
        repository.save_basket_plan(basket)
    if not basket.allocations:
        return _save_no_data(
            repository, source_replay_run_id, policy_id, policy_version, source_run.as_of_date,
            horizon_days, notes, save_intermediate, saved_trade_plan_count, save_basket, trade_plans, basket,
        )

    forward = {
        allocation.ticker: price_provider.get_forward_history(
            allocation.ticker, source_run.as_of_date, horizon_days
        )
        for allocation in basket.allocations
    }
    outcome, _ = run_basket_backtest(basket, forward, source_run.as_of_date, horizon_days)
    status = PolicyReplayStatus.NO_DATA if outcome.no_data_count == len(basket.allocations) else PolicyReplayStatus.COMPLETED
    objective = calculate_policy_replay_objective(
        len(basket.allocations), outcome.realized_return_pct, outcome.realized_pnl,
        outcome.win_count, outcome.loss_count, outcome.no_data_count,
    )
    result = PolicyReplayResult(
        policy_replay_id=uuid4().hex,
        source_replay_run_id=source_replay_run_id,
        replay_mode=PolicyReplayMode.FULL_POLICY_REPLAY,
        policy_id=policy_id,
        policy_version=policy_version,
        as_of_date=source_run.as_of_date,
        horizon_days=horizon_days,
        candidate_count=len(basket.allocations),
        trade_plan_count=len(trade_plans),
        basket_id=basket.basket_id,
        total_notional_value=outcome.total_notional_value,
        total_allocated_loss=outcome.total_allocated_loss,
        realized_pnl=outcome.realized_pnl,
        realized_return_pct=outcome.realized_return_pct,
        win_count=outcome.win_count,
        loss_count=outcome.loss_count,
        no_data_count=outcome.no_data_count,
        outcome=outcome.outcome.value,
        objective_score=objective,
        status=status,
        notes=notes,
        created_at=datetime.now(),
    )
    repository.save_policy_replay_result(result)
    return PolicyReplayExecution(
        result=result, trade_plans=trade_plans, basket=basket, save_intermediate=save_intermediate,
        saved_trade_plan_count=saved_trade_plan_count, saved_to_basket_plans=save_basket,
    )


def _save_no_data(
    repository,
    source_replay_run_id,
    policy_id,
    policy_version,
    as_of_date,
    horizon_days,
    notes,
    save_intermediate,
    saved_trade_plan_count,
    save_basket,
    trade_plans=None,
    basket=None,
) -> PolicyReplayExecution:
    result = PolicyReplayResult(
        policy_replay_id=uuid4().hex,
        source_replay_run_id=source_replay_run_id,
        replay_mode=PolicyReplayMode.FULL_POLICY_REPLAY,
        policy_id=policy_id,
        policy_version=policy_version,
        as_of_date=as_of_date,
        horizon_days=horizon_days,
        candidate_count=len(basket.allocations) if basket else 0,
        trade_plan_count=len(trade_plans or []),
        basket_id=basket.basket_id if basket else None,
        status=PolicyReplayStatus.NO_DATA,
        notes=[*notes, "Insufficient data for a complete policy replay outcome."],
        created_at=datetime.now(),
    )
    repository.save_policy_replay_result(result)
    return PolicyReplayExecution(
        result=result, trade_plans=trade_plans or [], basket=basket, save_intermediate=save_intermediate,
        saved_trade_plan_count=saved_trade_plan_count, saved_to_basket_plans=save_basket,
    )
