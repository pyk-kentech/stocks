from __future__ import annotations

from pathlib import Path

from stock_risk_mcp.local_model_benchmark_service import load_local_model_benchmark_report
from stock_risk_mcp.local_model_decision_report_engine import run_local_model_decision_report
from stock_risk_mcp.local_model_decision_report_fixture import load_local_model_benchmark_pack_fixture
from stock_risk_mcp.local_model_decision_report_guard import coverage_complete, validate_pack_structure
from stock_risk_mcp.local_model_decision_report_models import LocalModelBackendDecisionReport


def _resolve_pack_reports(pack_file, pack) -> tuple[list, dict[str, str]]:
    base = Path(pack_file).resolve().parent
    reports = []
    refs = {}
    for ref in pack.benchmark_report_files:
        path = base / ref
        report = load_local_model_benchmark_report(path)
        reports.append(report)
        refs[report.run_id] = ref
    return reports, refs


def validate_local_model_benchmark_pack(pack_file):
    pack = load_local_model_benchmark_pack_fixture(pack_file)
    reports, _ = _resolve_pack_reports(pack_file, pack)
    structure = validate_pack_structure(pack, pack_file)
    coverage = coverage_complete(pack, reports)
    return {**structure, **coverage}


def run_local_model_decision_report_cli(pack_file, output_file=None):
    pack = load_local_model_benchmark_pack_fixture(pack_file)
    reports, refs = _resolve_pack_reports(pack_file, pack)
    decision = run_local_model_decision_report(pack, reports, refs)
    if output_file:
        Path(output_file).write_text(decision.model_dump_json(indent=2), encoding="utf-8")
    return decision


def load_local_model_decision_report(path):
    try:
        return LocalModelBackendDecisionReport.model_validate_json(Path(path).read_text(encoding="utf-8"))
    except Exception as exc:
        raise ValueError(f"invalid local model decision report: {exc}") from exc
