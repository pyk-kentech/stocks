from datetime import date
from pathlib import Path

from stock_risk_mcp.adapters.file_utils import load_records
from stock_risk_mcp.signal_scoring import calculate_signal_score
from stock_risk_mcp.signals import SignalDirection, SignalSeverity, SignalType, TickerSignal, observed_date, parse_observed_at


def load_dilution_signals(path: str | Path, as_of_date: date) -> list[TickerSignal]:
    signals = []
    for record in load_records(path):
        observed_at = parse_observed_at(record["observed_at"])
        if observed_date(observed_at) > as_of_date:
            continue
        event = str(record.get("event_type", "UNKNOWN")).strip().upper()
        direction = SignalDirection.NEUTRAL if event == "OFFERING_CLOSED" else SignalDirection.NEGATIVE
        default = SignalSeverity.MEDIUM if event == "OFFERING_CLOSED" else SignalSeverity.HIGH
        severity = SignalSeverity(str(record.get("severity") or default.value).strip().upper())
        signals.append(TickerSignal(
            ticker=str(record["ticker"]), signal_type=SignalType.DILUTION, as_of_date=as_of_date,
            observed_at=observed_at, direction=direction, severity=severity,
            score_delta=calculate_signal_score(direction, severity, SignalType.DILUTION),
            source_name="dilution_signal_file", title=event.replace("_", " ").title(),
            summary=record.get("details"), raw_event_type=event, metadata=dict(record),
            reasons=[f"Dilution signal: {event}"],
        ))
    return signals
