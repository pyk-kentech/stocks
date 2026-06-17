from __future__ import annotations

import json
from pathlib import Path

from stock_risk_mcp.domestic_paper_shadow_models import DomesticPaperShadowFixture


def load_domestic_paper_shadow_fixture(path) -> DomesticPaperShadowFixture:
    fixture_path = Path(path)
    try:
        if fixture_path.suffix.lower() != ".json":
            raise ValueError("domestic paper shadow fixture must be an explicit local JSON file")
        payload = json.loads(fixture_path.read_text(encoding="utf-8"))
        return DomesticPaperShadowFixture.model_validate(payload)
    except Exception as exc:
        raise ValueError(f"invalid domestic paper shadow fixture: {exc}") from exc
