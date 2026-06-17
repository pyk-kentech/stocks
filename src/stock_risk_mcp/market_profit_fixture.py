from __future__ import annotations

import json
from pathlib import Path

from stock_risk_mcp.market_profit_models import MarketProfitCompareFixture, MarketProfitFixture


def load_market_profit_fixture(path) -> MarketProfitFixture:
    try:
        selected = Path(path)
        if selected.suffix.lower() != ".json":
            raise ValueError("market profit fixture must be an explicit local JSON file")
        return MarketProfitFixture.model_validate(json.loads(selected.read_text(encoding="utf-8")))
    except Exception as exc:
        raise ValueError(f"invalid market profit fixture: {exc}") from exc


def load_market_profit_compare_fixture(path) -> MarketProfitCompareFixture:
    try:
        selected = Path(path)
        if selected.suffix.lower() != ".json":
            raise ValueError("market profit compare fixture must be an explicit local JSON file")
        return MarketProfitCompareFixture.model_validate(json.loads(selected.read_text(encoding="utf-8")))
    except Exception as exc:
        raise ValueError(f"invalid market profit compare fixture: {exc}") from exc
