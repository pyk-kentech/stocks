from stock_risk_mcp.position_sizing_engine import build_position_sizing_review
from stock_risk_mcp.position_sizing_models import PositionSizingDecision, PositionSizingInput
from tests.test_position_sizing_models import position_sizing_payload


def _run(**overrides):
    payload = position_sizing_payload()
    payload.update(overrides)
    return build_position_sizing_review(PositionSizingInput.model_validate(payload))


def test_fixed_percent_stop_sizing_computes_risk_limited_quantity():
    result = _run(stop_mode="FIXED_PERCENT", fixed_stop_percent=0.05, explicit_stop_price=None)
    assert result.summary_report.decision == PositionSizingDecision.SIZE_READY
    assert result.stop_distance_report.stop_distance_percent == 0.05
    assert result.quantity_notional_report.rounded_quantity == 40
    assert result.quantity_notional_report.notional_value == 20000.0


def test_atr_multiple_stop_sizing_computes_bounded_quantity():
    result = _run(stop_mode="ATR_MULTIPLE", fixed_stop_percent=None, explicit_stop_price=None, atr_value=10.0, atr_multiplier=2.0)
    assert result.stop_distance_report.stop_distance_absolute == 20.0
    assert result.quantity_notional_report.rounded_quantity == 50


def test_explicit_stop_price_sizing_computes_bounded_quantity():
    result = _run(stop_mode="EXPLICIT_STOP_PRICE", fixed_stop_percent=None, explicit_stop_price=480.0)
    assert result.stop_distance_report.stop_price == 480.0
    assert result.quantity_notional_report.rounded_quantity == 50


def test_daily_risk_budget_limits_size():
    result = _run(remaining_daily_risk_budget=300.0)
    assert result.summary_report.decision == PositionSizingDecision.RISK_BUDGET_LIMITED
    assert result.quantity_notional_report.rounded_quantity == 12


def test_available_cash_limits_size():
    result = _run(available_cash=5000.0)
    assert result.summary_report.decision == PositionSizingDecision.CASH_LIMITED
    assert result.quantity_notional_report.rounded_quantity == 10


def test_max_single_position_exposure_limits_size():
    result = _run(max_single_position_exposure=0.08)
    assert result.summary_report.decision == PositionSizingDecision.REDUCE_SIZE
    assert result.quantity_notional_report.rounded_quantity == 16


def test_high_volatility_regime_reduces_size():
    result = _run(market_volatility_state="HIGH_VOL", volatility_size_multiplier=0.5)
    assert result.summary_report.decision == PositionSizingDecision.REDUCE_SIZE
    assert result.market_regime_adjustment_report.applied_size_multiplier == 0.5


def test_risk_off_regime_can_force_watch_only():
    result = _run(market_regime_label="RISK_OFF", market_regime_size_multiplier=0.0)
    assert result.summary_report.decision == PositionSizingDecision.WATCH_ONLY


def test_missing_market_regime_creates_note_but_not_auto_block():
    result = _run(market_regime_constraint_ref=None, market_regime_label=None)
    assert result.summary_report.decision != PositionSizingDecision.BLOCKED
    assert result.market_regime_adjustment_report.regime_gap_noted is True


def test_missing_provider_readiness_causes_data_gap():
    result = _run(provider_readiness_ref=None, provider_readiness_level="GAP")
    assert result.summary_report.decision == PositionSizingDecision.DATA_GAP


def test_sanity_check_only_provider_cannot_be_size_ready_without_research_policy():
    result = _run(provider_readiness_level="SANITY_CHECK_ONLY", provider_policy_allows_research_only=False)
    assert result.summary_report.decision == PositionSizingDecision.DATA_GAP


def test_missing_price_causes_gap():
    result = _run(entry_price=None)
    assert result.summary_report.decision in {PositionSizingDecision.GAP, PositionSizingDecision.BLOCKED}


def test_invalid_stop_distance_blocks():
    result = _run(stop_mode="EXPLICIT_STOP_PRICE", explicit_stop_price=500.0, fixed_stop_percent=None)
    assert result.summary_report.decision == PositionSizingDecision.BLOCKED


def test_future_price_atr_fx_leakage_blocks():
    result = _run(available_at="2026-06-24T09:10:00+09:00", decision_anchor_at="2026-06-24T09:05:00+09:00")
    assert result.summary_report.decision == PositionSizingDecision.BLOCKED


def test_learned_multiplier_cannot_exceed_hard_cap():
    result = _run(learned_size_multiplier=1.4)
    assert result.risk_budget_report.learned_multiplier_applied == 1.0


def test_inverse_hedge_candidate_requires_eligibility_liquidity_and_caps():
    result = _run(
        is_inverse_or_hedge=True,
        leverage_flag=True,
        daily_reset_warning=True,
        short_holding_period_warning=True,
        basis_risk_note="TRACKING_ERROR_RISK",
        max_inverse_hedge_exposure=0.05,
        current_gross_exposure=0.14,
    )
    assert result.inverse_hedge_sizing_report.inverse_hedge_review_required is True
    assert result.summary_report.decision == PositionSizingDecision.BLOCKED


def test_executable_order_object_presence_blocks():
    result = _run(source_refs=["fixtures/provider/qqq_price_contract.json", "real_order_payload.json"])
    assert result.summary_report.decision == PositionSizingDecision.BLOCKED


def test_output_remains_non_executable_and_audit_redacted():
    result = _run()
    assert result.summary_report.report_only is True
    assert result.summary_report.non_executable is True
    assert result.audit_records[0].redaction_applied is True

