from __future__ import annotations

from datetime import date, timedelta
from pathlib import Path

from stock_risk_mcp.adapters.file_price_history import FilePriceHistoryAdapter
from stock_risk_mcp.models import PriceBar
from stock_risk_mcp.price_history import sort_price_bars


class AsOfPriceHistoryProvider:
    def __init__(self, repository=None, price_history_file: str | Path | None = None) -> None:
        if repository is None and price_history_file is None:
            raise ValueError("repository or price_history_file is required")
        self.repository = repository
        self.file_bars = (
            FilePriceHistoryAdapter(Path(price_history_file)).load_price_bars()
            if price_history_file is not None
            else None
        )

    def get_history_until(self, ticker: str, as_of_date: date, min_bars: int = 120) -> list[PriceBar]:
        bars = [bar for bar in self._bars(ticker) if bar.date <= as_of_date]
        return bars if len(bars) >= min_bars else []

    def get_forward_history(self, ticker: str, after_date: date, horizon_days: int) -> list[PriceBar]:
        end_date = after_date + timedelta(days=horizon_days)
        return [bar for bar in self._bars(ticker) if after_date < bar.date <= end_date]

    def _bars(self, ticker: str) -> list[PriceBar]:
        symbol = ticker.strip().upper()
        source = self.file_bars if self.file_bars is not None else self.repository.get_all_price_history(symbol)
        return [bar for bar in sort_price_bars(source) if bar.ticker == symbol]
