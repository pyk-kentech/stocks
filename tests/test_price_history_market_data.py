from __future__ import annotations

import csv
import json
import math
from datetime import date, timedelta

import pytest

from stock_risk_mcp.adapters.price_history_market_data import PriceHistoryMarketDataAdapter
from stock_risk_mcp.cli import main
from stock_risk_mcp.models import PriceBar, SourceType
from stock_risk_mcp.price_history import (
    calculate_avg_dollar_volume,
    calculate_daily_return_volatility,
    calculate_return_pct_from_bars,
    latest_bar,
    sort_price_bars,
)
from stock_risk_mcp.reason_codes import HardBlockCode
from stock_risk_mcp.repository import RiskRepository


def test_price_history_helpers_calculate_latest_returns_volume_and_volatility() -> None:
    bars = _bars("CALC", closes=[10 + index for index in range(21)], volumes=[1000] * 21)

    sorted_bars = sort_price_bars(list(reversed(bars)))

    assert latest_bar(sorted_bars).close == 30
    assert calculate_return_pct_from_bars(sorted_bars, 5) == pytest.approx(((30 / 25) - 1) * 100)
    assert calculate_return_pct_from_bars(sorted_bars, 20) == pytest.approx(((30 / 10) - 1) * 100)
    assert calculate_avg_dollar_volume(sorted_bars, 20) == pytest.approx(sum((11 + index) * 1000 for index in range(20)) / 20)

    daily_returns = [((bar.close / previous.close) - 1) * 100 for previous, bar in zip(sorted_bars[-21:-1], sorted_bars[-20:])]
    expected_volatility = math.sqrt(sum((value - sum(daily_returns) / 20) ** 2 for value in daily_returns) / 20)
    assert calculate_daily_return_volatility(sorted_bars, 20) == pytest.approx(expected_volatility)


def test_price_history_helpers_return_none_when_data_is_insufficient() -> None:
    bars = _bars("SHORT", closes=[10, 11, 12], volumes=[1000, 1000, 1000])

    assert calculate_return_pct_from_bars(bars, 5) is None
    assert calculate_avg_dollar_volume(bars, 20) is None
    assert calculate_daily_return_volatility(bars, 20) is None


def test_file_adapter_calculates_market_snapshot_from_csv(tmp_path) -> None:
    price_file = tmp_path / "prices.csv"
    _write_price_csv(price_file, _bars("file", closes=[10 + index for index in range(21)], volumes=[1000] * 21))

    snapshot = PriceHistoryMarketDataAdapter(price_history_file=price_file, source_name="price_history_file").get_market_snapshot(
        "FILE"
    )

    assert snapshot.ticker == "FILE"
    assert snapshot.price == 30
    assert snapshot.market_cap_usd is None
    assert snapshot.return_5d_pct == pytest.approx(((30 / 25) - 1) * 100)
    assert snapshot.return_20d_pct == pytest.approx(((30 / 10) - 1) * 100)
    assert snapshot.avg_dollar_volume_20d == pytest.approx(sum((11 + index) * 1000 for index in range(20)) / 20)
    assert snapshot.volatility_20d_pct is not None
    assert snapshot.market_data_evidence is not None
    assert snapshot.market_data_evidence.source_name == "price_history_file"
    assert snapshot.market_data_evidence.source_type == SourceType.FILE


def test_file_adapter_raises_value_error_when_ticker_has_no_prices(tmp_path) -> None:
    price_file = tmp_path / "prices.csv"
    _write_price_csv(price_file, _bars("OTHER", closes=[10, 11], volumes=[1000, 1000]))

    with pytest.raises(ValueError, match="MISSING"):
        PriceHistoryMarketDataAdapter(price_history_file=price_file).get_market_snapshot("MISSING")


def test_db_adapter_uses_repository_price_history(tmp_path) -> None:
    repository = RiskRepository(tmp_path / "risk.sqlite3")
    repository.save_price_bars(_bars("DBPX", closes=[10 + index for index in range(21)], volumes=[1000] * 21))

    snapshot = PriceHistoryMarketDataAdapter(repository=repository).get_market_snapshot("dbpx")

    assert snapshot.ticker == "DBPX"
    assert snapshot.price == 30
    assert snapshot.market_data_evidence is not None
    assert snapshot.market_data_evidence.source_name == "price_history_db"
    assert snapshot.market_data_evidence.source_type == SourceType.SYSTEM


def test_evaluate_and_save_price_history_file_uses_file_market_snapshot_and_evidence(tmp_path, capsys) -> None:
    db_path = tmp_path / "risk.sqlite3"
    price_file = tmp_path / "prices.csv"
    _write_price_csv(price_file, _bars("PUMP", closes=[10] * 16 + [20, 21, 22, 23, 24], volumes=[1000] * 21))

    main(
        [
            "evaluate-and-save",
            "--ticker",
            "PUMP",
            "--side",
            "BUY",
            "--confidence",
            "0.7",
            "--reason",
            "file prices",
            "--db",
            str(db_path),
            "--price-history-file",
            str(price_file),
        ]
    )

    output = json.loads(capsys.readouterr().out)
    reason = next(
        item for item in output["result"]["reason_details"] if item["reason_code"] == HardBlockCode.RETURN_5D_TOO_HIGH.value
    )
    saved_reason = next(
        item
        for item in RiskRepository(db_path).get_evaluation_reasons(output["saved"]["evaluation_id"])
        if item.reason_code == HardBlockCode.RETURN_5D_TOO_HIGH.value
    )

    assert output["result"]["decision"] == "BLOCK"
    assert reason["evidence"]["source_name"] == "price_history_file"
    assert saved_reason.evidence is not None
    assert saved_reason.evidence.source_name == "price_history_file"


def test_evaluate_and_save_can_use_db_price_history(tmp_path, capsys) -> None:
    db_path = tmp_path / "risk.sqlite3"
    repository = RiskRepository(db_path)
    repository.save_price_bars(_bars("SAFE", closes=[10 + index for index in range(21)], volumes=[1000] * 21))

    main(
        [
            "evaluate-and-save",
            "--ticker",
            "SAFE",
            "--side",
            "BUY",
            "--confidence",
            "0.7",
            "--reason",
            "db prices",
            "--db",
            str(db_path),
            "--use-db-price-history",
        ]
    )

    output = json.loads(capsys.readouterr().out)
    reason = next(
        item for item in output["result"]["reason_details"] if item["reason_code"] == HardBlockCode.DOLLAR_VOLUME_TOO_LOW.value
    )

    assert output["result"]["reason_details"]
    assert reason["evidence"]["source_name"] == "price_history_db"


def _bars(ticker: str, closes: list[float], volumes: list[float]) -> list[PriceBar]:
    start = date(2026, 1, 1)
    return [
        PriceBar(ticker=ticker, date=start + timedelta(days=index), close=close, volume=volumes[index])
        for index, close in enumerate(closes)
    ]


def _write_price_csv(path, bars: list[PriceBar]) -> None:
    with path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=["ticker", "date", "open", "high", "low", "close", "volume"])
        writer.writeheader()
        for bar in bars:
            writer.writerow(
                {
                    "ticker": bar.ticker,
                    "date": bar.date.isoformat(),
                    "open": "",
                    "high": "",
                    "low": "",
                    "close": bar.close,
                    "volume": bar.volume,
                }
            )
