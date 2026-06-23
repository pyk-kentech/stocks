import json

from stock_risk_mcp.cli import main
from tests.test_regime_allocation_learning_models import regime_allocation_learning_payload


def write(path, payload):
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def run(capsys, args):
    main(args)
    return json.loads(capsys.readouterr().out)


def test_regime_allocation_learning_cli_commands_output_expected_reports(tmp_path, capsys):
    fixture_file = write(tmp_path / "regime_allocation_learning_fixture.json", regime_allocation_learning_payload())
    check = run(capsys, ["regime-allocation-learning-check", "--fixture-file", str(fixture_file)])
    feature = run(capsys, ["regime-feature-report", "--fixture-file", str(fixture_file)])
    action = run(capsys, ["allocation-action-candidate-report", "--fixture-file", str(fixture_file)])
    hedge = run(capsys, ["hedge-inverse-eligibility-report", "--fixture-file", str(fixture_file)])
    outcome = run(capsys, ["forward-outcome-label-report", "--fixture-file", str(fixture_file)])
    reward = run(capsys, ["allocation-reward-scoring-report", "--fixture-file", str(fixture_file)])
    leakage = run(capsys, ["regime-allocation-leakage-report", "--fixture-file", str(fixture_file)])
    readiness = run(capsys, ["regime-allocation-dataset-readiness-report", "--fixture-file", str(fixture_file)])
    assert check["decision"] in {"RESEARCH_READY", "TRAINING_READY", "GAP"}
    assert feature["report_only"] is True
    assert action["report_only"] is True
    assert hedge["report_only"] is True
    assert outcome["report_only"] is True
    assert reward["report_only"] is True
    assert leakage["report_only"] is True
    assert readiness["report_only"] is True


def test_regime_allocation_learning_cli_missing_fixture_is_json_safe(tmp_path, capsys):
    result = run(capsys, ["regime-allocation-learning-check", "--fixture-file", str(tmp_path / "missing.json")])
    assert result["status"] == "FAILED"
    assert result["errors"]


def test_regime_allocation_learning_cli_rejects_remote_or_parquet_paths(capsys):
    remote = run(capsys, ["regime-feature-report", "--fixture-file", "https://example.com/regime.json"])
    parquet = run(capsys, ["regime-feature-report", "--fixture-file", "regime.parquet"])
    assert remote["status"] == "FAILED"
    assert parquet["status"] == "FAILED"
