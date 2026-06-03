from __future__ import annotations

from datetime import date
from pathlib import Path

from stock_risk_mcp.adapters.base import MarketDataAdapter
from stock_risk_mcp.adapters.file_price_history import FilePriceHistoryAdapter
from stock_risk_mcp.models import Evidence, MarketSnapshot, PriceBar, SourceType
from stock_risk_mcp.price_history import (
    calculate_avg_dollar_volume,
    calculate_daily_return_volatility,
    calculate_return_pct_from_bars,
    latest_bar,
    normalize_ticker,
    sort_price_bars,
)
from stock_risk_mcp.repository import RiskRepository


class PriceHistoryMarketDataAdapter(MarketDataAdapter):
    def __init__(
        self,
        repository: RiskRepository | None = None,
        price_history_file: str | Path | None = None,
        source_name: str = "price_history_db",
    ) -> None:
        self.repository = repository
        self.price_history_file = Path(price_history_file) if price_history_file else None
        self.source_name = source_name

    def get_market_snapshot(self, ticker: str) -> MarketSnapshot:
        symbol = normalize_ticker(ticker)
        bars = [bar for bar in self._load_bars(symbol) if bar.ticker == symbol]
        if not bars:
            raise ValueError(f"No price history found for ticker {symbol}")

        sorted_bars = sort_price_bars(bars)
        current = latest_bar(sorted_bars)
        return MarketSnapshot(
            ticker=symbol,
            price=current.close,
            market_cap_usd=None,
            avg_dollar_volume_20d=calculate_avg_dollar_volume(sorted_bars, 20),
            return_5d_pct=calculate_return_pct_from_bars(sorted_bars, 5),
            return_20d_pct=calculate_return_pct_from_bars(sorted_bars, 20),
            volatility_20d_pct=calculate_daily_return_volatility(sorted_bars, 20),
            sector=None,
            market_data_evidence=Evidence(
                source_name=self.source_name,
                source_type=SourceType.FILE if self.price_history_file else SourceType.SYSTEM,
                observed_at=None,
                raw_reference=f"{symbol}:{current.date.isoformat()}",
                confidence=1.0,
            ),
        )

    def _load_bars(self, ticker: str) -> list[PriceBar]:
        if self.price_history_file is not None:
            return FilePriceHistoryAdapter(self.price_history_file).load_price_bars()
        if self.repository is not None:
            return self.repository.get_all_price_history(ticker)
        raise ValueError("PriceHistoryMarketDataAdapter requires repository or price_history_file")
