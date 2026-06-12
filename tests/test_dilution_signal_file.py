import json
from datetime import date

from stock_risk_mcp.dilution_signal_file import load_dilution_signals
from stock_risk_mcp.signals import SignalDirection, SignalSeverity


def test_dilution_file_marks_critical_negative_and_ignores_future(tmp_path) -> None:
    path = tmp_path / "dilution.json"
    path.write_text(json.dumps([
        {"ticker": "AAA", "observed_at": "2026-01-01", "event_type": "ATM_OFFERING", "severity": "CRITICAL", "details": "fixture"},
        {"ticker": "AAA", "observed_at": "2026-01-03", "event_type": "REVERSE_SPLIT", "severity": "HIGH"},
    ]), encoding="utf-8")

    signals = load_dilution_signals(path, date(2026, 1, 2))

    assert len(signals) == 1
    assert signals[0].direction == SignalDirection.NEGATIVE
    assert signals[0].severity == SignalSeverity.CRITICAL
    assert signals[0].score_delta == -100
