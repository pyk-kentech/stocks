from __future__ import annotations

import hashlib
from pathlib import Path

from stock_risk_mcp.paper_eval_engine import build_paper_eval_report
from stock_risk_mcp.paper_eval_fixture import load_paper_eval_fixture
from stock_risk_mcp.paper_eval_models import PaperEvalReport


def _checksum(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def run_paper_eval(fixture_file, output_file=None):
    fixture = load_paper_eval_fixture(fixture_file)
    report = build_paper_eval_report(fixture, _checksum(fixture_file))
    if output_file:
        Path(output_file).write_text(report.model_dump_json(indent=2), encoding="utf-8")
    return report


def load_paper_eval_report(path):
    try:
        return PaperEvalReport.model_validate_json(Path(path).read_text(encoding="utf-8"))
    except Exception as exc:
        raise ValueError(f"invalid paper evaluation report: {exc}") from exc
