from collections import defaultdict
from datetime import date
from pathlib import Path

from stock_risk_mcp.adapters.file_utils import load_records
from stock_risk_mcp.signal_scoring import calculate_signal_score
from stock_risk_mcp.signals import SignalDirection, SignalSeverity, SignalType, TickerSignal, observed_date, parse_observed_at


def load_toss_signals(path: str | Path, as_of_date: date) -> list[TickerSignal]:
    groups = defaultdict(list)
    for record in load_records(path):
        observed_at = parse_observed_at(record["observed_at"])
        if observed_date(observed_at) <= as_of_date:
            groups[(str(record["ticker"]).strip().upper(), observed_at)].append(record)
    signals = []
    for (ticker, observed_at), records in groups.items():
        direction, severity, reason = _classification(records)
        signals.append(TickerSignal(
            ticker=ticker, signal_type=SignalType.TOSS_PORTFOLIO, as_of_date=as_of_date,
            observed_at=observed_at, direction=direction, severity=severity,
            score_delta=calculate_signal_score(direction, severity, SignalType.TOSS_PORTFOLIO),
            source_name="toss_signal_file", title="Toss top investor portfolio aggregate",
            raw_event_type="TOSS_AGGREGATE", metadata={"records": records},
            reasons=[reason],
        ))
    return signals


def _classification(records):
    changes = [str(item.get("change_type", "")).strip().upper() for item in records]
    buy_count = sum(item in {"BUY", "ADD", "INCREASE"} for item in changes)
    exit_count = sum(item in {"EXIT", "SELL", "REDUCE"} for item in changes)
    holding_count = sum(float(item.get("holding_weight") or 0) > 0 for item in records)
    if exit_count >= 2:
        return SignalDirection.NEGATIVE, SignalSeverity.HIGH, "Multiple top investors reduced or exited"
    if buy_count >= 2:
        return SignalDirection.POSITIVE, SignalSeverity.HIGH, "Multiple top investors added positions"
    if holding_count >= 2:
        return SignalDirection.POSITIVE, SignalSeverity.MEDIUM, "Multiple top investors hold positions"
    return SignalDirection.NEUTRAL, SignalSeverity.LOW, "Single-investor Toss portfolio reference"
