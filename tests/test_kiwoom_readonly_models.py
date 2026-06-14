from datetime import datetime, timedelta

from stock_risk_mcp.kiwoom_readonly_models import (
    KiwoomEndpointCategory,
    KiwoomEnvironment,
    KiwoomQuote,
    KiwoomReadOnlyEndpoint,
    KiwoomToken,
)


def test_kiwoom_models_serialize_and_normalize() -> None:
    endpoint = KiwoomReadOnlyEndpoint(
        api_id="RO_QUOTE", path="/readonly/quote", category=KiwoomEndpointCategory.QUOTE,
        description="internal quote", read_only=True, enabled=True,
    )
    token = KiwoomToken(
        access_token="fake-token", token_type="Bearer",
        expires_at=datetime.now() + timedelta(hours=1), issued_at=datetime.now(),
        environment=KiwoomEnvironment.MOCK,
    )
    quote = KiwoomQuote(
        ticker=" 005930 ", price=70000, change=100, change_pct=0.1, volume=1000,
        trading_value=70_000_000, observed_at=datetime.now(), source_name="fake", raw_json={},
    )

    assert endpoint.model_dump(mode="json")["category"] == "QUOTE"
    assert token.environment == KiwoomEnvironment.MOCK
    assert quote.ticker == "005930"
