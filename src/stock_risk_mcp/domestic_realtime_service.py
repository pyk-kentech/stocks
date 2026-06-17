from __future__ import annotations

from pathlib import Path

from stock_risk_mcp.domestic_realtime_engine import (
    build_domestic_realtime_plan_report,
    build_domestic_realtime_quality_report,
    normalize_domestic_realtime_events,
)
from stock_risk_mcp.domestic_realtime_fixture import load_domestic_realtime_fixture


def run_domestic_realtime_profile_validate(fixture_file):
    fixture = load_domestic_realtime_fixture(fixture_file)
    return {
        "status": "COMPLETED",
        "strategy_track": fixture.strategy_request.strategy_track.value,
        "provider_id": fixture.provider_profile.provider_id,
        "market_id": fixture.strategy_request.market_profile.market_id,
        "metadata_json": fixture.provider_profile.model_dump(mode="json"),
    }


def run_domestic_realtime_plan_show(fixture_file):
    fixture = load_domestic_realtime_fixture(fixture_file)
    return build_domestic_realtime_plan_report(fixture)


def run_domestic_realtime_event_normalize(fixture_file, output_file=None):
    fixture = load_domestic_realtime_fixture(fixture_file)
    normalized = {"events": normalize_domestic_realtime_events(fixture)}
    if output_file:
        Path(output_file).write_text(__import__("json").dumps(normalized, indent=2), encoding="utf-8")
    return normalized


def run_domestic_realtime_quality_report(fixture_file, output_file=None):
    fixture = load_domestic_realtime_fixture(fixture_file)
    report = build_domestic_realtime_quality_report(fixture)
    if output_file:
        Path(output_file).write_text(report.model_dump_json(indent=2), encoding="utf-8")
    return report
