from datetime import date, datetime

from stock_risk_mcp.normalize_run import NormalizeRun, NormalizeRunStatus, NormalizeSourceResult, NormalizerType
from stock_risk_mcp.repository import RiskRepository


def test_normalize_run_totals_and_repository_round_trip(tmp_path) -> None:
    repository = RiskRepository(tmp_path / "risk.sqlite3")
    run = NormalizeRun(
        as_of_date=date(2026, 6, 13), status=NormalizeRunStatus.PARTIAL,
        source_results=[
            NormalizeSourceResult(
                normalizer_name="generic-price-csv", normalizer_type=NormalizerType.PRICE_HISTORY,
                input_path="raw.csv", output_path="normalized.csv", row_count=3,
                normalized_count=1, skipped_count=1, error_count=1,
            )
        ],
        completed_at=datetime.now(),
    )

    repository.save_normalize_run(run)
    loaded = repository.get_normalize_run(run.normalize_run_id)

    assert loaded.total_row_count == 3
    assert loaded.total_normalized_count == 1
    assert loaded.output_paths == ["normalized.csv"]
    assert repository.list_normalize_runs()[0].normalize_run_id == run.normalize_run_id
