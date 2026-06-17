from __future__ import annotations

from pathlib import Path

from stock_risk_mcp.domestic_market_regime_engine import (
    build_market_regime_classification,
    build_market_regime_gap_report,
    build_market_regime_report,
    build_market_regime_safety_report,
)
from stock_risk_mcp.domestic_market_regime_fixture import load_domestic_market_regime_fixture


def run_domestic_market_regime_config_validate(fixture_file):
    fixture = load_domestic_market_regime_fixture(fixture_file)
    return build_market_regime_gap_report(fixture)


def run_domestic_market_regime_classify(fixture_file, output_file=None):
    fixture = load_domestic_market_regime_fixture(fixture_file)
    report = build_market_regime_classification(fixture)
    if output_file:
        Path(output_file).write_text(report.model_dump_json(indent=2), encoding="utf-8")
    return report


def run_domestic_market_regime_report(fixture_file, output_file=None):
    fixture = load_domestic_market_regime_fixture(fixture_file)
    report = build_market_regime_report(fixture)
    if output_file:
        Path(output_file).write_text(report.model_dump_json(indent=2), encoding="utf-8")
    return report


def run_domestic_market_regime_gap_report(fixture_file, output_file=None):
    fixture = load_domestic_market_regime_fixture(fixture_file)
    report = build_market_regime_gap_report(fixture)
    if output_file:
        Path(output_file).write_text(report.model_dump_json(indent=2), encoding="utf-8")
    return report


def run_domestic_market_regime_safety_report(fixture_file, output_file=None):
    fixture = load_domestic_market_regime_fixture(fixture_file)
    report = build_market_regime_safety_report(fixture)
    if output_file:
        Path(output_file).write_text(report.model_dump_json(indent=2), encoding="utf-8")
    return report
