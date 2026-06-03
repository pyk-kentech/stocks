from __future__ import annotations

import csv

import pytest

from stock_risk_mcp.adapters.nasdaq_noncompliant_file import NasdaqNoncompliantFileAdapter
from stock_risk_mcp.models import SourceType


def test_load_records_from_csv_with_normalized_tickers_and_evidence(tmp_path) -> None:
    csv_path = tmp_path / "nasdaq_noncompliant.csv"
    _write_compliance_csv(
        csv_path,
        [
            {
                "ticker": " bad ",
                "company_name": "Example Bad Corp",
                "issue": "Bid Price",
                "deficiency": "Minimum bid price below requirement",
                "notice_date": "2026-05-01",
                "source_url": "https://www.nasdaq.com/market-activity/stocks/non-compliant-company-list",
                "raw_reference": "row-1",
            },
            {
                "ticker": "BAD",
                "company_name": "Example Bad Corp",
                "issue": "Market Value",
                "deficiency": "Market value below requirement",
                "notice_date": "not-a-date",
                "source_url": "https://example.test/second",
                "raw_reference": "row-2",
            },
        ],
    )

    status = NasdaqNoncompliantFileAdapter(csv_path).is_noncompliant("bad")

    assert status.ticker == "BAD"
    assert status.nasdaq_noncompliant is True
    assert len(status.records) == 2
    assert status.records[0].ticker == "BAD"
    assert status.records[0].notice_date.isoformat() == "2026-05-01"
    assert status.records[1].notice_date is None
    assert status.evidence is not None
    assert status.evidence.source_name == "nasdaq_noncompliant_file"
    assert status.evidence.source_type == SourceType.FILE
    assert status.evidence.source_url == "https://www.nasdaq.com/market-activity/stocks/non-compliant-company-list"
    assert status.evidence.raw_reference == "row-1"
    assert status.evidence.observed_at is not None


def test_is_noncompliant_returns_false_for_missing_ticker(tmp_path) -> None:
    csv_path = tmp_path / "nasdaq_noncompliant.csv"
    _write_compliance_csv(csv_path, [{"ticker": "BAD"}])

    status = NasdaqNoncompliantFileAdapter(csv_path).is_noncompliant("SAFE")

    assert status.ticker == "SAFE"
    assert status.nasdaq_noncompliant is False
    assert status.records == []
    assert status.evidence is None


def test_missing_ticker_column_raises_value_error(tmp_path) -> None:
    csv_path = tmp_path / "nasdaq_noncompliant.csv"
    with csv_path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=["company_name"])
        writer.writeheader()
        writer.writerow({"company_name": "No Ticker Corp"})

    with pytest.raises(ValueError, match="ticker"):
        NasdaqNoncompliantFileAdapter(csv_path).load_records()


def test_missing_file_raises_file_not_found_error(tmp_path) -> None:
    csv_path = tmp_path / "missing.csv"

    with pytest.raises(FileNotFoundError, match="missing.csv"):
        NasdaqNoncompliantFileAdapter(csv_path).load_records()


def _write_compliance_csv(path, rows: list[dict[str, str]]) -> None:
    fieldnames = ["ticker", "company_name", "issue", "deficiency", "notice_date", "source_url", "raw_reference"]
    with path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
