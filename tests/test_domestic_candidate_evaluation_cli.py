import json

from stock_risk_mcp.cli import main
from tests.test_domestic_candidate_evaluation_fixture import (
    domestic_candidate_evaluation_fixture_payload,
)
from tests.test_domestic_realtime_fixture import write


def run(capsys, args):
    main(args)
    return json.loads(capsys.readouterr().out)


def test_domestic_candidate_evaluation_cli_commands_return_json_safe_outputs(tmp_path, capsys):
    fixture_file = write(
        tmp_path,
        "domestic_candidate_evaluation_fixture.json",
        domestic_candidate_evaluation_fixture_payload(),
    )
    eval_file = tmp_path / "evaluation.json"
    gap_file = tmp_path / "gap.json"
    safety_file = tmp_path / "safety.json"
    validated = run(capsys, ["domestic-candidate-evaluation-config-validate", "--fixture-file", str(fixture_file)])
    evaluated = run(capsys, ["domestic-candidate-evaluate", "--fixture-file", str(fixture_file), "--output-file", str(eval_file)])
    gap = run(capsys, ["domestic-candidate-evaluation-gap-report", "--fixture-file", str(fixture_file), "--output-file", str(gap_file)])
    safety = run(capsys, ["domestic-candidate-evaluation-safety-report", "--fixture-file", str(fixture_file), "--output-file", str(safety_file)])
    assert validated["status"] == "COMPLETED"
    assert evaluated["status"] == "COMPLETED"
    assert gap["status"] == "COMPLETED"
    assert safety["status"] == "COMPLETED"


def test_domestic_candidate_evaluation_cli_invalid_fixture_is_json_safe(tmp_path, capsys):
    result = run(capsys, ["domestic-candidate-evaluation-config-validate", "--fixture-file", str(tmp_path / "missing.json")])
    assert result["status"] == "FAILED"
    assert result["errors"]
