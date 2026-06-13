from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta

from stock_risk_mcp.realtime_market_data import MarketDataEvent, MarketRegion, RollingMarketMetrics


@dataclass
class _Bucket:
    event_time: datetime
    price: float | None
    high: float | None
    low: float | None
    volume: float | None
    dollar_volume: float | None
    source_name: str
    warnings: list[str]


class RollingMarketMetricsCalculator:
    def __init__(self) -> None:
        self._buckets: dict[tuple[str, MarketRegion], dict[datetime, _Bucket]] = {}
        self._warnings: dict[tuple[str, MarketRegion], list[str]] = {}
        self._latest_event_time: dict[tuple[str, MarketRegion], datetime] = {}

    def add(self, event: MarketDataEvent) -> None:
        key = (event.symbol, event.region)
        bucket_time = event.event_time.replace(second=0, microsecond=0)
        buckets = self._buckets.setdefault(key, {})
        price = event.close if event.close is not None else event.price
        warnings: list[str] = []
        latest_event_time = self._latest_event_time.get(key)
        if latest_event_time is not None and event.event_time < latest_event_time:
            warnings.append("out_of_order_event")
        self._latest_event_time[key] = max(event.event_time, latest_event_time or event.event_time)
        if price is not None and price <= 0:
            warnings.append("bad_price")
            price = None
        if event.volume is not None and event.volume <= 0:
            warnings.append("bad_volume")
        state_warnings = self._warnings.setdefault(key, [])
        state_warnings.extend(item for item in warnings if item not in state_warnings)
        previous = buckets.get(bucket_time)
        if previous is None:
            buckets[bucket_time] = _Bucket(
                bucket_time, price, event.high or price, event.low or price,
                event.volume, event.dollar_volume, event.source_name, warnings,
            )
            return
        valid_volume = event.volume if event.volume is not None and event.volume > 0 else 0
        previous_volume = previous.volume if previous.volume is not None and previous.volume > 0 else 0
        previous.price = price if price is not None else previous.price
        previous.high = max(value for value in (previous.high, event.high, price) if value is not None)
        previous.low = min(value for value in (previous.low, event.low, price) if value is not None)
        previous.volume = previous_volume + valid_volume
        previous.dollar_volume = (previous.dollar_volume or 0) + (event.dollar_volume or 0)
        previous.warnings.extend(item for item in warnings if item not in previous.warnings)

    def latest(self, symbol: str, region: MarketRegion) -> RollingMarketMetrics:
        key = (symbol.strip().upper(), region)
        ordered = sorted(self._buckets.get(key, {}).values(), key=lambda item: item.event_time)
        if not ordered:
            raise LookupError(f"No realtime metrics for {key[0]} {region.value}")
        current = ordered[-1]
        previous = ordered[:-1]
        warnings = list(self._warnings.get(key, []))
        valid_previous_volumes = [
            item.volume for item in reversed(previous) if item.volume is not None and item.volume > 0
        ][:15]
        relative_volume = None
        if current.volume is not None and current.volume > 0 and valid_previous_volumes:
            relative_volume = current.volume / (sum(valid_previous_volumes) / len(valid_previous_volumes))
            if len(valid_previous_volumes) < 15:
                warnings.append("low_history_for_relative_volume")
        elif current.volume is not None and current.volume <= 0 and "bad_volume" not in warnings:
            warnings.append("bad_volume")

        preceding_15 = [item for item in previous if item.event_time >= current.event_time - timedelta(minutes=15)]
        prior_highs = [item.high for item in preceding_15 if item.high is not None]
        window_15 = [item for item in ordered if item.event_time >= current.event_time - timedelta(minutes=14)]
        window_5 = [item for item in ordered if item.event_time >= current.event_time - timedelta(minutes=4)]
        highs = [item.high for item in window_15 if item.high is not None]
        lows = [item.low for item in window_15 if item.low is not None]
        return RollingMarketMetrics(
            symbol=key[0],
            region=region,
            as_of=current.event_time,
            last_price=current.price,
            return_1m_pct=self._return_at(ordered, current, 1),
            return_5m_pct=self._return_at(ordered, current, 5),
            return_15m_pct=self._return_at(ordered, current, 15),
            volume_1m=current.volume,
            volume_5m=self._positive_sum(item.volume for item in window_5),
            volume_15m=self._positive_sum(item.volume for item in window_15),
            dollar_volume_5m=self._positive_sum(item.dollar_volume for item in window_5),
            relative_volume=relative_volume,
            high_15m=max(highs) if highs else None,
            low_15m=min(lows) if lows else None,
            breakout_15m=bool(current.price is not None and prior_highs and current.price > max(prior_highs)),
            halt_or_bad_tick_warning=any(
                item in {"bad_price", "bad_volume", "out_of_order_event"} for item in warnings
            ),
            source_name=current.source_name,
            warnings=list(dict.fromkeys(warnings)),
        )

    @staticmethod
    def _return_at(ordered: list[_Bucket], current: _Bucket, minutes: int) -> float | None:
        if current.price is None:
            return None
        cutoff = current.event_time - timedelta(minutes=minutes)
        candidates = [item for item in ordered[:-1] if item.event_time <= cutoff and item.price and item.price > 0]
        if not candidates:
            return None
        return (current.price / candidates[-1].price - 1) * 100

    @staticmethod
    def _positive_sum(values) -> float | None:
        valid = [value for value in values if value is not None and value > 0]
        return sum(valid) if valid else None
