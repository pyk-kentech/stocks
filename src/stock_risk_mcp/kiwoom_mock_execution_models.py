from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from uuid import uuid4

from pydantic import Field, field_validator

from stock_risk_mcp.models import StrictModel
from stock_risk_mcp.order_intent import OrderSide, OrderType
from stock_risk_mcp.realtime_market_data import MarketRegion


class KiwoomMockOrderStatus(StrEnum):
    ACCEPTED = "ACCEPTED"
    REJECTED = "REJECTED"
    FILLED = "FILLED"
    CANCELLED = "CANCELLED"
    UNKNOWN = "UNKNOWN"


class KiwoomMockOrderRequest(StrictModel):
    kiwoom_mock_order_request_id: str = Field(default_factory=lambda: f"kiwoom_mock_request_{uuid4().hex}")
    broker_order_request_id: str
    order_intent_id: str
    ticker: str
    region: MarketRegion
    side: OrderSide
    order_type: OrderType
    quantity: float | None = None
    notional: float | None = None
    limit_price: float | None = None
    stop_loss_price: float | None = None
    take_profit_price: float | None = None
    mock_fill_price: float | None = None
    created_at: datetime = Field(default_factory=datetime.now)
    metadata_json: dict = Field(default_factory=dict)

    @field_validator("ticker")
    @classmethod
    def normalize_ticker(cls, value: str) -> str:
        return value.strip().upper()


class KiwoomMockOrderReceipt(StrictModel):
    kiwoom_mock_order_receipt_id: str = Field(default_factory=lambda: f"kiwoom_mock_receipt_{uuid4().hex}")
    kiwoom_mock_order_request_id: str
    broker_order_receipt_id: str
    order_intent_id: str
    accepted: bool
    status: KiwoomMockOrderStatus
    filled_quantity: float | None = None
    filled_price: float | None = None
    filled_notional: float | None = None
    mock_order_id: str | None = None
    message: str
    created_at: datetime = Field(default_factory=datetime.now)
    metadata_json: dict = Field(default_factory=dict)
