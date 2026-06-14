from stock_risk_mcp.kiwoom_readonly_models import (
    KiwoomEndpointCategory,
    KiwoomReadOnlyRequestAudit,
    KiwoomReadOnlyResponseAudit,
)
from stock_risk_mcp.repository import RiskRepository


def test_kiwoom_readonly_repository_saves_sanitized_audits(tmp_path) -> None:
    repository = RiskRepository(tmp_path / "risk.sqlite3")
    request = KiwoomReadOnlyRequestAudit(
        api_id="RO_QUOTE", path="/readonly/quote", category=KiwoomEndpointCategory.QUOTE,
        ticker="005930", status="COMPLETED", metadata_json={"continuation_count": 0},
    )
    response = KiwoomReadOnlyResponseAudit(
        request_id=request.request_id, status="COMPLETED", metadata_json={"record_count": 1},
    )
    repository.save_kiwoom_readonly_request(request)
    repository.save_kiwoom_readonly_response(response)

    assert repository.list_kiwoom_readonly_requests(api_id="RO_QUOTE")[0] == request
    assert repository.list_kiwoom_readonly_responses(request_id=request.request_id)[0] == response
    assert "token" not in request.model_dump_json().lower()
    assert "authorization" not in response.model_dump_json().lower()
