from __future__ import annotations

import json
from pathlib import Path

from stock_risk_mcp.domestic_candidate_evaluation_models import DomesticCandidateEvaluationFixture


def load_domestic_candidate_evaluation_fixture(path) -> DomesticCandidateEvaluationFixture:
    try:
        selected = Path(path)
        if selected.suffix.lower() != ".json":
            raise ValueError("domestic candidate evaluation fixture must be an explicit local JSON file")
        return DomesticCandidateEvaluationFixture.model_validate(json.loads(selected.read_text(encoding="utf-8")))
    except Exception as exc:
        raise ValueError(f"invalid domestic candidate evaluation fixture: {exc}") from exc
