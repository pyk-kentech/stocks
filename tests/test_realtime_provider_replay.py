from datetime import datetime

from stock_risk_mcp.realtime_market_data import MarketRegion
from stock_risk_mcp.realtime_provider_replay import LocalReplayMarketDataProvider


def test_local_replay_sorts_filters_and_isolates_invalid_rows(tmp_path) -> None:
    path = tmp_path / "replay.csv"
    path.write_text(
        "symbol,region,event_time,event_type,close,volume,source_name\n"
        "AAPL,US,2026-06-13T09:32:00,BAR_1M,102,100,replay\n"
        "BAD,US,not-a-date,BAR_1M,10,10,replay\n"
        "AAPL,US,2026-06-13T09:31:00,BAR_1M,101,100,replay\n"
        "005930,KR,2026-06-13T09:31:00,BAR_1M,100,100,replay\n",
        encoding="utf-8",
    )
    provider = LocalReplayMarketDataProvider(path, MarketRegion.US)

    events = list(provider.iter_events(["AAPL"], None, None))

    assert [item.close for item in events] == [101, 102]
    assert provider.warnings
