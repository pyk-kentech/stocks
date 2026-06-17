from __future__ import annotations

import json
from pathlib import Path

from stock_risk_mcp.domestic_replay_models import DomesticReplayFixture


def load_domestic_replay_fixture(path) -> DomesticReplayFixture:
    fixture_path = Path(path)
    try:
        if fixture_path.suffix.lower() != ".json":
            raise ValueError("domestic replay fixture must be an explicit local JSON file")
        payload = json.loads(fixture_path.read_text(encoding="utf-8"))
        return DomesticReplayFixture.model_validate(payload)
    except Exception as exc:
        raise ValueError(f"invalid domestic replay fixture: {exc}") from exc
