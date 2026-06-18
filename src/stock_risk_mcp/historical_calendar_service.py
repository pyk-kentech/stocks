from __future__ import annotations

from pathlib import Path

from stock_risk_mcp.historical_calendar_engine import (
    build_historical_calendar_gap_report,
    build_historical_calendar_validation_report,
    parse_corporate_event_records,
    parse_market_event_records,
    parse_trading_session_records,
)
from stock_risk_mcp.historical_calendar_fixture import load_historical_calendar_fixture


def _build_historical_calendar_reports(fixture):
    session_records, session_issues = parse_trading_session_records(
        local_file_path=fixture.session_file_path,
        source_type=fixture.calendar_config.source_type,
    )
    market_events, market_event_issues = parse_market_event_records(
        local_file_path=fixture.market_event_file_path,
        source_type=fixture.calendar_config.source_type,
    )
    corporate_events, corporate_event_issues = parse_corporate_event_records(
        local_file_path=fixture.corporate_event_file_path,
        source_type=fixture.calendar_config.source_type,
    )
    validation = build_historical_calendar_validation_report(
        calendar_config=fixture.calendar_config,
        session_records=session_records,
        market_events=market_events,
        corporate_events=corporate_events,
        parse_issues=[*session_issues, *market_event_issues, *corporate_event_issues],
        calendar_batch_id=fixture.calendar_batch_id,
    )
    gap = build_historical_calendar_gap_report(
        calendar_config=fixture.calendar_config,
        validation_report=validation,
        calendar_batch_id=fixture.calendar_batch_id,
    )
    return validation, gap


def run_historical_calendar_config_validate(fixture_file):
    return load_historical_calendar_fixture(fixture_file)


def run_historical_calendar_validate(fixture_file, output_file=None):
    fixture = load_historical_calendar_fixture(fixture_file)
    validation, _ = _build_historical_calendar_reports(fixture)
    if output_file:
        Path(output_file).write_text(validation.model_dump_json(indent=2), encoding="utf-8")
    return validation


def run_historical_calendar_gap_report(fixture_file, output_file=None):
    fixture = load_historical_calendar_fixture(fixture_file)
    _, gap = _build_historical_calendar_reports(fixture)
    if output_file:
        Path(output_file).write_text(gap.model_dump_json(indent=2), encoding="utf-8")
    return gap
