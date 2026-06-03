from __future__ import annotations

from datetime import date, timedelta
import statistics

from stock_risk_mcp.models import PriceBar


def normalize_ticker(ticker: str) -> str:
    return ticker.strip().upper()


def sort_price_bars(bars: list[PriceBar]) -> list[PriceBar]:
    return sorted(bars, key=lambda item: item.date)


def latest_bar(bars: list[PriceBar]) -> PriceBar:
    sorted_bars = sort_price_bars(bars)
    if not sorted_bars:
        raise ValueError("Price history is empty")
    return sorted_bars[-1]


def calculate_return_pct_from_bars(bars: list[PriceBar], lookback_days: int) -> float | None:
    sorted_bars = sort_price_bars(bars)
    if len(sorted_bars) <= lookback_days:
        return None
    current = sorted_bars[-1]
    previous = sorted_bars[-1 - lookback_days]
    return ((current.close / previous.close) - 1) * 100


def calculate_avg_dollar_volume(bars: list[PriceBar], window: int) -> float | None:
    sorted_bars = sort_price_bars(bars)
    if len(sorted_bars) < window:
        return None
    window_bars = sorted_bars[-window:]
    if any(bar.volume is None for bar in window_bars):
        return None
    return sum(bar.close * float(bar.volume) for bar in window_bars) / window


def calculate_daily_return_volatility(bars: list[PriceBar], window: int) -> float | None:
    sorted_bars = sort_price_bars(bars)
    if len(sorted_bars) <= window:
        return None
    window_bars = sorted_bars[-(window + 1) :]
    daily_returns = [
        ((current.close / previous.close) - 1) * 100
        for previous, current in zip(window_bars[:-1], window_bars[1:])
    ]
    return statistics.pstdev(daily_returns)


def select_entry_bar(price_bars: list[PriceBar], evaluation_date: date) -> PriceBar | None:
    return _first_bar_on_or_after(price_bars, evaluation_date)


def select_exit_bar(price_bars: list[PriceBar], entry_date: date, horizon_days: int) -> PriceBar | None:
    target_date = entry_date + timedelta(days=horizon_days)
    return _first_bar_on_or_after(price_bars, target_date)


def bars_between(price_bars: list[PriceBar], start_date: date, end_date: date) -> list[PriceBar]:
    return [bar for bar in sort_price_bars(price_bars) if start_date <= bar.date <= end_date]


def _first_bar_on_or_after(price_bars: list[PriceBar], target_date: date) -> PriceBar | None:
    for bar in sort_price_bars(price_bars):
        if bar.date >= target_date:
            return bar
    return None
