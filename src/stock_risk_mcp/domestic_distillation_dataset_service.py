from __future__ import annotations

from pathlib import Path

from stock_risk_mcp.domestic_distillation_dataset_engine import (
    build_domestic_distillation_dataset_gap_report,
    build_domestic_distillation_dataset_pack,
    build_domestic_distillation_dataset_safety_report,
    build_domestic_distillation_dataset_validation_report,
)
from stock_risk_mcp.domestic_distillation_dataset_fixture import load_domestic_distillation_dataset_fixture


def run_domestic_distillation_dataset_config_validate(fixture_file):
    fixture = load_domestic_distillation_dataset_fixture(fixture_file)
    return build_domestic_distillation_dataset_validation_report(fixture)


def run_domestic_distillation_dataset_build(fixture_file, output_file=None):
    fixture = load_domestic_distillation_dataset_fixture(fixture_file)
    report = build_domestic_distillation_dataset_pack(fixture)
    if output_file:
        Path(output_file).write_text(report.model_dump_json(indent=2), encoding="utf-8")
    return report


def run_domestic_distillation_dataset_validate(fixture_file, output_file=None):
    fixture = load_domestic_distillation_dataset_fixture(fixture_file)
    report = build_domestic_distillation_dataset_validation_report(fixture)
    if output_file:
        Path(output_file).write_text(report.model_dump_json(indent=2), encoding="utf-8")
    return report


def run_domestic_distillation_dataset_gap_report(fixture_file, output_file=None):
    fixture = load_domestic_distillation_dataset_fixture(fixture_file)
    report = build_domestic_distillation_dataset_gap_report(fixture)
    if output_file:
        Path(output_file).write_text(report.model_dump_json(indent=2), encoding="utf-8")
    return report


def run_domestic_distillation_dataset_safety_report(fixture_file, output_file=None):
    fixture = load_domestic_distillation_dataset_fixture(fixture_file)
    report = build_domestic_distillation_dataset_safety_report(fixture)
    if output_file:
        Path(output_file).write_text(report.model_dump_json(indent=2), encoding="utf-8")
    return report
