from __future__ import annotations

from pathlib import Path

from stock_risk_mcp.domestic_shadow_outcome_engine import (
    build_domestic_shadow_outcome_validation_report,
    build_paper_shadow_outcome_label_batch,
    build_paper_shadow_outcome_review_report,
    build_paper_shadow_outcome_safety_report,
)
from stock_risk_mcp.domestic_shadow_outcome_fixture import load_domestic_shadow_outcome_fixture


def run_domestic_shadow_outcome_config_validate(fixture_file):
    fixture = load_domestic_shadow_outcome_fixture(fixture_file)
    return build_domestic_shadow_outcome_validation_report(fixture)


def run_domestic_shadow_outcome_label(fixture_file, output_file=None):
    fixture = load_domestic_shadow_outcome_fixture(fixture_file)
    report = build_paper_shadow_outcome_label_batch(fixture)
    if output_file:
        Path(output_file).write_text(report.model_dump_json(indent=2), encoding="utf-8")
    return report


def run_domestic_shadow_outcome_review_report(fixture_file, output_file=None):
    fixture = load_domestic_shadow_outcome_fixture(fixture_file)
    report = build_paper_shadow_outcome_review_report(fixture)
    if output_file:
        Path(output_file).write_text(report.model_dump_json(indent=2), encoding="utf-8")
    return report


def run_domestic_shadow_outcome_safety_report(fixture_file, output_file=None):
    fixture = load_domestic_shadow_outcome_fixture(fixture_file)
    report = build_paper_shadow_outcome_safety_report(fixture)
    if output_file:
        Path(output_file).write_text(report.model_dump_json(indent=2), encoding="utf-8")
    return report
