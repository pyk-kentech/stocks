import pytest

from stock_risk_mcp.kiwoom_sandbox_order_transport import (
    FakeKiwoomSandboxOrderTransport,
    KiwoomSandboxOrderPolicyError,
)


def test_fake_transport_allows_only_curated_order_endpoints():
    transport = FakeKiwoomSandboxOrderTransport()
    assert transport.post("kt10000", {})["status"] == "ACCEPTED"
    assert transport.post("kt10003", {"broker_order_id": "sandbox-1"})["status"] == "CANCELLED"
    for endpoint_id in ("ka10001", "kt00001", "au10001", "missing"):
        with pytest.raises(KiwoomSandboxOrderPolicyError):
            transport.post(endpoint_id, {})
