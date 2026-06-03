from __future__ import annotations

from stock_risk_mcp.adapters.base import PortfolioAdapter
from stock_risk_mcp.models import PortfolioState


class MockPortfolioAdapter(PortfolioAdapter):
    def get_portfolio_state(self, ticker: str, sector: str | None) -> PortfolioState:
        symbol = ticker.upper()
        if symbol == "FULL":
            return PortfolioState(
                total_equity_usd=100_000,
                cash_usd=30_000,
                current_position_pct=5,
                sector_exposure_pct=12,
                daily_pnl_pct=-0.2,
                open_orders_count=0,
            )
        if symbol == "DAILYLOSS":
            return PortfolioState(
                total_equity_usd=100_000,
                cash_usd=30_000,
                current_position_pct=0,
                sector_exposure_pct=12,
                daily_pnl_pct=-4,
                open_orders_count=0,
            )
        return PortfolioState(
            total_equity_usd=100_000,
            cash_usd=30_000,
            current_position_pct=0,
            sector_exposure_pct=8 if sector else 0,
            daily_pnl_pct=-0.2,
            open_orders_count=0,
        )
