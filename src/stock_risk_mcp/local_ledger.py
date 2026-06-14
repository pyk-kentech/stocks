from datetime import datetime
from uuid import uuid4

from pydantic import Field, field_validator

from stock_risk_mcp.models import StrictModel
from stock_risk_mcp.realtime_market_data import MarketRegion


class LocalLedgerPosition(StrictModel):
    position_id: str = Field(default_factory=lambda: f"ledger_position_{uuid4().hex}")
    symbol: str
    region: MarketRegion
    quantity: int = Field(ge=0)
    reserved_quantity: int = Field(default=0, ge=0)
    average_price: float | None = Field(default=None, gt=0)
    updated_at: datetime = Field(default_factory=datetime.now)
    metadata_json: dict = Field(default_factory=lambda: {"network_called": False})

    @field_validator("symbol")
    @classmethod
    def normalize_symbol(cls, value: str) -> str:
        value = value.strip().upper()
        if not value:
            raise ValueError("symbol required")
        return value

    @property
    def available_quantity(self) -> int:
        return max(self.quantity - self.reserved_quantity, 0)


class LocalLedgerTransaction(StrictModel):
    transaction_id: str = Field(default_factory=lambda: f"ledger_transaction_{uuid4().hex}")
    position_id: str
    symbol: str
    region: MarketRegion
    transaction_type: str
    quantity: int
    reserved_quantity: int
    observed_at: datetime = Field(default_factory=datetime.now)
    metadata_json: dict = Field(default_factory=lambda: {"network_called": False})


class LocalLedgerSnapshot(StrictModel):
    snapshot_id: str = Field(default_factory=lambda: f"ledger_snapshot_{uuid4().hex}")
    position_count: int
    total_quantity: int
    total_reserved_quantity: int
    observed_at: datetime = Field(default_factory=datetime.now)
    metadata_json: dict = Field(default_factory=lambda: {"network_called": False, "redacted": True})
