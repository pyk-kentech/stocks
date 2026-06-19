import json

import pytest

from stock_risk_mcp.cli import main
from tests.test_historical_dataset_validation_engine import _engine_payload, _with_records


def write(path, payload):
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def run(capsys, args):
    main(args)
    return json.loads(capsys.readouterr().out)


def test_historical_dataset_validation_cli_commands_return_report_only_json_outputs(tmp_path, capsys):
    fixture_file = write(tmp_path / "historical_dataset_validation_fixture.json", _with_records(_engine_payload(), 10))
    validation_file = tmp_path / "historical_dataset_validation_report.json"
    leakage_file = tmp_path / "historical_dataset_leakage_audit.json"
    split_file = tmp_path / "historical_dataset_split_manifest.json"
    coverage_file = tmp_path / "historical_dataset_coverage_report.json"
    distribution_file = tmp_path / "historical_dataset_label_distribution.json"

    validated = run(
        capsys,
        ["historical-dataset-validate", "--fixture-file", str(fixture_file), "--output-file", str(validation_file)],
    )
    leaked = run(
        capsys,
        ["historical-dataset-leakage-audit", "--fixture-file", str(fixture_file), "--output-file", str(leakage_file)],
    )
    split = run(
        capsys,
        ["historical-dataset-split-manifest", "--fixture-file", str(fixture_file), "--output-file", str(split_file)],
    )
    covered = run(
        capsys,
        ["historical-dataset-coverage-report", "--fixture-file", str(fixture_file), "--output-file", str(coverage_file)],
    )
    distributed = run(
        capsys,
        ["historical-dataset-label-distribution", "--fixture-file", str(fixture_file), "--output-file", str(distribution_file)],
    )

    assert validated["status"] == "COMPLETED"
    assert leaked["status"] == "COMPLETED"
    assert split["status"] == "COMPLETED"
    assert covered["status"] == "COMPLETED"
    assert distributed["status"] == "COMPLETED"

    validation_json = json.loads(validation_file.read_text(encoding="utf-8"))
    leakage_json = json.loads(leakage_file.read_text(encoding="utf-8"))
    split_json = json.loads(split_file.read_text(encoding="utf-8"))
    coverage_json = json.loads(coverage_file.read_text(encoding="utf-8"))
    distribution_json = json.loads(distribution_file.read_text(encoding="utf-8"))

    assert validation_json["report_only"] is True
    assert validation_json["non_executable"] is True
    assert leakage_json["feature_outcome_leakage_absent"] is True
    assert leakage_json["report_only"] is True
    assert split_json["split_policy"] == "CHRONOLOGICAL"
    assert split_json["random_shuffle_used"] is False
    assert split_json["report_only"] is True
    assert coverage_json["report_only"] is True
    assert distribution_json["report_only"] is True


@pytest.mark.parametrize(
    "command",
    [
        "historical-dataset-validate",
        "historical-dataset-leakage-audit",
        "historical-dataset-split-manifest",
        "historical-dataset-coverage-report",
        "historical-dataset-label-distribution",
    ],
)
def test_historical_dataset_validation_cli_missing_fixture_is_json_safe(command, tmp_path, capsys):
    result = run(capsys, [command, "--fixture-file", str(tmp_path / "missing.json")])
    assert result["status"] == "FAILED"
    assert result["errors"]


def test_historical_dataset_validation_cli_preserves_safety_and_split_policy(tmp_path, capsys):
    fixture_file = write(tmp_path / "historical_dataset_validation_fixture.json", _with_records(_engine_payload(), 10))

    result = run(capsys, ["historical-dataset-split-manifest", "--fixture-file", str(fixture_file)])

    assert result["report_only"] is True
    assert result["read_only"] is True
    assert result["non_executable"] is True
    assert result["local_file_only"] is True
    assert result["no_network"] is True
    assert result["no_provider_api"] is True
    assert result["no_order"] is True
    assert result["no_llm_runtime"] is True
    assert result["no_ml_training"] is True
    assert result["split_policy"] == "CHRONOLOGICAL"
    assert result["random_shuffle_used"] is False
    assert len(result["record_refs"]) == len({ref["dataset_record_id"] for ref in result["record_refs"]})


def test_historical_dataset_validation_cli_preserves_leakage_boundary(tmp_path, capsys):
    fixture_file = write(tmp_path / "historical_dataset_validation_fixture.json", _with_records(_engine_payload(), 10))

    result = run(capsys, ["historical-dataset-leakage-audit", "--fixture-file", str(fixture_file)])

    assert result["feature_outcome_leakage_absent"] is True
    assert result["outcome_label_in_features_count"] == 0
    assert result["forward_return_in_features_count"] == 0
    assert result["max_excursion_in_features_count"] == 0
    assert result["post_anchor_actual_value_in_features_count"] == 0
