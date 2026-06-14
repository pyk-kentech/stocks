from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from uuid import uuid4

from pydantic import Field, field_validator

from stock_risk_mcp.models import StrictModel
from stock_risk_mcp.order_intent import OrderSide, OrderType
from stock_risk_mcp.realtime_market_data import MarketRegion


class BrokerId(StrEnum):
    MOCK = "MOCK"
    KIWOOM = "KIWOOM"
    ALPACA = "ALPACA"
    UNKNOWN = "UNKNOWN"


class BrokerEnvironment(StrEnum):
    LOCAL_MOCK = "LOCAL_MOCK"
    PAPER = "PAPER"
    SANDBOX_DISABLED = "SANDBOX_DISABLED"
    LIVE_DISABLED = "LIVE_DISABLED"


class BrokerCapability(StrEnum):
    MARKET_DATA = "MARKET_DATA"
    ACCOUNT_READ = "ACCOUNT_READ"
    ORDER_SUBMIT = "ORDER_SUBMIT"
    ORDER_CANCEL = "ORDER_CANCEL"
    ORDER_REPLACE = "ORDER_REPLACE"
    WEBSOCKET_MARKET_DATA = "WEBSOCKET_MARKET_DATA"
    CONDITION_SEARCH = "CONDITION_SEARCH"


class BrokerConnectionStatus(StrEnum):
    DISCONNECTED = "DISCONNECTED"
    CONNECTED = "CONNECTED"
    DISABLED = "DISABLED"
    ERROR = "ERROR"


class BrokerOrderStatus(StrEnum):
    ACCEPTED = "ACCEPTED"
    REJECTED = "REJECTED"
    FILLED = "FILLED"
    PARTIALLY_FILLED = "PARTIALLY_FILLED"
    CANCELLED = "CANCELLED"
    UNKNOWN = "UNKNOWN"


class BrokerOrderRequest(StrictModel):
    broker_order_request_id: str = Field(default_factory=lambda: f"broker_request_{uuid4().hex}")
    order_intent_id: str
    broker_id: BrokerId
    environment: BrokerEnvironment
    ticker: str
    region: MarketRegion
    side: OrderSide
    order_type: OrderType
    quantity: float | None = None
    notional: float | None = None
    limit_price: float | None = None
    stop_loss_price: float | None = None
    take_profit_price: float | None = None
    created_at: datetime = Field(default_factory=datetime.now)
    metadata_json: dict = Field(default_factory=dict)

    @field_validator("ticker")
    @classmethod
    def normalize_ticker(cls, value: str) -> str:
        return value.strip().upper()


class BrokerOrderReceipt(StrictModel):
    broker_order_receipt_id: str = Field(default_factory=lambda: f"broker_receipt_{uuid4().hex}")
    broker_order_request_id: str
    order_intent_id: str
    broker_id: BrokerId
    environment: BrokerEnvironment
    status: BrokerOrderStatus
    accepted: bool
    filled_quantity: float | None = None
    filled_price: float | None = None
    filled_notional: float | None = None
    broker_order_id: str | None = None
    message: str
    created_at: datetime = Field(default_factory=datetime.now)
    metadata_json: dict = Field(default_factory=dict)


class BrokerAdapterHealth(StrictModel):
    broker_id: BrokerId
    environment: BrokerEnvironment
    status: BrokerConnectionStatus
    capabilities: list[BrokerCapability] = Field(default_factory=list)
    message: str
    checked_at: datetime = Field(default_factory=datetime.now)
