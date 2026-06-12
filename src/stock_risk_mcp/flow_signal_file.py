from datetime import date
from pathlib import Path

from stock_risk_mcp.adapters.file_utils import load_records
from stock_risk_mcp.signal_scoring import calculate_signal_score
from stock_risk_mcp.signals import SignalDirection, SignalSeverity, SignalType, TickerSignal, observed_date, parse_observed_at


def load_flow_signals(path: str | Path, as_of_date: date) -> list[TickerSignal]:
    signals = []
    for record in load_records(path):
        observed_at = parse_observed_at(record["observed_at"])
        if observed_date(observed_at) > as_of_date:
            continue
        foreign = float(record.get("foreign_net_buy") or 0)
        institution = float(record.get("institution_net_buy") or 0)
        if foreign > 0 and institution > 0:
            direction, reason = SignalDirection.POSITIVE, "Foreign and institution net buying"
        elif foreign < 0 and institution < 0:
            direction, reason = SignalDirection.NEGATIVE, "Foreign and institution net selling"
        else:
            direction, reason = SignalDirection.NEUTRAL, "Mixed foreign and institution flow"
        severity = SignalSeverity.MEDIUM
        signals.append(TickerSignal(
            ticker=str(record["ticker"]), signal_type=SignalType.FOREIGN_INSTITUTION_FLOW,
            as_of_date=as_of_date, observed_at=observed_at, direction=direction, severity=severity,
            score_delta=calculate_signal_score(direction, severity, SignalType.FOREIGN_INSTITUTION_FLOW),
            source_name="flow_signal_file", title="Foreign and institution flow",
            raw_event_type="FLOW", metadata=dict(record), reasons=[reason],
        ))
    return signals
