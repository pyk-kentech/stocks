from __future__ import annotations

import json
from pathlib import Path

from stock_risk_mcp.domestic_shadow_outcome_models import DomesticShadowOutcomeFixture


def load_domestic_shadow_outcome_fixture(path) -> DomesticShadowOutcomeFixture:
    fixture_path = Path(path)
    try:
        if fixture_path.suffix.lower() != ".json":
            raise ValueError("domestic shadow outcome fixture must be an explicit local JSON file")
        payload = json.loads(fixture_path.read_text(encoding="utf-8"))
        return DomesticShadowOutcomeFixture.model_validate(payload)
    except Exception as exc:
        raise ValueError(f"invalid domestic shadow outcome fixture: {exc}") from exc
