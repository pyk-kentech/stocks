from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from uuid import uuid4

from pydantic import Field

from stock_risk_mcp.models import StrictModel


class NotificationChannelType(StrEnum):
    CONSOLE = "CONSOLE"
    LOCAL_FILE = "LOCAL_FILE"
    MOCK = "MOCK"
    DISABLED = "DISABLED"
    WEBHOOK_DISABLED = "WEBHOOK_DISABLED"
    EMAIL_DISABLED = "EMAIL_DISABLED"
    TELEGRAM_DISABLED = "TELEGRAM_DISABLED"
    DISCORD_DISABLED = "DISCORD_DISABLED"
    SLACK_DISABLED = "SLACK_DISABLED"


class NotificationSeverity(StrEnum):
    INFO = "INFO"
    WARNING = "WARNING"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


SEVERITY_RANK = {
    NotificationSeverity.INFO: 1,
    NotificationSeverity.WARNING: 2,
    NotificationSeverity.HIGH: 3,
    NotificationSeverity.CRITICAL: 4,
}


class NotificationMessage(StrictModel):
    notification_id: str = Field(default_factory=lambda: f"notification_{uuid4().hex}")
    source_type: str
    source_id: str
    channel_type: NotificationChannelType = NotificationChannelType.MOCK
    severity: NotificationSeverity
    title: str
    message: str
    metadata: dict = Field(default_factory=dict)
    dedupe_key: str
    created_at: datetime = Field(default_factory=datetime.now)
    delivered_at: datetime | None = None
    delivery_status: str = "CREATED"
    error: str | None = None


def meets_minimum(severity: NotificationSeverity, minimum: NotificationSeverity) -> bool:
    return SEVERITY_RANK[severity] >= SEVERITY_RANK[minimum]


def sort_notifications(messages: list[NotificationMessage]) -> list[NotificationMessage]:
    return sorted(messages, key=lambda item: (-SEVERITY_RANK[item.severity], item.created_at, item.notification_id))
