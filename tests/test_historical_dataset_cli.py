import json

import pytest

from stock_risk_mcp.cli import main
from tests.test_historical_dataset_engine import _assembly_payload


def write(path, payload):
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def run(capsys, args):
    main(args)
    return json.loads(capsys.readouterr().out)


def test_historical_dataset_cli_commands_return_report_only_json_outputs(tmp_path, capsys):
    fixture_file = write(tmp_path / "historical_dataset_fixture.json", _assembly_payload())
    assemble_file = tmp_path / "historical_dataset_assemble.json"
    manifest_file = tmp_path / "historical_dataset_manifest.json"
    quality_file = tmp_path / "historical_dataset_quality.json"
    gap_file = tmp_path / "historical_dataset_gap.json"
    safety_file = tmp_path / "historical_dataset_safety.json"

    assembled = run(
        capsys,
        ["historical-dataset-assemble", "--fixture-file", str(fixture_file), "--output-file", str(assemble_file)],
    )
    manifested = run(
        capsys,
        ["historical-dataset-export-manifest", "--fixture-file", str(fixture_file), "--output-file", str(manifest_file)],
    )
    qualified = run(
        capsys,
        ["historical-dataset-quality-report", "--fixture-file", str(fixture_file), "--output-file", str(quality_file)],
    )
    gapped = run(
        capsys,
        ["historical-dataset-gap-report", "--fixture-file", str(fixture_file), "--output-file", str(gap_file)],
    )
    safe = run(
        capsys,
        ["historical-dataset-safety-report", "--fixture-file", str(fixture_file), "--output-file", str(safety_file)],
    )

    assert assembled["status"] == "COMPLETED"
    assert assembled["record_count"] == 1
    assert manifested["status"] == "COMPLETED"
    assert manifested["manifest_id"] == "DATASET-EXPORT-MANIFEST-1"
    assert qualified["status"] == "COMPLETED"
    assert qualified["record_count"] == 1
    assert gapped["status"] == "COMPLETED"
    assert safe["status"] == "COMPLETED"

    assembled_json = json.loads(assemble_file.read_text(encoding="utf-8"))
    manifest_json = json.loads(manifest_file.read_text(encoding="utf-8"))
    quality_json = json.loads(quality_file.read_text(encoding="utf-8"))
    gap_json = json.loads(gap_file.read_text(encoding="utf-8"))
    safety_json = json.loads(safety_file.read_text(encoding="utf-8"))

    assert assembled_json["schema_version"] == "5.4-historical-dataset-assembly-input"
    assert assembled_json["records"][0]["report_only"] is True
    assert "outcome_label" not in assembled_json["records"][0]["feature_block"]
    assert "forward_return_pct" not in assembled_json["records"][0]["feature_block"]
    assert manifest_json["report_only"] is True
    assert quality_json["report_only"] is True
    assert gap_json["report_only"] is True
    assert safety_json["read_only"] is True
    assert safety_json["report_only"] is True
    assert safety_json["non_executable"] is True
    assert safety_json["local_file_only"] is True
    assert safety_json["no_network"] is True
    assert safety_json["no_provider_api"] is True
    assert safety_json["no_order"] is True
    assert safety_json["no_llm_runtime"] is True
    assert safety_json["no_ml_training"] is True


@pytest.mark.parametrize(
    "command",
    [
        "historical-dataset-assemble",
        "historical-dataset-export-manifest",
        "historical-dataset-quality-report",
        "historical-dataset-gap-report",
        "historical-dataset-safety-report",
    ],
)
def test_historical_dataset_cli_missing_fixture_is_json_safe(command, tmp_path, capsys):
    result = run(capsys, [command, "--fixture-file", str(tmp_path / "missing.json")])
    assert result["status"] == "FAILED"
    assert result["errors"]


def test_historical_dataset_assemble_cli_does_not_mutate_scanner_replay_input(tmp_path, capsys):
    fixture_file = write(tmp_path / "historical_dataset_fixture.json", _assembly_payload())

    result = run(capsys, ["historical-dataset-assemble", "--fixture-file", str(fixture_file)])

    assert result["replay_input_unchanged"] is True
    assert result["scanner_replay_input"]["report_only"] is True
    assert "outcome_label" not in str(result["scanner_replay_input"]).lower()
