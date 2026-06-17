from __future__ import annotations

import json
from pathlib import Path

from stock_risk_mcp.domestic_realtime_models import DomesticRealtimeFixture


def load_domestic_realtime_fixture(path) -> DomesticRealtimeFixture:
    try:
        selected = Path(path)
        if selected.suffix.lower() != ".json":
            raise ValueError("domestic realtime fixture must be an explicit local JSON file")
        return DomesticRealtimeFixture.model_validate(json.loads(selected.read_text(encoding="utf-8")))
    except Exception as exc:
        raise ValueError(f"invalid domestic realtime fixture: {exc}") from exc
