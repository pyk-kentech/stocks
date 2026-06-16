from stock_risk_mcp.local_model_runtime_service import (
    load_local_model_candidates_result,
    load_local_model_runtime_result,
    run_local_model_advisory_dry_run,
    run_local_model_candidates_list,
    run_local_model_runtime_check,
)
from tests.test_local_model_runtime_fixture import candidates_fixture_payload, runtime_fixture_payload, write


def test_local_model_runtime_service_writes_optional_json_outputs(tmp_path):
    fixture_file = write(tmp_path, "local_model_runtime_fixture.json", runtime_fixture_payload())
    output_file = tmp_path / "local_model_runtime_result.json"
    result = run_local_model_runtime_check(fixture_file, output_file=output_file)
    assert output_file.exists()
    assert result.metadata_json["external_network_calls"] is False


def test_local_model_runtime_dry_run_service_round_trips_json(tmp_path):
    fixture_file = write(tmp_path, "local_model_runtime_fixture.json", runtime_fixture_payload(
        backend={
            "backend_type": "MOCK_LOCAL_RUNTIME",
            "adapter_name": "mock-local-runtime-v1",
            "model_name": "mock-qwen-class",
            "model_version": "0",
            "capabilities": {
                "supports_mock_execution": True,
                "supports_structured_json_output": True,
                "supports_korean": True,
                "supports_english": True,
                "supports_mixed_language": True,
                "supports_refusal_mode": True,
                "supports_timeout_budget": True,
                "supports_resource_budget": True,
                "supports_health_check": True,
                "supports_streaming": False,
                "requires_network": False,
                "requires_credentials": False,
                "may_create_order": False,
                "may_bypass_gates": False,
            },
            "runtime_metadata": {},
        },
    ))
    output_file = tmp_path / "local_model_runtime_result.json"
    created = run_local_model_advisory_dry_run(fixture_file, output_file=output_file)
    loaded = load_local_model_runtime_result(output_file)
    assert loaded == created


def test_local_model_candidates_list_service_round_trips_json(tmp_path):
    fixture_file = write(tmp_path, "local_model_candidates_fixture.json", candidates_fixture_payload())
    output_file = tmp_path / "local_model_candidates_result.json"
    created = run_local_model_candidates_list(fixture_file, output_file=output_file)
    loaded = load_local_model_candidates_result(output_file)
    assert loaded == created
