from __future__ import annotations

import json
from pathlib import Path

from stock_risk_mcp.domestic_market_regime_models import MarketRegimeFixture


def load_domestic_market_regime_fixture(path) -> MarketRegimeFixture:
    fixture_path = Path(path)
    try:
        if fixture_path.suffix.lower() != ".json":
            raise ValueError("domestic market regime fixture must be an explicit local JSON file")
        payload = json.loads(fixture_path.read_text(encoding="utf-8"))
        return MarketRegimeFixture.model_validate(payload)
    except Exception as exc:
        raise ValueError(f"invalid domestic market regime fixture: {exc}") from exc
