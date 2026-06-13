from datetime import datetime

from stock_risk_mcp.realtime_market_data import MarketRegion
from stock_risk_mcp.realtime_provider_mock import MockRealtimeMarketDataProvider


def test_mock_realtime_provider_is_deterministic() -> None:
    provider = MockRealtimeMarketDataProvider(MarketRegion.US)

    first = list(provider.iter_events(["AAPL"], datetime(2026, 6, 13, 9, 30), None))
    second = list(provider.iter_events(["AAPL"], datetime(2026, 6, 13, 9, 30), None))

    assert first == second
    assert len(first) == 16
    assert first[-1].volume > first[0].volume
