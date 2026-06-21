import json

import pytest

from stock_risk_mcp.cli import main
from tests.test_historical_model_training_engine import (
    _engine_payload,
    _set_split_manifest_from_records,
    _with_records,
)


def write(path, payload):
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def run(capsys, args):
    main(args)
    return json.loads(capsys.readouterr().out)


def test_historical_model_training_cli_commands_return_report_only_json_outputs(tmp_path, capsys):
    fixture_file = write(
        tmp_path / "historical_model_training_fixture.json",
        _set_split_manifest_from_records(_with_records(_engine_payload(), 6)),
    )
    plan_file = tmp_path / "historical_model_training_plan_check.json"
    train_file = tmp_path / "historical_model_training_sandbox.json"
    evaluation_file = tmp_path / "historical_model_evaluation_report.json"
    artifact_file = tmp_path / "historical_model_artifact_manifest.json"
    safety_file = tmp_path / "historical_model_training_safety_report.json"

    plan = run(
        capsys,
        ["historical-model-training-plan-check", "--fixture-file", str(fixture_file), "--output-file", str(plan_file)],
    )
    train = run(
        capsys,
        ["historical-model-train-sandbox", "--fixture-file", str(fixture_file), "--output-file", str(train_file)],
    )
    evaluation = run(
        capsys,
        ["historical-model-evaluation-report", "--fixture-file", str(fixture_file), "--output-file", str(evaluation_file)],
    )
    artifact = run(
        capsys,
        ["historical-model-artifact-manifest", "--fixture-file", str(fixture_file), "--output-file", str(artifact_file)],
    )
    safety = run(
        capsys,
        ["historical-model-training-safety-report", "--fixture-file", str(fixture_file), "--output-file", str(safety_file)],
    )

    assert plan["status"] == "COMPLETED"
    assert train["status"] == "COMPLETED"
    assert evaluation["status"] == "COMPLETED"
    assert artifact["status"] == "COMPLETED"
    assert safety["status"] == "COMPLETED"

    plan_json = json.loads(plan_file.read_text(encoding="utf-8"))
    train_json = json.loads(train_file.read_text(encoding="utf-8"))
    evaluation_json = json.loads(evaluation_file.read_text(encoding="utf-8"))
    artifact_json = json.loads(artifact_file.read_text(encoding="utf-8"))
    safety_json = json.loads(safety_file.read_text(encoding="utf-8"))

    assert plan_json["report_only"] is True
    assert plan_json["non_executable"] is True
    assert plan_json["eligible_for_sandbox_training"] is True
    assert train_json["run_report"]["training_executed"] is True
    assert train_json["run_report"]["report_only"] is True
    assert train_json["evaluation_report"]["runtime_trading_signal_present"] is False
    assert train_json["evaluation_report"]["order_candidate_present"] is False
    assert evaluation_json["report_only"] is True
    assert evaluation_json["runtime_trading_signal_present"] is False
    assert evaluation_json["order_candidate_present"] is False
    assert artifact_json["report_only"] is True
    assert artifact_json["non_executable"] is True
    assert artifact_json["offline_only"] is True
    assert safety_json["report_only"] is True
    assert safety_json["no_runtime_trading_signal"] is True
    assert safety_json["no_order_candidate"] is True


@pytest.mark.parametrize(
    "command",
    [
        "historical-model-training-plan-check",
        "historical-model-train-sandbox",
        "historical-model-evaluation-report",
        "historical-model-artifact-manifest",
        "historical-model-training-safety-report",
    ],
)
def test_historical_model_training_cli_missing_fixture_is_json_safe(command, tmp_path, capsys):
    result = run(capsys, [command, "--fixture-file", str(tmp_path / "missing.json")])
    assert result["status"] == "FAILED"
    assert result["errors"]


def test_historical_model_training_cli_preserves_safety_flags(tmp_path, capsys):
    fixture_file = write(
        tmp_path / "historical_model_training_fixture.json",
        _set_split_manifest_from_records(_with_records(_engine_payload(), 6)),
    )

    result = run(capsys, ["historical-model-training-safety-report", "--fixture-file", str(fixture_file)])

    assert result["read_only"] is True
    assert result["report_only"] is True
    assert result["non_executable"] is True
    assert result["local_file_only"] is True
    assert result["offline_only"] is True
    assert result["no_network"] is True
    assert result["no_provider_api"] is True
    assert result["no_order"] is True
    assert result["no_broker_path"] is True
    assert result["no_live_prod"] is True
    assert result["no_cloud_llm"] is True
    assert result["no_local_llm_runtime"] is True
    assert result["no_runtime_trading_signal"] is True
    assert result["no_order_candidate"] is True


def test_historical_model_training_cli_preserves_report_only_training_boundary(tmp_path, capsys):
    fixture_file = write(
        tmp_path / "historical_model_training_fixture.json",
        _set_split_manifest_from_records(_with_records(_engine_payload(), 6)),
    )

    result = run(capsys, ["historical-model-train-sandbox", "--fixture-file", str(fixture_file)])

    assert result["run_report"]["training_executed"] is True
    assert result["run_report"]["report_only"] is True
    assert result["evaluation_report"]["runtime_trading_signal_present"] is False
    assert result["evaluation_report"]["order_candidate_present"] is False
    assert result["artifact_manifest"]["no_runtime_trading_signal"] is True
    assert result["artifact_manifest"]["no_order_candidate"] is True
