from __future__ import annotations

from enum import StrEnum

from stock_risk_mcp.models import StrictModel


class StrategyRecommendation(StrEnum):
    ACCEPT = "ACCEPT"
    REJECT = "REJECT"
    NEED_MORE_DATA = "NEED_MORE_DATA"


class ObjectiveResult(StrictModel):
    objective_score: float
    avg_return_pct: float | None
    win_rate: float | None
    loss_rate: float | None
    profit_factor: float | None
    avg_max_drawdown: float | None
    sample_count: int
    overfit_penalty: float
    notes: list[str]
    recommendation: StrategyRecommendation


def calculate_objective_from_summary(
    sample_count: int,
    avg_return_pct: float | None,
    median_return_pct: float | None,
    win_rate: float | None,
    loss_rate: float | None,
    profit_factor: float | None,
    avg_max_drawdown: float | None,
    avg_realized_pnl: float | None,
) -> ObjectiveResult:
    drawdown = abs(min(avg_max_drawdown or 0, 0))
    overfit_penalty = max(drawdown - 15, 0) * 2
    score = 40.0
    score += (avg_return_pct or 0) * 2
    score += (median_return_pct or 0) * 0.5
    score += (win_rate or 0) * 30
    score -= (loss_rate or 0) * 20
    score += min(profit_factor or 0, 5) * 5
    score += max(min((avg_realized_pnl or 0) / 100, 10), -10)
    score -= drawdown * 1.5
    score -= overfit_penalty
    objective_score = round(max(0, min(100, score)), 4)
    notes = []
    if sample_count < 30:
        recommendation = StrategyRecommendation.NEED_MORE_DATA
        notes.append("sample_count is below 30; policy promotion is not allowed")
    elif objective_score >= 70:
        recommendation = StrategyRecommendation.ACCEPT
        notes.append("sample_count is sufficient and objective_score meets acceptance threshold")
    elif objective_score >= 50:
        recommendation = StrategyRecommendation.NEED_MORE_DATA
        notes.append("objective_score is inconclusive")
    else:
        recommendation = StrategyRecommendation.REJECT
        notes.append("objective_score is below rejection threshold")
    if drawdown > 15:
        notes.append("average max drawdown is worse than -15%; strong penalty applied")
    return ObjectiveResult(
        objective_score=objective_score,
        avg_return_pct=avg_return_pct,
        win_rate=win_rate,
        loss_rate=loss_rate,
        profit_factor=profit_factor,
        avg_max_drawdown=avg_max_drawdown,
        sample_count=sample_count,
        overfit_penalty=overfit_penalty,
        notes=notes,
        recommendation=recommendation,
    )
