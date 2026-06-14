from __future__ import annotations

from typing import Protocol

from stock_risk_mcp.broker_models import (
    BrokerAdapterHealth,
    BrokerCapability,
    BrokerEnvironment,
    BrokerId,
    BrokerOrderReceipt,
    BrokerOrderRequest,
)


class BrokerAdapter(Protocol):
    broker_id: BrokerId
    environment: BrokerEnvironment

    def health_check(self) -> BrokerAdapterHealth: ...

    def capabilities(self) -> list[BrokerCapability]: ...

    def submit_order(self, request: BrokerOrderRequest) -> BrokerOrderReceipt: ...

    def cancel_order(self, broker_order_id: str) -> BrokerOrderReceipt: ...
