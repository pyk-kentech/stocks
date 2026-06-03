from __future__ import annotations

from pathlib import Path

from stock_risk_mcp.adapters.base import TossSignalAdapter
from stock_risk_mcp.adapters.file_utils import find_record_by_ticker, load_records
from stock_risk_mcp.models import TossSignal


class FileTossSignalAdapter(TossSignalAdapter):
    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self.records = load_records(self.path)

    def get_toss_signal(self, ticker: str) -> TossSignal:
        record = dict(find_record_by_ticker(self.records, ticker))
        record.pop("ticker", None)
        return TossSignal.model_validate(record)
