from datetime import date

from stock_risk_mcp.import_run import ImportRun, ImportRunStatus, ImportSourceResult, ImportSourceType
from stock_risk_mcp.repository import RiskRepository


def test_import_run_repository_round_trip(tmp_path) -> None:
    repository = RiskRepository(tmp_path / "risk.sqlite3")
    run = ImportRun(
        import_run_id="import_test",
        as_of_date=date(2026, 6, 13),
        status=ImportRunStatus.COMPLETED,
        source_results=[
            ImportSourceResult(
                source_type=ImportSourceType.PRICE_HISTORY,
                file_path="prices.csv",
                row_count=2,
                saved_count=1,
                skipped_duplicate_count=1,
            )
        ],
        notes=["duplicate price rows were skipped without updating existing values"],
    )

    repository.save_import_run(run)

    loaded = repository.get_import_run("import_test")
    assert loaded == run
    assert repository.list_import_runs() == [run]
    assert repository.count_rows("import_runs") == 1
    assert repository.count_rows("import_source_results") == 1
