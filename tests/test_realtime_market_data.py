from datetime import datetime

import pytest

from stock_risk_mcp.realtime_market_data import (
    MarketDataEvent, MarketDataEventType, MarketRegion, RealtimeMonitorRun,
    RealtimeMonitorRunStatus, WatchlistEntry, WatchlistStatus,
)


def test_realtime_models_normalize_symbols_and_validate_counts() -> None:
    event = MarketDataEvent(
        symbol=" aapl ", region=MarketRegion.US, event_type=MarketDataEventType.BAR_1M,
        event_time=datetime(2026, 6, 13, 10), close=100, volume=1000, source_name="test",
    )
    entry = WatchlistEntry(
        symbol=" aapl ", region=MarketRegion.US, status=WatchlistStatus.HOT,
        first_seen_at=event.event_time, last_seen_at=event.event_time,
        promotion_reason="return", score=10, metrics_json="{}",
    )
    run = RealtimeMonitorRun(
        as_of=event.event_time, status=RealtimeMonitorRunStatus.COMPLETED,
        provider_name="mock", universe_count=1, processed_event_count=1,
        candidate_count=1, hot_watchlist_count=1,
    )

    assert event.symbol == entry.symbol == "AAPL"
    assert run.realtime_monitor_run_id.startswith("realtime_")
    with pytest.raises(ValueError):
        MarketDataEvent(
            symbol="", region=MarketRegion.US, event_type=MarketDataEventType.TRADE,
            event_time=event.event_time, source_name="test",
        )
