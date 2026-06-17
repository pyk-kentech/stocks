from __future__ import annotations

import json
from pathlib import Path

from stock_risk_mcp.domestic_calibration_models import DomesticCalibrationFixture


def load_domestic_calibration_fixture(path) -> DomesticCalibrationFixture:
    fixture_path = Path(path)
    try:
        if fixture_path.suffix.lower() != ".json":
            raise ValueError("domestic calibration fixture must be an explicit local JSON file")
        payload = json.loads(fixture_path.read_text(encoding="utf-8"))
        return DomesticCalibrationFixture.model_validate(payload)
    except Exception as exc:
        raise ValueError(f"invalid domestic calibration fixture: {exc}") from exc
