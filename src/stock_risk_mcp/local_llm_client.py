from __future__ import annotations

import json
from urllib.request import Request, urlopen

from stock_risk_mcp.agent_guardrails import is_local_endpoint
from stock_risk_mcp.local_llm import LocalLLMBackend, LocalLLMRequest
from stock_risk_mcp.local_llm_response import LocalLLMResponse, LocalLLMResponseStatus


class LocalLLMClient:
    def __init__(self, transport=None) -> None:
        self.transport = transport or _http_transport

    def run(self, request: LocalLLMRequest) -> LocalLLMResponse:
        if request.backend == LocalLLMBackend.DRY_RUN:
            return LocalLLMResponse(
                request_id=request.request_id, backend=request.backend, model=request.model,
                status=LocalLLMResponseStatus.DRY_RUN, content="DRY_RUN: prompt generated but not sent",
            )
        if request.backend == LocalLLMBackend.DISABLED:
            return self._failed(request, "local LLM backend disabled")
        endpoint = request.endpoint_url or ("http://localhost:11434" if request.backend == LocalLLMBackend.OLLAMA_LOCAL else None)
        if not is_local_endpoint(endpoint):
            return self._failed(request, "non-local endpoint blocked")
        try:
            content = self.transport(request, endpoint)
            return LocalLLMResponse(
                request_id=request.request_id, backend=request.backend, model=request.model,
                status=LocalLLMResponseStatus.COMPLETED, content=str(content),
            )
        except Exception as error:
            return self._failed(request, str(error))

    @staticmethod
    def _failed(request: LocalLLMRequest, error: str) -> LocalLLMResponse:
        return LocalLLMResponse(
            request_id=request.request_id, backend=request.backend, model=request.model,
            status=LocalLLMResponseStatus.FAILED, error=error, warnings=[error],
        )


def _http_transport(request: LocalLLMRequest, endpoint: str) -> str:
    context = json.dumps(request.context_json, ensure_ascii=False, sort_keys=True)
    user_content = f"{request.user_prompt}\n\nContext JSON:\n{context}"
    if request.backend == LocalLLMBackend.OLLAMA_LOCAL:
        url = f"{endpoint.rstrip('/')}/api/generate"
        payload = {"model": request.model, "prompt": f"{request.system_instructions}\n\n{user_content}", "stream": False}
    else:
        url = f"{endpoint.rstrip('/')}/chat/completions"
        payload = {
            "model": request.model,
            "messages": [{"role": "system", "content": request.system_instructions}, {"role": "user", "content": user_content}],
            "temperature": request.temperature, "max_tokens": request.max_tokens,
        }
    http_request = Request(url, data=json.dumps(payload).encode("utf-8"), headers={"Content-Type": "application/json"})
    with urlopen(http_request, timeout=30) as response:
        body = json.loads(response.read().decode("utf-8"))
    if request.backend == LocalLLMBackend.OLLAMA_LOCAL:
        return str(body.get("response") or "")
    return str(body["choices"][0]["message"]["content"])
