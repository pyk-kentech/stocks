from __future__ import annotations

import json
from pathlib import Path

from stock_risk_mcp.domestic_shadow_advisory_context_models import DomesticShadowAdvisoryContextFixture


def load_domestic_shadow_advisory_context_fixture(path) -> DomesticShadowAdvisoryContextFixture:
    fixture_path = Path(path)
    try:
        if fixture_path.suffix.lower() != ".json":
            raise ValueError("domestic shadow advisory context fixture must be an explicit local JSON file")
        payload = json.loads(fixture_path.read_text(encoding="utf-8"))
        return DomesticShadowAdvisoryContextFixture.model_validate(payload)
    except Exception as exc:
        raise ValueError(f"invalid domestic shadow advisory context fixture: {exc}") from exc
