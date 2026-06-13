from datetime import datetime, timedelta

from stock_risk_mcp.realtime_market_data import MarketDataEvent, MarketDataEventType, MarketRegion
from stock_risk_mcp.rolling_market_metrics import RollingMarketMetricsCalculator


def test_relative_volume_uses_previous_max_15_and_excludes_current() -> None:
    calc = RollingMarketMetricsCalculator()
    start = datetime(2026, 6, 13, 9, 30)
    for index in range(16):
        calc.add(_bar(start + timedelta(minutes=index), 100 + index, 100 if index < 15 else 400))

    metrics = calc.latest("AAPL", MarketRegion.US)

    assert metrics.relative_volume == 4
    assert metrics.volume_1m == 400
    assert metrics.return_5m_pct is not None
    assert metrics.breakout_15m is True


def test_relative_volume_handles_one_no_history_and_invalid_volumes() -> None:
    start = datetime(2026, 6, 13, 9, 30)
    one = RollingMarketMetricsCalculator()
    one.add(_bar(start, 100, 100))
    one.add(_bar(start + timedelta(minutes=1), 101, 300))
    none = RollingMarketMetricsCalculator()
    none.add(_bar(start, 100, 300))
    invalid = RollingMarketMetricsCalculator()
    invalid.add(_bar(start, 100, 0))
    invalid.add(_bar(start + timedelta(minutes=1), 101, -1))

    assert one.latest("AAPL", MarketRegion.US).relative_volume == 3
    assert "low_history_for_relative_volume" in one.latest("AAPL", MarketRegion.US).warnings
    assert none.latest("AAPL", MarketRegion.US).relative_volume is None
    assert invalid.latest("AAPL", MarketRegion.US).relative_volume is None
    assert "bad_volume" in invalid.latest("AAPL", MarketRegion.US).warnings


def test_out_of_order_event_is_marked_as_bad_tick() -> None:
    start = datetime(2026, 6, 13, 9, 30)
    calc = RollingMarketMetricsCalculator()
    calc.add(_bar(start + timedelta(minutes=1), 101, 100))
    calc.add(_bar(start, 100, 100))

    metrics = calc.latest("AAPL", MarketRegion.US)

    assert metrics.halt_or_bad_tick_warning is True
    assert "out_of_order_event" in metrics.warnings


def test_relative_volume_uses_previous_15_valid_buckets() -> None:
    start = datetime(2026, 6, 13, 9, 30)
    calc = RollingMarketMetricsCalculator()
    calc.add(_bar(start, 100, 200))
    for index in range(1, 15):
        calc.add(_bar(start + timedelta(minutes=index), 100, 100))
    calc.add(_bar(start + timedelta(minutes=15), 100, 0))
    calc.add(_bar(start + timedelta(minutes=16), 100, 300))

    metrics = calc.latest("AAPL", MarketRegion.US)

    assert metrics.relative_volume == 300 / ((200 + 14 * 100) / 15)


def _bar(when, close, volume):
    return MarketDataEvent(
        symbol="AAPL", region=MarketRegion.US, event_type=MarketDataEventType.BAR_1M,
        event_time=when, close=close, high=close, low=close, volume=volume,
        dollar_volume=close * volume, source_name="test",
    )
