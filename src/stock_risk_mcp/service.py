from __future__ import annotations

from dataclasses import dataclass

from stock_risk_mcp.adapters.base import (
    CompanyRiskAdapter,
    MarketDataAdapter,
    PortfolioAdapter,
    TossSignalAdapter,
)
from stock_risk_mcp.adapters.mock_company_risk import MockCompanyRiskAdapter
from stock_risk_mcp.adapters.mock_market_data import MockMarketDataAdapter
from stock_risk_mcp.adapters.mock_portfolio import MockPortfolioAdapter
from stock_risk_mcp.adapters.mock_toss_signal import MockTossSignalAdapter
from stock_risk_mcp.models import CompanyRisk, MarketSnapshot, PortfolioState, RiskPolicy, RiskResult, TossSignal, TradeProposal
from stock_risk_mcp.policy import load_policy
from stock_risk_mcp.risk_engine import evaluate_trade_risk


@dataclass(frozen=True)
class EvaluationContext:
    proposal: TradeProposal
    market: MarketSnapshot
    company: CompanyRisk
    portfolio: PortfolioState
    toss_signal: TossSignal
    policy: RiskPolicy
    result: RiskResult


class RiskEvaluationService:
    def __init__(
        self,
        policy: RiskPolicy | None = None,
        market_adapter: MarketDataAdapter | None = None,
        company_risk_adapter: CompanyRiskAdapter | None = None,
        portfolio_adapter: PortfolioAdapter | None = None,
        toss_signal_adapter: TossSignalAdapter | None = None,
    ) -> None:
        self.policy = policy or load_policy()
        self.market_adapter = market_adapter or MockMarketDataAdapter()
        self.company_risk_adapter = company_risk_adapter or MockCompanyRiskAdapter()
        self.portfolio_adapter = portfolio_adapter or MockPortfolioAdapter()
        self.toss_signal_adapter = toss_signal_adapter or MockTossSignalAdapter()

    def evaluate(self, proposal: TradeProposal) -> RiskResult:
        return self.evaluate_with_context(proposal).result

    def evaluate_with_context(self, proposal: TradeProposal) -> EvaluationContext:
        market = self.market_adapter.get_market_snapshot(proposal.ticker)
        company = self.company_risk_adapter.get_company_risk(proposal.ticker)
        portfolio = self.portfolio_adapter.get_portfolio_state(proposal.ticker, market.sector)
        toss_signal = self.toss_signal_adapter.get_toss_signal(proposal.ticker)
        result = evaluate_trade_risk(
            proposal=proposal,
            market=market,
            company=company,
            portfolio=portfolio,
            toss_signal=toss_signal,
            policy=self.policy,
        )
        return EvaluationContext(
            proposal=proposal,
            market=market,
            company=company,
            portfolio=portfolio,
            toss_signal=toss_signal,
            policy=self.policy,
            result=result,
        )
