import json

from stock_risk_mcp.cli import main
from tests.test_strategy_track_fixture import strategy_track_fixture_payload, strategy_track_request_payload, write


def run(capsys, args):
    main(args)
    return json.loads(capsys.readouterr().out)


def test_strategy_track_cli_commands_return_json_safe_outputs(tmp_path, capsys):
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
    fixture_file = write(tmp_path, "strategy_track_fixture.json", strategy_track_fixture_payload([domestic, overseas]))
    output_file = tmp_path / "strategy_track_report.json"
    validated = run(capsys, ["strategy-track-profile-validate", "--fixture-file", str(fixture_file), "--output-file", str(output_file)])
    shown = run(capsys, ["strategy-track-profile-show", "--output-file", str(output_file)])
    compared = run(capsys, ["strategy-track-compare", "--fixture-file", str(fixture_file)])
    assert validated["status"] == "COMPLETED"
    assert shown["summary"]["request_count"] == 2
    assert compared["comparison_count"] == 1


def test_strategy_track_cli_invalid_fixture_is_json_safe(tmp_path, capsys):
    result = run(capsys, ["strategy-track-profile-validate", "--fixture-file", str(tmp_path / "missing.json")])
    assert result["status"] == "FAILED"
    assert result["errors"]
