from datetime import datetime

from stock_risk_mcp.notifications import (
    NotificationChannelType,
    NotificationMessage,
    NotificationSeverity,
)
from stock_risk_mcp.repository import RiskRepository


def test_notification_message_repository_round_trip_and_dedupe(tmp_path) -> None:
    repository = RiskRepository(tmp_path / "risk.sqlite3")
    message = NotificationMessage(
        notification_id="notification-1", source_type="pipeline_alert", source_id="pipe-1",
        channel_type=NotificationChannelType.MOCK, severity=NotificationSeverity.HIGH,
        title="High alert", message="Research alert.", dedupe_key="pipe-1:high",
        created_at=datetime(2026, 6, 13),
    )

    repository.save_notification_messages([message])

    assert repository.list_notification_messages("pipe-1") == [message]
    assert repository.has_notification_dedupe_key("pipe-1:high") is True
