import json

from stock_risk_mcp.cli import main
from tests.test_domestic_realtime_fixture import write
from tests.test_domestic_shadow_outcome_fixture import shadow_outcome_fixture_payload


def run(capsys, args):
    main(args)
    return json.loads(capsys.readouterr().out)


def test_domestic_shadow_outcome_cli_commands_return_json_safe_outputs(tmp_path, capsys):
    fixture_file = write(
        tmp_path,
        "domestic_shadow_outcome_fixture.json",
        shadow_outcome_fixture_payload(tmp_path),
    )
    label_file = tmp_path / "domestic_shadow_outcome_labels.json"
    review_file = tmp_path / "domestic_shadow_outcome_review.json"
    safety_file = tmp_path / "domestic_shadow_outcome_safety.json"
    validated = run(capsys, ["domestic-shadow-outcome-config-validate", "--fixture-file", str(fixture_file)])
    labeled = run(capsys, ["domestic-shadow-outcome-label", "--fixture-file", str(fixture_file), "--output-file", str(label_file)])
    reviewed = run(capsys, ["domestic-shadow-outcome-review-report", "--fixture-file", str(fixture_file), "--output-file", str(review_file)])
    safety = run(capsys, ["domestic-shadow-outcome-safety-report", "--fixture-file", str(fixture_file), "--output-file", str(safety_file)])
    assert validated["status"] == "COMPLETED"
    assert labeled["status"] == "COMPLETED"
    assert reviewed["status"] == "COMPLETED"
    assert safety["status"] == "COMPLETED"


def test_domestic_shadow_outcome_cli_invalid_fixture_is_json_safe(tmp_path, capsys):
    result = run(capsys, ["domestic-shadow-outcome-config-validate", "--fixture-file", str(tmp_path / "missing.json")])
    assert result["status"] == "FAILED"
    assert result["errors"]
