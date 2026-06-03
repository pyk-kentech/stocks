from __future__ import annotations

from pathlib import Path

from stock_risk_mcp.adapters.base import MarketDataAdapter
from stock_risk_mcp.adapters.file_utils import find_record_by_ticker, load_records
from stock_risk_mcp.models import MarketSnapshot


class FileMarketDataAdapter(MarketDataAdapter):
    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self.records = load_records(self.path)

    def get_market_snapshot(self, ticker: str) -> MarketSnapshot:
        return MarketSnapshot.model_validate(find_record_by_ticker(self.records, ticker))
