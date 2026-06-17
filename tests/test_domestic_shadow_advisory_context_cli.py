import json

from stock_risk_mcp.cli import main
from tests.test_domestic_realtime_fixture import write
from tests.test_domestic_shadow_advisory_context_fixture import shadow_advisory_context_fixture_payload


def run(capsys, args):
    main(args)
    return json.loads(capsys.readouterr().out)


def test_domestic_shadow_advisory_context_cli_commands_return_json_safe_outputs(tmp_path, capsys):
    fixture_file = write(
        tmp_path,
        "domestic_shadow_advisory_context_fixture.json",
        shadow_advisory_context_fixture_payload(tmp_path),
    )
    bundle_file = tmp_path / "domestic_shadow_advisory_context_bundle.json"
    validate_file = tmp_path / "domestic_shadow_advisory_context_validation.json"
    gap_file = tmp_path / "domestic_shadow_advisory_context_gap.json"
    safety_file = tmp_path / "domestic_shadow_advisory_context_safety.json"
    validated = run(capsys, ["domestic-shadow-advisory-context-config-validate", "--fixture-file", str(fixture_file)])
    bundled = run(capsys, ["domestic-shadow-advisory-context-build", "--fixture-file", str(fixture_file), "--output-file", str(bundle_file)])
    verified = run(capsys, ["domestic-shadow-advisory-context-validate", "--fixture-file", str(fixture_file), "--output-file", str(validate_file)])
    gapped = run(capsys, ["domestic-shadow-advisory-context-gap-report", "--fixture-file", str(fixture_file), "--output-file", str(gap_file)])
    safe = run(capsys, ["domestic-shadow-advisory-context-safety-report", "--fixture-file", str(fixture_file), "--output-file", str(safety_file)])
    assert validated["status"] == "COMPLETED"
    assert bundled["status"] == "COMPLETED"
    assert verified["status"] == "COMPLETED"
    assert gapped["status"] == "COMPLETED"
    assert safe["status"] == "COMPLETED"


def test_domestic_shadow_advisory_context_cli_invalid_fixture_is_json_safe(tmp_path, capsys):
    result = run(capsys, ["domestic-shadow-advisory-context-config-validate", "--fixture-file", str(tmp_path / "missing.json")])
    assert result["status"] == "FAILED"
    assert result["errors"]
