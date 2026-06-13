from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from stock_risk_mcp.adapters.file_utils import load_records
from stock_risk_mcp.realtime_market_data import MarketDataEvent, MarketRegion


class LocalReplayMarketDataProvider:
    provider_name = "local-replay"

    def __init__(self, path: str | Path, region: MarketRegion) -> None:
        self.path = Path(path)
        self.region = region
        self.warnings: list[str] = []

    def iter_events(self, symbols: list[str], start: datetime | None, end: datetime | None):
        requested = {symbol.strip().upper() for symbol in symbols}
        events: list[MarketDataEvent] = []
        for index, record in enumerate(load_records(self.path), start=1):
            try:
                payload = {key: (None if value == "" else value) for key, value in record.items()}
                payload.setdefault("region", self.region.value)
                payload.setdefault("source_name", self.provider_name)
                payload.setdefault("raw_payload_json", json.dumps(record, ensure_ascii=False))
                event = MarketDataEvent.model_validate(payload)
                if event.region != self.region or event.symbol not in requested:
                    continue
                if start is not None and event.event_time < start:
                    continue
                if end is not None and event.event_time > end:
                    continue
                events.append(event)
            except Exception as exc:
                self.warnings.append(f"invalid replay row {index}: {exc}")
        yield from sorted(events, key=lambda item: item.event_time)
