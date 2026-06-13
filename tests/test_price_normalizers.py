import csv
from datetime import date

from stock_risk_mcp.price_normalizers import GenericPriceCSVNormalizer


def test_price_normalizer_maps_columns_skips_future_and_handles_bad_rows(tmp_path) -> None:
    raw = tmp_path / "raw.csv"
    raw.write_text(
        "Symbol,Day,Open,High,Low,Close,Volume\n"
        "aaa,2026-06-12,,,,10,100\n"
        "BBB,2026-06-14,1,2,1,2,100\n"
        "CCC,2026-06-12,1,2,1,,100\n"
        "DDD,2026-06-12,1,2,1,2,\n",
        encoding="utf-8",
    )

    result = GenericPriceCSVNormalizer().normalize(
        raw, tmp_path / "out", date(2026, 6, 13), output_name="prices.csv",
        columns={"ticker": "Symbol", "date": "Day", "open": "Open", "high": "High",
                 "low": "Low", "close": "Close", "volume": "Volume"},
    )

    rows = list(csv.DictReader(open(result.output_path, encoding="utf-8")))
    assert rows[0] == {
        "ticker": "AAA", "date": "2026-06-12", "open": "10.0", "high": "10.0",
        "low": "10.0", "close": "10.0", "volume": "100.0",
    }
    assert result.row_count == 4
    assert result.normalized_count == 1
    assert result.skipped_count == 1
    assert result.error_count == 2
    assert result.warnings
