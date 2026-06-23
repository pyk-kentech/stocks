from __future__ import annotations

from stock_risk_mcp.risk_adjusted_paper_eval_guard import validate_risk_adjusted_paper_eval_metadata_safety
from stock_risk_mcp.risk_adjusted_paper_eval_models import (
    PaperCostSlippageReport,
    PaperDrawdownExposureReport,
    PaperEvaluationSummaryReport,
    PaperPassReadinessReport,
    PaperRegimeFearBucketReport,
    PaperRiskAdjustedPerformanceReport,
    RiskAdjustedPaperEvalDecision,
    RiskAdjustedPaperEvalGapCategory,
    RiskAdjustedPaperEvalGapEntry,
    RiskAdjustedPaperEvalGapReport,
    RiskAdjustedPaperEvalInput,
    RiskAdjustedPaperEvalSafetyReport,
    VirtualOrder,
    VirtualPortfolioReport,
    VirtualPosition,
    VirtualTrade,
    VirtualTradeLedgerReport,
)


_BLOCKED_CAPABILITIES = [
    "LIVE_TRADING_BLOCKED",
    "REAL_ORDER_BLOCKED",
    "ACCOUNT_MUTATION_BLOCKED",
    "BROKER_API_BLOCKED",
    "KIWOOM_API_BLOCKED",
    "WEBSOCKET_BLOCKED",
    "NETWORK_BLOCKED",
    "AUTONOMOUS_TRADING_BLOCKED",
]


def _gap(input_id: str, suffix: str, category, severity: str, message: str) -> RiskAdjustedPaperEvalGapEntry:
    return RiskAdjustedPaperEvalGapEntry(
        gap_id=f"{input_id}-{suffix}",
        gap_category=category,
        severity=severity,
        message=message,
    )


def build_risk_adjusted_paper_evaluation(
    evaluation_input: RiskAdjustedPaperEvalInput,
) -> RiskAdjustedPaperEvalInput:
    for audit in evaluation_input.audit_records:
        validate_risk_adjusted_paper_eval_metadata_safety(
            {
                "source_path": audit.source_path,
                "operator_context": audit.operator_context,
            },
            context="risk-adjusted paper evaluation",
        )

    gap_entries: list[RiskAdjustedPaperEvalGapEntry] = []
    if not evaluation_input.allocation_policy_candidate_ref:
        gap_entries.append(_gap(evaluation_input.evaluation_id, "MISSING-V76-POLICY", RiskAdjustedPaperEvalGapCategory.MISSING_V76_POLICY_DEPENDENCY, "WARNING", "v7.6 policy candidate ref is missing"))
    if not evaluation_input.point_in_time_dataset_ref:
        gap_entries.append(_gap(evaluation_input.evaluation_id, "MISSING-PIT", RiskAdjustedPaperEvalGapCategory.MISSING_POINT_IN_TIME_DATASET, "WARNING", "point-in-time dataset evidence is missing"))
    if not evaluation_input.walk_forward_split_ref:
        gap_entries.append(_gap(evaluation_input.evaluation_id, "MISSING-WALK-FORWARD", RiskAdjustedPaperEvalGapCategory.MISSING_WALK_FORWARD_SPLIT, "WARNING", "walk-forward split evidence is missing"))
    if not evaluation_input.market_data_fixture_ref or not evaluation_input.available_at_safe_market_data:
        gap_entries.append(_gap(evaluation_input.evaluation_id, "MISSING-MARKET-DATA", RiskAdjustedPaperEvalGapCategory.MISSING_MARKET_DATA_FIXTURE, "WARNING", "market data fixture is missing or not available_at safe"))
    if not evaluation_input.cnn_fear_greed_feature_ref:
        gap_entries.append(_gap(evaluation_input.evaluation_id, "MISSING-CNN", RiskAdjustedPaperEvalGapCategory.MISSING_CNN_FEATURE, "REPORT_ONLY", "cnn fear and greed feature is missing"))
    if not evaluation_input.fee_tax_slippage_assumptions_ref:
        gap_entries.append(_gap(evaluation_input.evaluation_id, "MISSING-COSTS", RiskAdjustedPaperEvalGapCategory.MISSING_COST_SLIPPAGE_ASSUMPTIONS, "WARNING", "cost/slippage assumptions are missing"))
    if evaluation_input.future_price_leakage_detected:
        gap_entries.append(_gap(evaluation_input.evaluation_id, "FUTURE-PRICE-LEAKAGE", RiskAdjustedPaperEvalGapCategory.FUTURE_PRICE_LEAKAGE_DETECTED, "BLOCKING", "future price leakage detected"))
    if evaluation_input.future_regime_fear_leakage_detected:
        gap_entries.append(_gap(evaluation_input.evaluation_id, "FUTURE-REGIME-FEAR-LEAKAGE", RiskAdjustedPaperEvalGapCategory.FUTURE_REGIME_FEAR_LEAKAGE_DETECTED, "BLOCKING", "future regime/fear leakage detected"))

    entry_notional = evaluation_input.simulated_fill_price * evaluation_input.quantity
    gross_exposure = entry_notional / evaluation_input.initial_cash
    end_value = evaluation_input.end_price * evaluation_input.quantity
    gross_return_value = end_value - entry_notional
    total_fees = entry_notional * (evaluation_input.fee_bps / 10000)
    total_taxes = entry_notional * (evaluation_input.tax_bps / 10000)
    total_slippage = entry_notional * (evaluation_input.slippage_bps / 10000)
    realized_pnl = gross_return_value - total_fees - total_taxes - total_slippage
    total_return = realized_pnl / evaluation_input.initial_cash
    benchmark_relative_return = total_return - evaluation_input.benchmark_return
    max_drawdown = max(0.0, -min(total_return, 0.0))
    daily_loss_estimate = max(0.0, -total_return)

    if max_drawdown > evaluation_input.max_drawdown_limit:
        gap_entries.append(_gap(evaluation_input.evaluation_id, "MAX-DRAWDOWN-BREACH", RiskAdjustedPaperEvalGapCategory.MAX_DRAWDOWN_BREACH, "BLOCKING", "max drawdown limit breached"))
    if daily_loss_estimate > evaluation_input.daily_loss_limit:
        gap_entries.append(_gap(evaluation_input.evaluation_id, "DAILY-LOSS-BREACH", RiskAdjustedPaperEvalGapCategory.DAILY_LOSS_BREACH, "BLOCKING", "daily loss limit breached"))
    if evaluation_input.turnover > evaluation_input.turnover_limit:
        gap_entries.append(_gap(evaluation_input.evaluation_id, "EXCESSIVE-TURNOVER", RiskAdjustedPaperEvalGapCategory.EXCESSIVE_TURNOVER, "WARNING", "turnover exceeds configured limit"))
    if evaluation_input.inverse_hedge_exposure > evaluation_input.max_inverse_hedge_exposure:
        gap_entries.append(_gap(evaluation_input.evaluation_id, "EXCESSIVE-INVERSE-HEDGE", RiskAdjustedPaperEvalGapCategory.EXCESSIVE_INVERSE_HEDGE_EXPOSURE, "BLOCKING", "inverse or hedge exposure exceeds configured limit"))

    policy_decision = evaluation_input.policy_promotion_decision
    if policy_decision is None:
        decision = RiskAdjustedPaperEvalDecision.GAP
        reason = "missing policy promotion decision"
    elif policy_decision in {"BLOCKED", "REJECTED"}:
        gap_entries.append(_gap(evaluation_input.evaluation_id, "INVALID-POLICY-DECISION", RiskAdjustedPaperEvalGapCategory.INVALID_POLICY_PROMOTION_DECISION, "BLOCKING", "policy promotion decision is blocked or rejected"))
        decision = RiskAdjustedPaperEvalDecision.BLOCKED
        reason = "policy dependency is blocked"
    elif policy_decision == "RESEARCH_ONLY":
        decision = RiskAdjustedPaperEvalDecision.RESEARCH_ONLY
        reason = "policy is research-only"
    elif any(entry.severity == "BLOCKING" for entry in gap_entries):
        decision = RiskAdjustedPaperEvalDecision.BLOCKED
        reason = "blocking safety or risk gaps detected"
    elif any(entry.gap_category in {
        RiskAdjustedPaperEvalGapCategory.MISSING_V76_POLICY_DEPENDENCY,
        RiskAdjustedPaperEvalGapCategory.MISSING_POINT_IN_TIME_DATASET,
        RiskAdjustedPaperEvalGapCategory.MISSING_WALK_FORWARD_SPLIT,
        RiskAdjustedPaperEvalGapCategory.MISSING_MARKET_DATA_FIXTURE,
    } for entry in gap_entries):
        decision = RiskAdjustedPaperEvalDecision.GAP
        reason = "required dependency evidence is missing"
    elif not evaluation_input.fee_tax_slippage_assumptions_ref:
        decision = RiskAdjustedPaperEvalDecision.PAPER_EVALUATED
        reason = "paper evaluation completed without full cost assumptions"
    elif total_return > 0.02 and benchmark_relative_return > 0 and max_drawdown <= evaluation_input.max_drawdown_limit and evaluation_input.turnover <= evaluation_input.turnover_limit:
        decision = RiskAdjustedPaperEvalDecision.PAPER_PASS
        reason = "cost-adjusted paper evaluation meets pass thresholds"
    else:
        decision = RiskAdjustedPaperEvalDecision.PAPER_EVALUATED
        reason = "paper evaluation completed without pass-ready strength"

    virtual_order = VirtualOrder(
        virtual_order_id=f"{evaluation_input.evaluation_id}-ORDER-1",
        symbol=evaluation_input.symbol,
        side="SIMULATED_ALLOCATE",
        decision_timestamp=evaluation_input.decision_timestamp,
        simulated_fill_timestamp=evaluation_input.simulated_fill_timestamp,
        simulated_fill_price=evaluation_input.simulated_fill_price,
        quantity=evaluation_input.quantity,
        executable=False,
    )
    virtual_trade = VirtualTrade(
        virtual_trade_id=f"{evaluation_input.evaluation_id}-TRADE-1",
        symbol=evaluation_input.symbol,
        side="SIMULATED_ALLOCATE",
        fill_price=evaluation_input.simulated_fill_price,
        quantity=evaluation_input.quantity,
        fee_estimate=total_fees,
        tax_estimate=total_taxes,
        slippage_estimate=total_slippage,
        executable=False,
    )
    virtual_position = VirtualPosition(
        symbol=evaluation_input.symbol,
        quantity=evaluation_input.quantity,
        average_price=evaluation_input.simulated_fill_price,
        market_value=end_value,
    )
    base = {
        "report_id": f"{evaluation_input.evaluation_id}-REPORT",
        "cash": evaluation_input.initial_cash - entry_notional - total_fees - total_taxes - total_slippage,
        "virtual_positions": [virtual_position],
        "virtual_orders": [virtual_order],
        "virtual_trades": [virtual_trade],
        "equity_curve": [evaluation_input.initial_cash, evaluation_input.initial_cash + realized_pnl],
        "realized_pnl": realized_pnl,
        "unrealized_pnl": 0.0,
        "exposure": gross_exposure,
        "gross_exposure": gross_exposure,
        "net_exposure": gross_exposure,
        "turnover": evaluation_input.turnover,
        "max_drawdown": max_drawdown,
        "daily_loss_estimate": daily_loss_estimate,
    }
    summary_report = PaperEvaluationSummaryReport(
        **base,
        decision=decision,
        decision_reason=reason,
        total_return=total_return,
        benchmark_relative_return=benchmark_relative_return,
    )
    virtual_portfolio_report = VirtualPortfolioReport(**base)
    virtual_trade_ledger_report = VirtualTradeLedgerReport(**base)
    cost_slippage_report = PaperCostSlippageReport(
        **base,
        total_fees=total_fees,
        total_taxes=total_taxes,
        total_slippage=total_slippage,
        cost_adjusted_return=total_return,
        slippage_adjusted_return=(gross_return_value - total_slippage) / evaluation_input.initial_cash,
    )
    risk_adjusted_report = PaperRiskAdjustedPerformanceReport(
        **base,
        volatility=evaluation_input.volatility,
        sharpe_like_score=0.0 if evaluation_input.volatility == 0 else total_return / evaluation_input.volatility,
        sortino_like_score=0.0 if daily_loss_estimate == 0 else total_return / daily_loss_estimate,
        calmar_like_score=0.0 if max_drawdown == 0 else total_return / max_drawdown,
        hit_rate=1.0 if realized_pnl > 0 else 0.0,
        average_win=max(realized_pnl, 0.0),
        average_loss=min(realized_pnl, 0.0),
        tail_risk_estimate=max_drawdown + evaluation_input.inverse_hedge_exposure,
    )
    drawdown_exposure_report = PaperDrawdownExposureReport(
        **base,
        max_drawdown_limit_breached=max_drawdown > evaluation_input.max_drawdown_limit,
        daily_loss_limit_breached=daily_loss_estimate > evaluation_input.daily_loss_limit,
        max_gross_exposure_breached=gross_exposure > evaluation_input.max_gross_exposure,
        max_single_action_exposure_breached=gross_exposure > evaluation_input.max_single_action_exposure,
        max_inverse_hedge_exposure_breached=evaluation_input.inverse_hedge_exposure > evaluation_input.max_inverse_hedge_exposure,
        turnover_limit_breached=evaluation_input.turnover > evaluation_input.turnover_limit,
    )
    regime_fear_bucket_report = PaperRegimeFearBucketReport(
        **base,
        regime_bucket_performance={evaluation_input.regime_bucket_name: total_return},
        fear_bucket_performance={evaluation_input.fear_bucket_name or "MISSING": total_return} if evaluation_input.cnn_fear_greed_feature_ref else {},
        cnn_fear_greed_feature_used=bool(evaluation_input.cnn_fear_greed_feature_ref),
        missing_cnn_feature_gap_noted=not bool(evaluation_input.cnn_fear_greed_feature_ref),
    )
    pass_readiness_report = PaperPassReadinessReport(
        **base,
        decision=decision,
        policy_promotion_decision=policy_decision or "MISSING",
        costs_included_for_pass=bool(evaluation_input.fee_tax_slippage_assumptions_ref),
        point_in_time_evidence_present=bool(evaluation_input.point_in_time_dataset_ref),
        walk_forward_evidence_present=bool(evaluation_input.walk_forward_split_ref),
        no_future_leakage_detected=not evaluation_input.future_price_leakage_detected and not evaluation_input.future_regime_fear_leakage_detected,
    )
    safety_report = RiskAdjustedPaperEvalSafetyReport(
        safety_report_id=f"{evaluation_input.evaluation_id}-SAFETY-REPORT",
        blocked_capabilities=list(_BLOCKED_CAPABILITIES),
        findings=["local_offline_report_only=true", "virtual_execution_only=true"],
    )
    gap_entries.append(_gap(evaluation_input.evaluation_id, "EVALUATION-REPORT-GENERATED", RiskAdjustedPaperEvalGapCategory.EVALUATION_REPORT_GENERATED, "REPORT_ONLY", "risk-adjusted paper evaluation report generated"))
    gap_report = RiskAdjustedPaperEvalGapReport(
        gap_report_id=f"{evaluation_input.evaluation_id}-GAP-REPORT",
        decision=decision,
        gap_entries=gap_entries,
        blocking_gap_count=sum(1 for entry in gap_entries if entry.severity == "BLOCKING"),
        warning_gap_count=sum(1 for entry in gap_entries if entry.severity == "WARNING"),
    )
    return evaluation_input.model_copy(
        update={
            "summary_report": summary_report,
            "virtual_portfolio_report": virtual_portfolio_report,
            "virtual_trade_ledger_report": virtual_trade_ledger_report,
            "cost_slippage_report": cost_slippage_report,
            "risk_adjusted_performance_report": risk_adjusted_report,
            "drawdown_exposure_report": drawdown_exposure_report,
            "regime_fear_bucket_report": regime_fear_bucket_report,
            "pass_readiness_report": pass_readiness_report,
            "safety_report": safety_report,
            "gap_report": gap_report,
        }
    )
