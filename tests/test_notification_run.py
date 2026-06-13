from datetime import datetime

from stock_risk_mcp.notification_run import NotificationRun, NotificationRunStatus
from stock_risk_mcp.notifications import NotificationChannelType
from stock_risk_mcp.repository import RiskRepository


def test_notification_run_repository_round_trip(tmp_path) -> None:
    repository = RiskRepository(tmp_path / "risk.sqlite3")
    run = NotificationRun(
        notification_run_id="notify-1", source_type="pipeline", source_id="pipe-1",
        channel_type=NotificationChannelType.CONSOLE, status=NotificationRunStatus.COMPLETED,
        message_count=2, delivered_count=2, skipped_duplicate_count=0, failed_count=0,
        created_at=datetime(2026, 6, 13), completed_at=datetime(2026, 6, 13),
    )

    repository.save_notification_run(run)

    assert repository.get_notification_run("notify-1") == run
    assert repository.list_notification_runs() == [run]
