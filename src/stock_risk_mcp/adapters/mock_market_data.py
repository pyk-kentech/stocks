from __future__ import annotations

from stock_risk_mcp.adapters.base import MarketDataAdapter
from stock_risk_mcp.models import MarketSnapshot


class MockMarketDataAdapter(MarketDataAdapter):
    def get_market_snapshot(self, ticker: str) -> MarketSnapshot:
        symbol = ticker.upper()
        if symbol == "PUMP":
            return MarketSnapshot(
                ticker=symbol,
                price=4.2,
                market_cap_usd=900_000_000,
                avg_dollar_volume_20d=80_000_000,
                return_5d_pct=120,
                return_20d_pct=180,
                volatility_20d_pct=14,
                sector="Technology",
            )
        if symbol == "SAFE":
            return MarketSnapshot(
                ticker=symbol,
                price=125.5,
                market_cap_usd=30_000_000_000,
                avg_dollar_volume_20d=120_000_000,
                return_5d_pct=4.5,
                return_20d_pct=8.2,
                volatility_20d_pct=2.5,
                sector="Healthcare",
            )
        if symbol == "WATCH":
            return MarketSnapshot(
                ticker=symbol,
                price=18.4,
                market_cap_usd=750_000_000,
                avg_dollar_volume_20d=18_000_000,
                return_5d_pct=12,
                return_20d_pct=28,
                volatility_20d_pct=6.5,
                sector="Consumer",
            )
        if symbol == "UNKNOWN":
            return MarketSnapshot(
                ticker=symbol,
                price=9.8,
                market_cap_usd=None,
                avg_dollar_volume_20d=None,
                return_5d_pct=None,
                return_20d_pct=None,
                volatility_20d_pct=None,
                sector=None,
            )
        return MarketSnapshot(
            ticker=symbol,
            price=22.0,
            market_cap_usd=1_500_000_000,
            avg_dollar_volume_20d=35_000_000,
            return_5d_pct=7,
            return_20d_pct=15,
            volatility_20d_pct=4.5,
            sector="Industrial",
        )
