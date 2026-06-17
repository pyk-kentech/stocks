import json

from stock_risk_mcp.cli import main
from tests.test_market_profit_fixture import (
    market_profit_fixture_payload,
    overseas_market_profit_fixture_payload,
    write,
)


def run(capsys, args):
    main(args)
    return json.loads(capsys.readouterr().out)


def test_market_profit_cli_commands_return_json_safe_outputs(tmp_path, capsys):
    domestic_file = write(tmp_path, "market_profit_domestic_fixture.json", market_profit_fixture_payload())
    overseas_file = write(tmp_path, "market_profit_overseas_fixture.json", overseas_market_profit_fixture_payload())
    compare_file = write(
        tmp_path,
        "compare.json",
        {"fixture_files": [domestic_file.name, overseas_file.name]},
    )
    output_file = tmp_path / "market_profit_report.json"
    validated = run(capsys, ["market-profit-profile-validate", "--fixture-file", str(domestic_file), "--output-file", str(output_file)])
    shown = run(capsys, ["market-profit-estimate", "--fixture-file", str(domestic_file)])
    break_even = run(capsys, ["market-profit-break-even", "--fixture-file", str(domestic_file)])
    compared = run(capsys, ["market-profit-compare-tracks", "--fixture-file", str(compare_file), "--output-file", str(tmp_path / "compare_report.json")])
    assert validated["status"] == "COMPLETED"
    assert shown["check"]["net_profit_estimate"]["expected_net_pnl_amount"] > 0
    assert break_even["break_even_estimate"]["break_even_exit_price"] > 0
    assert compared["status"] == "COMPLETED"


def test_market_profit_cli_invalid_fixture_is_json_safe(tmp_path, capsys):
    result = run(capsys, ["market-profit-profile-validate", "--fixture-file", str(tmp_path / "missing.json")])
    assert result["status"] == "FAILED"
    assert result["errors"]
