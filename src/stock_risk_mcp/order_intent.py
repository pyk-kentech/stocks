from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from uuid import uuid4

from pydantic import Field, field_validator

from stock_risk_mcp.models import StrictModel
from stock_risk_mcp.realtime_market_data import MarketRegion


class OrderSide(StrEnum):
    BUY = "BUY"
    SELL = "SELL"


class OrderType(StrEnum):
    LIMIT = "LIMIT"
    STOP_LIMIT = "STOP_LIMIT"
    MARKET = "MARKET"


class ExecutionMode(StrEnum):
    PAPER = "PAPER"
    SANDBOX_DISABLED = "SANDBOX_DISABLED"
    LIVE_DISABLED = "LIVE_DISABLED"


class OrderIntentStatus(StrEnum):
    CREATED = "CREATED"
    RISK_BLOCKED = "RISK_BLOCKED"
    RISK_APPROVED = "RISK_APPROVED"
    EXECUTION_BLOCKED = "EXECUTION_BLOCKED"
    EXECUTION_APPROVED = "EXECUTION_APPROVED"
    PAPER_EXECUTED = "PAPER_EXECUTED"
    CANCELLED = "CANCELLED"
    EXPIRED = "EXPIRED"


class OrderIntent(StrictModel):
    order_intent_id: str = Field(default_factory=lambda: f"intent_{uuid4().hex}")
    ticker: str = ""
    region: MarketRegion = MarketRegion.UNKNOWN
    side: OrderSide
    order_type: OrderType
    quantity: float | None = None
    notional: float | None = None
    limit_price: float | None = None
    stop_loss_price: float | None = None
    take_profit_price: float | None = None
    source_type: str
    source_id: str
    reason: str
    confidence_score: float = Field(..., ge=0, le=1)
    created_at: datetime = Field(default_factory=datetime.now)
    expires_at: datetime | None = None
    status: OrderIntentStatus = OrderIntentStatus.CREATED
    metadata_json: dict = Field(default_factory=dict)

    @field_validator("ticker")
    @classmethod
    def normalize_ticker(cls, value: str) -> str:
        return value.strip().upper()


class RiskGateDecision(StrictModel):
    risk_gate_decision_id: str = Field(default_factory=lambda: f"risk_gate_{uuid4().hex}")
    order_intent_id: str
    approved: bool
    decision: str
    reasons_json: list[str] = Field(default_factory=list)
    rule_hits_json: list[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.now)


class ExecutionGateDecision(StrictModel):
    execution_gate_decision_id: str = Field(default_factory=lambda: f"execution_gate_{uuid4().hex}")
    order_intent_id: str
    approved: bool
    execution_mode: ExecutionMode
    decision: str
    reasons_json: list[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.now)


class PaperExecution(StrictModel):
    paper_execution_id: str = Field(default_factory=lambda: f"paper_execution_{uuid4().hex}")
    order_intent_id: str
    ticker: str
    side: OrderSide
    quantity: float
    requested_price: float | None = None
    filled_price: float
    filled_notional: float
    executed_at: datetime = Field(default_factory=datetime.now)
    status: str = "FILLED"
    metadata_json: dict = Field(default_factory=dict)
