from __future__ import annotations

from datetime import date

from pydantic import Field

from stock_risk_mcp.models import StrictModel


class PortfolioCurrencyContext(StrictModel):
    account_currency: str = "USD"
    trading_currency: str = "USD"
    as_of_date: date
    fx_rate: float | None = None
    fx_source_name: str | None = None
    fx_date: date | None = None
    fx_stale: bool = False
    account_equity_input: float | None = None
    cash_available_input: float | None = None
    account_equity_trading: float | None = None
    cash_available_trading: float | None = None
    warnings: list[str] = Field(default_factory=list)

    def trading_to_account(self, amount: float | None) -> float | None:
        if amount is None:
            return None
        if self.account_currency == self.trading_currency:
            return amount
        if self.fx_rate is None:
            return None
        return amount * self.fx_rate

    def account_to_trading(self, amount: float | None) -> float | None:
        if amount is None:
            return None
        if self.account_currency == self.trading_currency:
            return amount
        if self.fx_rate is None:
            return None
        return amount / self.fx_rate


def build_portfolio_currency_context(
    fx_service,
    account_currency: str,
    trading_currency: str,
    as_of_date: date,
    *,
    account_equity: float,
    cash_available: float,
    manual_rate: float | None = None,
    manual_source_name: str = "manual",
    max_staleness_days: int = 7,
) -> PortfolioCurrencyContext:
    account, trading = account_currency.upper(), trading_currency.upper()
    # Stored convention is trading/account, for example USD/KRW.
    conversion = fx_service.get_latest_fx_rate(
        trading, account, as_of_date, max_staleness_days, manual_rate, manual_source_name,
    )
    context = PortfolioCurrencyContext(
        account_currency=account, trading_currency=trading, as_of_date=as_of_date,
        fx_rate=conversion.rate, fx_source_name=conversion.source_name, fx_date=conversion.date,
        fx_stale=conversion.stale, account_equity_input=account_equity,
        cash_available_input=cash_available, warnings=conversion.warnings,
    )
    equity = context.account_to_trading(account_equity)
    cash = context.account_to_trading(cash_available)
    return context.model_copy(update={
        "account_equity_trading": equity if equity is not None else account_equity,
        "cash_available_trading": cash if cash is not None else cash_available,
    })
