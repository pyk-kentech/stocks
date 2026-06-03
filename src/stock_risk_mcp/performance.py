from __future__ import annotations

from stock_risk_mcp.models import BacktestOutcome, PriceBar


def calculate_return_pct(entry_price: float, exit_price: float) -> float:
    return round(((exit_price - entry_price) / entry_price) * 100, 4)


def calculate_max_drawdown_pct(price_bars: list[PriceBar], entry_price: float) -> float:
    if not price_bars:
        return 0.0
    lowest_low = min((bar.low if bar.low is not None else bar.close) for bar in price_bars)
    return round(((lowest_low - entry_price) / entry_price) * 100, 4)


def calculate_max_gain_pct(price_bars: list[PriceBar], entry_price: float) -> float:
    if not price_bars:
        return 0.0
    highest_high = max((bar.high if bar.high is not None else bar.close) for bar in price_bars)
    return round(((highest_high - entry_price) / entry_price) * 100, 4)


def classify_outcome(return_pct: float | None) -> BacktestOutcome:
    if return_pct is None:
        return BacktestOutcome.NO_DATA
    if return_pct >= 3.0:
        return BacktestOutcome.WIN
    if return_pct <= -3.0:
        return BacktestOutcome.LOSS
    return BacktestOutcome.FLAT
