from __future__ import annotations

from datetime import datetime, timezone

from stock_risk_mcp.market_profit_models import (
    BreakEvenMoveEstimate,
    CurrencyProfile,
    FXCostProfile,
    FeeTaxProfile,
    FeeTaxProfileStatus,
    MarketProfitFixture,
    MarketProfitReport,
    MarketProfitValidationReport,
    NetProfitEstimate,
    ProfitabilityEligibilityStatus,
    TaxEstimateMode,
    TrackAwareProfitabilityCheck,
    TradeCostEstimate,
    MarketProfitComparisonReport,
)
from stock_risk_mcp.strategy_track_models import StrategyTrackRequest


def _fx_rate(currency_profile: CurrencyProfile) -> float:
    if currency_profile.reporting_currency == currency_profile.base_currency:
        return 1.0
    if currency_profile.fx_rate is None:
        raise ValueError("FX rate is required")
    return currency_profile.fx_rate


def _is_stale(fixture: MarketProfitFixture) -> bool:
    if fixture.currency_profile.fx_timestamp is None or fixture.currency_profile.stale_fx_after_hours is None:
        return False
    age = fixture.created_at - fixture.currency_profile.fx_timestamp
    return age.total_seconds() > fixture.currency_profile.stale_fx_after_hours * 3600


def _costs(fixture: MarketProfitFixture) -> TradeCostEstimate:
    trade = fixture.trade_input
    profile = fixture.fee_tax_profile
    fx_rate = _fx_rate(fixture.currency_profile)
    gross_entry_trade = trade.entry_price * trade.quantity
    gross_exit_trade = trade.exit_price * trade.quantity
    gross_entry = gross_entry_trade * fx_rate
    gross_exit = gross_exit_trade * fx_rate
    buy_commission = gross_entry * profile.buy_commission_rate
    sell_commission = gross_exit * profile.sell_commission_rate
    transaction_tax = gross_exit * profile.transaction_tax_rate
    regulatory_fee = gross_exit * profile.regulatory_fee_rate
    fx_spread_cost = 0.0
    fx_conversion_fee = 0.0
    if fixture.fx_cost_profile is not None and fx_rate != 1.0:
        if fixture.fx_cost_profile.buy_side_conversion:
            fx_spread_cost += gross_entry * fixture.fx_cost_profile.fx_spread_rate
            fx_conversion_fee += gross_entry * fixture.fx_cost_profile.conversion_fee_rate
        if fixture.fx_cost_profile.sell_side_conversion:
            fx_spread_cost += gross_exit * fixture.fx_cost_profile.fx_spread_rate
            fx_conversion_fee += gross_exit * fixture.fx_cost_profile.conversion_fee_rate
    gross_pnl = gross_exit - gross_entry
    estimated_tax = 0.0
    if profile.tax_estimate_mode in {TaxEstimateMode.ESTIMATED_PER_TRADE, TaxEstimateMode.ESTIMATED_ANNUALIZED} and gross_pnl > 0:
        estimated_tax = gross_pnl * profile.estimated_tax_rate
    total_costs = buy_commission + sell_commission + transaction_tax + regulatory_fee + fx_spread_cost + fx_conversion_fee + estimated_tax
    return TradeCostEstimate(
        track=fixture.strategy_request.strategy_track,
        market_id=fixture.strategy_request.market_profile.market_id,
        trade_currency=fixture.currency_profile.base_currency,
        reporting_currency=fixture.currency_profile.reporting_currency,
        entry_price=trade.entry_price,
        exit_price=trade.exit_price,
        quantity=trade.quantity,
        gross_entry_amount=gross_entry,
        gross_exit_amount=gross_exit,
        buy_commission_amount=buy_commission,
        sell_commission_amount=sell_commission,
        transaction_tax_amount=transaction_tax,
        regulatory_fee_amount=regulatory_fee,
        fx_spread_cost_amount=fx_spread_cost,
        fx_conversion_fee_amount=fx_conversion_fee,
        estimated_tax_amount=estimated_tax,
        total_estimated_costs=total_costs,
        profile_status_summary={
            "fee_tax_status": profile.status.value,
            "tax_estimate_mode": profile.tax_estimate_mode.value,
            "simulation_only": profile.simulation_only,
        },
    )


def _net_profit(fixture: MarketProfitFixture, costs: TradeCostEstimate) -> NetProfitEstimate:
    gross_pnl = costs.gross_exit_amount - costs.gross_entry_amount
    actionable = fixture.fee_tax_profile.status == FeeTaxProfileStatus.ACTIVE and not fixture.fee_tax_profile.simulation_only
    reasons = []
    completeness = "COMPLETE"
    if fixture.fee_tax_profile.status in {FeeTaxProfileStatus.PLACEHOLDER, FeeTaxProfileStatus.NEEDS_EVIDENCE}:
        actionable = False
        reasons.append("REPORT_ONLY_PROFILE")
        completeness = "PLACEHOLDER_PROFILE"
    if fixture.fee_tax_profile.simulation_only:
        actionable = False
        reasons.append("SIMULATION_ONLY_PROFILE")
        completeness = "SIMULATION_ONLY"
    expected_net_pnl = gross_pnl - costs.total_estimated_costs
    expected_net_return = expected_net_pnl / costs.gross_entry_amount if costs.gross_entry_amount else 0.0
    return NetProfitEstimate(
        gross_pnl_amount=gross_pnl,
        total_estimated_costs=costs.total_estimated_costs,
        expected_net_pnl_amount=expected_net_pnl,
        expected_net_return_pct=expected_net_return,
        reporting_currency=costs.reporting_currency,
        tax_estimate_mode=fixture.fee_tax_profile.tax_estimate_mode,
        actionable_status=actionable,
        non_actionable_reasons=reasons,
        evidence_completeness_status=completeness,
    )


def _break_even(fixture: MarketProfitFixture, costs: TradeCostEstimate) -> BreakEvenMoveEstimate:
    fx_rate = _fx_rate(fixture.currency_profile)
    required_exit_reporting = costs.gross_entry_amount + costs.total_estimated_costs
    break_even_exit_price = required_exit_reporting / (fixture.trade_input.quantity * fx_rate)
    break_even_move_pct = (break_even_exit_price - fixture.trade_input.entry_price) / fixture.trade_input.entry_price
    minimum_target_price = max(fixture.trade_input.target_price, break_even_exit_price)
    minimum_required_move = (minimum_target_price - fixture.trade_input.entry_price) / fixture.trade_input.entry_price
    risk_distance = fixture.trade_input.entry_price - fixture.trade_input.risk_reference_price
    minimum_risk_reward = (minimum_target_price - fixture.trade_input.entry_price) / risk_distance
    return BreakEvenMoveEstimate(
        break_even_exit_price=break_even_exit_price,
        break_even_move_pct=break_even_move_pct,
        minimum_target_price_after_costs=minimum_target_price,
        minimum_required_move_after_costs=minimum_required_move,
        minimum_risk_reward_after_costs=minimum_risk_reward,
    )


def _eligibility(fixture: MarketProfitFixture, net: NetProfitEstimate, breakeven: BreakEvenMoveEstimate) -> tuple[ProfitabilityEligibilityStatus, list[str]]:
    reasons = []
    if fixture.strategy_request.strategy_track.value == "OVERSEAS_US":
        if fixture.currency_profile.fx_rate is None or fixture.fx_cost_profile is None:
            return ProfitabilityEligibilityStatus.BLOCKED_MISSING_FX, ["MISSING_FX_PROFILE"]
        if _is_stale(fixture):
            return ProfitabilityEligibilityStatus.BLOCKED_STALE_FX, ["STALE_FX"]
    if not net.actionable_status:
        return ProfitabilityEligibilityStatus.NON_ACTIONABLE_REPORT_ONLY, net.non_actionable_reasons or ["NON_ACTIONABLE"]
    if net.expected_net_pnl_amount <= 0:
        return ProfitabilityEligibilityStatus.BLOCKED_NON_POSITIVE_NET_PROFIT, ["EXPECTED_NET_PROFIT_NON_POSITIVE"]
    if net.expected_net_return_pct < fixture.trade_input.min_expected_net_return_pct:
        return ProfitabilityEligibilityStatus.BLOCKED_MIN_NET_RETURN, ["MIN_EXPECTED_NET_RETURN_NOT_MET"]
    if breakeven.break_even_move_pct > fixture.trade_input.max_break_even_move_pct:
        return ProfitabilityEligibilityStatus.BLOCKED_BREAK_EVEN_MOVE, ["BREAK_EVEN_MOVE_TOO_LARGE"]
    return ProfitabilityEligibilityStatus.ELIGIBLE, reasons


def build_market_profit_report(fixture: MarketProfitFixture, fixture_checksum: str) -> MarketProfitReport:
    costs = _costs(fixture)
    net = _net_profit(fixture, costs)
    breakeven = _break_even(fixture, costs)
    status, block_reasons = _eligibility(fixture, net, breakeven)
    return MarketProfitReport(
        fixture_checksum=fixture_checksum,
        run_id=fixture.run_id,
        created_at=fixture.created_at,
        check=TrackAwareProfitabilityCheck(
            strategy_track=fixture.strategy_request.strategy_track,
            market_profile=fixture.strategy_request.market_profile,
            fee_tax_profile=fixture.fee_tax_profile,
            currency_profile=fixture.currency_profile,
            fx_cost_profile=fixture.fx_cost_profile,
            trade_cost_estimate=costs,
            net_profit_estimate=net,
            break_even_estimate=breakeven,
            eligibility_status=status,
            warnings=[],
            block_reasons=block_reasons,
        ),
    )


def validate_market_profit_fixture(fixture: MarketProfitFixture) -> MarketProfitValidationReport:
    return MarketProfitValidationReport(
        run_id=fixture.run_id,
        created_at=fixture.created_at,
        summary={
            "strategy_track": fixture.strategy_request.strategy_track.value,
            "market_id": fixture.strategy_request.market_profile.market_id,
            "reporting_currency": fixture.currency_profile.reporting_currency,
        },
    )


def compare_market_profit_checks(requests: list[StrategyTrackRequest]) -> MarketProfitComparisonReport:
    comparisons = []
    for left, right in zip(requests, requests[1:]):
        changed_fields = []
        field_pairs = {
            "market_id": (left.market_profile.market_id, right.market_profile.market_id),
            "base_currency": (left.market_profile.base_currency, right.market_profile.base_currency),
            "settlement_cash_availability": (
                left.market_profile.settlement_cash_availability,
                right.market_profile.settlement_cash_availability,
            ),
            "fee_tax_profile_reference": (
                left.market_profile.fee_tax_profile_reference,
                right.market_profile.fee_tax_profile_reference,
            ),
            "provider_capability_reference": (
                left.market_profile.provider_capability_reference,
                right.market_profile.provider_capability_reference,
            ),
        }
        for name, pair in field_pairs.items():
            if pair[0] != pair[1]:
                changed_fields.append(name)
        comparisons.append(
            {
                "left_request_id": left.request_id,
                "right_request_id": right.request_id,
                "left_track": left.strategy_track.value,
                "right_track": right.strategy_track.value,
                "changed_fields": changed_fields,
            }
        )
    return MarketProfitComparisonReport(
        run_id="market-profit-comparison",
        created_at=datetime.now(timezone.utc),
        comparison_count=len(comparisons),
        comparisons=comparisons,
    )
