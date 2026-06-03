from __future__ import annotations

from stock_risk_mcp.models import DataSource, SourceType
from stock_risk_mcp.provenance import MOCK_DATA_SOURCES, evidence_for_reason_code
from stock_risk_mcp.repository import RiskRepository


def test_mock_provenance_sources_are_defined() -> None:
    names = {source.name for source in MOCK_DATA_SOURCES}

    assert "mock_market_data" in names
    assert "mock_company_risk" in names
    assert "mock_portfolio" in names
    assert "mock_toss_signal" in names
    assert evidence_for_reason_code("DILUTION_RISK_HIGH").source_name == "mock_company_risk"


def test_data_sources_upsert(tmp_path) -> None:
    repository = RiskRepository(tmp_path / "risk.sqlite3")

    source_id = repository.upsert_data_source(
        DataSource(
            name="mock_company_risk",
            source_type=SourceType.MOCK,
            description="first",
        )
    )
    updated_id = repository.upsert_data_source(
        DataSource(
            name="mock_company_risk",
            source_type=SourceType.MOCK,
            description="updated",
            enabled=False,
        )
    )

    sources = repository.get_data_sources()
    assert source_id == updated_id
    assert len(sources) == 1
    assert sources[0].description == "updated"
    assert sources[0].enabled is False


def test_ingestion_runs_start_and_finish(tmp_path) -> None:
    repository = RiskRepository(tmp_path / "risk.sqlite3")

    run_id = repository.start_ingestion_run("fixture_prices", "FILE", {"path": "prices.csv"})
    repository.finish_ingestion_run(run_id, "SUCCESS", records_seen=3, records_saved=2)

    runs = repository.get_ingestion_runs()
    assert len(runs) == 1
    assert runs[0].source_name == "fixture_prices"
    assert runs[0].source_type == SourceType.FILE
    assert runs[0].status == "SUCCESS"
    assert runs[0].records_seen == 3
    assert runs[0].records_saved == 2
    assert runs[0].metadata_json == {"path": "prices.csv"}
