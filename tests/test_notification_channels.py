from datetime import datetime

from stock_risk_mcp.notification_channels import (
    ConsoleNotificationChannel,
    DisabledNotificationChannel,
    LocalFileNotificationChannel,
    MockNotificationChannel,
)
from stock_risk_mcp.notifications import NotificationChannelType, NotificationMessage, NotificationSeverity


def test_local_channels_deliver_without_network(tmp_path) -> None:
    message = _message()
    output = tmp_path / "notification.md"
    console = ConsoleNotificationChannel()
    mock = MockNotificationChannel()

    assert "HIGH" in console.deliver(message)
    assert mock.deliver(message)
    assert mock.messages == [message]
    assert LocalFileNotificationChannel(output).deliver(message)
    assert "Research alert" in output.read_text(encoding="utf-8")
    assert DisabledNotificationChannel().deliver(message) is False


def test_local_file_channel_writes_jsonl_for_jsonl_path(tmp_path) -> None:
    output = tmp_path / "notification.jsonl"

    LocalFileNotificationChannel(output).deliver(_message())

    assert '"severity": "HIGH"' in output.read_text(encoding="utf-8")


def _message():
    return NotificationMessage(
        source_type="pipeline_alert", source_id="pipe-1", channel_type=NotificationChannelType.MOCK,
        severity=NotificationSeverity.HIGH, title="High alert", message="Research alert",
        dedupe_key="pipe-1:high", created_at=datetime(2026, 6, 13),
    )
