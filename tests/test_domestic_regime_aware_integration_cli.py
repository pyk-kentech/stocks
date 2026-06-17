import json

from stock_risk_mcp.cli import main
from tests.test_domestic_regime_aware_integration_fixture import (
    regime_aware_integration_fixture_payload,
)
from tests.test_domestic_realtime_fixture import write


def run(capsys, args):
    main(args)
    return json.loads(capsys.readouterr().out)


def test_domestic_regime_aware_integration_cli_commands_return_json_safe_outputs(tmp_path, capsys):
    fixture_file = write(
        tmp_path,
        "domestic_regime_aware_integration_fixture.json",
        regime_aware_integration_fixture_payload(tmp_path),
    )
    build_file = tmp_path / "domestic_regime_aware_integration_build.json"
    report_file = tmp_path / "domestic_regime_aware_integration_report.json"
    gap_file = tmp_path / "domestic_regime_aware_integration_gap.json"
    safety_file = tmp_path / "domestic_regime_aware_integration_safety.json"
    validated = run(capsys, ["domestic-regime-aware-integration-config-validate", "--fixture-file", str(fixture_file)])
    built = run(capsys, ["domestic-regime-aware-integration-build", "--fixture-file", str(fixture_file), "--output-file", str(build_file)])
    reported = run(capsys, ["domestic-regime-aware-integration-report", "--fixture-file", str(fixture_file), "--output-file", str(report_file)])
    gapped = run(capsys, ["domestic-regime-aware-gap-report", "--fixture-file", str(fixture_file), "--output-file", str(gap_file)])
    safe = run(capsys, ["domestic-regime-aware-safety-report", "--fixture-file", str(fixture_file), "--output-file", str(safety_file)])
    assert validated["status"] == "COMPLETED"
    assert built["status"] == "COMPLETED"
    assert reported["status"] == "COMPLETED"
    assert gapped["status"] == "COMPLETED"
    assert safe["status"] == "COMPLETED"


def test_domestic_regime_aware_integration_cli_invalid_fixture_is_json_safe(tmp_path, capsys):
    result = run(capsys, ["domestic-regime-aware-integration-config-validate", "--fixture-file", str(tmp_path / "missing.json")])
    assert result["status"] == "FAILED"
    assert result["errors"]
