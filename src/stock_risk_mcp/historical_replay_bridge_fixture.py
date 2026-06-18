from __future__ import annotations

from datetime import datetime
from pathlib import Path

from pydantic import Field, field_validator

from stock_risk_mcp.historical_calendar_models import HistoricalCalendarEventSnapshot
from stock_risk_mcp.historical_data_models import HistoricalMarketDataSnapshot
from stock_risk_mcp.historical_replay_bridge_models import HistoricalReplayBridgeConfig, aware
from stock_risk_mcp.historical_scanner_replay_models import HistoricalScannerReplayCandidateSeed
from stock_risk_mcp.models import StrictModel


class HistoricalReplayBridgeFixture(StrictModel):
    schema_version: str
    fixture_id: str = Field(..., min_length=1)
    created_at: datetime
    bridge_config: HistoricalReplayBridgeConfig
    historical_market_data_snapshot: HistoricalMarketDataSnapshot
    historical_calendar_event_snapshot: HistoricalCalendarEventSnapshot | None = None
    scanner_replay_hints: list[HistoricalScannerReplayCandidateSeed] = Field(default_factory=list)

    _created = field_validator("created_at")(aware)

    @field_validator("fixture_id", mode="before")
    @classmethod
    def normalize_fixture_id(cls, value):
        if value is None:
            raise ValueError("fixture_id must not be null")
        cleaned = str(value).strip()
        if not cleaned:
            raise ValueError("fixture_id must not be blank")
        return cleaned

    @field_validator("schema_version")
    @classmethod
    def exact_schema(cls, value: str) -> str:
        if value != "5.2-historical-replay-bridge-fixture":
            raise ValueError("schema_version must be exactly 5.2-historical-replay-bridge-fixture")
        return value


def load_historical_replay_bridge_fixture(path) -> HistoricalReplayBridgeFixture:
    source_path = str(path)
    try:
        return HistoricalReplayBridgeFixture.model_validate_json(Path(path).read_text(encoding="utf-8"))
    except Exception as exc:
        raise ValueError(f"invalid historical replay bridge fixture at {source_path}: {exc}") from exc
