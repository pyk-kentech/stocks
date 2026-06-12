from datetime import date, datetime

from stock_risk_mcp.signals import SignalDirection, SignalSeverity, SignalType, TickerSignal, signal_dedupe_key


def test_ticker_signal_normalizes_ticker_and_has_stable_dedupe_key() -> None:
    signal = TickerSignal(
        ticker=" aaa ", signal_type=SignalType.NEWS, as_of_date=date(2026, 1, 2),
        observed_at=datetime(2026, 1, 1, 9), direction=SignalDirection.POSITIVE,
        severity=SignalSeverity.HIGH, score_delta=10, source_name="news_signal_file",
        title="Contract", raw_event_type="CONTRACT",
    )

    assert signal.ticker == "AAA"
    assert signal_dedupe_key(signal) == (
        "AAA", "NEWS", "2026-01-01T09:00:00", "news_signal_file", "CONTRACT", "Contract",
    )
