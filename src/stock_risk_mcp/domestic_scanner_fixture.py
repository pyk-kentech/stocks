from __future__ import annotations

import json
from pathlib import Path

from stock_risk_mcp.domestic_scanner_models import DomesticScannerFixture


def load_domestic_scanner_fixture(path) -> DomesticScannerFixture:
    try:
        selected = Path(path)
        if selected.suffix.lower() != ".json":
            raise ValueError("domestic scanner fixture must be an explicit local JSON file")
        return DomesticScannerFixture.model_validate(json.loads(selected.read_text(encoding="utf-8")))
    except Exception as exc:
        raise ValueError(f"invalid domestic scanner fixture: {exc}") from exc
