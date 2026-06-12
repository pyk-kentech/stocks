from datetime import date, datetime

from stock_risk_mcp.candidate_universe import CandidateDecision, CandidateScanResult, CandidateSource, ScanRun, ScanRunStatus
from stock_risk_mcp.repository import RiskRepository
from stock_risk_mcp.scan_run import create_basket_from_scan_run, create_replay_snapshot_from_scan_run
from stock_risk_mcp.setup import SetupDirection, SetupGrade, TradeDecision, TradePlan


def test_scan_converts_to_basket_with_opt_in_save_and_replay_metadata(tmp_path) -> None:
    repository = RiskRepository(tmp_path / "risk.sqlite3")
    repository.save_scan_run(_run())
    repository.save_candidate_scan_results([_result("AAA"), _result("BBB"), _result("CCC")])

    basket, saved = create_basket_from_scan_run(repository, "scan-1", 10_000, 5_000, save_basket=False)
    saved_basket, saved_to_tables = create_basket_from_scan_run(
        repository, "scan-1", 10_000, 5_000, save_basket=True
    )
    replay = create_replay_snapshot_from_scan_run(repository, "scan-1", date(2026, 1, 1))

    assert saved is False
    assert saved_to_tables is True
    assert repository.get_basket_plan(saved_basket.basket_id).basket_id == saved_basket.basket_id
    assert len(basket.candidates) == 3
    snapshots = repository.list_replay_candidate_snapshots(replay.run_id)
    assert snapshots[0].snapshot_json["scan_decision"] == "INCLUDE"
    assert snapshots[0].snapshot_json["scan_score"] == 80


def _run():
    return ScanRun(scan_run_id="scan-1", as_of_date=date(2026,1,1), source=CandidateSource.MANUAL_LIST, universe_size=3, included_count=3, watch_count=0, excluded_count=0, status=ScanRunStatus.COMPLETED, created_at=datetime(2026,1,1))


def _result(ticker):
    plan = TradePlan(ticker=ticker, direction=SetupDirection.LONG, setup_grade=SetupGrade.A, setup_score=85, entry_price=10, stop_price=9, target_price=14, risk_reward_ratio=4, max_loss_amount=25, position_size=25, notional_value=250, decision=TradeDecision.PROPOSE, reasons=[], warnings=[], beginner_summary="fixture")
    return CandidateScanResult(scan_run_id="scan-1", ticker=ticker, as_of_date=date(2026,1,1), decision=CandidateDecision.INCLUDE, score=80, setup_grade="A", setup_score=85, trade_plan_decision="PROPOSE", metadata={"trade_plan": plan.model_dump(mode="json")})
