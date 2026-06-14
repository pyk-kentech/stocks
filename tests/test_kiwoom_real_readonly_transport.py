import pytest

from stock_risk_mcp.kiwoom_credentials import load_kiwoom_credentials
from stock_risk_mcp.kiwoom_real_readonly_models import (
    KiwoomCredentialSource,
    KiwoomRealNetworkConfig,
    KiwoomRealNetworkEnvironment,
)
from stock_risk_mcp.kiwoom_real_readonly_transport import (
    FakeKiwoomTokenProvider,
    KiwoomRealReadOnlyPolicyError,
    RealKiwoomReadOnlyHttpTransport,
)


class FakeHttpClient:
    def __init__(self):
        self.calls = []

    def post(self, url, headers, body, timeout_seconds):
        self.calls.append({"url": url, "headers": headers, "body": body, "timeout": timeout_seconds})
        return {"status_code": 200, "body": {"return_code": 0, "items": [{"stk_cd": "005930"}]}}


def enabled_config(**changes):
    return KiwoomRealNetworkConfig(enabled=True, **changes)


def credentials():
    return load_kiwoom_credentials(
        KiwoomCredentialSource.ENV,
        env={"KIWOOM_APPKEY": "fake-app", "KIWOOM_SECRETKEY": "fake-secret"},
    )


def test_selected_manifest_readonly_endpoint_is_allowed_with_fake_client():
    client = FakeHttpClient()
    transport = RealKiwoomReadOnlyHttpTransport(
        enabled_config(), credentials(), FakeKiwoomTokenProvider(), client
    )

    result = transport.post("ka10001", {"stk_cd": "005930"})

    assert result["status"] == "COMPLETED"
    assert client.calls[0]["url"] == "https://mockapi.kiwoom.com/api/dostk/stkinfo"
    assert client.calls[0]["headers"]["api-id"] == "ka10001"


@pytest.mark.parametrize("api_id", ["ka10171", "kt10000", "kt00001", "au10001", "missing"])
def test_transport_blocks_websocket_order_account_auth_and_unknown(api_id):
    client = FakeHttpClient()
    transport = RealKiwoomReadOnlyHttpTransport(
        enabled_config(), credentials(), FakeKiwoomTokenProvider(), client
    )

    with pytest.raises(KiwoomRealReadOnlyPolicyError):
        transport.post(api_id, {})

    assert client.calls == []


def test_transport_requires_exact_mock_base_url_and_blocks_prod():
    for config in (
        enabled_config(base_url="https://mockapi.kiwoom.com/"),
        enabled_config(base_url="https://example.com"),
        enabled_config(environment=KiwoomRealNetworkEnvironment.PROD_READONLY_DISABLED),
    ):
        client = FakeHttpClient()
        transport = RealKiwoomReadOnlyHttpTransport(config, credentials(), FakeKiwoomTokenProvider(), client)
        with pytest.raises(KiwoomRealReadOnlyPolicyError):
            transport.post("ka10001", {})
        assert client.calls == []


def test_transport_enforces_per_run_request_limit():
    client = FakeHttpClient()
    transport = RealKiwoomReadOnlyHttpTransport(
        enabled_config(max_requests_per_run=1), credentials(), FakeKiwoomTokenProvider(), client
    )
    transport.post("ka10001", {})
    with pytest.raises(KiwoomRealReadOnlyPolicyError, match="request limit"):
        transport.post("ka10004", {})
    assert len(client.calls) == 1
