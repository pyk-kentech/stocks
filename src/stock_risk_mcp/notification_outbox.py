from __future__ import annotations

from datetime import datetime
from pathlib import Path

from stock_risk_mcp.notification_channels import (
    ConsoleNotificationChannel,
    DisabledNotificationChannel,
    LocalFileNotificationChannel,
    MockNotificationChannel,
)
from stock_risk_mcp.notification_run import NotificationRun, NotificationRunStatus
from stock_risk_mcp.notifications import NotificationChannelType, NotificationMessage


def deliver_notifications(
    repository,
    messages: list[NotificationMessage],
    channel_type: NotificationChannelType,
    output_path: str | Path | None = None,
    output_dir: str | Path | None = None,
    save: bool = False,
    channel=None,
) -> NotificationRun:
    source_types = {item.source_type for item in messages}
    source_ids = {item.source_id for item in messages}
    run = NotificationRun(
        source_type=next(iter(source_types)) if len(source_types) == 1 else "mixed",
        source_id=next(iter(source_ids)) if len(source_ids) == 1 else "multiple",
        channel_type=channel_type, message_count=len(messages),
        output_path=str(output_path) if output_path else None,
    )
    if not messages:
        return _finish(repository, run.model_copy(update={
            "status": NotificationRunStatus.NO_ALERTS, "completed_at": datetime.now(),
        }), [], save)
    if channel_type not in {NotificationChannelType.CONSOLE, NotificationChannelType.LOCAL_FILE, NotificationChannelType.MOCK}:
        return _finish(repository, run.model_copy(update={
            "status": NotificationRunStatus.DISABLED, "completed_at": datetime.now(),
        }), [], save)
    target = output_path
    if channel_type == NotificationChannelType.LOCAL_FILE and target is None:
        target = Path(output_dir or "notifications") / f"{run.notification_run_id}.md"
        run = run.model_copy(update={"output_path": str(target)})
    delivery_channel = channel or _channel(channel_type, target)
    delivered: list[NotificationMessage] = []
    seen: set[str] = set()
    skipped = failed = successful = 0
    errors: list[str] = []
    for original in messages:
        if original.dedupe_key in seen or (save and repository.has_notification_dedupe_key(original.dedupe_key)):
            skipped += 1
            continue
        seen.add(original.dedupe_key)
        message = original.model_copy(update={"channel_type": channel_type})
        try:
            delivery_channel.deliver(message)
            message = message.model_copy(update={"delivery_status": "DELIVERED", "delivered_at": datetime.now()})
            successful += 1
        except Exception as error:
            message = message.model_copy(update={"delivery_status": "FAILED", "error": str(error)})
            failed += 1
            errors.append(str(error))
        delivered.append(message)
    if failed and successful:
        status = NotificationRunStatus.PARTIAL
    elif failed:
        status = NotificationRunStatus.FAILED
    else:
        status = NotificationRunStatus.COMPLETED
    completed = run.model_copy(update={
        "status": status, "delivered_count": successful, "skipped_duplicate_count": skipped,
        "failed_count": failed, "errors": errors, "completed_at": datetime.now(),
    })
    return _finish(repository, completed, delivered, save)


def _channel(channel_type, output_path):
    if channel_type == NotificationChannelType.CONSOLE:
        return ConsoleNotificationChannel()
    if channel_type == NotificationChannelType.LOCAL_FILE:
        return LocalFileNotificationChannel(output_path)
    if channel_type == NotificationChannelType.MOCK:
        return MockNotificationChannel()
    return DisabledNotificationChannel()


def _finish(repository, run, messages, save):
    if save:
        repository.save_notification_run(run)
        repository.save_notification_messages(messages)
    return run
