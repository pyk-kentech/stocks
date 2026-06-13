from __future__ import annotations

from datetime import date

from stock_risk_mcp.fx import FXConversion


class FXService:
    def __init__(self, repository) -> None:
        self.repository = repository

    def get_latest_fx_rate(
        self,
        base_currency: str,
        quote_currency: str,
        as_of_date: date,
        max_staleness_days: int = 7,
        manual_rate: float | None = None,
        manual_source_name: str = "manual",
    ) -> FXConversion:
        base, quote = base_currency.upper(), quote_currency.upper()
        if base == quote:
            return FXConversion(base_currency=base, quote_currency=quote, date=as_of_date, rate=1.0, source_name="same_currency")
        if manual_rate is not None:
            return FXConversion(
                base_currency=base, quote_currency=quote, date=as_of_date,
                rate=manual_rate, source_name=manual_source_name,
            )
        direct = self.repository.get_latest_fx_rate_asof(base, quote, as_of_date)
        inverse = None if direct else self.repository.get_latest_fx_rate_asof(quote, base, as_of_date)
        if direct:
            rate, item = float(direct["rate"]), direct
        elif inverse:
            rate, item = 1 / float(inverse["rate"]), inverse
        else:
            return FXConversion(
                base_currency=base, quote_currency=quote,
                warnings=[f"FX rate unavailable for {base}/{quote}; trading-currency values were preserved."],
            )
        fx_date = date.fromisoformat(str(item["date"]))
        stale = (as_of_date - fx_date).days > max_staleness_days
        warnings = [f"FX rate is stale: {fx_date.isoformat()}"] if stale else []
        return FXConversion(
            base_currency=base, quote_currency=quote, date=fx_date, rate=rate,
            source_name=item.get("source_name"), stale=stale, warnings=warnings,
        )

    def convert_amount(
        self, amount: float, from_currency: str, to_currency: str, as_of_date: date, **kwargs
    ) -> tuple[float | None, FXConversion]:
        conversion = self.get_latest_fx_rate(from_currency, to_currency, as_of_date, **kwargs)
        return conversion.convert(amount, from_currency, to_currency), conversion
