from __future__ import annotations

import csv
import json
from datetime import date, timedelta

from stock_risk_mcp.cli import main
from stock_risk_mcp.indicators import IndicatorSet, IndicatorSignal, IndicatorValue
from stock_risk_mcp.models import Evidence, PriceBar, Severity, SourceType
from stock_risk_mcp.repository import RiskRepository


def test_indicator_models_normalize_ticker_and_code() -> None:
    value = IndicatorValue(
        ticker=" safe ",
        indicator_code="return_5d_pct",
        category="PRICE_TREND",
        value=12.3,
        unit="PCT",
        signal=IndicatorSignal.NEUTRAL,
        severity=Severity.LOW,
        interpretation="단기 과열 수준은 아닙니다.",
        beginner_explanation="최근 5일 가격 변화가 과도하지 않습니다.",
    )

    indicator_set = IndicatorSet(ticker=" safe ", indicators=[value])

    assert value.ticker == "SAFE"
    assert value.indicator_code == "RETURN_5D_PCT"
    assert indicator_set.ticker == "SAFE"


def test_repository_saves_and_gets_latest_indicator_values(tmp_path) -> None:
    repository = RiskRepository(tmp_path / "risk.sqlite3")
    first = _indicator("RETURN_5D_PCT", 10)
    latest = _indicator("RETURN_5D_PCT", 20)

    repository.save_indicator_values([first])
    repository.save_indicator_values([latest])

    assert repository.count_rows("indicator_values") == 2
    assert [value.value for value in repository.get_indicator_values("safe", latest_only=False)] == [10.0, 20.0]
    assert [value.value for value in repository.get_indicator_values("safe")] == [20.0]


def test_analyze_indicators_cli_uses_file_and_db_price_history(tmp_path, capsys) -> None:
    price_file = tmp_path / "prices.csv"
    db_path = tmp_path / "risk.sqlite3"
    bars = _bars(121)
    _write_price_csv(price_file, bars)

    main(["analyze-indicators", "--ticker", "SAFE", "--price-history-file", str(price_file)])
    file_output = json.loads(capsys.readouterr().out)

    repository = RiskRepository(db_path)
    repository.save_price_bars(bars)
    main(["analyze-indicators", "--ticker", "SAFE", "--db", str(db_path), "--use-db-price-history"])
    db_output = json.loads(capsys.readouterr().out)

    assert file_output["ticker"] == "SAFE"
    assert len(file_output["indicators"]) == 17
    assert file_output["indicators"][0]["evidence"]["source_name"] == "price_history_file"
    assert "score" in file_output
    assert db_output["indicators"][0]["evidence"]["source_name"] == "price_history_db"


def test_analyze_indicators_and_save_cli_persists_values(tmp_path, capsys) -> None:
    price_file = tmp_path / "prices.csv"
    db_path = tmp_path / "risk.sqlite3"
    _write_price_csv(price_file, _bars(121))

    main(
        [
            "analyze-indicators-and-save",
            "--ticker",
            "SAFE",
            "--price-history-file",
            str(price_file),
            "--db",
            str(db_path),
        ]
    )

    output = json.loads(capsys.readouterr().out)
    repository = RiskRepository(db_path)

    assert output["saved"]["indicator_values"] == 17
    assert repository.count_rows("indicator_values") == 17
    assert len(repository.get_indicator_values("SAFE")) == 17


def _indicator(code: str, value: float) -> IndicatorValue:
    return IndicatorValue(
        ticker="SAFE",
        indicator_code=code,
        category="PRICE_TREND",
        value=value,
        unit="PCT",
        signal=IndicatorSignal.NEUTRAL,
        severity=Severity.LOW,
        interpretation="neutral",
        beginner_explanation="neutral",
        evidence=Evidence(source_name="price_history_file", source_type=SourceType.FILE),
    )


def _bars(count: int) -> list[PriceBar]:
    start = date(2026, 1, 1)
    return [
        PriceBar(
            ticker="SAFE",
            date=start + timedelta(days=index),
            high=101 + index,
            low=99 + index,
            close=100 + index,
            volume=1000,
        )
        for index in range(count)
    ]


def _write_price_csv(path, bars: list[PriceBar]) -> None:
    with path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=["ticker", "date", "open", "high", "low", "close", "volume"])
        writer.writeheader()
        for bar in bars:
            writer.writerow(bar.model_dump(mode="json"))
