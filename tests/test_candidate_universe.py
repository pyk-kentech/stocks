import csv
from datetime import date

from stock_risk_mcp.candidate_universe import load_db_universe, load_file_universe, load_manual_universe
from stock_risk_mcp.models import PriceBar
from stock_risk_mcp.repository import RiskRepository


def test_loads_db_file_and_manual_universes_without_future_tickers(tmp_path) -> None:
    cutoff = date(2026, 1, 2)
    repository = RiskRepository(tmp_path / "risk.sqlite3")
    repository.save_price_bars([
        PriceBar(ticker="AAA", date=date(2026, 1, 1), close=10),
        PriceBar(ticker="FUTURE", date=date(2026, 1, 3), close=10),
    ])
    price_file = tmp_path / "prices.csv"
    with price_file.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=["ticker", "date", "close"])
        writer.writeheader()
        writer.writerows([{"ticker": "BBB", "date": "2026-01-01", "close": 10}, {"ticker": "FUTURE", "date": "2026-01-03", "close": 10}])

    assert load_db_universe(repository, cutoff) == ["AAA"]
    assert load_file_universe(price_file, cutoff) == ["BBB"]
    assert load_manual_universe([" aaa ", "AAA", "bbb"]) == ["AAA", "BBB"]
