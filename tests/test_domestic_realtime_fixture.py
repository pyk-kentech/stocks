import json

import pytest

from stock_risk_mcp.domestic_realtime_fixture import load_domestic_realtime_fixture


def provider_profile_payload(
    *,
    strategy_track: str = "DOMESTIC_KR",
    market_id: str = "KRX",
    provider_id: str = "KIWOOM",
):
    return {
        "provider_id": provider_id,
        "strategy_track": strategy_track,
        "market_id": market_id,
        "supported_asset_types": ["STOCK"],
        "provider_mode": "SIMULATION_ONLY",
        "max_symbol_capacity": 2,
        "subscription_grouping": "WATCHLIST",
        "event_types_supported": ["TRADE", "QUOTE", "ORDERBOOK"],
        "normalized_field_availability": ["price", "volume", "cumulative_volume"],
        "provider_staleness_threshold_seconds": 60,
        "received_timestamp_tolerance_seconds": 5,
        "status": "FUTURE_PROVIDER_CANDIDATE",
    }


def market_profile_payload(
    *,
    strategy_track: str = "DOMESTIC_KR",
    market_id: str = "KRX",
    country: str = "KR",
    base_currency: str = "KRW",
    fx_reference: str | None = None,
):
    resolved_fx_reference = fx_reference
    if resolved_fx_reference is None and strategy_track == "OVERSEAS_US":
        resolved_fx_reference = "USD/KRW"
    fee_tax_profile_reference = "fee_tax/domestic_kr.json"
    realtime_data_profile_reference = "realtime/domestic_kr.json"
    provider_capability_reference = "providers/kiwoom_domestic_kr.json"
    settlement_cash_availability = "T+2 domestic placeholder"
    trading_hours = "09:00-15:30 Asia/Seoul"
    exchange_session_profile = "KRX_REGULAR"
    if strategy_track == "OVERSEAS_US":
        fee_tax_profile_reference = "fee_tax/overseas_us.json"
        realtime_data_profile_reference = "realtime/overseas_us.json"
        provider_capability_reference = "providers/overseas_us_simulation_only.json"
        settlement_cash_availability = "T+1 overseas placeholder"
        trading_hours = "PRE+REGULAR+AFTER_HOURS"
        exchange_session_profile = "US_EXTENDED_HOURS"
    return {
        "request_id": "domestic-request-1",
        "strategy_track": strategy_track,
        "strategy_track_candidates": [strategy_track],
        "market_profile": {
            "market_id": market_id,
            "country": country,
            "base_currency": base_currency,
            "exchange_session_profile": exchange_session_profile,
            "trading_hours": trading_hours,
            "settlement_cash_availability": settlement_cash_availability,
            "fee_tax_profile_reference": fee_tax_profile_reference,
            "realtime_data_profile_reference": realtime_data_profile_reference,
            "provider_capability_reference": provider_capability_reference,
            "fx_reference": resolved_fx_reference,
        },
        "provider_capability": {
            "provider_id": "KIWOOM",
            "track": strategy_track,
            "supported_markets": [market_id],
            "supported_asset_types": ["STOCK"],
            "domestic_support": True,
            "overseas_support": False,
            "realtime_support": True,
            "order_support": False,
            "account_support": False,
            "status": "AVAILABLE_DOMESTIC_ONLY" if strategy_track == "DOMESTIC_KR" else "SIMULATION_ONLY",
        },
    }


def subscription_limit_payload(max_symbols: int = 2):
    return {
        "provider_id": "KIWOOM",
        "max_subscribed_symbols": max_symbols,
        "max_groups": 2,
        "priority_tier_policy": "PIN_HIGH_PRIORITY",
        "overflow_policy": "DROP_LOWEST_PRIORITY",
        "downgrade_policy": "REPORT_ONLY_OVERFLOW",
        "limit_evidence": "fixture-limit",
    }


def subscription_plan_payload(symbols=None):
    symbols = symbols or ["005930", "000660"]
    return {
        "plan_id": "krx-plan-1",
        "strategy_track": "DOMESTIC_KR",
        "provider_id": "KIWOOM",
        "watch_universe": "domestic-watchlist",
        "symbols": symbols,
        "subscription_groups": [
            {"group_id": "high-priority", "symbols": symbols[:1], "priority_tier": 1},
            {"group_id": "default", "symbols": symbols[1:], "priority_tier": 2},
        ],
        "dynamic_add_policy": "ADD_HIGH_PRIORITY_ONLY",
        "dynamic_remove_policy": "REMOVE_LOWEST_PRIORITY_FIRST",
        "stale_subscription_handling": "FAIL_CLOSED",
        "fallback_mode": "REPORT_ONLY_IF_OVER_CAPACITY",
    }


def staleness_policy_payload(
    *,
    default_policy: str = "FAIL_CLOSED",
    allow_report_only_downgrade: bool = False,
):
    return {
        "default_policy": default_policy,
        "provider_timestamp_required": True,
        "received_timestamp_required": True,
        "maximum_provider_to_received_lag_seconds": 5,
        "maximum_event_age_seconds": 60,
        "impossible_timestamp_rejection": True,
        "timestamp_mismatch_treatment": "STALE_OR_INVALID",
        "allow_report_only_downgrade": allow_report_only_downgrade,
    }


def event_payload(
    *,
    event_type: str = "TRADE",
    provider_timestamp: str = "2026-06-17T09:00:01+09:00",
    received_timestamp: str = "2026-06-17T09:00:03+09:00",
    symbol: str = "005930",
    extra: dict | None = None,
):
    data = {
        "provider_id": "KIWOOM",
        "strategy_track": "DOMESTIC_KR",
        "market_id": "KRX",
        "symbol": symbol,
        "event_type": event_type,
        "provider_timestamp": provider_timestamp,
        "received_timestamp": received_timestamp,
        "source_fixture_id": "fixture-event-1",
        "price": 70000.0,
        "volume": 100.0,
        "cumulative_volume": 1000.0,
        "best_bid": 69900.0,
        "best_ask": 70100.0,
        "bid_size": 1000.0,
        "ask_size": 1200.0,
        "orderbook_bid_levels": [{"price": 69900.0, "size": 1000.0}],
        "orderbook_ask_levels": [{"price": 70100.0, "size": 1200.0}],
        "baseline_volume": 200.0,
    }
    if extra:
        data.update(extra)
    return data


def domestic_realtime_fixture_payload(
    *,
    strategy_request: dict | None = None,
    provider_profile: dict | None = None,
    subscription_limit: dict | None = None,
    subscription_plan: dict | None = None,
    staleness_policy: dict | None = None,
    events: list[dict] | None = None,
    report_only_mode: bool = False,
):
    return {
        "schema_version": "4.2-domestic-realtime-fixture",
        "run_id": "domestic-realtime-run-1",
        "created_at": "2026-06-17T09:01:00+09:00",
        "report_only_mode": report_only_mode,
        "strategy_request": strategy_request or market_profile_payload(),
        "provider_profile": provider_profile or provider_profile_payload(),
        "subscription_limit": subscription_limit or subscription_limit_payload(),
        "subscription_plan": subscription_plan or subscription_plan_payload(),
        "staleness_policy": staleness_policy or staleness_policy_payload(),
        "events": events or [event_payload()],
    }


def write(tmp_path, name, value):
    path = tmp_path / name
    path.write_text(json.dumps(value), encoding="utf-8")
    return path


def test_domestic_realtime_fixture_loads_valid_domestic_kiwoom_profile(tmp_path):
    fixture = load_domestic_realtime_fixture(write(tmp_path, "domestic_realtime_fixture.json", domestic_realtime_fixture_payload()))
    assert fixture.strategy_request.strategy_track.value == "DOMESTIC_KR"
    assert fixture.provider_profile.provider_id == "KIWOOM"


def test_domestic_realtime_fixture_loads_valid_subscription_plan(tmp_path):
    fixture = load_domestic_realtime_fixture(write(tmp_path, "domestic_realtime_fixture.json", domestic_realtime_fixture_payload()))
    assert fixture.subscription_plan.plan_id == "krx-plan-1"
    assert len(fixture.subscription_plan.symbols) == 2


def test_domestic_realtime_fixture_requires_explicit_json_file(tmp_path):
    with pytest.raises(ValueError, match="JSON"):
        load_domestic_realtime_fixture(write(tmp_path, "domestic_realtime_fixture.txt", domestic_realtime_fixture_payload()))


def test_domestic_realtime_fixture_rejects_missing_strategy_track(tmp_path):
    payload = domestic_realtime_fixture_payload()
    del payload["strategy_request"]["strategy_track"]
    with pytest.raises(ValueError, match="strategy_track"):
        load_domestic_realtime_fixture(write(tmp_path, "domestic_realtime_fixture.json", payload))


def test_domestic_realtime_fixture_rejects_missing_market_profile(tmp_path):
    payload = domestic_realtime_fixture_payload()
    del payload["strategy_request"]["market_profile"]
    with pytest.raises(ValueError, match="market_profile"):
        load_domestic_realtime_fixture(write(tmp_path, "domestic_realtime_fixture.json", payload))


def test_domestic_realtime_fixture_rejects_overseas_us_track(tmp_path):
    payload = domestic_realtime_fixture_payload(
        strategy_request=market_profile_payload(strategy_track="OVERSEAS_US", market_id="US_EQUITY", country="US", base_currency="USD"),
        provider_profile=provider_profile_payload(strategy_track="OVERSEAS_US", market_id="US_EQUITY"),
    )
    with pytest.raises(ValueError, match="DOMESTIC_KR"):
        load_domestic_realtime_fixture(write(tmp_path, "domestic_realtime_fixture.json", payload))
