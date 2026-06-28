from __future__ import annotations

from dataclasses import dataclass

from stock_risk_mcp.historical_market_data_models import HistoricalOhlcvRow
from stock_risk_mcp.offline_strategy_models import (
    OfflineStrategyCandidate,
    OfflineStrategyFamily,
    OfflineStrategySignal,
    OfflineStrategySignalAction,
)


@dataclass
class OfflineStrategySignalBundle:
    signals: list[OfflineStrategySignal]
    diagnostics_by_instrument: dict[str, dict[str, object]]


def _mean(values: list[float]) -> float | None:
    return sum(values) / len(values) if values else None


def _ema_series(values: list[float], period: int) -> list[float]:
    if not values:
        return []
    alpha = 2.0 / (float(period) + 1.0)
    output = [values[0]]
    for value in values[1:]:
        output.append(alpha * value + (1.0 - alpha) * output[-1])
    return output


def _rsi_series(closes: list[float], period: int) -> list[float | None]:
    series: list[float | None] = [None] * len(closes)
    if len(closes) <= period:
        return series
    deltas = [right - left for left, right in zip(closes, closes[1:])]
    gain = sum(max(delta, 0.0) for delta in deltas[:period]) / float(period)
    loss = sum(max(-delta, 0.0) for delta in deltas[:period]) / float(period)

    def _value() -> float:
        if loss == 0 and gain > 0:
            return 100.0
        if loss == 0:
            return 50.0
        return 100.0 - (100.0 / (1.0 + gain / loss))

    series[period] = _value()
    for index, delta in enumerate(deltas[period:], start=period + 1):
        gain = (gain * (period - 1) + max(delta, 0.0)) / float(period)
        loss = (loss * (period - 1) + max(-delta, 0.0)) / float(period)
        series[index] = _value()
    return series


def _macd_series(closes: list[float], fast_period: int, slow_period: int, signal_period: int) -> tuple[list[float | None], list[float | None], list[float | None]]:
    if len(closes) < max(fast_period, slow_period):
        size = len(closes)
        return [None] * size, [None] * size, [None] * size
    fast = _ema_series(closes, fast_period)
    slow = _ema_series(closes, slow_period)
    line = [fast_value - slow_value for fast_value, slow_value in zip(fast, slow)]
    signal = _ema_series(line, signal_period)
    hist = [line_value - signal_value for line_value, signal_value in zip(line, signal)]
    return line, signal, hist


def _required_indicator_columns(family: OfflineStrategyFamily) -> list[str]:
    if family == OfflineStrategyFamily.VOLUME_PULLBACK_LONG:
        return ["OPEN_PRICE", "HIGH_PRICE", "LOW_PRICE", "CLOSE_PRICE", "VOLUME", "VOLUME_RATIO", "BODY_RATIO"]
    if family == OfflineStrategyFamily.RSI_OVERSOLD_REBOUND:
        return ["CLOSE_PRICE", "RSI_LEVEL"]
    if family == OfflineStrategyFamily.MACD_RSI_MOMENTUM:
        return ["CLOSE_PRICE", "VOLUME", "MACD_LINE", "MACD_SIGNAL", "RSI_LEVEL"]
    return ["CLOSE_PRICE"]


def _compact_columns(value: set[str]) -> str:
    return ",".join(sorted(item for item in value if item))


def _compact_counts(value: dict[str, int]) -> str:
    return ",".join(f"{key}={value[key]}" for key in sorted(value))


def _build_symbol_diagnostics(
    *,
    symbol: str,
    rows: list[HistoricalOhlcvRow],
    candidate_signals: list[OfflineStrategySignal],
    required_indicator_columns: list[str],
) -> dict[str, object]:
    available_columns: set[str] = set()
    missing_columns: set[str] = set()
    condition_pass_counts: dict[str, int] = {}
    condition_block_counts: dict[str, int] = {}
    first_possible_signal_date = None
    first_entry_signal_date = None
    last_entry_signal_date = None
    for signal in candidate_signals:
        features = signal.signal_features
        available_columns.update(
            str(item).upper()
            for item in str(features.get("indicator_columns_available") or "").split(",")
            if item
        )
        missing_columns.update(
            str(item).upper()
            for item in str(features.get("missing_indicator_columns") or "").split(",")
            if item
        )
        for key in (
            "rows_with_valid_indicator_window",
            "macd_cross_count",
            "rsi_condition_count",
            "volume_condition_count",
            "candle_condition_count",
            "pullback_condition_count",
            "rebound_condition_count",
            "final_entry_condition_count",
            "signal_count_before_filters",
        ):
            condition_pass_counts[key] = condition_pass_counts.get(key, 0) + int(features.get(key) or 0)
        for key in (
            "schema_gap_count",
            "hold_count",
            "blocked_by_missing_indicator_count",
            "blocked_by_condition_count",
        ):
            condition_block_counts[key] = condition_block_counts.get(key, 0) + int(features.get(key) or 0)
        if first_possible_signal_date is None and int(features.get("rows_with_valid_indicator_window") or 0) > 0:
            first_possible_signal_date = signal.observed_at.isoformat()
        if signal.action == OfflineStrategySignalAction.ENTER_LONG:
            if first_entry_signal_date is None:
                first_entry_signal_date = signal.observed_at.isoformat()
            last_entry_signal_date = signal.observed_at.isoformat()
    entry_signal_count = sum(1 for signal in candidate_signals if signal.action == OfflineStrategySignalAction.ENTER_LONG)
    exit_signal_count = sum(1 for signal in candidate_signals if signal.action == OfflineStrategySignalAction.EXIT_LONG)
    signal_count_before_filters = condition_pass_counts.get("signal_count_before_filters", 0)
    indicator_columns_available = sorted(set(required_indicator_columns) & available_columns)
    missing_indicator_columns = sorted(set(required_indicator_columns) - set(indicator_columns_available) | missing_columns)
    return {
        "symbol": symbol,
        "symbol_row_count": len(rows),
        "input_row_count": len(rows),
        "date_min": rows[0].observed_at.isoformat() if rows else None,
        "date_max": rows[-1].observed_at.isoformat() if rows else None,
        "indicator_columns_available": indicator_columns_available,
        "required_indicator_columns": required_indicator_columns,
        "missing_indicator_columns": missing_indicator_columns,
        "signal_input_schema_gap": bool(missing_indicator_columns),
        "signal_count_before_filters": signal_count_before_filters,
        "entry_signal_count": entry_signal_count,
        "exit_signal_count": exit_signal_count,
        "condition_pass_counts": condition_pass_counts,
        "condition_block_counts": condition_block_counts,
        "first_possible_signal_date": first_possible_signal_date,
        "first_entry_signal_date": first_entry_signal_date,
        "last_entry_signal_date": last_entry_signal_date,
        "rows_with_valid_indicator_window": condition_pass_counts.get("rows_with_valid_indicator_window", 0),
        "macd_cross_count": condition_pass_counts.get("macd_cross_count", 0),
        "rsi_condition_count": condition_pass_counts.get("rsi_condition_count", 0),
        "volume_condition_count": condition_pass_counts.get("volume_condition_count", 0),
        "candle_condition_count": condition_pass_counts.get("candle_condition_count", 0),
        "pullback_condition_count": condition_pass_counts.get("pullback_condition_count", 0),
        "rebound_condition_count": condition_pass_counts.get("rebound_condition_count", 0),
        "final_entry_condition_count": condition_pass_counts.get("final_entry_condition_count", 0),
    }


def _aggregate_candidate_diagnostics(diagnostics_by_instrument: dict[str, dict[str, object]]) -> dict[str, object]:
    aggregate: dict[str, object] = {
        "input_row_count": sum(int(item.get("input_row_count") or 0) for item in diagnostics_by_instrument.values()),
        "symbol_count": len(diagnostics_by_instrument),
        "entry_signal_count": sum(int(item.get("entry_signal_count") or 0) for item in diagnostics_by_instrument.values()),
        "exit_signal_count": sum(int(item.get("exit_signal_count") or 0) for item in diagnostics_by_instrument.values()),
        "signal_count_before_filters": sum(int(item.get("signal_count_before_filters") or 0) for item in diagnostics_by_instrument.values()),
        "signal_input_schema_gap_count": sum(1 for item in diagnostics_by_instrument.values() if item.get("signal_input_schema_gap")),
        "missing_indicator_columns": sorted(
            {
                column
                for item in diagnostics_by_instrument.values()
                for column in item.get("missing_indicator_columns", [])
            }
        ),
    }
    for key in (
        "rows_with_valid_indicator_window",
        "macd_cross_count",
        "rsi_condition_count",
        "volume_condition_count",
        "candle_condition_count",
        "pullback_condition_count",
        "rebound_condition_count",
        "final_entry_condition_count",
    ):
        aggregate[key] = sum(int(item.get(key) or 0) for item in diagnostics_by_instrument.values())
    return aggregate


def build_offline_strategy_signal_bundle(
    dataset_id: str,
    rows_by_instrument: dict[str, list[HistoricalOhlcvRow]],
    candidate: OfflineStrategyCandidate,
) -> OfflineStrategySignalBundle:
    signals: list[OfflineStrategySignal] = []
    diagnostics_by_instrument: dict[str, dict[str, object]] = {}
    required_indicator_columns = _required_indicator_columns(candidate.family)
    for instrument_id, instrument_rows in rows_by_instrument.items():
        rows = sorted(instrument_rows, key=lambda item: item.observed_at)
        if not rows:
            diagnostics_by_instrument[instrument_id] = {
                "symbol": instrument_id,
                "symbol_row_count": 0,
                "input_row_count": 0,
                "date_min": None,
                "date_max": None,
                "indicator_columns_available": [],
                "required_indicator_columns": required_indicator_columns,
                "missing_indicator_columns": required_indicator_columns,
                "signal_input_schema_gap": True,
                "signal_count_before_filters": 0,
                "entry_signal_count": 0,
                "exit_signal_count": 0,
                "condition_pass_counts": {},
                "condition_block_counts": {"schema_gap_count": 1},
                "first_possible_signal_date": None,
                "first_entry_signal_date": None,
                "last_entry_signal_date": None,
            }
            continue

        closes = [float(row.close_price) for row in rows]
        opens = [float(row.open_price or row.close_price) for row in rows]
        highs = [float(row.high_price or row.close_price) for row in rows]
        lows = [float(row.low_price or row.close_price) for row in rows]
        volumes = [float(row.volume or 0.0) for row in rows]
        rsi_period = int(candidate.parameter_values.get("RSI_PERIOD") or 14)
        oversold_threshold = float(candidate.parameter_values.get("OVERSOLD_THRESHOLD") or 30.0)
        rebound_threshold = float(candidate.parameter_values.get("REBOUND_THRESHOLD") or max(oversold_threshold + 5.0, 40.0))
        hold_bars = int(candidate.parameter_values.get("HOLD_BARS") or 1)
        macd_fast = int(candidate.parameter_values.get("MACD_FAST") or 12)
        macd_slow = int(candidate.parameter_values.get("MACD_SLOW") or 26)
        macd_signal_period = int(candidate.parameter_values.get("MACD_SIGNAL") or 9)
        rsi_midline = float(candidate.parameter_values.get("RSI_MIDLINE") or 50.0)
        allow_overbought = bool(candidate.parameter_values.get("ALLOW_OVERBOUGHT_SECOND_LEG") or False)
        volume_lookback = int(candidate.parameter_values.get("VOLUME_LOOKBACK") or 5)
        volume_multiplier = float(candidate.parameter_values.get("VOLUME_MULTIPLIER") or 1.5)
        pullback_max_bars = int(candidate.parameter_values.get("PULLBACK_MAX_BARS") or 2)
        rsi_values = _rsi_series(closes, rsi_period)
        macd_line, macd_signal_values, macd_hist = _macd_series(closes, macd_fast, macd_slow, macd_signal_period)
        candidate_signals: list[OfflineStrategySignal] = []
        min_history = max(3, rsi_period + 1, volume_lookback + 1, macd_slow + 1 if candidate.family == OfflineStrategyFamily.MACD_RSI_MOMENTUM else 3)
        for index, row in enumerate(rows):
            if index + 1 < min_history:
                continue
            prev_close = closes[index - 1]
            row_range = max(highs[index] - lows[index], 1e-9)
            body_ratio = abs(closes[index] - opens[index]) / row_range
            recent_volume_window = volumes[max(0, index - volume_lookback) : index]
            recent_volume_avg = _mean(recent_volume_window)
            volume_ratio = (volumes[index] / recent_volume_avg) if recent_volume_avg else None
            rsi_level = rsi_values[index]
            prev_rsi = rsi_values[index - 1] if index > 0 else None
            current_macd = macd_line[index] if index < len(macd_line) else None
            current_signal = macd_signal_values[index] if index < len(macd_signal_values) else None
            prev_macd = macd_line[index - 1] if index > 0 and index - 1 < len(macd_line) else None
            prev_signal = macd_signal_values[index - 1] if index > 0 and index - 1 < len(macd_signal_values) else None
            current_hist = macd_hist[index] if index < len(macd_hist) else None
            prev_hist = macd_hist[index - 1] if index > 0 and index - 1 < len(macd_hist) else None
            prior_hist = macd_hist[index - 2] if index > 1 and index - 2 < len(macd_hist) else None
            recent_pullback_down_closes = sum(
                1
                for pullback_index in range(max(1, index - pullback_max_bars), index)
                if closes[pullback_index] < closes[pullback_index - 1]
            )
            available_indicator_columns = {"CLOSE_PRICE"}
            missing_indicator_columns: set[str] = set()
            if row.open_price is not None:
                available_indicator_columns.add("OPEN_PRICE")
            else:
                missing_indicator_columns.add("OPEN_PRICE")
            if row.high_price is not None:
                available_indicator_columns.add("HIGH_PRICE")
            else:
                missing_indicator_columns.add("HIGH_PRICE")
            if row.low_price is not None:
                available_indicator_columns.add("LOW_PRICE")
            else:
                missing_indicator_columns.add("LOW_PRICE")
            if row.volume is not None:
                available_indicator_columns.add("VOLUME")
            else:
                missing_indicator_columns.add("VOLUME")
            if volume_ratio is not None:
                available_indicator_columns.add("VOLUME_RATIO")
            elif candidate.family == OfflineStrategyFamily.VOLUME_PULLBACK_LONG:
                missing_indicator_columns.add("VOLUME_RATIO")
            if rsi_level is not None:
                available_indicator_columns.add("RSI_LEVEL")
            elif candidate.family in {OfflineStrategyFamily.RSI_OVERSOLD_REBOUND, OfflineStrategyFamily.MACD_RSI_MOMENTUM}:
                missing_indicator_columns.add("RSI_LEVEL")
            if current_macd is not None:
                available_indicator_columns.add("MACD_LINE")
            elif candidate.family == OfflineStrategyFamily.MACD_RSI_MOMENTUM:
                missing_indicator_columns.add("MACD_LINE")
            if current_signal is not None:
                available_indicator_columns.add("MACD_SIGNAL")
            elif candidate.family == OfflineStrategyFamily.MACD_RSI_MOMENTUM:
                missing_indicator_columns.add("MACD_SIGNAL")
            available_indicator_columns.add("BODY_RATIO")
            if set(required_indicator_columns) - available_indicator_columns:
                missing_indicator_columns.update(set(required_indicator_columns) - available_indicator_columns)
            signal_input_schema_gap = bool(missing_indicator_columns)
            rows_with_valid_indicator_window = 0 if signal_input_schema_gap else 1
            macd_cross_count = 0
            rsi_condition_count = 0
            volume_condition_count = 0
            candle_condition_count = 0
            pullback_condition_count = 0
            rebound_condition_count = 0
            final_entry_condition_count = 0
            signal_count_before_filters = 0
            action = OfflineStrategySignalAction.HOLD
            rationale = "conditions not met"
            if signal_input_schema_gap:
                rationale = "signal input schema gap"
            elif candidate.family == OfflineStrategyFamily.VOLUME_PULLBACK_LONG:
                volume_condition = (volume_ratio or 0.0) >= volume_multiplier
                candle_condition = closes[index] > opens[index] and body_ratio >= 0.2
                pullback_condition = recent_pullback_down_closes >= 1
                relaxed_prefilter = volume_multiplier <= 1.0 and volume_condition and candle_condition
                volume_condition_count = int(volume_condition)
                candle_condition_count = int(candle_condition)
                pullback_condition_count = int(pullback_condition)
                signal_count_before_filters = int((volume_condition and candle_condition) or relaxed_prefilter)
                final_entry_condition_count = int(volume_condition and candle_condition and pullback_condition)
                if final_entry_condition_count:
                    action = OfflineStrategySignalAction.ENTER_LONG
                    rationale = "volume pullback entry setup"
                elif signal_count_before_filters:
                    rationale = "volume pullback prefilter triggered"
            elif candidate.family == OfflineStrategyFamily.RSI_OVERSOLD_REBOUND:
                oversold_recent = any(
                    value is not None and value <= oversold_threshold
                    for value in rsi_values[max(0, index - hold_bars) : index + 1]
                )
                rebound_condition = prev_rsi is not None and rsi_level is not None and prev_rsi < rebound_threshold <= rsi_level
                relaxed_prefilter = rsi_level is not None and oversold_threshold >= 35.0 and rsi_level >= rebound_threshold
                rsi_condition_count = int(oversold_recent)
                rebound_condition_count = int(rebound_condition)
                signal_count_before_filters = int(rebound_condition or relaxed_prefilter)
                final_entry_condition_count = int(oversold_recent and rebound_condition)
                if final_entry_condition_count:
                    action = OfflineStrategySignalAction.ENTER_LONG
                    rationale = "rsi oversold rebound entry setup"
                elif signal_count_before_filters:
                    rationale = "rsi rebound prefilter triggered"
            elif candidate.family == OfflineStrategyFamily.MACD_RSI_MOMENTUM:
                macd_cross = (
                    prev_macd is not None
                    and prev_signal is not None
                    and current_macd is not None
                    and current_signal is not None
                    and prev_macd <= prev_signal
                    and current_macd > current_signal
                )
                bullish_reacceleration = (
                    current_hist is not None
                    and prev_hist is not None
                    and prior_hist is not None
                    and current_hist > 0
                    and (current_hist - prev_hist) > 0
                    and ((current_hist - prev_hist) - (prev_hist - prior_hist)) >= 0
                )
                rsi_condition = rsi_level is not None and rsi_level >= rsi_midline and (allow_overbought or rsi_level <= 70.0)
                relaxed_prefilter = allow_overbought and current_macd is not None and current_signal is not None and current_macd > current_signal and rsi_level is not None and rsi_level >= (rsi_midline - 5.0)
                macd_cross_count = int(macd_cross or bullish_reacceleration)
                rsi_condition_count = int(rsi_condition)
                signal_count_before_filters = int((macd_cross and rsi_condition) or relaxed_prefilter)
                final_entry_condition_count = int(macd_cross and rsi_condition)
                if final_entry_condition_count:
                    action = OfflineStrategySignalAction.ENTER_LONG
                    rationale = "macd rsi momentum entry setup"
                elif signal_count_before_filters:
                    rationale = "macd rsi momentum prefilter triggered"
            blocked_by_condition_count = int(rows_with_valid_indicator_window and not final_entry_condition_count)
            hold_count = int(action == OfflineStrategySignalAction.HOLD)
            signal = OfflineStrategySignal(
                signal_id=f"{dataset_id}-{candidate.candidate_id}-{instrument_id}-{row.observed_at.isoformat()}",
                candidate_id=candidate.candidate_id,
                instrument_id=instrument_id,
                observed_at=row.observed_at,
                action=action,
                rationale=rationale,
                signal_features={
                    "close": closes[index],
                    "volume_ratio": volume_ratio,
                    "body_ratio": body_ratio,
                    "rsi_level": rsi_level,
                    "macd_line": current_macd,
                    "macd_signal": current_signal,
                    "indicator_columns_available": _compact_columns(available_indicator_columns),
                    "missing_indicator_columns": _compact_columns(missing_indicator_columns),
                    "rows_with_valid_indicator_window": rows_with_valid_indicator_window,
                    "macd_cross_count": macd_cross_count,
                    "rsi_condition_count": rsi_condition_count,
                    "volume_condition_count": volume_condition_count,
                    "candle_condition_count": candle_condition_count,
                    "pullback_condition_count": pullback_condition_count,
                    "rebound_condition_count": rebound_condition_count,
                    "final_entry_condition_count": final_entry_condition_count,
                    "signal_count_before_filters": signal_count_before_filters,
                    "schema_gap_count": int(signal_input_schema_gap),
                    "blocked_by_missing_indicator_count": int(signal_input_schema_gap),
                    "blocked_by_condition_count": blocked_by_condition_count,
                    "hold_count": hold_count,
                    "condition_pass_counts": _compact_counts(
                        {
                            key: value
                            for key, value in {
                                "rows_with_valid_indicator_window": rows_with_valid_indicator_window,
                                "macd_cross_count": macd_cross_count,
                                "rsi_condition_count": rsi_condition_count,
                                "volume_condition_count": volume_condition_count,
                                "candle_condition_count": candle_condition_count,
                                "pullback_condition_count": pullback_condition_count,
                                "rebound_condition_count": rebound_condition_count,
                                "final_entry_condition_count": final_entry_condition_count,
                                "signal_count_before_filters": signal_count_before_filters,
                            }.items()
                            if value
                        }
                    ),
                },
            )
            candidate_signals.append(signal)
            signals.append(signal)
        diagnostics_by_instrument[instrument_id] = _build_symbol_diagnostics(
            symbol=instrument_id,
            rows=rows,
            candidate_signals=candidate_signals,
            required_indicator_columns=required_indicator_columns,
        )
    return OfflineStrategySignalBundle(
        signals=signals,
        diagnostics_by_instrument=diagnostics_by_instrument,
    )


def build_offline_strategy_signals(dataset_id: str, rows_by_instrument: dict[str, list], candidate: OfflineStrategyCandidate) -> list[OfflineStrategySignal]:
    return build_offline_strategy_signal_bundle(dataset_id, rows_by_instrument, candidate).signals


def aggregate_offline_strategy_signal_diagnostics(diagnostics_by_instrument: dict[str, dict[str, object]]) -> dict[str, object]:
    return _aggregate_candidate_diagnostics(diagnostics_by_instrument)
