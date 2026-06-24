import json

from stock_risk_mcp.cli import main
from tests.test_position_sizing_models import position_sizing_payload


def write(path, payload):
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def run(capsys, args):
    main(args)
    return json.loads(capsys.readouterr().out)


def test_position_sizing_cli_commands_output_expected_reports(tmp_path, capsys):
    fixture = write(tmp_path / "position_sizing_fixture.json", position_sizing_payload())
    check = run(capsys, ["position-sizing-check", "--fixture-file", str(fixture)])
    summary = run(capsys, ["position-sizing-summary-report", "--fixture-file", str(fixture)])
    stop = run(capsys, ["stop-distance-report", "--fixture-file", str(fixture)])
    budget = run(capsys, ["risk-budget-report", "--fixture-file", str(fixture)])
    readiness = run(capsys, ["position-sizing-data-readiness-report", "--fixture-file", str(fixture)])
    quantity = run(capsys, ["position-quantity-notional-report", "--fixture-file", str(fixture)])
    cost = run(capsys, ["position-cost-assumption-report", "--fixture-file", str(fixture)])
    regime = run(capsys, ["market-regime-sizing-adjustment-report", "--fixture-file", str(fixture)])
    inverse = run(capsys, ["inverse-hedge-sizing-report", "--fixture-file", str(fixture)])
    boundary = run(capsys, ["position-sizing-boundary-violation-report", "--fixture-file", str(fixture)])
    gap = run(capsys, ["position-sizing-gap-report", "--fixture-file", str(fixture)])

    assert check["decision"] in {"SIZE_READY", "REDUCE_SIZE", "CASH_LIMITED", "RISK_BUDGET_LIMITED", "WATCH_ONLY", "DATA_GAP", "GAP", "BLOCKED", "REJECTED"}
    for report in (summary, stop, budget, readiness, quantity, cost, regime, inverse, boundary, gap):
        assert report["report_only"] is True


def test_position_sizing_cli_missing_fixture_is_json_safe(tmp_path, capsys):
    result = run(capsys, ["position-sizing-check", "--fixture-file", str(tmp_path / "missing.json")])
    assert result["status"] == "FAILED"
    assert result["errors"]


def test_position_sizing_cli_rejects_remote_or_parquet_paths(capsys):
    remote = run(capsys, ["position-sizing-summary-report", "--fixture-file", "https://example.com/position_sizing.json"])
    parquet = run(capsys, ["position-sizing-summary-report", "--fixture-file", "position_sizing.parquet"])
    assert remote["status"] == "FAILED"
    assert parquet["status"] == "FAILED"
