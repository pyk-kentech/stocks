import json

from stock_risk_mcp.cli import main
from tests.test_local_llm_advisory_fixture import fixture_payload, write


def run(capsys, args):
    main(args)
    return json.loads(capsys.readouterr().out)


def test_local_llm_advisory_run_and_show_commands(tmp_path, capsys):
    fixture_file = write(tmp_path, "local_llm_advisory_fixture.json", fixture_payload())
    output_file = tmp_path / "local_llm_advisory_result.json"
    summary = run(capsys, ["local-llm-advisory-run", "--fixture-file", str(fixture_file), "--output-file", str(output_file)])
    shown = run(capsys, ["local-llm-advisory-show", "--output-file", str(output_file)])
    assert summary["status"] == "COMPLETED"
    assert shown["metadata_json"]["advisory_only"] is True
    assert shown["metadata_json"]["may_create_order"] is False


def test_local_llm_advisory_invalid_fixture_is_json_safe(tmp_path, capsys):
    result = run(capsys, ["local-llm-advisory-run", "--fixture-file", str(tmp_path / "missing.json")])
    assert result["status"] == "FAILED"
    assert result["errors"]
