import csv
from datetime import date, timedelta

from stock_risk_mcp.asof_price_history import AsOfPriceHistoryProvider
from stock_risk_mcp.models import PriceBar
from stock_risk_mcp.repository import RiskRepository


def test_asof_provider_separates_history_and_forward_db_bars(tmp_path) -> None:
    repository = RiskRepository(tmp_path / "risk.sqlite3")
    cutoff = date(2026, 1, 5)
    repository.save_price_bars(_bars("SAFE", date(2026, 1, 1), 10))
    provider = AsOfPriceHistoryProvider(repository=repository)

    history = provider.get_history_until("SAFE", cutoff, min_bars=5)
    forward = provider.get_forward_history("SAFE", cutoff, horizon_days=3)

    assert history
    assert all(bar.date <= cutoff for bar in history)
    assert forward
    assert all(cutoff < bar.date <= cutoff + timedelta(days=3) for bar in forward)
    assert provider.get_history_until("SAFE", cutoff, min_bars=6) == []


def test_asof_provider_supports_local_price_file(tmp_path) -> None:
    price_file = tmp_path / "prices.csv"
    bars = _bars("SAFE", date(2026, 1, 1), 6)
    with price_file.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=["ticker", "date", "open", "high", "low", "close", "volume"])
        writer.writeheader()
        for bar in bars:
            writer.writerow(bar.model_dump(mode="json"))

    provider = AsOfPriceHistoryProvider(price_history_file=price_file)

    assert len(provider.get_history_until("SAFE", date(2026, 1, 4), min_bars=4)) == 4
    assert len(provider.get_forward_history("SAFE", date(2026, 1, 4), horizon_days=2)) == 2


def _bars(ticker: str, start: date, count: int) -> list[PriceBar]:
    return [
        PriceBar(
            ticker=ticker,
            date=start + timedelta(days=index),
            open=10 + index,
            high=11 + index,
            low=9 + index,
            close=10 + index,
            volume=1_000_000,
        )
        for index in range(count)
    ]
