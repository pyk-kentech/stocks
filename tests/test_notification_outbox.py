from datetime import datetime

from stock_risk_mcp.notification_outbox import deliver_notifications
from stock_risk_mcp.notification_run import NotificationRunStatus
from stock_risk_mcp.notifications import NotificationChannelType, NotificationMessage, NotificationSeverity
from stock_risk_mcp.repository import RiskRepository


class FailingChannel:
    def deliver(self, message):
        raise OSError("delivery failed")


class PartiallyFailingChannel:
    def deliver(self, message):
        if message.title == "Failure":
            raise OSError("one failed")
        return True


def test_delivery_dedupes_persists_and_handles_statuses(tmp_path) -> None:
    repository = RiskRepository(tmp_path / "risk.sqlite3")
    message = _message()

    first = deliver_notifications(repository, [message], NotificationChannelType.MOCK, save=True)
    duplicate = deliver_notifications(repository, [message], NotificationChannelType.MOCK, save=True)
    empty = deliver_notifications(repository, [], NotificationChannelType.MOCK, save=True)
    disabled = deliver_notifications(repository, [message.model_copy(update={"dedupe_key": "new"})], NotificationChannelType.DISABLED)

    assert first.status == NotificationRunStatus.COMPLETED
    assert duplicate.skipped_duplicate_count == 1
    assert empty.status == NotificationRunStatus.NO_ALERTS
    assert disabled.status == NotificationRunStatus.DISABLED


def test_delivery_failure_is_captured_and_saved(tmp_path) -> None:
    repository = RiskRepository(tmp_path / "risk.sqlite3")

    run = deliver_notifications(
        repository, [_message()], NotificationChannelType.MOCK, save=True, channel=FailingChannel()
    )

    assert run.status == NotificationRunStatus.FAILED
    assert run.failed_count == 1
    assert "delivery failed" in run.errors[0]
    assert repository.list_notification_messages()[0].error == "delivery failed"


def test_delivery_partial_failure_is_captured(tmp_path) -> None:
    repository = RiskRepository(tmp_path / "risk.sqlite3")
    messages = [_message(), _message().model_copy(update={"title": "Failure", "dedupe_key": "pipe-1:failure"})]

    run = deliver_notifications(
        repository, messages, NotificationChannelType.MOCK, channel=PartiallyFailingChannel()
    )

    assert run.status == NotificationRunStatus.PARTIAL
    assert run.delivered_count == 1
    assert run.failed_count == 1


def _message():
    return NotificationMessage(
        source_type="pipeline_alert", source_id="pipe-1", channel_type=NotificationChannelType.MOCK,
        severity=NotificationSeverity.HIGH, title="High alert", message="Research alert",
        dedupe_key="pipe-1:high", created_at=datetime(2026, 6, 13),
    )
