from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from uuid import uuid4

from pydantic import Field, field_validator

from stock_risk_mcp.models import StrictModel


class KiwoomEnvironment(StrEnum):
    MOCK = "MOCK"
    PROD_DISABLED = "PROD_DISABLED"


class KiwoomEndpointCategory(StrEnum):
    OAUTH = "OAUTH"
    STOCK_INFO = "STOCK_INFO"
    QUOTE = "QUOTE"
    RANKING = "RANKING"
    FLOW = "FLOW"
    CHART = "CHART"
    CONDITION_SEARCH = "CONDITION_SEARCH"
    REALTIME_METADATA = "REALTIME_METADATA"


class KiwoomReadOnlyEndpoint(StrictModel):
    api_id: str
    path: str
    category: KiwoomEndpointCategory
    description: str
    read_only: bool
    enabled: bool


class KiwoomToken(StrictModel):
    access_token: str
    token_type: str
    expires_at: datetime
    issued_at: datetime
    environment: KiwoomEnvironment
    metadata_json: dict = Field(default_factory=dict)


class _TickerModel(StrictModel):
    ticker: str

    @field_validator("ticker")
    @classmethod
    def normalize_ticker(cls, value: str) -> str:
        return value.strip().upper()


class KiwoomStockInfo(_TickerModel):
    name: str
    market: str
    sector: str | None = None
    source_name: str
    observed_at: datetime
    raw_json: dict


class KiwoomQuote(_TickerModel):
    price: float
    change: float | None = None
    change_pct: float | None = None
    volume: float | None = None
    trading_value: float | None = None
    observed_at: datetime
    source_name: str
    raw_json: dict


class KiwoomRankItem(_TickerModel):
    name: str
    rank_type: str
    rank: int
    price: float | None = None
    change_pct: float | None = None
    volume: float | None = None
    trading_value: float | None = None
    observed_at: datetime
    raw_json: dict


class KiwoomFlowItem(_TickerModel):
    foreign_net_buy_amount: float | None = None
    institution_net_buy_amount: float | None = None
    foreign_net_buy_shares: float | None = None
    institution_net_buy_shares: float | None = None
    observed_at: datetime
    raw_json: dict


class KiwoomChartBar(_TickerModel):
    bar_time: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float
    raw_json: dict


class KiwoomConditionSearchItem(_TickerModel):
    condition_id: str
    condition_name: str
    name: str
    observed_at: datetime
    raw_json: dict


class KiwoomReadOnlyRequestAudit(StrictModel):
    request_id: str = Field(default_factory=lambda: f"kiwoom_request_{uuid4().hex}")
    api_id: str
    path: str
    category: KiwoomEndpointCategory
    ticker: str | None = None
    market: str | None = None
    condition_id: str | None = None
    status: str
    error: str | None = None
    observed_at: datetime = Field(default_factory=datetime.now)
    metadata_json: dict = Field(default_factory=dict)


class KiwoomReadOnlyResponseAudit(StrictModel):
    response_id: str = Field(default_factory=lambda: f"kiwoom_response_{uuid4().hex}")
    request_id: str
    status: str
    error: str | None = None
    observed_at: datetime = Field(default_factory=datetime.now)
    metadata_json: dict = Field(default_factory=dict)
