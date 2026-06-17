import json

from stock_risk_mcp.cli import main
from tests.test_domestic_market_regime_fixture import market_regime_fixture_payload
from tests.test_domestic_realtime_fixture import write


def run(capsys, args):
    main(args)
    return json.loads(capsys.readouterr().out)


def test_domestic_market_regime_cli_commands_return_json_safe_outputs(tmp_path, capsys):
    fixture_file = write(
        tmp_path,
        "domestic_market_regime_fixture.json",
        market_regime_fixture_payload(),
    )
    classification_file = tmp_path / "domestic_market_regime_classification.json"
    report_file = tmp_path / "domestic_market_regime_report.json"
    gap_file = tmp_path / "domestic_market_regime_gap.json"
    safety_file = tmp_path / "domestic_market_regime_safety.json"
    validated = run(capsys, ["domestic-market-regime-config-validate", "--fixture-file", str(fixture_file)])
    classified = run(capsys, ["domestic-market-regime-classify", "--fixture-file", str(fixture_file), "--output-file", str(classification_file)])
    reported = run(capsys, ["domestic-market-regime-report", "--fixture-file", str(fixture_file), "--output-file", str(report_file)])
    gapped = run(capsys, ["domestic-market-regime-gap-report", "--fixture-file", str(fixture_file), "--output-file", str(gap_file)])
    safe = run(capsys, ["domestic-market-regime-safety-report", "--fixture-file", str(fixture_file), "--output-file", str(safety_file)])
    assert validated["status"] == "COMPLETED"
    assert classified["status"] == "COMPLETED"
    assert reported["status"] == "COMPLETED"
    assert gapped["status"] == "COMPLETED"
    assert safe["status"] == "COMPLETED"


def test_domestic_market_regime_cli_invalid_fixture_is_json_safe(tmp_path, capsys):
    result = run(capsys, ["domestic-market-regime-config-validate", "--fixture-file", str(tmp_path / "missing.json")])
    assert result["status"] == "FAILED"
    assert result["errors"]
