from __future__ import annotations

from typing import TYPE_CHECKING

from stock_risk_mcp.strategy_experiments import StrategyExperiment, create_common_outcome_experiment
from stock_risk_mcp.strategy_objective import StrategyRecommendation
from stock_risk_mcp.strategy_policy import (
    StrategyPolicy,
    StrategyPolicyCreator,
    StrategyPolicyStatus,
    normalize_weights,
    validate_strategy_policy,
)

if TYPE_CHECKING:
    from stock_risk_mcp.repository import RiskRepository


MUTATIONS = [
    "volume_spike_score_up",
    "dollar_volume_score_up",
    "volatility_penalty_up",
    "max_drawdown_penalty_up",
    "risk_reward_score_up",
    "setup_grade_score_up",
    "rsi_score_down",
    "return_5d_score_down",
    "A_threshold_up",
    "B_threshold_up",
    "max_basket_loss_pct_down",
    "max_single_candidate_loss_pct_down",
]


class StrategyOptimizer:
    def __init__(self, repository: RiskRepository | None = None) -> None:
        self.repository = repository

    def propose_candidate_policies(self, baseline: StrategyPolicy, n: int) -> list[StrategyPolicy]:
        if n < 0:
            raise ValueError("n must be non-negative")
        candidates = []
        for index in range(n):
            candidate = self.perturb_policy(baseline, MUTATIONS[index % len(MUTATIONS)])
            cycle = index // len(MUTATIONS)
            if cycle:
                candidate = candidate.model_copy(update={"version": f"{candidate.version}-{cycle + 1}"})
            candidates.append(candidate)
        return candidates

    def perturb_policy(self, baseline: StrategyPolicy, mutation_id: str) -> StrategyPolicy:
        weights = baseline.weights.copy()
        thresholds = baseline.setup_thresholds.copy()
        risk_overrides = baseline.risk_overrides.copy()
        if mutation_id.endswith("_score_up") or mutation_id.endswith("_penalty_up"):
            key = mutation_id.removesuffix("_up")
            weights[key] = weights[key] + 0.03
            weights = normalize_weights(weights)
        elif mutation_id.endswith("_score_down"):
            key = mutation_id.removesuffix("_down")
            weights[key] = max(0, weights[key] - 0.03)
            weights = normalize_weights(weights)
        elif mutation_id == "A_threshold_up":
            thresholds["A"] += 5
        elif mutation_id == "B_threshold_up":
            thresholds["B"] += 5
        elif mutation_id == "max_basket_loss_pct_down":
            risk_overrides["max_basket_loss_pct"] = max(
                0.01, float(risk_overrides["max_basket_loss_pct"]) - 0.25
            )
        elif mutation_id == "max_single_candidate_loss_pct_down":
            risk_overrides["max_single_candidate_loss_pct"] = max(
                0.01, float(risk_overrides["max_single_candidate_loss_pct"]) - 0.05
            )
        else:
            raise ValueError(f"Unsupported mutation_id: {mutation_id}")
        candidate = StrategyPolicy(
            policy_id=baseline.policy_id,
            version=f"{baseline.version}-{mutation_id}",
            status=StrategyPolicyStatus.DRAFT,
            weights=weights,
            setup_thresholds=thresholds,
            basket_rules=baseline.basket_rules.copy(),
            risk_overrides=risk_overrides,
            created_by=StrategyPolicyCreator.OPTIMIZER,
            reason=f"Deterministic mutation: {mutation_id}",
            parent_policy_id=baseline.policy_id,
            parent_version=baseline.version,
            created_at=baseline.created_at,
        )
        return validate_strategy_policy(candidate)

    def evaluate_policy_from_basket_results(self, policy: StrategyPolicy, horizon_days: int) -> StrategyExperiment:
        if self.repository is None:
            raise ValueError("repository is required for policy evaluation")
        baseline = self.repository.get_active_strategy_policy() or policy
        results = self.repository.list_basket_backtest_results(limit=None)
        return create_common_outcome_experiment(baseline, policy, results, horizon_days)

    def recommend_best_policy(self, experiments: list[StrategyExperiment]) -> StrategyPolicy | None:
        if self.repository is None:
            raise ValueError("repository is required for policy recommendation")
        accepted = [item for item in experiments if item.recommendation == StrategyRecommendation.ACCEPT]
        if not accepted:
            return None
        best = max(accepted, key=lambda item: item.objective_score)
        return self.repository.get_strategy_policy(best.candidate_policy_id, best.candidate_version)
