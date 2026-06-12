from datetime import date, datetime

from stock_risk_mcp.basket import BasketAllocation, BasketMode, BasketPlan, BasketPolicy, BasketRiskSummary
from stock_risk_mcp.models import BacktestOutcome
from stock_risk_mcp.paper_trading import BasketBacktestResult
from stock_risk_mcp.replay_snapshot import (
    ReplayBasketSnapshot,
    ReplayCandidateSnapshot,
    ReplayOutcomeSnapshot,
    ReplayRun,
    ReplayRunStatus,
    ReplaySnapshotMode,
    ReplayTradePlanSnapshot,
    basket_snapshot_from_plan,
    outcome_snapshot_from_result,
)
from stock_risk_mcp.repository import RiskRepository
from stock_risk_mcp.setup import SetupGrade, TradeDecision


def test_replay_snapshot_converters_preserve_complete_payload() -> None:
    plan = _plan()
    result = _result(plan.basket_id)

    basket = basket_snapshot_from_plan("run-1", plan)
    outcome = outcome_snapshot_from_result("run-1", result)

    assert basket.basket_id == "basket-replay"
    assert basket.snapshot_json["policy"]["account_equity"] == 10_000
    assert outcome.snapshot_json["outcome"] == "WIN"


def test_repository_round_trips_replay_records(tmp_path) -> None:
    repository = RiskRepository(tmp_path / "risk.sqlite3")
    run = ReplayRun(
        run_id="run-1",
        status=ReplayRunStatus.COMPLETED,
        snapshot_mode=ReplaySnapshotMode.FIXED_RULES,
        source_type="RECENT_TRADE_PLANS",
        as_of_date=date(2026, 6, 13),
        notes=["Basket was stored only as replay snapshot."],
        created_at=datetime(2026, 6, 13),
    )
    candidate = ReplayCandidateSnapshot(
        run_id=run.run_id,
        ticker="SAFE",
        source="recent_trade_plan",
        snapshot_json={"ticker": "SAFE"},
    )
    trade = ReplayTradePlanSnapshot(
        run_id=run.run_id,
        ticker="SAFE",
        decision="PROPOSE",
        snapshot_json={"ticker": "SAFE", "decision": "PROPOSE"},
    )
    basket = basket_snapshot_from_plan(run.run_id, _plan())
    outcome = outcome_snapshot_from_result(run.run_id, _result("basket-replay"))

    repository.save_replay_run(run)
    repository.save_replay_candidate_snapshot(candidate)
    repository.save_replay_trade_plan_snapshot(trade)
    repository.save_replay_basket_snapshot(basket)
    repository.save_replay_outcome_snapshot(outcome)

    assert repository.get_replay_run("run-1") == run
    assert repository.list_replay_runs() == [run]
    assert repository.list_replay_candidate_snapshots("run-1") == [candidate]
    assert repository.list_replay_trade_plan_snapshots("run-1") == [trade]
    assert repository.get_replay_basket_snapshot("run-1") == basket
    assert repository.get_replay_outcome_snapshot("run-1") == outcome
    assert repository.count_rows("replay_runs") == 1
    assert repository.count_rows("replay_basket_snapshots") == 1


def _plan() -> BasketPlan:
    allocation = BasketAllocation(
        ticker="SAFE",
        setup_grade=SetupGrade.A,
        allocated_loss_amount=10,
        allocated_notional_value=100,
        position_size=10,
        entry_price=10,
        stop_price=9,
        target_price=12,
        risk_reward_ratio=2,
        allocation_reason="fixture",
    )
    return BasketPlan(
        basket_id="basket-replay",
        basket_name="fixture",
        mode=BasketMode.PAPER_TRADING,
        policy=BasketPolicy(account_equity=10_000, cash_available=5_000, min_candidates=1),
        candidates=[],
        allocations=[allocation],
        blocked=[],
        risk_summary=BasketRiskSummary(
            total_allocated_loss=10,
            max_allowed_loss=100,
            total_notional_value=100,
            max_allowed_notional=2500,
            candidate_count=1,
            sector_counts={},
            theme_counts={},
            blocked_reasons=[],
            warnings=[],
            risk_ok=True,
        ),
        decision=TradeDecision.PROPOSE,
        beginner_summary="fixture",
        created_at=datetime(2026, 6, 13),
    )


def _result(basket_id: str) -> BasketBacktestResult:
    return BasketBacktestResult(
        basket_id=basket_id,
        horizon_days=10,
        entry_date=date(2026, 6, 1),
        exit_date=date(2026, 6, 10),
        total_notional_value=100,
        total_allocated_loss=10,
        realized_pnl=20,
        realized_return_pct=20,
        max_drawdown=-5,
        max_gain=20,
        win_count=1,
        loss_count=0,
        flat_count=0,
        no_data_count=0,
        closed_trade_count=1,
        outcome=BacktestOutcome.WIN,
        created_at=datetime(2026, 6, 10),
    )
