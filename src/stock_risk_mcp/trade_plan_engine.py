from __future__ import annotations

import math

from stock_risk_mcp.basket_risk_engine import review_basket_risk
from stock_risk_mcp.trade_plan_models import (
    BasketRiskState,
    TradePlan,
    TradePlanFixture,
    TradePlanInput,
    TradePlanReport,
    TradePlanSide,
    TradePlanStatus,
)


def build_trade_plan_report(fixture: TradePlanFixture, fixture_checksum: str) -> TradePlanReport:
    plans = [build_trade_plan(candidate, fixture.config) for candidate in fixture.candidates]
    state = BasketRiskState(
        running_basket_risk_amount=0,
        max_basket_risk_amount=fixture.config.portfolio_equity * fixture.config.max_basket_risk_pct,
    )
    reviewed = []
    for plan in plans:
        if plan.plan_status != TradePlanStatus.TRADE_PLAN_READY:
            reviewed.append(plan)
            continue
        decision = review_basket_risk(state, plan.max_loss_amount)
        if not decision.accepted:
            reviewed.append(
                plan.model_copy(
                    update={
                        "plan_status": TradePlanStatus.BLOCKED_BASKET_RISK_CAP,
                        "block_reasons": [*plan.block_reasons, decision.block_reason],
                    }
                )
            )
            continue
        state = decision.updated_state
        reviewed.append(plan)
    summary = {
        "candidate_count": len(reviewed),
        "ready_count": sum(plan.plan_status == TradePlanStatus.TRADE_PLAN_READY for plan in reviewed),
        "watch_only_count": sum(plan.plan_status == TradePlanStatus.WATCH_ONLY for plan in reviewed),
        "blocked_count": sum(
            plan.plan_status
            in {
                TradePlanStatus.BLOCKED_INVALID_STOP,
                TradePlanStatus.BLOCKED_RISK_REWARD_TOO_LOW,
                TradePlanStatus.BLOCKED_BASKET_RISK_CAP,
                TradePlanStatus.BLOCKED_INSUFFICIENT_EVIDENCE,
                TradePlanStatus.BLOCKED_UNSUPPORTED_SIDE,
            }
            for plan in reviewed
        ),
        "no_trade_count": sum(plan.plan_status == TradePlanStatus.NO_TRADE for plan in reviewed),
    }
    return TradePlanReport(
        fixture_checksum=fixture_checksum,
        run_id=fixture.run_id,
        created_at=fixture.created_at,
        config=fixture.config,
        plans=reviewed,
        summary_counts=summary,
        total_ready_basket_risk_amount=state.running_basket_risk_amount,
        max_basket_risk_amount=state.max_basket_risk_amount,
    )


def build_trade_plan(candidate: TradePlanInput, config) -> TradePlan:
    plan = TradePlan(
        ticker=candidate.ticker,
        side=candidate.side,
        setup_type=candidate.setup_type,
        setup_grade=candidate.setup_grade,
        entry_reference=candidate.entry_reference,
        stop_reference=candidate.stop_reference,
        target_reference=candidate.target_reference,
        plan_status=TradePlanStatus.WATCH_ONLY,
        warnings=list(candidate.warnings),
        technical_evidence_summary=candidate.technical_evidence_summary,
        llm_signal_summary=candidate.llm_signal_summary,
    )
    if candidate.side != TradePlanSide.BUY:
        return blocked_plan(
            plan,
            TradePlanStatus.BLOCKED_UNSUPPORTED_SIDE,
            ["UNSUPPORTED_SIDE", "SHORT_SELLING_DISABLED", "MARGIN_DISABLED", "LEVERAGE_DISABLED"],
        )

    if candidate.stop_reference is None:
        return blocked_plan(plan, TradePlanStatus.BLOCKED_INVALID_STOP, ["MISSING_STOP_REFERENCE"])
    if candidate.stop_reference >= candidate.entry_reference:
        return blocked_plan(plan, TradePlanStatus.BLOCKED_INVALID_STOP, ["INVALID_STOP_RELATIONSHIP"])

    stop_distance = abs(candidate.entry_reference - candidate.stop_reference)
    if not math.isfinite(stop_distance) or stop_distance <= 0:
        return blocked_plan(plan, TradePlanStatus.BLOCKED_INVALID_STOP, ["INVALID_STOP_DISTANCE"])

    if candidate.target_reference is None:
        return blocked_plan(plan, TradePlanStatus.BLOCKED_INSUFFICIENT_EVIDENCE, ["MISSING_TARGET_REFERENCE"])
    reward_distance = candidate.target_reference - candidate.entry_reference
    if not math.isfinite(reward_distance) or reward_distance <= 0:
        return blocked_plan(plan, TradePlanStatus.BLOCKED_INSUFFICIENT_EVIDENCE, ["INVALID_TARGET_REFERENCE"])

    risk_amount = config.portfolio_equity * config.risk_pct_per_trade
    quantity = math.floor(risk_amount / stop_distance)
    risk_reward_ratio = reward_distance / stop_distance
    max_loss_amount = quantity * stop_distance if quantity > 0 else 0
    updated = plan.model_copy(
        update={
            "stop_distance": stop_distance,
            "reward_distance": reward_distance,
            "risk_reward_ratio": risk_reward_ratio,
            "max_loss_amount": max_loss_amount,
            "suggested_quantity": quantity,
            "basket_risk_amount": max_loss_amount,
        }
    )
    if risk_reward_ratio < config.fixed_min_risk_reward:
        return blocked_plan(updated, TradePlanStatus.BLOCKED_RISK_REWARD_TOO_LOW, ["RISK_REWARD_BELOW_MINIMUM"])
    if quantity <= 0:
        return updated.model_copy(
            update={
                "plan_status": TradePlanStatus.NO_TRADE,
                "warnings": [*updated.warnings, "ACCOUNT_RISK_BUDGET_TOO_SMALL_FOR_STOP_DISTANCE"],
            }
        )
    return updated.model_copy(update={"plan_status": TradePlanStatus.TRADE_PLAN_READY})


def blocked_plan(plan: TradePlan, status: TradePlanStatus, reasons: list[str]) -> TradePlan:
    return plan.model_copy(update={"plan_status": status, "block_reasons": reasons})
