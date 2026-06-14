from __future__ import annotations

from stock_risk_mcp.kiwoom_readonly_models import KiwoomEndpointCategory, KiwoomReadOnlyEndpoint


FORBIDDEN_TERMS = {
    "order", "buy", "sell", "cancel", "account", "balance", "position", "holding",
    "fill", "execution", "cash", "margin", "credit",
}

DEFAULT_ENDPOINTS = [
    KiwoomReadOnlyEndpoint(api_id="RO_STOCK_INFO", path="/readonly/stock-info", category=KiwoomEndpointCategory.STOCK_INFO, description="internal deterministic stock info", read_only=True, enabled=True),
    KiwoomReadOnlyEndpoint(api_id="RO_QUOTE", path="/readonly/quote", category=KiwoomEndpointCategory.QUOTE, description="internal deterministic quote", read_only=True, enabled=True),
    KiwoomReadOnlyEndpoint(api_id="RO_RANKING", path="/readonly/ranking", category=KiwoomEndpointCategory.RANKING, description="internal deterministic ranking", read_only=True, enabled=True),
    KiwoomReadOnlyEndpoint(api_id="RO_FLOW", path="/readonly/flow", category=KiwoomEndpointCategory.FLOW, description="internal deterministic flow", read_only=True, enabled=True),
    KiwoomReadOnlyEndpoint(api_id="RO_CHART", path="/readonly/chart", category=KiwoomEndpointCategory.CHART, description="internal deterministic chart", read_only=True, enabled=True),
    KiwoomReadOnlyEndpoint(api_id="RO_CONDITION_LIST", path="/readonly/condition/list", category=KiwoomEndpointCategory.CONDITION_SEARCH, description="internal deterministic condition list", read_only=True, enabled=True),
    KiwoomReadOnlyEndpoint(api_id="RO_CONDITION_RUN", path="/readonly/condition/run", category=KiwoomEndpointCategory.CONDITION_SEARCH, description="internal deterministic condition search", read_only=True, enabled=True),
]


class KiwoomReadOnlyAllowlist:
    def __init__(self, endpoints: list[KiwoomReadOnlyEndpoint] | None = None) -> None:
        self._endpoints = list(DEFAULT_ENDPOINTS if endpoints is None else endpoints)
        for endpoint in self._endpoints:
            self._validate(endpoint)

    def list_endpoints(self) -> list[KiwoomReadOnlyEndpoint]:
        return list(self._endpoints)

    def require(self, api_id: str, path: str) -> KiwoomReadOnlyEndpoint:
        for endpoint in self._endpoints:
            if endpoint.api_id == api_id and endpoint.path == path:
                self._validate(endpoint)
                return endpoint
        raise ValueError("endpoint is not in the Kiwoom read-only allowlist")

    @staticmethod
    def _validate(endpoint: KiwoomReadOnlyEndpoint) -> None:
        if not endpoint.read_only or not endpoint.enabled:
            raise ValueError("endpoint is not enabled read-only")
        text = " ".join((endpoint.api_id, endpoint.path, endpoint.category.value, endpoint.description)).lower()
        if any(term in text for term in FORBIDDEN_TERMS):
            raise ValueError("forbidden endpoint term")
