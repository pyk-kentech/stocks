from __future__ import annotations

from datetime import date, datetime
from enum import StrEnum
from uuid import uuid4

from pydantic import Field, model_validator

from stock_risk_mcp.models import StrictModel


class ImportSourceType(StrEnum):
    PRICE_HISTORY = "PRICE_HISTORY"
    COMPLIANCE = "COMPLIANCE"
    NEWS_SIGNAL = "NEWS_SIGNAL"
    DILUTION_SIGNAL = "DILUTION_SIGNAL"
    TOSS_SIGNAL = "TOSS_SIGNAL"
    FLOW_SIGNAL = "FLOW_SIGNAL"
    UNKNOWN = "UNKNOWN"


class ImportRunStatus(StrEnum):
    CREATED = "CREATED"
    COMPLETED = "COMPLETED"
    PARTIAL = "PARTIAL"
    FAILED = "FAILED"


class ImportSourceResult(StrictModel):
    source_type: ImportSourceType
    file_path: str
    row_count: int = Field(0, ge=0)
    saved_count: int = Field(0, ge=0)
    skipped_duplicate_count: int = Field(0, ge=0)
    error_count: int = Field(0, ge=0)
    warnings: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)


class ImportRun(StrictModel):
    import_run_id: str = Field(default_factory=lambda: f"import_{uuid4().hex}")
    as_of_date: date | None = None
    status: ImportRunStatus = ImportRunStatus.CREATED
    source_results: list[ImportSourceResult] = Field(default_factory=list)
    total_row_count: int = Field(0, ge=0)
    total_saved_count: int = Field(0, ge=0)
    total_skipped_duplicate_count: int = Field(0, ge=0)
    total_error_count: int = Field(0, ge=0)
    notes: list[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.now)
    completed_at: datetime | None = None

    @model_validator(mode="after")
    def calculate_totals(self) -> "ImportRun":
        self.total_row_count = sum(item.row_count for item in self.source_results)
        self.total_saved_count = sum(item.saved_count for item in self.source_results)
        self.total_skipped_duplicate_count = sum(item.skipped_duplicate_count for item in self.source_results)
        self.total_error_count = sum(item.error_count for item in self.source_results)
        return self
