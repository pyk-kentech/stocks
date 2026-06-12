from __future__ import annotations

import statistics
from datetime import datetime
from enum import StrEnum
from uuid import uuid4

from stock_risk_mcp.models import BacktestOutcome, StrictModel
from stock_risk_mcp.paper_trading import BasketBacktestResult
from stock_risk_mcp.strategy_objective import (
    StrategyRecommendation,
    calculate_objective_from_summary,
)
from stock_risk_mcp.strategy_policy import StrategyPolicy


class StrategyEvaluationMode(StrEnum):
    COMMON_OUTCOME_EVALUATION = "COMMON_OUTCOME_EVALUATION"
    FEATURE_RESCORING = "FEATURE_RESCORING"
    FULL_POLICY_REPLAY = "FULL_POLICY_REPLAY"


class StrategyExperiment(StrictModel):
    experiment_id: str
    baseline_policy_id: str
    baseline_version: str
    candidate_policy_id: str
    candidate_version: str
    evaluation_mode: StrategyEvaluationMode
    horizon_days: int
    sample_count: int
    avg_return_pct: float | None
    median_return_pct: float | None
    win_rate: float | None
    loss_rate: float | None
    profit_factor: float | None
    avg_max_drawdown: float | None
    avg_realized_pnl: float | None
    objective_score: float
    recommendation: StrategyRecommendation
    notes: list[str]
    created_at: datetime


def create_common_outcome_experiment(
    baseline: StrategyPolicy,
    candidate: StrategyPolicy,
    results: list[BasketBacktestResult],
    horizon_days: int,
) -> StrategyExperiment:
    returns = [result.realized_return_pct for result in results]
    pnls = [result.realized_pnl for result in results]
    gains = sum(value for value in pnls if value > 0)
    losses = abs(sum(value for value in pnls if value < 0))
    drawdowns = [result.max_drawdown for result in results if result.max_drawdown is not None]
    sample_count = len(results)
    avg_return = statistics.fmean(returns) if returns else None
    median_return = statistics.median(returns) if returns else None
    win_rate = sum(result.outcome == BacktestOutcome.WIN for result in results) / sample_count if results else None
    loss_rate = sum(result.outcome == BacktestOutcome.LOSS for result in results) / sample_count if results else None
    objective = calculate_objective_from_summary(
        sample_count=sample_count,
        avg_return_pct=avg_return,
        median_return_pct=median_return,
        win_rate=win_rate,
        loss_rate=loss_rate,
        profit_factor=gains / losses if losses else None,
        avg_max_drawdown=statistics.fmean(drawdowns) if drawdowns else None,
        avg_realized_pnl=statistics.fmean(pnls) if pnls else None,
    )
    notes = [
        "evaluation_mode=COMMON_OUTCOME_EVALUATION",
        "Common outcome evaluation does not compare actual candidate policy performance.",
        "Candidate policy was not reapplied to historical features or basket construction.",
        *objective.notes,
    ]
    return StrategyExperiment(
        experiment_id=uuid4().hex,
        baseline_policy_id=baseline.policy_id,
        baseline_version=baseline.version,
        candidate_policy_id=candidate.policy_id,
        candidate_version=candidate.version,
        evaluation_mode=StrategyEvaluationMode.COMMON_OUTCOME_EVALUATION,
        horizon_days=horizon_days,
        sample_count=sample_count,
        avg_return_pct=avg_return,
        median_return_pct=median_return,
        win_rate=win_rate,
        loss_rate=loss_rate,
        profit_factor=gains / losses if losses else None,
        avg_max_drawdown=statistics.fmean(drawdowns) if drawdowns else None,
        avg_realized_pnl=statistics.fmean(pnls) if pnls else None,
        objective_score=objective.objective_score,
        recommendation=objective.recommendation,
        notes=notes,
        created_at=datetime.now(),
    )
