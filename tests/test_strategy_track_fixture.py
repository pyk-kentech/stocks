import json

import pytest

from stock_risk_mcp.strategy_track_fixture import load_strategy_track_fixture


def strategy_track_request_payload(
    *,
    request_id: str = "domestic-request-1",
    strategy_track: str = "DOMESTIC_KR",
    market_profile: dict | None = None,
    provider_capability: dict | None = None,
    strategy_track_candidates: list[str] | None = None,
):
    return {
        "request_id": request_id,
        "strategy_track": strategy_track,
        "strategy_track_candidates": strategy_track_candidates or [strategy_track],
        "market_profile": market_profile or {
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
        "provider_capability": provider_capability or {
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
    }


def strategy_track_fixture_payload(requests: list[dict] | None = None):
    return {
        "schema_version": "4.0-strategy-track-fixture",
        "run_id": "strategy-track-run-1",
        "created_at": "2026-06-17T12:00:00+00:00",
        "strategy_requests": requests or [strategy_track_request_payload()],
    }


def write(tmp_path, name, value):
    path = tmp_path / name
    path.write_text(json.dumps(value), encoding="utf-8")
    return path


def test_strategy_track_fixture_loads_valid_domestic_profile(tmp_path):
    fixture = load_strategy_track_fixture(write(tmp_path, "strategy_track_fixture.json", strategy_track_fixture_payload()))
    request = fixture.strategy_requests[0]
    assert request.strategy_track.value == "DOMESTIC_KR"
    assert request.provider_capability.status.value == "AVAILABLE_DOMESTIC_ONLY"


def test_strategy_track_fixture_loads_valid_overseas_simulation_only_profile(tmp_path):
    overseas = strategy_track_request_payload(
        request_id="overseas-request-1",
        strategy_track="OVERSEAS_US",
        market_profile={
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
        provider_capability={
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
    )
    fixture = load_strategy_track_fixture(write(tmp_path, "strategy_track_fixture.json", strategy_track_fixture_payload([overseas])))
    request = fixture.strategy_requests[0]
    assert request.strategy_track.value == "OVERSEAS_US"
    assert request.provider_capability.status.value == "SIMULATION_ONLY"


def test_strategy_track_fixture_requires_explicit_json_file(tmp_path):
    with pytest.raises(ValueError, match="JSON"):
        load_strategy_track_fixture(write(tmp_path, "strategy_track_fixture.txt", strategy_track_fixture_payload()))


def test_strategy_track_fixture_rejects_missing_track(tmp_path):
    payload = strategy_track_fixture_payload()
    del payload["strategy_requests"][0]["strategy_track"]
    with pytest.raises(ValueError, match="strategy_track"):
        load_strategy_track_fixture(write(tmp_path, "strategy_track_fixture.json", payload))


def test_strategy_track_fixture_rejects_ambiguous_track_candidates(tmp_path):
    payload = strategy_track_fixture_payload([strategy_track_request_payload(strategy_track_candidates=["DOMESTIC_KR", "OVERSEAS_US"])])
    with pytest.raises(ValueError, match="ambiguous"):
        load_strategy_track_fixture(write(tmp_path, "strategy_track_fixture.json", payload))


def test_strategy_track_fixture_rejects_invalid_provider_capability(tmp_path):
    payload = strategy_track_fixture_payload([
        strategy_track_request_payload(
            provider_capability={
                "provider_id": "KIWOOM",
                "track": "DOMESTIC_KR",
                "supported_markets": ["KRX"],
                "supported_asset_types": ["STOCK"],
                "domestic_support": False,
                "overseas_support": True,
                "realtime_support": True,
                "order_support": False,
                "account_support": False,
                "status": "AVAILABLE_DOMESTIC_ONLY",
            }
        )
    ])
    with pytest.raises(ValueError, match="provider capability"):
        load_strategy_track_fixture(write(tmp_path, "strategy_track_fixture.json", payload))


def test_strategy_track_fixture_rejects_domestic_overseas_assumption_leakage(tmp_path):
    payload = strategy_track_fixture_payload([
        strategy_track_request_payload(
            market_profile={
                "market_id": "KRX",
                "country": "KR",
                "base_currency": "KRW",
                "exchange_session_profile": "KRX_REGULAR",
                "trading_hours": "09:00-15:30 Asia/Seoul",
                "settlement_cash_availability": "T+2 domestic placeholder",
                "fee_tax_profile_reference": "fee_tax/overseas_us.json",
                "realtime_data_profile_reference": "realtime/domestic_kr.json",
                "provider_capability_reference": "providers/kiwoom_domestic_kr.json",
                "fx_reference": "USD/KRW",
            }
        )
    ])
    with pytest.raises(ValueError, match="cross-track"):
        load_strategy_track_fixture(write(tmp_path, "strategy_track_fixture.json", payload))
