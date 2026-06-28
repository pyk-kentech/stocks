from __future__ import annotations

from collections import defaultdict
from statistics import median

from stock_risk_mcp.offline_strategy_models import (
    OfflineStrategyBacktestResult,
    OfflineStrategyCandidate,
    OfflineStrategyExitReason,
    OfflineStrategyReadinessStatus,
    OfflineStrategySignalAction,
    OfflineStrategySimulatedTrade,
    OfflineStrategyTradeIntent,
)


FILL_POLICY = "CONSERVATIVE_NEXT_BAR_FILL"


def _exit_signal_date(rows: list, signal_index: int, exit_index: int) -> object | None:
    if exit_index <= signal_index + 1:
        return rows[signal_index].observed_at
    return rows[exit_index - 1].observed_at


def _drawdown(trades: list[OfflineStrategySimulatedTrade]) -> tuple[float, float]:
    running = 0.0
    peak = 0.0
    max_drawdown = 0.0
    for trade in trades:
        running += trade.net_return
        peak = max(peak, running)
        max_drawdown = min(max_drawdown, running - peak)
    raw = abs(max_drawdown)
    capped = min(raw, 1.0)
    return raw, capped


def build_offline_strategy_backtest(
    dataset_id: str,
    rows_by_instrument: dict[str, list],
    candidate: OfflineStrategyCandidate,
    signals,
    fee_bps: float,
    slippage_bps: float,
) -> tuple[list[OfflineStrategyTradeIntent], OfflineStrategyBacktestResult]:
    intents: list[OfflineStrategyTradeIntent] = []
    trades: list[OfflineStrategySimulatedTrade] = []
    trade_audit_records: list[dict[str, object]] = []
    signals_by_instrument = defaultdict(list)
    for signal in signals:
        signals_by_instrument[signal.instrument_id].append(signal)

    entry_order_count = 0
    exit_order_count = 0
    forced_exit_count = 0
    end_of_data_exit_count = 0
    holding_period_exit_count = 0
    stop_loss_exit_count = 0
    take_profit_exit_count = 0
    signal_exit_count = 0
    unmatched_entry_count = 0
    unmatched_exit_count = 0
    same_bar_fill_count = 0
    lookahead_violation_count = 0
    leakage_audit_errors: list[str] = []
    holding_bars: list[int] = []
    first_entry_date = None
    first_exit_date = None
    last_entry_date = None
    last_exit_date = None

    for instrument_id, instrument_signals in signals_by_instrument.items():
        rows = rows_by_instrument[instrument_id]
        row_by_time = {row.observed_at: index for index, row in enumerate(rows)}
        for signal in instrument_signals:
            if signal.action != OfflineStrategySignalAction.ENTER_LONG:
                continue
            signal_index = row_by_time.get(signal.observed_at)
            if signal_index is None:
                unmatched_entry_count += 1
                leakage_audit_errors.append(f"{instrument_id}:SIGNAL_INDEX_MISSING")
                continue
            if signal_index + 1 >= len(rows):
                unmatched_entry_count += 1
                leakage_audit_errors.append(f"{instrument_id}:NEXT_BAR_FILL_UNAVAILABLE")
                continue
            entry_row = rows[signal_index + 1]
            entry_order_count += 1
            next_bar_fill_used = True
            same_bar_fill_detected = entry_row.observed_at <= signal.observed_at
            if same_bar_fill_detected:
                same_bar_fill_count += 1
                lookahead_violation_count += 1
                leakage_audit_errors.append(f"{instrument_id}:ENTRY_SAME_BAR_OR_EARLIER_FILL")
            exit_index = min(signal_index + 4, len(rows) - 1)
            exit_row = rows[exit_index]
            exit_signal_at = _exit_signal_date(rows, signal_index, exit_index)
            if exit_signal_at is not None and exit_row.observed_at < exit_signal_at:
                lookahead_violation_count += 1
                leakage_audit_errors.append(f"{instrument_id}:EXIT_FILL_PRECEDES_EXIT_SIGNAL")
            exit_reason = OfflineStrategyExitReason.TIME_EXIT
            forced_exit = False
            end_of_data_exit = False
            if exit_index == len(rows) - 1:
                end_of_data_exit = True
                end_of_data_exit_count += 1
                exit_reason = OfflineStrategyExitReason.DATA_GAP
            else:
                holding_period_exit_count += 1
            forced_exit = end_of_data_exit or exit_reason == OfflineStrategyExitReason.TIME_EXIT
            if forced_exit:
                forced_exit_count += 1
            exit_order_count += 1
            entry_price = entry_row.open_price or entry_row.close_price
            exit_price = exit_row.close_price
            gross_return = (exit_price / entry_price) - 1.0
            net_return = gross_return - (fee_bps + slippage_bps) / 10_000.0
            holding_bar_count = max(0, exit_index - (signal_index + 1))
            holding_bars.append(holding_bar_count)
            first_entry_date = entry_row.observed_at.isoformat() if first_entry_date is None else first_entry_date
            first_exit_date = exit_row.observed_at.isoformat() if first_exit_date is None else first_exit_date
            last_entry_date = entry_row.observed_at.isoformat()
            last_exit_date = exit_row.observed_at.isoformat()
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
                    exit_reason=exit_reason,
                    split_role="TEST",
                )
            )
            trade_audit_records.append(
                {
                    "candidate_id": candidate.candidate_id,
                    "instrument_id": instrument_id,
                    "signal_date": signal.observed_at.isoformat(),
                    "entry_fill_date": entry_row.observed_at.isoformat(),
                    "exit_signal_date": exit_signal_at.isoformat() if exit_signal_at is not None else None,
                    "exit_fill_date": exit_row.observed_at.isoformat(),
                    "fill_policy": FILL_POLICY,
                    "next_bar_fill_used": next_bar_fill_used,
                    "same_bar_fill_detected": same_bar_fill_detected,
                    "lookahead_detected": same_bar_fill_detected or (exit_signal_at is not None and exit_row.observed_at < exit_signal_at),
                    "exit_reason": exit_reason.value,
                    "holding_bars": holding_bar_count,
                    "forced_exit": forced_exit,
                    "end_of_data_exit": end_of_data_exit,
                    "signal_exit": False,
                }
            )

    cumulative_return = sum(trade.net_return for trade in trades)
    max_drawdown_raw, max_drawdown = _drawdown(trades)
    warnings = ["LOW_LIQUIDITY_WARNING_APPLIED"] if candidate.asset_liquidity_profile.value in {"SMALL_CAP", "LOW_LIQUIDITY_WARNING", "HIGH_VOLATILITY_MOMENTUM"} else []
    if max_drawdown_raw > 1.0:
        warnings.append("DRAWDOWN_UNIT_OR_CALCULATION_WARNING")
    leakage_audit_status = "LEAKAGE_AUDIT_FAILED" if leakage_audit_errors else "LEAKAGE_AUDIT_PASSED"
    trade_audit_summary = {
        "actual_trade_count": len(trades),
        "entry_order_count": entry_order_count,
        "exit_order_count": exit_order_count,
        "forced_exit_count": forced_exit_count,
        "end_of_data_exit_count": end_of_data_exit_count,
        "holding_period_exit_count": holding_period_exit_count,
        "stop_loss_exit_count": stop_loss_exit_count,
        "take_profit_exit_count": take_profit_exit_count,
        "signal_exit_count": signal_exit_count,
        "unmatched_entry_count": unmatched_entry_count,
        "unmatched_exit_count": unmatched_exit_count,
        "first_entry_date": first_entry_date,
        "first_exit_date": first_exit_date,
        "last_entry_date": last_entry_date,
        "last_exit_date": last_exit_date,
        "average_holding_bars": (sum(holding_bars) / len(holding_bars)) if holding_bars else 0.0,
        "median_holding_bars": float(median(holding_bars)) if holding_bars else 0.0,
        "fill_policy": FILL_POLICY,
        "next_bar_fill_used": True,
        "same_bar_fill_detected": same_bar_fill_count > 0,
        "lookahead_detected": lookahead_violation_count > 0,
        "same_bar_fill_count": same_bar_fill_count,
        "lookahead_violation_count": lookahead_violation_count,
        "leakage_audit_status": leakage_audit_status,
        "max_drawdown_value": max_drawdown,
        "max_drawdown_raw": max_drawdown_raw,
        "max_drawdown_unit": "FRACTION_OF_EQUITY",
        "max_drawdown_capped_to_1_if_fraction": max_drawdown_raw > 1.0,
    }
    result = OfflineStrategyBacktestResult(
        result_id=f"{dataset_id}-{candidate.candidate_id}-BACKTEST-RESULT",
        candidate_id=candidate.candidate_id,
        readiness_status=OfflineStrategyReadinessStatus.BACKTEST_READY,
        trade_count=len(trades),
        cumulative_return=cumulative_return,
        max_drawdown=max_drawdown,
        max_drawdown_raw=max_drawdown_raw,
        max_drawdown_unit="FRACTION_OF_EQUITY",
        max_drawdown_capped_to_1_if_fraction=max_drawdown_raw > 1.0,
        trades=trades,
        trade_audit_summary=trade_audit_summary,
        trade_audit_records=trade_audit_records,
        leakage_audit_status=leakage_audit_status,
        leakage_audit_errors=leakage_audit_errors,
        same_bar_fill_count=same_bar_fill_count,
        lookahead_violation_count=lookahead_violation_count,
        warnings=warnings,
    )
    return intents, result
