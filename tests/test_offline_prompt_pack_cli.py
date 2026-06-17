import json

from stock_risk_mcp.cli import main
from tests.test_offline_prompt_pack_fixture import (
    domestic_trading_task_payload,
    overseas_profitability_task_payload,
    prompt_pack_payload,
    prompt_task_payload,
    write,
)


def run(capsys, args):
    main(args)
    return json.loads(capsys.readouterr().out)


def valid_pack_payload():
    return prompt_pack_payload(tasks=[
        prompt_task_payload(
            task_id="generic-en-1",
            language="ENGLISH",
            domain="MISSING_DATA",
            task_type="IDENTIFY_MISSING_DATA",
            safety_trap_tags=["UNSAFE_INSTRUCTION_REJECTION", "ADVISORY_BOUNDARY_REFUSAL", "JSON_ONLY_RESPONSE_ENFORCEMENT"],
        ),
        prompt_task_payload(
            task_id="generic-mixed-1",
            language="MIXED",
            domain="ASSUMPTION_CHALLENGE",
            task_type="CHALLENGE_ASSUMPTIONS",
            safety_trap_tags=["UNSAFE_INSTRUCTION_REJECTION", "ADVISORY_BOUNDARY_REFUSAL", "TRACK_MISSING_FAIL_CLOSED"],
        ),
        domestic_trading_task_payload(),
        overseas_profitability_task_payload(),
    ])


def test_offline_prompt_pack_cli_commands_return_json_safe_outputs(tmp_path, capsys):
    fixture_file = write(tmp_path, "offline_prompt_pack_fixture.json", valid_pack_payload())
    validation_output = tmp_path / "prompt_pack_validation.json"
    coverage_output = tmp_path / "prompt_pack_coverage.json"
    gap_output = tmp_path / "prompt_pack_gap.json"
    validated = run(capsys, ["prompt-pack-validate", "--fixture-file", str(fixture_file), "--output-file", str(validation_output)])
    shown = run(capsys, ["prompt-pack-show", "--fixture-file", str(fixture_file)])
    coverage = run(capsys, ["prompt-pack-coverage-report", "--fixture-file", str(fixture_file), "--output-file", str(coverage_output)])
    gap = run(capsys, ["prompt-pack-gap-report", "--fixture-file", str(fixture_file), "--output-file", str(gap_output)])
    assert validated["status"] == "COMPLETED"
    assert shown["prompt_pack_id"] == "offline-prompt-pack-1"
    assert coverage["status"] == "COMPLETED"
    assert gap["status"] == "COMPLETED"


def test_offline_prompt_pack_cli_invalid_fixture_is_json_safe(tmp_path, capsys):
    result = run(capsys, ["prompt-pack-validate", "--fixture-file", str(tmp_path / "missing.json")])
    assert result["status"] == "FAILED"
    assert result["errors"]
