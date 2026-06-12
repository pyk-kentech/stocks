from datetime import date, datetime

from stock_risk_mcp.candidate_universe import CandidateDecision, CandidateScanResult, CandidateSource, ScanRun, ScanRunStatus
from stock_risk_mcp.repository import RiskRepository


def test_repository_round_trips_scan_run_and_results(tmp_path) -> None:
    repository = RiskRepository(tmp_path / "risk.sqlite3")
    run = ScanRun(
        scan_run_id="scan-1", as_of_date=date(2026, 6, 13), source=CandidateSource.MANUAL_LIST,
        universe_size=1, included_count=1, watch_count=0, excluded_count=0, status=ScanRunStatus.COMPLETED,
        notes=["fixture"], created_at=datetime(2026, 6, 13),
    )
    result = CandidateScanResult(
        scan_run_id="scan-1", ticker="SAFE", as_of_date=date(2026, 6, 13),
        decision=CandidateDecision.INCLUDE, score=80, setup_grade="A", setup_score=85,
        trade_plan_decision="PROPOSE", price=10, reasons=["fixture"], warnings=[], metadata={"x": 1},
    )

    repository.save_scan_run(run)
    repository.save_candidate_scan_results([result])

    assert repository.get_scan_run("scan-1") == run
    assert repository.list_scan_runs() == [run]
    assert repository.list_candidate_scan_results("scan-1") == [result]
    assert repository.list_candidate_scan_results("scan-1", "INCLUDE") == [result]
