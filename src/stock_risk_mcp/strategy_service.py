from __future__ import annotations

import hashlib
from pathlib import Path

from stock_risk_mcp.repository import RiskRepository
from stock_risk_mcp.strategy_advisor import DisabledLocalLLMAdvisor, LocalLLMAdvisor
from stock_risk_mcp.strategy_core import DeterministicStrategyEngine, StrategyRun
from stock_risk_mcp.strategy_fixture import load_strategy_fixture


class StrategyService:
    def __init__(
        self, repository: RiskRepository, engine=None, advisor: LocalLLMAdvisor | None = None
    ) -> None:
        self.repository = repository
        self.engine = engine or DeterministicStrategyEngine()
        self.advisor = advisor or DisabledLocalLLMAdvisor()

    def run_fixture(self, path: str | Path, include_llm_review: bool = False) -> dict:
        selected = Path(path)
        fixture = load_strategy_fixture(selected)
        run = StrategyRun(
            fixture_checksum=hashlib.sha256(selected.read_bytes()).hexdigest(),
            engine_name=self.engine.name,
            snapshot_count=len(fixture.snapshots),
            candidate_count=len(fixture.candidates),
            decision_count=len(fixture.candidates),
        )
        self.repository.save_strategy_run(run)
        snapshots = {item.snapshot_id: item for item in fixture.snapshots}
        for snapshot in fixture.snapshots:
            self.repository.save_strategy_feature_snapshot(snapshot, run.run_id)
        decisions = []
        reviews = []
        for candidate in fixture.candidates:
            self.repository.save_strategy_candidate(candidate, run.run_id)
            decision = self.engine.decide(snapshots[candidate.snapshot_id], candidate, fixture.config).model_copy(
                update={"run_id": run.run_id}
            )
            self.repository.save_strategy_decision(decision)
            decisions.append(decision)
            if include_llm_review:
                review = self.advisor.review(run.run_id, snapshots[candidate.snapshot_id], candidate, decision)
                self.repository.save_local_llm_review(review)
                reviews.append(review)
        return {"run": run, "decisions": decisions, "local_llm_reviews": reviews}
