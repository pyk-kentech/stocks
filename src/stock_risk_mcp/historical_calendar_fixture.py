from __future__ import annotations

from datetime import datetime
from pathlib import Path

from pydantic import Field, field_validator

from stock_risk_mcp.historical_calendar_models import TradingCalendarConfig, aware
from stock_risk_mcp.models import StrictModel


class HistoricalCalendarFixture(StrictModel):
    schema_version: str
    fixture_id: str = Field(..., min_length=1)
    created_at: datetime
    calendar_config: TradingCalendarConfig
    session_file_path: str = Field(..., min_length=1)
    market_event_file_path: str = Field(..., min_length=1)
    corporate_event_file_path: str = Field(..., min_length=1)
    calendar_batch_id: str = Field(..., min_length=1)
    source_descriptor_ids: list[str] = Field(default_factory=list)

    _created = field_validator("created_at")(aware)

    @field_validator("schema_version")
    @classmethod
    def exact_schema(cls, value: str) -> str:
        if value != "5.1-historical-calendar-ingestion-fixture":
            raise ValueError("schema_version must be exactly 5.1-historical-calendar-ingestion-fixture")
        return value


def load_historical_calendar_fixture(path) -> HistoricalCalendarFixture:
    try:
        return HistoricalCalendarFixture.model_validate_json(Path(path).read_text(encoding="utf-8"))
    except Exception as exc:
        raise ValueError(f"invalid historical calendar fixture: {exc}") from exc
