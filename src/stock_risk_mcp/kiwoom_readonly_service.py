from __future__ import annotations

from stock_risk_mcp.kiwoom_readonly_adapter import KiwoomRestReadOnlyAdapter
from stock_risk_mcp.kiwoom_readonly_allowlist import KiwoomReadOnlyAllowlist
from stock_risk_mcp.kiwoom_readonly_models import (
    KiwoomEnvironment,
    KiwoomReadOnlyRequestAudit,
    KiwoomReadOnlyResponseAudit,
)
from stock_risk_mcp.repository import RiskRepository


class KiwoomReadOnlyService:
    def __init__(
        self,
        repository: RiskRepository,
        environment: KiwoomEnvironment = KiwoomEnvironment.MOCK,
        adapter: KiwoomRestReadOnlyAdapter | None = None,
    ) -> None:
        self.repository = repository
        self.adapter = adapter or KiwoomRestReadOnlyAdapter(environment=environment)
        self.allowlist = KiwoomReadOnlyAllowlist()

    def get_stock_info(self, ticker): return self._run("RO_STOCK_INFO", {"ticker": ticker}, lambda: self.adapter.get_stock_info(ticker))
    def get_quote(self, ticker): return self._run("RO_QUOTE", {"ticker": ticker}, lambda: self.adapter.get_quote(ticker))
    def get_rankings(self, rank_type, market): return self._run("RO_RANKING", {"market": market}, lambda: self.adapter.get_rankings(rank_type, market))
    def get_flow(self, ticker=None, market=None): return self._run("RO_FLOW", {"ticker": ticker, "market": market}, lambda: self.adapter.get_flow(ticker, market))
    def get_chart_bars(self, ticker, interval, count): return self._run("RO_CHART", {"ticker": ticker}, lambda: self.adapter.get_chart_bars(ticker, interval, count))
    def list_condition_searches(self): return self._run("RO_CONDITION_LIST", {}, self.adapter.list_condition_searches)
    def run_condition_search(self, condition_id): return self._run("RO_CONDITION_RUN", {"condition_id": condition_id}, lambda: self.adapter.run_condition_search(condition_id))

    def _run(self, api_id: str, selectors: dict, operation) -> dict:
        endpoint = next(item for item in self.allowlist.list_endpoints() if item.api_id == api_id)
        result = operation()
        request = KiwoomReadOnlyRequestAudit(
            api_id=api_id, path=endpoint.path, category=endpoint.category,
            ticker=selectors.get("ticker"), market=selectors.get("market"),
            condition_id=selectors.get("condition_id"), status=result["status"],
            error=result.get("error"), metadata_json={"network_access": False},
        )
        response = KiwoomReadOnlyResponseAudit(
            request_id=request.request_id, status=result["status"], error=result.get("error"),
            metadata_json={
                "network_access": False,
                "continuation_count": result.get("continuation_count", 0),
                "record_count": len(result.get("data", [])) if isinstance(result.get("data"), list) else int(result.get("data") is not None),
            },
        )
        self.repository.save_kiwoom_readonly_request(request)
        self.repository.save_kiwoom_readonly_response(response)
        return {**result, "request_id": request.request_id, "response_id": response.response_id}
