from __future__ import annotations

from datetime import date

from stock_risk_mcp.models import BacktestOutcome, PriceBar
from stock_risk_mcp.performance import (
    calculate_max_drawdown_pct,
    calculate_max_gain_pct,
    calculate_return_pct,
    classify_outcome,
)


def test_return_pct_is_calculated() -> None:
    assert calculate_return_pct(100, 110) == 10.0
    assert calculate_return_pct(100, 97) == -3.0


def test_max_drawdown_pct_is_calculated_from_lows() -> None:
    bars = [
        PriceBar(ticker="SAFE", date=date(2026, 1, 1), low=98, close=100),
        PriceBar(ticker="SAFE", date=date(2026, 1, 2), low=90, close=105),
        PriceBar(ticker="SAFE", date=date(2026, 1, 3), low=95, close=110),
    ]
    assert calculate_max_drawdown_pct(bars, 100) == -10.0


def test_max_gain_pct_is_calculated_from_highs() -> None:
    bars = [
        PriceBar(ticker="SAFE", date=date(2026, 1, 1), high=102, close=100),
        PriceBar(ticker="SAFE", date=date(2026, 1, 2), high=115, close=105),
        PriceBar(ticker="SAFE", date=date(2026, 1, 3), high=108, close=104),
    ]
    assert calculate_max_gain_pct(bars, 100) == 15.0


def test_outcome_classification() -> None:
    assert classify_outcome(3.0) == BacktestOutcome.WIN
    assert classify_outcome(-3.0) == BacktestOutcome.LOSS
    assert classify_outcome(2.99) == BacktestOutcome.FLAT
    assert classify_outcome(None) == BacktestOutcome.NO_DATA
