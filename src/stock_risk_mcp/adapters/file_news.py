from __future__ import annotations

from pathlib import Path

from stock_risk_mcp.adapters.file_utils import load_records
from stock_risk_mcp.models import NewsEvent


class FileNewsAdapter:
    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self.records = load_records(self.path)

    def get_news_events(self, ticker: str) -> list[NewsEvent]:
        symbol = ticker.upper()
        return [
            NewsEvent.model_validate(record)
            for record in self.records
            if str(record.get("ticker", "")).upper() == symbol
        ]
