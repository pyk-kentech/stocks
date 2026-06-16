from __future__ import annotations

import json
from pathlib import Path

from stock_risk_mcp.local_model_benchmark_models import LocalModelBenchmarkFixture, LocalModelCandidateOutputFixture


def _load_json(path):
    path = Path(path)
    if path.suffix.lower() != ".json":
        raise ValueError("fixture file must be JSON")
    return json.loads(path.read_text(encoding="utf-8"))


def load_local_model_benchmark_fixture(path) -> LocalModelBenchmarkFixture:
    try:
        return LocalModelBenchmarkFixture.model_validate(_load_json(path))
    except Exception as exc:
        raise ValueError(f"invalid local model benchmark fixture: {exc}") from exc


def load_local_model_candidate_output_fixture(path) -> LocalModelCandidateOutputFixture:
    try:
        return LocalModelCandidateOutputFixture.model_validate(_load_json(path))
    except Exception as exc:
        raise ValueError(f"invalid local model candidate output fixture: {exc}") from exc
