from __future__ import annotations

import statistics

from stock_risk_mcp.models import PriceBar
from stock_risk_mcp.price_history import calculate_avg_dollar_volume, calculate_return_pct_from_bars, sort_price_bars


def calculate_indicators(bars: list[PriceBar]) -> dict[str, float | None]:
    sorted_bars = sort_price_bars(bars)
    if not sorted_bars:
        raise ValueError("Price history is empty")

    sma20 = _sma(sorted_bars, 20)
    sma60 = _sma(sorted_bars, 60)
    latest = sorted_bars[-1]
    return {
        "RETURN_1D_PCT": calculate_return_pct_from_bars(sorted_bars, 1),
        "RETURN_5D_PCT": calculate_return_pct_from_bars(sorted_bars, 5),
        "RETURN_20D_PCT": calculate_return_pct_from_bars(sorted_bars, 20),
        "RETURN_60D_PCT": calculate_return_pct_from_bars(sorted_bars, 60),
        "SMA_20": sma20,
        "SMA_60": sma60,
        "SMA_120": _sma(sorted_bars, 120),
        "DISTANCE_FROM_SMA_20_PCT": _distance_from_sma(latest.close, sma20),
        "DISTANCE_FROM_SMA_60_PCT": _distance_from_sma(latest.close, sma60),
        "AVG_DOLLAR_VOLUME_20D": calculate_avg_dollar_volume(sorted_bars, 20),
        "VOLUME_SPIKE_RATIO": _volume_spike_ratio(sorted_bars, 20),
        "DOLLAR_VOLUME_SPIKE_RATIO": _dollar_volume_spike_ratio(sorted_bars, 20),
        "VOLATILITY_20D_PCT": _volatility(sorted_bars, 20),
        "ATR_14_PCT": _atr_pct(sorted_bars, 14),
        "MAX_DRAWDOWN_60D_PCT": _max_drawdown(sorted_bars, 60),
        "RSI_14": _rsi(sorted_bars, 14),
        "BOLLINGER_POSITION": _bollinger_position(sorted_bars, 20),
    }


def _sma(bars: list[PriceBar], window: int) -> float | None:
    if len(bars) < window:
        return None
    return statistics.fmean(bar.close for bar in bars[-window:])


def _distance_from_sma(latest_close: float, sma: float | None) -> float | None:
    return ((latest_close / sma) - 1) * 100 if sma else None


def _volume_spike_ratio(bars: list[PriceBar], window: int) -> float | None:
    if len(bars) < window or any(bar.volume is None for bar in bars[-window:]):
        return None
    average = statistics.fmean(float(bar.volume) for bar in bars[-window:])
    return float(bars[-1].volume) / average if average else None


def _dollar_volume_spike_ratio(bars: list[PriceBar], window: int) -> float | None:
    average = calculate_avg_dollar_volume(bars, window)
    latest = bars[-1]
    if average is None or latest.volume is None or average == 0:
        return None
    return (latest.close * latest.volume) / average


def _volatility(bars: list[PriceBar], window: int) -> float | None:
    if len(bars) <= window:
        return None
    returns = [
        ((current.close / previous.close) - 1) * 100
        for previous, current in zip(bars[-(window + 1) : -1], bars[-window:])
    ]
    return statistics.pstdev(returns)


def _atr_pct(bars: list[PriceBar], window: int) -> float | None:
    if len(bars) <= window:
        return None
    selected = bars[-(window + 1) :]
    if any(bar.high is None or bar.low is None for bar in selected[1:]):
        return None
    true_ranges = [
        max(
            float(current.high) - float(current.low),
            abs(float(current.high) - previous.close),
            abs(float(current.low) - previous.close),
        )
        for previous, current in zip(selected[:-1], selected[1:])
    ]
    return statistics.fmean(true_ranges) / selected[-1].close * 100


def _max_drawdown(bars: list[PriceBar], window: int) -> float | None:
    if len(bars) < window:
        return None
    peak = bars[-window].close
    max_drawdown = 0.0
    for bar in bars[-window:]:
        peak = max(peak, bar.close)
        max_drawdown = min(max_drawdown, ((bar.close / peak) - 1) * 100)
    return max_drawdown


def _rsi(bars: list[PriceBar], window: int) -> float | None:
    if len(bars) <= window:
        return None
    changes = [current.close - previous.close for previous, current in zip(bars[-(window + 1) : -1], bars[-window:])]
    average_gain = statistics.fmean(max(change, 0) for change in changes)
    average_loss = statistics.fmean(max(-change, 0) for change in changes)
    if average_loss == 0:
        return 100.0 if average_gain > 0 else 50.0
    relative_strength = average_gain / average_loss
    return 100 - (100 / (1 + relative_strength))


def _bollinger_position(bars: list[PriceBar], window: int) -> float | None:
    if len(bars) < window:
        return None
    closes = [bar.close for bar in bars[-window:]]
    mean = statistics.fmean(closes)
    standard_deviation = statistics.pstdev(closes)
    if standard_deviation == 0:
        return None
    lower = mean - 2 * standard_deviation
    upper = mean + 2 * standard_deviation
    return (closes[-1] - lower) / (upper - lower)
