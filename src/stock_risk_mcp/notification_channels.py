from __future__ import annotations

import json
from pathlib import Path

from stock_risk_mcp.notifications import NotificationMessage


def format_notification(message: NotificationMessage) -> str:
    return f"[{message.severity.value}] {message.title}\n{message.message}"


class ConsoleNotificationChannel:
    def deliver(self, message: NotificationMessage) -> str:
        return format_notification(message)


class LocalFileNotificationChannel:
    def __init__(self, output_path: str | Path) -> None:
        self.output_path = Path(output_path)

    def deliver(self, message: NotificationMessage) -> str:
        self.output_path.parent.mkdir(parents=True, exist_ok=True)
        if self.output_path.suffix.lower() == ".jsonl":
            content = json.dumps(message.model_dump(mode="json"), ensure_ascii=False) + "\n"
        else:
            content = f"## {message.title}\n\n**Severity:** {message.severity.value}\n\n{message.message}\n\n"
        with self.output_path.open("a", encoding="utf-8") as handle:
            handle.write(content)
        return str(self.output_path)


class MockNotificationChannel:
    def __init__(self) -> None:
        self.messages: list[NotificationMessage] = []

    def deliver(self, message: NotificationMessage) -> bool:
        self.messages.append(message)
        return True


class DisabledNotificationChannel:
    def deliver(self, message: NotificationMessage) -> bool:
        return False
