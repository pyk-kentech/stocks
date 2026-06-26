from __future__ import annotations

from statistics import mean

from stock_risk_mcp.divergence_features import calculate_divergence_features
from stock_risk_mcp.historical_market_data_models import HistoricalOhlcvRow
from stock_risk_mcp.hma_features import calculate_hma_features
from stock_risk_mcp.macd_features import calculate_macd_features
from stock_risk_mcp.offline_strategy_models import OfflineStrategyCandidate
from stock_risk_mcp.rsi_features import calculate_rsi_features
from stock_risk_mcp.technical_evidence_models import TechnicalOHLCVPoint


def _to_points(rows: list[HistoricalOhlcvRow]) -> list[TechnicalOHLCVPoint]:
    return [
        TechnicalOHLCVPoint(
            timestamp=row.observed_at,
            open=row.open_price or row.close_price,
            high=row.high_price or row.close_price,
            low=row.low_price or row.close_price,
            close=row.close_price,
            volume=row.volume or 0.0,
        )
        for row in sorted(rows, key=lambda item: item.observed_at)
    ]


def calculate_offline_strategy_indicators(rows: list[HistoricalOhlcvRow], candidate: OfflineStrategyCandidate) -> dict[str, float | bool | str | None]:
    del candidate
    points = _to_points(rows)
    closes = [point.close for point in points]
    volumes = [point.volume for point in points]
    macd = calculate_macd_features(points)
    rsi = calculate_rsi_features(points)
    hma = calculate_hma_features(points)
    divergence = calculate_divergence_features(closes, rsi.rsi_series)
    avg_volume = mean(volumes[-10:]) if len(volumes) >= 10 else (mean(volumes) if volumes else 0.0)
    latest = points[-1]
    body_ratio = abs(latest.close - latest.open) / max(latest.high - latest.low, 1e-9)
    upper_wick_ratio = (latest.high - max(latest.open, latest.close)) / max(latest.high - latest.low, 1e-9)
    close_location = (latest.close - latest.low) / max(latest.high - latest.low, 1e-9)
    prior_runup_pct = ((latest.close / points[-6].close) - 1.0) if len(points) >= 6 else 0.0
    return {
        "close": latest.close,
        "volume_ratio": (latest.volume / avg_volume) if avg_volume else None,
        "body_ratio": body_ratio,
        "upper_wick_ratio": upper_wick_ratio,
        "close_location": close_location,
        "prior_runup_pct": prior_runup_pct,
        "macd_golden_cross": macd.macd_golden_cross,
        "macd_dead_cross": macd.macd_dead_cross,
        "macd_bullish_reacceleration": macd.macd_bullish_reacceleration,
        "rsi_level": rsi.rsi_level,
        "rsi_50_reclaim": rsi.rsi_50_reclaim,
        "rsi_50_loss": rsi.rsi_50_loss,
        "rsi_overbought": rsi.rsi_overbought,
        "rsi_oversold": rsi.rsi_oversold,
        "hma100_trend_state": hma.hma100_trend_state,
        "bullish_rsi_divergence": divergence.bullish_rsi_divergence,
        "bearish_rsi_divergence": divergence.bearish_rsi_divergence,
    }
