from __future__ import annotations

from stock_risk_mcp.offline_strategy_indicator_engine import calculate_offline_strategy_indicators
from stock_risk_mcp.offline_strategy_models import (
    OfflineStrategyCandidate,
    OfflineStrategyFamily,
    OfflineStrategySignal,
    OfflineStrategySignalAction,
)


def build_offline_strategy_signals(dataset_id: str, rows_by_instrument: dict[str, list], candidate: OfflineStrategyCandidate) -> list[OfflineStrategySignal]:
    signals: list[OfflineStrategySignal] = []
    for instrument_id, rows in rows_by_instrument.items():
        if len(rows) < 20:
            continue
        features = calculate_offline_strategy_indicators(rows, candidate)
        action = OfflineStrategySignalAction.HOLD
        rationale = "insufficient setup"
        if candidate.family == OfflineStrategyFamily.VOLUME_PULLBACK_LONG:
            if (features.get("volume_ratio") or 0) >= float(candidate.parameter_values.get("VOLUME_MULTIPLIER", 1.5)) and (features.get("body_ratio") or 0) >= 0.5:
                action = OfflineStrategySignalAction.ENTER_LONG
                rationale = "volume expansion with strong body candle"
        elif candidate.family == OfflineStrategyFamily.UPPER_WICK_REVERSAL:
            if (features.get("upper_wick_ratio") or 0) >= float(candidate.parameter_values.get("UPPER_WICK_RATIO", 0.4)):
                action = OfflineStrategySignalAction.AVOID_LONG
                rationale = "upper wick exhaustion detected"
            else:
                action = OfflineStrategySignalAction.RISK_WARNING
                rationale = "reversal template remains research-only"
        elif candidate.family == OfflineStrategyFamily.RSI_OVERSOLD_REBOUND:
            if features.get("rsi_oversold") or (features.get("rsi_level") or 100) <= float(candidate.parameter_values.get("OVERSOLD_THRESHOLD", 30.0)):
                action = OfflineStrategySignalAction.ENTER_LONG
                rationale = "oversold rebound signal"
        elif candidate.family == OfflineStrategyFamily.MACD_RSI_MOMENTUM:
            rsi_level = features.get("rsi_level") or 0
            if features.get("macd_golden_cross") and (rsi_level >= 50 and rsi_level <= 70 or features.get("rsi_50_reclaim")):
                action = OfflineStrategySignalAction.ENTER_LONG
                rationale = "macd and rsi momentum confirmation"
        signals.append(
            OfflineStrategySignal(
                signal_id=f"{dataset_id}-{candidate.candidate_id}-{instrument_id}-{rows[-1].observed_at.isoformat()}",
                candidate_id=candidate.candidate_id,
                instrument_id=instrument_id,
                observed_at=rows[-1].observed_at,
                action=action,
                rationale=rationale,
                signal_features=features,
            )
        )
    return signals
