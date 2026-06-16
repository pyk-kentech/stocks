from __future__ import annotations

import hashlib
from pathlib import Path

from stock_risk_mcp.walk_forward_policy_engine import build_walk_forward_policy_report
from stock_risk_mcp.walk_forward_policy_fixture import load_walk_forward_policy_fixture
from stock_risk_mcp.walk_forward_policy_models import WalkForwardPolicyReport


def _checksum(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def run_walk_forward_policy_replay(fixture_file, output_file=None):
    fixture = load_walk_forward_policy_fixture(fixture_file)
    report = build_walk_forward_policy_report(fixture, _checksum(fixture_file))
    if output_file:
        Path(output_file).write_text(report.model_dump_json(indent=2), encoding="utf-8")
    return report


def load_walk_forward_policy_report(path):
    try:
        return WalkForwardPolicyReport.model_validate_json(Path(path).read_text(encoding="utf-8"))
    except Exception as exc:
        raise ValueError(f"invalid walk-forward policy report: {exc}") from exc
