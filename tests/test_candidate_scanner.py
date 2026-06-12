from datetime import date, timedelta

from stock_risk_mcp.asof_price_history import AsOfPriceHistoryProvider
from stock_risk_mcp.candidate_scanner import scan_candidate
from stock_risk_mcp.candidate_universe import CandidateScanPolicy
from stock_risk_mcp.models import PriceBar
from stock_risk_mcp.repository import RiskRepository
from stock_risk_mcp.strategy_policy import create_default_strategy_policy


def test_scanner_uses_only_asof_history_and_excludes_insufficient_data(tmp_path) -> None:
    repository = RiskRepository(tmp_path / "risk.sqlite3")
    cutoff = date(2026, 1, 5)
    repository.save_price_bars(_bars("GOOD", date(2025, 9, 1), 140) + _bars("SHORT", date(2026, 1, 1), 5))
    provider = AsOfPriceHistoryProvider(repository=repository)

    good = scan_candidate("run", "GOOD", cutoff, provider, repository, CandidateScanPolicy())
    short = scan_candidate("run", "SHORT", cutoff, provider, repository, CandidateScanPolicy())

    assert good.metadata["last_price_date"] <= cutoff.isoformat()
    assert short.decision.value == "EXCLUDE"
    assert any("insufficient" in reason.lower() for reason in short.reasons)


def test_scanner_propagates_strategy_policy_metadata(tmp_path) -> None:
    repository = RiskRepository(tmp_path / "risk.sqlite3")
    cutoff = date(2026, 1, 5)
    repository.save_price_bars(_bars("GOOD", date(2025, 9, 1), 140))

    result = scan_candidate(
        "run", "GOOD", cutoff, AsOfPriceHistoryProvider(repository=repository),
        repository, CandidateScanPolicy(), create_default_strategy_policy(),
    )

    assert result.metadata["policy_id"] == "default"
    assert result.metadata["policy_version"] == "v1"
    assert result.metadata["scoring_mode"] == "POLICY_WEIGHTED"


def _bars(ticker, start, count):
    return [PriceBar(ticker=ticker, date=start + timedelta(days=i), open=10+i*.1, high=11+i*.1, low=9.5+i*.1, close=10.5+i*.1, volume=5_000_000+i*100_000) for i in range(count)]
