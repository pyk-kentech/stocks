from __future__ import annotations

import hashlib
import json
from pathlib import Path

from stock_risk_mcp.market_profit_engine import (
    build_market_profit_report,
    compare_market_profit_checks,
    validate_market_profit_fixture,
)
from stock_risk_mcp.market_profit_fixture import load_market_profit_compare_fixture, load_market_profit_fixture
from stock_risk_mcp.market_profit_models import MarketProfitReport, MarketProfitValidationReport


def _checksum(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def run_market_profit_profile_validation(fixture_file, output_file=None):
    fixture = load_market_profit_fixture(fixture_file)
    report = validate_market_profit_fixture(fixture)
    if output_file:
        Path(output_file).write_text(report.model_dump_json(indent=2), encoding="utf-8")
    return report


def run_market_profit_estimate(fixture_file, output_file=None):
    fixture = load_market_profit_fixture(fixture_file)
    report = build_market_profit_report(fixture, _checksum(fixture_file))
    if output_file:
        Path(output_file).write_text(report.model_dump_json(indent=2), encoding="utf-8")
    return report


def run_market_profit_compare_tracks(compare_fixture_file, output_file=None):
    compare_fixture = load_market_profit_compare_fixture(compare_fixture_file)
    base = Path(compare_fixture_file).resolve().parent
    requests = [load_market_profit_fixture(base / ref).strategy_request for ref in compare_fixture.fixture_files]
    report = compare_market_profit_checks(requests)
    if output_file:
        Path(output_file).write_text(report.model_dump_json(indent=2), encoding="utf-8")
    return report


def load_market_profit_report(path):
    try:
        return MarketProfitReport.model_validate_json(Path(path).read_text(encoding="utf-8"))
    except Exception as exc:
        raise ValueError(f"invalid market profit report: {exc}") from exc


def load_market_profit_validation_report(path):
    try:
        return MarketProfitValidationReport.model_validate_json(Path(path).read_text(encoding="utf-8"))
    except Exception as exc:
        raise ValueError(f"invalid market profit validation report: {exc}") from exc
