import json

import pytest

from stock_risk_mcp.cli import main
from tests.test_historical_dataset_readiness_engine import (
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


def test_historical_dataset_readiness_cli_commands_return_report_only_json_outputs(tmp_path, capsys):
    fixture_file = write(
        tmp_path / "historical_dataset_readiness_fixture.json",
        _set_split_manifest_from_records(_with_records(_engine_payload(), 6)),
    )
    readiness_file = tmp_path / "historical_dataset_readiness_report.json"
    split_file = tmp_path / "historical_dataset_split_quality_report.json"
    imbalance_file = tmp_path / "historical_dataset_imbalance_report.json"
    baseline_file = tmp_path / "historical_dataset_baseline_evaluation.json"
    safety_file = tmp_path / "historical_dataset_readiness_safety_report.json"

    readiness = run(
        capsys,
        ["historical-dataset-readiness-report", "--fixture-file", str(fixture_file), "--output-file", str(readiness_file)],
    )
    split = run(
        capsys,
        ["historical-dataset-split-quality-report", "--fixture-file", str(fixture_file), "--output-file", str(split_file)],
    )
    imbalance = run(
        capsys,
        ["historical-dataset-imbalance-report", "--fixture-file", str(fixture_file), "--output-file", str(imbalance_file)],
    )
    baseline = run(
        capsys,
        ["historical-dataset-baseline-evaluation", "--fixture-file", str(fixture_file), "--output-file", str(baseline_file)],
    )
    safety = run(
        capsys,
        ["historical-dataset-readiness-safety-report", "--fixture-file", str(fixture_file), "--output-file", str(safety_file)],
    )

    assert readiness["status"] == "COMPLETED"
    assert split["status"] == "COMPLETED"
    assert imbalance["status"] == "COMPLETED"
    assert baseline["status"] == "COMPLETED"
    assert safety["status"] == "COMPLETED"

    readiness_json = json.loads(readiness_file.read_text(encoding="utf-8"))
    split_json = json.loads(split_file.read_text(encoding="utf-8"))
    imbalance_json = json.loads(imbalance_file.read_text(encoding="utf-8"))
    baseline_json = json.loads(baseline_file.read_text(encoding="utf-8"))
    safety_json = json.loads(safety_file.read_text(encoding="utf-8"))

    assert readiness_json["report_only"] is True
    assert readiness_json["non_executable"] is True
    assert split_json["chronological_split"] is True
    assert split_json["random_shuffle_used"] is False
    assert split_json["report_only"] is True
    assert imbalance_json["report_only"] is True
    assert imbalance_json["severe_imbalance_warning"] is False
    assert baseline_json["deterministic_only"] is True
    assert baseline_json["non_learning_only"] is True
    assert baseline_json["runtime_trading_signal_present"] is False
    assert safety_json["report_only"] is True
    assert safety_json["no_learned_model_evaluation"] is True


@pytest.mark.parametrize(
    "command",
    [
        "historical-dataset-readiness-report",
        "historical-dataset-split-quality-report",
        "historical-dataset-imbalance-report",
        "historical-dataset-baseline-evaluation",
        "historical-dataset-readiness-safety-report",
    ],
)
def test_historical_dataset_readiness_cli_missing_fixture_is_json_safe(command, tmp_path, capsys):
    result = run(capsys, [command, "--fixture-file", str(tmp_path / "missing.json")])
    assert result["status"] == "FAILED"
    assert result["errors"]


def test_historical_dataset_readiness_cli_preserves_safety_flags(tmp_path, capsys):
    fixture_file = write(
        tmp_path / "historical_dataset_readiness_fixture.json",
        _set_split_manifest_from_records(_with_records(_engine_payload(), 6)),
    )

    result = run(capsys, ["historical-dataset-readiness-safety-report", "--fixture-file", str(fixture_file)])

    assert result["report_only"] is True
    assert result["read_only"] is True
    assert result["non_executable"] is True
    assert result["local_file_only"] is True
    assert result["no_network"] is True
    assert result["no_provider_api"] is True
    assert result["no_order"] is True
    assert result["no_llm_runtime"] is True
    assert result["no_ml_training"] is True
    assert result["no_learned_model_evaluation"] is True


def test_historical_dataset_readiness_cli_preserves_baseline_non_learning_boundary(tmp_path, capsys):
    fixture_file = write(
        tmp_path / "historical_dataset_readiness_fixture.json",
        _set_split_manifest_from_records(_with_records(_engine_payload(), 6)),
    )

    result = run(capsys, ["historical-dataset-baseline-evaluation", "--fixture-file", str(fixture_file)])

    assert result["deterministic_only"] is True
    assert result["non_learning_only"] is True
    assert result["trained_model_artifact_present"] is False
    assert result["model_weights_present"] is False
    assert result["runtime_trading_signal_present"] is False
