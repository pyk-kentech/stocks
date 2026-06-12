from __future__ import annotations

import math
from datetime import date, timedelta

import pytest

from stock_risk_mcp.indicator_calculators import calculate_indicators
from stock_risk_mcp.models import PriceBar


def test_calculate_supported_price_history_indicators() -> None:
    bars = _bars(121)

    values = calculate_indicators(bars)

    assert values["RETURN_1D_PCT"] == pytest.approx(((221 / 220) - 1) * 100)
    assert values["RETURN_5D_PCT"] == pytest.approx(((221 / 216) - 1) * 100)
    assert values["RETURN_20D_PCT"] == pytest.approx(((221 / 201) - 1) * 100)
    assert values["RETURN_60D_PCT"] == pytest.approx(((221 / 161) - 1) * 100)
    assert values["SMA_20"] == pytest.approx(sum(range(202, 222)) / 20)
    assert values["SMA_60"] == pytest.approx(sum(range(162, 222)) / 60)
    assert values["SMA_120"] == pytest.approx(sum(range(102, 222)) / 120)
    assert values["DISTANCE_FROM_SMA_20_PCT"] == pytest.approx(((221 / values["SMA_20"]) - 1) * 100)
    assert values["DISTANCE_FROM_SMA_60_PCT"] == pytest.approx(((221 / values["SMA_60"]) - 1) * 100)
    assert values["AVG_DOLLAR_VOLUME_20D"] == pytest.approx(sum(close * 1000 for close in range(202, 222)) / 20)
    assert values["VOLUME_SPIKE_RATIO"] == pytest.approx(1)
    assert values["DOLLAR_VOLUME_SPIKE_RATIO"] == pytest.approx(221000 / values["AVG_DOLLAR_VOLUME_20D"])

    daily_returns = [((current / previous) - 1) * 100 for previous, current in zip(range(201, 221), range(202, 222))]
    assert values["VOLATILITY_20D_PCT"] == pytest.approx(_pstdev(daily_returns))
    assert values["ATR_14_PCT"] == pytest.approx((2 / 221) * 100)
    assert values["MAX_DRAWDOWN_60D_PCT"] == pytest.approx(0)
    assert values["RSI_14"] == pytest.approx(100)

    last_20 = list(range(202, 222))
    std = _pstdev(last_20)
    expected_bollinger = (221 - ((sum(last_20) / 20) - 2 * std)) / (4 * std)
    assert values["BOLLINGER_POSITION"] == pytest.approx(expected_bollinger)


def test_calculators_handle_drawdown_volume_spike_and_insufficient_data() -> None:
    bars = _bars(10)
    values = calculate_indicators(bars)

    assert values["RETURN_1D_PCT"] is not None
    assert values["RETURN_20D_PCT"] is None
    assert values["SMA_20"] is None
    assert values["RSI_14"] is None
    assert values["BOLLINGER_POSITION"] is None

    drawdown_bars = _custom_bars([100] * 55 + [90, 80, 70, 60, 50], [1000] * 59 + [10000])
    drawdown_values = calculate_indicators(drawdown_bars)

    assert drawdown_values["MAX_DRAWDOWN_60D_PCT"] == pytest.approx(-50)
    assert drawdown_values["VOLUME_SPIKE_RATIO"] > 5


def _bars(count: int) -> list[PriceBar]:
    closes = [101 + index for index in range(count)]
    return _custom_bars(closes, [1000] * count)


def _custom_bars(closes: list[float], volumes: list[float]) -> list[PriceBar]:
    start = date(2026, 1, 1)
    return [
        PriceBar(
            ticker="SAFE",
            date=start + timedelta(days=index),
            high=close + 1,
            low=close - 1,
            close=close,
            volume=volumes[index],
        )
        for index, close in enumerate(closes)
    ]


def _pstdev(values: list[float]) -> float:
    mean = sum(values) / len(values)
    return math.sqrt(sum((value - mean) ** 2 for value in values) / len(values))
