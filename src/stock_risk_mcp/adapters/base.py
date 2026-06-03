from __future__ import annotations

from abc import ABC, abstractmethod

from stock_risk_mcp.models import CompanyRisk, MarketSnapshot, PortfolioState, TossSignal


class MarketDataAdapter(ABC):
    @abstractmethod
    def get_market_snapshot(self, ticker: str) -> MarketSnapshot:
        raise NotImplementedError


class CompanyRiskAdapter(ABC):
    @abstractmethod
    def get_company_risk(self, ticker: str) -> CompanyRisk:
        raise NotImplementedError


class PortfolioAdapter(ABC):
    @abstractmethod
    def get_portfolio_state(self, ticker: str, sector: str | None) -> PortfolioState:
        raise NotImplementedError


class TossSignalAdapter(ABC):
    @abstractmethod
    def get_toss_signal(self, ticker: str) -> TossSignal:
        raise NotImplementedError
