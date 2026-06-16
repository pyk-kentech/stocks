import json

from stock_risk_mcp.cli import main
from tests.test_paper_eval_fixture import fixture_payload, write


def run(capsys, args):
    main(args)
    return json.loads(capsys.readouterr().out)


def test_paper_eval_run_and_show_commands(tmp_path, capsys):
    fixture_file = write(tmp_path, "paper_eval_fixture.json", fixture_payload())
    output_file = tmp_path / "paper_eval_report.json"

    summary = run(capsys, ["paper-eval-run", "--fixture-file", str(fixture_file), "--output-file", str(output_file)])
    shown = run(capsys, ["paper-eval-show", "--output-file", str(output_file)])

    assert summary["status"] == "COMPLETED"
    assert shown["metadata_json"]["paper_only"] is True
    assert shown["metadata_json"]["orders_submitted"] is False


def test_paper_eval_invalid_fixture_is_json_safe(tmp_path, capsys):
    result = run(capsys, ["paper-eval-run", "--fixture-file", str(tmp_path / "missing.json")])
    assert result["status"] == "FAILED"
    assert result["errors"]
