from __future__ import annotations

from datetime import datetime, timedelta

from stock_risk_mcp.realtime_market_data import MarketDataEvent, MarketDataEventType, MarketRegion


class MockRealtimeMarketDataProvider:
    provider_name = "mock-realtime"

    def __init__(self, region: MarketRegion) -> None:
        self.region = region
        self.warnings: list[str] = []

    def iter_events(self, symbols: list[str], start: datetime | None, end: datetime | None):
        base = start or datetime(2026, 6, 13, 9, 30)
        for symbol_index, symbol in enumerate(symbols):
            base_price = 100.0 + symbol_index * 10
            for index in range(16):
                event_time = base + timedelta(minutes=index)
                if end is not None and event_time > end:
                    continue
                close = base_price + index * 0.25
                volume = 100.0 if index < 15 else 400.0 + symbol_index
                yield MarketDataEvent(
                    symbol=symbol,
                    region=self.region,
                    event_type=MarketDataEventType.BAR_1M,
                    event_time=event_time,
                    open=close,
                    high=close,
                    low=close,
                    close=close,
                    volume=volume,
                    dollar_volume=close * volume,
                    source_name=self.provider_name,
                )
