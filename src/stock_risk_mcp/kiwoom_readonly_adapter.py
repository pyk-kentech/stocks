from __future__ import annotations

from stock_risk_mcp.kiwoom_readonly_allowlist import KiwoomReadOnlyAllowlist
from stock_risk_mcp.kiwoom_readonly_models import (
    KiwoomChartBar,
    KiwoomConditionSearchItem,
    KiwoomEnvironment,
    KiwoomFlowItem,
    KiwoomQuote,
    KiwoomRankItem,
    KiwoomStockInfo,
)
from stock_risk_mcp.kiwoom_rest_client import KiwoomRestClient


class KiwoomRestReadOnlyAdapter:
    def __init__(
        self,
        environment: KiwoomEnvironment = KiwoomEnvironment.MOCK,
        client: KiwoomRestClient | None = None,
    ) -> None:
        self.environment = environment
        self.client = client or KiwoomRestClient()
        self.allowlist = KiwoomReadOnlyAllowlist()

    def health_check(self) -> dict:
        if self.environment != KiwoomEnvironment.MOCK:
            return {"status": "DISABLED", "environment": self.environment.value, "network_access": False}
        return {"status": "CONNECTED", "environment": self.environment.value, "network_access": False}

    def list_readonly_endpoints(self):
        return self.allowlist.list_endpoints()

    def get_stock_info(self, ticker: str) -> dict:
        return self._one("RO_STOCK_INFO", "/readonly/stock-info", {"ticker": ticker}, KiwoomStockInfo)

    def get_quote(self, ticker: str) -> dict:
        return self._one("RO_QUOTE", "/readonly/quote", {"ticker": ticker}, KiwoomQuote)

    def get_rankings(self, rank_type: str, market: str) -> dict:
        return self._many("RO_RANKING", "/readonly/ranking", {"rank_type": rank_type, "market": market}, KiwoomRankItem)

    def get_flow(self, ticker: str | None = None, market: str | None = None) -> dict:
        return self._many("RO_FLOW", "/readonly/flow", {"ticker": ticker, "market": market}, KiwoomFlowItem)

    def get_chart_bars(self, ticker: str, interval: str, count: int) -> dict:
        return self._many("RO_CHART", "/readonly/chart", {"ticker": ticker, "interval": interval, "count": count}, KiwoomChartBar)

    def list_condition_searches(self) -> dict:
        return self._many("RO_CONDITION_LIST", "/readonly/condition/list", {}, KiwoomConditionSearchItem)

    def run_condition_search(self, condition_id: str) -> dict:
        return self._many("RO_CONDITION_RUN", "/readonly/condition/run", {"condition_id": condition_id}, KiwoomConditionSearchItem)

    def _one(self, api_id: str, path: str, body: dict, model) -> dict:
        result = self._request(api_id, path, body)
        if result["status"] != "COMPLETED":
            return result
        record = result.get("record")
        return {**result, "data": model(**record, source_name="kiwoom-fake", raw_json=record) if record else None}

    def _many(self, api_id: str, path: str, body: dict, model) -> dict:
        result = self._request(api_id, path, body)
        if result["status"] != "COMPLETED":
            return result
        return {**result, "data": [model(**record, raw_json=record) for record in result.get("records", [])]}

    def _request(self, api_id: str, path: str, body: dict) -> dict:
        if self.environment != KiwoomEnvironment.MOCK:
            return {"status": "DISABLED", "error": "Kiwoom PROD network disabled in v2.11", "data": None}
        return self.client.request_readonly(api_id, path, body)
