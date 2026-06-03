from __future__ import annotations

from pathlib import Path

from stock_risk_mcp.adapters.file_utils import load_records
from stock_risk_mcp.models import PriceBar


class FilePriceHistoryAdapter:
    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)

    def load_price_bars(self) -> list[PriceBar]:
        return [PriceBar.model_validate(_normalize_empty_strings(record)) for record in load_records(self.path)]


def _normalize_empty_strings(record: dict) -> dict:
    return {key: (None if value == "" else value) for key, value in record.items()}
