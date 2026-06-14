from __future__ import annotations


KIWOOM_MOCK_EXECUTION_ENDPOINTS = {
    "KIWOOM_MOCK_ORDER_SUBMIT": "/kiwoom-mock/order/submit",
    "KIWOOM_MOCK_ORDER_CANCEL": "/kiwoom-mock/order/cancel",
    "KIWOOM_MOCK_ORDER_STATUS": "/kiwoom-mock/order/status",
}


class KiwoomMockExecutionEndpointAllowlist:
    def validate(self, api_id: str, path: str) -> bool:
        if KIWOOM_MOCK_EXECUTION_ENDPOINTS.get(api_id) != path:
            raise ValueError("Kiwoom mock execution endpoint not allowlisted")
        return True


class FakeKiwoomExecutionTransport:
    def __init__(self) -> None:
        self.calls: list[dict[str, str]] = []
        self._statuses: dict[str, str] = {}

    def post(self, path: str, body: dict) -> dict:
        if path not in KIWOOM_MOCK_EXECUTION_ENDPOINTS.values():
            raise ValueError("Kiwoom mock execution endpoint not allowlisted")
        self.calls.append({"path": path})
        if path == "/kiwoom-mock/order/submit":
            if body.get("simulate_error"):
                return {"status": "REJECTED", "accepted": False, "message": "simulated local transport error"}
            mock_order_id = f"kiwoom_mock_order_{body['broker_order_request_id']}"
            self._statuses[mock_order_id] = "FILLED"
            return {
                "status": "FILLED", "accepted": True, "mock_order_id": mock_order_id,
                "filled_quantity": body["quantity"], "filled_price": body["fill_price"],
                "filled_notional": body["quantity"] * body["fill_price"],
                "message": "deterministic Kiwoom local mock fill",
            }
        mock_order_id = str(body.get("mock_order_id", ""))
        if path == "/kiwoom-mock/order/cancel":
            self._statuses[mock_order_id] = "CANCELLED"
            return {"status": "CANCELLED", "accepted": True, "mock_order_id": mock_order_id, "message": "deterministic local cancellation"}
        return {
            "status": self._statuses.get(mock_order_id, "UNKNOWN"), "accepted": mock_order_id in self._statuses,
            "mock_order_id": mock_order_id, "message": "deterministic local status",
        }
