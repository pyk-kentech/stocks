import json

from stock_risk_mcp.cli import main
from tests.test_training_pipeline_promotion_models import training_pipeline_promotion_payload


def write(path, payload):
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def run(capsys, args):
    main(args)
    return json.loads(capsys.readouterr().out)


def test_training_pipeline_promotion_cli_commands_output_expected_reports(tmp_path, capsys):
    fixture_file = write(tmp_path / "training_pipeline_promotion_fixture.json", training_pipeline_promotion_payload())
    check = run(capsys, ["training-pipeline-promotion-check", "--fixture-file", str(fixture_file)])
    eligibility = run(capsys, ["training-dataset-eligibility-report", "--fixture-file", str(fixture_file)])
    dependency = run(capsys, ["training-dependency-report", "--fixture-file", str(fixture_file)])
    risk = run(capsys, ["training-leakage-overfit-risk-report", "--fixture-file", str(fixture_file)])
    repro = run(capsys, ["training-reproducibility-report", "--fixture-file", str(fixture_file)])
    artifact = run(capsys, ["model-artifact-policy-report", "--fixture-file", str(fixture_file)])
    promotion = run(capsys, ["model-promotion-readiness-report", "--fixture-file", str(fixture_file)])
    assert check["decision"] in {"TRAINING_READY", "PAPER_CANDIDATE", "PROMOTION_GAP"}
    assert eligibility["report_only"] is True
    assert dependency["report_only"] is True
    assert risk["report_only"] is True
    assert repro["report_only"] is True
    assert artifact["report_only"] is True
    assert promotion["report_only"] is True


def test_training_pipeline_promotion_cli_missing_fixture_is_json_safe(tmp_path, capsys):
    result = run(capsys, ["training-pipeline-promotion-check", "--fixture-file", str(tmp_path / "missing.json")])
    assert result["status"] == "FAILED"
    assert result["errors"]


def test_training_pipeline_promotion_cli_rejects_remote_or_parquet_paths(capsys):
    remote = run(capsys, ["training-dataset-eligibility-report", "--fixture-file", "https://example.com/training.json"])
    parquet = run(capsys, ["training-dataset-eligibility-report", "--fixture-file", "training.parquet"])
    assert remote["status"] == "FAILED"
    assert parquet["status"] == "FAILED"
