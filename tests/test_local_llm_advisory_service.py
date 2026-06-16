from stock_risk_mcp.local_llm_advisory_service import load_local_llm_advisory_result, run_local_llm_advisory
from tests.test_local_llm_advisory_fixture import fixture_payload, write


def test_local_llm_advisory_service_writes_optional_json_output_only(tmp_path):
    fixture_file = write(tmp_path, "local_llm_advisory_fixture.json", fixture_payload())
    output_file = tmp_path / "local_llm_advisory_result.json"
    result = run_local_llm_advisory(fixture_file, output_file=output_file)
    assert output_file.exists()
    assert result.metadata_json["external_network_calls"] is False


def test_local_llm_advisory_report_loader_round_trips_json(tmp_path):
    fixture_file = write(tmp_path, "local_llm_advisory_fixture.json", fixture_payload())
    output_file = tmp_path / "local_llm_advisory_result.json"
    created = run_local_llm_advisory(fixture_file, output_file=output_file)
    loaded = load_local_llm_advisory_result(output_file)
    assert loaded == created
