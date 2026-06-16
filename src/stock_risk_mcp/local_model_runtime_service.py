from __future__ import annotations

import hashlib
from pathlib import Path

from stock_risk_mcp.local_model_runtime_engine import (
    list_local_model_candidates,
    run_local_model_advisory_dry_run_fixture,
    run_local_model_runtime_check_fixture,
)
from stock_risk_mcp.local_model_runtime_fixture import load_local_model_candidates_fixture, load_local_model_runtime_fixture
from stock_risk_mcp.local_model_runtime_models import LocalModelCandidatesResult, LocalModelRuntimeResult


def _checksum(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _write_result(output_file, result):
    if output_file:
        Path(output_file).write_text(result.model_dump_json(indent=2), encoding="utf-8")


def run_local_model_candidates_list(fixture_file, output_file=None):
    fixture = load_local_model_candidates_fixture(fixture_file)
    result = list_local_model_candidates(fixture, _checksum(fixture_file))
    _write_result(output_file, result)
    return result


def run_local_model_runtime_check(fixture_file, output_file=None):
    fixture = load_local_model_runtime_fixture(fixture_file)
    result = run_local_model_runtime_check_fixture(fixture, _checksum(fixture_file))
    _write_result(output_file, result)
    return result


def run_local_model_advisory_dry_run(fixture_file, output_file=None):
    fixture = load_local_model_runtime_fixture(fixture_file)
    result = run_local_model_advisory_dry_run_fixture(fixture, _checksum(fixture_file))
    _write_result(output_file, result)
    return result


def load_local_model_runtime_result(path):
    try:
        return LocalModelRuntimeResult.model_validate_json(Path(path).read_text(encoding="utf-8"))
    except Exception as exc:
        raise ValueError(f"invalid local model runtime result: {exc}") from exc


def load_local_model_candidates_result(path):
    try:
        return LocalModelCandidatesResult.model_validate_json(Path(path).read_text(encoding="utf-8"))
    except Exception as exc:
        raise ValueError(f"invalid local model candidates result: {exc}") from exc
