from __future__ import annotations

from datetime import date, datetime
from enum import StrEnum
from uuid import uuid4

from pydantic import Field, model_validator

from stock_risk_mcp.models import StrictModel


class NormalizerType(StrEnum):
    PRICE_HISTORY = "PRICE_HISTORY"
    NEWS_SIGNAL = "NEWS_SIGNAL"
    DILUTION_SIGNAL = "DILUTION_SIGNAL"
    TOSS_SIGNAL = "TOSS_SIGNAL"
    FLOW_SIGNAL = "FLOW_SIGNAL"
    COMPLIANCE = "COMPLIANCE"
    FX_RATE = "FX_RATE"
    UNKNOWN = "UNKNOWN"


class NormalizeRunStatus(StrEnum):
    CREATED = "CREATED"
    COMPLETED = "COMPLETED"
    PARTIAL = "PARTIAL"
    FAILED = "FAILED"
    NO_INPUT = "NO_INPUT"


class NormalizedOutputFormat(StrEnum):
    CSV = "CSV"
    JSON = "JSON"


class NormalizeSourceResult(StrictModel):
    normalizer_name: str
    normalizer_type: NormalizerType
    input_path: str
    output_path: str | None = None
    row_count: int = Field(0, ge=0)
    normalized_count: int = Field(0, ge=0)
    skipped_count: int = Field(0, ge=0)
    error_count: int = Field(0, ge=0)
    warnings: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)


class NormalizeRun(StrictModel):
    normalize_run_id: str = Field(default_factory=lambda: f"normalize_{uuid4().hex}")
    as_of_date: date | None = None
    status: NormalizeRunStatus = NormalizeRunStatus.CREATED
    source_results: list[NormalizeSourceResult] = Field(default_factory=list)
    total_row_count: int = Field(0, ge=0)
    total_normalized_count: int = Field(0, ge=0)
    total_skipped_count: int = Field(0, ge=0)
    total_error_count: int = Field(0, ge=0)
    output_paths: list[str] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.now)
    completed_at: datetime | None = None

    @model_validator(mode="after")
    def calculate_totals(self) -> "NormalizeRun":
        self.total_row_count = sum(item.row_count for item in self.source_results)
        self.total_normalized_count = sum(item.normalized_count for item in self.source_results)
        self.total_skipped_count = sum(item.skipped_count for item in self.source_results)
        self.total_error_count = sum(item.error_count for item in self.source_results)
        self.output_paths = [item.output_path for item in self.source_results if item.output_path]
        return self
