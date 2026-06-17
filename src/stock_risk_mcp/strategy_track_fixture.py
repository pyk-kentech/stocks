from __future__ import annotations

import json
from pathlib import Path

from stock_risk_mcp.strategy_track_models import StrategyTrackFixture


def load_strategy_track_fixture(path) -> StrategyTrackFixture:
    try:
        selected = Path(path)
        if selected.suffix.lower() != ".json":
            raise ValueError("strategy track fixture must be an explicit local JSON file")
        return StrategyTrackFixture.model_validate(json.loads(selected.read_text(encoding="utf-8")))
    except Exception as exc:
        raise ValueError(f"invalid strategy track fixture: {exc}") from exc
