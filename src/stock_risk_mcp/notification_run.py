from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from uuid import uuid4

from pydantic import Field

from stock_risk_mcp.models import StrictModel
from stock_risk_mcp.notifications import NotificationChannelType


class NotificationRunStatus(StrEnum):
    CREATED = "CREATED"
    COMPLETED = "COMPLETED"
    PARTIAL = "PARTIAL"
    FAILED = "FAILED"
    DISABLED = "DISABLED"
    NO_ALERTS = "NO_ALERTS"


class NotificationRun(StrictModel):
    notification_run_id: str = Field(default_factory=lambda: f"notification_run_{uuid4().hex}")
    source_type: str
    source_id: str
    channel_type: NotificationChannelType
    status: NotificationRunStatus = NotificationRunStatus.CREATED
    message_count: int = 0
    delivered_count: int = 0
    skipped_duplicate_count: int = 0
    failed_count: int = 0
    output_path: str | None = None
    warnings: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.now)
    completed_at: datetime | None = None
