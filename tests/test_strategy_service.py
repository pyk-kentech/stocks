import json

from stock_risk_mcp.repository import RiskRepository
from stock_risk_mcp.strategy_core import StrategyDecisionStatus
from stock_risk_mcp.strategy_service import StrategyService


def fixture_file(tmp_path):
    path = tmp_path / "fixture.json"
    path.write_text(json.dumps({
        "schema_version": "3.0", "config": {},
        "snapshots": [{"snapshot_id": "s1", "ticker": "ABC", "region": "US", "observed_at": "2026-06-15T00:00:00", "features": {"signal_score": 0.8, "risk_score": 0.2, "hard_block": False}}],
        "candidates": [{"candidate_id": "c1", "snapshot_id": "s1", "side": "BUY", "order_type": "LIMIT", "quantity": 1, "limit_price": 10, "rationale": "fixture"}],
    }), encoding="utf-8")
    return path


def test_strategy_service_runs_fixture_and_persists_audit(tmp_path) -> None:
    repository = RiskRepository(tmp_path / "risk.sqlite3")
    result = StrategyService(repository).run_fixture(fixture_file(tmp_path))

    assert result["run"].status.value == "COMPLETED"
    assert result["decisions"][0].status == StrategyDecisionStatus.CANDIDATE_BUY
    assert repository.get_strategy_run(result["run"].run_id) == result["run"]
    assert repository.get_strategy_candidate("c1").candidate_id == "c1"
    assert repository.get_strategy_decision(result["decisions"][0].decision_id).status == StrategyDecisionStatus.CANDIDATE_BUY
    assert repository.list_local_llm_reviews() == []


def test_strategy_service_can_record_disabled_advisory_review(tmp_path) -> None:
    repository = RiskRepository(tmp_path / "risk.sqlite3")
    result = StrategyService(repository).run_fixture(fixture_file(tmp_path), include_llm_review=True)
    reviews = repository.list_local_llm_reviews()
    assert len(reviews) == 1
    assert reviews[0].decision_id == result["decisions"][0].decision_id
    assert reviews[0].metadata_json["advisory_only"] is True
