from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Protocol
from uuid import uuid4

from pydantic import Field, field_validator

from stock_risk_mcp.models import StrictModel
from stock_risk_mcp.realtime_market_data import MarketRegion


class StrategyDecisionStatus(StrEnum):
    WATCH = "WATCH"
    AVOID = "AVOID"
    CANDIDATE_BUY = "CANDIDATE_BUY"
    CANDIDATE_SELL = "CANDIDATE_SELL"
    BLOCKED = "BLOCKED"
    NEEDS_MORE_DATA = "NEEDS_MORE_DATA"


class StrategyDecisionReason(StrEnum):
    MISSING_REQUIRED_FEATURES = "MISSING_REQUIRED_FEATURES"
    HARD_RISK_BLOCK = "HARD_RISK_BLOCK"
    HIGH_RISK = "HIGH_RISK"
    FORBIDDEN_ORDER_TYPE = "FORBIDDEN_ORDER_TYPE"
    FORBIDDEN_EXPOSURE = "FORBIDDEN_EXPOSURE"
    BUY_SIGNAL = "BUY_SIGNAL"
    SELL_SIGNAL = "SELL_SIGNAL"
    INSUFFICIENT_SIGNAL = "INSUFFICIENT_SIGNAL"


class StrategyCandidateSide(StrEnum):
    BUY = "BUY"
    SELL = "SELL"


class StrategyCandidateOrderType(StrEnum):
    LIMIT = "LIMIT"
    STOP_LIMIT = "STOP_LIMIT"
    MARKET = "MARKET"


class StrategyConfig(StrictModel):
    required_features: list[str] = Field(default_factory=lambda: ["signal_score", "risk_score", "hard_block"])
    buy_threshold: float = Field(0.7, ge=-1, le=1)
    sell_threshold: float = Field(-0.7, ge=-1, le=1)
    avoid_risk_threshold: float = Field(0.8, ge=0, le=1)


class StrategyFeatureSnapshot(StrictModel):
    snapshot_id: str = Field(default_factory=lambda: f"strategy_snapshot_{uuid4().hex}")
    ticker: str = Field(..., min_length=1)
    region: MarketRegion
    observed_at: datetime = Field(default_factory=datetime.now)
    features: dict[str, float | bool | str | None]
    source_references: list[str] = Field(default_factory=list)
    metadata_json: dict = Field(default_factory=dict)

    @field_validator("ticker")
    @classmethod
    def normalize_ticker(cls, value: str) -> str:
        return value.strip().upper()


class StrategyCandidate(StrictModel):
    candidate_id: str = Field(default_factory=lambda: f"strategy_candidate_{uuid4().hex}")
    snapshot_id: str
    side: StrategyCandidateSide
    order_type: StrategyCandidateOrderType
    quantity: float | None = Field(default=None, gt=0)
    notional: float | None = Field(default=None, gt=0)
    limit_price: float | None = Field(default=None, gt=0)
    stop_loss_price: float | None = Field(default=None, gt=0)
    take_profit_price: float | None = Field(default=None, gt=0)
    rationale: str = Field(..., min_length=1)
    metadata_json: dict = Field(default_factory=dict)


class StrategyDecision(StrictModel):
    decision_id: str = Field(default_factory=lambda: f"strategy_decision_{uuid4().hex}")
    run_id: str = ""
    candidate_id: str
    snapshot_id: str
    status: StrategyDecisionStatus
    reasons: list[StrategyDecisionReason]
    confidence_score: float = Field(..., ge=0, le=1)
    draft_order_intent_allowed: bool = False
    requires_sell_safety: bool = False
    warnings: list[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.now)


class StrategyRunStatus(StrEnum):
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class StrategyRun(StrictModel):
    run_id: str = Field(default_factory=lambda: f"strategy_run_{uuid4().hex}")
    fixture_checksum: str
    engine_name: str = "deterministic-baseline-v3.0"
    status: StrategyRunStatus = StrategyRunStatus.COMPLETED
    snapshot_count: int = 0
    candidate_count: int = 0
    decision_count: int = 0
    warnings: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)
    metadata_json: dict = Field(default_factory=lambda: {
        "offline": True, "network_called": False, "credentials_read": False,
        "account_data_read": False, "orders_submitted": False,
    })
    created_at: datetime = Field(default_factory=datetime.now)


class StrategyEngine(Protocol):
    def decide(
        self, snapshot: StrategyFeatureSnapshot, candidate: StrategyCandidate, config: StrategyConfig
    ) -> StrategyDecision: ...


class DeterministicStrategyEngine:
    name = "deterministic-baseline-v3.0"

    def decide(
        self, snapshot: StrategyFeatureSnapshot, candidate: StrategyCandidate, config: StrategyConfig
    ) -> StrategyDecision:
        base = {"candidate_id": candidate.candidate_id, "snapshot_id": snapshot.snapshot_id}
        if candidate.order_type == StrategyCandidateOrderType.MARKET:
            return StrategyDecision(**base, status=StrategyDecisionStatus.BLOCKED,
                                    reasons=[StrategyDecisionReason.FORBIDDEN_ORDER_TYPE], confidence_score=1)
        forbidden = ("margin", "short", "credit", "leverage", "options", "futures", "fractional")
        if any(bool(candidate.metadata_json.get(key)) for key in forbidden):
            return StrategyDecision(**base, status=StrategyDecisionStatus.BLOCKED,
                                    reasons=[StrategyDecisionReason.FORBIDDEN_EXPOSURE], confidence_score=1)
        if any(snapshot.features.get(name) is None for name in config.required_features):
            return StrategyDecision(**base, status=StrategyDecisionStatus.NEEDS_MORE_DATA,
                                    reasons=[StrategyDecisionReason.MISSING_REQUIRED_FEATURES], confidence_score=0)
        if bool(snapshot.features["hard_block"]):
            return StrategyDecision(**base, status=StrategyDecisionStatus.BLOCKED,
                                    reasons=[StrategyDecisionReason.HARD_RISK_BLOCK], confidence_score=1)
        risk_score = float(snapshot.features["risk_score"])
        signal_score = float(snapshot.features["signal_score"])
        if risk_score >= config.avoid_risk_threshold:
            return StrategyDecision(**base, status=StrategyDecisionStatus.AVOID,
                                    reasons=[StrategyDecisionReason.HIGH_RISK], confidence_score=risk_score)
        if candidate.side == StrategyCandidateSide.BUY and signal_score >= config.buy_threshold:
            return StrategyDecision(**base, status=StrategyDecisionStatus.CANDIDATE_BUY,
                                    reasons=[StrategyDecisionReason.BUY_SIGNAL], confidence_score=abs(signal_score),
                                    draft_order_intent_allowed=True)
        if candidate.side == StrategyCandidateSide.SELL and signal_score <= config.sell_threshold:
            return StrategyDecision(**base, status=StrategyDecisionStatus.CANDIDATE_SELL,
                                    reasons=[StrategyDecisionReason.SELL_SIGNAL], confidence_score=abs(signal_score),
                                    draft_order_intent_allowed=True, requires_sell_safety=True)
        return StrategyDecision(**base, status=StrategyDecisionStatus.WATCH,
                                reasons=[StrategyDecisionReason.INSUFFICIENT_SIGNAL],
                                confidence_score=min(abs(signal_score), 1))
