import json

from stock_risk_mcp.cli import main
from tests.test_local_model_benchmark_fixture import (
    benchmark_fixture_payload,
    candidate_output_fixture_payload,
    write,
)


def run(capsys, args):
    main(args)
    return json.loads(capsys.readouterr().out)


def test_local_model_benchmark_commands_return_json_safe_outputs(tmp_path, capsys):
    benchmark_file = write(tmp_path, "local_model_benchmark_fixture.json", benchmark_fixture_payload())
    candidate_file = write(tmp_path, "local_model_candidate_output_fixture.json", candidate_output_fixture_payload())
    output_file = tmp_path / "local_model_benchmark_report.json"
    summary = run(capsys, [
        "local-model-benchmark-run",
        "--fixture-file",
        str(benchmark_file),
        "--candidate-output-file",
        str(candidate_file),
        "--output-file",
        str(output_file),
    ])
    shown = run(capsys, ["local-model-benchmark-show", "--output-file", str(output_file)])
    ranked = run(capsys, ["local-model-candidates-rank", "--benchmark-report-file", str(output_file)])
    assert summary["status"] == "COMPLETED"
    assert shown["summary_counts"]["eligible_count"] == 1
    assert ranked["ranked_candidates"][0]["candidate_model_id"] == "mock-qwen-7b-q4"


def test_local_model_benchmark_invalid_fixture_is_json_safe(tmp_path, capsys):
    result = run(capsys, [
        "local-model-benchmark-run",
        "--fixture-file",
        str(tmp_path / "missing.json"),
        "--candidate-output-file",
        str(tmp_path / "missing-candidate.json"),
    ])
    assert result["status"] == "FAILED"
    assert result["errors"]
