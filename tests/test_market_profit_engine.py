from stock_risk_mcp.market_profit_engine import build_market_profit_report, compare_market_profit_checks
from stock_risk_mcp.market_profit_models import ProfitabilityEligibilityStatus
from stock_risk_mcp.market_profit_fixture import load_market_profit_fixture
from tests.test_market_profit_fixture import (
    market_profit_fixture_payload,
    overseas_market_profit_fixture_payload,
    write,
)


def test_market_profit_engine_builds_valid_domestic_profitability_estimate(tmp_path):
    fixture = load_market_profit_fixture(write(tmp_path, "market_profit_fixture.json", market_profit_fixture_payload()))
    report = build_market_profit_report(fixture, "fixture")
    assert report.check.net_profit_estimate.expected_net_pnl_amount > 0
    assert report.check.eligibility_status == ProfitabilityEligibilityStatus.ELIGIBLE


def test_market_profit_engine_builds_valid_overseas_profitability_estimate_with_fx(tmp_path):
    fixture = load_market_profit_fixture(write(tmp_path, "market_profit_fixture.json", overseas_market_profit_fixture_payload()))
    report = build_market_profit_report(fixture, "fixture")
    assert report.check.trade_cost_estimate.fx_spread_cost_amount > 0
    assert report.check.net_profit_estimate.reporting_currency == "KRW"


def test_market_profit_engine_fails_closed_on_stale_fx_for_overseas(tmp_path):
    payload = overseas_market_profit_fixture_payload()
    payload["currency_profile"]["fx_timestamp"] = "2026-06-15T10:00:00+00:00"
    payload["currency_profile"]["stale_fx_after_hours"] = 24
    fixture = load_market_profit_fixture(write(tmp_path, "market_profit_fixture.json", payload))
    report = build_market_profit_report(fixture, "fixture")
    assert report.check.eligibility_status == ProfitabilityEligibilityStatus.BLOCKED_STALE_FX


def test_market_profit_engine_report_only_result_cannot_approve_trade_eligibility(tmp_path):
    payload = market_profit_fixture_payload(fee_tax_profile={
        "track": "DOMESTIC_KR",
        "market_id": "KRX",
        "asset_type": "STOCK",
        "buy_commission_rate": 0.001,
        "sell_commission_rate": 0.001,
        "transaction_tax_rate": 0.0018,
        "regulatory_fee_rate": 0.0,
        "annual_tax_treatment": "placeholder",
        "tax_estimate_mode": "REPORT_ONLY",
        "effective_date": "2026-06-17",
        "evidence_source": "local fixture",
        "status": "PLACEHOLDER",
        "simulation_only": False,
    })
    fixture = load_market_profit_fixture(write(tmp_path, "market_profit_fixture.json", payload))
    report = build_market_profit_report(fixture, "fixture")
    assert report.check.net_profit_estimate.actionable_status is False
    assert report.check.eligibility_status == ProfitabilityEligibilityStatus.NON_ACTIONABLE_REPORT_ONLY


def test_market_profit_engine_builds_net_profit_blocked_estimate(tmp_path):
    payload = market_profit_fixture_payload(trade_input={
        "entry_price": 10000.0,
        "exit_price": 10130.0,
        "quantity": 10,
        "min_expected_net_return_pct": 0.01,
        "max_break_even_move_pct": 0.05,
        "target_price": 10130.0,
        "risk_reference_price": 9500.0,
    })
    fixture = load_market_profit_fixture(write(tmp_path, "market_profit_fixture.json", payload))
    report = build_market_profit_report(fixture, "fixture")
    assert report.check.eligibility_status == ProfitabilityEligibilityStatus.BLOCKED_MIN_NET_RETURN


def test_market_profit_engine_builds_break_even_estimate(tmp_path):
    fixture = load_market_profit_fixture(write(tmp_path, "market_profit_fixture.json", market_profit_fixture_payload()))
    report = build_market_profit_report(fixture, "fixture")
    assert report.check.break_even_estimate.break_even_exit_price > fixture.trade_input.entry_price
    assert report.check.break_even_estimate.minimum_target_price_after_costs >= report.check.break_even_estimate.break_even_exit_price


def test_market_profit_compare_tracks_reports_changed_profitability_fields(tmp_path):
    domestic = load_market_profit_fixture(write(tmp_path, "domestic.json", market_profit_fixture_payload())).strategy_request
    overseas = load_market_profit_fixture(write(tmp_path, "overseas.json", overseas_market_profit_fixture_payload())).strategy_request
    report = compare_market_profit_checks([domestic, overseas])
    assert report.comparison_count == 1
    assert "base_currency" in report.comparisons[0]["changed_fields"]
