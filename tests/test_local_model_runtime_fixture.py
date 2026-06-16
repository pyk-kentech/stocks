import json

import pytest

from stock_risk_mcp.local_model_runtime_fixture import load_local_model_candidates_fixture, load_local_model_runtime_fixture


def runtime_fixture_payload(backend=None, request=None, runtime_limits=None, mock_response=None, safety=None):
    return {
        "schema_version": "3.9-local-model-runtime-fixture",
        "run_id": "local-model-runtime-check-1",
        "created_at": "2026-06-17T12:00:00+00:00",
        "backend": backend or {
            "backend_type": "DISABLED",
            "adapter_name": "disabled-runtime",
            "model_name": "disabled",
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
            "runtime_metadata": {},
        },
        "request": request or {
            "task_type": "SUMMARIZE_TECHNICAL_EVIDENCE",
            "ticker": "abc",
            "text_blocks": ["RSI recovered above 50", "Volume expanded"],
        },
        "runtime_limits": runtime_limits or {
            "timeout_ms": 500,
            "max_output_tokens": 300,
            "max_memory_mb": 1024,
        },
        "mock_response": mock_response or {
            "response_text": "Technical evidence is constructive but incomplete.",
            "bullet_points": ["RSI recovered above 50", "Volume expanded"],
            "risk_labels": ["MISSING_STOP_CONTEXT"],
        },
        "safety": safety or {
            "advisory_only": True,
            "may_create_order": False,
            "may_bypass_gates": False,
        },
    }


def candidates_fixture_payload(candidates=None):
    return {
        "schema_version": "3.9-local-model-candidates-fixture",
        "run_id": "local-model-candidates-list-1",
        "created_at": "2026-06-17T12:00:00+00:00",
        "candidates": candidates or [
            {
                "candidate_id": "mock-qwen-7b",
                "backend_type": "MOCK_LOCAL_RUNTIME",
                "model_family": "QWEN",
                "model_class": "7B",
                "mixed_language_support": True,
                "structured_output_suitability": "HIGH",
                "hallucination_risk": "LOWER",
                "hardware_tier": "LOCAL_GPU_12GB",
                "recommended_for_future_eval": True,
            }
        ],
    }


def write(tmp_path, name, value):
    path = tmp_path / name
    path.write_text(json.dumps(value), encoding="utf-8")
    return path


def test_local_model_runtime_fixture_normalizes_ticker_and_validates_disabled_backend(tmp_path):
    fixture = load_local_model_runtime_fixture(write(tmp_path, "local_model_runtime_fixture.json", runtime_fixture_payload()))
    assert fixture.request.ticker == "ABC"
    assert fixture.backend.backend_type.value == "DISABLED"
    assert fixture.safety.advisory_only is True


def test_local_model_candidates_fixture_loads_expected_candidate_schema(tmp_path):
    fixture = load_local_model_candidates_fixture(write(tmp_path, "local_model_candidates_fixture.json", candidates_fixture_payload()))
    assert len(fixture.candidates) == 1
    assert fixture.candidates[0].backend_type.value == "MOCK_LOCAL_RUNTIME"


def test_local_model_runtime_fixture_requires_explicit_json_file(tmp_path):
    with pytest.raises(ValueError, match="JSON"):
        load_local_model_runtime_fixture(write(tmp_path, "local_model_runtime_fixture.txt", runtime_fixture_payload()))


@pytest.mark.parametrize("change", [
    lambda value: value.update(created_at="2026-06-17T12:00:00"),
    lambda value: value["backend"].update(backend_type="OPENAI"),
    lambda value: value["backend"].update(runtime_metadata={"endpoint_url": "http://localhost"}),
    lambda value: value["runtime_limits"].update(timeout_ms=0),
    lambda value: value["runtime_limits"].update(max_memory_mb=0),
    lambda value: value["request"].update(text_blocks=["ok", ""]),
    lambda value: value["safety"].update(advisory_only=False),
    lambda value: value["backend"]["capabilities"].update(requires_network=True),
])
def test_local_model_runtime_fixture_rejects_invalid_values(tmp_path, change):
    value = runtime_fixture_payload()
    change(value)
    with pytest.raises(ValueError):
        load_local_model_runtime_fixture(write(tmp_path, "local_model_runtime_fixture.json", value))


def test_local_model_candidates_fixture_rejects_invalid_candidate_values(tmp_path):
    value = candidates_fixture_payload(candidates=[{
        "candidate_id": "bad-cloud",
        "backend_type": "OLLAMA_LOCAL",
        "model_family": "QWEN",
        "model_class": "7B",
        "mixed_language_support": True,
        "structured_output_suitability": "HIGH",
        "hallucination_risk": "LOWER",
        "hardware_tier": "LOCAL_GPU_12GB",
        "recommended_for_future_eval": True,
        "requires_network": True,
    }])
    with pytest.raises(ValueError):
        load_local_model_candidates_fixture(write(tmp_path, "local_model_candidates_fixture.json", value))
