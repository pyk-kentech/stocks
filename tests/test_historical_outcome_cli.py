import copy
import json

import pytest

from stock_risk_mcp.cli import main
from tests.test_historical_outcome_engine import _multi_session_payload
from tests.test_historical_outcome_models import historical_outcome_fixture_payload


def write(path, payload):
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def run(capsys, args):
    main(args)
    return json.loads(capsys.readouterr().out)


def test_historical_outcome_cli_commands_return_report_only_json_outputs(tmp_path, capsys):
    payload = _multi_session_payload()
    fixture_file = write(tmp_path / "historical_outcome_fixture.json", payload)
    observe_file = tmp_path / "historical_outcome_observe.json"
    label_file = tmp_path / "historical_outcome_label_report.json"
    gap_file = tmp_path / "historical_outcome_gap_report.json"
    safety_file = tmp_path / "historical_outcome_safety_report.json"

    observed = run(
        capsys,
        ["historical-outcome-observe", "--fixture-file", str(fixture_file), "--output-file", str(observe_file)],
    )
    labeled = run(
        capsys,
        ["historical-outcome-label-report", "--fixture-file", str(fixture_file), "--output-file", str(label_file)],
    )
    gapped = run(
        capsys,
        ["historical-outcome-gap-report", "--fixture-file", str(fixture_file), "--output-file", str(gap_file)],
    )
    safe = run(
        capsys,
        ["historical-outcome-safety-report", "--fixture-file", str(fixture_file), "--output-file", str(safety_file)],
    )

    assert observed["status"] == "COMPLETED"
    assert observed["window_count"] >= 1
    assert labeled["status"] == "COMPLETED"
    assert labeled["label_count"] >= 1
    assert gapped["status"] == "COMPLETED"
    assert safe["status"] == "COMPLETED"

    observed_json = json.loads(observe_file.read_text(encoding="utf-8"))
    labeled_json = json.loads(label_file.read_text(encoding="utf-8"))
    gap_json = json.loads(gap_file.read_text(encoding="utf-8"))
    safety_json = json.loads(safety_file.read_text(encoding="utf-8"))

    assert observed_json["schema_version"] == "5.3-historical-outcome-observation-input"
    assert labeled_json["warning_count"] >= 0
    assert all(label["report_only"] is True for label in labeled_json["labels"])
    assert all(label["outcome_observed_after_anchor"] is True for label in labeled_json["labels"])
    assert gap_json["observation_input_id"] == observed_json["observation_input_id"]
    assert safety_json["read_only"] is True
    assert safety_json["non_executable"] is True
    assert safety_json["local_file_only"] is True
    assert safety_json["no_network"] is True
    assert safety_json["no_provider_api"] is True
    assert safety_json["no_order"] is True
    assert safety_json["no_llm_runtime"] is True
    assert safety_json["no_ml_training"] is True
    assert observed_json["scanner_replay_input"] == run(
        capsys,
        ["historical-outcome-label-report", "--fixture-file", str(fixture_file)],
    )["scanner_replay_input"]


@pytest.mark.parametrize(
    "command",
    [
        "historical-outcome-observe",
        "historical-outcome-label-report",
        "historical-outcome-gap-report",
        "historical-outcome-safety-report",
    ],
)
def test_historical_outcome_cli_missing_fixture_is_json_safe(command, tmp_path, capsys):
    result = run(capsys, [command, "--fixture-file", str(tmp_path / "missing.json")])
    assert result["status"] == "FAILED"
    assert result["errors"]


def test_historical_outcome_label_report_cli_does_not_mutate_scanner_replay_input(tmp_path, capsys):
    payload = historical_outcome_fixture_payload()
    payload["label_report"]["labels"] = []
    fixture_file = write(tmp_path / "historical_outcome_fixture.json", payload)
    observed = run(capsys, ["historical-outcome-observe", "--fixture-file", str(fixture_file)])

    result = run(capsys, ["historical-outcome-label-report", "--fixture-file", str(fixture_file)])

    assert result["replay_input_unchanged"] is True
    assert result["scanner_replay_input"] == observed["scanner_replay_input"]
    assert "outcome_label" not in str(result["scanner_replay_input"]).lower()
