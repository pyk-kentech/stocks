from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta

from stock_risk_mcp.models import PriceBar
from stock_risk_mcp.paper_trading import ExitReason
from stock_risk_mcp.price_history import sort_price_bars


@dataclass(frozen=True)
class ExitSimulationResult:
    reason: ExitReason
    date: date | None = None
    price: float | None = None


def simulate_long_exit(
    entry_price: float,
    stop_price: float,
    target_price: float | None,
    price_bars: list[PriceBar],
    entry_date: date,
    horizon_days: int,
) -> ExitSimulationResult:
    bars = [bar for bar in sort_price_bars(price_bars) if bar.date >= entry_date]
    if not bars:
        return ExitSimulationResult(reason=ExitReason.NO_DATA)
    horizon_date = entry_date + timedelta(days=horizon_days)
    within_horizon = [bar for bar in bars if bar.date <= horizon_date]
    for bar in within_horizon:
        low = bar.low if bar.low is not None else bar.close
        high = bar.high if bar.high is not None else bar.close
        if low <= stop_price:
            return ExitSimulationResult(reason=ExitReason.STOP_LOSS, date=bar.date, price=stop_price)
        if target_price is not None and high >= target_price:
            return ExitSimulationResult(reason=ExitReason.TAKE_PROFIT, date=bar.date, price=target_price)
    exit_bar = next((bar for bar in bars if bar.date >= horizon_date), within_horizon[-1] if within_horizon else None)
    if exit_bar is None:
        return ExitSimulationResult(reason=ExitReason.NO_DATA)
    return ExitSimulationResult(reason=ExitReason.TIME_EXIT, date=exit_bar.date, price=exit_bar.close)
