from __future__ import annotations

from pathlib import Path

from stock_risk_mcp.domestic_replay_engine import (
    build_domestic_replay_promotion_readiness_report,
    build_domestic_replay_report,
    build_domestic_replay_validation_report,
)
from stock_risk_mcp.domestic_replay_fixture import load_domestic_replay_fixture


def run_domestic_replay_config_validate(fixture_file):
    fixture = load_domestic_replay_fixture(fixture_file)
    return build_domestic_replay_validation_report(fixture)


def run_domestic_replay_run(fixture_file, output_file=None):
    fixture = load_domestic_replay_fixture(fixture_file)
    report = build_domestic_replay_report(fixture)
    if output_file:
        Path(output_file).write_text(report.model_dump_json(indent=2), encoding="utf-8")
    return report


def run_domestic_replay_metrics_report(fixture_file, output_file=None):
    report = run_domestic_replay_run(fixture_file)
    if output_file:
        Path(output_file).write_text(report.metrics.model_dump_json(indent=2), encoding="utf-8")
    return report.metrics


def run_domestic_replay_promotion_readiness(fixture_file, output_file=None):
    fixture = load_domestic_replay_fixture(fixture_file)
    report = build_domestic_replay_promotion_readiness_report(fixture)
    if output_file:
        Path(output_file).write_text(report.model_dump_json(indent=2), encoding="utf-8")
    return report
