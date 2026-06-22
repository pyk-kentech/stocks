import json

import pytest

from stock_risk_mcp.cli import main
from tests.test_historical_paper_trading_engine import _engine_payload


def write(path, payload):
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def run(capsys, args):
    main(args)
    return json.loads(capsys.readouterr().out)


def test_historical_paper_trading_cli_commands_return_paper_only_json_outputs(tmp_path, capsys):
    fixture_file = write(tmp_path / "historical_paper_trading_fixture.json", _engine_payload())
    run_file = tmp_path / "historical_paper_trading_run.json"
    performance_file = tmp_path / "historical_paper_trading_performance.json"
    safety_file = tmp_path / "historical_paper_trading_safety.json"
    gap_file = tmp_path / "historical_paper_trading_gap.json"

    run_result = run(
        capsys,
        ["historical-paper-trading-run", "--fixture-file", str(fixture_file), "--output-file", str(run_file)],
    )
    performance_result = run(
        capsys,
        ["historical-paper-trading-performance-report", "--fixture-file", str(fixture_file), "--output-file", str(performance_file)],
    )
    safety_result = run(
        capsys,
        ["historical-paper-trading-safety-report", "--fixture-file", str(fixture_file), "--output-file", str(safety_file)],
    )
    gap_result = run(
        capsys,
        ["historical-paper-trading-gap-report", "--fixture-file", str(fixture_file), "--output-file", str(gap_file)],
    )

    assert run_result["status"] == "COMPLETED"
    assert performance_result["status"] == "COMPLETED"
    assert safety_result["status"] == "COMPLETED"
    assert gap_result["status"] == "COMPLETED"

    run_json = json.loads(run_file.read_text(encoding="utf-8"))
    performance_json = json.loads(performance_file.read_text(encoding="utf-8"))
    safety_json = json.loads(safety_file.read_text(encoding="utf-8"))
    gap_json = json.loads(gap_file.read_text(encoding="utf-8"))

    assert run_json["paper_only"] is True
    assert run_json["simulated_only"] is True
    assert run_json["non_executable"] is True
    assert performance_json["paper_only"] is True
    assert performance_json["simulated_only"] is True
    assert safety_json["paper_only"] is True
    assert safety_json["no_real_order"] is True
    assert safety_json["no_real_order_intent"] is True
    assert gap_json["paper_only"] is True
    assert "PAPER_TRADING_PLAN_GENERATED" in gap_json["gap_categories"]


@pytest.mark.parametrize(
    "command",
    [
        "historical-paper-trading-run",
        "historical-paper-trading-performance-report",
        "historical-paper-trading-safety-report",
        "historical-paper-trading-gap-report",
    ],
)
def test_historical_paper_trading_cli_missing_fixture_is_json_safe(command, tmp_path, capsys):
    result = run(capsys, [command, "--fixture-file", str(tmp_path / "missing.json")])
    assert result["status"] == "FAILED"
    assert result["errors"]


def test_historical_paper_trading_cli_output_has_required_safety_flags(tmp_path, capsys):
    fixture_file = write(tmp_path / "historical_paper_trading_fixture.json", _engine_payload())

    result = run(capsys, ["historical-paper-trading-safety-report", "--fixture-file", str(fixture_file)])

    assert result["paper_only"] is True
    assert result["simulated_only"] is True
    assert result["non_executable"] is True
    assert result["local_file_only"] is True
    assert result["offline_only"] is True
    assert result["read_only_input"] is True
    assert result["no_network"] is True
    assert result["no_provider_api"] is True
    assert result["no_real_order"] is True
    assert result["no_real_order_intent"] is True
    assert result["no_broker_api"] is True
    assert result["no_account_api"] is True
    assert result["no_order_api"] is True
    assert result["no_kiwoom_api"] is True
    assert result["no_ls_api"] is True
    assert result["no_live_trading"] is True
    assert result["no_live_prod"] is True
    assert result["no_cloud_llm"] is True
    assert result["no_local_llm_runtime"] is True
    assert result["no_external_execution"] is True


def test_historical_paper_trading_cli_output_has_no_real_order_or_metadata(tmp_path, capsys):
    fixture_file = write(tmp_path / "historical_paper_trading_fixture.json", _engine_payload())

    result = run(capsys, ["historical-paper-trading-run", "--fixture-file", str(fixture_file)])
    dumped = json.dumps(result).lower()

    assert "\"real_order_intent\":" not in dumped
    assert "\"broker_order_intent\":" not in dumped
    assert "\"broker_metadata\":" not in dumped
    assert "\"account_metadata\":" not in dumped
    assert "\"kiwoom_metadata\":" not in dumped
    assert "\"ls_metadata\":" not in dumped
    assert "\"network_provider\":" not in dumped
    assert "\"live_trading_marker\":" not in dumped
    assert "\"live_prod_marker\":" not in dumped
    assert "\"parquet_path\":" not in dumped
