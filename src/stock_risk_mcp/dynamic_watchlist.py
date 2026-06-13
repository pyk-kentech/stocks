from __future__ import annotations

import json
from dataclasses import dataclass

from stock_risk_mcp.realtime_market_data import (
    IntradayCandidateSignal,
    MarketRegion,
    RollingMarketMetrics,
    WatchlistEntry,
    WatchlistStatus,
)


@dataclass(frozen=True)
class WatchlistPromotionRule:
    min_dollar_volume_5m: float = 1_000_000
    max_hot_watchlist_size: int = 20


class DynamicWatchlist:
    def __init__(self, rule: WatchlistPromotionRule | None = None) -> None:
        self.rule = rule or WatchlistPromotionRule()

    def evaluate(
        self,
        metrics_list: list[RollingMarketMetrics],
        previous: dict[str, WatchlistEntry],
    ) -> tuple[list[WatchlistEntry], list[IntradayCandidateSignal]]:
        ranked: list[tuple[float, RollingMarketMetrics, list[str], bool]] = []
        for metrics in metrics_list:
            blocked = self._blocked(metrics)
            reasons = self._reasons(metrics)
            ranked.append((self._score(metrics), metrics, reasons, blocked))
        eligible = sorted(
            (item for item in ranked if item[2] and not item[3]),
            key=lambda item: (-item[0], item[1].symbol),
        )
        hot_symbols = {item[1].symbol for item in eligible[: self.rule.max_hot_watchlist_size]}
        entries: list[WatchlistEntry] = []
        signals: list[IntradayCandidateSignal] = []
        for score, metrics, reasons, blocked in ranked:
            old = previous.get(metrics.symbol)
            if blocked:
                status = WatchlistStatus.BLOCKED
            elif metrics.symbol in hot_symbols:
                status = WatchlistStatus.HOT
            elif old is not None and old.status == WatchlistStatus.HOT:
                status = WatchlistStatus.COOLING
            else:
                status = WatchlistStatus.CANDIDATE
            reason = ", ".join(reasons) if reasons else status.value.lower()
            entry = WatchlistEntry(
                symbol=metrics.symbol,
                region=metrics.region,
                status=status,
                first_seen_at=old.first_seen_at if old else metrics.as_of,
                last_seen_at=metrics.as_of,
                promotion_reason=reason,
                score=score,
                metrics_json=json.dumps(metrics.model_dump(mode="json"), ensure_ascii=False),
                warnings=metrics.warnings,
            )
            entries.append(entry)
            signals.append(IntradayCandidateSignal(
                symbol=metrics.symbol,
                region=metrics.region,
                status=status,
                score=score,
                reasons=reasons,
                metrics=metrics.model_dump(mode="json"),
                warnings=metrics.warnings,
                generated_at=metrics.as_of,
            ))
        return entries, signals

    def _reasons(self, metrics: RollingMarketMetrics) -> list[str]:
        reasons: list[str] = []
        if metrics.return_5m_pct is not None and metrics.return_5m_pct >= 3:
            reasons.append("return_5m_pct")
        if metrics.relative_volume is not None and metrics.relative_volume >= 3:
            reasons.append("relative_volume")
        if (
            self.rule.min_dollar_volume_5m > 0
            and metrics.dollar_volume_5m is not None
            and metrics.dollar_volume_5m >= self.rule.min_dollar_volume_5m
        ):
            reasons.append("dollar_volume_5m")
        if metrics.breakout_15m and metrics.relative_volume is not None and metrics.relative_volume >= 2:
            reasons.append("breakout_15m")
        return reasons

    @staticmethod
    def _blocked(metrics: RollingMarketMetrics) -> bool:
        return (
            metrics.region == MarketRegion.UNKNOWN
            or metrics.last_price is None
            or metrics.last_price <= 0
            or metrics.volume_1m is None
            or metrics.volume_1m <= 0
            or metrics.halt_or_bad_tick_warning
        )

    def _score(self, metrics: RollingMarketMetrics) -> float:
        dollar = 0.0
        if self.rule.min_dollar_volume_5m > 0 and metrics.dollar_volume_5m is not None:
            dollar = min(metrics.dollar_volume_5m / self.rule.min_dollar_volume_5m, 10)
        return (
            max(metrics.return_5m_pct or 0, 0)
            + min(metrics.relative_volume or 0, 10)
            + dollar
            + (2 if metrics.breakout_15m else 0)
            - 10 * len(metrics.warnings)
        )
