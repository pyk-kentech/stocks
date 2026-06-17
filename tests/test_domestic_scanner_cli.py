import json

from stock_risk_mcp.cli import main
from tests.test_domestic_scanner_fixture import domestic_scanner_fixture_payload
from tests.test_domestic_realtime_fixture import write


def run(capsys, args):
    main(args)
    return json.loads(capsys.readouterr().out)


def test_domestic_scanner_cli_commands_return_json_safe_outputs(tmp_path, capsys):
    fixture_file = write(tmp_path, "domestic_scanner_fixture.json", domestic_scanner_fixture_payload())
    candidate_file = tmp_path / "candidates.json"
    watchlist_file = tmp_path / "watchlist.json"
    quality_file = tmp_path / "quality.json"
    validated = run(capsys, ["domestic-scanner-config-validate", "--fixture-file", str(fixture_file)])
    candidates = run(capsys, ["domestic-scanner-candidates", "--fixture-file", str(fixture_file), "--output-file", str(candidate_file)])
    watchlist = run(capsys, ["domestic-scanner-watchlist-plan", "--fixture-file", str(fixture_file), "--output-file", str(watchlist_file)])
    quality = run(capsys, ["domestic-scanner-quality-report", "--fixture-file", str(fixture_file), "--output-file", str(quality_file)])
    assert validated["status"] == "COMPLETED"
    assert candidates["status"] == "COMPLETED"
    assert watchlist["status"] == "COMPLETED"
    assert quality["status"] == "COMPLETED"


def test_domestic_scanner_cli_invalid_fixture_is_json_safe(tmp_path, capsys):
    result = run(capsys, ["domestic-scanner-config-validate", "--fixture-file", str(tmp_path / "missing.json")])
    assert result["status"] == "FAILED"
    assert result["errors"]
