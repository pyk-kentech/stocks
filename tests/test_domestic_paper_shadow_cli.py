import json

from stock_risk_mcp.cli import main
from tests.test_domestic_paper_shadow_fixture import paper_shadow_fixture_payload
from tests.test_domestic_realtime_fixture import write


def run(capsys, args):
    main(args)
    return json.loads(capsys.readouterr().out)


def test_domestic_paper_shadow_cli_commands_return_json_safe_outputs(tmp_path, capsys):
    fixture_file = write(
        tmp_path,
        "domestic_paper_shadow_fixture.json",
        paper_shadow_fixture_payload(tmp_path),
    )
    journal_file = tmp_path / "paper_shadow_journal.json"
    review_file = tmp_path / "paper_shadow_review.json"
    safety_file = tmp_path / "paper_shadow_safety.json"
    validated = run(capsys, ["domestic-paper-shadow-config-validate", "--fixture-file", str(fixture_file)])
    journaled = run(capsys, ["domestic-paper-shadow-journal-build", "--fixture-file", str(fixture_file), "--output-file", str(journal_file)])
    reviewed = run(capsys, ["domestic-paper-shadow-review-report", "--fixture-file", str(fixture_file), "--output-file", str(review_file)])
    safety = run(capsys, ["domestic-paper-shadow-safety-report", "--fixture-file", str(fixture_file), "--output-file", str(safety_file)])
    assert validated["status"] == "COMPLETED"
    assert journaled["status"] == "COMPLETED"
    assert reviewed["status"] == "COMPLETED"
    assert safety["status"] == "COMPLETED"


def test_domestic_paper_shadow_cli_invalid_fixture_is_json_safe(tmp_path, capsys):
    result = run(capsys, ["domestic-paper-shadow-config-validate", "--fixture-file", str(tmp_path / "missing.json")])
    assert result["status"] == "FAILED"
    assert result["errors"]
