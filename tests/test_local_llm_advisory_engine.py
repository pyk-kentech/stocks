from stock_risk_mcp.local_llm_advisory_engine import run_local_llm_advisory_fixture
from stock_risk_mcp.local_llm_advisory_models import LocalLLMAdvisoryFixture
from tests.test_local_llm_advisory_fixture import fixture_payload


def fixture(value=None):
    return LocalLLMAdvisoryFixture.model_validate(value or fixture_payload())


def test_disabled_backend_returns_safe_refusal():
    result = run_local_llm_advisory_fixture(fixture(), "fixture-checksum")
    assert result.status == "BACKEND_DISABLED"
    assert result.metadata_json["advisory_only"] is True
    assert result.metadata_json["external_network_calls"] is False


def test_local_model_metadata_opt_in_can_return_safe_advisory_response():
    result = run_local_llm_advisory_fixture(
        fixture(fixture_payload(
            task_type="EXPLAIN_TRADE_PLAN_RISK",
            backend={
                "backend_type": "LOCAL_MODEL",
                "model_name": "fixture-local",
                "model_version": "1",
                "runtime_metadata": {"quantization": "q4"},
            },
        )),
        "fixture-checksum",
    )
    assert result.status == "ADVISORY_RESPONSE"
    assert result.metadata_json["may_create_order"] is False


def test_unsafe_output_is_rejected_fail_closed():
    result = run_local_llm_advisory_fixture(
        fixture(fixture_payload(
            task_type="SUMMARIZE_TECHNICAL_EVIDENCE",
            backend={
                "backend_type": "LOCAL_MODEL",
                "model_name": "fixture-local",
                "model_version": "1",
                "runtime_metadata": {"quantization": "q4"},
            },
            inputs={
                "ticker": "ABC",
                "title": "Unsafe text",
                "text_blocks": ["Buy now and place an order immediately"],
            },
        )),
        "fixture-checksum",
    )
    assert result.status == "UNSAFE_OUTPUT_REJECTED"


def test_allowed_advisory_tasks_are_supported():
    for task in (
        "SUMMARIZE_TECHNICAL_EVIDENCE",
        "SUMMARIZE_MARKET_DISCOVERY",
        "SUMMARIZE_LLM_SIGNAL_EVALUATION",
        "EXPLAIN_TRADE_PLAN_RISK",
        "CHALLENGE_WEAK_ASSUMPTIONS",
        "LIST_MISSING_DATA",
        "CLASSIFY_ADVISORY_RISK_LANGUAGE",
    ):
        result = run_local_llm_advisory_fixture(
            fixture(fixture_payload(
                task_type=task,
                backend={
                    "backend_type": "LOCAL_MODEL",
                    "model_name": "fixture-local",
                    "model_version": "1",
                    "runtime_metadata": {"quantization": "q4"},
                },
            )),
            "fixture-checksum",
        )
        assert result.status == "ADVISORY_RESPONSE"
