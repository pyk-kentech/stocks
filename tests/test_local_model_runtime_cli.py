import json

from stock_risk_mcp.cli import main
from tests.test_local_model_runtime_fixture import candidates_fixture_payload, runtime_fixture_payload, write


def run(capsys, args):
    main(args)
    return json.loads(capsys.readouterr().out)


def test_local_model_runtime_commands_return_json_safe_outputs(tmp_path, capsys):
    candidates_file = write(tmp_path, "local_model_candidates_fixture.json", candidates_fixture_payload())
    runtime_file = write(tmp_path, "local_model_runtime_fixture.json", runtime_fixture_payload(
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
    listed = run(capsys, ["local-model-candidates-list", "--fixture-file", str(candidates_file)])
    checked = run(capsys, ["local-model-runtime-check", "--fixture-file", str(runtime_file)])
    summary = run(capsys, ["local-model-advisory-dry-run", "--fixture-file", str(runtime_file), "--output-file", str(output_file)])
    assert listed["candidate_count"] == 1
    assert checked["status"] == "MOCK_RUNTIME_READY"
    assert summary["status"] == "COMPLETED"


def test_local_model_runtime_invalid_fixture_is_json_safe(tmp_path, capsys):
    result = run(capsys, ["local-model-runtime-check", "--fixture-file", str(tmp_path / "missing.json")])
    assert result["status"] == "FAILED"
    assert result["errors"]
