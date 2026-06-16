import json
from pathlib import Path

from stock_risk_mcp.trade_plan_models import TradePlanFixture


def load_trade_plan_fixture(path) -> TradePlanFixture:
    try:
        selected = Path(path)
        if selected.suffix.lower() != ".json":
            raise ValueError("trade plan fixture must be an explicit local JSON file")
        return TradePlanFixture.model_validate(json.loads(selected.read_text(encoding="utf-8")))
    except Exception as exc:
        raise ValueError(f"invalid trade plan fixture: {exc}") from exc
