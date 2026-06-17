from stock_risk_mcp.strategy_track_engine import compare_strategy_track_requests, validate_strategy_track_fixture
from tests.test_strategy_track_fixture import strategy_track_fixture_payload, strategy_track_request_payload


def test_strategy_track_engine_validates_requests_and_metadata(tmp_path):
    fixture = strategy_track_fixture_payload()
    report = validate_strategy_track_fixture(fixture)
    assert report.summary["request_count"] == 1
    assert report.metadata_json["broker_api_called"] is False
    assert report.metadata_json["live_or_prod_used"] is False


def test_strategy_track_compare_reports_track_specific_differences():
    domestic = strategy_track_request_payload()
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
    report = compare_strategy_track_requests([domestic, overseas])
    assert report.comparisons[0]["changed_fields"]
    assert "base_currency" in report.comparisons[0]["changed_fields"]
    assert "provider_status" in report.comparisons[0]["changed_fields"]
