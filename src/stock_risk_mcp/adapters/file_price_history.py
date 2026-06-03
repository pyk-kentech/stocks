from __future__ import annotations

from pathlib import Path

from stock_risk_mcp.adapters.file_utils import load_records
from stock_risk_mcp.models import PriceBar


class FilePriceHistoryAdapter:
    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)

    def load_price_bars(self) -> list[PriceBar]:
        return [PriceBar.model_validate(record) for record in load_records(self.path)]
