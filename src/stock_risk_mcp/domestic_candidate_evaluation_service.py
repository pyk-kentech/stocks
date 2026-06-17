from __future__ import annotations

from pathlib import Path

from stock_risk_mcp.domestic_candidate_evaluation_engine import (
    build_candidate_evaluation_gap_report,
    build_candidate_evaluation_report,
    build_candidate_evaluation_safety_report,
    build_candidate_evaluation_validation_report,
)
from stock_risk_mcp.domestic_candidate_evaluation_fixture import (
    load_domestic_candidate_evaluation_fixture,
)


def run_domestic_candidate_evaluation_config_validate(fixture_file):
    fixture = load_domestic_candidate_evaluation_fixture(fixture_file)
    return build_candidate_evaluation_validation_report(fixture)


def run_domestic_candidate_evaluate(fixture_file, output_file=None):
    fixture = load_domestic_candidate_evaluation_fixture(fixture_file)
    report = build_candidate_evaluation_report(fixture)
    if output_file:
        Path(output_file).write_text(report.model_dump_json(indent=2), encoding="utf-8")
    return report


def run_domestic_candidate_evaluation_gap_report(fixture_file, output_file=None):
    fixture = load_domestic_candidate_evaluation_fixture(fixture_file)
    report = build_candidate_evaluation_gap_report(fixture)
    if output_file:
        Path(output_file).write_text(report.model_dump_json(indent=2), encoding="utf-8")
    return report


def run_domestic_candidate_evaluation_safety_report(fixture_file, output_file=None):
    fixture = load_domestic_candidate_evaluation_fixture(fixture_file)
    report = build_candidate_evaluation_safety_report(fixture)
    if output_file:
        Path(output_file).write_text(report.model_dump_json(indent=2), encoding="utf-8")
    return report
