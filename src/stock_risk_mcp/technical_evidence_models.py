from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Literal

from pydantic import Field, field_validator, model_validator

from stock_risk_mcp.models import StrictModel


def aware(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("timestamp must include timezone")
    return value


class TechnicalOHLCVPoint(StrictModel):
    timestamp: datetime
    open: float = Field(..., gt=0)
    high: float = Field(..., gt=0)
    low: float = Field(..., gt=0)
    close: float = Field(..., gt=0)
    volume: float = Field(..., ge=0)
    _timestamp = field_validator("timestamp")(aware)

    @model_validator(mode="after")
    def validate_ohlc(self):
        if not self.low <= self.open <= self.high or not self.low <= self.close <= self.high:
            raise ValueError("OHLC relationship invalid")
        return self


class TechnicalSeries(StrictModel):
    ticker: str = Field(..., min_length=1)
    points: list[TechnicalOHLCVPoint]
    @field_validator("ticker")
    @classmethod
    def upper(cls, value): return value.strip().upper()
    @model_validator(mode="after")
    def ordered(self):
        if any(b.timestamp <= a.timestamp for a, b in zip(self.points, self.points[1:])):
            raise ValueError("points must be strictly increasing")
        return self


class TechnicalFixture(StrictModel):
    schema_version: Literal["3.2"]
    as_of_timestamp: datetime
    config: dict = Field(default_factory=dict)
    series: list[TechnicalSeries]
    _asof = field_validator("as_of_timestamp")(aware)
    @model_validator(mode="after")
    def validate_series(self):
        if len({item.ticker for item in self.series}) != len(self.series):
            raise ValueError("duplicate ticker")
        if any(point.timestamp > self.as_of_timestamp for item in self.series for point in item.points):
            raise ValueError("point after as_of_timestamp")
        return self


class MACDFeatures(StrictModel):
    macd_line: float | None = None; macd_signal: float | None = None; macd_histogram: float | None = None
    macd_histogram_slope: float | None = None; macd_histogram_acceleration: float | None = None
    macd_golden_cross: bool = False; macd_dead_cross: bool = False; macd_bullish_reacceleration: bool = False
    histogram_series: list[float] = Field(default_factory=list, exclude=True)


class RSIFeatures(StrictModel):
    rsi_level: float | None = None; rsi_50_reclaim: bool = False; rsi_50_loss: bool = False
    rsi_overbought: bool = False; rsi_oversold: bool = False
    rsi_series: list[float | None] = Field(default_factory=list, exclude=True)


class MAFeatures(StrictModel):
    ma20: float | None = None; ma50: float | None = None; ma200: float | None = None
    ma_alignment_20_50_200: str = "INSUFFICIENT_DATA"
    price_above_ma20: bool | None = None; price_above_ma50: bool | None = None; price_above_ma200: bool | None = None


class HMAFeatures(StrictModel):
    hma100: float | None = None; hma100_slope: float | None = None; hma100_trend_state: str = "INSUFFICIENT_DATA"


class ATRFeatures(StrictModel):
    atr14: float | None = None; atr_stop_distance: float | None = None; stop_distance_pct: float | None = None
    excessive_risk: bool = False


class VolumeFeatures(StrictModel):
    volume_ratio: float | None = None; dollar_volume: float | None = None; dollar_volume_ratio: float | None = None
    volume_spike_confirmation: bool = False; volume_dry_up_warning: bool = False


class DivergenceFeatures(StrictModel):
    bullish_rsi_divergence: bool = False; bearish_rsi_divergence: bool = False
    reasons: list[str] = Field(default_factory=list)


class TechnicalSetupType(StrEnum):
    ROSS_MOMENTUM_CROSS = "ROSS_MOMENTUM_CROSS"
    ROSS_PULLBACK_REACCELERATION = "ROSS_PULLBACK_REACCELERATION"
    TECHNICAL_NO_TRADE = "TECHNICAL_NO_TRADE"


class TechnicalGrade(StrEnum):
    A = "A"; B = "B"; C = "C"; NO_TRADE = "NO_TRADE"


class TechnicalEvidence(StrictModel):
    ticker: str; evidence_timestamp: datetime; point_count: int
    macd: MACDFeatures; rsi: RSIFeatures; ma: MAFeatures; hma: HMAFeatures; atr: ATRFeatures
    volume: VolumeFeatures; divergence: DivergenceFeatures
    setup_type: TechnicalSetupType; grade: TechnicalGrade; total_score: int
    component_scores: dict[str, int]; reasons: list[str] = Field(default_factory=list); warnings: list[str] = Field(default_factory=list)


class TechnicalEvidenceResult(StrictModel):
    schema_version: Literal["3.2-result"] = "3.2-result"
    fixture_checksum: str; as_of_timestamp: datetime; evidence: list[TechnicalEvidence]
    metadata_json: dict = Field(default_factory=lambda: {"advisory_only": True, "external_network_calls": False, "orders_created": False})
