from __future__ import annotations

from datetime import date, datetime
from enum import StrEnum
from uuid import uuid4

from pydantic import Field

from stock_risk_mcp.models import StrictModel


class ConnectorType(StrEnum):
    MARKET_DATA = "MARKET_DATA"
    NEWS = "NEWS"
    DILUTION = "DILUTION"
    TOSS_PORTFOLIO = "TOSS_PORTFOLIO"
    FLOW = "FLOW"
    COMPLIANCE = "COMPLIANCE"
    FX = "FX"
    UNKNOWN = "UNKNOWN"


class ConnectorMode(StrEnum):
    MOCK = "MOCK"
    LOCAL_FILE = "LOCAL_FILE"
    MANUAL_EXPORT = "MANUAL_EXPORT"
    DISABLED = "DISABLED"


class ConnectorRunStatus(StrEnum):
    CREATED = "CREATED"
    COMPLETED = "COMPLETED"
    PARTIAL = "PARTIAL"
    FAILED = "FAILED"
    DISABLED = "DISABLED"


class ConnectorOutputFormat(StrEnum):
    CSV = "CSV"
    JSON = "JSON"


class ConnectorOutput(StrictModel):
    connector_name: str
    connector_type: ConnectorType
    output_format: ConnectorOutputFormat
    output_path: str
    row_count: int = Field(ge=0)
    created_at: datetime = Field(default_factory=datetime.now)
    metadata: dict = Field(default_factory=dict)


class ConnectorRun(StrictModel):
    connector_run_id: str = Field(default_factory=lambda: f"connector_{uuid4().hex}")
    as_of_date: date
    connector_name: str
    connector_type: ConnectorType
    mode: ConnectorMode
    status: ConnectorRunStatus = ConnectorRunStatus.CREATED
    output_path: str | None = None
    row_count: int = Field(0, ge=0)
    warnings: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)
    metadata: dict = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.now)
    completed_at: datetime | None = None


class ConnectorResult(StrictModel):
    connector_run: ConnectorRun
    output: ConnectorOutput | None = None
