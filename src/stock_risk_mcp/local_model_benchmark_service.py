from __future__ import annotations

import hashlib
from pathlib import Path

from stock_risk_mcp.local_model_benchmark_engine import rank_eligible_candidates, run_local_model_benchmark
from stock_risk_mcp.local_model_benchmark_fixture import load_local_model_benchmark_fixture, load_local_model_candidate_output_fixture
from stock_risk_mcp.local_model_benchmark_models import LocalModelBenchmarkReport


def _checksum(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def run_local_model_benchmark_cli(benchmark_fixture_file, candidate_output_file, output_file=None):
    benchmark_fixture = load_local_model_benchmark_fixture(benchmark_fixture_file)
    candidate_fixture = load_local_model_candidate_output_fixture(candidate_output_file)
    report = run_local_model_benchmark(
        benchmark_fixture,
        candidate_fixture,
        _checksum(benchmark_fixture_file),
        _checksum(candidate_output_file),
    )
    if output_file:
        Path(output_file).write_text(report.model_dump_json(indent=2), encoding="utf-8")
    return report


def load_local_model_benchmark_report(path):
    try:
        return LocalModelBenchmarkReport.model_validate_json(Path(path).read_text(encoding="utf-8"))
    except Exception as exc:
        raise ValueError(f"invalid local model benchmark report: {exc}") from exc


def rank_local_model_candidates_from_report(path):
    return [item.model_dump(mode="json") for item in rank_eligible_candidates(load_local_model_benchmark_report(path))]
