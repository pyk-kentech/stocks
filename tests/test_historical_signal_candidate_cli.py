import json

import pytest

from stock_risk_mcp.cli import main
from tests.test_historical_signal_candidate_engine import _engine_payload


def write(path, payload):
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def run(capsys, args):
    main(args)
    return json.loads(capsys.readouterr().out)


def test_historical_signal_candidate_cli_commands_return_report_only_json_outputs(tmp_path, capsys):
    fixture_file = write(tmp_path / "historical_signal_candidate_fixture.json", _engine_payload())
    build_file = tmp_path / "historical_signal_candidate_build.json"
    report_file = tmp_path / "historical_signal_candidate_report.json"
    safety_file = tmp_path / "historical_signal_candidate_safety_report.json"
    gap_file = tmp_path / "historical_signal_candidate_gap_report.json"

    build = run(
        capsys,
        ["historical-signal-candidate-build", "--fixture-file", str(fixture_file), "--output-file", str(build_file)],
    )
    report = run(
        capsys,
        ["historical-signal-candidate-report", "--fixture-file", str(fixture_file), "--output-file", str(report_file)],
    )
    safety = run(
        capsys,
        ["historical-signal-candidate-safety-report", "--fixture-file", str(fixture_file), "--output-file", str(safety_file)],
    )
    gap = run(
        capsys,
        ["historical-signal-candidate-gap-report", "--fixture-file", str(fixture_file), "--output-file", str(gap_file)],
    )

    assert build["status"] == "COMPLETED"
    assert report["status"] == "COMPLETED"
    assert safety["status"] == "COMPLETED"
    assert gap["status"] == "COMPLETED"

    build_json = json.loads(build_file.read_text(encoding="utf-8"))
    report_json = json.loads(report_file.read_text(encoding="utf-8"))
    safety_json = json.loads(safety_file.read_text(encoding="utf-8"))
    gap_json = json.loads(gap_file.read_text(encoding="utf-8"))

    assert build_json["report_only"] is True
    assert build_json["non_executable"] is True
    assert build_json["accepted_candidate_count"] == 2
    assert report_json["report_only"] is True
    assert report_json["candidate_count"] == 2
    assert safety_json["report_only"] is True
    assert safety_json["no_runtime_trading_signal"] is True
    assert safety_json["no_order_candidate"] is True
    assert safety_json["no_paper_trading"] is True
    assert gap_json["report_only"] is True
    assert "SIGNAL_CANDIDATE_REPORT_GENERATED" in gap_json["gap_categories"]


@pytest.mark.parametrize(
    "command",
    [
        "historical-signal-candidate-build",
        "historical-signal-candidate-report",
        "historical-signal-candidate-safety-report",
        "historical-signal-candidate-gap-report",
    ],
)
def test_historical_signal_candidate_cli_missing_fixture_is_json_safe(command, tmp_path, capsys):
    result = run(capsys, [command, "--fixture-file", str(tmp_path / "missing.json")])
    assert result["status"] == "FAILED"
    assert result["errors"]


def test_historical_signal_candidate_cli_preserves_report_only_non_executable_boundary(tmp_path, capsys):
    fixture_file = write(tmp_path / "historical_signal_candidate_fixture.json", _engine_payload())

    result = run(capsys, ["historical-signal-candidate-report", "--fixture-file", str(fixture_file)])

    assert result["report_only"] is True
    assert result["non_executable"] is True
    assert result["local_file_only"] is True
    assert result["offline_only"] is True


def test_historical_signal_candidate_cli_does_not_create_runtime_signal_order_candidate_or_paper_trading_fields(tmp_path, capsys):
    fixture_file = write(tmp_path / "historical_signal_candidate_fixture.json", _engine_payload())

    result = run(capsys, ["historical-signal-candidate-build", "--fixture-file", str(fixture_file)])
    dumped = json.dumps(result).lower()

    assert "buy" not in dumped
    assert "sell" not in dumped
    assert "entry" not in dumped
    assert "exit" not in dumped
    assert "order_intent" not in dumped
    assert "paper_order" not in dumped
