from stock_risk_mcp.market_universe import MarketUniverseRegistry
from stock_risk_mcp.realtime_market_data import MarketRegion


def test_market_universe_normalizes_dedupes_and_limits() -> None:
    registry = MarketUniverseRegistry(max_symbols=2)

    result = registry.register([" aapl ", "AAPL", "nvda", "tsla"], MarketRegion.US)

    assert result.symbols == ["AAPL", "NVDA"]
    assert any("max_symbols" in warning for warning in result.warnings)


def test_market_universe_blocks_unknown_region() -> None:
    result = MarketUniverseRegistry().register(["AAPL"], MarketRegion.UNKNOWN)
    assert result.symbols == []
    assert result.blocked_symbols == ["AAPL"]
