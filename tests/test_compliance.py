from __future__ import annotations

import csv
import json

from stock_risk_mcp.adapters.file_company_risk import FileCompanyRiskWithComplianceAdapter
from stock_risk_mcp.adapters.mock_company_risk import MockCompanyRiskAdapter
from stock_risk_mcp.adapters.nasdaq_noncompliant_file import NasdaqNoncompliantFileAdapter
from stock_risk_mcp.cli import main
from stock_risk_mcp.models import SourceType
from stock_risk_mcp.reason_codes import HardBlockCode
from stock_risk_mcp.repository import RiskRepository


def test_company_risk_wrapper_overrides_nasdaq_noncompliant_and_preserves_evidence(tmp_path) -> None:
    csv_path = tmp_path / "nasdaq_noncompliant.csv"
    _write_compliance_csv(csv_path, [{"ticker": "SAFE", "source_url": "https://example.test/list", "raw_reference": "row-1"}])
    adapter = FileCompanyRiskWithComplianceAdapter(
        base_company_risk_adapter=MockCompanyRiskAdapter(),
        compliance_adapter=NasdaqNoncompliantFileAdapter(csv_path),
    )

    company = adapter.get_company_risk("safe")

    assert company.ticker == "SAFE"
    assert company.nasdaq_noncompliant is True
    assert company.nasdaq_noncompliance_evidence is not None
    assert company.nasdaq_noncompliance_evidence.source_name == "nasdaq_noncompliant_file"
    assert company.nasdaq_noncompliance_evidence.source_type == SourceType.FILE


def test_ingest_nasdaq_noncompliant_cli_saves_records_sources_and_run(tmp_path, capsys) -> None:
    db_path = tmp_path / "risk.sqlite3"
    csv_path = tmp_path / "nasdaq_noncompliant.csv"
    _write_compliance_csv(csv_path, [{"ticker": "BAD"}, {"ticker": "XYZ"}])

    main(["ingest-nasdaq-noncompliant", "--file", str(csv_path), "--db", str(db_path)])

    output = json.loads(capsys.readouterr().out)
    repository = RiskRepository(db_path)
    sources = {source.name: source for source in repository.get_data_sources()}
    runs = repository.get_ingestion_runs()
    records = repository.get_compliance_records("bad")

    assert output == {
        "source_name": "nasdaq_noncompliant_file",
        "records_seen": 2,
        "records_saved": 2,
        "status": "SUCCESS",
    }
    assert repository.count_rows("compliance_records") == 2
    assert records[0].ticker == "BAD"
    assert sources["nasdaq_noncompliant_file"].source_type == SourceType.FILE
    assert runs[0].source_name == "nasdaq_noncompliant_file"
    assert runs[0].source_type == SourceType.FILE
    assert runs[0].records_seen == 2
    assert runs[0].records_saved == 2


def test_check_compliance_cli_outputs_status(tmp_path, capsys) -> None:
    csv_path = tmp_path / "nasdaq_noncompliant.csv"
    _write_compliance_csv(
        csv_path,
        [
            {
                "ticker": "BAD",
                "issue": "Bid Price",
                "deficiency": "Minimum bid price below requirement",
                "notice_date": "2026-05-01",
                "source_url": "https://www.nasdaq.com/market-activity/stocks/non-compliant-company-list",
                "raw_reference": "row-1",
            }
        ],
    )

    main(["check-compliance", "--ticker", "bad", "--file", str(csv_path)])

    output = json.loads(capsys.readouterr().out)
    assert output["ticker"] == "BAD"
    assert output["nasdaq_noncompliant"] is True
    assert output["records"][0]["issue"] == "Bid Price"
    assert output["records"][0]["notice_date"] == "2026-05-01"
    assert output["evidence"]["source_name"] == "nasdaq_noncompliant_file"
    assert output["evidence"]["source_type"] == "FILE"
    assert output["evidence"]["raw_reference"] == "row-1"


def test_evaluate_and_save_uses_nasdaq_file_evidence_for_hard_block(tmp_path, capsys) -> None:
    db_path = tmp_path / "risk.sqlite3"
    csv_path = tmp_path / "nasdaq_noncompliant.csv"
    _write_compliance_csv(csv_path, [{"ticker": "SAFE", "source_url": "https://example.test/list", "raw_reference": "row-1"}])

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
            "file compliance fixture",
            "--db",
            str(db_path),
            "--nasdaq-noncompliant-file",
            str(csv_path),
        ]
    )

    output = json.loads(capsys.readouterr().out)
    reason = next(
        item for item in output["result"]["reason_details"] if item["reason_code"] == HardBlockCode.NASDAQ_NONCOMPLIANT.value
    )
    repository_reason = next(
        item
        for item in RiskRepository(db_path).get_evaluation_reasons(output["saved"]["evaluation_id"])
        if item.reason_code == HardBlockCode.NASDAQ_NONCOMPLIANT.value
    )

    assert output["result"]["decision"] == "BLOCK"
    assert reason["evidence"]["source_name"] == "nasdaq_noncompliant_file"
    assert reason["evidence"]["source_type"] == "FILE"
    assert repository_reason.evidence is not None
    assert repository_reason.evidence.source_name == "nasdaq_noncompliant_file"


def _write_compliance_csv(path, rows: list[dict[str, str]]) -> None:
    fieldnames = ["ticker", "company_name", "issue", "deficiency", "notice_date", "source_url", "raw_reference"]
    with path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
