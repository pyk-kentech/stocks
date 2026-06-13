from datetime import date

from stock_risk_mcp.fx_risk import build_fx_aware_sizing
from stock_risk_mcp.portfolio_currency import PortfolioCurrencyContext


def test_fx_aware_sizing_preserves_max_loss_first_and_records_both_currencies() -> None:
    context = PortfolioCurrencyContext(
        account_currency="KRW", trading_currency="USD", as_of_date=date(2026, 6, 13),
        fx_rate=1380, account_equity_input=10_000_000, cash_available_input=5_000_000,
        account_equity_trading=7246.38, cash_available_trading=3623.19,
    )

    result = build_fx_aware_sizing("AAA", 10, 8.8, 20_000, context)

    assert round(result.max_loss_trading, 2) == 14.49
    assert result.shares == 12
    assert result.max_loss_account == 20_000
    assert result.notional_account == 165_600
