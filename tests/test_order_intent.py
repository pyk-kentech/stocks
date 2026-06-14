from datetime import datetime

from stock_risk_mcp.order_intent import (
    ExecutionMode,
    OrderIntent,
    OrderIntentStatus,
    OrderSide,
    OrderType,
)
from stock_risk_mcp.realtime_market_data import MarketRegion


def test_order_intent_normalizes_ticker_and_defaults_to_created() -> None:
    intent = OrderIntent(
        ticker=" aapl ", region=MarketRegion.US, side=OrderSide.BUY,
        order_type=OrderType.LIMIT, quantity=1, limit_price=100,
        source_type="manual", source_id="test", reason="test", confidence_score=0.5,
    )

    assert intent.ticker == "AAPL"
    assert intent.status == OrderIntentStatus.CREATED
    assert intent.order_intent_id.startswith("intent_")
    assert intent.metadata_json == {}
    assert isinstance(intent.created_at, datetime)
    assert ExecutionMode.PAPER.value == "PAPER"
