import pytest

from stock_risk_mcp.kiwoom_mock_execution_transport import (
    FakeKiwoomExecutionTransport,
    KiwoomMockExecutionEndpointAllowlist,
)


def test_kiwoom_mock_execution_allowlist_is_exact() -> None:
    allowlist = KiwoomMockExecutionEndpointAllowlist()
    assert allowlist.validate("KIWOOM_MOCK_ORDER_SUBMIT", "/kiwoom-mock/order/submit")
    assert allowlist.validate("KIWOOM_MOCK_ORDER_CANCEL", "/kiwoom-mock/order/cancel")
    assert allowlist.validate("KIWOOM_MOCK_ORDER_STATUS", "/kiwoom-mock/order/status")
    with pytest.raises(ValueError):
        allowlist.validate("KIWOOM_MOCK_ORDER_SUBMIT", "/orders")


def test_fake_kiwoom_execution_transport_is_deterministic() -> None:
    transport = FakeKiwoomExecutionTransport()
    submitted = transport.post("/kiwoom-mock/order/submit", {
        "broker_order_request_id": "broker_request_1", "quantity": 2, "fill_price": 100,
    })
    cancelled = transport.post("/kiwoom-mock/order/cancel", {"mock_order_id": submitted["mock_order_id"]})
    status = transport.post("/kiwoom-mock/order/status", {"mock_order_id": submitted["mock_order_id"]})

    assert submitted["mock_order_id"] == "kiwoom_mock_order_broker_request_1"
    assert submitted["status"] == "FILLED"
    assert cancelled["status"] == "CANCELLED"
    assert status["status"] == "CANCELLED"
    assert transport.calls[0] == {"path": "/kiwoom-mock/order/submit"}
