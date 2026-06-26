from __future__ import annotations

from collections import defaultdict

from stock_risk_mcp.offline_strategy_models import (
    OfflineStrategyBacktestResult,
    OfflineStrategyCandidate,
    OfflineStrategyExitReason,
    OfflineStrategyReadinessStatus,
    OfflineStrategySignalAction,
    OfflineStrategySimulatedTrade,
    OfflineStrategyTradeIntent,
)


def build_offline_strategy_backtest(dataset_id: str, rows_by_instrument: dict[str, list], candidate: OfflineStrategyCandidate, signals, fee_bps: float, slippage_bps: float) -> tuple[list[OfflineStrategyTradeIntent], OfflineStrategyBacktestResult]:
    intents: list[OfflineStrategyTradeIntent] = []
    trades: list[OfflineStrategySimulatedTrade] = []
    signals_by_instrument = defaultdict(list)
    for signal in signals:
        signals_by_instrument[signal.instrument_id].append(signal)
    for instrument_id, instrument_signals in signals_by_instrument.items():
        rows = rows_by_instrument[instrument_id]
        row_by_time = {row.observed_at: index for index, row in enumerate(rows)}
        for signal in instrument_signals:
            if signal.action != OfflineStrategySignalAction.ENTER_LONG:
                continue
            signal_index = row_by_time.get(signal.observed_at)
            if signal_index is None or signal_index + 1 >= len(rows):
                continue
            entry_row = rows[signal_index + 1]
            exit_index = min(signal_index + 4, len(rows) - 1)
            exit_row = rows[exit_index]
            entry_price = entry_row.open_price or entry_row.close_price
            exit_price = exit_row.close_price
            gross_return = (exit_price / entry_price) - 1.0
            net_return = gross_return - (fee_bps + slippage_bps) / 10_000.0
            intent = OfflineStrategyTradeIntent(
                intent_id=f"{dataset_id}-{candidate.candidate_id}-{instrument_id}-{signal.signal_id}-INTENT",
                candidate_id=candidate.candidate_id,
                signal_id=signal.signal_id,
                instrument_id=instrument_id,
                action=signal.action,
                entry_after_at=entry_row.observed_at,
                stop_reference=entry_row.low_price or entry_price,
                target_reference=entry_price * 1.02,
            )
            intents.append(intent)
            trades.append(
                OfflineStrategySimulatedTrade(
                    trade_id=f"{dataset_id}-{candidate.candidate_id}-{instrument_id}-{signal.signal_id}-TRADE",
                    candidate_id=candidate.candidate_id,
                    instrument_id=instrument_id,
                    entry_at=entry_row.observed_at,
                    exit_at=exit_row.observed_at,
                    entry_price=entry_price,
                    exit_price=exit_price,
                    gross_return=gross_return,
                    net_return=net_return,
                    exit_reason=OfflineStrategyExitReason.TIME_EXIT,
                    split_role="TEST",
                )
            )
    cumulative_return = sum(trade.net_return for trade in trades)
    running = 0.0
    peak = 0.0
    max_drawdown = 0.0
    for trade in trades:
        running += trade.net_return
        peak = max(peak, running)
        max_drawdown = min(max_drawdown, running - peak)
    result = OfflineStrategyBacktestResult(
        result_id=f"{dataset_id}-{candidate.candidate_id}-BACKTEST-RESULT",
        candidate_id=candidate.candidate_id,
        readiness_status=OfflineStrategyReadinessStatus.BACKTEST_READY,
        trade_count=len(trades),
        cumulative_return=cumulative_return,
        max_drawdown=abs(max_drawdown),
        trades=trades,
        warnings=["LOW_LIQUIDITY_WARNING_APPLIED"] if candidate.asset_liquidity_profile.value in {"SMALL_CAP", "LOW_LIQUIDITY_WARNING", "HIGH_VOLATILITY_MOMENTUM"} else [],
    )
    return intents, result
