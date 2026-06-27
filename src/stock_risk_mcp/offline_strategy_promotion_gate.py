from __future__ import annotations

from stock_risk_mcp.offline_strategy_models import (
    OfflineStrategyBacktestResult,
    OfflineStrategyCandidate,
    OfflineStrategyMetricSummary,
    OfflineStrategyPipelineInput,
    OfflineStrategyPromotionDecision,
    OfflineStrategyStatus,
)


def build_offline_strategy_promotion_decision(
    pipeline_input: OfflineStrategyPipelineInput,
    candidate: OfflineStrategyCandidate,
    backtest_result: OfflineStrategyBacktestResult,
    metric_summary: OfflineStrategyMetricSummary,
    *,
    diagnostics: dict[str, int | float | str | bool | None] | None = None,
) -> OfflineStrategyPromotionDecision:
    reasons: list[str] = []
    status = OfflineStrategyStatus.PROMOTED_OFFLINE_CANDIDATE
    gate = pipeline_input.promotion_gate_config

    def set_status(next_status: OfflineStrategyStatus) -> None:
        nonlocal status
        priority = {
            OfflineStrategyStatus.REJECTED: 5,
            OfflineStrategyStatus.BLOCKED: 5,
            OfflineStrategyStatus.WATCHLIST_ONLY_ROLLING_ONLY: 4,
            OfflineStrategyStatus.WATCHLIST_ONLY: 3,
            OfflineStrategyStatus.RESEARCH_ONLY: 2,
            OfflineStrategyStatus.PROMOTED_OFFLINE_CANDIDATE: 1,
        }
        if priority.get(next_status, 0) >= priority.get(status, 0):
            status = next_status

    if not candidate.promotion_eligible:
        set_status(OfflineStrategyStatus.RESEARCH_ONLY)
        reasons.append("SHORT_OR_REVERSAL_TEMPLATE_NOT_PROMOTION_ELIGIBLE")
    if metric_summary.trade_count < gate.min_trade_count:
        set_status(OfflineStrategyStatus.REJECTED)
        reasons.append("MIN_TRADE_COUNT_NOT_MET")
    if pipeline_input.primary_walk_forward_mode.value == "ROLLING_CHRONOLOGICAL_WALK_FORWARD":
        set_status(OfflineStrategyStatus.WATCHLIST_ONLY_ROLLING_ONLY)
        reasons.append("ROLLING_MODE_IS_SECONDARY_ONLY")
    if metric_summary.max_drawdown > gate.max_drawdown_cap:
        set_status(OfflineStrategyStatus.REJECTED)
        reasons.append("MAX_DRAWDOWN_CAP_EXCEEDED")
    if metric_summary.profit_factor < gate.min_profit_factor:
        set_status(OfflineStrategyStatus.REJECTED)
        reasons.append("PROFIT_FACTOR_TOO_LOW")
    if metric_summary.expectancy < gate.min_expectancy:
        set_status(OfflineStrategyStatus.REJECTED)
        reasons.append("EXPECTANCY_TOO_LOW")
    if metric_summary.cumulative_return <= 0 and status == OfflineStrategyStatus.PROMOTED_OFFLINE_CANDIDATE:
        set_status(OfflineStrategyStatus.WATCHLIST_ONLY)
        reasons.append("NON_POSITIVE_CUMULATIVE_RETURN")
    if not backtest_result.trades:
        set_status(OfflineStrategyStatus.RESEARCH_ONLY)
        reasons.append("NO_TRADES")
    return OfflineStrategyPromotionDecision(
        decision_id=f"{pipeline_input.dataset_id}-{candidate.candidate_id}-PROMOTION-DECISION",
        candidate_id=candidate.candidate_id,
        family=candidate.family,
        status=status,
        reasons=reasons or ["PROMOTION_GATE_PASSED"],
        diagnostics=diagnostics or {},
    )
