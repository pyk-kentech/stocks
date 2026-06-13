from __future__ import annotations

from datetime import date as Date
from enum import StrEnum

from pydantic import Field

from stock_risk_mcp.models import StrictModel


class CurrencyCode(StrEnum):
    USD = "USD"
    KRW = "KRW"
    UNKNOWN = "UNKNOWN"


class FXConversion(StrictModel):
    base_currency: str
    quote_currency: str
    date: Date | None = None
    rate: float | None = Field(default=None, gt=0)
    source_name: str | None = None
    stale: bool = False
    warnings: list[str] = Field(default_factory=list)

    def convert(self, amount: float, from_currency: str, to_currency: str) -> float | None:
        source, target = from_currency.upper(), to_currency.upper()
        if source == target:
            return amount
        if self.rate is None:
            return None
        if source == self.base_currency and target == self.quote_currency:
            return amount * self.rate
        if source == self.quote_currency and target == self.base_currency:
            return amount / self.rate
        return None


def convert_with_rate(amount: float, from_currency: str, to_currency: str, rate: float | None) -> float | None:
    if str(from_currency).upper() == str(to_currency).upper():
        return amount
    return amount * rate if rate is not None else None
