from __future__ import annotations

from pathlib import Path

from stock_risk_mcp.domestic_regime_aware_integration_engine import (
    build_domestic_regime_aware_gap_report,
    build_domestic_regime_aware_integration_report,
    build_domestic_regime_aware_safety_report,
)
from stock_risk_mcp.domestic_regime_aware_integration_fixture import (
    load_domestic_regime_aware_integration_fixture,
)


def run_domestic_regime_aware_integration_config_validate(fixture_file):
    fixture = load_domestic_regime_aware_integration_fixture(fixture_file)
    return build_domestic_regime_aware_gap_report(fixture)


def run_domestic_regime_aware_integration_build(fixture_file, output_file=None):
    fixture = load_domestic_regime_aware_integration_fixture(fixture_file)
    report = build_domestic_regime_aware_integration_report(fixture)
    if output_file:
        Path(output_file).write_text(report.model_dump_json(indent=2), encoding="utf-8")
    return report


def run_domestic_regime_aware_integration_report(fixture_file, output_file=None):
    fixture = load_domestic_regime_aware_integration_fixture(fixture_file)
    report = build_domestic_regime_aware_integration_report(fixture)
    if output_file:
        Path(output_file).write_text(report.model_dump_json(indent=2), encoding="utf-8")
    return report


def run_domestic_regime_aware_gap_report(fixture_file, output_file=None):
    fixture = load_domestic_regime_aware_integration_fixture(fixture_file)
    report = build_domestic_regime_aware_gap_report(fixture)
    if output_file:
        Path(output_file).write_text(report.model_dump_json(indent=2), encoding="utf-8")
    return report


def run_domestic_regime_aware_safety_report(fixture_file, output_file=None):
    fixture = load_domestic_regime_aware_integration_fixture(fixture_file)
    report = build_domestic_regime_aware_safety_report(fixture)
    if output_file:
        Path(output_file).write_text(report.model_dump_json(indent=2), encoding="utf-8")
    return report
