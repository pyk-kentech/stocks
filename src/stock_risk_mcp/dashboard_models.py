from __future__ import annotations

from datetime import date, datetime
from enum import StrEnum
from uuid import uuid4

from pydantic import Field

from stock_risk_mcp.models import StrictModel
from stock_risk_mcp.notifications import NotificationSeverity


class DashboardType(StrEnum):
    OVERVIEW = "OVERVIEW"
    PIPELINE_RUN = "PIPELINE_RUN"
    DAILY = "DAILY"
    POLICY = "POLICY"
    ALERTS = "ALERTS"
    REPORTS = "REPORTS"


class DashboardBuildStatus(StrEnum):
    COMPLETED = "COMPLETED"
    PARTIAL = "PARTIAL"
    FAILED = "FAILED"
    NO_DATA = "NO_DATA"


class DashboardSection(StrictModel):
    title: str
    summary: str
    html: str
    severity: NotificationSeverity = NotificationSeverity.INFO


class DashboardBuildResult(StrictModel):
    dashboard_id: str = Field(default_factory=lambda: f"dashboard_{uuid4().hex}")
    dashboard_type: DashboardType
    as_of_date: date | None = None
    source_id: str | None = None
    status: DashboardBuildStatus
    output_path: str | None = None
    section_count: int = 0
    warnings: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)
    generated_at: datetime = Field(default_factory=datetime.now)
