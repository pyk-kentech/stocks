from __future__ import annotations

from pathlib import Path

from stock_risk_mcp.domestic_calibration_engine import (
    build_calibration_run_result,
    build_domestic_calibration_validation_report,
    build_policy_comparison_report,
    build_promotion_gate_report,
)
from stock_risk_mcp.domestic_calibration_fixture import load_domestic_calibration_fixture


def run_domestic_calibration_config_validate(fixture_file):
    fixture = load_domestic_calibration_fixture(fixture_file)
    return build_domestic_calibration_validation_report(fixture)


def run_domestic_calibration_run(fixture_file, output_file=None):
    fixture = load_domestic_calibration_fixture(fixture_file)
    report = build_calibration_run_result(fixture)
    if output_file:
        Path(output_file).write_text(report.model_dump_json(indent=2), encoding="utf-8")
    return report


def run_domestic_policy_compare(fixture_file, output_file=None):
    fixture = load_domestic_calibration_fixture(fixture_file)
    report = build_policy_comparison_report(fixture)
    if output_file:
        Path(output_file).write_text(report.model_dump_json(indent=2), encoding="utf-8")
    return report


def run_domestic_promotion_gate_report(fixture_file, output_file=None):
    fixture = load_domestic_calibration_fixture(fixture_file)
    report = build_promotion_gate_report(fixture)
    if output_file:
        Path(output_file).write_text(report.model_dump_json(indent=2), encoding="utf-8")
    return report
