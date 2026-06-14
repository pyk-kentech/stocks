from stock_risk_mcp.kiwoom_readonly_service import KiwoomReadOnlyService
from stock_risk_mcp.repository import RiskRepository


def test_kiwoom_service_persists_sanitized_quote_audits(tmp_path) -> None:
    repository = RiskRepository(tmp_path / "risk.sqlite3")
    result = KiwoomReadOnlyService(repository).get_quote("005930")

    assert result["status"] == "COMPLETED"
    assert result["request_id"]
    assert result["response_id"]
    assert repository.list_kiwoom_readonly_requests()
    assert repository.list_kiwoom_readonly_responses()
    assert "token" not in str(result).lower()
    assert "authorization" not in str(result).lower()
