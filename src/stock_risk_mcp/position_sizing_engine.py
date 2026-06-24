from __future__ import annotations

import math

from stock_risk_mcp.position_sizing_guard import validate_position_sizing_metadata_safety
from stock_risk_mcp.position_sizing_models import (
    InverseHedgeSizingReport,
    MarketRegimeSizingAdjustmentReport,
    PositionCostAssumptionReport,
    PositionQuantityNotionalReport,
    PositionSizingBoundaryViolationReport,
    PositionSizingDataReadinessReport,
    PositionSizingDecision,
    PositionSizingGapEntry,
    PositionSizingGapReport,
    PositionSizingInput,
    PositionSizingSummaryReport,
    RiskBudgetReport,
    StopDistanceMode,
    StopDistanceReport,
)


def _gap(input_id: str, suffix: str, category: str, severity: str, message: str) -> PositionSizingGapEntry:
    return PositionSizingGapEntry(
        gap_id=f"{input_id}-{suffix}",
        gap_category=category,
        severity=severity,
        message=message,
    )


def _safe_ref_present(value: str | None) -> bool:
    return bool(value and str(value).strip())


def _calc_stop(input_data: PositionSizingInput) -> tuple[float | None, float | None, float | None, float | None, bool]:
    if not input_data.entry_price:
        return None, None, None, None, False
    entry = input_data.entry_price
    if input_data.stop_mode == StopDistanceMode.FIXED_PERCENT and input_data.fixed_stop_percent:
        stop_distance_abs = entry * input_data.fixed_stop_percent
        return entry - stop_distance_abs, stop_distance_abs, input_data.fixed_stop_percent, None, stop_distance_abs > 0
    if input_data.stop_mode == StopDistanceMode.ATR_MULTIPLE and input_data.atr_value and input_data.atr_multiplier:
        stop_distance_abs = input_data.atr_value * input_data.atr_multiplier
        return entry - stop_distance_abs, stop_distance_abs, stop_distance_abs / entry, input_data.atr_multiplier, stop_distance_abs > 0
    if input_data.stop_mode == StopDistanceMode.EXPLICIT_STOP_PRICE and input_data.explicit_stop_price:
        stop_distance_abs = entry - input_data.explicit_stop_price
        return input_data.explicit_stop_price, stop_distance_abs, stop_distance_abs / entry, None, stop_distance_abs > 0
    if input_data.stop_mode == StopDistanceMode.VOLATILITY_ADJUSTED and input_data.atr_value:
        atr_multiple = input_data.atr_multiplier or 1.0
        stop_distance_abs = input_data.atr_value * atr_multiple * max(input_data.volatility_size_multiplier, 1.0)
        return entry - stop_distance_abs, stop_distance_abs, stop_distance_abs / entry, atr_multiple, stop_distance_abs > 0
    return None, None, None, None, False


def build_position_sizing_review(position_input: PositionSizingInput) -> PositionSizingInput:
    for audit in position_input.audit_records:
        validate_position_sizing_metadata_safety(
            {"source_path": audit.source_path, "operator_context": audit.operator_context},
            context="position sizing audit",
        )

    gap_entries: list[PositionSizingGapEntry] = []
    violations: list[str] = []

    if any("real_order" in ref.lower() or "order_payload" in ref.lower() for ref in position_input.source_refs):
        violations.append("EXECUTABLE_ORDER_OBJECT_PRESENT")
    if not position_input.entry_price or not position_input.current_price:
        gap_entries.append(_gap(position_input.sizing_review_id, "MISSING-PRICE", "MISSING_PRICE", "BLOCKING", "price evidence is missing"))
    if position_input.available_at and position_input.decision_anchor_at and position_input.available_at > position_input.decision_anchor_at:
        gap_entries.append(_gap(position_input.sizing_review_id, "FUTURE-LEAKAGE", "FUTURE_PRICE_ATR_FX_LEAKAGE", "BLOCKING", "available_at is later than decision anchor"))
    if position_input.provider_readiness_level == "SANITY_CHECK_ONLY" and not position_input.provider_policy_allows_research_only:
        gap_entries.append(_gap(position_input.sizing_review_id, "PROVIDER-SANITY-ONLY", "PROVIDER_SANITY_ONLY", "WARNING", "sanity-check-only provider cannot promote size"))

    price_ready = _safe_ref_present(position_input.price_contract_ref) and position_input.available_at is not None
    atr_ready = (position_input.stop_mode != StopDistanceMode.ATR_MULTIPLE) or (_safe_ref_present(position_input.atr_contract_ref) and position_input.available_at is not None and position_input.atr_value is not None)
    fx_needed = position_input.currency != "USD" or (position_input.fx_conversion_rate is not None and position_input.fx_conversion_rate != 1.0)
    fx_ready = (not fx_needed) or (_safe_ref_present(position_input.fx_contract_ref) and _safe_ref_present(position_input.fx_conversion_ref))
    cost_ready = _safe_ref_present(position_input.cost_contract_ref) and _safe_ref_present(position_input.fee_tax_slippage_assumption_ref)
    if not position_input.provider_readiness_ref or position_input.provider_readiness_level in {"GAP", "REJECTED"}:
        gap_entries.append(_gap(position_input.sizing_review_id, "PROVIDER-GAP", "PROVIDER_READINESS_GAP", "WARNING", "provider readiness evidence is missing or invalid"))
    if not price_ready:
        gap_entries.append(_gap(position_input.sizing_review_id, "PRICE-REF-GAP", "MISSING_PRICE_CONTRACT", "BLOCKING", "price contract ref or available_at is missing"))
    if not atr_ready:
        gap_entries.append(_gap(position_input.sizing_review_id, "ATR-REF-GAP", "MISSING_ATR_EVIDENCE", "WARNING", "atr evidence is missing"))
    if not fx_ready:
        gap_entries.append(_gap(position_input.sizing_review_id, "FX-REF-GAP", "MISSING_FX_EVIDENCE", "WARNING", "fx evidence is missing"))
    if not cost_ready:
        gap_entries.append(_gap(position_input.sizing_review_id, "COST-REF-GAP", "MISSING_COST_EVIDENCE", "WARNING", "cost evidence is missing"))

    stop_price, stop_distance_abs, stop_distance_pct, atr_multiple, stop_valid = _calc_stop(position_input)
    if not stop_valid:
        gap_entries.append(_gap(position_input.sizing_review_id, "STOP-GAP", "INVALID_STOP_DISTANCE", "BLOCKING", "stop distance is invalid or unsupported"))

    risk_cash = min(position_input.account_equity * position_input.risk_per_trade_percent, position_input.max_risk_cash_per_trade)
    effective_risk_cash = min(risk_cash, position_input.remaining_daily_risk_budget)
    if position_input.remaining_daily_risk_budget < risk_cash:
        gap_entries.append(_gap(position_input.sizing_review_id, "DAILY-RISK-LIMIT", "DAILY_RISK_LIMIT_ACTIVE", "WARNING", "remaining daily risk budget limits size"))

    applied_multiplier = position_input.market_regime_size_multiplier * position_input.volatility_size_multiplier * position_input.confidence_multiplier
    if position_input.market_volatility_state == "HIGH_VOL":
        applied_multiplier = min(applied_multiplier, 0.5)
    learned_applied = min(position_input.learned_size_multiplier, 1.0)
    regime_gap_noted = False
    if not position_input.market_regime_constraint_ref or not position_input.market_regime_label:
        regime_gap_noted = True
        gap_entries.append(_gap(position_input.sizing_review_id, "REGIME-GAP", "MISSING_MARKET_REGIME", "REPORT_ONLY", "market regime evidence is missing"))

    raw_quantity = 0.0
    rounded_quantity = 0
    notional_value = 0.0
    exposure_after_trade = position_input.current_gross_exposure
    if stop_distance_abs and position_input.entry_price:
        raw_quantity = (effective_risk_cash / stop_distance_abs) * applied_multiplier if stop_distance_abs > 0 else 0.0
        if position_input.requested_quantity is not None and position_input.requested_quantity > 0:
            raw_quantity = min(raw_quantity, float(position_input.requested_quantity))
        rounded_quantity = max(0, math.floor(raw_quantity / position_input.round_lot_size) * position_input.round_lot_size)
        notional_value = rounded_quantity * position_input.entry_price
        exposure_after_trade = position_input.current_gross_exposure + (notional_value / position_input.account_equity if position_input.account_equity else 0.0)

    cash_limited_quantity = math.floor(position_input.available_cash / position_input.entry_price) if position_input.entry_price else 0
    single_position_limit_quantity = math.floor((position_input.account_equity * position_input.max_single_position_exposure) / position_input.entry_price) if position_input.entry_price else 0
    cap_quantity = min(value for value in (rounded_quantity, cash_limited_quantity, single_position_limit_quantity) if value >= 0)
    cash_limited = cash_limited_quantity < rounded_quantity
    risk_budget_limited = position_input.remaining_daily_risk_budget < risk_cash
    exposure_limited = single_position_limit_quantity < rounded_quantity
    if cash_limited or exposure_limited:
        rounded_quantity = max(0, cap_quantity)
        notional_value = rounded_quantity * (position_input.entry_price or 0.0)
        exposure_after_trade = position_input.current_gross_exposure + (notional_value / position_input.account_equity if position_input.account_equity else 0.0)

    inverse_breach = False
    inverse_review_required = position_input.is_inverse_or_hedge
    if position_input.is_inverse_or_hedge:
        required = [
            _safe_ref_present(position_input.instrument_eligibility_ref),
            _safe_ref_present(position_input.liquidity_evidence_ref),
            bool(position_input.leverage_flag),
            bool(position_input.daily_reset_warning),
            bool(position_input.short_holding_period_warning),
            bool(position_input.basis_risk_note),
        ]
        if not all(required):
            gap_entries.append(_gap(position_input.sizing_review_id, "INVERSE-GAP", "INVERSE_HEDGE_REQUIREMENTS_MISSING", "BLOCKING", "inverse or hedge requirements are incomplete"))
        inverse_exposure_after = position_input.current_gross_exposure + (notional_value / position_input.account_equity if position_input.account_equity else 0.0)
        inverse_breach = inverse_exposure_after > position_input.max_inverse_hedge_exposure
        if inverse_breach:
            gap_entries.append(_gap(position_input.sizing_review_id, "INVERSE-CAP", "INVERSE_HEDGE_CAP_BREACH", "BLOCKING", "inverse or hedge cap exceeded"))

    estimated_fees = notional_value * (position_input.fee_bps / 10000)
    estimated_tax = notional_value * (position_input.tax_bps / 10000)
    estimated_slippage = notional_value * (position_input.slippage_bps / 10000)
    total_estimated_cost = estimated_fees + estimated_tax + estimated_slippage

    if violations:
        gap_entries.append(_gap(position_input.sizing_review_id, "BOUNDARY-VIOLATION", "EXECUTABLE_ORDER_DETECTED", "BLOCKING", "unsafe executable order metadata detected"))

    if position_input.market_regime_label == "RISK_OFF" and position_input.market_regime_size_multiplier <= 0:
        decision = PositionSizingDecision.WATCH_ONLY
        reason = "risk-off policy reduced size to watch-only"
    elif any(entry.severity == "BLOCKING" for entry in gap_entries) or violations:
        decision = PositionSizingDecision.BLOCKED
        reason = "blocking gap or boundary violation detected"
    elif not price_ready or not stop_valid:
        decision = PositionSizingDecision.GAP
        reason = "price or stop evidence is insufficient"
    elif not atr_ready or not fx_ready or not cost_ready or not position_input.provider_readiness_ref:
        decision = PositionSizingDecision.DATA_GAP
        reason = "provider or canonical data readiness is incomplete"
    elif position_input.provider_readiness_level == "SANITY_CHECK_ONLY" and not position_input.provider_policy_allows_research_only:
        decision = PositionSizingDecision.DATA_GAP
        reason = "provider is sanity-check-only"
    elif risk_budget_limited:
        decision = PositionSizingDecision.RISK_BUDGET_LIMITED
        reason = "daily risk budget reduced allowed size"
    elif cash_limited:
        decision = PositionSizingDecision.CASH_LIMITED
        reason = "available cash reduced allowed size"
    elif exposure_limited or applied_multiplier < 1.0:
        decision = PositionSizingDecision.REDUCE_SIZE
        reason = "exposure or regime policy reduced allowed size"
    elif rounded_quantity <= 0:
        decision = PositionSizingDecision.BLOCKED
        reason = "no valid quantity remains after constraints"
    else:
        decision = PositionSizingDecision.SIZE_READY
        reason = "sizing evidence is sufficient and within hard caps"

    summary_report = PositionSizingSummaryReport(
        report_id=f"{position_input.sizing_review_id}-SUMMARY-REPORT",
        decision=decision,
        decision_reason=reason,
        candidate_symbol=position_input.candidate_symbol,
        risk_cash=risk_cash,
        effective_risk_cash=effective_risk_cash,
        rounded_quantity=rounded_quantity,
        notional_value=notional_value,
        capital_usage_percent=(notional_value / position_input.available_cash) if position_input.available_cash else 0.0,
        risk_usage_percent=(effective_risk_cash / risk_cash) if risk_cash else 0.0,
        remaining_cash_estimate=position_input.available_cash - notional_value - total_estimated_cost,
        remaining_daily_risk_budget_estimate=position_input.remaining_daily_risk_budget - min(effective_risk_cash, risk_cash),
    )
    stop_distance_report = StopDistanceReport(
        report_id=f"{position_input.sizing_review_id}-STOP-REPORT",
        stop_mode=position_input.stop_mode,
        stop_price=stop_price,
        stop_distance_absolute=stop_distance_abs,
        stop_distance_percent=stop_distance_pct,
        atr_multiple=atr_multiple,
        stop_valid=stop_valid,
        stop_evidence_ref=position_input.atr_contract_ref if position_input.stop_mode == StopDistanceMode.ATR_MULTIPLE else position_input.price_contract_ref,
    )
    risk_budget_report = RiskBudgetReport(
        report_id=f"{position_input.sizing_review_id}-RISK-BUDGET-REPORT",
        risk_per_trade_cap=position_input.risk_per_trade_percent,
        max_daily_loss_cap=position_input.max_daily_loss_cap,
        max_open_risk_cap=position_input.max_open_risk_cap,
        market_regime_size_multiplier=position_input.market_regime_size_multiplier,
        volatility_size_multiplier=position_input.volatility_size_multiplier,
        confidence_multiplier=position_input.confidence_multiplier,
        learned_multiplier_requested=position_input.learned_size_multiplier,
        learned_multiplier_applied=learned_applied,
        fail_closed=position_input.fail_closed,
    )
    data_readiness_report = PositionSizingDataReadinessReport(
        report_id=f"{position_input.sizing_review_id}-DATA-READINESS-REPORT",
        price_ready=price_ready,
        atr_ready=atr_ready,
        fx_ready=fx_ready,
        cost_ready=cost_ready,
        provider_readiness_level=position_input.provider_readiness_level,
        research_only_policy_allowed=position_input.provider_policy_allows_research_only,
        missing_refs=[
            label for label, ready in (
                ("PRICE_CONTRACT_REF", price_ready),
                ("ATR_CONTRACT_REF", atr_ready),
                ("FX_CONTRACT_REF", fx_ready),
                ("COST_CONTRACT_REF", cost_ready),
            ) if not ready
        ],
    )
    quantity_notional_report = PositionQuantityNotionalReport(
        report_id=f"{position_input.sizing_review_id}-QUANTITY-REPORT",
        stop_distance_per_share=stop_distance_abs or 0.0,
        raw_quantity=raw_quantity,
        rounded_quantity=rounded_quantity,
        notional_value=notional_value,
        exposure_after_trade=exposure_after_trade,
    )
    cost_assumption_report = PositionCostAssumptionReport(
        report_id=f"{position_input.sizing_review_id}-COST-REPORT",
        estimated_fees=estimated_fees,
        estimated_tax=estimated_tax,
        estimated_slippage=estimated_slippage,
        total_estimated_cost=total_estimated_cost,
        fee_tax_slippage_assumption_ref=position_input.fee_tax_slippage_assumption_ref,
    )
    regime_report = MarketRegimeSizingAdjustmentReport(
        report_id=f"{position_input.sizing_review_id}-REGIME-REPORT",
        market_regime_label=position_input.market_regime_label,
        market_volatility_state=position_input.market_volatility_state,
        market_stress_state=position_input.market_stress_state,
        applied_size_multiplier=applied_multiplier,
        regime_gap_noted=regime_gap_noted,
        watch_only_triggered=decision == PositionSizingDecision.WATCH_ONLY,
    )
    inverse_report = InverseHedgeSizingReport(
        report_id=f"{position_input.sizing_review_id}-INVERSE-HEDGE-REPORT",
        inverse_hedge_review_required=inverse_review_required,
        inverse_hedge_cap_breached=inverse_breach,
        leverage_flag_present=position_input.leverage_flag,
        daily_reset_warning_present=position_input.daily_reset_warning,
        short_holding_period_warning_present=position_input.short_holding_period_warning,
        basis_risk_note=position_input.basis_risk_note,
    )
    boundary_report = PositionSizingBoundaryViolationReport(
        report_id=f"{position_input.sizing_review_id}-BOUNDARY-REPORT",
        violations=violations,
    )
    gap_entries.append(_gap(position_input.sizing_review_id, "SIZING-REPORT-GENERATED", "POSITION_SIZING_REPORT_GENERATED", "REPORT_ONLY", "position sizing report generated"))
    gap_report = PositionSizingGapReport(
        gap_report_id=f"{position_input.sizing_review_id}-GAP-REPORT",
        decision=decision,
        gap_entries=gap_entries,
        blocking_gap_count=sum(1 for entry in gap_entries if entry.severity == "BLOCKING"),
        warning_gap_count=sum(1 for entry in gap_entries if entry.severity == "WARNING"),
        gap_categories=[entry.gap_category for entry in gap_entries],
    )
    return position_input.model_copy(
        update={
            "summary_report": summary_report,
            "stop_distance_report": stop_distance_report,
            "risk_budget_report": risk_budget_report,
            "data_readiness_report": data_readiness_report,
            "quantity_notional_report": quantity_notional_report,
            "cost_assumption_report": cost_assumption_report,
            "market_regime_adjustment_report": regime_report,
            "inverse_hedge_sizing_report": inverse_report,
            "boundary_violation_report": boundary_report,
            "gap_report": gap_report,
        }
    )
