from datetime import datetime

from stock_risk_mcp.realtime_market_data import (
    MarketRegion, RealtimeMonitorRun, RealtimeMonitorRunStatus, WatchlistEntry, WatchlistStatus,
)
from stock_risk_mcp.repository import RiskRepository


def test_realtime_repository_round_trips_run_and_upserts_watchlist(tmp_path) -> None:
    repository = RiskRepository(tmp_path / "risk.sqlite3")
    now = datetime(2026, 6, 13, 10)
    run = RealtimeMonitorRun(
        as_of=now, status=RealtimeMonitorRunStatus.COMPLETED, provider_name="mock",
        universe_count=1, processed_event_count=16, candidate_count=1, hot_watchlist_count=1,
    )
    entry = WatchlistEntry(
        symbol="AAPL", region=MarketRegion.US, status=WatchlistStatus.HOT,
        first_seen_at=now, last_seen_at=now, promotion_reason="return", score=10, metrics_json="{}",
    )

    repository.save_realtime_monitor_run(run)
    repository.upsert_watchlist_entry(entry)
    repository.upsert_watchlist_entry(entry.model_copy(update={"score": 20}))

    assert repository.get_realtime_monitor_run(run.realtime_monitor_run_id) == run
    assert repository.list_realtime_monitor_runs()[0] == run
    assert repository.get_watchlist_entry("AAPL", MarketRegion.US).score == 20
    assert len(repository.list_watchlist_entries(WatchlistStatus.HOT)) == 1
