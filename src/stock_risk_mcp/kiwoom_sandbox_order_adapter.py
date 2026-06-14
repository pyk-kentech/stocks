from __future__ import annotations

from stock_risk_mcp.kiwoom_sandbox_order_transport import RealKiwoomSandboxOrderTransport


class KiwoomSandboxOrderAdapter:
    def __init__(self, transport: RealKiwoomSandboxOrderTransport) -> None:
        self.transport = transport

    def submit(self, body: dict) -> dict:
        return self.transport.post("kt10000", body)

    def cancel(self, body: dict) -> dict:
        return self.transport.post("kt10003", body)
