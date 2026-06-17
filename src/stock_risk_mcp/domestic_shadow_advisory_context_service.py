from __future__ import annotations

from pathlib import Path

from stock_risk_mcp.domestic_shadow_advisory_context_engine import (
    build_domestic_shadow_advisory_context_bundle,
    build_domestic_shadow_advisory_context_gap_report,
    build_domestic_shadow_advisory_context_safety_report,
    build_domestic_shadow_advisory_context_validation_report,
)
from stock_risk_mcp.domestic_shadow_advisory_context_fixture import load_domestic_shadow_advisory_context_fixture


def run_domestic_shadow_advisory_context_config_validate(fixture_file):
    fixture = load_domestic_shadow_advisory_context_fixture(fixture_file)
    return build_domestic_shadow_advisory_context_validation_report(fixture)


def run_domestic_shadow_advisory_context_build(fixture_file, output_file=None):
    fixture = load_domestic_shadow_advisory_context_fixture(fixture_file)
    report = build_domestic_shadow_advisory_context_bundle(fixture)
    if output_file:
        Path(output_file).write_text(report.model_dump_json(indent=2), encoding="utf-8")
    return report


def run_domestic_shadow_advisory_context_validate(fixture_file, output_file=None):
    fixture = load_domestic_shadow_advisory_context_fixture(fixture_file)
    report = build_domestic_shadow_advisory_context_validation_report(fixture)
    if output_file:
        Path(output_file).write_text(report.model_dump_json(indent=2), encoding="utf-8")
    return report


def run_domestic_shadow_advisory_context_gap_report(fixture_file, output_file=None):
    fixture = load_domestic_shadow_advisory_context_fixture(fixture_file)
    report = build_domestic_shadow_advisory_context_gap_report(fixture)
    if output_file:
        Path(output_file).write_text(report.model_dump_json(indent=2), encoding="utf-8")
    return report


def run_domestic_shadow_advisory_context_safety_report(fixture_file, output_file=None):
    fixture = load_domestic_shadow_advisory_context_fixture(fixture_file)
    report = build_domestic_shadow_advisory_context_safety_report(fixture)
    if output_file:
        Path(output_file).write_text(report.model_dump_json(indent=2), encoding="utf-8")
    return report
