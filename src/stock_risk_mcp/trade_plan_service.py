from __future__ import annotations

import hashlib
from pathlib import Path

from stock_risk_mcp.trade_plan_engine import build_trade_plan_report
from stock_risk_mcp.trade_plan_fixture import load_trade_plan_fixture
from stock_risk_mcp.trade_plan_models import TradePlanReport


def _checksum(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def run_trade_plan(fixture_file, output_file=None):
    fixture = load_trade_plan_fixture(fixture_file)
    report = build_trade_plan_report(fixture, _checksum(fixture_file))
    if output_file:
        Path(output_file).write_text(report.model_dump_json(indent=2), encoding="utf-8")
    return report


def load_trade_plan_report(path):
    try:
        return TradePlanReport.model_validate_json(Path(path).read_text(encoding="utf-8"))
    except Exception as exc:
        raise ValueError(f"invalid trade plan report: {exc}") from exc
