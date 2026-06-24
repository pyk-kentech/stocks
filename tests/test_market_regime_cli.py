import json

from stock_risk_mcp.cli import main
from tests.test_market_regime_models import market_regime_payload


def write(path, payload):
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def run(capsys, args):
    main(args)
    return json.loads(capsys.readouterr().out)


def test_market_regime_cli_commands_output_expected_reports(tmp_path, capsys):
    fixture = write(tmp_path / "market_regime_fixture.json", market_regime_payload())
    check = run(capsys, ["market-regime-check", "--fixture-file", str(fixture)])
    summary = run(capsys, ["market-regime-summary-report", "--fixture-file", str(fixture)])
    snapshot = run(capsys, ["market-regime-input-snapshot-report", "--fixture-file", str(fixture)])
    risk = run(capsys, ["risk-appetite-report", "--fixture-file", str(fixture)])
    direction = run(capsys, ["market-direction-regime-report", "--fixture-file", str(fixture)])
    vol = run(capsys, ["volatility-regime-report", "--fixture-file", str(fixture)])
    stress = run(capsys, ["fx-rate-dollar-stress-report", "--fixture-file", str(fixture)])
    conflict = run(capsys, ["cross-asset-conflict-report", "--fixture-file", str(fixture)])
    constraint = run(capsys, ["market-regime-downstream-constraint-report", "--fixture-file", str(fixture)])
    feature = run(capsys, ["market-regime-training-feature-report", "--fixture-file", str(fixture)])
    gap = run(capsys, ["market-regime-gap-report", "--fixture-file", str(fixture)])
    assert check["decision"] in {"REGIME_READY", "TRAINING_FEATURE_READY", "GAP", "BLOCKED", "RESEARCH_ONLY", "REJECTED"}
    assert summary["report_only"] is True
    assert snapshot["report_only"] is True
    assert risk["report_only"] is True
    assert direction["report_only"] is True
    assert vol["report_only"] is True
    assert stress["report_only"] is True
    assert conflict["report_only"] is True
    assert constraint["report_only"] is True
    assert feature["report_only"] is True
    assert gap["report_only"] is True


def test_market_regime_cli_missing_fixture_is_json_safe(tmp_path, capsys):
    result = run(capsys, ["market-regime-check", "--fixture-file", str(tmp_path / "missing.json")])
    assert result["status"] == "FAILED"
    assert result["errors"]


def test_market_regime_cli_rejects_remote_or_parquet_paths(capsys):
    remote = run(capsys, ["market-regime-summary-report", "--fixture-file", "https://example.com/market_regime.json"])
    parquet = run(capsys, ["market-regime-summary-report", "--fixture-file", "market_regime.parquet"])
    assert remote["status"] == "FAILED"
    assert parquet["status"] == "FAILED"
