from __future__ import annotations

from copy import deepcopy
from typing import Protocol


class KiwoomTransport(Protocol):
    def post(self, path: str, headers: dict, body: dict) -> dict: ...


class DisabledNetworkError(RuntimeError):
    pass


def default_fake_fixtures() -> dict:
    observed = "2026-06-13T10:00:00"
    return {
        "/readonly/stock-info": {"status": "COMPLETED", "record": {"ticker": "005930", "name": "Samsung Electronics", "market": "KOSPI", "sector": "Semiconductor", "observed_at": observed}},
        "/readonly/quote": {"status": "COMPLETED", "record": {"ticker": "005930", "price": 70000, "change": 100, "change_pct": 0.14, "volume": 100000, "trading_value": 7000000000, "observed_at": observed}},
        "/readonly/ranking": {"status": "COMPLETED", "records": [{"ticker": "005930", "name": "Samsung Electronics", "rank_type": "volume", "rank": 1, "price": 70000, "change_pct": 0.14, "volume": 100000, "trading_value": 7000000000, "observed_at": observed}]},
        "/readonly/flow": {"status": "COMPLETED", "records": [{"ticker": "005930", "foreign_net_buy_amount": 1000, "institution_net_buy_amount": 500, "foreign_net_buy_shares": 10, "institution_net_buy_shares": 5, "observed_at": observed}]},
        "/readonly/chart": {"status": "COMPLETED", "records": [{"ticker": "005930", "bar_time": observed, "open": 69900, "high": 70100, "low": 69800, "close": 70000, "volume": 1000}]},
        "/readonly/condition/list": {"status": "COMPLETED", "records": [{"condition_id": "C1", "condition_name": "Local momentum", "ticker": "005930", "name": "Samsung Electronics", "observed_at": observed}]},
        "/readonly/condition/run": {"status": "COMPLETED", "records": [{"condition_id": "C1", "condition_name": "Local momentum", "ticker": "005930", "name": "Samsung Electronics", "observed_at": observed}]},
    }


class FakeKiwoomTransport:
    def __init__(self, fixtures: dict | None = None) -> None:
        self.fixtures = fixtures or default_fake_fixtures()
        self.calls: list[dict] = []
        self._indices: dict[str, int] = {}

    def post(self, path: str, headers: dict, body: dict) -> dict:
        self.calls.append({"path": path, "body": deepcopy(body)})
        fixture = self.fixtures.get(path)
        if fixture is None:
            return {"status": "FAILED", "error": "fake fixture not found"}
        if isinstance(fixture, list):
            index = self._indices.get(path, 0)
            self._indices[path] = index + 1
            fixture = fixture[min(index, len(fixture) - 1)]
        return deepcopy(fixture)


class RealKiwoomHttpTransport:
    def post(self, path: str, headers: dict, body: dict) -> dict:
        raise DisabledNetworkError("real Kiwoom network transport disabled in v2.11")
