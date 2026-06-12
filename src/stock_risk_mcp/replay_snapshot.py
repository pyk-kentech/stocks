from __future__ import annotations

from datetime import date, datetime
from enum import StrEnum
from typing import Any

from pydantic import Field

from stock_risk_mcp.basket import BasketPlan
from stock_risk_mcp.models import StrictModel
from stock_risk_mcp.paper_trading import BasketBacktestResult


class ReplayRunStatus(StrEnum):
    CREATED = "CREATED"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class ReplaySnapshotMode(StrEnum):
    FIXED_RULES = "FIXED_RULES"
    POLICY_WEIGHTED = "POLICY_WEIGHTED"


class ReplayRun(StrictModel):
    run_id: str
    status: ReplayRunStatus
    snapshot_mode: ReplaySnapshotMode
    source_type: str
    source_basket_id: str | None = None
    as_of_date: date | None = None
    policy_id: str | None = None
    policy_version: str | None = None
    notes: list[str] = Field(default_factory=list)
    created_at: datetime


class ReplayCandidateSnapshot(StrictModel):
    run_id: str
    ticker: str
    source: str
    snapshot_json: dict[str, Any]


class ReplayTradePlanSnapshot(StrictModel):
    run_id: str
    ticker: str
    trade_plan_id: int | None = None
    decision: str
    snapshot_json: dict[str, Any]


class ReplayBasketSnapshot(StrictModel):
    run_id: str
    basket_id: str
    decision: str
    policy_id: str | None = None
    policy_version: str | None = None
    scoring_mode: str
    snapshot_json: dict[str, Any]


class ReplayOutcomeSnapshot(StrictModel):
    run_id: str
    basket_id: str
    outcome: str
    realized_return_pct: float
    snapshot_json: dict[str, Any]


def basket_snapshot_from_plan(run_id: str, plan: BasketPlan) -> ReplayBasketSnapshot:
    return ReplayBasketSnapshot(
        run_id=run_id,
        basket_id=plan.basket_id,
        decision=plan.decision.value,
        policy_id=plan.policy_id,
        policy_version=plan.policy_version,
        scoring_mode=plan.basket_scoring_mode,
        snapshot_json=plan.model_dump(mode="json"),
    )


def outcome_snapshot_from_result(run_id: str, result: BasketBacktestResult) -> ReplayOutcomeSnapshot:
    return ReplayOutcomeSnapshot(
        run_id=run_id,
        basket_id=result.basket_id,
        outcome=result.outcome.value,
        realized_return_pct=result.realized_return_pct,
        snapshot_json=result.model_dump(mode="json"),
    )
