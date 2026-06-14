from datetime import datetime
from enum import StrEnum
from uuid import uuid4

from pydantic import Field

from stock_risk_mcp.models import StrictModel


class SellSafetyStatus(StrEnum):
    APPROVED = "APPROVED"
    BLOCKED = "BLOCKED"
    NEEDS_RECONCILIATION = "NEEDS_RECONCILIATION"


class SellSafetyDecision(StrictModel):
    sell_safety_decision_id: str = Field(default_factory=lambda: f"sell_safety_{uuid4().hex}")
    order_intent_id: str
    symbol: str
    status: SellSafetyStatus
    requested_quantity: int | None = None
    available_quantity: int | None = None
    reconciliation_status: str | None = None
    reasons_json: list[str] = Field(default_factory=list)
    observed_at: datetime = Field(default_factory=datetime.now)
    metadata_json: dict = Field(default_factory=lambda: {"network_called": False, "orders_submitted": False})
