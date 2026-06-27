from __future__ import annotations

import json
from abc import ABC, abstractmethod
from urllib import request
from urllib.error import HTTPError

from stock_risk_mcp.historical_market_data_guard import is_pytest_runtime
from stock_risk_mcp.historical_market_data_models import HistoricalChartRequestPreview, HistoricalMarketDataTransportKind


class HistoricalMarketDataTransport(ABC):
    transport_kind: HistoricalMarketDataTransportKind

    @abstractmethod
    def execute(self, preview: HistoricalChartRequestPreview, *, auth_header: str | None = None) -> dict[str, object]:
        raise NotImplementedError


class MockHistoricalMarketDataTransport(HistoricalMarketDataTransport):
    transport_kind = HistoricalMarketDataTransportKind.MOCK

    def __init__(self, response_by_request_id: dict[str, dict[str, object]] | None = None) -> None:
        self.response_by_request_id = {str(key).upper(): value for key, value in (response_by_request_id or {}).items()}

    def execute(self, preview: HistoricalChartRequestPreview, *, auth_header: str | None = None) -> dict[str, object]:
        del auth_header
        request_id = preview.report_id.replace("-REQUEST-PREVIEW", "").upper()
        return self.response_by_request_id.get(
            request_id,
            {
                "status_code": 200,
                "headers": {"cont-yn": preview.headers.get("cont-yn", "N"), "next-key": preview.headers.get("next-key", "")},
                "body_json": {"return_code": 0, "return_msg": "MOCK_CAPTURE_READY"},
            },
        )


class RealKiwoomChartTransport(HistoricalMarketDataTransport):
    transport_kind = HistoricalMarketDataTransportKind.REAL_KIWOOM_CHART

    def __init__(self, *, timeout_seconds: int = 10, base_url: str = "https://api.kiwoom.com") -> None:
        if is_pytest_runtime():
            raise ValueError("real chart transport must remain unavailable in pytest")
        self.timeout_seconds = timeout_seconds
        self.base_url = base_url.rstrip("/")

    def execute(self, preview: HistoricalChartRequestPreview, *, auth_header: str | None = None) -> dict[str, object]:
        body = json.dumps(preview.body_json).encode("utf-8")
        req = request.Request(
            f"{self.base_url}{preview.path}",
            data=body,
            method="POST",
            headers={
                "Content-Type": "application/json;charset=UTF-8",
                "api-id": str(preview.headers.get("api-id") or ""),
                "authorization": auth_header or "",
                "cont-yn": str(preview.headers.get("cont-yn") or "N"),
                "next-key": str(preview.headers.get("next-key") or ""),
            },
        )
        opener = request.build_opener(request.ProxyHandler({}))
        try:
            response = opener.open(req, timeout=self.timeout_seconds)
        except HTTPError as error:
            response = error
        with response:
            payload = json.loads(response.read().decode("utf-8"))
            return {
                "status_code": response.status,
                "headers": dict(response.headers.items()),
                "body_json": payload,
            }
