from __future__ import annotations

from pathlib import Path

from stock_risk_mcp.historical_calendar_models import CalendarGapCategory, HistoricalCalendarSourceType


def build_calendar_issue(
    category: CalendarGapCategory,
    message: str,
    *,
    row_number: int | None = None,
    field_name: str | None = None,
) -> dict[str, object]:
    issue: dict[str, object] = {
        "category": category.value,
        "message": message,
    }
    if row_number is not None:
        issue["row_number"] = row_number
    if field_name is not None:
        issue["field_name"] = field_name
    return issue


def validate_calendar_source_path(
    *,
    local_file_path: str,
    source_type: HistoricalCalendarSourceType,
) -> tuple[Path | None, list[dict[str, object]]]:
    issues: list[dict[str, object]] = []
    lowered = local_file_path.strip().lower()

    if source_type not in {HistoricalCalendarSourceType.LOCAL_CSV, HistoricalCalendarSourceType.LOCAL_JSONL}:
        issues.append(
            build_calendar_issue(
                CalendarGapCategory.UNSUPPORTED_SOURCE_TYPE,
                "calendar source_type must remain local_csv or local_jsonl",
            )
        )
        return None, issues
    if lowered.startswith(("http://", "https://")) or "://" in lowered:
        issues.append(
            build_calendar_issue(
                CalendarGapCategory.REMOTE_FETCH_NOT_ALLOWED,
                "calendar source path must remain local-only",
            )
        )
        return None, issues

    path = Path(local_file_path)
    if not path.exists():
        issues.append(
            build_calendar_issue(
                CalendarGapCategory.MISSING_CALENDAR_FILE,
                "calendar source file does not exist",
            )
        )
        return None, issues
    if not path.is_file():
        issues.append(
            build_calendar_issue(
                CalendarGapCategory.UNSAFE_SOURCE_PATH,
                "calendar source path must reference a regular file",
            )
        )
        return None, issues

    expected_suffix = ".csv" if source_type == HistoricalCalendarSourceType.LOCAL_CSV else ".jsonl"
    if path.suffix.lower() != expected_suffix:
        issues.append(
            build_calendar_issue(
                CalendarGapCategory.UNSAFE_SOURCE_PATH,
                f"calendar source file must use {expected_suffix}",
            )
        )
        return None, issues
    return path, issues
