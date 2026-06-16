from __future__ import annotations

import json
from pathlib import Path

from stock_risk_mcp.local_model_decision_report_models import LocalModelBenchmarkPackFixture


def _load_json(path):
    path = Path(path)
    if path.suffix.lower() != ".json":
        raise ValueError("fixture file must be JSON")
    return json.loads(path.read_text(encoding="utf-8"))


def load_local_model_benchmark_pack_fixture(path) -> LocalModelBenchmarkPackFixture:
    try:
        return LocalModelBenchmarkPackFixture.model_validate(_load_json(path))
    except Exception as exc:
        raise ValueError(f"invalid local model benchmark pack fixture: {exc}") from exc
