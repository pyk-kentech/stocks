import json

import pytest

from stock_risk_mcp.market_profit_fixture import load_market_profit_fixture


def market_profit_fixture_payload(
    *,
    strategy_request: dict | None = None,
    fee_tax_profile: dict | None = None,
    currency_profile: dict | None = None,
    fx_cost_profile: dict | None = None,
    trade_input: dict | None = None,
):
    return {
        "schema_version": "4.1-market-profit-fixture",
        "run_id": "market-profit-run-1",
        "created_at": "2026-06-17T12:00:00+00:00",
        "strategy_request": strategy_request or {
            "request_id": "domestic-request-1",
            "strategy_track": "DOMESTIC_KR",
            "strategy_track_candidates": ["DOMESTIC_KR"],
            "market_profile": {
                "market_id": "KRX",
                "country": "KR",
                "base_currency": "KRW",
                "exchange_session_profile": "KRX_REGULAR",
                "trading_hours": "09:00-15:30 Asia/Seoul",
                "settlement_cash_availability": "T+2 domestic placeholder",
                "fee_tax_profile_reference": "fee_tax/domestic_kr.json",
                "realtime_data_profile_reference": "realtime/domestic_kr.json",
                "provider_capability_reference": "providers/kiwoom_domestic_kr.json",
                "fx_reference": None,
            },
            "provider_capability": {
                "provider_id": "KIWOOM",
                "track": "DOMESTIC_KR",
                "supported_markets": ["KRX"],
                "supported_asset_types": ["STOCK"],
                "domestic_support": True,
                "overseas_support": False,
                "realtime_support": True,
                "order_support": False,
                "account_support": False,
                "status": "AVAILABLE_DOMESTIC_ONLY",
            },
        },
        "fee_tax_profile": fee_tax_profile or {
            "track": "DOMESTIC_KR",
            "market_id": "KRX",
            "asset_type": "STOCK",
            "buy_commission_rate": 0.001,
            "sell_commission_rate": 0.001,
            "transaction_tax_rate": 0.0018,
            "regulatory_fee_rate": 0.0,
            "annual_tax_treatment": "placeholder",
            "tax_estimate_mode": "EXCLUDED",
            "effective_date": "2026-06-17",
            "evidence_source": "local fixture",
            "status": "ACTIVE",
            "simulation_only": False,
        },
        "currency_profile": currency_profile or {
            "base_currency": "KRW",
            "settlement_currency": "KRW",
            "reporting_currency": "KRW",
            "fx_reference_pair": None,
            "fx_rate_source": None,
            "fx_timestamp": None,
            "fx_rate": None,
            "stale_fx_after_hours": None,
            "missing_fx_policy": "FAIL_CLOSED",
        },
        "fx_cost_profile": fx_cost_profile,
        "trade_input": trade_input or {
            "entry_price": 10000.0,
            "exit_price": 11000.0,
            "quantity": 10,
            "min_expected_net_return_pct": 0.01,
            "max_break_even_move_pct": 0.05,
            "target_price": 11000.0,
            "risk_reference_price": 9500.0,
        },
    }


def overseas_market_profit_fixture_payload():
    return market_profit_fixture_payload(
        strategy_request={
            "request_id": "overseas-request-1",
            "strategy_track": "OVERSEAS_US",
            "strategy_track_candidates": ["OVERSEAS_US"],
            "market_profile": {
                "market_id": "US_EQUITY",
                "country": "US",
                "base_currency": "USD",
                "exchange_session_profile": "US_EXTENDED_HOURS",
                "trading_hours": "PRE+REGULAR+AFTER_HOURS",
                "settlement_cash_availability": "T+1 overseas placeholder",
                "fee_tax_profile_reference": "fee_tax/overseas_us.json",
                "realtime_data_profile_reference": "realtime/overseas_us.json",
                "provider_capability_reference": "providers/overseas_us_simulation_only.json",
                "fx_reference": "USD/KRW",
            },
            "provider_capability": {
                "provider_id": "UNRESOLVED",
                "track": "OVERSEAS_US",
                "supported_markets": ["NYSE", "NASDAQ"],
                "supported_asset_types": ["STOCK"],
                "domestic_support": False,
                "overseas_support": True,
                "realtime_support": False,
                "order_support": False,
                "account_support": False,
                "status": "SIMULATION_ONLY",
            },
        },
        fee_tax_profile={
            "track": "OVERSEAS_US",
            "market_id": "US_EQUITY",
            "asset_type": "STOCK",
            "buy_commission_rate": 0.001,
            "sell_commission_rate": 0.001,
            "transaction_tax_rate": 0.0,
            "regulatory_fee_rate": 0.00003,
            "annual_tax_treatment": "placeholder",
            "tax_estimate_mode": "EXCLUDED",
            "effective_date": "2026-06-17",
            "evidence_source": "local fixture",
            "status": "ACTIVE",
            "simulation_only": False,
        },
        currency_profile={
            "base_currency": "USD",
            "settlement_currency": "USD",
            "reporting_currency": "KRW",
            "fx_reference_pair": "USD/KRW",
            "fx_rate_source": "fixture",
            "fx_timestamp": "2026-06-17T11:00:00+00:00",
            "fx_rate": 1350.0,
            "stale_fx_after_hours": 24,
            "missing_fx_policy": "FAIL_CLOSED",
        },
        fx_cost_profile={
            "fx_spread_rate": 0.001,
            "conversion_fee_rate": 0.0005,
            "buy_side_conversion": True,
            "sell_side_conversion": True,
            "realized_fx_only": True,
            "status": "ACTIVE",
        },
        trade_input={
            "entry_price": 10.0,
            "exit_price": 12.0,
            "quantity": 10,
            "min_expected_net_return_pct": 0.01,
            "max_break_even_move_pct": 0.2,
            "target_price": 12.0,
            "risk_reference_price": 9.0,
        },
    )


def write(tmp_path, name, value):
    path = tmp_path / name
    path.write_text(json.dumps(value), encoding="utf-8")
    return path


def test_market_profit_fixture_loads_valid_domestic_profile(tmp_path):
    fixture = load_market_profit_fixture(write(tmp_path, "market_profit_fixture.json", market_profit_fixture_payload()))
    assert fixture.strategy_request.strategy_track.value == "DOMESTIC_KR"
    assert fixture.fee_tax_profile.status.value == "ACTIVE"


def test_market_profit_fixture_loads_valid_overseas_profile_with_fx(tmp_path):
    fixture = load_market_profit_fixture(write(tmp_path, "market_profit_fixture.json", overseas_market_profit_fixture_payload()))
    assert fixture.strategy_request.strategy_track.value == "OVERSEAS_US"
    assert fixture.currency_profile.fx_reference_pair == "USD/KRW"


def test_market_profit_fixture_requires_explicit_json_file(tmp_path):
    with pytest.raises(ValueError, match="JSON"):
        load_market_profit_fixture(write(tmp_path, "market_profit_fixture.txt", market_profit_fixture_payload()))


def test_market_profit_fixture_rejects_missing_market_profile(tmp_path):
    payload = market_profit_fixture_payload()
    del payload["strategy_request"]["market_profile"]
    with pytest.raises(ValueError, match="market_profile"):
        load_market_profit_fixture(write(tmp_path, "market_profit_fixture.json", payload))


def test_market_profit_fixture_rejects_missing_strategy_track(tmp_path):
    payload = market_profit_fixture_payload()
    del payload["strategy_request"]["strategy_track"]
    with pytest.raises(ValueError, match="strategy_track"):
        load_market_profit_fixture(write(tmp_path, "market_profit_fixture.json", payload))


def test_market_profit_fixture_rejects_missing_fee_tax_profile(tmp_path):
    payload = market_profit_fixture_payload()
    del payload["fee_tax_profile"]
    with pytest.raises(ValueError, match="fee_tax_profile"):
        load_market_profit_fixture(write(tmp_path, "market_profit_fixture.json", payload))


def test_market_profit_fixture_rejects_missing_currency_profile(tmp_path):
    payload = market_profit_fixture_payload()
    del payload["currency_profile"]
    with pytest.raises(ValueError, match="currency_profile"):
        load_market_profit_fixture(write(tmp_path, "market_profit_fixture.json", payload))


def test_market_profit_fixture_rejects_missing_fx_for_overseas(tmp_path):
    payload = overseas_market_profit_fixture_payload()
    payload["currency_profile"]["fx_rate"] = None
    payload["currency_profile"]["fx_timestamp"] = None
    payload["fx_cost_profile"] = None
    with pytest.raises(ValueError, match="FX"):
        load_market_profit_fixture(write(tmp_path, "market_profit_fixture.json", payload))


def test_market_profit_fixture_defaults_placeholder_profile_to_report_only(tmp_path):
    payload = market_profit_fixture_payload(fee_tax_profile={
        "track": "DOMESTIC_KR",
        "market_id": "KRX",
        "asset_type": "STOCK",
        "buy_commission_rate": 0.001,
        "sell_commission_rate": 0.001,
        "transaction_tax_rate": 0.0018,
        "regulatory_fee_rate": 0.0,
        "annual_tax_treatment": "placeholder",
        "tax_estimate_mode": "EXCLUDED",
        "effective_date": "2026-06-17",
        "evidence_source": "local fixture",
        "status": "PLACEHOLDER",
        "simulation_only": False,
    })
    fixture = load_market_profit_fixture(write(tmp_path, "market_profit_fixture.json", payload))
    assert fixture.fee_tax_profile.tax_estimate_mode.value == "REPORT_ONLY"


def test_market_profit_fixture_rejects_placeholder_profile_non_report_only_without_simulation(tmp_path):
    payload = market_profit_fixture_payload(fee_tax_profile={
        "track": "DOMESTIC_KR",
        "market_id": "KRX",
        "asset_type": "STOCK",
        "buy_commission_rate": 0.001,
        "sell_commission_rate": 0.001,
        "transaction_tax_rate": 0.0018,
        "regulatory_fee_rate": 0.0,
        "annual_tax_treatment": "placeholder",
        "tax_estimate_mode": "ESTIMATED_PER_TRADE",
        "effective_date": "2026-06-17",
        "evidence_source": "local fixture",
        "status": "PLACEHOLDER",
        "simulation_only": False,
    })
    with pytest.raises(ValueError, match="REPORT_ONLY"):
        load_market_profit_fixture(write(tmp_path, "market_profit_fixture.json", payload))
