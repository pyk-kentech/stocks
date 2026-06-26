from __future__ import annotations

import json
from pathlib import Path

from stock_risk_mcp.controlled_execution_models import ControlledExecutionPipelineInput


def load_controlled_execution_fixture(path: Path | str) -> ControlledExecutionPipelineInput:
    fixture_path = Path(path)
    payload = json.loads(fixture_path.read_text(encoding="utf-8"))
    return ControlledExecutionPipelineInput.model_validate(payload)
