from __future__ import annotations

from datetime import date, datetime
from enum import StrEnum

from pydantic import Field

from stock_risk_mcp.models import StrictModel
from stock_risk_mcp.strategy_objective import StrategyRecommendation, calculate_objective_from_summary


class PolicyReplayMode(StrEnum):
    FULL_POLICY_REPLAY = "FULL_POLICY_REPLAY"


class PolicyReplayStatus(StrEnum):
    CREATED = "CREATED"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    NO_DATA = "NO_DATA"


class PolicyReplayResult(StrictModel):
    policy_replay_id: str
    source_replay_run_id: str
    replay_mode: PolicyReplayMode
    policy_id: str
    policy_version: str
    as_of_date: date
    horizon_days: int = Field(..., ge=1)
    candidate_count: int = Field(..., ge=0)
    trade_plan_count: int = Field(..., ge=0)
    basket_id: str | None = None
    total_notional_value: float | None = None
    total_allocated_loss: float | None = None
    realized_pnl: float | None = None
    realized_return_pct: float | None = None
    win_count: int | None = None
    loss_count: int | None = None
    no_data_count: int | None = None
    outcome: str | None = None
    objective_score: float | None = None
    status: PolicyReplayStatus
    notes: list[str] = Field(default_factory=list)
    created_at: datetime


class PolicyComparisonResult(StrictModel):
    comparison_id: str
    source_replay_run_id: str
    baseline_policy_id: str
    baseline_policy_version: str
    candidate_policy_id: str
    candidate_policy_version: str
    baseline_replay_id: str | None = None
    candidate_replay_id: str | None = None
    baseline_return_pct: float | None = None
    candidate_return_pct: float | None = None
    return_delta_pct: float | None = None
    baseline_objective_score: float | None = None
    candidate_objective_score: float | None = None
    objective_delta: float | None = None
    recommendation: StrategyRecommendation
    notes: list[str] = Field(default_factory=list)
    created_at: datetime


def calculate_policy_replay_objective(
    candidate_count: int,
    realized_return_pct: float,
    realized_pnl: float,
    win_count: int,
    loss_count: int,
    no_data_count: int,
) -> float:
    total = win_count + loss_count + no_data_count
    objective = calculate_objective_from_summary(
        sample_count=max(candidate_count, total),
        avg_return_pct=realized_return_pct,
        median_return_pct=realized_return_pct,
        win_rate=win_count / total if total else None,
        loss_rate=loss_count / total if total else None,
        profit_factor=None,
        avg_max_drawdown=None,
        avg_realized_pnl=realized_pnl,
    ).objective_score
    return round(max(0, objective - no_data_count * 5 - max(3 - candidate_count, 0) * 10), 4)
