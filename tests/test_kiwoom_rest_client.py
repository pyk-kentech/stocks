from datetime import datetime, timedelta

from stock_risk_mcp.kiwoom_readonly_models import KiwoomEnvironment, KiwoomToken
from stock_risk_mcp.kiwoom_rest_client import KiwoomRestClient
from stock_risk_mcp.kiwoom_transport import FakeKiwoomTransport


def test_client_handles_continuation_without_exposing_token_or_headers() -> None:
    transport = FakeKiwoomTransport({
        "/readonly/ranking": [
            {"status": "COMPLETED", "records": [{"ticker": "A"}], "cont-yn": "Y", "next-key": "2"},
            {"status": "COMPLETED", "records": [{"ticker": "B"}], "cont-yn": "N"},
        ]
    })
    client = KiwoomRestClient(transport=transport, token=_token())
    result = client.request_readonly("RO_RANKING", "/readonly/ranking", {"rank_type": "volume"})

    assert [item["ticker"] for item in result["records"]] == ["A", "B"]
    assert result["continuation_count"] == 1
    assert "token" not in str(result).lower()
    assert "authorization" not in str(result).lower()


def test_client_normalizes_allowlist_and_transport_errors() -> None:
    client = KiwoomRestClient(transport=FakeKiwoomTransport(), token=_token())
    assert client.request_readonly("BAD", "/order", {})["status"] == "FAILED"


def _token():
    now = datetime.now()
    return KiwoomToken(
        access_token="fake-token", token_type="Bearer", issued_at=now,
        expires_at=now + timedelta(hours=1), environment=KiwoomEnvironment.MOCK,
    )
