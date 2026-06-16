from __future__ import annotations

import json
from pathlib import Path

from stock_risk_mcp.local_model_runtime_models import LocalModelCandidatesFixture, LocalModelRuntimeFixture


def _load_json(path):
    path = Path(path)
    if path.suffix.lower() != ".json":
        raise ValueError("fixture file must be JSON")
    return json.loads(path.read_text(encoding="utf-8"))


def load_local_model_runtime_fixture(path) -> LocalModelRuntimeFixture:
    try:
        return LocalModelRuntimeFixture.model_validate(_load_json(path))
    except Exception as exc:
        raise ValueError(f"invalid local model runtime fixture: {exc}") from exc


def load_local_model_candidates_fixture(path) -> LocalModelCandidatesFixture:
    try:
        return LocalModelCandidatesFixture.model_validate(_load_json(path))
    except Exception as exc:
        raise ValueError(f"invalid local model candidates fixture: {exc}") from exc
