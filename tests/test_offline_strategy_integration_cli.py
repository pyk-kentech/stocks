import json

import pytest

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


def test_offline_strategy_cli_alias_reports_build_from_fixture(tmp_path):
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

    alias_commands = [
        "offline-strategy-parameter-search-plan-report",
        "offline-strategy-training-launch-plan-report",
        "offline-strategy-walk-forward-plan-report",
        "offline-strategy-backtest-smoke-report",
        "offline-strategy-research-readiness-report",
    ]
    for command in alias_commands:
        args = parser.parse_args([command, "--fixture-file", str(fixture_file)])
        result = run_command(args)
        assert result


def test_cli_main_help_uses_command_parser(capsys):
    from stock_risk_mcp.cli import main

    with pytest.raises(SystemExit) as exc:
        main(["--help"])

    assert exc.value.code == 0
    output = capsys.readouterr().out
    assert "historical-market-data-real-capture-preflight-report" in output
    assert "offline-strategy-template-catalog-report" in output
    assert "offline-strategy-parameter-search-plan-report" in output
