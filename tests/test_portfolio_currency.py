from datetime import date

from stock_risk_mcp.fx_service import FXService
from stock_risk_mcp.portfolio_currency import build_portfolio_currency_context
from stock_risk_mcp.repository import RiskRepository


def test_portfolio_context_converts_krw_inputs_to_usd_trading(tmp_path) -> None:
    repository = RiskRepository(tmp_path / "risk.sqlite3")
    context = build_portfolio_currency_context(
        FXService(repository), "KRW", "USD", date(2026, 6, 13),
        account_equity=10_000_000, cash_available=5_000_000, manual_rate=1380,
    )

    assert round(context.account_equity_trading, 2) == 7246.38
    assert round(context.cash_available_trading, 2) == 3623.19
    assert context.fx_rate == 1380


def test_portfolio_context_preserves_legacy_values_when_fx_missing(tmp_path) -> None:
    context = build_portfolio_currency_context(
        FXService(RiskRepository(tmp_path / "risk.sqlite3")), "KRW", "USD", date(2026, 6, 13),
        account_equity=100, cash_available=50,
    )

    assert context.account_equity_trading == 100
    assert context.cash_available_trading == 50
    assert context.fx_rate is None
    assert context.warnings
