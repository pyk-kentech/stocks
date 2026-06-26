import json

from stock_risk_mcp.cli import run_command
from tests.test_offline_strategy_models import offline_strategy_rows_payload


def test_offline_strategy_cli_reports_build_from_fixture(tmp_path):
    fixture_file = tmp_path / "offline_strategy_fixture.json"
    fixture_file.write_text(
        json.dumps(
            {
                "pipeline_id": "offline-strategy-test",
                "dataset_id": "offline-strategy-test",
                "ohlcv_rows": offline_strategy_rows_payload(),
            }
        ),
        encoding="utf-8",
    )
    parser = __import__("stock_risk_mcp.cli", fromlist=["build_command_parser"]).build_command_parser()

    args = parser.parse_args(["offline-strategy-template-catalog-report", "--fixture-file", str(fixture_file)])
    result = run_command(args)
    assert len(result) >= 4

    args = parser.parse_args(["offline-strategy-promotion-gate-report", "--fixture-file", str(fixture_file)])
    result = run_command(args)
    assert len(result) >= 1
