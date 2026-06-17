from __future__ import annotations

from pathlib import Path

from stock_risk_mcp.strategy_track_engine import compare_strategy_track_requests, validate_strategy_track_fixture
from stock_risk_mcp.strategy_track_fixture import load_strategy_track_fixture
from stock_risk_mcp.strategy_track_models import StrategyTrackComparisonReport, StrategyTrackValidationReport


def run_strategy_track_profile_validation(fixture_file, output_file=None):
    fixture = load_strategy_track_fixture(fixture_file)
    report = validate_strategy_track_fixture(fixture)
    if output_file:
        Path(output_file).write_text(report.model_dump_json(indent=2), encoding="utf-8")
    return report


def load_strategy_track_validation_report(path):
    try:
        return StrategyTrackValidationReport.model_validate_json(Path(path).read_text(encoding="utf-8"))
    except Exception as exc:
        raise ValueError(f"invalid strategy track validation report: {exc}") from exc


def run_strategy_track_compare(fixture_file, output_file=None):
    fixture = load_strategy_track_fixture(fixture_file)
    report = compare_strategy_track_requests(fixture)
    if output_file:
        Path(output_file).write_text(report.model_dump_json(indent=2), encoding="utf-8")
    return report


def load_strategy_track_comparison_report(path):
    try:
        return StrategyTrackComparisonReport.model_validate_json(Path(path).read_text(encoding="utf-8"))
    except Exception as exc:
        raise ValueError(f"invalid strategy track comparison report: {exc}") from exc
