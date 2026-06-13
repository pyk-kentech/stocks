from __future__ import annotations

from datetime import date, datetime
from enum import StrEnum
from uuid import uuid4

from pydantic import Field

from stock_risk_mcp.models import StrictModel


class ProviderPackType(StrEnum):
    PRICE = "PRICE"
    FX = "FX"
    PRICE_AND_FX = "PRICE_AND_FX"
    NEWS = "NEWS"
    DILUTION = "DILUTION"
    UNKNOWN = "UNKNOWN"


class ProviderPackRunStatus(StrEnum):
    CREATED = "CREATED"
    COMPLETED = "COMPLETED"
    PARTIAL = "PARTIAL"
    FAILED = "FAILED"
    DISABLED = "DISABLED"


class ProviderPackRun(StrictModel):
    provider_pack_run_id: str = Field(default_factory=lambda: f"provider_pack_{uuid4().hex}")
    provider_pack_type: ProviderPackType
    as_of_date: date
    status: ProviderPackRunStatus = ProviderPackRunStatus.CREATED
    connector_run_ids: list[str] = Field(default_factory=list)
    normalize_run_id: str | None = None
    import_run_id: str | None = None
    output_paths: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.now)
    completed_at: datetime | None = None
