from __future__ import annotations

import json
from pathlib import Path

from stock_risk_mcp.paper_evaluation_models import PaperEvaluationPipelineInput


def load_paper_evaluation_fixture(path: str | Path) -> PaperEvaluationPipelineInput:
    candidate = Path(path)
    lowered = str(candidate).lower()
    if "://" in lowered or lowered.startswith("//"):
        raise ValueError("paper evaluation fixture must be an explicit local JSON file")
    if candidate.suffix.lower() != ".json":
        raise ValueError("paper evaluation fixture must be a .json file")
    payload = json.loads(candidate.read_text(encoding="utf-8"))
    return PaperEvaluationPipelineInput.model_validate(payload)
