from __future__ import annotations

import csv
from datetime import datetime
from pathlib import Path
from typing import Any

from stock_risk_mcp.compliance import (
    NASDAQ_NONCOMPLIANT_SOURCE_NAME,
    ComplianceRecord,
    ComplianceStatus,
)
from stock_risk_mcp.models import Evidence, SourceType


class NasdaqNoncompliantFileAdapter:
    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self._records: list[ComplianceRecord] | None = None

    def load_records(self) -> list[ComplianceRecord]:
        if self._records is not None:
            return self._records
        if not self.path.exists():
            raise FileNotFoundError(f"Nasdaq noncompliant data file not found: {self.path}")

        observed_at = datetime.now()
        with self.path.open("r", encoding="utf-8-sig", newline="") as file:
            reader = csv.DictReader(file)
            if reader.fieldnames is None or "ticker" not in {name.strip() for name in reader.fieldnames}:
                raise ValueError("Nasdaq noncompliant CSV must include a ticker column")
            self._records = [_record_from_row(row, observed_at) for row in reader if str(row.get("ticker", "")).strip()]
        return self._records

    def is_noncompliant(self, ticker: str) -> ComplianceStatus:
        symbol = ticker.strip().upper()
        records = [record for record in self.load_records() if record.ticker == symbol]
        return ComplianceStatus(
            ticker=symbol,
            nasdaq_noncompliant=bool(records),
            records=records,
            evidence=_evidence_from_record(records[0]) if records else None,
        )


def _record_from_row(row: dict[str, Any], observed_at: datetime) -> ComplianceRecord:
    return ComplianceRecord(
        ticker=_clean(row.get("ticker")) or "",
        company_name=_clean(row.get("company_name")),
        issue=_clean(row.get("issue")),
        deficiency=_clean(row.get("deficiency")),
        notice_date=_parse_date(_clean(row.get("notice_date"))),
        source_url=_clean(row.get("source_url")),
        raw_reference=_clean(row.get("raw_reference")),
        observed_at=observed_at,
    )


def _evidence_from_record(record: ComplianceRecord) -> Evidence:
    return Evidence(
        source_name=record.source_name,
        source_type=record.source_type,
        source_url=record.source_url,
        observed_at=record.observed_at,
        raw_reference=record.raw_reference,
        confidence=1.0,
    )


def _clean(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _parse_date(value: str | None):
    if value is None:
        return None
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError:
        return None
