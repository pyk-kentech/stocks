import pytest

from stock_risk_mcp.kiwoom_credentials import load_kiwoom_credentials
from stock_risk_mcp.kiwoom_real_readonly_models import KiwoomCredentialSource, KiwoomRealNetworkConfig
from stock_risk_mcp.kiwoom_real_readonly_transport import KiwoomRealReadOnlyPolicyError, RealKiwoomTokenProvider


class FakeAuthClient:
    def __init__(self):
        self.calls = []

    def post(self, url, headers, body, timeout_seconds):
        self.calls.append({"url": url, "headers": headers, "body": body})
        return {"status_code": 200, "body": {"token": "fake-access-token"}}


def test_real_token_provider_requires_explicit_auth_opt_in():
    client = FakeAuthClient()
    credentials = load_kiwoom_credentials(
        KiwoomCredentialSource.ENV,
        env={"KIWOOM_APPKEY": "fake-app", "KIWOOM_SECRETKEY": "fake-secret"},
    )
    provider = RealKiwoomTokenProvider(client)

    with pytest.raises(KiwoomRealReadOnlyPolicyError, match="auth token request"):
        provider.get_token(KiwoomRealNetworkConfig(enabled=True), credentials)
    assert client.calls == []

    token = provider.get_token(
        KiwoomRealNetworkConfig(enabled=True, allow_auth_token_request=True), credentials
    )
    assert token == "fake-access-token"
    assert client.calls[0]["url"] == "https://mockapi.kiwoom.com/oauth2/token"
    assert "secretkey" in client.calls[0]["body"]
