import json

from stock_risk_mcp.cli import main
from tests.test_allocation_policy_training_models import allocation_policy_training_payload


def write(path, payload):
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def run(capsys, args):
    main(args)
    return json.loads(capsys.readouterr().out)


def test_allocation_policy_training_cli_commands_output_expected_reports(tmp_path, capsys):
    fixture_file = write(tmp_path / "allocation_policy_training_fixture.json", allocation_policy_training_payload())
    check = run(capsys, ["allocation-policy-training-check", "--fixture-file", str(fixture_file)])
    summary = run(capsys, ["allocation-policy-training-summary-report", "--fixture-file", str(fixture_file)])
    selection = run(capsys, ["regime-action-selection-report", "--fixture-file", str(fixture_file)])
    walk_forward = run(capsys, ["allocation-policy-walk-forward-report", "--fixture-file", str(fixture_file)])
    risk = run(capsys, ["allocation-policy-risk-adjusted-report", "--fixture-file", str(fixture_file)])
    turnover = run(capsys, ["allocation-policy-turnover-slippage-report", "--fixture-file", str(fixture_file)])
    drawdown = run(capsys, ["allocation-policy-drawdown-stability-report", "--fixture-file", str(fixture_file)])
    readiness = run(capsys, ["allocation-policy-promotion-readiness-report", "--fixture-file", str(fixture_file)])
    artifact = run(capsys, ["allocation-policy-artifact-report", "--fixture-file", str(fixture_file)])
    assert check["decision"] in {"TRAINED_OFFLINE", "PAPER_CANDIDATE", "GAP"}
    assert summary["report_only"] is True
    assert selection["report_only"] is True
    assert walk_forward["report_only"] is True
    assert risk["report_only"] is True
    assert turnover["report_only"] is True
    assert drawdown["report_only"] is True
    assert readiness["report_only"] is True
    assert artifact["report_only"] is True


def test_allocation_policy_training_cli_missing_fixture_is_json_safe(tmp_path, capsys):
    result = run(capsys, ["allocation-policy-training-check", "--fixture-file", str(tmp_path / "missing.json")])
    assert result["status"] == "FAILED"
    assert result["errors"]


def test_allocation_policy_training_cli_rejects_remote_or_parquet_paths(capsys):
    remote = run(capsys, ["allocation-policy-training-summary-report", "--fixture-file", "https://example.com/policy.json"])
    parquet = run(capsys, ["allocation-policy-training-summary-report", "--fixture-file", "policy.parquet"])
    assert remote["status"] == "FAILED"
    assert parquet["status"] == "FAILED"
