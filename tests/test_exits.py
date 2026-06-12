from __future__ import annotations

from datetime import date, timedelta

from stock_risk_mcp.exits import simulate_long_exit
from stock_risk_mcp.models import PriceBar
from stock_risk_mcp.paper_trading import ExitReason


def test_stop_loss_take_profit_and_stop_priority() -> None:
    entry_date = date(2026, 1, 1)

    stop = simulate_long_exit(10, 9, 12, [_bar(entry_date, low=8.5, high=10.5, close=9)], entry_date, 10)
    target = simulate_long_exit(10, 9, 12, [_bar(entry_date, low=9.5, high=12.5, close=12)], entry_date, 10)
    both = simulate_long_exit(10, 9, 12, [_bar(entry_date, low=8.5, high=12.5, close=11)], entry_date, 10)

    assert stop.reason == ExitReason.STOP_LOSS
    assert stop.price == 9
    assert target.reason == ExitReason.TAKE_PROFIT
    assert target.price == 12
    assert both.reason == ExitReason.STOP_LOSS


def test_time_exit_and_no_data() -> None:
    entry_date = date(2026, 1, 1)
    bars = [
        _bar(entry_date + timedelta(days=1), low=9.5, high=10.5, close=10.2),
        _bar(entry_date + timedelta(days=5), low=9.7, high=10.8, close=10.6),
    ]

    time_exit = simulate_long_exit(10, 9, 12, bars, entry_date, 5)
    no_data = simulate_long_exit(10, 9, 12, [], entry_date, 5)

    assert time_exit.reason == ExitReason.TIME_EXIT
    assert time_exit.date == entry_date + timedelta(days=5)
    assert time_exit.price == 10.6
    assert no_data.reason == ExitReason.NO_DATA
    assert no_data.price is None


def _bar(day: date, low: float, high: float, close: float) -> PriceBar:
    return PriceBar(ticker="SAFE", date=day, low=low, high=high, close=close)
