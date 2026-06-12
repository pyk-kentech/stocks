from datetime import date, datetime

from stock_risk_mcp.repository import RiskRepository
from stock_risk_mcp.signals import SignalDirection, SignalSeverity, SignalType, TickerSignal


def test_repository_round_trips_asof_signals_and_skips_duplicates(tmp_path) -> None:
    repository = RiskRepository(tmp_path / "risk.sqlite3")
    past = _signal("2026-01-01")
    future = _signal("2026-01-03")

    first = repository.save_ticker_signals([past, future])
    second = repository.save_ticker_signals([past])

    assert len(first) == 2
    assert second == []
    assert repository.list_ticker_signals("AAA", date(2026, 1, 2)) == [past]
    assert repository.get_signals_for_ticker_asof("AAA", date(2026, 1, 2)) == [past]


def _signal(observed):
    return TickerSignal(
        ticker="AAA", signal_type=SignalType.NEWS, as_of_date=date(2026, 1, 2),
        observed_at=datetime.fromisoformat(observed), direction=SignalDirection.POSITIVE,
        severity=SignalSeverity.HIGH, score_delta=10, source_name="fixture",
        title="same", raw_event_type="CONTRACT",
    )
