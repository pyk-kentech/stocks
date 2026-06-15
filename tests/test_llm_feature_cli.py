import json

from stock_risk_mcp.cli import main
from tests.test_llm_feature_fixture import outcome_payload, signal_payload, write


def run(capsys, args):
    main(args)
    return json.loads(capsys.readouterr().out)


def test_llm_feature_store_evaluate_and_show_commands(tmp_path, capsys):
    signals = write(tmp_path, "signals.json", signal_payload())
    outcomes = write(tmp_path, "outcomes.json", outcome_payload())
    output = tmp_path / "report.json"

    feature = run(capsys, ["llm-feature-store-run", "--signal-fixture-file", str(signals)])
    summary = run(capsys, [
        "llm-signal-evaluate", "--signal-fixture-file", str(signals),
        "--outcome-fixture-file", str(outcomes), "--output-file", str(output),
    ])
    shown = run(capsys, ["llm-signal-evaluation-show", "--output-file", str(output)])

    assert feature["metadata_json"]["llm_called"] is False
    assert summary["status"] == "COMPLETED"
    assert shown["metadata_json"]["orders_created"] is False


def test_llm_feature_invalid_fixture_is_json_safe(tmp_path, capsys):
    result = run(capsys, ["llm-feature-store-run", "--signal-fixture-file", str(tmp_path / "missing.json")])
    assert result["status"] == "FAILED" and result["errors"]
