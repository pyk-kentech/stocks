from stock_risk_mcp.local_llm import LocalLLMBackend, LocalLLMRequest
from stock_risk_mcp.local_llm_client import LocalLLMClient
from stock_risk_mcp.local_llm_response import LocalLLMResponseStatus


def test_dry_run_never_calls_transport() -> None:
    calls = []
    response = LocalLLMClient(transport=lambda *args: calls.append(args)).run(_request(LocalLLMBackend.DRY_RUN))

    assert response.status == LocalLLMResponseStatus.DRY_RUN
    assert calls == []


def test_non_local_endpoint_is_blocked_without_transport_call() -> None:
    calls = []
    request = _request(LocalLLMBackend.OPENAI_COMPAT_LOCAL, "https://api.openai.com/v1")

    response = LocalLLMClient(transport=lambda *args: calls.append(args)).run(request)

    assert response.status == LocalLLMResponseStatus.FAILED
    assert response.content is None
    assert response.error == "non-local endpoint blocked"
    assert "non-local endpoint blocked" in response.warnings
    assert calls == []


def test_local_transport_failure_becomes_failed_response() -> None:
    request = _request(LocalLLMBackend.OLLAMA_LOCAL, "http://localhost:11434")

    response = LocalLLMClient(transport=lambda *args: (_ for _ in ()).throw(ConnectionError("offline"))).run(request)

    assert response.status == LocalLLMResponseStatus.FAILED
    assert response.error == "offline"


def test_openai_compat_local_requires_explicit_endpoint() -> None:
    calls = []
    response = LocalLLMClient(transport=lambda *args: calls.append(args)).run(_request(LocalLLMBackend.OPENAI_COMPAT_LOCAL))

    assert response.status == LocalLLMResponseStatus.FAILED
    assert response.error == "non-local endpoint blocked"
    assert calls == []


def _request(backend, endpoint=None):
    return LocalLLMRequest(
        backend=backend, endpoint_url=endpoint, prompt_id="prompt-1",
        system_instructions="Read only.", user_prompt="Explain.", context_json={},
    )
