from pathlib import Path

import pytest

from stock_risk_mcp.kiwoom_account_read_models import KiwoomAccountReadConfig
from stock_risk_mcp.kiwoom_account_read_transport import KiwoomAccountReadPolicyError, RealKiwoomAccountReadTransport
from stock_risk_mcp.kiwoom_real_readonly_models import KiwoomCredentials, KiwoomCredentialSource


class FakeTokenProvider:
    def get_token(self, config, credentials):
        return "fake-token"


class FakeClient:
    def __init__(self):
        self.calls = []

    def post(self, url, headers, body, timeout_seconds):
        self.calls.append((url, headers, body))
        return {"status_code": 200, "body": {"holdings": []}}


def test_transport_allows_only_account_read_manifest_ids_with_fake_dependencies():
    client = FakeClient()
    transport = RealKiwoomAccountReadTransport(
        KiwoomAccountReadConfig(),
        KiwoomCredentials(
            appkey="fake", secretkey="fake", account_number="fake-account",
            source=KiwoomCredentialSource.ENV,
        ),
        FakeTokenProvider(),
        client,
    )
    assert transport.request("kt00018")["status"] == "COMPLETED"
    for endpoint_id in ("ka10001", "kt10000", "missing"):
        with pytest.raises(KiwoomAccountReadPolicyError):
            transport.request(endpoint_id)
    assert len(client.calls) == 1


def test_account_read_is_not_wired_to_strategy_system_smoke_or_order_service():
    root = Path(__file__).resolve().parents[1] / "src" / "stock_risk_mcp"
    for name in ("strategy_optimizer.py", "system_smoke.py", "kiwoom_sandbox_order_service.py"):
        assert "kiwoom_account_read" not in (root / name).read_text(encoding="utf-8")
