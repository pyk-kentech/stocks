from datetime import date, timedelta

from stock_risk_mcp.asof_price_history import AsOfPriceHistoryProvider
from stock_risk_mcp.candidate_universe import CandidateDecision, CandidateScanPolicy, CandidateSource
from stock_risk_mcp.models import PriceBar
from stock_risk_mcp.repository import RiskRepository
from stock_risk_mcp.scan_pipeline import run_candidate_scan


def test_pipeline_scans_sorts_limits_and_optionally_saves(tmp_path) -> None:
    repository = RiskRepository(tmp_path / "risk.sqlite3")
    for ticker in ("AAA", "BBB"):
        repository.save_price_bars(_bars(ticker))
    output = run_candidate_scan(
        repository, AsOfPriceHistoryProvider(repository=repository), ["AAA", "BBB"], date(2026, 1, 5),
        CandidateSource.MANUAL_LIST, CandidateScanPolicy(max_candidates=1), save=True,
    )

    assert output.run.universe_size == 2
    assert sum(item.decision != CandidateDecision.EXCLUDE for item in output.results) <= 1
    assert repository.count_rows("scan_runs") == 1
    assert repository.count_rows("candidate_scan_results") == 2


def _bars(ticker):
    return [PriceBar(ticker=ticker, date=date(2025, 9, 1)+timedelta(days=i), open=10+i*.1, high=11+i*.1, low=9.5+i*.1, close=10.5+i*.1, volume=5_000_000+i*100_000) for i in range(140)]
