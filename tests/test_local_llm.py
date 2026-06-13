from stock_risk_mcp.agent_brief import AgentBrief
from stock_risk_mcp.agent_context import AgentContext, AgentContextType, AgentPermissionLevel
from stock_risk_mcp.agent_prompt import AgentPrompt
from stock_risk_mcp.local_llm import LocalLLMBackend, LocalLLMRequest
from stock_risk_mcp.local_llm_response import LocalLLMResponse, LocalLLMResponseStatus
from stock_risk_mcp.repository import RiskRepository


def test_agent_and_local_llm_repository_round_trips(tmp_path) -> None:
    repository = RiskRepository(tmp_path / "risk.sqlite3")
    context = AgentContext(context_type=AgentContextType.ANALYSIS_REPORT, source_id="report-1", permission_level=AgentPermissionLevel.READ_ONLY, summary="Summary", context_json={})
    prompt = AgentPrompt(context_id=context.context_id, system_instructions="Read only.", user_prompt="Explain.", context_json={})
    brief = AgentBrief(source_id="report-1", title="Brief", summary="Summary", disclaimer="Research only.")
    request = LocalLLMRequest(backend=LocalLLMBackend.DRY_RUN, prompt_id=prompt.prompt_id, system_instructions=prompt.system_instructions, user_prompt=prompt.user_prompt, context_json={})
    response = LocalLLMResponse(request_id=request.request_id, backend=LocalLLMBackend.DRY_RUN, status=LocalLLMResponseStatus.DRY_RUN)

    repository.save_agent_context(context)
    repository.save_agent_prompt(prompt)
    repository.save_agent_brief(brief)
    repository.save_local_llm_request(request)
    repository.save_local_llm_response(response)

    assert repository.get_agent_context(context.context_id) == context
    assert repository.get_agent_prompt(prompt.prompt_id) == prompt
    assert repository.get_agent_brief(brief.brief_id) == brief
    assert repository.list_local_llm_responses() == [response]
