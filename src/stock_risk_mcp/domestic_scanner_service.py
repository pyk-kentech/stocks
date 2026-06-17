from __future__ import annotations

from pathlib import Path

from stock_risk_mcp.domestic_scanner_engine import (
    build_domestic_scanner_candidates,
    build_domestic_scanner_quality_report,
    build_domestic_scanner_validation_report,
    build_domestic_scanner_watchlist_plan,
)
from stock_risk_mcp.domestic_scanner_fixture import load_domestic_scanner_fixture


def run_domestic_scanner_config_validate(fixture_file):
    fixture = load_domestic_scanner_fixture(fixture_file)
    return build_domestic_scanner_validation_report(fixture)


def run_domestic_scanner_candidates(fixture_file, output_file=None):
    fixture = load_domestic_scanner_fixture(fixture_file)
    report = build_domestic_scanner_candidates(fixture)
    if output_file:
        Path(output_file).write_text(report.model_dump_json(indent=2), encoding="utf-8")
    return report


def run_domestic_scanner_watchlist_plan(fixture_file, output_file=None):
    fixture = load_domestic_scanner_fixture(fixture_file)
    report = build_domestic_scanner_candidates(fixture)
    plan = build_domestic_scanner_watchlist_plan(report)
    if output_file:
        Path(output_file).write_text(plan.model_dump_json(indent=2), encoding="utf-8")
    return plan


def run_domestic_scanner_quality_report(fixture_file, output_file=None):
    fixture = load_domestic_scanner_fixture(fixture_file)
    report = build_domestic_scanner_quality_report(fixture)
    if output_file:
        Path(output_file).write_text(report.model_dump_json(indent=2), encoding="utf-8")
    return report
