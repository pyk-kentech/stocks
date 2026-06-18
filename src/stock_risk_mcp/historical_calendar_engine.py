from __future__ import annotations

import csv
import json
from datetime import datetime
from pathlib import Path

from pydantic import ValidationError

from stock_risk_mcp.historical_calendar_guard import build_calendar_issue, validate_calendar_source_path
from stock_risk_mcp.historical_calendar_models import (
    CalendarGapCategory,
    CalendarGapReport,
    CalendarGapStatus,
    CalendarValidationReport,
    CalendarValidationStatus,
    CorporateEventRecord,
    HistoricalCalendarManifest,
    HistoricalCalendarSourceType,
    MarketEventRecord,
    TradingCalendarConfig,
    TradingSessionRecord,
)


def _seoul_day_start(value) -> datetime:
    return datetime.fromisoformat(f"{value.isoformat()}T00:00:00+09:00")


def _seoul_day_end(value) -> datetime:
    return datetime.fromisoformat(f"{value.isoformat()}T23:59:59+09:00")


def _read_csv_rows(path: Path) -> list[dict[str, object]]:
    with path.open(encoding="utf-8", newline="") as handle:
        return [dict(row) for row in csv.DictReader(handle)]


def _read_jsonl_rows(path: Path) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            stripped = line.strip()
            if stripped:
                rows.append(json.loads(stripped))
    return rows


def _read_rows(local_file_path: str, source_type: HistoricalCalendarSourceType) -> tuple[list[dict[str, object]], list[dict[str, object]]]:
    path, issues = validate_calendar_source_path(local_file_path=local_file_path, source_type=source_type)
    if path is None:
        return [], issues
    rows = _read_csv_rows(path) if source_type == HistoricalCalendarSourceType.LOCAL_CSV else _read_jsonl_rows(path)
    return rows, issues


def _map_validation_error(exc: ValidationError, *, row_number: int) -> list[dict[str, object]]:
    issues: list[dict[str, object]] = []
    for error in exc.errors():
        field_name = ".".join(str(part) for part in error["loc"])
        message = error["msg"]
        category = CalendarGapCategory.UNSAFE_SOURCE_PATH
        if field_name == "timezone":
            category = CalendarGapCategory.TIMEZONE_MISMATCH
        issues.append(build_calendar_issue(category, message, row_number=row_number, field_name=field_name))
    return issues


def parse_trading_session_records(
    *,
    local_file_path: str,
    source_type: HistoricalCalendarSourceType,
) -> tuple[list[TradingSessionRecord], list[dict[str, object]]]:
    rows, issues = _read_rows(local_file_path, source_type)
    records: list[TradingSessionRecord] = []
    for index, row in enumerate(rows, start=1):
        try:
            records.append(TradingSessionRecord.model_validate(row))
        except ValidationError as exc:
            issues.extend(_map_validation_error(exc, row_number=index))
    return records, issues


def parse_market_event_records(
    *,
    local_file_path: str,
    source_type: HistoricalCalendarSourceType,
) -> tuple[list[MarketEventRecord], list[dict[str, object]]]:
    rows, issues = _read_rows(local_file_path, source_type)
    records: list[MarketEventRecord] = []
    for index, row in enumerate(rows, start=1):
        try:
            records.append(MarketEventRecord.model_validate(row))
        except ValidationError as exc:
            issues.extend(_map_validation_error(exc, row_number=index))
    return records, issues


def parse_corporate_event_records(
    *,
    local_file_path: str,
    source_type: HistoricalCalendarSourceType,
) -> tuple[list[CorporateEventRecord], list[dict[str, object]]]:
    rows, issues = _read_rows(local_file_path, source_type)
    records: list[CorporateEventRecord] = []
    for index, row in enumerate(rows, start=1):
        try:
            records.append(CorporateEventRecord.model_validate(row))
        except ValidationError as exc:
            issues.extend(_map_validation_error(exc, row_number=index))
    return records, issues


def build_historical_calendar_validation_report(
    *,
    calendar_config: TradingCalendarConfig,
    session_records: list[TradingSessionRecord],
    market_events: list[MarketEventRecord],
    corporate_events: list[CorporateEventRecord],
    parse_issues: list[dict[str, object]],
    calendar_batch_id: str,
) -> CalendarValidationReport:
    issues = list(parse_issues)
    market_id = calendar_config.market_profile.market_id
    timezone = "Asia/Seoul"
    session_dates = set()
    session_keys = set()
    event_keys = set()

    for session in session_records:
        if session.market != market_id:
            issues.append(build_calendar_issue(CalendarGapCategory.MARKET_PROFILE_MISMATCH, "session market must match calendar market profile"))
        if session.timezone != timezone:
            issues.append(build_calendar_issue(CalendarGapCategory.TIMEZONE_MISMATCH, "session timezone must match Asia/Seoul"))
        key = (session.market, session.date)
        if key in session_keys:
            issues.append(build_calendar_issue(CalendarGapCategory.DUPLICATE_SESSION, "duplicate trading session detected"))
        else:
            session_keys.add(key)
        session_dates.add(session.date)

    for event in market_events:
        if event.market != market_id:
            issues.append(build_calendar_issue(CalendarGapCategory.MARKET_PROFILE_MISMATCH, "market event market must match calendar market profile"))
        if event.timezone != timezone:
            issues.append(build_calendar_issue(CalendarGapCategory.TIMEZONE_MISMATCH, "market event timezone should remain Asia/Seoul"))
        key = (event.event_id, event.event_date)
        if key in event_keys:
            issues.append(build_calendar_issue(CalendarGapCategory.DUPLICATE_EVENT, "duplicate market event detected"))
        else:
            event_keys.add(key)
        if event.event_date not in session_dates:
            issues.append(build_calendar_issue(CalendarGapCategory.MISSING_SESSION, "market event date must map to a known trading session"))

    for event in corporate_events:
        if event.market != market_id:
            issues.append(build_calendar_issue(CalendarGapCategory.MARKET_PROFILE_MISMATCH, "corporate event market must match calendar market profile"))
        key = (event.symbol, event.event_date, event.event_type.value)
        if key in event_keys:
            issues.append(build_calendar_issue(CalendarGapCategory.DUPLICATE_EVENT, "duplicate corporate event detected"))
        else:
            event_keys.add(key)
        if event.event_date not in session_dates:
            issues.append(build_calendar_issue(CalendarGapCategory.MISSING_SESSION, "corporate event date must map to a known trading session"))

    warning_categories = {CalendarGapCategory.TIMEZONE_MISMATCH.value}
    blocking_issues = [issue for issue in issues if issue["category"] not in warning_categories]
    warning_issues = [issue for issue in issues if issue["category"] in warning_categories]

    if blocking_issues:
        status = CalendarValidationStatus.INVALID
        error_count = len(blocking_issues)
        warning_count = len(warning_issues)
    elif warning_issues:
        status = CalendarValidationStatus.VALID_WITH_WARNINGS
        error_count = 0
        warning_count = len(warning_issues)
    else:
        status = CalendarValidationStatus.VALID
        error_count = 0
        warning_count = 0

    return CalendarValidationReport(
        calendar_validation_report_id=f"{calendar_batch_id}-validation",
        calendar_batch_id=calendar_batch_id,
        strategy_track=calendar_config.strategy_track,
        market_profile_id=market_id,
        validation_status=status,
        error_count=error_count,
        warning_count=warning_count,
        validation_issues=issues,
    )


def build_historical_calendar_gap_report(
    *,
    calendar_config: TradingCalendarConfig,
    validation_report: CalendarValidationReport,
    calendar_batch_id: str,
) -> CalendarGapReport:
    del calendar_config
    categories = [CalendarGapCategory(issue["category"]) for issue in validation_report.validation_issues]
    unique_categories = list(dict.fromkeys(categories))
    warning_categories = {CalendarGapCategory.TIMEZONE_MISMATCH}
    blocking_gap_count = sum(1 for category in categories if category not in warning_categories)
    report_only_gap_count = sum(1 for category in categories if category in warning_categories)

    if not unique_categories:
        gap_status = CalendarGapStatus.NO_GAPS
    elif blocking_gap_count:
        gap_status = CalendarGapStatus.BLOCKING_GAPS
    else:
        gap_status = CalendarGapStatus.REPORT_ONLY_GAPS

    return CalendarGapReport(
        calendar_gap_report_id=f"{calendar_batch_id}-gap",
        calendar_batch_id=calendar_batch_id,
        gap_status=gap_status,
        gap_categories=unique_categories,
        blocking_gap_count=blocking_gap_count,
        report_only_gap_count=report_only_gap_count,
        gaps=validation_report.validation_issues,
    )


def build_historical_calendar_manifest(
    *,
    calendar_config: TradingCalendarConfig,
    session_records: list[TradingSessionRecord],
    market_events: list[MarketEventRecord],
    corporate_events: list[CorporateEventRecord],
    validation_report: CalendarValidationReport,
    gap_report: CalendarGapReport,
    calendar_batch_id: str,
    source_descriptor_ids: list[str],
) -> HistoricalCalendarManifest:
    date_points = []
    for record in session_records:
        date_points.append(_seoul_day_start(record.date))
        date_points.append(_seoul_day_end(record.date))
    for event in market_events:
        date_points.append(event.event_time or _seoul_day_start(event.event_date))
    for event in corporate_events:
        date_points.append(_seoul_day_start(event.event_date))
    if not date_points:
        date_points = [_seoul_day_start(datetime.fromisoformat("2026-01-01T00:00:00+09:00").date())]

    return HistoricalCalendarManifest(
        calendar_manifest_id=f"{calendar_batch_id}-manifest",
        calendar_batch_id=calendar_batch_id,
        source_descriptor_ids=source_descriptor_ids,
        strategy_track=calendar_config.strategy_track,
        market_profile_id=calendar_config.market_profile.market_id,
        session_record_count=len(session_records),
        market_event_count=len(market_events),
        corporate_event_count=len(corporate_events),
        date_range_start=min(date_points),
        date_range_end=max(date_points),
        timezone="Asia/Seoul",
        validation_report_id=validation_report.calendar_validation_report_id,
        gap_report_id=gap_report.calendar_gap_report_id,
    )
