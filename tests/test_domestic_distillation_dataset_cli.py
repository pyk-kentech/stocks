import json

from stock_risk_mcp.cli import main
from tests.test_domestic_distillation_dataset_fixture import distillation_dataset_fixture_payload
from tests.test_domestic_realtime_fixture import write


def run(capsys, args):
    main(args)
    return json.loads(capsys.readouterr().out)


def test_domestic_distillation_dataset_cli_commands_return_json_safe_outputs(tmp_path, capsys):
    fixture_file = write(
        tmp_path,
        "domestic_distillation_dataset_fixture.json",
        distillation_dataset_fixture_payload(tmp_path),
    )
    pack_file = tmp_path / "domestic_distillation_dataset_pack.json"
    validate_file = tmp_path / "domestic_distillation_dataset_validation.json"
    gap_file = tmp_path / "domestic_distillation_dataset_gap.json"
    safety_file = tmp_path / "domestic_distillation_dataset_safety.json"
    validated = run(capsys, ["domestic-distillation-dataset-config-validate", "--fixture-file", str(fixture_file)])
    packed = run(capsys, ["domestic-distillation-dataset-build", "--fixture-file", str(fixture_file), "--output-file", str(pack_file)])
    verified = run(capsys, ["domestic-distillation-dataset-validate", "--fixture-file", str(fixture_file), "--output-file", str(validate_file)])
    gapped = run(capsys, ["domestic-distillation-dataset-gap-report", "--fixture-file", str(fixture_file), "--output-file", str(gap_file)])
    safe = run(capsys, ["domestic-distillation-dataset-safety-report", "--fixture-file", str(fixture_file), "--output-file", str(safety_file)])
    assert validated["status"] == "COMPLETED"
    assert packed["status"] == "COMPLETED"
    assert verified["status"] == "COMPLETED"
    assert gapped["status"] == "COMPLETED"
    assert safe["status"] == "COMPLETED"


def test_domestic_distillation_dataset_cli_invalid_fixture_is_json_safe(tmp_path, capsys):
    result = run(capsys, ["domestic-distillation-dataset-config-validate", "--fixture-file", str(tmp_path / "missing.json")])
    assert result["status"] == "FAILED"
    assert result["errors"]
