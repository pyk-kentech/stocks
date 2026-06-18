from __future__ import annotations

from datetime import datetime
from pathlib import Path

from pydantic import Field, field_validator

from stock_risk_mcp.historical_data_models import (
    HistoricalDataAdjustmentPolicy,
    HistoricalDataIngestionConfig,
    HistoricalDataProviderProvenance,
    HistoricalDataSourceDescriptor,
    aware,
)
from stock_risk_mcp.models import StrictModel


class HistoricalDataFixture(StrictModel):
    schema_version: str
    fixture_id: str = Field(..., min_length=1)
    created_at: datetime
    ingestion_config: HistoricalDataIngestionConfig
    source_descriptor: HistoricalDataSourceDescriptor
    provider_provenance: HistoricalDataProviderProvenance
    adjustment_policy: HistoricalDataAdjustmentPolicy
    ingestion_batch_id: str = Field(..., min_length=1)
    audit_record_ids: list[str] = Field(default_factory=list)

    _created = field_validator("created_at")(aware)

    @field_validator("schema_version")
    @classmethod
    def exact_schema(cls, value: str) -> str:
        if value != "5.1-historical-data-ingestion-fixture":
            raise ValueError("schema_version must be exactly 5.1-historical-data-ingestion-fixture")
        return value


def load_historical_data_fixture(path) -> HistoricalDataFixture:
    try:
        return HistoricalDataFixture.model_validate_json(Path(path).read_text(encoding="utf-8"))
    except Exception as exc:
        raise ValueError(f"invalid historical data fixture: {exc}") from exc
