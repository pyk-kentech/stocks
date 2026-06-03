from __future__ import annotations

from datetime import date, timedelta

from stock_risk_mcp.models import PriceBar


def select_entry_bar(price_bars: list[PriceBar], evaluation_date: date) -> PriceBar | None:
    return _first_bar_on_or_after(price_bars, evaluation_date)


def select_exit_bar(price_bars: list[PriceBar], entry_date: date, horizon_days: int) -> PriceBar | None:
    target_date = entry_date + timedelta(days=horizon_days)
    return _first_bar_on_or_after(price_bars, target_date)


def bars_between(price_bars: list[PriceBar], start_date: date, end_date: date) -> list[PriceBar]:
    return [bar for bar in sorted(price_bars, key=lambda item: item.date) if start_date <= bar.date <= end_date]


def _first_bar_on_or_after(price_bars: list[PriceBar], target_date: date) -> PriceBar | None:
    for bar in sorted(price_bars, key=lambda item: item.date):
        if bar.date >= target_date:
            return bar
    return None
