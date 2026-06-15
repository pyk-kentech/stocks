import json

from stock_risk_mcp.cli import main
from tests.test_market_discovery_fixture import payload, write_json


def run(capsys, args):
    main(args)
    return json.loads(capsys.readouterr().out)


def test_market_discovery_run_output_and_show(tmp_path, capsys):
    fixture = write_json(tmp_path, payload())
    output = tmp_path / "result.json"

    summary = run(capsys, [
        "market-discovery-run", "--fixture-file", str(fixture),
        "--output-file", str(output),
    ])
    shown = run(capsys, ["market-discovery-show", "--output-file", str(output)])
    stdout = run(capsys, ["market-discovery-run", "--fixture-file", str(fixture)])

    assert summary["status"] == "COMPLETED"
    assert summary["summary_counts"] == {"DISCOVER": 1, "WATCH": 0, "EXCLUDE": 0}
    assert shown["metadata_json"]["advisory_only"] is True
    assert stdout["candidates"][0]["ticker"] == "ABC"


def test_market_discovery_invalid_fixture_is_json_safe(tmp_path, capsys):
    result = run(capsys, [
        "market-discovery-run", "--fixture-file", str(tmp_path / "missing.json"),
    ])
    assert result["status"] == "FAILED"
    assert result["errors"]
