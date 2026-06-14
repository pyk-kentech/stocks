from stock_risk_mcp.kiwoom_credentials import load_kiwoom_credentials
from stock_risk_mcp.kiwoom_real_readonly_models import KiwoomCredentialSource, KiwoomRealNetworkConfig
from stock_risk_mcp.kiwoom_real_readonly_service import KiwoomRealReadOnlyService
from stock_risk_mcp.kiwoom_real_readonly_transport import FakeKiwoomTokenProvider, RealKiwoomReadOnlyHttpTransport
from stock_risk_mcp.repository import RiskRepository


class FakeClient:
    def post(self, url, headers, body, timeout_seconds):
        return {"status_code": 200, "body": {"return_code": 0, "secretkey": "response-secret"}}


def test_disabled_health_is_audited_without_credentials(tmp_path):
    repository = RiskRepository(tmp_path / "risk.sqlite3")
    result = KiwoomRealReadOnlyService(repository).health()

    assert result["status"] == "DISABLED"
    assert result["credentials_loaded"] is False
    assert repository.list_kiwoom_real_readonly_runs()[0].status == "DISABLED"


def test_service_persists_redacted_request_and_response_audits(tmp_path):
    repository = RiskRepository(tmp_path / "risk.sqlite3")
    creds = load_kiwoom_credentials(
        KiwoomCredentialSource.ENV,
        env={"KIWOOM_APPKEY": "fake-app", "KIWOOM_SECRETKEY": "fake-secret"},
    )
    config = KiwoomRealNetworkConfig(enabled=True)
    transport = RealKiwoomReadOnlyHttpTransport(config, creds, FakeKiwoomTokenProvider(), FakeClient())
    service = KiwoomRealReadOnlyService(repository, config, creds, transport)

    result = service.request("ka10001", {"stk_cd": "005930", "secretkey": "request-secret"})

    assert result["status"] == "COMPLETED"
    serialized = str(repository.list_kiwoom_real_readonly_requests()) + str(repository.list_kiwoom_real_readonly_responses())
    assert "request-secret" not in serialized
    assert "response-secret" not in serialized
    assert "fake-secret" not in serialized
    assert "authorization" not in serialized.lower()
    assert "secretkey" not in serialized.lower()


def test_blocked_request_is_audited_without_calling_client(tmp_path):
    repository = RiskRepository(tmp_path / "risk.sqlite3")
    service = KiwoomRealReadOnlyService(repository)
    result = service.request("kt10000", {})
    assert result["status"] == "BLOCKED"
    assert repository.list_kiwoom_real_readonly_requests()[0].status == "BLOCKED"
