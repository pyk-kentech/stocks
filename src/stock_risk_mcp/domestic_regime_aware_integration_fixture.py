from __future__ import annotations

import json
from pathlib import Path

from stock_risk_mcp.domestic_regime_aware_integration_models import (
    DomesticRegimeAwareIntegrationFixture,
)


def load_domestic_regime_aware_integration_fixture(path) -> DomesticRegimeAwareIntegrationFixture:
    fixture_path = Path(path)
    try:
        if fixture_path.suffix.lower() != ".json":
            raise ValueError("domestic regime-aware integration fixture must be an explicit local JSON file")
        payload = json.loads(fixture_path.read_text(encoding="utf-8"))
        return DomesticRegimeAwareIntegrationFixture.model_validate(payload)
    except Exception as exc:
        raise ValueError(f"invalid domestic regime-aware integration fixture: {exc}") from exc
