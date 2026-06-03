from __future__ import annotations

from stock_risk_mcp.adapters.base import PortfolioAdapter
from stock_risk_mcp.models import Decision, PortfolioState
from stock_risk_mcp.service import RiskEvaluationService

from tests.utils import make_policy, make_proposal


class LowCashPortfolioAdapter(PortfolioAdapter):
    def get_portfolio_state(self, ticker: str, sector: str | None) -> PortfolioState:
        return PortfolioState(
            total_equity_usd=100_000,
            cash_usd=50,
            current_position_pct=0,
            sector_exposure_pct=0,
            daily_pnl_pct=0,
            open_orders_count=0,
        )


class FullPositionPortfolioAdapter(PortfolioAdapter):
    def get_portfolio_state(self, ticker: str, sector: str | None) -> PortfolioState:
        return PortfolioState(
            total_equity_usd=100_000,
            cash_usd=30_000,
            current_position_pct=5,
            sector_exposure_pct=0,
            daily_pnl_pct=0,
            open_orders_count=0,
        )


class DailyLossPortfolioAdapter(PortfolioAdapter):
    def get_portfolio_state(self, ticker: str, sector: str | None) -> PortfolioState:
        return PortfolioState(
            total_equity_usd=100_000,
            cash_usd=30_000,
            current_position_pct=0,
            sector_exposure_pct=0,
            daily_pnl_pct=-3,
            open_orders_count=0,
        )


def test_max_order_usd_does_not_exceed_cash() -> None:
    result = RiskEvaluationService(
        policy=make_policy(min_cash_pct=0),
        portfolio_adapter=LowCashPortfolioAdapter(),
    ).evaluate(make_proposal("SAFE"))
    assert result.max_order_usd <= 50


def test_full_position_blocks() -> None:
    result = RiskEvaluationService(
        policy=make_policy(),
        portfolio_adapter=FullPositionPortfolioAdapter(),
    ).evaluate(make_proposal("SAFE"))
    assert result.decision == Decision.BLOCK
    assert result.max_order_usd == 0


def test_daily_loss_at_limit_blocks() -> None:
    result = RiskEvaluationService(
        policy=make_policy(),
        portfolio_adapter=DailyLossPortfolioAdapter(),
    ).evaluate(make_proposal("SAFE"))
    assert result.decision == Decision.BLOCK
    assert any("일일 손실" in block for block in result.hard_blocks)
