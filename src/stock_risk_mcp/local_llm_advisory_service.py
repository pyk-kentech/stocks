from __future__ import annotations

import hashlib
from pathlib import Path

from stock_risk_mcp.local_llm_advisory_engine import run_local_llm_advisory_fixture
from stock_risk_mcp.local_llm_advisory_fixture import load_local_llm_advisory_fixture
from stock_risk_mcp.local_llm_advisory_models import LocalLLMAdvisoryResult


def _checksum(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def run_local_llm_advisory(fixture_file, output_file=None):
    fixture = load_local_llm_advisory_fixture(fixture_file)
    result = run_local_llm_advisory_fixture(fixture, _checksum(fixture_file))
    if output_file:
        Path(output_file).write_text(result.model_dump_json(indent=2), encoding="utf-8")
    return result


def load_local_llm_advisory_result(path):
    try:
        return LocalLLMAdvisoryResult.model_validate_json(Path(path).read_text(encoding="utf-8"))
    except Exception as exc:
        raise ValueError(f"invalid local LLM advisory result: {exc}") from exc
