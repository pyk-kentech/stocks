from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Literal

from pydantic import Field, field_validator, model_validator

from stock_risk_mcp.models import StrictModel
from stock_risk_mcp.strategy_core import StrategyCandidate, StrategyConfig, StrategyFeatureSnapshot


def _aware(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("timestamp must include timezone information")
    return value


class StrategyBacktestConfig(StrictModel):
    initial_cash: float = Field(..., gt=0)
    fixed_quantity: float = Field(..., gt=0)


class StrategyBacktestSnapshot(StrictModel):
    snapshot: StrategyFeatureSnapshot
    features_available_at: datetime

    _validate_available_at = field_validator("features_available_at")(_aware)


class StrategyBacktestCandidateEvent(StrictModel):
    candidate: StrategyCandidate
    decision_timestamp: datetime

    _validate_decision_timestamp = field_validator("decision_timestamp")(_aware)


class StrategyBacktestPricePoint(StrictModel):
    timestamp: datetime
    price: float = Field(..., gt=0)

    _validate_timestamp = field_validator("timestamp")(_aware)


class StrategyBacktestPricePath(StrictModel):
    ticker: str = Field(..., min_length=1)
    points: list[StrategyBacktestPricePoint]

    @field_validator("ticker")
    @classmethod
    def normalize_ticker(cls, value: str) -> str:
        return value.strip().upper()

    @model_validator(mode="after")
    def validate_order(self):
        timestamps = [item.timestamp for item in self.points]
        if any(current <= previous for previous, current in zip(timestamps, timestamps[1:])):
            raise ValueError("price point timestamps must be strictly increasing")
        return self


class StrategyBacktestFixture(StrictModel):
    schema_version: Literal["3.1"]
    strategy_config: StrategyConfig
    backtest_config: StrategyBacktestConfig
    snapshots: list[StrategyBacktestSnapshot]
    candidate_events: list[StrategyBacktestCandidateEvent]
    price_paths: list[StrategyBacktestPricePath]

    @model_validator(mode="after")
    def validate_references_and_timestamps(self):
        snapshots = {item.snapshot.snapshot_id: item for item in self.snapshots}
        if len(snapshots) != len(self.snapshots):
            raise ValueError("duplicate snapshot_id")
        if len({item.candidate.candidate_id for item in self.candidate_events}) != len(self.candidate_events):
            raise ValueError("duplicate candidate_id")
        if len({item.ticker for item in self.price_paths}) != len(self.price_paths):
            raise ValueError("duplicate price path ticker")
        seen: set[tuple[str, datetime]] = set()
        for wrapper in self.snapshots:
            _aware(wrapper.snapshot.observed_at)
        for event in self.candidate_events:
            wrapper = snapshots.get(event.candidate.snapshot_id)
            if wrapper is None:
                raise ValueError("candidate references missing snapshot")
            if wrapper.features_available_at > event.decision_timestamp:
                raise ValueError("FEATURES_AVAILABLE_AFTER_DECISION")
            key = (wrapper.snapshot.ticker, event.decision_timestamp)
            if key in seen:
                raise ValueError("DUPLICATE_CANDIDATE_TIMESTAMP_FOR_TICKER")
            seen.add(key)
        return self


def load_strategy_backtest_fixture(path: str | Path) -> StrategyBacktestFixture:
    selected = Path(path)
    try:
        return StrategyBacktestFixture.model_validate(json.loads(selected.read_text(encoding="utf-8")))
    except Exception as exc:
        raise ValueError(f"invalid strategy backtest fixture: {exc}") from exc
