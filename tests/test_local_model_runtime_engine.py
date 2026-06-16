from stock_risk_mcp.local_model_runtime_engine import list_local_model_candidates, run_local_model_advisory_dry_run_fixture, run_local_model_runtime_check_fixture
from stock_risk_mcp.local_model_runtime_models import LocalModelCandidatesFixture, LocalModelRuntimeFixture
from tests.test_local_model_runtime_fixture import candidates_fixture_payload, runtime_fixture_payload


def runtime_fixture(value=None):
    return LocalModelRuntimeFixture.model_validate(value or runtime_fixture_payload())


def candidates_fixture(value=None):
    return LocalModelCandidatesFixture.model_validate(value or candidates_fixture_payload())


def test_disabled_backend_returns_safe_disabled_response():
    result = run_local_model_advisory_dry_run_fixture(runtime_fixture(), "fixture-checksum")
    assert result.status == "BACKEND_DISABLED"
    assert result.metadata_json["real_model_called"] is False
    assert result.metadata_json["mock_runtime_used"] is False


def test_mock_runtime_returns_deterministic_fixture_derived_response():
    result = run_local_model_advisory_dry_run_fixture(
        runtime_fixture(runtime_fixture_payload(
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
                "runtime_metadata": {"quantization": "q4"},
            },
        )),
        "fixture-checksum",
    )
    assert result.status == "ADVISORY_RESPONSE"
    assert result.metadata_json["mock_runtime_used"] is True
    assert result.summary_text == "Technical evidence is constructive but incomplete."


def test_runtime_check_returns_ready_for_mock_runtime():
    result = run_local_model_runtime_check_fixture(
        runtime_fixture(runtime_fixture_payload(
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
        )),
        "fixture-checksum",
    )
    assert result.status == "MOCK_RUNTIME_READY"
    assert result.health_metadata["health_status"] == "READY"


def test_future_backend_execution_is_rejected_in_v39():
    result = run_local_model_advisory_dry_run_fixture(
        runtime_fixture(runtime_fixture_payload(
            backend={
                "backend_type": "OLLAMA_LOCAL",
                "adapter_name": "ollama-local",
                "model_name": "qwen2.5",
                "model_version": "0",
                "capabilities": {
                    "supports_mock_execution": False,
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
                "runtime_metadata": {"transport": "local_only"},
            },
        )),
        "fixture-checksum",
    )
    assert result.status == "UNIMPLEMENTED_BACKEND_REJECTED"
    assert result.metadata_json["real_model_called"] is False


def test_unsafe_output_is_rejected_fail_closed():
    result = run_local_model_advisory_dry_run_fixture(
        runtime_fixture(runtime_fixture_payload(
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
            mock_response={
                "response_text": "Buy now and submit the order immediately.",
                "bullet_points": [],
                "risk_labels": [],
            },
        )),
        "fixture-checksum",
    )
    assert result.status == "UNSAFE_OUTPUT_REJECTED"


def test_candidate_listing_returns_deterministic_result():
    result = list_local_model_candidates(candidates_fixture(), "fixture-checksum")
    assert result.candidate_count == 1
    assert result.metadata_json["cloud_backend_used"] is False
