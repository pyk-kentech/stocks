from datetime import datetime

from stock_risk_mcp.dynamic_watchlist import DynamicWatchlist, WatchlistPromotionRule
from stock_risk_mcp.realtime_market_data import MarketRegion, RollingMarketMetrics, WatchlistStatus


def test_dynamic_watchlist_promotes_rules_caps_hot_and_blocks_bad_tick() -> None:
    engine = DynamicWatchlist(WatchlistPromotionRule(min_dollar_volume_5m=1000, max_hot_watchlist_size=2))
    metrics = [
        _metrics("RET", return_5m_pct=4),
        _metrics("RVOL", relative_volume=4),
        _metrics("DOLLAR", dollar_volume_5m=2000),
        _metrics("BAD", return_5m_pct=10, halt_or_bad_tick_warning=True),
    ]

    entries, signals = engine.evaluate(metrics, {})

    assert sum(item.status == WatchlistStatus.HOT for item in entries) == 2
    assert next(item for item in entries if item.symbol == "BAD").status == WatchlistStatus.BLOCKED
    assert len(signals) == 4


def test_existing_hot_becomes_cooling_and_none_rvol_does_not_promote() -> None:
    engine = DynamicWatchlist(WatchlistPromotionRule(min_dollar_volume_5m=1000))
    previous = {"OLD": engine.evaluate([_metrics("OLD", return_5m_pct=4)], {})[0][0]}

    entries, _ = engine.evaluate([_metrics("OLD"), _metrics("NONE", relative_volume=None)], previous)

    assert next(item for item in entries if item.symbol == "OLD").status == WatchlistStatus.COOLING
    assert next(item for item in entries if item.symbol == "NONE").status == WatchlistStatus.CANDIDATE


def _metrics(symbol, **updates):
    base = RollingMarketMetrics(
        symbol=symbol, region=MarketRegion.US, as_of=datetime(2026, 6, 13, 10),
        last_price=100, volume_1m=100, source_name="test",
    )
    return base.model_copy(update=updates)
