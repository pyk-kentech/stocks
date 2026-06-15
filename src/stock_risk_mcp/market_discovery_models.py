from __future__ import annotations

import math
from datetime import datetime
from enum import StrEnum
from typing import Literal

from pydantic import Field, field_validator, model_validator

from stock_risk_mcp.models import StrictModel


def _aware(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("timestamp must include timezone")
    return value


def _finite_number(value):
    if isinstance(value, bool) or not isinstance(value, (int, float, str)):
        raise ValueError("value must be numeric")
    try:
        number = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError("value must be numeric") from exc
    if not math.isfinite(number):
        raise ValueError("value must be finite")
    return value


class MarketDiscoveryConfig(StrictModel):
    min_price: float = Field(..., gt=0, allow_inf_nan=False)
    max_price: float | None = Field(default=None, gt=0, allow_inf_nan=False)
    min_price_change_pct: float = Field(..., gt=0, allow_inf_nan=False)
    min_volume_spike_ratio: float = Field(..., gt=0, allow_inf_nan=False)
    min_dollar_volume_spike_ratio: float = Field(..., gt=0, allow_inf_nan=False)
    min_average_dollar_volume_20d: float = Field(..., gt=0, allow_inf_nan=False)
    max_candidates: int = Field(..., ge=1, le=1000)

    @field_validator(
        "min_price", "max_price", "min_price_change_pct",
        "min_volume_spike_ratio", "min_dollar_volume_spike_ratio",
        "min_average_dollar_volume_20d", mode="before",
    )
    @classmethod
    def finite_numbers(cls, value):
        return None if value is None else _finite_number(value)

    @field_validator("max_candidates", mode="before")
    @classmethod
    def integer_candidate_limit(cls, value):
        if isinstance(value, bool):
            raise ValueError("max_candidates must be an integer")
        return value

    @model_validator(mode="after")
    def valid_price_range(self):
        if self.max_price is not None and self.max_price < self.min_price:
            raise ValueError("max_price must be greater than or equal to min_price")
        return self


class MarketDiscoverySnapshotRow(StrictModel):
    ticker: str = Field(..., min_length=1)
    observed_at: datetime
    price: float = Field(..., gt=0, allow_inf_nan=False)
    previous_close: float = Field(..., gt=0, allow_inf_nan=False)
    volume: float = Field(..., ge=0, allow_inf_nan=False)
    average_volume_20d: float = Field(..., gt=0, allow_inf_nan=False)
    average_dollar_volume_20d: float = Field(..., gt=0, allow_inf_nan=False)

    _timestamp = field_validator("observed_at")(_aware)

    @field_validator("ticker")
    @classmethod
    def normalize_ticker(cls, value: str) -> str:
        value = value.strip().upper()
        if not value:
            raise ValueError("ticker must not be blank")
        return value

    @field_validator(
        "price", "previous_close", "volume", "average_volume_20d",
        "average_dollar_volume_20d", mode="before",
    )
    @classmethod
    def finite_numbers(cls, value):
        return _finite_number(value)


class MarketDiscoveryFixture(StrictModel):
    schema_version: Literal["3.3"]
    as_of_timestamp: datetime
    scanner_config: MarketDiscoveryConfig
    rows: list[MarketDiscoverySnapshotRow] = Field(..., min_length=1)

    _as_of = field_validator("as_of_timestamp")(_aware)

    @model_validator(mode="after")
    def validate_rows(self):
        if len({row.ticker for row in self.rows}) != len(self.rows):
            raise ValueError("duplicate ticker")
        if any(row.observed_at > self.as_of_timestamp for row in self.rows):
            raise ValueError("observed_at after as_of_timestamp")
        return self


class MarketDiscoveryClassification(StrEnum):
    DISCOVER = "DISCOVER"
    WATCH = "WATCH"
    EXCLUDE = "EXCLUDE"


class MarketDiscoveryEvidence(StrictModel):
    price_change_pct: float
    volume_spike_ratio: float
    dollar_volume: float
    dollar_volume_spike_ratio: float
    price_in_range: bool
    price_change_pass: bool
    volume_spike_pass: bool
    dollar_volume_spike_pass: bool
    liquidity_pass: bool


class MarketDiscoveryEvaluation(StrictModel):
    ticker: str
    observed_at: datetime
    classification: MarketDiscoveryClassification
    score: int = Field(..., ge=0, le=100)
    component_scores: dict[str, int]
    evidence: MarketDiscoveryEvidence
    reasons: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class MarketDiscoveryCandidate(MarketDiscoveryEvaluation):
    pass


class MarketDiscoveryResult(StrictModel):
    schema_version: Literal["3.3-result"] = "3.3-result"
    fixture_checksum: str
    fixture_format: Literal["JSON", "CSV"]
    as_of_timestamp: datetime
    scanner_config: MarketDiscoveryConfig
    evaluations: list[MarketDiscoveryEvaluation]
    candidates: list[MarketDiscoveryCandidate]
    summary_counts: dict[str, int]
    metadata_json: dict = Field(default_factory=lambda: {
        "advisory_only": True,
        "external_network_calls": False,
        "scraping_used": False,
        "strategy_decisions_created": False,
        "order_intents_created": False,
        "orders_created": False,
    })
