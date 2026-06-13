from datetime import date, datetime

from stock_risk_mcp.local_llm import LocalLLMBackend
from stock_risk_mcp.local_llm_response import LocalLLMResponse, LocalLLMResponseStatus
from stock_risk_mcp.notification_digest import build_daily_digest
from stock_risk_mcp.notifications import NotificationSeverity
from stock_risk_mcp.repository import RiskRepository


def test_daily_digest_optionally_includes_failed_local_llm_responses(tmp_path) -> None:
    repository = RiskRepository(tmp_path / "risk.sqlite3")
    repository.save_local_llm_response(LocalLLMResponse(
        response_id="response-1", request_id="request-1", backend=LocalLLMBackend.OPENAI_COMPAT_LOCAL,
        status=LocalLLMResponseStatus.FAILED, error="non-local endpoint blocked",
        warnings=["non-local endpoint blocked"], created_at=datetime(2026, 6, 13),
    ))

    without_llm = build_daily_digest(repository, date(2026, 6, 13), NotificationSeverity.INFO)
    with_llm = build_daily_digest(
        repository, date(2026, 6, 13), NotificationSeverity.INFO, include_local_llm_responses=True
    )

    assert "response-1" not in without_llm.message
    assert "response-1" in with_llm.message
    assert "No critical alerts" in without_llm.message
