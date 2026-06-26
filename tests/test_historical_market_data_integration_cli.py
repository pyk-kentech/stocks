import json

from stock_risk_mcp.cli import run_command
from tests.test_historical_market_data_models import historical_market_data_payload, write_manual_daily_payload


def test_historical_market_data_cli_reports_build_from_fixture(tmp_path):
    manual_file = tmp_path / "manual_daily.json"
    write_manual_daily_payload(manual_file)
    fixture_file = tmp_path / "historical_market_data_fixture.json"
    fixture_file.write_text(
        json.dumps(
            historical_market_data_payload(
                store_root=str(tmp_path / "normalized"),
                raw_lake_root=str(tmp_path / "raw_lake"),
                manual_payload_path=str(manual_file),
            )
        ),
        encoding="utf-8",
    )

    parser = __import__("stock_risk_mcp.cli", fromlist=["build_command_parser"]).build_command_parser()

    args = parser.parse_args(["historical-market-data-normalized-manifest", "--fixture-file", str(fixture_file)])
    result = run_command(args)
    assert result["row_count"] == 3

    args = parser.parse_args(["historical-market-data-v10-integration-report", "--fixture-file", str(fixture_file)])
    result = run_command(args)
    assert result["price_history_rows_ready"] is True

    args = parser.parse_args(["historical-market-data-strategy-research-readiness-report", "--fixture-file", str(fixture_file)])
    result = run_command(args)
    assert len(result["rows"]) >= 5
