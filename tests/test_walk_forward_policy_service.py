from stock_risk_mcp.walk_forward_policy_service import load_walk_forward_policy_report, run_walk_forward_policy_replay
from tests.test_walk_forward_policy_fixture import fixture_payload, write


def test_policy_replay_service_writes_optional_json_output_only(tmp_path):
    fixture_file = write(tmp_path, "policy_replay_fixture.json", fixture_payload())
    output_file = tmp_path / "policy_replay_report.json"
    report = run_walk_forward_policy_replay(fixture_file, output_file=output_file)
    assert output_file.exists()
    assert report.metadata_json["external_network_calls"] is False


def test_policy_replay_report_loader_round_trips_json(tmp_path):
    fixture_file = write(tmp_path, "policy_replay_fixture.json", fixture_payload())
    output_file = tmp_path / "policy_replay_report.json"
    created = run_walk_forward_policy_replay(fixture_file, output_file=output_file)
    loaded = load_walk_forward_policy_report(output_file)
    assert loaded == created
