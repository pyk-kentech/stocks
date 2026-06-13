import json
from datetime import datetime

from stock_risk_mcp.cli import main
from stock_risk_mcp.realtime_market_data import MarketRegion, RealtimeMonitorRunStatus
from stock_risk_mcp.realtime_monitor import run_realtime_monitor
from stock_risk_mcp.realtime_provider_mock import MockRealtimeMarketDataProvider
from stock_risk_mcp.repository import RiskRepository


def test_realtime_monitor_persists_run_watchlist_and_summary(tmp_path) -> None:
    repository = RiskRepository(tmp_path / "risk.sqlite3")

    result = run_realtime_monitor(
        repository, MockRealtimeMarketDataProvider(MarketRegion.US), ["AAPL", "NVDA"],
        MarketRegion.US, output_dir=tmp_path / "out", max_events=1000, max_hot_watchlist_size=1,
        as_of=datetime(2026, 6, 13, 10),
    )

    assert result.run.status == RealtimeMonitorRunStatus.COMPLETED
    assert result.run.hot_watchlist_count == 1
    assert repository.list_watchlist_entries()
    assert (tmp_path / "out" / "realtime_monitor_summary.json").exists()


def test_realtime_cli_mock_lists_and_shows(tmp_path, capsys) -> None:
    db = tmp_path / "risk.sqlite3"
    main([
        "run-realtime-monitor", "--db", str(db), "--provider", "mock", "--region", "US",
        "--symbols", "AAPL,NVDA", "--output-dir", str(tmp_path / "out"),
        "--max-events", "1000", "--max-hot-watchlist-size", "1",
    ])
    result = json.loads(capsys.readouterr().out)
    main(["watchlist-list", "--db", str(db), "--status", "HOT"])
    watchlist = json.loads(capsys.readouterr().out)
    main(["realtime-runs", "--db", str(db)])
    runs = json.loads(capsys.readouterr().out)
    main(["realtime-show", "--db", str(db), "--realtime-monitor-run-id", result["run"]["realtime_monitor_run_id"]])
    shown = json.loads(capsys.readouterr().out)

    assert result["run"]["status"] == "COMPLETED"
    assert watchlist["watchlist_entries"]
    assert runs["realtime_monitor_runs"]
    assert shown["realtime_monitor_run_id"] == result["run"]["realtime_monitor_run_id"]
