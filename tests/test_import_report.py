from stock_risk_mcp.import_report import import_run_report
from stock_risk_mcp.import_run import ImportRun, ImportRunStatus, ImportSourceResult, ImportSourceType


def test_import_report_includes_aggregate_and_source_counts() -> None:
    run = ImportRun(
        import_run_id="import_report",
        status=ImportRunStatus.PARTIAL,
        source_results=[
            ImportSourceResult(
                source_type=ImportSourceType.NEWS_SIGNAL,
                file_path="news.csv",
                row_count=3,
                saved_count=1,
                skipped_duplicate_count=1,
                error_count=1,
            )
        ],
    )

    report = import_run_report(run)

    assert report["status"] == "PARTIAL"
    assert report["total_row_count"] == 3
    assert report["source_results"][0]["error_count"] == 1
