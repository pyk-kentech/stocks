from __future__ import annotations

from datetime import date, datetime

from pydantic import Field, field_validator

from stock_risk_mcp.models import Evidence, SourceType, StrictModel


NASDAQ_NONCOMPLIANT_SOURCE_NAME = "nasdaq_noncompliant_file"


class ComplianceRecord(StrictModel):
    ticker: str = Field(..., min_length=1)
    source_name: str = NASDAQ_NONCOMPLIANT_SOURCE_NAME
    source_type: SourceType = SourceType.FILE
    company_name: str | None = None
    issue: str | None = None
    deficiency: str | None = None
    notice_date: date | None = None
    source_url: str | None = None
    raw_reference: str | None = None
    observed_at: datetime

    @field_validator("ticker")
    @classmethod
    def normalize_ticker(cls, value: str) -> str:
        return value.strip().upper()


class ComplianceStatus(StrictModel):
    ticker: str = Field(..., min_length=1)
    nasdaq_noncompliant: bool
    records: list[ComplianceRecord]
    evidence: Evidence | None = None

    @field_validator("ticker")
    @classmethod
    def normalize_ticker(cls, value: str) -> str:
        return value.strip().upper()
