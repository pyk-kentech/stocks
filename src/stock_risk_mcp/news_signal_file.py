from datetime import date
from pathlib import Path

from stock_risk_mcp.adapters.file_utils import load_records
from stock_risk_mcp.signal_scoring import calculate_signal_score
from stock_risk_mcp.signals import SignalDirection, SignalSeverity, SignalType, TickerSignal, observed_date, parse_observed_at


def load_news_signals(path: str | Path, as_of_date: date) -> list[TickerSignal]:
    signals = []
    for record in load_records(path):
        observed_at = parse_observed_at(record["observed_at"])
        if observed_date(observed_at) > as_of_date:
            continue
        direction, severity, warnings = _classification(record)
        signals.append(TickerSignal(
            ticker=str(record["ticker"]), signal_type=SignalType.NEWS, as_of_date=as_of_date,
            observed_at=observed_at, direction=direction, severity=severity,
            score_delta=calculate_signal_score(direction, severity, SignalType.NEWS),
            source_name="news_signal_file", title=record.get("title"), summary=record.get("summary"),
            raw_event_type=_upper(record.get("event_type")), metadata=dict(record),
            reasons=[f"News signal: {record.get('event_type') or 'UNKNOWN'}"], warnings=warnings,
        ))
    return signals


def _classification(record):
    event = _upper(record.get("event_type")) or "UNKNOWN"
    sentiment = _upper(record.get("sentiment"))
    materiality = _upper(record.get("materiality"))
    negative_events = {"LAWSUIT", "REGULATORY", "INVESTIGATION"}
    positive_events = {"EARNINGS_BEAT", "GUIDANCE_RAISE", "CONTRACT", "FDA_APPROVAL", "PARTNERSHIP"}
    if event in negative_events:
        return SignalDirection.NEGATIVE, SignalSeverity.HIGH, []
    if materiality == "HIGH" and sentiment == "NEGATIVE":
        return SignalDirection.NEGATIVE, SignalSeverity.HIGH, []
    if materiality == "HIGH" and sentiment == "POSITIVE":
        return SignalDirection.POSITIVE, SignalSeverity.HIGH, []
    if event in positive_events:
        return SignalDirection.POSITIVE, SignalSeverity.MEDIUM, []
    return SignalDirection.NEUTRAL, SignalSeverity.LOW, ["Unknown news event classification"]


def _upper(value):
    return str(value).strip().upper() if value not in (None, "") else None
