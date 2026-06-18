import json

import pytest

from stock_risk_mcp.cli import main
from tests.test_historical_replay_bridge_engine import bridge_fixture_payload


def write(path, payload):
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def run(capsys, args):
    main(args)
    return json.loads(capsys.readouterr().out)


def test_historical_replay_bridge_cli_commands_return_json_safe_outputs(tmp_path, capsys):
    fixture_file = write(tmp_path / "historical_replay_bridge_fixture.json", bridge_fixture_payload())
    build_output_file = tmp_path / "historical_replay_bridge_build.json"
    window_file = tmp_path / "historical_replay_window_report.json"
    gap_file = tmp_path / "historical_replay_gap_report.json"
    safety_file = tmp_path / "historical_replay_safety_report.json"

    built = run(
        capsys,
        ["historical-replay-bridge-build", "--fixture-file", str(fixture_file), "--output-file", str(build_output_file)],
    )
    streamed = run(capsys, ["historical-replay-event-stream", "--fixture-file", str(fixture_file)])
    windowed = run(capsys, ["historical-replay-window-report", "--fixture-file", str(fixture_file), "--output-file", str(window_file)])
    scanned = run(capsys, ["historical-scanner-replay-input", "--fixture-file", str(fixture_file)])
    gapped = run(capsys, ["historical-replay-gap-report", "--fixture-file", str(fixture_file), "--output-file", str(gap_file)])
    safe = run(capsys, ["historical-replay-safety-report", "--fixture-file", str(fixture_file), "--output-file", str(safety_file)])

    assert built["status"] == "COMPLETED"
    assert built["window_count"] == 1
    assert streamed["stream_id"] == "BRIDGE-FIXTURE-1-STREAM"
    assert len(streamed["events"]) == 1
    assert windowed["status"] == "COMPLETED"
    assert scanned["schema_version"] == "5.2-historical-scanner-replay-input"
    assert scanned["no_order"] is True
    assert all(seed["is_order_candidate"] is False for seed in scanned["candidate_seeds"])
    assert gapped["status"] == "COMPLETED"
    assert safe["status"] == "COMPLETED"
    assert json.loads(build_output_file.read_text(encoding="utf-8"))["schema_version"] == "5.2-historical-replay-bridge-report"
    assert json.loads(window_file.read_text(encoding="utf-8"))["schema_version"] == "5.2-historical-replay-window-bundle"
    assert json.loads(gap_file.read_text(encoding="utf-8"))["schema_version"] == "5.2-historical-replay-bridge-gap-report"
    assert json.loads(safety_file.read_text(encoding="utf-8"))["safety_report_id"] == "historical-replay-bridge-safety-report"


@pytest.mark.parametrize(
    "command",
    [
        "historical-replay-bridge-build",
        "historical-replay-event-stream",
        "historical-replay-window-report",
        "historical-scanner-replay-input",
        "historical-replay-gap-report",
        "historical-replay-safety-report",
    ],
)
def test_historical_replay_bridge_cli_missing_fixture_is_json_safe(command, tmp_path, capsys):
    result = run(capsys, [command, "--fixture-file", str(tmp_path / "missing.json")])
    assert result["status"] == "FAILED"
    assert result["errors"]


@pytest.mark.parametrize(
    ("label", "mutate", "expected_error"),
    [
        (
            "remote_url_source_type",
            lambda payload: payload["historical_market_data_snapshot"]["source_descriptor"].__setitem__("source_type", "remote_url"),
            "source_type must be one of local_csv or local_jsonl",
        ),
        (
            "provider_api_source_type",
            lambda payload: payload["historical_market_data_snapshot"]["source_descriptor"].__setitem__("source_type", "provider_api"),
            "source_type must be one of local_csv or local_jsonl",
        ),
        (
            "network_path",
            lambda payload: payload["historical_market_data_snapshot"]["source_descriptor"].__setitem__("local_file_path", "network://socket"),
            "network",
        ),
        (
            "parquet_path",
            lambda payload: payload["historical_market_data_snapshot"]["source_descriptor"].__setitem__("local_file_path", "fixtures/historical/replay.parquet"),
            "parquet",
        ),
        (
            "order_like_metadata",
            lambda payload: payload["historical_market_data_snapshot"]["provider_provenance"].__setitem__("notes", "order candidate handoff"),
            "order",
        ),
        (
            "execution_like_metadata",
            lambda payload: payload["historical_market_data_snapshot"]["provider_provenance"].__setitem__("notes", "execution path handoff"),
            "execution",
        ),
        (
            "live_prod_metadata",
            lambda payload: payload["historical_market_data_snapshot"]["provider_provenance"].__setitem__("notes", "live prod bridge"),
            "live",
        ),
        (
            "llm_gemini_metadata",
            lambda payload: payload["historical_market_data_snapshot"]["provider_provenance"].__setitem__("notes", "gemini llm runtime"),
            "gemini",
        ),
        (
            "ml_training_metadata",
            lambda payload: payload["historical_market_data_snapshot"]["provider_provenance"].__setitem__("notes", "ml training trigger"),
            "training",
        ),
        (
            "crawler_metadata",
            lambda payload: payload["historical_market_data_snapshot"]["provider_provenance"].__setitem__("notes", "crawler trigger"),
            "crawler",
        ),
    ],
)
def test_historical_replay_event_stream_cli_fails_closed_for_unsafe_fixture_inputs(
    label,
    mutate,
    expected_error,
    tmp_path,
    capsys,
):
    payload = bridge_fixture_payload()
    mutate(payload)
    fixture_file = write(tmp_path / f"{label}.json", payload)

    result = run(capsys, ["historical-replay-event-stream", "--fixture-file", str(fixture_file)])

    assert result["status"] == "FAILED"
    assert any(expected_error in error.lower() for error in result["errors"])
