import pytest

from stock_risk_mcp.kiwoom_transport import (
    DisabledNetworkError,
    FakeKiwoomTransport,
    RealKiwoomHttpTransport,
)


def test_fake_transport_is_deterministic_and_supports_continuation_error() -> None:
    transport = FakeKiwoomTransport()
    first = transport.post("/readonly/quote", {"authorization": "Bearer fake"}, {"ticker": "005930"})
    second = transport.post("/readonly/quote", {"authorization": "Bearer fake"}, {"ticker": "005930"})

    assert first == second
    assert transport.calls[0] == {"path": "/readonly/quote", "body": {"ticker": "005930"}}
    error = FakeKiwoomTransport({"/readonly/quote": {"status": "FAILED", "error": "fake error"}})
    assert error.post("/readonly/quote", {}, {})["error"] == "fake error"


def test_real_kiwoom_transport_is_always_disabled() -> None:
    with pytest.raises(DisabledNetworkError):
        RealKiwoomHttpTransport().post("/readonly/quote", {}, {})
