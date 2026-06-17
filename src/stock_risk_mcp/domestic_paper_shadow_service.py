from __future__ import annotations

from pathlib import Path

from stock_risk_mcp.domestic_paper_shadow_engine import (
    build_domestic_paper_shadow_validation_report,
    build_paper_shadow_gap_report,
    build_paper_shadow_journal,
    build_paper_shadow_review_report,
    build_paper_shadow_safety_report,
)
from stock_risk_mcp.domestic_paper_shadow_fixture import load_domestic_paper_shadow_fixture


def run_domestic_paper_shadow_config_validate(fixture_file):
    fixture = load_domestic_paper_shadow_fixture(fixture_file)
    return build_domestic_paper_shadow_validation_report(fixture)


def run_domestic_paper_shadow_journal_build(fixture_file, output_file=None):
    fixture = load_domestic_paper_shadow_fixture(fixture_file)
    report = build_paper_shadow_journal(fixture)
    if output_file:
        Path(output_file).write_text(report.model_dump_json(indent=2), encoding="utf-8")
    return report


def run_domestic_paper_shadow_review_report(fixture_file, output_file=None):
    fixture = load_domestic_paper_shadow_fixture(fixture_file)
    report = build_paper_shadow_review_report(fixture)
    if output_file:
        Path(output_file).write_text(report.model_dump_json(indent=2), encoding="utf-8")
    return report


def run_domestic_paper_shadow_safety_report(fixture_file, output_file=None):
    fixture = load_domestic_paper_shadow_fixture(fixture_file)
    report = build_paper_shadow_safety_report(fixture)
    if output_file:
        Path(output_file).write_text(report.model_dump_json(indent=2), encoding="utf-8")
    return report


def run_domestic_paper_shadow_gap_report(fixture_file, output_file=None):
    fixture = load_domestic_paper_shadow_fixture(fixture_file)
    report = build_paper_shadow_gap_report(fixture)
    if output_file:
        Path(output_file).write_text(report.model_dump_json(indent=2), encoding="utf-8")
    return report
