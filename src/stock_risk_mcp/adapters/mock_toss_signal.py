from __future__ import annotations

from stock_risk_mcp.adapters.base import TossSignalAdapter
from stock_risk_mcp.models import SignalLevel, TossSignal


class MockTossSignalAdapter(TossSignalAdapter):
    def get_toss_signal(self, ticker: str) -> TossSignal:
        symbol = ticker.upper()
        if symbol == "SAFE":
            return TossSignal(
                tracked_investors_holding=42,
                new_buy_count_7d=9,
                consensus_level=SignalLevel.HIGH,
                signal_quality=SignalLevel.HIGH,
                historical_follow_return_30d_pct=7.5,
            )
        if symbol == "WATCH":
            return TossSignal(
                tracked_investors_holding=15,
                new_buy_count_7d=3,
                consensus_level=SignalLevel.MEDIUM,
                signal_quality=SignalLevel.MEDIUM,
                historical_follow_return_30d_pct=1.2,
            )
        if symbol in {"PUMP", "DILUTE", "BAD"}:
            return TossSignal(
                tracked_investors_holding=4,
                new_buy_count_7d=1,
                consensus_level=SignalLevel.LOW,
                signal_quality=SignalLevel.LOW,
                historical_follow_return_30d_pct=-6,
            )
        return TossSignal(
            tracked_investors_holding=8,
            new_buy_count_7d=2,
            consensus_level=SignalLevel.MEDIUM,
            signal_quality=SignalLevel.MEDIUM,
            historical_follow_return_30d_pct=2,
        )
