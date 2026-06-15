from __future__ import annotations

import json
from pathlib import Path
from typing import Literal

from pydantic import model_validator

from stock_risk_mcp.models import StrictModel
from stock_risk_mcp.strategy_core import StrategyCandidate, StrategyConfig, StrategyFeatureSnapshot


class StrategyFixture(StrictModel):
    schema_version: Literal["3.0"]
    config: StrategyConfig = StrategyConfig()
    snapshots: list[StrategyFeatureSnapshot]
    candidates: list[StrategyCandidate]

    @model_validator(mode="after")
    def validate_snapshot_references(self):
        snapshot_ids = {item.snapshot_id for item in self.snapshots}
        missing = [item.snapshot_id for item in self.candidates if item.snapshot_id not in snapshot_ids]
        if missing:
            raise ValueError(f"candidate references missing snapshot: {missing[0]}")
        return self


def load_strategy_fixture(path: str | Path) -> StrategyFixture:
    selected = Path(path)
    try:
        payload = json.loads(selected.read_text(encoding="utf-8"))
        return StrategyFixture.model_validate(payload)
    except Exception as exc:
        raise ValueError(f"invalid strategy fixture: {exc}") from exc
